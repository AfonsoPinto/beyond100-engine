"""
Vai buscar fotos de jogadores com LICENÇA LIVRE (Wikidata + Wikimedia Commons).

Fluxo, por jogador:
  1. Procura o jogador na Wikidata e confirma que é tenista (e, se houver data de nascimento, que coincide).
  2. Lê a imagem principal (P18) e, na Commons, a licença e o autor.
  3. Só aceita CC0 / domínio público / CC BY (sem SA, NC ou ND). Guarda a foto em photos/ e o crédito
     em photos/credits.json (o cartão mostra o crédito automaticamente). Regista a origem em photos/sources.json.

Uso:
    py fetch_photos.py "Nome Do Jogador" --birthday 1997-02-19
    set FETCH_PHOTOS=1     (o result_card.py passa a chamar isto sozinho, uma vez por jogador)

Variáveis: WIKI_CONTACT (o teu email, a Wikimedia pede-o no User-Agent), PHOTO_DIR (por omissão photos),
           ALLOW_SA=1 para aceitar também CC BY-SA (NÃO recomendado: obriga a partilhar a imagem sob a mesma licença).

Cobertura: só existe foto para quem tem imagem na Wikidata. Muitos jogadores de Challenger/ITF não têm; nesses
casos o cartão continua a usar o monograma. Uma licença livre não dispensa atribuição nem cobre marcas ou
patrocinadores visíveis na foto. Não é aconselhamento jurídico.
Requisitos: py -m pip install requests pillow
"""
import argparse
import html
import json
import os
import urllib.parse
import re
import sys
import time
import unicodedata

PHOTO_DIR = os.environ.get("PHOTO_DIR", "photos")
UA = f"Beyond100/0.1 (https://beyond100.tennis; {os.environ.get('WIKI_CONTACT', 'contact-not-set')})"
WD = "https://www.wikidata.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
Q_HUMAN, Q_TENNIS = "Q5", "Q10833314"
MISS_RETRY_DAYS = 10


