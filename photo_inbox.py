"""Fotos com autorização (ex.: FPT) a partir de um link (pasta do Dropbox, .zip direto ou ficheiro).
Uso (workflow photo_inbox.yml, lançado no admin → Fotos):
  python photo_inbox.py --sport tennis|padel --url-b64 <link em base64> --credit "Foto: {fotógrafo}/FPT" [--fallback "Nome"] [--dry]
O que faz:
  1) descarrega e abre os .zip (também .zip dentro de .zip);
  2) identifica o jogador PELO NOME DO FICHEIRO, comparando com os jogadores que já temos nos dados
     (nunca pela cara); ficheiros com dois jogadores conhecidos, ou sem nenhum, ficam de fora;
  3) lê o fotógrafo dos dados da foto (EXIF Artist / IPTC By-line); sem fotógrafo e sem --fallback, não entra;
  4) escolhe a melhor foto de cada jogador (vertical primeiro, depois a maior), reduz para 1600 px e guarda-a
     só para quem AINDA NÃO TEM foto (as que já existem não são trocadas);
  5) escreve o relatório (o que entrou, o que ficou de fora e porquê) que o admin mostra."""
import argparse
import base64
import io
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
import zipfile

from PIL import Image, ImageOps

EXTS = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")
NOISE = {"atp", "wta", "itf", "open", "challenger", "lisboa", "belem", "maia", "porto", "oeiras", "final", "qf", "sf", "r16", "r32", "dsc", "img",
         "foto", "fotos", "photo", "maiaopen", "belemopen", "lisboabelemopen", "lbo", "mo", "court", "encontros", "ambiente", "the", "de", "da", "do", "dos", "das", "e"}


def toks(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return [t for t in re.split(r"[^a-z]+", s) if t]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).strip("-")