def slug(text):
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def _get(url, params):
    import requests
    r = requests.get(url, params={**params, "format": "json"}, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    time.sleep(0.25)  # simpatia com o servidor
    return r.json()


def _download(url, path):
    import requests
    from PIL import Image
    import io
    r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    r.raise_for_status()
    Image.open(io.BytesIO(r.content)).convert("RGB").save(path, quality=92)


def _claim_ids(entity, prop):
    out = []
    for c in entity.get("claims", {}).get(prop, []):
        v = (c.get("mainsnak", {}).get("datavalue") or {}).get("value")
        if isinstance(v, dict) and "id" in v:
            out.append(v["id"])
    return out


def _birth(entity):
    for c in entity.get("claims", {}).get("P569", []):
        v = (c.get("mainsnak", {}).get("datavalue") or {}).get("value")
        if isinstance(v, dict) and v.get("time"):
            return v["time"][1:11]          # "+1997-02-19T00:00:00Z" -> "1997-02-19"
    return None


def _find_entity(name, birthday=None):
    """Item da Wikidata do tenista que bate certo com nome (e data de nascimento), ou None."""
    found = _get(WD, {"action": "wbsearchentities", "search": name, "language": "en", "type": "item", "limit": 7})
    ids = [x["id"] for x in found.get("search", [])]
    if not ids:
        return None
    ents = _get(WD, {"action": "wbgetentities", "ids": "|".join(ids), "props": "claims"}).get("entities", {})
    cands = []
    for qid in ids:
        e = ents.get(qid, {})
        if Q_HUMAN not in _claim_ids(e, "P31") or Q_TENNIS not in _claim_ids(e, "P106"):
            continue
        if birthday and _birth(e) and _birth(e) != birthday:
            continue
        cands.append(e)
    if not cands or (not birthday and len(cands) > 1):   # sem data de nascimento, só aceita um candidato único
        return None
    return cands[0]


def find_image_file(name, birthday=None):
    """Nome do ficheiro da Commons (P18) de um tenista que bate certo com nome (e data de nascimento)."""
    e = _find_entity(name, birthday)
    if not e:
        return None
    for c in e.get("claims", {}).get("P18", []):
        v = (c.get("mainsnak", {}).get("datavalue") or {}).get("value")
        if isinstance(v, str):
            return v
    return None


def fetch_handle(name, birthday, photo_dir=None):
    """Perfil de Instagram (@utilizador) a partir da Wikidata (P2003). EXIGE data de nascimento, para não trocar de pessoa."""
    photo_dir = photo_dir or PHOTO_DIR
    key = slug(name)
    if not key or not birthday:
        return None
    os.makedirs(photo_dir, exist_ok=True)
    path = os.path.join(photo_dir, "handles_cache.json")
    cache = _load(path, {})
    hit = cache.get(key)
    if hit and (hit.get("h") or time.time() - hit.get("ts", 0) < MISS_RETRY_DAYS * 86400):
        return hit.get("h") or None
    try:
        e = _find_entity(name, birthday)
    except Exception as ex:
        print(f"Falha ao procurar perfil de {name}: {ex}", file=sys.stderr)
        return None
    h = None
    if e:
        for c in e.get("claims", {}).get("P2003", []):
            if c.get("rank") == "deprecated":
                continue
            v = (c.get("mainsnak", {}).get("datavalue") or {}).get("value")
            if isinstance(v, str) and re.fullmatch(r"[A-Za-z0-9._]{1,30}", v):
                h = "@" + v
                break
    cache[key] = {"h": h, "ts": time.time()}
    _save(path, cache)
    return h


def license_ok(lic):
    L = (lic or "").upper().strip()
    if L.startswith("CC0") or L.startswith("PUBLIC DOMAIN") or L.startswith("PDM"):
        return True
    m = re.match(r"CC BY(?:-([A-Z-]+))? \d", L)
    if not m:
        return False
    mods = m.group(1)
    return mods is None or (mods == "SA" and os.environ.get("ALLOW_SA") == "1")


def _day(txt):
    """'2024-05-30 10:12:00' / '2024:05:30' / '30 May 2024' -> 'AAAA-MM-DD' (ou só o ano); '' se não houver data."""
    t = re.sub(r"<[^>]+>", "", txt or "")
    m = re.search(r"(20\d\d|19\d\d)[-:/.](\d\d)[-:/.](\d\d)", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    y = re.search(r"(20\d\d|19\d\d)", t)
    return y.group(1) + "-00-00" if y else ""


def commons_info(filename):
    q = _get(COMMONS, {"action": "query", "titles": "File:" + filename, "prop": "imageinfo",
                       "iiprop": "url|extmetadata", "iiurlwidth": 800})
    for page in q.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [None])[0]
        if not info:
            continue
        meta = info.get("extmetadata", {})
        val = lambda k: (meta.get(k) or {}).get("value", "")
        artist = re.sub(r"<[^>]+>", "", html.unescape(val("Artist"))).strip()
        return {"url": info.get("thumburl") or info.get("url"), "license": val("LicenseShortName"),
                "artist": artist[:60] or "Wikimedia Commons", "page": info.get("descriptionurl", ""),
                "taken": _day(val("DateTimeOriginal") or val("DateTime"))}
    return None


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


FLICKR_LIC = {"4": "CC BY 2.0", "5": "CC BY-SA 2.0", "9": "CC0 1.0", "10": "Public Domain Mark 1.0"}


def flickr_find(name, all_=False):
    """Procura no Flickr (só licenças CC BY, CC0, domínio público e, se ALLOW_SA=1, CC BY-SA). Exige o nome completo e 'tennis' no
    título/etiquetas/descrição e uma imagem com pelo menos 800 px. Devolve {url, license, artist, page} ou None.
    Precisa da chave gratuita FLICKR_KEY."""
    key = os.environ.get("FLICKR_KEY")
    if not key:
        return [] if all_ else None
    import requests
    lic = "4,9,10" + (",5" if os.environ.get("ALLOW_SA") == "1" else "")
    r = requests.get("https://api.flickr.com/services/rest/", params={
        "method": "flickr.photos.search", "api_key": key, "text": f'"{name}" tennis', "license": lic, "media": "photos",
        "content_type": 1, "safe_search": 1, "sort": "relevance", "per_page": 25, "format": "json", "nojsoncallback": 1,
        "extras": "license,owner_name,tags,description,url_l,url_c,url_o,path_alias,date_taken"}, headers={"User-Agent": UA}, timeout=20)
    r.raise_for_status()
    time.sleep(0.3)
    want = re.sub(r"[^a-z0-9]", "", slug(name))
    found = []
    for p in (r.json().get("photos") or {}).get("photo", []):
        text = " ".join([p.get("title", ""), p.get("tags", ""), (p.get("description") or {}).get("_content", "")])
        flat = re.sub(r"[^a-z0-9]", "", slug(text))
        if want not in flat or "tennis" not in text.lower():
            continue
        url, w = None, 0
        for k in ("url_l", "url_c"):
            if p.get(k) and int(p.get("width_" + k[-1], 0) or 0) >= 800:
                url, w = p[k], int(p["width_" + k[-1]])
                break
        if not url or str(p.get("license")) not in FLICKR_LIC:
            continue
        owner = p.get("ownername") or "Flickr user"
        cand = {"url": url, "license": FLICKR_LIC[str(p["license"])], "artist": f"{owner} (Flickr)",
                "page": f"https://www.flickr.com/photos/{p.get('pathalias') or p.get('owner')}/{p['id']}",
                "taken": _day(p.get("datetaken", ""))}
        if not all_:
            return cand
        found.append(cand)
    return found if all_ else None


def commons_search(name, max_ratio=1.6, all_=False):
    """Procura ficheiros na Commons pelo nome do jogador (além da foto principal da Wikidata): licença livre aceite, nome completo no título,
    descrição ou categorias, largura >= 800 px. Devolve a mais recente (mesmo formato de commons_info) ou None. Sem chave."""
    want = re.sub(r"[^a-z0-9]", "", slug(name))
    if not want:
        return [] if all_ else None
    found = []
    q = _get(COMMONS, {"action": "query", "generator": "search", "gsrnamespace": 6, "gsrlimit": 20,
                       "gsrsearch": f'"{name}" tennis', "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1000})
    best = None
    for page in (q.get("query") or {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [None])[0]
        if not info or "jpeg" not in (info.get("mime") or "") or (info.get("width") or 0) < 800:
            continue
        meta = info.get("extmetadata", {})
        val = lambda k: (meta.get(k) or {}).get("value", "")
        # o nome tem de estar no NOME DO FICHEIRO (nas categorias/descrição aparecem também fotos de estádios e de outros jogadores)
        title = re.sub(r"^File:", "", page.get("title", ""))
        w_, h_ = info.get("width") or 0, info.get("height") or 1
        if want not in re.sub(r"[^a-z0-9]", "", slug(title)) or not license_ok(val("LicenseShortName")):
            continue
        if w_ / h_ > max_ratio or w_ / h_ < 0.5:          # panorâmicas e imagens muito estreitas não servem para o cartão
            continue
        if re.search(r"\b(vs|v|versus|and|final|stadium|court|crowd|trophy)\b", title.lower()) and want not in re.sub(r"[^a-z0-9]", "", slug(title.split(" vs ")[0])):
            continue
        artist = re.sub(r"<[^>]+>", "", html.unescape(val("Artist"))).strip()
        cand = {"url": info.get("thumburl") or info.get("url"), "license": val("LicenseShortName"),
                "artist": artist[:60] or "Wikimedia Commons", "page": info.get("descriptionurl", ""),
                "taken": _day(val("DateTimeOriginal") or val("DateTime"))}
        if cand["url"]:
            found.append(cand)
        if cand["url"] and (best is None or (cand["taken"] or "") > (best["taken"] or "")):
            best = cand
    return sorted(found, key=lambda c: c.get("taken") or "", reverse=True) if all_ else best


OFFCOURT = re.compile(r"laureus|award|gala\b|red[_ -]?carpet|ceremony|premiere|reception|wedding|press[_ -]?conference|"
                      r"interview|photocall|party|dinner|charity|fashion|met[_ -]gala", re.I)


def off_court(page_or_title):
    """Foto fora do court (gala, prémios, passadeira vermelha…): só como último recurso nos posts."""
    return bool(OFFCOURT.search(requests_unquote(page_or_title or "")))


def requests_unquote(t):
    try:
        from urllib.parse import unquote
        return unquote(t)
    except Exception:
        return t


def title_ok(name, title):
    """O nome do ficheiro tem de conter o apelido do jogador (evita estádios, multidões e outras pessoas)."""
    t = slug(re.sub(r"^File:", "", title or ""))
    toks = [x for x in slug(name).split("-")[1:] if len(x) >= 4] or [x for x in slug(name).split("-") if len(x) >= 4]
    return bool(toks) and any(x in t for x in toks)


def audit_photos(photo_dir=None):
    """Apaga fotos descarregadas cujo nome de ficheiro não identifica o jogador (ex.: panorâmicas de estádio). Sem rede.
    Fotos postas à mão (sem commons_page em sources.json) nunca são tocadas. Voltam a ser procuradas com as regras atuais."""
    photo_dir = photo_dir or PHOTO_DIR
    sp = os.path.join(photo_dir, "sources.json")
    sources = _load(sp, {})
    bad = []
    for fn, v in sources.items():
        m = re.search(r"/wiki/(File:[^?#]+)", (v or {}).get("commons_page", ""))
        if m and not title_ok(fn[:-4], urllib.parse.unquote(m.group(1))):
            bad.append(fn)
    for fn in bad:
        try:
            os.remove(os.path.join(photo_dir, fn))
        except OSError:
            pass
        for f in ("sources.json", "credits.json", "refresh.json"):
            d = _load(os.path.join(photo_dir, f), {})
            d.pop(fn, None)
            d.pop(fn[:-4], None)
            _save(os.path.join(photo_dir, f), d)
        print(f"Foto removida (o nome do ficheiro não identifica o jogador): {fn}")
    return bad


def _candidate(name, birthday=None):
    """Melhor foto livre disponível (Wikimedia e Flickr; a mais recente). Devolve (info, motivo_se_falhar)."""
    info, why = None, ""
    fname = find_image_file(name, birthday)
    if not fname:
        why = "sem imagem na Wikidata ou jogador não identificado com certeza"
    else:
        info = commons_info(fname)
        if info and not title_ok(name, fname):
            info, why = None, f"o ficheiro da Wikidata ({fname}) não identifica o jogador"
        elif not info or not info["url"]:
            info, why = None, "ficheiro não encontrado na Commons"
        elif not license_ok(info["license"]):
            why, info = f"licença não aceite ({info['license'] or 'desconhecida'})", None
    # se já há foto principal (Wikidata), a pesquisa só a troca por retratos (altura >= largura): estádios e vistas largas ficam de fora
    ratio = 1.15 if info else 1.6
    def _on(lst):
        return next((x for x in (lst or []) if not off_court(x.get("page"))), None)
    for finder in (lambda nm: _on(commons_search(nm, ratio, all_=True)), flickr_find):    # outras fotos da Commons e, com chave, do Flickr
        try:
            c = finder(name)
        except Exception as e:
            print(f"pesquisa por nome: {name}: {e}", file=sys.stderr)
            continue
        if not c or off_court(c.get("page")):
            continue
        # a foto principal da Wikidata é a mais segura quanto a quem está na imagem: só é trocada por outra
        # se tiver data conhecida e a nova for comprovadamente mais recente, ou se a principal for de fora do court (gala, prémios)
        if not info or off_court(info.get("page")) or ((info.get("taken") or "") and (c.get("taken") or "") > info["taken"]):
            info = c
    return info, why


def _save_info(photo_dir, key, info):
    credits = _load(os.path.join(photo_dir, "credits.json"), {})
    credits[key + ".jpg"] = f"Photo: {info['artist']} / {info['license']}"
    _save(os.path.join(photo_dir, "credits.json"), credits)
    sources = _load(os.path.join(photo_dir, "sources.json"), {})
    sources[key + ".jpg"] = {"commons_page": info["page"], "license": info["license"], "artist": info["artist"],
                             "taken": info.get("taken", "")}
    _save(os.path.join(photo_dir, "sources.json"), sources)


REFRESH_DAYS = 30


def refresh_photo(name, birthday=None, photo_dir=None):
    """Troca a foto guardada por uma mais recente, se existir. Só mexe em fotos descarregadas por esta pipeline
    (as que estão em sources.json); fotos postas à mão nunca são alteradas. Verifica cada jogador no máx. 1 vez por mês."""
    photo_dir = photo_dir or PHOTO_DIR
    key = slug(name)
    dest = os.path.join(photo_dir, key + ".jpg")
    sources = _load(os.path.join(photo_dir, "sources.json"), {})
    cur = sources.get(key + ".jpg")
    if not key or not os.path.exists(dest) or not cur or is_blocked(key, photo_dir):
        return False
    rpath = os.path.join(photo_dir, "refresh.json")
    done = _load(rpath, {})
    if time.time() - done.get(key, 0) < REFRESH_DAYS * 86400:
        return False
    done[key] = time.time()
    _save(rpath, done)
    taken = cur.get("taken")
    if not taken:                                    # fotos antigas sem data: vai buscá-la à página de origem
        m = re.search(r"/wiki/(File:[^?#]+)", cur.get("commons_page", ""))
        if m:
            try:
                ci = commons_info(urllib.parse.unquote(m.group(1))[5:])
                taken = (ci or {}).get("taken", "")
            except Exception:
                pass
    try:
        info, _ = _candidate(name, birthday)
        if not taken or not info or not (info.get("taken") or "") > taken:    # sem data da foto atual não arrisca trocar
            return False
        if info["page"] == cur.get("commons_page"):
            return False
        _download(info["url"], dest)
    except Exception as e:
        print(f"Atualizar foto de {name}: {e}", file=sys.stderr)
        return False
    _save_info(photo_dir, key, info)
    print(f"Foto de {name} trocada por uma mais recente ({info.get('taken')}).")
    return True


def is_blocked(key, photo_dir=None):
    """Jogadores cuja foto automática foi recusada à mão (photos/blocked.json). Podem ter foto posta à mão em photos/<nome>.jpg."""
    return key in set(_load(os.path.join(photo_dir or PHOTO_DIR, "blocked.json"), []))


def fetch_photo(name, birthday=None, photo_dir=None):
    """Devolve o caminho da foto guardada, ou None. Nunca guarda fotos sem licença aceite."""
    photo_dir = photo_dir or PHOTO_DIR
    key = slug(name)
    if not key:
        return None
    os.makedirs(photo_dir, exist_ok=True)
    dest = os.path.join(photo_dir, key + ".jpg")
    if os.path.exists(dest):
        return dest
    if is_blocked(key, photo_dir):
        return None
    misses_path = os.path.join(photo_dir, ("misses_sa" if os.environ.get("ALLOW_SA") == "1" else "misses")
                               + "_cs" + ("_fl" if os.environ.get("FLICKR_KEY") else "") + ".json")
    misses = _load(misses_path, {})
    if time.time() - misses.get(key, 0) < MISS_RETRY_DAYS * 86400:
        return None

    def miss(reason):
        misses[key] = time.time()
        _save(misses_path, misses)
        print(f"Sem foto livre para {name}: {reason}", file=sys.stderr)
        return None

    try:
        info, why = _candidate(name, birthday)
        if not info:
            return miss(why or "sem foto")
        _download(info["url"], dest)
    except Exception as e:                       # rede em baixo, limite de pedidos, etc.
        print(f"Falha ao obter foto de {name}: {e}", file=sys.stderr)
        return None
    _save_info(photo_dir, key, info)
    return dest


# ---------------------------------------------------------------- galeria (várias fotos recentes por jogador, para alternar nos posts)
GALLERY_MAX = int(os.environ.get("PHOTO_GALLERY") or "6")          # fotos extra por jogador (além da principal)
PHOTO_MAX_AGE_Y = int(os.environ.get("PHOTO_MAX_AGE_Y") or "3")    # só fotos extra tiradas nos últimos N anos (com data conhecida)
GALLERY_EVERY_D = 30


def recent_cutoff():
    return f"{time.gmtime().tm_year - PHOTO_MAX_AGE_Y}-{time.strftime('%m-%d', time.gmtime())}"


def main_taken(key, photo_dir=None):
    """Data (AAAA-MM-DD) da foto principal do jogador, se conhecida."""
    sources = _load(os.path.join(photo_dir or PHOTO_DIR, "sources.json"), {})
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        t = (sources.get(key + ext) or {}).get("taken")
        if t:
            return t
    return ""


def gallery(name, birthday=None, photo_dir=None, force=False):
    """Junta até GALLERY_MAX fotos extra, recentes e com licença aceite, em photos/alt/<jogador>-<n>.jpg.
    Mesmas regras da foto principal (nome do jogador no ficheiro/título, licença livre, tamanho mínimo). No máx. 1 vez por mês por jogador.
    Fotos recusadas à mão (fix_photos com bloqueio) ficam em photos/blocked_pages.json e nunca voltam."""
    photo_dir = photo_dir or PHOTO_DIR
    key = slug(name)
    if not key or is_blocked(key, photo_dir) or GALLERY_MAX <= 0:
        return []
    gpath = os.path.join(photo_dir, "gallery.json")
    state = _load(gpath, {})
    if not force and time.time() - state.get(key, 0) < GALLERY_EVERY_D * 86400:
        return []
    state[key] = time.time()
    _save(gpath, state)
    sources = _load(os.path.join(photo_dir, "sources.json"), {})
    have = {v.get("commons_page") for v in sources.values() if isinstance(v, dict)}
    blocked = set(_load(os.path.join(photo_dir, "blocked_pages.json"), []))
    cut = recent_cutoff()
    cands = []
    for finder in (lambda nm: commons_search(nm, 1.15, all_=True), lambda nm: flickr_find(nm, all_=True)):
        try:
            cands += finder(name) or []
        except Exception as e:
            print(f"galeria: {name}: {e}", file=sys.stderr)
    cands = [c for c in cands if c.get("taken") and c.get("page") not in have and c.get("page") not in blocked
             and not off_court(c.get("page"))]
    recent = [c for c in cands if c["taken"] >= cut]
    if recent:
        cands = recent
    else:                         # sem fotos recentes: aceita as que forem pelo menos tão recentes como a foto principal
        mt = main_taken(key, photo_dir)
        cands = [c for c in cands if mt and c["taken"] >= mt]
    cands.sort(key=lambda c: c.get("taken") or "", reverse=True)
    os.makedirs(os.path.join(photo_dir, "alt"), exist_ok=True)
    added = []
    n = 1
    for c in cands:
        while os.path.exists(os.path.join(photo_dir, "alt", f"{key}-{n}.jpg")):
            n += 1
        if n > GALLERY_MAX:
            break
        rel = f"alt/{key}-{n}"
        try:
            _download(c["url"], os.path.join(photo_dir, rel + ".jpg"))
        except Exception as e:
            print(f"galeria: {name}: {e}", file=sys.stderr)
            continue
        _save_info(photo_dir, rel, c)
        have.add(c.get("page"))
        added.append(rel)
    if added:
        print(f"Galeria de {name}: +{len(added)} fotos recentes.")
    return added


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--birthday", help="AAAA-MM-DD (a API dá este campo; ajuda a não trocar de pessoa)")
    a = ap.parse_args()
    p = fetch_photo(a.name, a.birthday)
    print("Foto guardada em:" if p else "Sem foto livre.", p or "")