def known_players(sport):
    """{nome: chave} dos jogadores que já conhecemos (ténis: slug; padel: id)."""
    out = {}
    if sport == "padel":
        for pid, p in (json.load(open("padel/data/players.json", encoding="utf-8")) if os.path.exists("padel/data/players.json") else {}).items():
            if p.get("name"):
                out[p["name"]] = str(p.get("id") or pid)
        return out
    def add(n):
        if n and " / " not in n:
            out[n] = slug(n)
    for f in ("results.json", "archive.json"):
        try:
            for r in json.load(open(f, encoding="utf-8")):
                add(r["p1"]["name"]); add(r["p2"]["name"])
        except (OSError, ValueError, KeyError, TypeError):
            pass
    try:                                                           # jogadores que já receberam foto numa importação anterior
        for x in json.load(open("photos/inbox_log.json", encoding="utf-8")):
            if not x.get("dry"):
                for y in x.get("added") or []:
                    add(y.get("player"))
    except (OSError, ValueError):
        pass
    for f, key in (("ranks.json", None), ("upcoming.json", "matches"), ("live.json", "matches")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if key:
            for m in d.get(key) or []:
                add((m.get("p1") or {}).get("name")); add((m.get("p2") or {}).get("name"))
        else:
            for v in d.values():
                add((v or {}).get("name"))
    return out


# primeiros nomes comuns (sobretudo ibéricos, italianos, franceses, do leste): para ler 'JOAO DOMINGUES' como Nome + Apelido.
# 'BARRANCO COSANO' (dois apelidos) não começa por um nome destes e fica de fora; 'MARTIN TIFFON' entraria como 'Martin Tiffon',
# que não é ninguém nos nossos dados (a foto só aparece se um jogador tiver exatamente esse nome).
GIVEN = set("""joao jose antonio francisco manuel pedro paulo luis carlos miguel tiago diogo goncalo rui nuno ricardo bruno andre rafael
gustavo guilherme henrique duarte martim rodrigo tomas vasco afonso frederico fred filipe fabio hugo jaime marco marcos daniel david
alexandre alex alejandro alberto alvaro adrian angel javier jorge juan pablo sergio raul ruben roberto oscar ivan enrique fernando
gonzalo ignacio inigo jaume jordi pol oriol marc albert nicolas nico lucas mateo matias martin max maximo santiago sebastian thiago
lorenzo luca matteo francesco andrea giovanni giulio stefano simone federico riccardo leonardo gabriele mattia alessandro filippo
pierre jean louis hugo arthur theo leo lucas mathieu clement quentin romain benjamin antoine maxime thomas nicolas valentin
michael michal milos marko luka duje ivan nikola stefan petar filip matej jan jakub tomas lukas dominik vit zdenek ondrej
dmitry alexei andrei sergei oleksii ilya pavel nikita roman maxim vladimir yaroslav artem
john james robert william ryan patrick tristan trey dali sumit vilius zsombor elmer karol kimmer admir benjamin""".split())
ARTISTS = {"helenavalente": "Helena Valente", "eduardooliveira": "Eduardo Oliveira"}   # nomes que a câmara grava juntos


def _aliases():
    fp = "padel/photos/aliases.json" if "padel" in sys.argv else "photos/aliases.json"
    try:
        d = json.load(open(fp, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {" ".join(toks(k)): v.strip() for k, v in d.items() if isinstance(v, str) and len(v.split()) >= 2}


ALIASES = _aliases()


def _photographers():
    """Iniciais no nome do ficheiro -> fotógrafo, confirmadas à mão no admin (ex.: {'BR': 'Beatriz Ruivo'})."""
    fp = "padel/photos/photographers.json" if "padel" in sys.argv else "photos/photographers.json"
    try:
        return {k.upper(): v.strip() for k, v in json.load(open(fp, encoding="utf-8")).items() if isinstance(v, str) and v.strip()}
    except (OSError, ValueError):
        return {}


PHOTOGRAPHERS = _photographers()


def nice_artist(a):
    """'HELENAVALENTE' -> 'Helena Valente'; 'EDUARDO OLIVEIRA' -> 'Eduardo Oliveira'."""
    a = re.sub(r"\s+", " ", (a or "").strip())
    k = re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", a).encode("ascii", "ignore").decode().lower())
    if k in ARTISTS:
        return ARTISTS[k]
    return a.title() if a.isupper() else a


def split_name(fname):
    """Palavras do nome e iniciais do fotógrafo escritas no ficheiro. Formatos da FPT:
    'Diogo MARQUES (POR)_EO_04375.JPG', 'DUJE AJDUKOVIC_HV_03.JPG', 'Abdullah_Shelbayh_BelemOpen_18_10_023.jpg'.
    Devolve (['Diogo', 'MARQUES'], 'EO')."""
    b = os.path.splitext(os.path.basename(fname))[0]
    m = re.search(r"(?:^|[_\s)-])([A-Z]{2,3})(?=[_\s-]|\d|$)", re.sub(r"\(\w+\)", " ", b))
    ini = m.group(1) if m else ""
    head = re.split(r"\s*\(|_", b)[0]
    if " " in head.strip():                                       # 'Diogo MARQUES' / 'DUJE AJDUKOVIC'
        ws = [w for w in re.split(r"[\s.-]+", head) if w]
    else:                                                         # 'Abdullah_Shelbayh_BelemOpen_...': palavras no início
        ws = []
        for p in re.split(r"[_\s-]+", b):
            if not p or re.search(r"\d", p) or p.lower() in NOISE or (len(p) <= 3 and p.isupper()) or not p.isalpha():
                break
            ws.append(p)
    if ini and ws and ws[-1] == ini:
        ws = ws[:-1]
    if re.search(r"\bvs?\b|\bx\b|&|/", " ".join(ws), re.I) or not 1 <= len(ws) <= 4 or any(w.lower() in NOISE or len(w) < 2 for w in ws):
        ws = []
    return ws, ini


def name_from_file(fname):
    ws, _ = split_name(fname)
    return " ".join(w.title() if w.isupper() else w for w in ws)


def clear_name(ws):
    """O nome deixa claro qual é o primeiro nome? 'Diogo MARQUES', 'Joao Dinis SILVA', 'Abdullah Shelbayh' (título),
    ou tudo em maiúsculas começado por um primeiro nome comum ('JOAO DOMINGUES')."""
    if len(ws) < 2:
        return False
    if not ws[0].isupper() and ws[-1].isupper():
        return True
    if all(w[:1].isupper() and not w.isupper() for w in ws):
        return True
    return all(w.isupper() for w in ws) and len(ws) <= 3 and bool(toks(ws[0])) and toks(ws[0])[0] in GIVEN


def resolve_new(nm, players):
    """Nome lido do ficheiro que é quase igual a um jogador que já conhecemos (gralha ou nome incompleto): usa o conhecido.
    Só se houver UM candidato: todos os nomes do ficheiro dentro do nome conhecido, ou semelhança >= 0,9."""
    from difflib import SequenceMatcher
    t = toks(nm)
    if len(t) < 2:
        return None
    sub = [k for k in players if players.get(k) and set(t) <= set(toks(k)) and toks(k)[0] == t[0]]
    if len(sub) == 1:
        return sub[0]
    near = [k for k in players if players.get(k) and SequenceMatcher(None, " ".join(t), " ".join(toks(k))).ratio() >= 0.9]
    return near[0] if len(near) == 1 else None


def match(fname, players):
    """Jogador do nome do ficheiro: todos os nomes do jogador (2+ letras) têm de estar no nome do ficheiro.
    Devolve (nome, None) ou (None, motivo)."""
    from difflib import SequenceMatcher
    fl = toks(os.path.splitext(os.path.basename(fname))[0])
    ft = set(fl)
    hits = []
    for name in players:
        nt = [t for t in toks(name) if len(t) >= 2]
        if len(nt) < 2:
            continue
        if set(nt) <= ft:
            hits.append(name)
            continue
        # grafias diferentes do primeiro nome (Abdullah / Abedallah): apelido(s) exatos + primeiro nome parecido (>= 0,7)
        if set(nt[1:]) <= ft and any(SequenceMatcher(None, nt[0], t).ratio() >= 0.7 for t in fl if t not in nt[1:] and len(t) >= 3):
            hits.append(name)
    exact = [h for h in hits if set(t for t in toks(h) if len(t) >= 2) <= ft]
    if exact:
        hits = exact                                              # nome completo no ficheiro ganha a parecidos
    if not hits:
        return None, "nome não reconhecido"
    hits = [h for h in hits if not any(h != o and set(toks(h)) < set(toks(o)) for o in hits)]   # 'Joao Sousa' dentro de 'Joao Sousa Silva'
    if len({slug(h) for h in hits}) > 1:
        return None, "mais de um jogador no nome: " + " + ".join(sorted(hits))
    return hits[0], None


def photographer(im):
    """Fotógrafo guardado na foto: EXIF Artist/Copyright, IPTC By-line/Credit/Copyright ou XMP dc:creator."""
    clean = lambda v: re.sub(r"(?i)^(©|\(c\)|copyright|foto:?|photo:?)\s*", "", v or "").strip(" ,;/")
    try:
        ex = im.getexif()
        for tag in (0x013B, 0x8298):
            v = ex.get(tag)
            if isinstance(v, bytes):
                v = v.decode("utf-8", "ignore")
            if isinstance(v, str) and clean(v):
                return clean(v)
    except Exception:
        pass
    try:
        from PIL import IptcImagePlugin
        info = IptcImagePlugin.getiptcinfo(im) or {}
        for key in ((2, 80), (2, 116), (2, 110)):
            v = info.get(key)
            if isinstance(v, list):
                v = v[0]
            if isinstance(v, bytes) and clean(v.decode("utf-8", "ignore")):
                return clean(v.decode("utf-8", "ignore"))
    except Exception:
        pass
    try:
        x = im.info.get("xmp") or im.info.get("XML:com.adobe.xmp") or b""
        x = x.decode("utf-8", "ignore") if isinstance(x, bytes) else str(x)
        m = re.search(r"<dc:creator>.*?<rdf:li[^>]*>([^<]+)</rdf:li>", x, re.S) or re.search(r'dc:creator="([^"]+)"', x)
        if m and clean(m.group(1)):
            return clean(m.group(1))
    except Exception:
        pass
    return ""


def camera_serial(im):
    """Número de série da câmara (EXIF BodySerialNumber 0xA431, no bloco Exif) — para saber de quem é a câmara."""
    try:
        v = im.getexif().get_ifd(0x8769).get(0xA431)
        return str(v).strip() if v else ""
    except Exception:
        return ""


def initials(name):
    return "".join(w[0] for w in toks(name)).upper()


CAMERAS_FP = "photos/cameras.json"     # nº de série da câmara -> fotógrafo (aprendido nas fotos que trazem o nome)


def _stream(url, dest, method="GET", **kw):
    import requests
    with requests.request(method, url, stream=True, timeout=180, headers={"User-Agent": "Mozilla/5.0 Beyond100"}, **kw) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return dest


def download(url, dest):
    """Descarrega o link para 'dest' (ficheiro) ou para uma pasta (Google Drive). Aceita:
    Dropbox (pasta ou ficheiro), Google Drive (pasta ou ficheiro), OneDrive / SharePoint (ficheiro .zip),
    WeTransfer (we.tl / wetransfer.com) e qualquer link direto para um .zip ou uma foto."""
    import requests
    low = url.lower()
    if "dropbox.com" in low:
        url = re.sub(r"([?&])dl=0", r"\1dl=1", url)
        if "dl=1" not in url:
            url += ("&" if "?" in url else "?") + "dl=1"
        return _stream(url, dest)
    if "drive.google.com" in low or "docs.google.com" in low:
        import gdown
        if "/folders/" in low:                                    # pasta: descarrega tudo para uma pasta
            out = dest + "_dir"
            os.makedirs(out, exist_ok=True)
            gdown.download_folder(url, output=out, quiet=True, remaining_ok=True)
            return out
        return gdown.download(url, dest, quiet=True, fuzzy=True)
    if "1drv.ms" in low or "onedrive.live.com" in low:            # OneDrive pessoal: API pública de partilhas
        enc = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        return _stream(f"https://api.onedrive.com/v1.0/shares/u!{enc}/root/content", dest)
    if "sharepoint.com" in low:                                   # OneDrive empresarial / SharePoint
        return _stream(url + ("&" if "?" in url else "?") + "download=1", dest)
    if "we.tl" in low or "wetransfer.com" in low:
        if "we.tl" in low:
            url = requests.head(url, allow_redirects=True, timeout=30).url
        m = re.search(r"/downloads/([0-9a-f]+)/(?:[0-9a-f]+/)?([0-9a-f]+)", url)
        if not m:
            sys.exit("Link do WeTransfer não reconhecido (usa o link da página de download).")
        r = requests.post(f"https://wetransfer.com/api/v4/transfers/{m.group(1)}/download", timeout=60,
                          json={"security_hash": m.group(2), "intent": "entire_transfer"},
                          headers={"User-Agent": "Mozilla/5.0", "x-requested-with": "XMLHttpRequest"})
        r.raise_for_status()
        link = r.json().get("direct_link")
        if not link:
            sys.exit("O WeTransfer não deu link de download (pode ter expirado).")
        return _stream(link, dest)
    return _stream(url, dest)


def images_in(path):
    """(nome, bytes) de todas as imagens, abrindo .zip (e .zip dentro de .zip)."""
    def walk_zip(z, prefix=""):
        for n in z.namelist():
            low = n.lower()
            if n.endswith("/") or "__macosx" in low:
                continue
            if low.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(z.read(n))) as zz:
                    yield from walk_zip(zz, prefix + n + "/")
            elif low.endswith(EXTS):
                yield prefix + n, (lambda z=z, n=n: z.read(n))
    if os.path.isdir(path):                                        # Google Drive: pasta com fotos e/ou .zip
        for root, _, files in os.walk(path):
            for f in sorted(files):
                fp = os.path.join(root, f)
                if f.lower().endswith(".zip") and zipfile.is_zipfile(fp):
                    with zipfile.ZipFile(fp) as z:
                        yield from walk_zip(z, f + "/")
                elif f.lower().endswith(EXTS):
                    yield f, (lambda fp=fp: open(fp, "rb").read())
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            yield from walk_zip(z)
    else:
        yield os.path.basename(path), (lambda: open(path, "rb").read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", choices=("tennis", "padel"), required=True)
    ap.add_argument("--url-b64", required=True)
    ap.add_argument("--credit", default="Foto: {fotógrafo}/FPT")
    ap.add_argument("--fallback", default="")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--replace", action="store_true", help="troca fotos automáticas (Wikimedia) por estas; fotos postas à mão nunca")
    a = ap.parse_args()
    url = base64.b64decode(a.url_b64 + "=" * (-len(a.url_b64) % 4)).decode().strip()
    if not re.match(r"^https://", url):
        sys.exit("Link inválido (tem de começar por https://).")
    pdir = "padel/photos" if a.sport == "padel" else "photos"
    log_fp = os.path.join(pdir, "inbox_log.json")
    players = known_players(a.sport)
    print(f"{len(players)} jogadores conhecidos ({a.sport}).")
    tmp = tempfile.mkdtemp()
    src = download(url, os.path.join(tmp, "download.bin"))
    size = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(src) for f in fs) if os.path.isdir(src) else os.path.getsize(src)
    print("Descarregado:", size // 1024, "KB")
    best, skipped, n, later = {}, [], 0, []
    ini_art, no_art = {}, []                                       # iniciais do fotógrafo no ficheiro -> nome (aprendido nesta pasta)
    try:
        cams = json.load(open(CAMERAS_FP, encoding="utf-8"))
    except (OSError, ValueError):
        cams = {}
    for name, read in images_in(src):
        n += 1
        who, why = match(name, players)
        if not who and why == "nome não reconhecido":
            ws, _ini = split_name(name)
            nm = name_from_file(name)
            raw = " ".join(ws)
            # só confio num nome novo no formato 'Nome APELIDO' (primeiro nome em minúsculas, apelido em maiúsculas): é claro
            # qual é o primeiro nome. 'DUJE AJDUKOVIC' / 'BARRANCO COSANO' (tudo em maiúsculas) ficam para comparar depois.
            alias = ALIASES.get(" ".join(toks(raw)))
            if alias:                                              # nome confirmado à mão no admin (ex.: 'CACAO' -> nome completo)
                who = alias
                players.setdefault(alias, slug(alias) if a.sport == "tennis" else None)
            # 'Nome APELIDO' ou 'Nome Nome APELIDO' (o apelido em maiúsculas no fim): é claro qual é o primeiro nome;
            # 'JOAO DOMINGUES' (tudo em maiúsculas) só se a 1.ª palavra for um primeiro nome comum
            clear = clear_name(ws)
            if who:
                pass
            elif nm and clear and len(ws) >= 4 and " " not in os.path.basename(name).split("_")[0]:
                skipped.append({"file": os.path.basename(name), "why": "4 ou mais nomes seguidos (pode ser um par)"})
                continue
            elif nm and clear:                                     # jogador que ainda não está nos nossos dados
                who = resolve_new(nm, players) or nm               # 'Elmer Moler' -> 'Elmer Moller', 'Leyre Romero' -> 'Leyre Romero Gormaz'
                players.setdefault(who, slug(who) if a.sport == "tennis" else None)
            elif nm:
                later.append((name, read, nm))                    # tudo em maiúsculas ou só o apelido: compara com os nomes claros
                continue
        if not who:
            skipped.append({"file": os.path.basename(name), "why": why})
            continue
        if players.get(who) is None:
            skipped.append({"file": os.path.basename(name), "why": "padel: jogador não está nos nossos dados", "player": who})
            continue
        data = read()                                             # só lê do .zip as fotos de jogadores reconhecidos
        try:
            im = Image.open(io.BytesIO(data))                    # só lê o cabeçalho (rápido): tamanho e dados da câmara
        except Exception:
            skipped.append({"file": os.path.basename(name), "why": "imagem ilegível"})
            continue
        art0 = photographer(im)
        ser = camera_serial(im)
        if art0 and ser:
            cams[ser] = nice_artist(art0)
        ini = split_name(name)[1]
        if art0 and ini:
            ini_art.setdefault(ini, {}).setdefault(nice_artist(art0), 0)
            ini_art[ini][nice_artist(art0)] += 1
        art = art0 or a.fallback.strip()
        if not art:
            if ini:                                                # sem nome na foto, mas com iniciais ('_BR_'): vê depois se outras fotos as explicam
                no_art.append((who, name, data, im.size, ini, ser))
                continue
            skipped.append({"file": os.path.basename(name), "why": "sem fotógrafo nos dados da foto", "player": who})
            continue
        w, h = im.size
        try:
            if im.getexif().get(274) in (5, 6, 7, 8):             # foto rodada pela câmara
                w, h = h, w
        except Exception:
            pass
        score = (1 if h > w else 0, w * h)
        cur = best.get(who)
        if not cur or score > cur["score"]:
            best[who] = {"score": score, "data": data, "file": os.path.basename(name), "artist": art}
    for name, read, sur in later:          # 'DUJE AJDUKOVIC' = mesmo nome completo; 'NIJBOER' = UM só jogador com esse apelido
        st = toks(sur)
        if " ".join(st) in ALIASES:
            al = ALIASES[" ".join(st)]
            players.setdefault(al, slug(al) if a.sport == "tennis" else None)
            pool_alias = {al}
        else:
            pool_alias = None
        # nome completo: pode ser qualquer jogador conhecido; só o apelido: só os jogadores desta MESMA pasta (evita 'PEREZ' = outra pessoa)
        pool = pool_alias or (players if len(st) >= 2 else set(best))
        cands = pool_alias or {w for w in pool if players.get(w) and (toks(w) == st or (len(st) == 1 and toks(w)[-1:] == st))}
        if len(cands) != 1:
            skipped.append({"file": os.path.basename(name), "why": "só o apelido no nome" + (" (vários jogadores)" if cands else ""), "token": sur})
            continue
        who = cands.pop()
        try:
            data = read()
            im = Image.open(io.BytesIO(data))
        except Exception:
            continue
        art0 = photographer(im)
        ser = camera_serial(im)
        if art0 and ser:
            cams[ser] = nice_artist(art0)
        ini = split_name(name)[1]
        if art0 and ini:
            ini_art.setdefault(ini, {}).setdefault(nice_artist(art0), 0)
            ini_art[ini][nice_artist(art0)] += 1
        art = art0 or a.fallback.strip()
        if not art:
            if ini:                                                # sem nome na foto, mas com iniciais ('_BR_'): vê depois se outras fotos as explicam
                no_art.append((who, name, data, im.size, ini, ser))
                continue
            skipped.append({"file": os.path.basename(name), "why": "sem fotógrafo nos dados da foto", "player": who})
            continue
        w, h = im.size
        score = (1 if h > w else 0, w * h)
        if who not in best or score > best[who]["score"]:
            best[who] = {"score": score, "data": data, "file": os.path.basename(name), "artist": art}
    for who, name, data, (w, h), ini, ser in no_art:               # '_BR_' = o fotógrafo que assina '_BR_' nas outras fotos desta pasta
        arts = {PHOTOGRAPHERS[ini]: 1} if ini in PHOTOGRAPHERS else (ini_art.get(ini) or {})
        if not arts and ser in cams and initials(cams[ser]) == ini:   # mesma câmara de uma foto assinada E as iniciais batem certo
            arts = {cams[ser]: 1}
        if len(arts) != 1:
            skipped.append({"file": os.path.basename(name), "why": f"sem fotógrafo nos dados da foto (iniciais {ini})", "player": who, "ini": ini})
            continue
        art = next(iter(arts))
        score = (1 if h > w else 0, w * h)
        if who not in best or score > best[who]["score"]:
            best[who] = {"score": score, "data": data, "file": os.path.basename(name), "artist": art}
    print(f"{n} imagens, {len(best)} jogadores identificados, {len(skipped)} de fora.")
    cfp = os.path.join(pdir, "credits.json")
    credits = json.load(open(cfp, encoding="utf-8")) if os.path.exists(cfp) else {}
    added, had = [], []
    try:
        blocked = set(json.load(open(os.path.join(pdir, "inbox_block.json"), encoding="utf-8")).get("keys") or [])
    except (OSError, ValueError):
        blocked = set()
    changed = [log_fp, cfp, CAMERAS_FP]
    srcp = os.path.join(pdir, "sources.json")
    sources = json.load(open(srcp, encoding="utf-8")) if os.path.exists(srcp) else {}

    def automatic(key):
        """A foto atual veio da busca automática (Wikimedia/Flickr)? Só essas podem ser trocadas."""
        if a.sport == "padel":
            return bool((credits.get(key) or {}).get("auto"))
        return f"{key}.jpg" in sources
    for who, b in sorted(best.items()):
        key = players[who]
        dest = os.path.join(pdir, f"{key}.jpg")
        if key in blocked:                                         # retirada à mão (duas pessoas, par, nome errado): não volta
            skipped.append({"file": b["file"], "why": "jogador bloqueado (foto retirada à mão)", "player": who})
            continue
        art = nice_artist(b["artist"])
        cr = a.credit.replace("{fotógrafo}", art).replace("{fotografo}", art)
        if os.path.exists(dest) and not (a.replace and automatic(key)):
            had.append({"player": who, "file": b["file"], "credit": cr})
            continue
        if os.path.exists(dest) and a.sport != "padel":
            sources.pop(f"{key}.jpg", None)                       # deixa de ser 'automática': a busca semanal não a troca
        added.append({"player": who, "file": b["file"], "credit": cr, "key": key})
        if a.dry:
            continue
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(b["data"]))).convert("RGB")
        im.thumbnail((1600, 1600))
        im.save(dest, quality=88, optimize=True)                 # sem os dados da câmara (o crédito fica no credits.json)
        changed.append(dest)
        if a.sport == "padel":
            credits[key] = {"credit": cr, "page": url, "license": "Autorização FPT", "offcourt": False, "auto": time.strftime("%Y-%m-%d")}
        else:
            credits[f"{key}.jpg"] = cr
    log = json.load(open(log_fp, encoding="utf-8")) if os.path.exists(log_fp) else []
    log.append({"ts": time.time(), "url": re.sub(r"\?.*", "", url), "credit": a.credit, "dry": a.dry, "images": n,
                "added": added, "had_photo": had, "skipped_n": len(skipped),
                "reasons": {k: sum(1 for x in skipped if x["why"] == k) for k in {x["why"] for x in skipped}},
                "skipped": [x for k in {x["why"] for x in skipped} for x in [y for y in skipped if y["why"] == k][:40]]})
    json.dump(cams, open(CAMERAS_FP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)   # aprende mesmo numa simulação
    if not a.dry:
        json.dump(credits, open(cfp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        if a.sport != "padel" and os.path.exists(srcp):
            json.dump(sources, open(srcp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            changed.append(srcp)
    # só estes ficheiros vão para o GitHub (assim nunca repõe fotos apagadas entretanto)
    open(".inbox_changed", "w").write("\n".join(sorted(set(p for p in changed if os.path.exists(p)))))
    json.dump(log[-20:], open(log_fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Entraram {len(added)} fotos novas; {len(had)} jogadores já tinham foto; {len(skipped)} imagens de fora.")
    for x in added:
        print("  +", x["player"], "·", x["credit"])


if __name__ == "__main__":
    main()
