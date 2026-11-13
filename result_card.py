"""
Gera cartões de resultado de ténis (1080x1350, formato Instagram 4:5)
a partir da Live Tennis API.

Uso (PowerShell):
    py result_card.py                  # cartões de exemplo (sem API)
    $env:LIVETENNIS_KEY="a_tua_chave"  # define a chave só nesta janela
    py result_card.py --live           # jogos ao vivo reais
    py result_card.py --live --pt      # só jogos com jogadores portugueses
    py result_card.py --live --max 3   # no máximo 3 cartões
    py result_card.py --live --lang pt # cartões em português (default: inglês)
    py result_card.py --results        # cartões finais dos jogos acompanhados que já acabaram
    py result_card.py --page           # gera a pasta site/ (index.html + results.html)
    py result_card.py --page --player Borges   # results.html só com jogos de um jogador
    (RESULTS_RETENTION_DAYS define quantos dias se guardam resultados; por omissão 90)

Notícias (cartões RISING / UPSET) saem sozinhas de --live e --results; precisam do news_card.py na mesma pasta.
Fotos (opcional): põe imagens em photos/<id>.jpg ou photos/<nome-do-jogador>.jpg. Só usa fotos tuas ou com licença
(e, se pedir atribuição, regista-a em photos/credits.json: {"nome-do-jogador.jpg": "Foto: Autor / CC BY 4.0"}).
Com FETCH_PHOTOS=1, tenta obter fotos de licença livre (Wikimedia) através do fetch_photos.py.
Sem foto, o cartão usa um monograma com as iniciais.
Requisitos: py -m pip install pillow requests
Nota: a chave grátis permite ~100 pedidos/dia. Cada execução com --live usa 1.
"""
import argparse
import calendar
import datetime
import shutil
import html
import json
import os
import sys
import time
import unicodedata
import re
from PIL import Image, ImageDraw, ImageFont, ImageOps

API_BASE = "https://api.livetennisapi.com/api/public/v1"
BRAND = "@beyond100.tennis"

W, H = 1080, 1350
BG_TOP, BG_BOTTOM = (14, 59, 46), (6, 28, 22)
ACCENT = (212, 232, 80)
WHITE = (245, 245, 240)
MUTED = (150, 175, 165)
LINE = (40, 90, 75)
DARK = (6, 28, 22)

FONT_BOLD = [
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_HEAD = [
    "C:/Windows/Fonts/seguibl.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_REG = [
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

I18N = {
    "pt": {
        "live": "AO VIVO", "final": "RESULTADO FINAL", "cur": "GAME ATUAL",
        "winner": "VENCEDOR", "rank": "Ranking", "set": "SET",
        "surfaces": {"clay": "Terra batida", "hard": "Piso duro", "grass": "Relva", "carpet": "Carpete"},
        "rounds": {
            "1/64-finals": "Ronda de 128", "1/32-finals": "Ronda de 64",
            "1/16-finals": "Ronda de 32", "1/8-finals": "Oitavos de final",
            "1/4-finals": "Quartos de final", "semi-finals": "Meias-finais",
            "semifinals": "Meias-finais", "final": "Final",
        },
        "formats": {"BO3": "Melhor de 3 sets", "BO5": "Melhor de 5 sets"},
    },
    "en": {
        "live": "LIVE", "final": "FINAL RESULT", "cur": "CURRENT GAME",
        "winner": "WINNER", "rank": "Rank", "set": "SET",
        "surfaces": {"clay": "Clay", "hard": "Hard court", "grass": "Grass", "carpet": "Carpet"},
        "rounds": {
            "1/64-finals": "Round of 128", "1/32-finals": "Round of 64",
            "1/16-finals": "Round of 32", "1/8-finals": "Round of 16",
            "1/4-finals": "Quarterfinals", "semi-finals": "Semifinals",
            "semifinals": "Semifinals", "final": "Final",
        },
        "formats": {"BO3": "Best of 3 sets", "BO5": "Best of 5 sets"},
    },
}
T = I18N["en"]  # idioma ativo (definido por --lang)
LANG = "en"


# ---------- utilitários de desenho ----------
def font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def gradient():
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / H
        row = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = row
    return img


def fit_font(d, text, paths, size, max_w, min_size=28):
    f = font(paths, size)
    while d.textlength(text, font=f) > max_w and size > min_size:
        size -= 2
        f = font(paths, size)
    return f


def centered(d, y, text, paths, size, fill, max_w=W - 160):
    f = fit_font(d, text, paths, size, max_w)
    w = d.textlength(text, font=f)
    d.text(((W - w) / 2, y), text, font=f, fill=fill)


def pill(d, y, text, filled):
    f = font(FONT_BOLD, 30)
    w = d.textlength(text, font=f)
    pad, h = 30, 58
    x0 = (W - w) / 2 - pad
    box = [x0, y, x0 + w + 2 * pad, y + h]
    if filled:
        d.rounded_rectangle(box, radius=h // 2, fill=ACCENT)
        d.text((x0 + pad, y + h / 2), text, font=f, fill=DARK, anchor="lm")
    else:
        d.rounded_rectangle(box, radius=h // 2, outline=MUTED, width=2)
        d.text((x0 + pad, y + h / 2), text, font=f, fill=MUTED, anchor="lm")


def pick_name(d, full, max_w, size=54):
    """Nome completo se couber; senão 'N. Apelido' (abreviado)."""
    parts = full.split()
    cands = [full]
    if len(parts) > 2:
        cands.append(f"{parts[0][0]}. {' '.join(parts[-2:])}")
    if len(parts) > 1:
        cands.append(f"{parts[0][0]}. {parts[-1]}")
    for c in cands:
        f = font(FONT_BOLD, size)
        if d.textlength(c, font=f) <= max_w:
            return c, f
    return cands[-1], fit_font(d, cands[-1], FONT_BOLD, size, max_w)


# ---------- tradução dos dados da API ----------
def round_pt(text):
    tail = (text or "").split(" - ")[-1].strip()
    return T["rounds"].get(tail.lower(), tail)


def is_live(m):
    return m.get("status") == "live"


def winner_index(m):
    s = (m.get("score") or {}).get("sets") or [0, 0]
    return 1 if s[0] > s[1] else 2 if s[1] > s[0] else 0


# ---------- cartão (identidade Beyond100: verde e creme) ----------
GREEN, DEEP, CREAM, VOLT = (14, 58, 45), (9, 40, 31), (247, 242, 230), (217, 242, 61)
SOFT, RED, TILE_EDGE = (176, 196, 183), (235, 64, 52), (88, 124, 108)
FONT_SERIF_B = [
    "C:/Windows/Fonts/georgiab.ttf", "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
]
FONT_SERIF_I = [
    "C:/Windows/Fonts/georgiai.ttf", "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
]


def _tw(d, text, f, track=0):
    return sum(d.textlength(c, font=f) for c in text) + track * (len(text) - 1)


def spaced(d, cx, cy, text, f, fill, track):
    x = cx - _tw(d, text, f, track) / 2
    for c in text:
        d.text((x, cy), c, font=f, fill=fill, anchor="lm")
        x += d.textlength(c, font=f) + track


def _wrap(d, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def pick_name2(d, full, max_w, size, paths):
    """Nome completo se couber; senão 'N. Apelido'; senão reduz a letra."""
    parts = full.split()
    cands = [full]
    if len(parts) > 2:
        cands.append(f"{parts[0][0]}. {' '.join(parts[-2:])}")
    if len(parts) > 1:
        cands.append(f"{parts[0][0]}. {parts[-1]}")
    for c in cands:
        f = font(paths, size)
        if d.textlength(c, font=f) <= max_w:
            return c, f
    return cands[-1], fit_font(d, cands[-1], paths, size, max_w)


PHOTO_DIR = os.environ.get("PHOTO_DIR", "photos")   # fotos TUAS ou com licença (ver notas no fim do ficheiro)
SURFACE_COL = {"clay": (201, 106, 60), "hard": (80, 130, 225), "grass": (120, 190, 90), "carpet": (170, 100, 150)}
COURT_LINE = (24, 76, 61)


def _slug(text):
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def find_photo(p):
    """photos/<id>.jpg ou photos/<nome-do-jogador>.jpg. Devolve (caminho, crédito) ou (None, None)."""
    def lookup():
        credits = _load_json(os.path.join(PHOTO_DIR, "credits.json"), {}) if os.path.isdir(PHOTO_DIR) else {}
        for key in (str(p.get("id")), _slug(p.get("name", ""))):
            for ext in (".jpg", ".jpeg", ".png", ".webp"):
                fp = os.path.join(PHOTO_DIR, key + ext)
                if key and os.path.exists(fp):
                    return fp, credits.get(key + ext)
        return None, None

    found = lookup()
    if found[0] is None and os.environ.get("FETCH_PHOTOS") == "1":   # só fotos com licença livre
        try:
            from fetch_photos import fetch_photo
            fetch_photo(p.get("name"), p.get("birthday"), PHOTO_DIR)
            found = lookup()
        except ImportError:
            pass
    return found


PHOTO_REPEAT_DAYS = float(os.environ.get("PHOTO_REPEAT_DAYS") or "10")   # foto usada há menos de N dias: o post não sai (exceto finais)
PHOTO_REPEAT_3D = float(os.environ.get("PHOTO_REPEAT_3D") or "3")      # a única foto do vencedor saiu há menos de 3 dias: -3
PHOTO_REPEAT_10D = float(os.environ.get("PHOTO_REPEAT_10D") or "1.5")   # há menos de 10 dias: -1,5
POST_PHOTO_REPEAT = False     # última escolha de find_post_photo repetiu uma foto usada há pouco (sem alternativa)


_RD = {"final": "F", "finals": "F", "semi-finals": "SF", "semifinals": "SF", "quarter-finals": "QF", "quarterfinals": "QF",
       "1/8-finals": "R16", "round of 16": "R16", "1/16-finals": "R32", "round of 32": "R32", "1/32-finals": "R64", "round of 64": "R64",
       "1/64-finals": "R128", "round of 128": "R128"}


def _champion_card(m, pw, pl, wd, sets, tag, out_path):
    """Cartão de campeão: o caminho até ao título vem dos nossos resultados do mesmo torneio (últimos 12 dias)."""
    from photo_cards import render_champion
    name = pw.get("name") or ""
    base = webapp.base_tournament(m.get("tournament", ""))
    day = (m.get("updated_at") or time.strftime("%Y-%m-%d"))[:10]
    road, lost_sets = [], 0
    for r in sorted(load_results(), key=lambda r: r.get("date", "")):
        if webapp.base_tournament(r.get("tournament", "")) != base or str(r.get("id")) == str(m.get("id")):
            continue
        try:
            if abs((datetime.date.fromisoformat(day) - datetime.date.fromisoformat(r.get("date", "")[:10])).days) > 12:
                continue
        except ValueError:
            continue
        i = 1 if r["p1"]["name"] == name else 2 if r["p2"]["name"] == name else 0
        if not i or r.get("winner") != i:
            continue
        o = r["p%d" % (3 - i)]
        rd = "Q" if r.get("q") else _RD.get((r.get("round") or "").strip().lower(), "")
        road.append((rd, o.get("name") or "", o.get("rank")))
        g = r.get("games") or [[], []]
        lost_sets += sum(1 for a, b in zip(g[i - 1], g[2 - i]) if a < b)
    road.append(("F", pl.get("name") or "", pl.get("ranking")))
    lost_sets += sum(1 for a, b in sets if a < b)
    # só a parte do caminho sem buracos até à final (se não acompanhámos uma ronda, as anteriores ficam de fora) e sem contagem de
    # vitórias/sets: não sabemos se vimos o quadro todo, e um número errado é pior do que nenhum (9/11/2026)
    order = ["R128", "R64", "R32", "R16", "QF", "SF", "F"]
    tail = []
    for x in reversed(road):
        if tail and x[0] in order and tail[-1][0] in order and order.index(x[0]) != order.index(tail[-1][0]) - 1:
            break
        if x[0] not in order:
            break
        tail.append(x)
    road = list(reversed(tail))
    wins = len(road)
    note = ""
    try:
        date = datetime.date.fromisoformat(day).strftime("%-d %b %Y")
    except ValueError:
        date = ""
    d = {"name": name, "rank": pw.get("ranking"), "photo": wd.get("photo"), "credit": wd.get("credit"),
         "tournament": re.sub(r"^(ATP|WTA)\s+", "", base), "level": (tag or "").upper(), "date": date,
         "final": {"opp": pl.get("name") or "", "opp_rank": pl.get("ranking"), "sets": sets}, "road": road, "note": note}
    print(f"Jogo {m.get('id')}: campeão, cartão próprio ({wins} vitórias no caminho).")
    if _env("RESULT_STYLE", "C") == "C":                        # 9/11/2026: campeão = modelo B (cartaz)
        import modern_cards
        return modern_cards.card_b({"sport": "tennis", "kicker": "CHAMPION", "level": d["level"], "tournament": d["tournament"],
                                    "round": "Final", "date": d["date"],
                                    "winners": [{"name": name, "rank": pw.get("ranking"), "country": (pw.get("country") or "").upper()}],
                                    "losers": [{"name": pl.get("name") or "", "rank": pl.get("ranking")}], "sets": sets,
                                    "photo": d["photo"], "credit": d["credit"], "road": road}, out_path)
    return render_champion(d, out_path)


_KNOWN = None


def _known_names():
    """Nomes de todos os jogadores dos nossos resultados (para reconhecer fotos com outro jogador no nome do ficheiro)."""
    global _KNOWN
    if _KNOWN is None:
        try:
            _KNOWN = {x[k]["name"] for x in load_results() for k in ("p1", "p2") if x.get(k, {}).get("name")}
        except Exception:
            _KNOWN = set()
    return _KNOWN


def _same_image(page):
    """A mesma foto no Commons com e sem corte ('X_01.jpg' e 'X_01_(cropped).jpg') conta como uma só (9/11/2026)."""
    import urllib.parse
    f = urllib.parse.unquote((page or "").rsplit("/", 1)[-1]).lower()
    return re.sub(r"[_ ]\((edited[_ ]and[_ ])?cropped\)", "", re.sub(r"\.(jpe?g|png|webp)$", "", f))


def _few_photos(key):
    """Menos de 2 fotos diferentes deste jogador: procura fotos novas já (no máximo 1 vez por semana), em vez de esperar um mês."""
    srcs = _load_json(os.path.join(PHOTO_DIR, "sources.json"), {})
    imgs = {_same_image(v.get("commons_page")) for k, v in srcs.items() if isinstance(v, dict)
            and (k == key + ".jpg" or (k.startswith("alt/" + key + "-") and k[len(key) + 5:-4].isdigit()))}
    if len(imgs) >= 2:
        return False
    st = _load_json(os.path.join(PHOTO_DIR, "gallery.json"), {})
    return time.time() - st.get(key, 0) > 7 * 86400


def find_post_photo(p, dry=False):
    """Foto para um POST (não para o site): alterna entre a foto principal e as fotos extra recentes do jogador (photos/alt/),
    escolhendo a que foi usada há mais tempo. A principal só fica de fora se for antiga e houver alternativas recentes.
    Regista o uso em photos/used.json. Devolve (caminho, crédito) como find_photo."""
    main = find_photo(p)
    name = p.get("name") or ""
    if not main[0] or not name:
        return (main[0], main[1], 0) if dry else main
    import fetch_photos
    key = fetch_photos.slug(name)
    if os.environ.get("FETCH_PHOTOS") == "1":
        try:
            fetch_photos.gallery(name, p.get("birthday"), PHOTO_DIR, force=_few_photos(key))
        except Exception as e:
            print("Galeria de fotos:", name, type(e).__name__)
    credits = _load_json(os.path.join(PHOTO_DIR, "credits.json"), {})
    sources = _load_json(os.path.join(PHOTO_DIR, "sources.json"), {})
    cut = fetch_photos.recent_cutoff()
    opts = []
    adir = os.path.join(PHOTO_DIR, "alt")
    if os.path.isdir(adir):
        for fn in sorted(os.listdir(adir)):
            rel = "alt/" + fn
            if fn.startswith(key + "-") and fn[len(key) + 1:-4].isdigit() and fn.endswith(".jpg") and credits.get(rel):
                _t = (sources.get(rel) or {}).get("taken") or ""
                _mt = fetch_photos.main_taken(key, PHOTO_DIR)
                if _t >= cut or (_mt and _t >= _mt):          # recentes, ou pelo menos tão recentes como a principal
                    opts.append((os.path.join(adir, fn), credits[rel], rel, (sources.get(rel) or {}).get("taken") or ""))
    mrel = os.path.relpath(main[0], PHOTO_DIR).replace(os.sep, "/")
    mtaken = (sources.get(mrel) or {}).get("taken") or ""
    if not opts or not mtaken or mtaken >= cut:
        opts.insert(0, (main[0], main[1], mrel, mtaken))
    on = [o for o in opts if not fetch_photos.off_court((sources.get(o[2]) or {}).get("commons_page"))]
    if on:                                                         # fotos de gala/prémios só se não houver nenhuma em court
        opts = on
    # 9/11/2026: só fotos nítidas, com tamanho e de uma pessoa só (sem cerimónias nem "X vs Y"); se nenhuma servir, o post sai sem foto
    import photo_quality
    good = []
    for o in opts:
        why = []
        if photo_quality.card_ok(o[0], name, (sources.get(o[2]) or {}).get("commons_page"), _known_names(), why):
            good.append(o)
        else:
            print(f"Foto de {name} ({o[2]}) não serve para post: {why[0]}.")
    if not good:
        return (None, None, 0) if dry else (None, None)
    opts = good
    seen_img, uniq = set(), []
    for o in opts:                                                 # a mesma foto com e sem corte só conta uma vez
        k_ = _same_image((sources.get(o[2]) or {}).get("commons_page")) or o[2]
        if k_ not in seen_img:
            seen_img.add(k_)
            uniq.append(o)
    opts = uniq
    upath = os.path.join(PHOTO_DIR, "used.json")
    used = _load_json(upath, {})
    for o in opts:                                                 # uso de uma versão conta para a outra
        k_ = _same_image((sources.get(o[2]) or {}).get("commons_page"))
        for rel_, v_ in sources.items():
            if rel_ != o[2] and isinstance(v_, dict) and k_ and _same_image(v_.get("commons_page")) == k_:
                used[o[2]] = max(used.get(o[2], 0), used.get(rel_, 0))
    opts.sort(key=lambda o: o[3] or "", reverse=True)              # empate: a mais recente primeiro
    pick = min(opts, key=lambda o: used.get(o[2], 0))              # a usada há mais tempo (ou nunca usada)
    if dry:                                                        # só para saber há quanto tempo saiu (não regista nada)
        return pick[0], pick[1], used.get(pick[2], 0)
    global POST_PHOTO_REPEAT
    POST_PHOTO_REPEAT = time.time() - used.get(pick[2], 0) < 10 * 86400   # a mesma foto saiu há menos de 10 dias
    used[pick[2]] = time.time()
    try:
        with open(upath, "w", encoding="utf-8") as f:
            json.dump(used, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
    return pick[0], pick[1]


def court_watermark(d):
    """Campo visto de cima, quase invisível, como textura de fundo."""
    x0, x1, y0, y1 = 190, 890, 150, 1210
    sid, sv, mid = 70, 255, (150 + 1210) // 2
    d.rectangle([x0, y0, x1, y1], outline=COURT_LINE, width=4)
    for x in (x0 + sid, x1 - sid):
        d.line([(x, y0), (x, y1)], fill=COURT_LINE, width=4)
    d.line([(x0 - 20, mid), (x1 + 20, mid)], fill=COURT_LINE, width=6)
    for y in (mid - sv, mid + sv):
        d.line([(x0 + sid, y), (x1 - sid, y)], fill=COURT_LINE, width=4)
    d.line([(540, mid - sv), (540, mid + sv)], fill=COURT_LINE, width=4)


def avatar(img, cx, cy, r, p, ring, credits_out):
    """Foto (se existir em photos/) ou monograma com as iniciais."""
    d = ImageDraw.Draw(img)
    fp, credit = find_photo(p)
    if fp:
        ph = ImageOps.fit(Image.open(fp).convert("RGB"), (2 * r, 2 * r), centering=(0.5, 0.3))
        mask = Image.new("L", (2 * r, 2 * r), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
        img.paste(ph, (cx - r, cy - r), mask)
        if credit:
            credits_out.append(credit)
    else:
        parts = (p.get("name") or "?").split()
        ini = (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=DEEP)
        d.text((cx, cy), ini, font=font(FONT_SERIF_B, int(r * 0.85)), fill=CREAM, anchor="mm")
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring, width=5)


def render_card(m, out_path):
    """Texto importante fica dentro de x=120..960 (a grelha do Instagram corta as margens)."""
    img = Image.new("RGB", (W, H), GREEN)
    d = ImageDraw.Draw(img)
    d.rectangle([36, 36, W - 37, H - 37], outline=CREAM, width=3)
    d.rectangle([52, 52, W - 53, H - 53], outline=CREAM, width=1)
    court_watermark(d)
    credits_used = []
    live = is_live(m)
    score = m.get("score") or {}
    g1, g2 = (score.get("games") or [[], []])[:2]
    n = max(len(g1), len(g2), 1)
    sets = [(g1[i] if i < len(g1) else 0, g2[i] if i < len(g2) else 0) for i in range(n)]
    win = 0 if live else winner_index(m)

    # marca + estado
    spaced(d, W / 2, 125, "BEYOND100", font(FONT_SERIF_B, 40), CREAM, 10)
    label = T["live"] if live else T["final"]
    bf, track = font(FONT_BOLD, 30), 6
    tw = _tw(d, label, bf, track)
    bw = tw + (130 if live else 90)
    x0, y0 = W / 2 - bw / 2, 175
    if live:
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + 62], radius=31, fill=VOLT)
        d.ellipse([x0 + 34, y0 + 21, x0 + 54, y0 + 41], fill=RED)
        spaced(d, x0 + 70 + tw / 2, y0 + 31, label, bf, GREEN, track)
    else:
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + 62], radius=31, outline=CREAM, width=3)
        spaced(d, W / 2, y0 + 31, label, bf, CREAM, track)

    # torneio (até 2 linhas) e subtítulo
    tf = font(FONT_SERIF_B, 62)
    lines = _wrap(d, m.get("tournament", ""), tf, 800)
    if len(lines) > 2:
        tf = font(FONT_SERIF_B, 50)
        lines = _wrap(d, m.get("tournament", ""), tf, 800)[:2]
    y = 330 if len(lines) == 1 else 305
    for ln in lines:
        d.text((W / 2, y), ln, font=tf, fill=CREAM, anchor="mm")
        y += 74
    sub = " · ".join(x for x in [round_pt(m.get("round")), T["surfaces"].get(m.get("surface"), "")] if x)
    d.text((W / 2, y + 18), sub, font=fit_font(d, sub, FONT_SERIF_I, 38, 800), fill=SOFT, anchor="mm")

    # painel dos jogadores
    d.rounded_rectangle([120, 520, 960, 930], radius=38, fill=DEEP, outline=CREAM, width=2)
    d.line([(160, 725), (920, 725)], fill=TILE_EDGE, width=2)
    ts, gap = (92, 12) if n <= 3 else (72, 10)
    tiles_left = 920 - (n * ts + (n - 1) * gap)
    name_x = 262
    name_max = tiles_left - name_x - 24
    for i in range(2):
        p = m["players"]["p%d" % (i + 1)]
        yc = 622 + i * 206
        dim = win and win != i + 1
        name, nf = pick_name2(d, p.get("name", "?"), name_max, 50, FONT_SERIF_B)
        d.text((name_x, yc - 22), name, font=nf, fill=SOFT if dim else CREAM, anchor="lm")
        info = (p.get("country") or "").upper()
        if p.get("ranking"):
            info += f"  ·  {T['rank']} {p['ranking']}"
        inf = font(FONT_REG, 28)
        d.text((name_x, yc + 36), info, font=inf, fill=SOFT, anchor="lm")
        mv = p.get("ranking_movement")
        if p.get("ranking") and mv in ("up", "down"):        # seta a partir dos dados da API
            ax, ay = name_x + d.textlength(info, font=inf) + 22, yc + 36
            tri = [(ax - 9, ay + 7), (ax + 9, ay + 7), (ax, ay - 9)] if mv == "up" else [(ax - 9, ay - 7), (ax + 9, ay - 7), (ax, ay + 9)]
            d.polygon(tri, fill=VOLT if mv == "up" else RED)
        ring = VOLT if win == i + 1 else SURFACE_COL.get(m.get("surface"), SOFT)
        avatar(img, 190, yc, 52, p, ring, credits_used)
        if live and score.get("server") == i + 1:
            d.ellipse([222, yc - 58, 244, yc - 36], fill=VOLT, outline=GREEN, width=3)
        for j, st in enumerate(sets):
            mine, other = st[i], st[1 - i]
            bx = tiles_left + j * (ts + gap)
            box = [bx, yc - ts / 2, bx + ts, yc + ts / 2]
            if mine > other:
                d.rounded_rectangle(box, radius=22, fill=VOLT)
                col = GREEN
            else:
                d.rounded_rectangle(box, radius=22, outline=TILE_EDGE, width=2)
                col = SOFT
            d.text((bx + ts / 2, yc), str(mine), font=font(FONT_SERIF_B, int(ts * 0.55)), fill=col, anchor="mm")

    # bloco inferior
    pts = score.get("points") or []
    if live and len(pts) == 2:
        lab2, big = T["cur"], f"{pts[0]} – {pts[1]}"
    elif live:                                   # fonte sem pontos: mostra os jogos do set em curso
        lab2, big = f"{T['set']} {n}", f"{sets[-1][0]} – {sets[-1][1]}"
    else:
        lab2, big = T["winner"], None
    spaced(d, W / 2, 1000, lab2.upper(), font(FONT_BOLD, 26), SOFT, 6)
    if live:
        d.text((W / 2, 1085), big, font=font(FONT_SERIF_B, 112), fill=VOLT, anchor="mm")
    elif win:
        wn = m["players"]["p%d" % win].get("name", "")
        d.text((W / 2, 1085), wn, font=fit_font(d, wn, FONT_SERIF_I, 84, 800), fill=VOLT, anchor="mm")
    extra = " · ".join(x for x in [m.get("court"), T["formats"].get(m.get("format"), "")] if x)
    if extra:
        d.text((W / 2, 1160), extra, font=fit_font(d, extra, FONT_REG, 30, 800), fill=SOFT, anchor="mm")

    if credits_used:
        ct = " · ".join(dict.fromkeys(credits_used))
        d.text((W / 2, 1200), ct, font=fit_font(d, ct, FONT_REG, 22, 760), fill=SOFT, anchor="mm")

    # rodapé
    d.ellipse([W / 2 - 9, 1228, W / 2 + 9, 1246], fill=VOLT)
    d.text((W / 2, 1280), BRAND, font=font(FONT_BOLD, 34), fill=CREAM, anchor="mm")

    img.save(out_path, quality=95)
    return out_path


# ---------- dados ----------
def _headers():
    key = os.environ.get("LIVETENNIS_KEY")
    if not key:
        sys.exit('Falta a chave. No PowerShell: $env:LIVETENNIS_KEY="a_tua_chave"')
    return {"X-API-Key": key}


# ---------- quota diária da API (plano gratuito: 100 pedidos/dia) ----------
API_CALLS_FILE = "api_calls.json"
API_DAILY_LIMIT = int(os.environ.get("API_DAILY_LIMIT") or "100")
QUOTA_RESERVE = int(os.environ.get("QUOTA_RESERVE") or "20")
LIVE_RESERVE = int(os.environ.get("LIVE_RESERVE") or "6")
QUOTA_RESET_UTC = int(os.environ.get("QUOTA_RESET_UTC") or "22")   # hora (UTC) a que a quota da Live Tennis API renova (visto no /usage: 22h)


def api_day(ts=None):
    """O 'dia' da quota da API: começa às QUOTA_RESET_UTC h (UTC), não à meia-noite."""
    t = time.time() if ts is None else ts
    return time.strftime("%Y-%m-%d", time.gmtime(t + (24 - QUOTA_RESET_UTC) % 24 * 3600))       # últimos pedidos do dia: só para a lista de jogos ao vivo     # pedidos guardados para o essencial (resultados)


def _usage_used():
    """Pedidos já usados hoje segundo o /usage da própria API (usage.json), se for recente e legível."""
    u = _load_json("usage.json", {})
    if time.time() - u.get("ts", 0) > 7 * 3600 or api_day(u.get("ts", 0)) != api_day():
        return None                                              # leitura de antes da renovação da quota já não conta
    f = u.get("fields") or {}
    if isinstance(f.get("today.calls"), (int, float)):            # formato real do /usage: today.calls, limits.per_day, today.remaining_day
        return int(f["today.calls"])
    pick = lambda pat: next((v for k, v in f.items() if re.search(pat, k, re.I) and isinstance(v, (int, float))), None)
    used, lim, rem = pick(r"used|consumed|calls|count"), pick(r"per_?day"), pick(r"remaining")
    if used is None and lim is not None and rem is not None:
        used = lim - rem
    return int(used) if isinstance(used, (int, float)) else None


def quota_used():
    d = _load_json(API_CALLS_FILE, {})
    today = api_day()
    n = d.get("n", 0) if d.get("day") == today else 0
    u = _usage_used()
    return max(n, u) if u is not None else n


class QuotaSkip(Exception):
    pass


def api_get(path, params=None, kind="core"):
    """Pedido à API com contador diário. 'extra' (ordem de jogo, fichas, próximos jogos) só corre se ficar
    uma reserva de QUOTA_RESERVE pedidos para o essencial ('core': jogos ao vivo e confirmação de resultados)."""
    import requests
    used = quota_used()
    # prioridades: 1) lista de jogos ao vivo (sem ela, um jogo que comece e acabe entre leituras nunca é seguido = post perdido);
    # 2) confirmar resultados (pode esperar: os jogos seguidos ficam na fila); 3) extras (ordem de jogo, fichas, próximos jogos)
    if kind == "extra" and used + QUOTA_RESERVE >= API_DAILY_LIMIT:
        raise QuotaSkip(f"quota: {used}/{API_DAILY_LIMIT} usados, extras em pausa (reserva {QUOTA_RESERVE})")
    if kind == "core" and used >= API_DAILY_LIMIT - LIVE_RESERVE:
        raise QuotaSkip(f"quota: {used}/{API_DAILY_LIMIT} usados, confirmações em pausa (guardados {LIVE_RESERVE} para os jogos ao vivo)")
    if used >= API_DAILY_LIMIT - 1:
        raise QuotaSkip(f"quota: {used}/{API_DAILY_LIMIT} usados, a parar")
    today = api_day()
    d = _load_json(API_CALLS_FILE, {})
    if d.get("day") != today:
        d = {"day": today, "n": 0, "by": {}}
    d["n"] = d.get("n", 0) + 1
    key = path.strip("/").split("/")[0] + ("/id" if path.count("/") > 1 else "")
    d.setdefault("by", {})[key] = d["by"].get(key, 0) + 1
    with open(API_CALLS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f)
    return requests.get(f"{API_BASE}{path}", params=params, headers=_headers(), timeout=20)


def fetch_live():
    r = api_get("/matches", {"status": "live"}, kind="live")
    r.raise_for_status()
    return r.json().get("data", [])


def fetch_match(match_id):
    """Um jogo por id (inclui jogos terminados; grátis no plano FREE)."""
    import requests
    try:
        r = api_get(f"/matches/{match_id}")
    except QuotaSkip as e:
        raise requests.exceptions.RequestException(str(e))
    r.raise_for_status()
    return r.json()


# ---------- próximos jogos (para mostrar "a seguir" na página de cada torneio) ----------
UPCOMING_FILE = "upcoming.json"
UPCOMING_EVERY_H = float(os.environ.get("UPCOMING_EVERY_H") or "12")


def _live_p(p):
    itf = p.get("itf_ranking") or {}
    return {"name": p["name"], "country": p.get("country"), "rank": p.get("ranking"), "bd": p.get("birthday"), "pid": p.get("id"),
            "hand": p.get("hand"), "bh": p.get("backhand"), "itf": itf.get("rank") if isinstance(itf, dict) else None}


def save_live(matches):
    """Jogos a decorrer agora (Tour/Challenger, singulares), para a faixa "Playing now" do site."""
    import webapp
    rows = []
    for m in matches:
        if m.get("is_doubles") or is_qual(m) or m.get("tour") not in ("atp", "wta", "challenger"):
            continue
        pl = m.get("players") or {}
        a_, b_ = pl.get("p1") or {}, pl.get("p2") or {}
        g = (m.get("score") or {}).get("games") or [[], []]
        if not a_.get("name") or not b_.get("name") or not g[0]:
            continue
        tp, _, rr = (m.get("round") or "").rpartition(" - ")
        _, _, _, tag = webapp.classify(webapp.api_view(m))
        rows.append({"id": m.get("id"), "tournament": re.sub(r"^(ATP|WTA)\s+", "", tp), "round": rr, "tag": tag.upper(),
                     "p1": _live_p(a_), "p2": _live_p(b_),
                     "games": [list(g[0]), list(g[1])],
                     "sets": (m.get("score") or {}).get("sets"), "points": (m.get("score") or {}).get("points"),
                     "server": (m.get("score") or {}).get("server"), "surface": m.get("surface"), "court": m.get("court"),
                     "format": m.get("format"), "gender": m.get("gender"), "indoor": m.get("indoor"), "live_at": m.get("live_at"),
                     "tb": (m.get("score") or {}).get("is_tiebreak"), "tier": m.get("tier")})
    with open(extras.LIVE_FILE, "w", encoding="utf-8") as f:
        json.dump({"ts": time.time(), "matches": rows[:12]}, f, ensure_ascii=False)
    print(f"A decorrer agora: {len(rows)} jogos guardados.")


def refresh_upcoming():
    import requests
    data = _load_json(UPCOMING_FILE, {})
    if time.time() - data.get("ts", 0) < UPCOMING_EVERY_H * 3600:
        print("Próximos jogos: atualizados há pouco, salto.")
        return
    try:
        r = api_get("/matches", {"status": "upcoming"}, kind="extra")
        r.raise_for_status()
        rows = r.json().get("data", [])
    except Exception as e:
        print(f"Próximos jogos: não consegui obter ({e}).")
        return
    out = []
    for m in rows:
        if m.get("is_doubles") or is_qual(m) or m.get("tour") not in ("atp", "wta", "challenger"):
            continue
        pl = m.get("players") or {}
        a_, b_ = pl.get("p1") or {}, pl.get("p2") or {}
        if not a_.get("name") or not b_.get("name"):
            continue                                   # adversário ainda por definir
        rd = m.get("round") or ""
        tp, _, rr = rd.rpartition(" - ")
        out.append({"id": m.get("id"), "tp": tp, "round": rr or rd, "t": m.get("scheduled_time"),
                    "tour": m.get("tour"), "gender": m.get("gender"),
                    "p1": {"name": a_["name"], "country": a_.get("country"), "rank": a_.get("ranking")},
                    "p2": {"name": b_["name"], "country": b_.get("country"), "rank": b_.get("ranking")}})
    with open(UPCOMING_FILE, "w", encoding="utf-8") as f:
        json.dump({"ts": time.time(), "matches": out[:200]}, f, ensure_ascii=False, indent=1)
    print(f"Próximos jogos: {len(out)} guardados.")


# ---------- ordem de jogo (endpoint /fixtures, gratuito): horas de início de hoje/amanhã ----------
FIXTURES_FILE = "fixtures.json"
FIXTURES_EVERY_H = float(os.environ.get("FIXTURES_EVERY_H") or "6")
FIXTURES_PAGES = int(os.environ.get("FIXTURES_PAGES") or "2")


def _full_names():
    """'m. berrettini' -> 'Matteo Berrettini', a partir dos nomes que já conhecemos (o /fixtures abrevia o nome próprio)."""
    names = [v.get("name") for v in _load_json(RANKS_FILE, {}).values()]
    names += [p_["name"] for r in load_results() for p_ in (r["p1"], r["p2"])]
    for m in _load_json(extras.LIVE_FILE, {}).get("matches", []) + _load_json(UPCOMING_FILE, {}).get("matches", []):
        names += [(m.get("p1") or {}).get("name"), (m.get("p2") or {}).get("name")]
    idx = {}
    for n in names:
        if not n or "/" in n:
            continue
        parts = n.split()
        for k in range(1, len(parts)):                 # apelidos compostos: "J. Romero Gormaz"
            key = (parts[0][0].lower(), webapp.slugify(" ".join(parts[k:])))
            idx.setdefault(key, set()).add(n)
    return {k: next(iter(v)) for k, v in idx.items() if len(v) == 1}


def _expand(short, idx):
    m = re.match(r"^([A-Za-zÀ-ÿ])[a-zà-ÿ]*\.?\s+(.+)$", (short or "").strip())
    if not m:
        return short
    return idx.get((m.group(1).lower(), webapp.slugify(m.group(2))), short)


def _tour_norm(t):
    """O /fixtures usa 'challenger_women' (WTA 125) e 'itf_men'/'itf_women'; o resto do código usa atp/wta/challenger/itf."""
    t = (t or "").lower()
    return "challenger" if t.startswith("challenger") else "itf" if t.startswith("itf") else t


def refresh_fixtures():
    import requests
    data = _load_json(FIXTURES_FILE, {})
    if time.time() - data.get("ts", 0) < FIXTURES_EVERY_H * 3600:
        print("Ordem de jogo: atualizada há pouco, salto.")
        return
    rows = []
    for page in range(FIXTURES_PAGES):
        try:
            r = api_get("/fixtures", {"limit": 50, "offset": page * 50}, kind="extra")
            r.raise_for_status()
            j = r.json()
        except Exception as e:
            print(f"Ordem de jogo: não consegui obter a página {page + 1} ({e}).")
            break
        rows += j.get("data", [])
        if not (j.get("meta") or {}).get("has_more"):
            break
    if not rows:
        return
    idx = _full_names()
    ranks = {v.get("name"): v.get("rank") for v in _load_json(RANKS_FILE, {}).values()}
    out = []
    for f_ in rows:
        a_, b_ = f_.get("player1_name") or "", f_.get("player2_name") or ""
        if f_.get("is_qualifying") or not a_ or not b_ or "/" in a_ + b_:
            continue
        rd = f_.get("round") or ""
        tp, _, rr = rd.rpartition(" - ")
        na, nb = _expand(a_, idx), _expand(b_, idx)
        out.append({"id": f_.get("match_id"), "tp": re.sub(r"^(ATP|WTA)\s+", "", tp) or f_.get("tournament") or "",
                    "round": rr or rd, "rc": f_.get("round_code"), "t": f_.get("start_time"), "day": f_.get("event_date"),
                    "status": f_.get("status"), "tour": _tour_norm(f_.get("tour")), "gender": f_.get("gender"), "surface": f_.get("surface"),
                    "p1": {"name": na, "rank": ranks.get(na)}, "p2": {"name": nb, "rank": ranks.get(nb)}})
    with open(FIXTURES_FILE, "w", encoding="utf-8") as f:
        json.dump({"ts": time.time(), "matches": out}, f, ensure_ascii=False, indent=1)
    print(f"Ordem de jogo: {len(out)} jogos guardados ({len(rows)} recebidos).")
    # junta as horas aos próximos jogos (quadros, 'Next match'): o /fixtures é mais frequente que o /matches?status=upcoming
    up = _load_json(UPCOMING_FILE, {"ts": 0, "matches": []})
    have = {str(u.get("id")): u for u in up.get("matches", [])}
    for x in out:
        if str(x.get("status") or "").lower() in ("live", "finished", "completed", "ended", "cancelled", "canceled", "retired", "walkover", "postponed") \
                or x.get("tour") not in ("atp", "wta", "challenger"):
            continue
        u = have.get(str(x["id"]))
        if u:
            u["t"] = x.get("t") or u.get("t")
        elif x["p1"]["name"] and x["p2"]["name"]:
            up.setdefault("matches", []).append({"id": x["id"], "tp": x["tp"], "round": x["round"], "t": x["t"], "tour": x["tour"],
                                                 "gender": x["gender"], "p1": dict(x["p1"]), "p2": dict(x["p2"])})
    with open(UPCOMING_FILE, "w", encoding="utf-8") as f:
        json.dump(up, f, ensure_ascii=False, indent=1)


# ---------- ficha dos jogadores (/players/{id}, gratuito mas 1 pedido por jogador): época por piso, títulos, altura ----------
PSTATS_FILE = "player_stats.json"
PSTATS_PER_RUN = int(os.environ.get("PLAYER_STATS_PER_RUN") or "1")
PSTATS_PER_DAY = int(os.environ.get("PLAYER_STATS_PER_DAY") or "4")
PSTATS_MAX_AGE_D = float(os.environ.get("PLAYER_STATS_MAX_AGE_D") or "7")


def refresh_player_stats():
    """Atualiza a ficha de poucos jogadores por execução: primeiro os que estão a jogar agora (Tour, depois Challenger)."""
    import requests
    if PSTATS_PER_RUN <= 0:
        return
    data = _load_json(PSTATS_FILE, {})
    now = time.time()
    want = []
    lv = {"CHA": 0, "ATP": 1, "WTA": 1}            # ATP/WTA já têm perfil grátis pelo ESPN: os pedidos pagos vão primeiro para o Challenger
    for m in sorted(_load_json(extras.LIVE_FILE, {}).get("matches", []), key=lambda m: lv.get((m.get("tag") or "")[:3], 2)):
        for k in ("p1", "p2"):
            pid = (m.get(k) or {}).get("pid")
            if pid and now - (data.get(str(pid)) or {}).get("ts", 0) > PSTATS_MAX_AGE_D * 86400 and pid not in want:
                want.append(pid)
    day0 = time.mktime(time.strptime(time.strftime("%Y-%m-%d", time.gmtime()), "%Y-%m-%d")) - time.timezone
    done_today = sum(1 for v in data.values() if v.get("ts", 0) >= day0)
    for pid in want[:max(0, min(PSTATS_PER_RUN, PSTATS_PER_DAY - done_today))]:
        try:
            r = api_get(f"/players/{pid}", kind="extra")
            r.raise_for_status()
            j = r.json()
        except Exception as e:
            print(f"Ficha do jogador {pid}: falhou ({e}).")
            continue
        seasons = []
        for x in ((j.get("stats") or {}).get("season") or []):
            if x.get("type") != "singles":
                continue
            num = lambda k: int(x[k]) if str(x.get(k) or "").isdigit() else None
            seasons.append({"y": x.get("season"), "w": num("matches_won"), "l": num("matches_lost"), "t": num("titles"),
                            "rk": num("rank"), "s": {sf: [num(f"{sf}_won"), num(f"{sf}_lost")] for sf in ("hard", "clay", "grass")}})
        data[str(pid)] = {"ts": now, "name": j.get("name"), "h": j.get("height_cm"), "hand": j.get("hand"), "bh": j.get("backhand"),
                          "seasons": sorted(seasons, key=lambda x: str(x.get("y")), reverse=True)[:4]}
        print(f"Ficha do jogador {j.get('name')}: {len(seasons)} épocas.")
    with open(PSTATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


# ---------- acompanhamento mínimo (só ids, para respeitar os termos de armazenamento) ----------
STATE_FILE = "tracked.json"
MIN_AGE_BEFORE_CHECK_S = int(os.environ.get("MIN_AGE_MIN") or "45") * 60   # execuções manuais podem baixar isto
MAX_TRACKED = int(os.environ.get("MAX_TRACKED") or "12")
TRACK_MAX_PRIO = int(os.environ.get("TRACK_MAX_PRIO") or "2")             # 1 = só Tour+Challenger gastam quota; 2 = também ITF
PRIO_FILE = "tracked_prio.json"                                          # id -> prioridade (0 Tour, 1 Challenger, 2 ITF, 3 resto)
TRACK_MAX_AGE_H = 48  # ids mais antigos são apagados


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def load_prio():
    try:
        with open(PRIO_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_prio(prio):
    with open(PRIO_FILE, "w", encoding="utf-8") as f:
        json.dump(prio, f, indent=2)


META_FILE = "tracked_meta.json"     # retrato mínimo dos jogos acompanhados (só enquanto estão na fila), para confirmar pelo ESPN
META_KEYS = ("id", "tournament", "round", "round_code", "surface", "tour", "gender", "is_qualifying", "is_doubles", "format",
             "court", "indoor", "tier")
ESPN_ON = os.environ.get("ESPN_ON", "1") != "0"


def load_meta():
    return _load_json(META_FILE, {})


def save_meta(meta, keep):
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in meta.items() if k in keep}, f, ensure_ascii=False)


def snap(m):
    out = {k: m.get(k) for k in META_KEYS if m.get(k) is not None}
    out["players"] = {k: {f: ((m.get("players") or {}).get(k) or {}).get(f) for f in ("name", "country", "ranking", "birthday", "id")}
                      for k in ("p1", "p2")}
    return out


def espn_candidate(meta):
    """Jogos que o ESPN cobre: ATP e WTA (incluindo WTA 125). Challenger masculino e ITF ficam com a API."""
    t = (meta or {}).get("tour")
    return t in ("atp", "wta") or (t == "challenger" and meta.get("gender") == "women")


def _count_free(n=1):
    d = _load_json(API_CALLS_FILE, {})
    if d.get("day") != api_day():
        d = {"day": api_day(), "n": 0, "by": {}}
    d["espn"] = d.get("espn", 0) + n
    with open(API_CALLS_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f)


def track(ids):
    state = load_state()
    now = time.time()
    for i in ids:
        state.setdefault(str(i), now)
    save_state(state)


# ---------- resultados guardados (só os campos que se mostram ao público) ----------
RESULTS_FILE = "results.json"
RETENTION_DAYS = int(os.environ.get("RESULTS_RETENTION_DAYS", "90"))


def load_results():
    try:
        with open(RESULTS_FILE, encoding="utf-8") as f:
            return _heal(json.load(f))
    except (OSError, ValueError):
        return []


def prune(results):
    cutoff = time.strftime("%Y-%m-%d", time.gmtime(time.time() - RETENTION_DAYS * 86400))
    return [r for r in results if r.get("date", "") >= cutoff]


ARCHIVE_FILE = "archive.json"


def _archive(results):
    """Histórico permanente (nunca apagado). O site só mostra os últimos RETENTION_DAYS dias, mas tudo fica aqui para análises."""
    arc = {}
    try:
        with open(ARCHIVE_FILE, encoding="utf-8") as f:
            arc = {str(r.get("id")): r for r in json.load(f)}
    except (OSError, ValueError):
        pass
    for r in results:
        arc[str(r.get("id"))] = r
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(arc.values(), key=lambda r: r.get("date", "")), f, ensure_ascii=False, separators=(",", ":"))


def save_results(results):
    if os.environ.get("KEEP_ARCHIVE") != "0":      # ligado por defeito (KEEP_ARCHIVE=0 desliga). Mantém o repositório PRIVADO: não é para publicar
        _archive(results)
    results = sorted(prune(results), key=lambda r: r.get("date", ""), reverse=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def slim(m):
    """Reduz um jogo da API aos campos públicos (nunca guardamos a resposta completa)."""
    sc = m.get("score") or {}
    games = sc.get("games") or [[], []]
    pl = m.get("players") or {}
    return {
        "id": m.get("id"),
        "date": (m.get("updated_at") or "")[:10] or time.strftime("%Y-%m-%d", time.gmtime()),
        "tournament": m.get("tournament", ""),
        "round": ("Qualifying " + (m.get("round") or "").split(" - ")[-1].strip().lower()) if is_qual(m) else (m.get("round") or "").split(" - ")[-1].strip(),
        "surface": m.get("surface"),
        "p1": {"name": pl.get("p1", {}).get("name", "?"), "country": pl.get("p1", {}).get("country"), "rank": pl.get("p1", {}).get("ranking"),
               "bd": pl.get("p1", {}).get("birthday")},
        "p2": {"name": pl.get("p2", {}).get("name", "?"), "country": pl.get("p2", {}).get("country"), "rank": pl.get("p2", {}).get("ranking"),
               "bd": pl.get("p2", {}).get("birthday")},
        "games": [list(games[0]), list(games[1])],
        "winner": winner_index(m),
        "tour": m.get("tour"), "gender": m.get("gender"), "q": is_qual(m), "fq": bool(m.get("is_qualifying")),
    }


def _past_context(m, w):
    """Contexto calculado só com os jogos que já acompanhamos (nada vem de fora): caminho no torneio, forma recente e confronto direto.
    Os números e frases vão para a IA como dados; ela não calcula nada."""
    try:
        if w not in (1, 2):
            return {}
        cur = slim(m)
        pw, pl = cur["p%d" % w], cur["p%d" % (3 - w)]
        today = datetime.date.fromisoformat(cur["date"])
        base = webapp.base_tournament(cur["tournament"]).lower()
        rows = []
        for r in load_results():
            if r.get("id") == m.get("id") or r.get("q"):
                continue
            try:
                d = datetime.date.fromisoformat((r.get("date") or "")[:10])
            except ValueError:
                continue
            if d > today or (today - d).days > 60 or r.get("winner") not in (1, 2):
                continue
            rows.append((d, r))
        rows.sort(key=lambda x: x[0])

        def view(r, name):
            """(ganhou?, adversário, resultado do ponto de vista de `name`) ou None."""
            for i in (1, 2):
                if (r.get("p%d" % i) or {}).get("name") == name:
                    me, op = (r.get("p%d" % i) or {}), (r.get("p%d" % (3 - i)) or {})
                    g = r.get("games") or [[], []]
                    sc = " ".join(f"{a}-{b}" for a, b in zip(g[i - 1], g[2 - i]))
                    return (r.get("winner") == i, op.get("name", "?"), sc, op.get("rank"))
            return None

        ctx = {}
        for tag, name in (("winner", pw["name"]), ("loser", pl["name"])):
            path, form = [], []
            for d, r in rows:
                v = view(r, name)
                if not v:
                    continue
                form.append(v[0])
                if webapp.base_tournament(r.get("tournament", "")).lower() == base and (today - d).days <= 21:
                    path.append(f"{r.get('round') or ''}: {'beat' if v[0] else 'lost to'} {v[1]} {v[2]}".strip(": "))
            if path:
                ctx["earlier_rounds_" + tag] = path[-4:]
            last = form[-6:]
            if len(last) >= 3:
                wn, ls = sum(last), len(last) - sum(last)
                ctx["recent_form_" + tag] = f"{wn} {'win' if wn == 1 else 'wins'} and {ls} {'loss' if ls == 1 else 'losses'} in the last {len(last)} tracked matches"
        h2h = [view(r, pw["name"]) for _, r in rows]
        h2h = [v for v in h2h if v and v[1] == pl["name"]]
        if h2h:
            ctx["earlier_meetings_tracked"] = [("winner won " if v[0] else "winner lost ") + v[2] for v in h2h[-3:]]
        if pw.get("bd"):
            try:
                age = (today - datetime.date.fromisoformat(pw["bd"][:10])).days // 365
                if 14 < age < 50:
                    ctx["winner_age"] = age
            except ValueError:
                pass
        if pw.get("country"):
            ctx["winner_country"] = pw["country"]
        if pl.get("country"):
            ctx["loser_country"] = pl["country"]
        return ctx
    except Exception as e:
        print("Contexto da legenda indisponível:", type(e).__name__, e)
        return {}


def add_result(m):
    row = slim(m)
    try:                                          # o mesmo jogo pode já ter entrado pelo ESPN (src="espn"): fica a versão da API, com os tie-breaks do ESPN
        import espn as _e
        ka, kb = _e._keys(row["p1"]["name"]), _e._keys(row["p2"]["name"])
        bt = webapp.slugify(webapp.base_tournament(row["tournament"]))
        dup = [r for r in load_results() if r.get("src") == "espn" and webapp.slugify(webapp.base_tournament(r.get("tournament", ""))) == bt
               and ((ka & _e._keys(r["p1"]["name"]) and kb & _e._keys(r["p2"]["name"])) or (ka & _e._keys(r["p2"]["name"]) and kb & _e._keys(r["p1"]["name"])))]
    except Exception:
        dup = []
    for r in dup:
        if r.get("tb") and len(r["tb"][0]) == len(row["games"][0]):
            row["tb"] = r["tb"] if ka & _e._keys(r["p1"]["name"]) else [r["tb"][1], r["tb"][0]]
    if m.get("source") == "espn" and m.get("tb"):
        row["tb"] = m["tb"]
    results = [r for r in load_results() if r.get("id") != m.get("id") and not any(r.get("id") == d.get("id") for d in dup)]
    results.append(row)
    save_results(results)
    try:
        extras.update_stats(row)
    except Exception as e:                          # as estatísticas nunca devem impedir o resultado de ser guardado
        print("Estatísticas acumuladas: erro", e)


# ---------- site estático (verde e creme) ----------
IG_URL = "https://www.instagram.com/beyond100.tennis/"
PAGE_TEXT = {
    "en": {"title": "Latest results", "lead": "Challenger, ITF and the tour beyond the top 100.",
           "empty": "No results yet. Check back soon.", "nav": "Results", "home": "Home",
           "h1a": "Tennis beyond", "h1b": "the top 100.",
           "desc": "Live scores, clean result cards and the stories from the Challenger, ITF and WTA courts.",
           "follow": "Follow @beyond100.tennis", "all": "All results",
           "note": "Scores are provided for information only and may contain delays or errors.",
           "f_all": "All", "f_men": "Men", "f_women": "Women", "f_singles": "Singles", "f_doubles": "Doubles",
           "f_alltour": "All tournaments", "f_matches": "matches", "f_more": "Show more",
           "f_tournament": "Tournament", "f_player": "Search player", "f_highlights": "Top matches", "f_games": "of games",
           "f_champion": "Champion", "f_bracket": "Bracket", "f_tbd": "To be decided", "f_search_tour": "Search tournament", "f_tournaments": "All tournaments",
           "b_comeback": "Comeback", "b_bagel": "Bagel (6-0)", "b_breadstick": "Breadstick (6-1)",
           "b_super": "Super tie-break", "b_tb": "{n} tie-break", "b_closest": "Closest of the day"},
    "pt": {"title": "Últimos resultados", "lead": "Challenger, ITF e o circuito para lá do top 100.",
           "empty": "Ainda sem resultados. Volta em breve.", "nav": "Resultados", "home": "Início",
           "h1a": "Ténis para lá", "h1b": "do top 100.",
           "desc": "Resultados ao vivo, cartões limpos e as histórias dos campos de Challenger, ITF e WTA.",
           "follow": "Segue @beyond100.tennis", "all": "Todos os resultados",
           "note": "Os resultados são apenas informativos e podem conter atrasos ou erros.",
           "f_all": "Todos", "f_men": "Masculino", "f_women": "Feminino", "f_singles": "Singulares", "f_doubles": "Pares",
           "f_alltour": "Todos os torneios", "f_matches": "jogos", "f_more": "Mostrar mais",
           "f_tournament": "Torneio", "f_player": "Pesquisar jogador", "f_highlights": "Destaques", "f_games": "dos jogos",
           "f_champion": "Campeão", "f_bracket": "Quadro", "f_tbd": "Por apurar", "f_search_tour": "Pesquisar torneio", "f_tournaments": "Todos os torneios",
           "b_comeback": "Virada", "b_bagel": "Set a 0", "b_breadstick": "Set 6-1",
           "b_super": "Super tie-break", "b_tb": "{n} tie-break", "b_closest": "Mais disputado do dia"},
}

EMBLEM_SVG = """<svg viewBox="0 0 600 600" role="img" aria-label="Beyond100" class="emb">
<circle cx="300" cy="300" r="290" fill="#0e3a2d" stroke="#f7f2e6" stroke-width="8"/>
<circle cx="300" cy="300" r="170" fill="none" stroke="#f7f2e6" stroke-width="2"/>
<defs><path id="pt" d="M 100,300 A 200,200 0 0 1 500,300"/><path id="pb" d="M 68,300 A 232,232 0 0 0 532,300"/></defs>
<text font-family="Georgia,'Times New Roman',serif" font-weight="700" font-size="46" letter-spacing="8" fill="#f7f2e6" text-anchor="middle"><textPath href="#pt" startOffset="50%">BEYOND100</textPath></text>
<text font-family="Georgia,'Times New Roman',serif" font-weight="700" font-size="30" letter-spacing="5" fill="#f7f2e6" text-anchor="middle"><textPath href="#pb" startOffset="50%">TENNIS · CHALLENGER · ITF</textPath></text>
<circle cx="64" cy="300" r="10" fill="#d9f23d"/><circle cx="536" cy="300" r="10" fill="#d9f23d"/>
<text x="300" y="352" font-family="Georgia,'Times New Roman',serif" font-weight="700" font-size="150" fill="#f7f2e6" text-anchor="middle">100</text>
</svg>"""

import webapp
import extras
import site_more
import i18n_site
import sport_switch
import site_ui
SITE_CSS_OLD = """
:root{--g:#0e3a2d;--deep:#09281f;--c:#f7f2e6;--v:#d9f23d;--s:#b0c4b7;--e:#2c5d4c}
*{box-sizing:border-box}
body{margin:0;background:var(--g);color:var(--c);font:16px/1.5 system-ui,"Segoe UI",Arial,sans-serif}
a{color:inherit}
.wrap{max-width:720px;margin:0 auto;padding:0 20px}
nav{display:flex;justify-content:space-between;align-items:center;padding:22px 0}
.brand{font:700 1.15rem Georgia,"Times New Roman",serif;letter-spacing:.22em;text-decoration:none}
nav div a{margin-left:18px;color:var(--s);text-decoration:none;font-size:.95rem}
nav div a:hover{color:var(--c)}
.hero{text-align:center;padding:24px 0 40px}
.emb{width:min(250px,64vw);height:auto}
h1{font:700 2.6rem/1.05 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:24px 0 12px;letter-spacing:-.01em}
h1 em{color:var(--v);font-weight:400}
.hero p{color:var(--s);max-width:34ch;margin:0 auto 26px}
.btn{display:inline-block;background:var(--v);color:var(--g);font-weight:700;padding:13px 24px;border-radius:999px;text-decoration:none;margin:4px}
.btn.ghost{background:none;color:var(--c);border:2px solid var(--c)}
h2.sec{font:700 1.4rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:12px 0 14px;display:flex;justify-content:space-between;align-items:baseline}
h2.sec a{font:500 .9rem system-ui;color:var(--v)}
.page-h{padding:18px 0 10px}.page-h h1{font-size:2.1rem;margin:0 0 6px;text-align:left}
.page-h p{color:var(--s);margin:0}
article{background:var(--deep);border:1px solid var(--e);border-radius:22px;padding:16px 18px;margin:0 0 14px}
article h3{margin:0;font:700 .78rem system-ui;text-transform:uppercase;letter-spacing:.12em;color:var(--v)}
.m{color:var(--s);font-size:.85rem;margin:2px 0 8px}
.pl{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:8px 0;color:var(--s)}
.pl+.pl{border-top:1px solid var(--e)}
.pl.win{color:var(--c)}
.nm{display:block;font:700 1.1rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}.pl small{color:var(--s)}
.ch{display:flex;gap:6px}
.ch b{min-width:38px;height:38px;border-radius:11px;border:1px solid var(--e);color:var(--s);display:grid;place-items:center;font:700 1.05rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.ch b.on{background:var(--v);border-color:var(--v);color:var(--g)}
.empty{color:var(--s)}
footer{color:var(--s);font-size:.8rem;padding:28px 0 44px;border-top:1px solid var(--e);margin-top:28px}
"""


SITE_CSS = webapp.CSS


def _results_html(results, tr, empty):
    esc = html.escape
    rows = []
    for r in results:
        _, _, _, tag = webapp.classify(r)
        lines = []
        for i in (0, 1):
            p = r["p%d" % (i + 1)]
            chips = ""
            for a_, b_ in zip(r["games"][0], r["games"][1]):
                mine, other = (a_, b_) if i == 0 else (b_, a_)
                chips += f'<b class="{"on" if mine > other else ""}">{mine}</b>'
            cls = "win" if r["winner"] == i + 1 else ""
            lines.append(f'<div class="pl {cls}"><div>{webapp.name_html(p, r, esc)}'
                         f'<small>{esc(webapp.who_tag(p))}</small></div>'
                         f'<div class="ch">{chips}</div></div>')
        meta = " · ".join(x for x in [r["date"], tr["rounds"].get(r["round"].lower(), r["round"]),
                                       tr["surfaces"].get(r.get("surface"), "")] if x)
        tagh = f'<span class="tag">{esc(tag)}</span>' if tag else ""
        rows.append(f'<section class="tg"><h3 class="th">{tagh}<span>{esc(webapp.base_tournament(r["tournament"]))}</span></h3>'
                    f'<div class="mt">{webapp.mh_html(r, meta, esc)}{lines[0]}{lines[1]}</div></section>')
    return "\n".join(rows) or f'<p class="empty">{esc(empty)}</p>'


SOURCE_CODES = ["i", "w", "f", "x", "e"]   # i=Instagram w=WhatsApp f=Facebook x=X e=email
SITE_BASE = os.environ.get("SITE_URL") or "https://beyond100tennis.com"


LASTMOD, NOINDEX = {}, set()          # preenchidos por build_site: data da última alteração e páginas fora do Google
INDEXNOW_KEY = "b100c4e9a7f24d6e8a1f0b3c5d7e9f21"   # chave pública do IndexNow (é publicada no site; não é segredo)


def _manual_handles():
    import fetch_photos
    return {fetch_photos.slug(k): v.strip() for k, v in _load_json(HANDLES_FILE, {}).items()
            if not k.startswith("_") and re.fullmatch(r"@[A-Za-z0-9._]{1,30}", (v or "").strip())}


def _crumbs(items):
    """BreadcrumbList (schema.org): Início > ... > página."""
    lst = [{"@type": "ListItem", "position": 1, "name": "Beyond100", "item": SITE_BASE + "/"}]
    for i, (n, u) in enumerate(items, 2):
        lst.append({"@type": "ListItem", "position": i, "name": n, "item": f"{SITE_BASE}/{u}"})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": lst}


def _beacon():
    """Cloudflare Web Analytics manual: só carrega se este browser não for do dono (localStorage b100_owner, posto pelo /admin/)."""
    tok = re.sub(r"[^A-Za-z0-9]", "", os.environ.get("CF_BEACON_TOKEN") or "")
    if not tok:
        return ""
    return ('<script>try{if(!localStorage.getItem("b100_owner")){var s=document.createElement("script");s.defer=true;'
            's.src="https://static.cloudflareinsights.com/beacon.min.js";'
            's.setAttribute("data-cf-beacon",\'{"token":"' + tok + '"}\');document.head.appendChild(s)}}catch(e){}</script>\n')


def _tab_of(path):
    p = (path or "").split("?")[0]
    p = re.sub(r"^(es|fr|de|it)/", "", p)
    if p in ("", "index.html"):
        return "home"
    if p.startswith(("results", "m/", "t/", "live/", "next", "week")):
        return "results"
    if p.startswith("order-of-play"):
        return "today"
    if p.startswith("highlights"):
        return "videos"
    if p.startswith(("players", "p/", "countries", "c/", "rankings", "power", "road")):
        return "players"
    if p.startswith(("stats", "records")):
        return "stats"
    return ""


def _tbar(tx, path):
    import site_nav
    return site_nav.bar("tennis", _tab_of(path))


def clean_url(u):
    """URL como a Cloudflare a serve: /x.html redireciona (308) para /x e /pasta/index.html para /pasta/. O canonical, o sitemap
    e os hreflang têm de apontar para a versão final, senão o Google vê duas páginas e um canonical que redireciona (5/11/2026)."""
    u = u or ""
    if u.endswith("index.html"):
        return u[: -len("index.html")]
    return u[:-5] if u.endswith(".html") else u


_TT = None


def _title_test(slug, name, rk, has_next):
    """Título e frase de abertura do teste (gsc.json -> title_tests, estado 'running' ou 'won'), ou None."""
    global _TT
    if _TT is None:
        try:
            _TT = json.load(open("gsc.json", encoding="utf-8")).get("title_tests") or {}
        except (OSError, ValueError):
            _TT = {}
    t = _TT.get(slug)
    if not t or t.get("status") not in ("running", "won"):
        return None
    er = _load_json("espn_rank.json", {})
    hit, lg = None, ""
    for k in ("atp", "wta"):
        for x in er.get(k) or []:
            if (x.get("n") or "").lower() == (name or "").lower():
                hit, lg = x, k.upper()
    r = (hit or {}).get("r") or rk
    if not r:
        return None
    mv = ""
    if hit and isinstance(hit.get("prev"), int) and hit["prev"] != r:
        mv = f" (▲{hit['prev'] - r} this week)" if hit["prev"] > r else f" (▼{r - hit['prev']} this week)"
    day = time.strftime("%-d %b %Y")
    title = f"{name} ranking: No. {r}{mv} · updated {day}"
    lead = f"{name} is No. {r} in the {lg + ' ' if lg else ''}ranking{mv}, updated {day}." + (" Next match, live score and results." if has_next else " Latest results and form.")
    return title, lead


def _nl_slide():
    try:
        import nl_cta
        return nl_cta.slide("tennis")
    except Exception:
        return ""


def _shell(title, body, tx, root="", path="", desc=None, image="og/default.png", lang="en", alts=None, noindex=False, canonical=None, ld=None):
    esc = html.escape
    try:
        _lv = bool(extras.live_rows())
    except Exception:
        _lv = False
    import site_nav
    live_pill = site_nav.live_pill("/index.html#live-now", show=_lv, sport="tennis")
    desc = desc or ("Results, rankings and stories from the Challenger and ITF circuit: the tennis beyond the top 100. "
                    "Daily results, a weekly numbers report and player stats.")
    seo = (f'<meta name="description" content="{esc(desc)}">\n'
           f'<link rel="canonical" href="{SITE_BASE}/{clean_url(path if canonical is None else canonical)}">\n'
           f'<meta property="og:type" content="website"><meta property="og:site_name" content="Beyond100">\n'
           f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">\n'
           f'<meta property="og:url" content="{SITE_BASE}/{clean_url(path)}">\n'
           f'<meta property="og:image" content="{SITE_BASE}/{image}"><meta name="twitter:card" content="summary_large_image">\n'
           f'<meta name="twitter:image" content="{SITE_BASE}/{image}">\n')
    for blk in (ld or []):                             # dados estruturados (schema.org) para o Google
        seo += '<script type="application/ld+json">' + json.dumps(blk, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    if path == "":                                     # página inicial: diz ao Google o nome da marca e o Instagram
        seo += ('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": [
            {"@type": "WebSite", "name": "Beyond100", "alternateName": ["Beyond 100 Tennis", "Beyond100 Tennis", "beyond100tennis"],
             "url": SITE_BASE + "/"},
            {"@type": "Organization", "name": "Beyond100", "alternateName": "Beyond 100 Tennis", "url": SITE_BASE + "/",
             "logo": SITE_BASE + "/favicon.png", "sameAs": [IG_URL]}]}) + "</script>\n")
    if alts:
        for lg, href in alts.items():
            seo += f'<link rel="alternate" hreflang="{lg}" href="{SITE_BASE}/{clean_url(href)}">\n'
        seo += f'<link rel="alternate" hreflang="x-default" href="{SITE_BASE}/{clean_url(alts["en"])}">\n'
    langs = ""
    if alts:
        langs = '<p class="lg">' + " · ".join(
            (f'<b>{esc(i18n_site.LANGS[lg])}</b>' if lg == lang else f'<a href="/{href}" hreflang="{lg}">{esc(i18n_site.LANGS[lg])}</a>')
            for lg, href in alts.items()) + "</p>"
    return (f'<!doctype html>\n<html lang="{lang}"><head><meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{esc(title)}</title>\n{seo}<meta name="theme-color" content="#0e3a2d">\n'
            f'{"<meta name=robots content=noindex,follow>" if noindex else "<meta name=robots content=max-image-preview:large>"}{_beacon()}'
            f'<link rel="icon" href="/favicon.svg" type="image/svg+xml">\n'
            f'<link rel="icon" href="/favicon.png" sizes="192x192" type="image/png">\n'
            f'<link rel="apple-touch-icon" href="/favicon.png">\n'
            f'<style>{SITE_CSS}{extras.EXTRA_CSS}{site_ui.CSS}{sport_switch.CSS}{site_nav.CSS}</style></head><body><div class="wrap">\n'
            f'<nav><a class="brand" href="{root}index.html">BEYOND100</a><div>'
            f'{live_pill}<a class="ntop" href="{root}results.html">{esc(tx["nav"])}</a><a class="ntop" href="{root}players.html">{esc(tx.get("players", "Players"))}</a>{(f'<a class="ntop" href="{root}rankings.html">{esc(extras.L(tx, "x_rankings"))}</a>' if extras.have_full_rankings() else "")}<a class="ntop" href="{root}stats.html">{esc(extras.L(tx, "x_stats"))}</a><a href="{IG_URL}">Instagram</a>{site_more.SEARCH_BTN}</div></nav>\n{sport_switch.switch("tennis")}'
            f'{site_more.SEARCH_HTML}{body}\n' + site_nav.footer("BEYOND100", "Tennis beyond the top 100: Challenger, ITF and WTA scores, rankings and the stories behind them.",
                                                           [("Follow on Instagram", IG_URL, True), ("Weekly newsletter", "/newsletter/latest.html", False)],
                                                           [("Explore", [("Latest results", "/results.html"), ("Order of play", "/order-of-play.html"), ("Next week", "/next.html"),
                                                                         ("This week", "/week/"), ("Players", "/players.html"), ("Highlights", "/highlights.html")]),
                                                            ("Rankings & stats", [("Rankings", "/rankings.html"), ("Road to the Top 100", "/road.html"), ("Power Ranking", "/power.html"),
                                                                                  ("Records", "/records.html"), ("Stats", "/stats.html"), ("Countries", "/countries.html")]),
                                                            ("Beyond100", [("About", "/about.html"), (extras.L(tx, "x_credits"), "/credits.html"), ("Beyond Padel", "/padel/index.html")])],
                                                           esc(tx["note"]), f"<span>{langs.lstrip(' ·')}</span>" if langs else "")
            + f'</div>{_tbar(tx, path)}' + __import__("site_ui").LOCALTIME_JS + __import__("site_ui").DEAD_YT_JS + _nl_slide() + '</body></html>')


FAVICON_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0e3a2d"/>'
               '<circle cx="32" cy="32" r="25" fill="none" stroke="#f4efe0" stroke-width="3"/>'
               '<text x="32" y="40" text-anchor="middle" font-family="Georgia,serif" font-weight="700" font-size="22" fill="#d9f23a">100</text></svg>')


def write_favicons(out_dir):
    with open(os.path.join(out_dir, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(FAVICON_SVG)
    S = 192
    im = Image.new("RGB", (S, S), (14, 58, 45))
    d = ImageDraw.Draw(im)
    d.ellipse((14, 14, S - 14, S - 14), outline=(244, 239, 224), width=8)
    d.text((S / 2, S / 2 + 2), "100", font=font(FONT_SERIF_B, 62), fill=(217, 242, 58), anchor="mm")
    im.save(os.path.join(out_dir, "favicon.png"))


def og_image(path, title, sub=""):
    """Imagem de partilha 1200x630 (verde e creme) para WhatsApp, Instagram, X, etc."""
    W_, H_ = 1200, 630
    im = Image.new("RGB", (W_, H_), (14, 58, 45))
    d = ImageDraw.Draw(im)
    d.rectangle([40, 40, W_ - 40, H_ - 40], outline=(44, 93, 76), width=3)
    d.text((80, 100), "BEYOND100", font=font(FONT_SERIF_B, 34), fill=(217, 242, 58))
    f = fit_font(d, title, FONT_SERIF_B, 92, W_ - 160, 40)
    d.text((80, 290), title, font=f, fill=(247, 242, 230), anchor="ls")
    if sub:
        d.text((80, 360), sub, font=fit_font(d, sub, FONT_BOLD, 38, W_ - 160, 24), fill=(176, 196, 183), anchor="ls")
    d.text((80, H_ - 90), "Tennis beyond the top 100  ·  beyond100tennis.com", font=font(FONT_BOLD, 28), fill=(247, 242, 230))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)


def _og_avatar(img, cx, cy, r, p, ring, credits_out):
    """Como avatar(), mas só com fotos já guardadas (nunca vai à rede durante a construção do site)."""
    lp = local_photo(p.get("name") or "")
    if lp:
        key, fp = lp
        cr = _load_json(os.path.join(PHOTO_DIR, "credits.json"), {}).get(os.path.basename(fp))
        try:
            ph = ImageOps.fit(Image.open(fp).convert("RGB"), (2 * r, 2 * r), centering=(0.5, 0.3))
            mask = Image.new("L", (2 * r, 2 * r), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
            img.paste(ph, (cx - r, cy - r), mask)
            if cr:
                credits_out.append(cr)
            ImageDraw.Draw(img).ellipse([cx - r, cy - r, cx + r, cy + r], outline=ring, width=5)
            return
        except Exception:
            pass
    d = ImageDraw.Draw(img)
    parts = (p.get("name") or "?").split()
    ini = (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=DEEP, outline=ring, width=5)
    d.text((cx, cy), ini, font=font(FONT_SERIF_B, int(r * 0.85)), fill=CREAM, anchor="mm")


def og_match(path, tag, tournament, rnd, p1, p2, games, winner=None, live=False):
    """Imagem de partilha de um jogo (1200x630): os dois jogadores com foto, resultado por sets, 'LIVE' ou 'FINAL'."""
    W_, H_ = 1200, 630
    im = Image.new("RGB", (W_, H_), GREEN)
    d = ImageDraw.Draw(im)
    d.rectangle([28, 28, W_ - 29, H_ - 29], outline=(44, 93, 76), width=3)
    d.text((70, 72), "BEYOND100", font=font(FONT_SERIF_B, 30), fill=VOLT, anchor="lm")
    clean = lambda t: " ".join(str(t or "").split())
    head = " · ".join(clean(x) for x in [tag, tournament, rnd] if x)
    d.text((W_ - 70, 72), head, font=fit_font(d, head, FONT_BOLD, 30, 760, 18), fill=SOFT, anchor="rm")
    credits = []
    n = max(len(games[0]), len(games[1]), 1)
    for i, p in enumerate((p1, p2)):
        cy = 230 + i * 200
        won = winner == i + 1
        _og_avatar(im, 150, cy, 72, p, VOLT if won else (88, 124, 108), credits)
        nm = clean(p.get("name")) or "?"
        nf = fit_font(d, nm, FONT_SERIF_B, 58, 560, 30)
        d.text((250, cy - 20), nm, font=nf, fill=CREAM if (won or not winner) else SOFT, anchor="ls")
        info = " · ".join(x for x in [(p.get("country") or "").upper(), f"#{p['rank']}" if isinstance(p.get("rank"), int) and p["rank"] > 0 else ""] if x)
        d.text((250, cy + 30), info, font=font(FONT_BOLD, 28), fill=SOFT, anchor="ls")
        mine, oth = games[i], games[1 - i]
        for k in range(n):
            x = W_ - 110 - (n - 1 - k) * 92
            a = mine[k] if k < len(mine) else ""
            b = oth[k] if k < len(oth) else ""
            on = isinstance(a, int) and isinstance(b, int) and a > b and (not live or k < n - 1)
            d.rounded_rectangle([x - 38, cy - 46, x + 38, cy + 34], radius=14, fill=VOLT if on else None,
                                outline=VOLT if on else (88, 124, 108), width=3)
            d.text((x, cy - 6), str(a), font=font(FONT_SERIF_B, 48), fill=GREEN if on else CREAM, anchor="mm")
    badge = "LIVE" if live else "FINAL"
    bf = font(FONT_BOLD, 26)
    bw = d.textlength(badge, font=bf) + 36
    d.rounded_rectangle([70, H_ - 104, 70 + bw, H_ - 60], radius=12, fill=VOLT)
    d.text((70 + bw / 2, H_ - 82), badge, font=bf, fill=GREEN, anchor="mm")
    d.text((90 + bw, H_ - 82), "beyond100tennis.com", font=font(FONT_BOLD, 28), fill=CREAM, anchor="lm")
    if credits:
        cr = clean("Photos: " + " · ".join(dict.fromkeys(c.replace("Photo: ", "") for c in credits)))
        d.text((W_ - 70, H_ - 82), cr, font=fit_font(d, cr, FONT_REG, 18, 520, 12), fill=SOFT, anchor="rm")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, optimize=True)


def local_photo(name):
    """Foto já guardada em photos/ (sem rede), ou None."""
    key = _slug(name)
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        fp = os.path.join(PHOTO_DIR, key + ext)
        if key and os.path.exists(fp):
            return key, fp
    return None


def prefetch_photos(people, budget_s=70):
    """Procura (na Wikimedia, só licenças livres) as fotos que ainda faltam, por ordem de importância, com um limite de tempo por execução."""
    try:
        from fetch_photos import audit_photos
        audit_photos(PHOTO_DIR)                      # tira fotos cujo ficheiro não identifica o jogador (sem rede)
    except Exception as e:
        print("Auditoria de fotos:", e)
    if os.environ.get("FETCH_PHOTOS") != "1":
        return
    from fetch_photos import fetch_photo, refresh_photo
    t0, n = time.time(), 0
    for name, bd in people:
        if time.time() - t0 > budget_s:
            break
        if not name:
            continue
        if local_photo(name):                       # já tem foto: de vez em quando procura uma mais recente (máx. 1x/mês por jogador)
            try:
                refresh_photo(name, bd, PHOTO_DIR)
            except Exception as e:
                print("Foto (atualizar):", name, e)
            continue
        try:
            fetch_photo(name, bd, PHOTO_DIR)
            n += 1
        except Exception as e:
            print("Foto (site):", name, e)
    print(f"Fotos do site: {n} jogadores verificados.")


def build_avatars(out_dir, names):
    """Miniaturas quadradas (192 px) das fotos licenciadas, para o site. Também prepara os créditos."""
    credits = _load_json(os.path.join(PHOTO_DIR, "credits.json"), {}) if os.path.isdir(PHOTO_DIR) else {}
    sources = _load_json(os.path.join(PHOTO_DIR, "sources.json"), {}) if os.path.isdir(PHOTO_DIR) else {}
    idir = os.path.join(out_dir, "img")
    webapp.AVATARS.clear()
    extras.CREDITS.clear()
    extras.CREDIT_ROWS.clear()
    for name in sorted(set(n for n in names if n)):
        lp = local_photo(name)
        if not lp:
            continue
        key, fp = lp
        base = os.path.basename(fp)
        cr = credits.get(base)
        if not cr:                                       # sem crédito registado: só usamos se for foto tua (sem licença a atribuir)
            if os.path.exists(os.path.join(PHOTO_DIR, "sources.json")) and base in sources:
                continue
        try:
            os.makedirs(idir, exist_ok=True)
            src = Image.open(fp).convert("RGB")
            im = ImageOps.fit(src, (192, 192), centering=(0.5, 0.2))
            im.save(os.path.join(idir, key + ".jpg"), quality=82, optimize=True)
            os.makedirs(os.path.join(idir, "big"), exist_ok=True)         # foto grande do topo da página do jogador (7/11/2026)
            ImageOps.fit(src, (600, 750), centering=(0.5, 0.25)).save(os.path.join(idir, "big", key + ".jpg"), quality=80, optimize=True, progressive=True)
        except Exception as e:
            print("Miniatura falhou:", name, e)
            continue
        webapp.AVATARS.add(key)
        if cr:
            extras.CREDITS[key] = cr
            extras.CREDIT_ROWS[key] = {"name": name, "credit": cr, "page": (sources.get(base) or {}).get("commons_page", "")}


def _safe(fn):
    try:
        return fn() or ""
    except Exception as e:
        print("Bloco falhou:", getattr(fn, "__name__", fn), type(e).__name__, e)
        return ""


def _home_v2(results, singles, tx, tr, hl):
    """Página inicial nova: acontecimento do dia, quem somos + pesquisa + números, ao vivo, campeões com foto, destaques, resultados por torneio."""
    import home_ui
    import player_ui as pu
    import site_ui
    esc = html.escape
    today = datetime.date.today()
    rk = lambda p: p.get("rank") if isinstance(p.get("rank"), int) and p["rank"] > 0 else None
    ini = lambda n: "".join(x[0] for x in (n or "?").split()[:2]).upper()
    big = lambda n: f"/img/big/{webapp.slugify(n)}.jpg" if webapp.slugify(n) in webapp.AVATARS else ""
    sc_of = lambda r: " ".join(f"{x}-{y}" for x, y in zip(r["games"][r["winner"] - 1], r["games"][2 - r["winner"]]))
    is_final = lambda r: (r.get("round") or "").strip().lower() in ("final", "finals")

    def age(r):
        try:
            return (today - datetime.date.fromisoformat(r.get("date", "")[:10])).days
        except ValueError:
            return 99

    # --- acontecimento do dia (e os 3 seguintes, ao lado)
    full = lambda r: bool(r["games"][0]) and webapp._set_done(r["games"][0][-1], r["games"][1][-1])   # sem desistências (ex.: 7-6 3-0 ret.)
    rlab = lambda r: tr["rounds"].get((r.get("round") or "").lower(), r.get("round") or "")
    cands = []
    for r in singles:
        if r.get("winner") not in (1, 2) or age(r) > 3:
            continue
        W, L = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
        tag = webapp.classify(r)[3]
        pts = None
        if is_final(r):
            pts = 100 - 8 * _tier_rank(tag)
        elif rk(W) and rk(L) and rk(W) - rk(L) >= 150 and full(r):
            pts = 40 + min((rk(W) - rk(L)) / 20, 30)
        if pts is None:
            continue
        pts += (25 if big(W["name"]) else 0) - 6 * age(r)
        cands.append((pts, r))
    cands.sort(key=lambda c: -c[0])
    best = cands[0] if cands else None
    lead = ""
    more_rows = ""
    for _, r in cands[1:4]:
        W, L = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
        T = webapp.base_tournament(r.get("tournament", ""))
        what = f"wins {T}" if is_final(r) else f"(No. {rk(W)}) beats No. {rk(L)} {_surname(L['name'])}"
        more_rows += (f'<a href="/m/{r["id"]}.html">{webapp.avatar(W["name"], "av") or f"<span class=i>{esc(ini(W['name']))}</span>"}'
                      f'<span><b>{esc(W["name"])} {esc(what)}</b><small>{esc(sc_of(r))} · {esc(rlab(r))} · {esc(T if not is_final(r) else webapp.classify(r)[3])}</small></span></a>')
    if best:
        r = best[1]
        W, L = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
        T = webapp.base_tournament(r.get("tournament", ""))
        tag = webapp.classify(r)[3]
        try:
            d = datetime.date.fromisoformat(r["date"][:10]).strftime("%-d %b")
        except ValueError:
            d = ""
        cr = extras.CREDITS.get(webapp.slugify(W["name"]), "") if big(W["name"]) else ""
        if is_final(r):
            lead = home_ui.lead(f"/m/{r['id']}.html", big(W["name"]), ini(W["name"]), [tag or "Final", "Champion"], f"{W['name']} wins {T}",
                                f"Beat {L['name']}" + (f" (No. {rk(L)})" if rk(L) else "") + f" {sc_of(r)} in the final" + (f" · {d}" if d else ""), cr)
        else:
            lead = home_ui.lead(f"/m/{r['id']}.html", big(W["name"]), ini(W["name"]), ["Upset", tag], f"{W['name']} stuns {L['name']}",
                                f"No. {rk(W)} beat No. {rk(L)} {sc_of(r)} · {rlab(r)} · {T}" + (f" · {d}" if d else ""), cr)
    # --- lado: quem somos, pesquisa, números
    n = webapp.week_numbers(results)
    side = (home_ui.search()
            + home_ui.intro(tx["h1a"], tx["h1b"], tx["desc"], [(tx["follow"], IG_URL, True), ("This week", "/week/", False)])
            + (f'<div class="hm-more"><div class="pv-lab">More stories</div>{more_rows}</div>' if more_rows else "")
            + home_ui.nums([(n["matches"], "matches in 7 days", "/week/"), (n["tournaments"], "tournaments", "/results.html"),
                            (n["finals"], "finals", "/results.html")]))
    if not lead:                                                  # sem acontecimento forte: o lado ocupa a largura toda
        lead, side = side, ""
    # --- campeões com foto
    seen, cards = set(), []
    _cut = (today - datetime.timedelta(days=10)).isoformat()
    for r in singles:
        if r.get("date", "") < _cut or r.get("winner") not in (1, 2) or not is_final(r):
            continue
        g, _, _, tag = webapp.classify(r)
        key = (webapp.base_tournament(r.get("tournament", "")), g)
        if key in seen:
            continue
        seen.add(key)
        W, L = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
        cards.append((_tier_rank(tag) + (0 if g == "men" else 0.0001), r.get("date", ""),
                      home_ui.champ(f"/m/{r['id']}.html", big(W["name"]), ini(W["name"]), tag or "Final", {"men": "Men", "women": "Women"}.get(g, "Champion"),
                                    W["name"], key[0], f"d. {_surname(L['name'])} {sc_of(r)} · {r.get('date', '')[8:10]}/{r.get('date', '')[5:7]}")))
    cards.sort(key=lambda c: (c[0], "".join(chr(255 - ord(ch)) for ch in c[1])))
    champs = (site_ui.sec("Latest champions", "/results.html", "All results") + '<div class="hm-row">' + "".join(c[2] for c in cards[:8]) + "</div>") if cards else ""
    # --- resultados por torneio
    groups, order = {}, []
    for r in singles:
        if r.get("winner") not in (1, 2):
            continue
        t = webapp.base_tournament(r.get("tournament", ""))
        if t not in groups:
            if len(order) >= 4:
                continue
            groups[t] = []
            order.append(t)
        if len(groups[t]) < 4:
            groups[t].append(r)
    evs = ""
    for t in order:
        rs = groups[t]
        r0 = rs[0]
        g, _, _, tag = webapp.classify(r0)
        rows = []
        for r in rs:
            W, L = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
            tb = r.get("tb")
            rows.append((extras._rshort(r.get("round"), r.get("q")), extras.plink(W["name"]),
                         f"d. {L['name']}" + (f" · No. {rk(L)}" if rk(L) else ""),
                         pu.score(r["games"][r["winner"] - 1], r["games"][2 - r["winner"]], tb[r["winner"] - 1] if tb else None, tb[2 - r["winner"]] if tb else None),
                         f"/m/{r['id']}.html", True))
        ts = webapp.slugify(t)
        evs += pu.event(f'<a href="/t/{ts}.html">{esc(t)}</a>', " · ".join(x for x in [tag, (r0.get("surface") or "").title(), r0.get("date", "")] if x), "", rows)
    res = (site_ui.sec(esc(tx["title"]), "results.html", tx["all"].rstrip(" →")) + f'<div class="hm-res">{evs}</div>') if evs else ""
    rest = (f'{extras.live_block(tx, 4)}{champs}'
            + (site_ui.sec("▶ Latest highlights", "/highlights.html", "All videos") + hl if hl else "")
            + res + _safe(extras.spotlight_block)
            + f'{webapp.week_block(n, tx)}{sport_switch.promo()}'
            + site_ui.quick([("/results.html", "Results", "Every score, newest first"), ("/order-of-play.html", "Today", "Order of play, live"),
                             ("/players.html", "Players", "Form and streaks"), ("/week/", "This week", "Champions, upsets and climbers")])
            + f'{extras.newsletter_block(tx)}')
    return f"<style>{pu.CSS}</style>" + home_ui.page(lead, side, rest)


def _core_pages(results, singles, tx, tr, lang, linkable):
    """Páginas principais (início, resultados, jogadores, rankings, stats, créditos) num idioma."""
    esc = html.escape
    ranks = _load_json(RANKS_FILE, {})
    _words = lambda t, d0: " ".join(f'<span class="hw" style="animation-delay:{d0 + 0.14 * i:.2f}s">{esc(w)}</span>' for i, w in enumerate(t.split()))
    import site_ui
    import tennis_videos
    # campeões dos últimos 10 dias (finais de singulares), um por torneio e género
    _cut = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 10 * 86400))
    _seen, _ch, _cards = set(), "", []
    for r in singles:
        if r.get("date", "") < _cut or r.get("winner") not in (1, 2) or (r.get("round") or "").strip().lower() not in ("final", "finals"):
            continue
        _g, _k, _lv, _tag = webapp.classify(r)
        _key = (webapp.base_tournament(r.get("tournament", "")), _g)
        if _key in _seen:
            continue
        _seen.add(_key)
        _w, _l = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
        _sc = " ".join(f"{x}-{y}" for x, y in zip(r["games"][r["winner"] - 1], r["games"][2 - r["winner"]]))
        _av = webapp.avatar(_w["name"], "av") or f'<span class="ini">{esc("".join(x[0] for x in _w["name"].split()[:2]).upper())}</span>'
        _cards.append((_tier_rank(_tag) + (0 if _g == "men" else 0.0001), r.get("date", ""), site_ui.champ_card(f"/m/{r['id']}.html", _tag or "Final", webapp.base_tournament(r.get("tournament", "")),
                                  {"men": "Men", "women": "Women"}.get(_g, "Champion"),
                                  f'{esc(_w["name"])}', f'{r.get("date", "")[5:]} · d. {_surname(_l["name"])} {_sc}', _av)))
    # torneios a decorrer sem campeão ainda: mostra quem ganhou no ano passado (ESPN), no lugar do seu nível (6/11/2026)
    try:
        _ev = _load_json("espn.json", {}).get("events") or []
        _now = time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())
        for ev in _ev:
            if not (ev.get("start", "") <= _now <= ev.get("end", "")):
                continue
            for _g, _pn in (ev.get("prev") or {}).items():
                _bt = webapp.slugify(ev.get("tp") or "")
                if not _pn or (webapp.base_tournament(ev.get("tp") or ""), _g) in _seen:
                    continue
                _rr = next((x for x in singles if webapp.slugify(webapp.base_tournament(x.get("tournament", ""))) == _bt
                            and webapp.classify(x)[0] == _g and x.get("date", "") >= ev.get("start", "")[:10]), None)
                if not _rr:
                    continue
                _tag = webapp.classify(_rr)[3]
                _fin = (dt_end := ev.get("end", "")[:10])
                try:
                    _fin = (datetime.date.fromisoformat(dt_end) - datetime.timedelta(days=1)).strftime("%d %b")
                except ValueError:
                    pass
                _av = webapp.avatar(_pn, "av") or f'<span class="ini">{esc("".join(x[0] for x in _pn.split()[:2]).upper())}</span>'
                _cards.append((_tier_rank(_tag) + (0 if _g == "men" else 0.0001), "9" + ev.get("end", ""),
                               site_ui.champ_card(f"/t/{_bt}.html", _tag or "", webapp.base_tournament(ev.get("tp") or ""),
                                                  f"{int(time.strftime('%Y')) - 1} champion", esc(_pn), f"Defending · final {_fin}", _av)))
    except Exception as e:
        print("Campeões do ano passado:", type(e).__name__, e)
    # 6/11/2026: por ordem de importância (Grand Slam, 1000, 500, 250, 125, Challenger por pontos, ITF); no mesmo nível ATP antes de WTA, e o mais recente primeiro
    _cards.sort(key=lambda c: (c[0], "".join(chr(255 - ord(ch)) for ch in c[1])))
    _ch = "".join(c[2] for c in _cards[:8])
    _hl = tennis_videos.cards(results, None, 8)
    home = (''
            f'<div class="court" aria-hidden="true"><div class="cl"></div><div class="net"></div><div class="bsh"></div><div class="ball"></div></div>'
            + site_ui.hero(EMBLEM_SVG, tx["h1a"], tx["h1b"], tx["desc"], [(tx["follow"], IG_URL, True), (tx["title"], "results.html", False)])
            + f'{extras.live_block(tx, 4)}'
            + (site_ui.sec("▶ Latest highlights", "/highlights.html", "All videos") + _hl if _hl else "")
            + (site_ui.sec("Latest champions", "/results.html", "All results") + f'<div class="ui-row">{_ch}</div>' if _ch else "")
            + _safe(extras.spotlight_block)
            + site_ui.sec(esc(tx["title"]), "results.html", tx["all"].rstrip(" →"))
            + f'{_results_html(singles[:4], tr, tx["empty"])}'
            f'{webapp.week_block(webapp.week_numbers(results), tx)}'
            f'{sport_switch.promo()}'
            + site_ui.quick([("/results.html", "Results", "Every score, newest first"), ("/order-of-play.html", "Today", "Order of play, live"),
                             ("/players.html", "Players", "Form and streaks"), ("/stats.html", "Stats", "Records and numbers")])
            + f'{extras.newsletter_block(tx)}')
    if os.environ.get("HOME_V2", "1") != "0":                     # 13/11/2026: página inicial nova (home_ui); HOME_V2=0 volta à antiga
        try:
            home = _home_v2(results, singles, tx, tr, _hl)
        except Exception as e:
            print("Página inicial v2 falhou:", type(e).__name__, e)
    home_title = "Beyond100 Tennis · " + (f'{tx["h1a"]} {tx["h1b"]}' if lang != "en" else "Challenger, ITF and WTA results beyond the top 100")
    return [("index.html", home, home_title),
            ("results.html", webapp.results_page(results, tr, tx, lang), tx["title"] + " · Beyond100 Tennis"),
            ("players.html", webapp.players_page(results, tx), tx.get("players", "Players") + " · Beyond100 Tennis"),
            ("stats.html", extras.stats_page(tx, tr), extras.L(tx, "x_stats") + " · Beyond100 Tennis"),
            ("highlights.html", __import__("tennis_videos").page(results), "Match highlights · Beyond100 Tennis"),
            ("credits.html", extras.credits_page(tx), extras.L(tx, "x_credits") + " · Beyond100 Tennis")] + (
        [("rankings.html", extras.rankings_page(tx, ranks, linkable, results), extras.L(tx, "x_rankings") + " · Beyond100 Tennis")])


def _bio_grid(results):
    """Topo da página do link da bio (/i/): miniaturas dos últimos posts publicados no Instagram; tocar leva à página do jogo
    (resultado completo, highlights, quadro). É o que quem vem do Instagram procura."""
    have = {str(r.get("id")) for r in results}
    sent = sorted([e for v in _load_json(POSTS_FILE, {}).values() for e in v if e.get("sent") and e.get("image") and str(e.get("id")) in have],
                  key=lambda e: e.get("sent_at") or "", reverse=True)[:9]
    if not sent:
        return ""
    css = ("<style>.bio{margin:4px 0 22px}.bio h2{font:700 1rem system-ui;margin:0 0 10px;display:flex;justify-content:space-between;align-items:baseline}"
           ".bio h2 small{font:500 .8rem system-ui;opacity:.7}.bio .g{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;border-radius:14px;overflow:hidden}"
           ".bio a{position:relative;display:block;aspect-ratio:4/5;background:#000}.bio img{width:100%;height:100%;object-fit:cover;display:block}"
           ".bio a span{position:absolute;right:5px;top:5px;font:800 .55rem system-ui;letter-spacing:.04em;background:#d9f23a;color:#0e3a2d;"
           "border-radius:999px;padding:1px 6px;opacity:.92}</style>")
    return (css + '<section class="bio"><h2>From our Instagram <small>tap a post for the full match</small></h2><div class="g">' + "".join(
        f'<a href="/m/{e["id"]}.html"><img src="/posts/{html.escape(e["image"])}" alt="" loading="lazy" width="360" height="450"><span>Match ›</span></a>'
        for e in sent) + "</div></section>")


def build_site(out_dir="site", player=None):
    """Gera o site (pasta pronta para o Cloudflare Pages): inglês na raiz e /es/, /fr/, /de/, /it/ nas páginas principais."""
    tx, tr = i18n_site.tx_for("en", PAGE_TEXT[LANG]), T
    esc = html.escape
    results = _heal(prune(load_results()))
    results = sorted(results, key=lambda r: r.get("date", ""), reverse=True)
    if player:
        q = player.lower()
        results = [r for r in results if q in r["p1"]["name"].lower() or q in r["p2"]["name"].lower()]
    os.makedirs(out_dir, exist_ok=True)
    _names = [p_["name"] for r in results for p_ in (r["p1"], r["p2"])]
    _names += [v.get("name") for v in _load_json(RANKS_FILE, {}).values()]
    for _m in _load_json(extras.LIVE_FILE, {}).get("matches", []):
        _names += [_m["p1"]["name"], _m["p2"]["name"]]
    _people = []
    for _m in _load_json(extras.LIVE_FILE, {}).get("matches", []):
        _people += [(_m["p1"]["name"], _m["p1"].get("bd")), (_m["p2"]["name"], _m["p2"].get("bd"))]
    for r in results[:80]:
        _w = r.get("winner")
        for i_ in ((_w, 3 - _w) if _w in (1, 2) else (1, 2)):
            _people.append((r["p%d" % i_]["name"], r["p%d" % i_].get("bd")))
    _people += [(v.get("name"), None) for v in sorted(_load_json(RANKS_FILE, {}).values(), key=lambda v: v.get("rank", 9999))[:40]]
    webapp.CUR_RANKS.update({v.get("name"): v.get("rank") for v in _load_json(RANKS_FILE, {}).values() if v.get("name")})
    extras.RANKS.update({webapp.slugify(v.get("name")): v for v in _load_json(RANKS_FILE, {}).values() if v.get("name")})
    _ps = _load_json(PSTATS_FILE, {})
    extras.PSTATS.update(_ps)
    extras.PSTATS_BY_NAME.update({webapp.slugify(v.get("name") or ""): v for v in _ps.values() if v.get("name")})
    prefetch_photos(_people)
    build_avatars(out_dir, _names)
    singles = [r for r in results if webapp.classify(r)[1] == "singles" and not r.get("q")]   # a qualificação fica só na página de resultados
    linkable = set(extras.players_index(results))
    extras.LINKABLE.clear()
    extras.LINKABLE.update(linkable)
    extras.PIDX = extras.players_index(results)       # o bloco "Players in the spotlight" da página inicial precisa dele (7/11/2026)
    paths = []
    write_favicons(out_dir)
    if os.path.isdir("posts"):                         # JPEGs dos posts (o Instagram vai buscá-los a este endereço)
        shutil.copytree("posts", os.path.join(out_dir, "posts"), dirs_exist_ok=True)
    multi = LANG == "en"                               # versões noutros idiomas só quando o site principal está em inglês
    for lg in (list(i18n_site.LANGS) if multi else [LANG]):
        ltx = i18n_site.tx_for(lg, PAGE_TEXT["en"]) if lg != LANG else tx
        ltr = i18n_site.tr_for(lg, I18N["en"]) if lg != LANG else tr
        ldir = out_dir if lg == "en" else os.path.join(out_dir, lg)
        os.makedirs(ldir, exist_ok=True)
        for name, body, title in _core_pages(results, singles, ltx, ltr, lg, linkable):
            href = lambda l_: ("" if name == "index.html" else name) if l_ == "en" else f"{l_}/{name if name != 'index.html' else ''}"
            alts = {l_: href(l_) for l_ in i18n_site.LANGS} if multi else None
            path = os.path.join(ldir, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(_shell(title, body, ltx, path=href(lg), lang=lg, alts=alts))
            paths.append(path)
    # páginas de origem (/i/ Instagram, /w/ WhatsApp ...): cópia da página inicial; as visitas a cada uma mostram de onde vieram
    try:
        _home = open(os.path.join(out_dir, "index.html"), encoding="utf-8").read()
        for _k in SOURCE_CODES:
            os.makedirs(os.path.join(out_dir, _k), exist_ok=True)
            _h = _home.replace("<head>", "<head><base href=\"/\"><meta name=robots content=noindex,follow>", 1)
            if _k == "i":                                    # 'link in bio': os últimos posts do Instagram, cada um leva ao seu jogo
                _h = _h.replace("Padel</a></div></div>", "Padel</a></div></div>" + _bio_grid(results), 1)
            with open(os.path.join(out_dir, _k, "index.html"), "w", encoding="utf-8") as f:
                f.write(_h)
    except Exception as e:
        print("Páginas de origem falharam:", e)
    # uma página por torneio (singulares primeiro, pares depois)
    done_ids = {str(x.get("id")) for x in results}
    ups = [u for u in _load_json(UPCOMING_FILE, {}).get("matches", []) if str(u.get("id")) not in done_ids]
    try:                                          # ATP/WTA por jogar vindos do ESPN (nomes completos, court e hora), sem repetir os da API
        import espn_sync, espn as _e
        eu = espn_sync.upcoming()
        if eu:
            seen = {k for u in eu for k in espn_sync._pair_keys(u["p1"]["name"], u["p2"]["name"])}
            ups = [u for u in ups if not any(k in seen for k in espn_sync._pair_keys(u["p1"]["name"], u["p2"]["name"]))] + eu
    except Exception as e:
        print("ESPN (próximos jogos): erro", e)
    groups = {}
    for x in results:
        groups.setdefault(webapp.base_tournament(x.get("tournament", "")), []).append(x)
    tdir = os.path.join(out_dir, "t")
    os.makedirs(tdir, exist_ok=True)
    og_dir = os.path.join(out_dir, "og")
    try:
        og_image(os.path.join(og_dir, "default.png"), "Tennis beyond the top 100", "Challenger · ITF · Tour results and stats")
    except Exception as e:
        print("Imagem de partilha (default) falhou:", e)
    for name, rs in groups.items():
        slug_t = webapp.slugify(name)
        body = webapp.tournament_page(name, rs, tr, tx, upcoming=ups)
        try:                                      # campeão do ano anterior (ESPN) e como lhe está a correr este ano
            import espn_sync, espn as _e
            _g = webapp.classify(rs[0])[0]
            _dc = espn_sync.defending(name, _g)
            if _dc:
                _k = _e._keys(_dc)
                _mine = sorted([x for x in rs if " / " not in x["p1"]["name"] and not x.get("q") and x.get("winner") in (1, 2)
                                and (_k & _e._keys(x["p1"]["name"]) or _k & _e._keys(x["p2"]["name"]))], key=lambda x: x.get("date", ""))
                _st, _up = "", True
                if _mine:
                    _last = _mine[-1]
                    _won = bool(_k & _e._keys(_last["p%d" % _last["winner"]]["name"]))
                    _rd = tr["rounds"].get((_last.get("round") or "").lower(), _last.get("round") or "")
                    _fin = (_last.get("round") or "").lower() == "final"
                    _st, _up = ("Defended the title", True) if _won and _fin else (f"Still in · won {_rd}", True) if _won else (f"Out · {_rd}", False)
                body = body.replace("</section>", site_ui.defending(extras.plink(_dc), _st, _up) + "</section>", 1)
        except Exception as e:
            print("Campeão em título (ESPN): erro", e)
        try:
            _ex, _ch = extras.tournament_extras(name, webapp.classify(rs[0])[0])
            body = (body.replace("</section>", "</section>" + _ex, 1) if _ex else body) + _ch   # a jogar: no topo; campeões: no fim
            _today = time.strftime("%Y-%m-%d", time.gmtime())
            _on = (bool(_ex and "Playing now" in _ex) or any(x.get("date") == _today for x in rs)
                   or any(u.get("date") == _today for u in webapp.scheduled_for(name, ups)))
            import tennis_videos
            _hc = tennis_videos.cards(rs)
            if _hc:
                body = body.replace("</section>", "</section>" + _hc, 1)
            if _on:
                _g, _k, _lv, _tag = webapp.classify(rs[0])
                _w = tennis_videos.watch_block(name, _tag, _g, _lv)
                if _w:
                    body = body.replace("</section>", "</section>" + _w, 1)
        except Exception as e:
            print("Extras do torneio falharam:", name, e)
        path = os.path.join(tdir, slug_t + ".html")
        img = "og/default.png"
        try:
            gender_, _, level_, tag_ = webapp.classify(rs[0])
            og_image(os.path.join(og_dir, f"t-{slug_t}.png"), name, " · ".join(x for x in [tag_, "results and draw"] if x))
            img = f"og/t-{slug_t}.png"
        except Exception as e:
            print("Imagem de partilha falhou:", name, e)
        _ds = sorted(x.get("date", "") for x in rs if x.get("date"))
        _tl = [{"@context": "https://schema.org", "@type": "SportsEvent", "name": name, "sport": "Tennis",
                "url": f"{SITE_BASE}/t/{os.path.basename(path)}", "eventStatus": "https://schema.org/EventScheduled",
                "location": {"@type": "Place", "name": re.sub(r"^(ATP|WTA|ITF)\s+(Challenger\s+)?", "", name) or name},
                "organizer": {"@type": "Organization", "name": "ATP Tour" if "ATP" in name.upper() or "CHALLENGER" in name.upper() else "WTA" if "WTA" in name.upper() else "ITF"}},
               _crumbs([("Results", "results.html"), (name, "t/" + os.path.basename(path))])]
        if _ds:
            _tl[0].update(startDate=_ds[0], endDate=_ds[-1])
            LASTMOD["t/" + os.path.basename(path)] = _ds[-1]
        _n = len(rs)
        # título para o Google: nome oficial (ESPN) + ano + nível, como as pessoas pesquisam ("Rolex Paris Masters 2026 results")
        try:
            import espn_sync
            _ev = espn_sync.event_for(name)
        except Exception:
            _ev = None
        _off = (_ev or {}).get("name") or name
        _yr = (_ds[-1] if _ds else time.strftime("%Y-%m-%d", time.gmtime()))[:4]
        _tagt = webapp.classify(rs[0])[3] or ""
        _full = _off if _yr in _off else f"{_off} {_yr}"
        _ttl = _full + (f" ({_tagt})" if _tagt and _tagt.lower() not in _full.lower() else "")
        _ups_t = [u for u in ups if webapp.slugify(re.sub(r"^(atp|wta|challenger|itf)\s+", "", (u.get("tp") or "").lower())) == slug_t
                  and len(u.get("t") or "") >= 16]
        if _off != name:
            body = body.replace("</h1>", f'</h1><p class="mut2" style="margin:-4px 0 6px">{esc(_full)}</p>', 1)
        _tl[0]["name"] = _full
        for u in sorted(_ups_t, key=lambda u: u["t"])[:20]:          # jogos marcados: o Google pode mostrar a hora na pesquisa
            _tl.append({"@context": "https://schema.org", "@type": "SportsEvent", "sport": "Tennis",
                        "name": f'{u["p1"]["name"]} vs {u["p2"]["name"]}, {_full}' + (f' ({u["round"]})' if u.get("round") else ""),
                        "startDate": u["t"], "eventStatus": "https://schema.org/EventScheduled",
                        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                        "location": {"@type": "Place", "name": (u.get("court") + ", " if u.get("court") else "") + name},
                        "competitor": [{"@type": "Person", "name": u["p1"]["name"]}, {"@type": "Person", "name": u["p2"]["name"]}],
                        "superEvent": {"@type": "SportsEvent", "name": _full, "url": f"{SITE_BASE}/t/{os.path.basename(path)}"},
                        "url": f"{SITE_BASE}/t/{os.path.basename(path)}"})
        with open(path, "w", encoding="utf-8") as f:
            f.write(_shell(f"{_ttl}: results, draw and order of play · Beyond100", body, tx, root="../", path="t/" + os.path.basename(path),
                           desc=f"{_ttl}: {_n} results with scores and rankings, the draw"
                                + (f", and the next {len(_ups_t)} matches with start times" if _ups_t else "")
                                + (f". Updated {_ds[-1]}." if _ds else "."), image=img, ld=_tl))
        paths.append(path)
    # uma página por jogo (singulares, últimos 45 dias)
    mdir = os.path.join(out_dir, "m")
    os.makedirs(mdir, exist_ok=True)
    cut = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 45 * 86400))
    _og_cut = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 3 * 86400))
    for r in results:
        if r.get("id") is None or r.get("date", "") < cut or webapp.classify(r)[1] != "singles" or r.get("winner") not in (1, 2):
            continue
        path = os.path.join(mdir, f"{r['id']}.html")
        _w = r["winner"]
        _pw, _pl = r["p%d" % _w], r["p%d" % (3 - _w)]
        _tn = webapp.base_tournament(r.get("tournament", ""))
        _sc = ", ".join(f"{x}-{y}" for x, y in zip(r["games"][_w - 1], r["games"][2 - _w]))
        _ml = [{"@context": "https://schema.org", "@type": "SportsEvent", "name": f"{_pw['name']} vs {_pl['name']}, {_tn}",
                "sport": "Tennis", "startDate": r.get("date", ""), "eventStatus": "https://schema.org/EventScheduled",
                "url": f"{SITE_BASE}/m/{r['id']}.html", "location": {"@type": "Place", "name": _tn},
                "superEvent": {"@type": "SportsEvent", "name": _tn, "url": f"{SITE_BASE}/t/{webapp.slugify(_tn)}.html"},
                "competitor": [{"@type": "Person", "name": _pw["name"], "url": f"{SITE_BASE}/p/{webapp.slugify(_pw['name'])}.html"},
                               {"@type": "Person", "name": _pl["name"], "url": f"{SITE_BASE}/p/{webapp.slugify(_pl['name'])}.html"}],
                "description": f"{_pw['name']} beat {_pl['name']} {_sc}" + (f" ({r.get('round')})" if r.get("round") else "") + "."},
               _crumbs([("Results", "results.html"), (_tn, f"t/{webapp.slugify(_tn)}.html"), (f"{_pw['name']} vs {_pl['name']}", f"m/{r['id']}.html")])]
        LASTMOD[f"m/{r['id']}.html"] = r.get("date", "")
        _rk = lambda p: f" (#{p['rank']})" if isinstance(p.get("rank"), int) else ""
        _img = "og/default.png"
        if r.get("date", "") >= _og_cut:              # imagem de partilha própria para os jogos dos últimos dias
            try:
                og_match(os.path.join(og_dir, "m", f"{r['id']}.png"), webapp.classify(r)[3], _tn,
                         tr["rounds"].get((r.get("round") or "").lower(), r.get("round") or ""), r["p1"], r["p2"], r["games"], r["winner"])
                _img = f"og/m/{r['id']}.png"
            except Exception as e:
                print("Imagem de partilha do jogo falhou:", r.get("id"), e)
        with open(path, "w", encoding="utf-8") as f:
            f.write(_shell(extras.match_title(r), extras.match_page(r, results, tr, tx) +
                           site_more.share_html(f"{SITE_BASE}/m/{r['id']}.html", f"{_pw['name']} beat {_pl['name']} {_sc} at {_tn}"),
                           tx, root="../", path=f"m/{r['id']}.html",
                           desc=f"{_pw['name']}{_rk(_pw)} beat {_pl['name']}{_rk(_pl)} {_sc} at {_tn}" +
                                (f", {r.get('round')}" if r.get("round") else "") + f" on {r.get('date', '')}. Full score, rankings and head-to-head.",
                           ld=_ml, image=_img))
        paths.append(path)
    # uma página por jogo a decorrer (/live/<id>.html); os que já acabaram reencaminham para /m/<id>.html
    ldir = os.path.join(out_dir, "live")
    os.makedirs(ldir, exist_ok=True)
    _live = extras.live_rows()
    _tslugs = {webapp.slugify(webapp.base_tournament(r.get("tournament", ""))) for r in results}
    for m_ in _live:
        _a, _b = m_["p1"]["name"], m_["p2"]["name"]
        _img = "og/default.png"
        try:
            og_match(os.path.join(og_dir, "live", f"{m_['id']}.png"), m_.get("tag", ""), m_.get("tournament", ""), m_.get("round", ""),
                     m_["p1"], m_["p2"], m_["games"], live=True)
            _img = f"og/live/{m_['id']}.png"
        except Exception as e:
            print("Imagem de partilha (ao vivo) falhou:", m_.get("id"), e)
        with open(os.path.join(ldir, f"{m_['id']}.html"), "w", encoding="utf-8") as f:
            f.write(_shell(f"{_a} vs {_b} live · {m_.get('tournament', '')} · Beyond100",
                           extras.live_page(m_, results, tr, tx, _tslugs) +
                           site_more.share_html(f"{SITE_BASE}/live/{m_['id']}.html", f"{_a} vs {_b} at {m_.get('tournament', '')}, follow it live", "Share this match", sub="Live score, updated through the match."),
                           tx, root="../", path=f"live/{m_['id']}.html", noindex=True, image=_img,
                           desc=f"{_a} vs {_b}, {m_.get('round', '')} at {m_.get('tournament', '')}: live score, rankings and road to this match."))
    _live_ids = {str(m_["id"]) for m_ in _live}
    _cut2 = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 3 * 86400))
    for r in results:
        if r.get("id") is None or str(r["id"]) in _live_ids or r.get("date", "") < _cut2 or r.get("winner") not in (1, 2):
            continue
        with open(os.path.join(ldir, f"{r['id']}.html"), "w", encoding="utf-8") as f:
            f.write(f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
                    f'<link rel="canonical" href="{SITE_BASE}/m/{r["id"]}.html"><meta http-equiv="refresh" content="0;url=/m/{r["id"]}.html">'
                    f'<title>Final score</title><a href="/m/{r["id"]}.html">Final score</a>')
    # uma página por jogador (singulares)
    pdir = os.path.join(out_dir, "p")
    os.makedirs(pdir, exist_ok=True)
    ranks_by_name = {v.get("name"): v for v in _load_json(RANKS_FILE, {}).values()}
    extras.PIDX = extras.players_index(results)
    extras.TSLUGS = {webapp.slugify(webapp.base_tournament(r.get("tournament", ""))) for r in results}
    for slug_p, e in list(extras.PIDX.items())[:3000]:
        if not slug_p:
            continue
        path = os.path.join(pdir, slug_p + ".html")
        _ms = e["matches"]
        _wins = sum(1 for i, r in _ms if r["winner"] == i)
        _last = max((r.get("date", "") for _, r in _ms), default="")
        _lt = next((webapp.base_tournament(r.get("tournament", "")) for _, r in sorted(_ms, key=lambda x: x[1].get("date", ""), reverse=True)), "")
        _rk = ((ranks_by_name.get(e["name"]) or {}).get("rank")) or e.get("rank")
        _h = extras.hist_entry(e["name"]) or {}
        try:
            _tp = extras._tape({"name": e["name"], "bd": e.get("bd")})
        except Exception:
            _tp = {}
        try:
            _nx = bool(extras.next_match_block(e["name"]))
        except Exception:
            _nx = False
        try:
            import espn_sync
            _ep = espn_sync.profile_for(e["name"])
        except Exception:
            _ep = {}
        # páginas muito pobres ficam fora do Google até haver mais dados (perfil do ESPN ou próximo jogo marcado já contam)
        _thin = len(_ms) < 2 and not _h and not _ep.get("n") and not _nx
        try:                                            # quem as pessoas procuram nunca fica fora do Google
            import reach
            if slug_p in reach.searched_slugs():
                _thin = False
        except Exception:
            pass
        _bits = [x for x in [f"age {_tp['age']}" if _tp.get("age") else "", f"{_tp['h'] / 100:.2f} m" if _tp.get("h") else "",
                             f"{_tp['hand'].lower()}-handed" if _tp.get("hand") else ""] if x]
        _desc = ((f"{e['name']} is ranked No. {_rk}" if _rk else f"{e['name']}") + (f" ({e['country']})" if e.get("country") else "")
                 + (f", {', '.join(_bits)}" if _bits else "")
                 + f": {_wins}-{len(_ms) - _wins} in the matches we tracked" + (f", last at {_lt} on {_last}" if _lt and _last else "")
                 + (". Next match, results" if _nx else ". Results") + ", ranking history and career stats.")
        _test = _title_test(slug_p, e["name"], _rk, _nx)              # 11/11/2026: teste de título nas páginas "Ninguém clica"
        if _test:
            _desc = _test[1] + " " + _desc
        _person = {"@context": "https://schema.org", "@type": "Person", "name": e["name"], "url": f"{SITE_BASE}/p/{slug_p}",
                   "jobTitle": "Professional tennis player", "description": _desc}
        if e.get("country"):
            _person["nationality"] = {"@type": "Country", "name": e["country"]}
        _bd = str((_h.get("bio") or {}).get("dob") or "")
        if len(_bd) >= 8 and _bd[:8].isdigit():
            _person["birthDate"] = f"{_bd[:4]}-{_bd[4:6]}-{_bd[6:8]}"
        elif _ep.get("bd"):
            _person["birthDate"] = _ep["bd"]
        if _tp.get("h"):
            _person["height"] = {"@type": "QuantitativeValue", "value": _tp["h"], "unitCode": "CMT"}
        _hd = _manual_handles().get(slug_p)              # só perfis confirmados à mão (sem pedidos à Wikidata durante o site)
        if _hd:
            _person["sameAs"] = [f"https://www.instagram.com/{_hd.lstrip('@')}/"]
        if os.path.exists(os.path.join(out_dir, "img", slug_p + ".jpg")):
            _person["image"] = f"{SITE_BASE}/img/big/{slug_p}.jpg"
        if _thin:
            NOINDEX.add("p/" + slug_p + ".html")
        LASTMOD["p/" + slug_p + ".html"] = _last
        with open(path, "w", encoding="utf-8") as f:
            _yr = (_last or time.strftime("%Y"))[:4]
            # título no formato que as pessoas pesquisam ("<nome> ranking"), com o número logo à vista (Search Console, 5/11/2026)
            _tt = (f"{e['name']} ranking {_yr}: No. {_rk}" if _rk else f"{e['name']} ranking {_yr}") + (" · results and next match" if _nx else " · results and stats")
            if _test:
                _tt = _test[0]
            f.write(_shell(_tt + " | Beyond100",
                           extras.player_page(e, tr, tx, ranks_by_name), tx,
                           root="../", path="p/" + slug_p + ".html", desc=_desc, noindex=_thin,
                           ld=[_person, _crumbs([("Players", "players.html"), (e["name"], "p/" + slug_p + ".html")])]))
        paths.append(path)
    # páginas extra: próxima semana, países, pesquisa
    try:
        import rising as _rising
        _rs = _rising.risers(results, datetime.date.today())
    except Exception:
        _rs = []
    _p = os.path.join(out_dir, "order-of-play.html")
    with open(_p, "w", encoding="utf-8") as f:
        f.write(_shell("Order of play: today's Challenger, ITF, ATP and WTA matches · Beyond100", extras.order_of_play_page(results), tx,
                       path="order-of-play.html", desc="Start times for today's and tomorrow's matches on the ATP Challenger, ITF, ATP and WTA tours, with live scores and results.",
                       ld=[_crumbs([("Order of play", "order-of-play.html")])] + extras.order_of_play_ld(SITE_BASE)))
    paths.append(_p)
    _p = os.path.join(out_dir, "next.html")
    with open(_p, "w", encoding="utf-8") as f:
        f.write(_shell("Next week on the Challenger, ITF and WTA tours · Beyond100", site_more.next_week_page(results, linkable, _rs), tx,
                       path="next.html", desc="The tournaments coming up next week on the ATP Challenger, ITF and WTA tours, and the players arriving in form.",
                       ld=[_crumbs([("Next week", "next.html")])]))
    paths.append(_p)
    _index = dict(list(extras.players_index(results).items())[:3000])
    _cp, _cidx = site_more.country_pages(_index, results, tr, tx)
    cdir = os.path.join(out_dir, "c")
    os.makedirs(cdir, exist_ok=True)
    for _c, (_t, _b, _d, _n, _lm) in _cp.items():
        _p = os.path.join(cdir, _c.lower() + ".html")
        with open(_p, "w", encoding="utf-8") as f:
            f.write(_shell(_t, _b, tx, root="../", path=f"c/{_c.lower()}.html", desc=_d,
                           ld=[_crumbs([("Countries", "countries.html"), (site_more.country_name(_c), f"c/{_c.lower()}.html")])]))
        if _lm:
            LASTMOD[f"c/{_c.lower()}.html"] = _lm
        paths.append(_p)
    _p = os.path.join(out_dir, "countries.html")
    with open(_p, "w", encoding="utf-8") as f:
        f.write(_shell("Tennis players by country · Beyond100", _cidx, tx, path="countries.html",
                       desc="Tennis players beyond the top 100 by country, with this week's results on the Challenger, ITF and WTA tours."))
    paths.append(_p)
    # Road to the Top 100, Power Ranking e Recordes da época
    import features
    _latest = {webapp.slugify(v.get("name", "")): v.get("rank") for v in _load_json(RANKS_FILE, {}).values()}
    for _fn, _title, _desc, _body in [
            ("road.html", "Road to the Top 100: players ranked 101 to 130 · Beyond100",
             "The tennis players knocking on the door of the top 100: rankings, moves and points to go, men and women.",
             lambda: features.road_page(features.road_official() or features.road(results, _load_json(RANKS_FILE, {})), linkable, site_more.flag)),
            ("power.html", "Power Ranking: best form outside the top 100 · Beyond100",
             "Our weekly ranking of the tennis players in the best form outside the top 100, from the last 14 days of Challenger, ITF and WTA results.",
             lambda: features.power_page(features.power(results, _latest), linkable, site_more.flag)),
            ("about.html", "About Beyond100: tennis and padel beyond the top 100",
             "What Beyond100 is, how the site updates, where the scores, rankings and photos come from, and how to reach us.",
             extras.about_page),
            ("records.html", f"Season records {datetime.date.today().year}: Challenger, ITF and WTA · Beyond100",
             "Most wins, titles, comebacks, tie-breaks and biggest upsets of the season beyond the top 100.",
             lambda: features.records_page(features.records(results), linkable, site_more.flag))]:
        try:
            _p = os.path.join(out_dir, _fn)
            with open(_p, "w", encoding="utf-8") as f:
                f.write(_shell(_title, _body(), tx, path=_fn, desc=_desc, ld=[_crumbs([(_title.split(":")[0].split(" · ")[0], _fn)])]))
            paths.append(_p)
        except Exception as e:
            print("Página", _fn, "falhou:", type(e).__name__, e)
    try:                                                      # 13/11/2026: páginas semanais "The week beyond the top 100" (SEO)
        import week_pages
        for _p, _lm in week_pages.make(out_dir, _shell, tx, _crumbs):
            paths.append(_p)
            LASTMOD[os.path.relpath(_p, out_dir).replace(os.sep, "/")] = _lm
    except Exception as e:
        print("Páginas semanais falharam:", type(e).__name__, e)
    with open(os.path.join(out_dir, "search.json"), "w", encoding="utf-8") as f:
        json.dump(site_more.search_index({k: v for k, v in _index.items() if ("p/" + k + ".html") not in NOINDEX}, sorted(groups)), f,
                  ensure_ascii=False, separators=(",", ":"))
    urls = [os.path.relpath(x, out_dir).replace(os.sep, "/") for x in paths]
    urls = ["" if u == "index.html" else (u[:-len("index.html")] if u.endswith("/index.html") else u) for u in urls]
    today = datetime.date.today().isoformat()
    urls = [u for u in urls if u not in NOINDEX]
    with open(os.path.join(out_dir, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            lm = (LASTMOD.get(u) or today)[:10]
            f.write(f"<url><loc>{SITE_BASE}/{html.escape(clean_url(u))}</loc><lastmod>{lm}</lastmod></url>\n")
        f.write("</urlset>\n")
    # páginas que mudaram hoje: o passo IndexNow avisa o Bing/Yandex/Seznam (o Google lê o sitemap)
    with open("indexnow_urls.json", "w", encoding="utf-8") as f:
        json.dump([f"{SITE_BASE}/{u}" for u in urls if (LASTMOD.get(u) or today)[:10] >= today or "/" not in u], f)
    with open(os.path.join(out_dir, INDEXNOW_KEY + ".txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)
    with open(os.path.join(out_dir, "404.html"), "w", encoding="utf-8") as f:
        f.write(_shell("Page not found · Beyond100", f'<section class="hero"><h1>Page not found</h1><p>This page moved or no longer exists. '
                       f'Matches stay online for 45 days; player and tournament pages stay while we track them.</p>'
                       f'<a class="btn" href="/results.html">Latest results</a><a class="btn ghost" href="/players.html">Players</a></section>',
                       tx, path="404.html", noindex=True))
    with open(os.path.join(out_dir, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nDisallow: /admin/\nDisallow: /admin-api/\nSitemap: {SITE_BASE}/sitemap.xml\nSitemap: {SITE_BASE}/padel/sitemap.xml\n")
    _adm = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin")       # página de gestão (protegida pelo Cloudflare Access)
    if os.path.isdir(_adm):
        shutil.copytree(_adm, os.path.join(out_dir, "admin"), dirs_exist_ok=True)
        with open(os.path.join(out_dir, "_headers"), "a", encoding="utf-8") as f:
            f.write("/admin/*\n  X-Robots-Tag: noindex, nofollow\n  Cache-Control: no-store\n")
    return paths


# ---------- notícias a partir de dados reais (nada é inventado) ----------
RANKS_FILE = "ranks.json"
def _env(name, default):
    v = os.environ.get(name)
    return default if v is None or not v.strip() else v


PHOTO_BONUS = float(_env("PHOTO_BONUS", "2"))          # bónus se o vencedor tem foto licenciada
NO_PHOTO_EXTRA = float(_env("NO_PHOTO_EXTRA", "1"))   # sem foto, o limiar sobe
UPSET_GAP = int(os.environ.get("UPSET_GAP", "80"))
UPSET_MAX_LOSER_RANK = int(_env("UPSET_MAX_LOSER_RANK", "250"))   # o derrotado tem de ser top 250 para contar como surpresa
TOUR_MIN_RANK = int(_env("TOUR_MIN_RANK", "50"))                     # no Tour, o vencedor tem de estar fora do top N (ranking > N)
POST_LEVELS = {x.strip() for x in _env("POST_LEVELS", "challenger,tour").lower().split(",") if x.strip()}   # níveis que geram post: challenger,tour,itf
REQUIRE_PHOTO = True   # 9/11/2026 (Afonso): sem foto boa do vencedor, não há post (fica só no site)                      # só publica se o vencedor tiver foto licenciada
MIN_ITF_TIER = int(_env("MIN_ITF_TIER", "60"))                      # ITF só é publicado a partir de W60/M60 (M15/M25/W35... ficam só no site)   # diferença mínima de ranking para ser "surpresa"
RISING_MAX_JUMP = 150                                 # saltos maiores são tratados como erro nos dados
RANK_MAX_AGE_D = 60                                   # só compara com rankings vistos nos últimos 60 dias


def _load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def update_ranks(m):
    """Guarda só (id, nome, país, ranking, data). Devolve eventos 'sobe para o top 100'."""
    ranks = _load_json(RANKS_FILE, {})
    now, today = time.time(), time.strftime("%Y-%m-%d", time.gmtime())
    events = []
    for k in ("p1", "p2"):
        p = (m.get("players") or {}).get(k) or {}
        pid, rank = p.get("id"), p.get("ranking")
        if pid is None or not isinstance(rank, int):
            continue
        prev = ranks.get(str(pid))
        if (prev and prev["rank"] > 100 and rank <= 100 and prev["rank"] - rank <= RISING_MAX_JUMP
                and now - prev["ts"] <= RANK_MAX_AGE_D * 86400):
            events.append({
                "headline": "Enters the top 100." if LANG == "en" else "Entra no top 100.",
                "player": p.get("name", ""), "country": p.get("country"),
                "rank_before": prev["rank"], "rank_now": rank,
                "context": (f"Up {prev['rank'] - rank} places since {prev['date']}" if LANG == "en"
                            else f"Sobe {prev['rank'] - rank} lugares desde {prev['date']}"),
            })
        rec = {"name": p.get("name"), "country": p.get("country"), "rank": rank, "date": today, "ts": now,
               "pts": p.get("ranking_points"), "mv": p.get("ranking_movement")}
        if prev and prev.get("rank") != rank:
            rec["prev"], rec["prev_date"] = prev["rank"], prev.get("date", "")
        elif prev and prev.get("prev"):
            rec["prev"], rec["prev_date"] = prev["prev"], prev.get("prev_date", "")
        ranks[str(pid)] = rec
    ranks = {k: v for k, v in ranks.items() if now - v["ts"] <= RETENTION_DAYS * 86400}
    with open(RANKS_FILE, "w", encoding="utf-8") as f:
        json.dump(ranks, f, ensure_ascii=False, indent=2)
    return events


def upset_event(m):
    """Surpresa: o vencedor tem ranking pelo menos UPSET_GAP lugares pior que o derrotado."""
    w = winner_index(m)
    sets = (m.get("score") or {}).get("sets") or [0, 0]
    if not w or max(sets) < 2:          # ignora desistências e walkovers
        return None
    pw, pl = m["players"]["p%d" % w], m["players"]["p%d" % (3 - w)]
    rw, rl = pw.get("ranking"), pl.get("ranking")
    if not (isinstance(rw, int) and isinstance(rl, int)) or rw - rl < UPSET_GAP or rl > UPSET_MAX_LOSER_RANK:
        return None
    games = (m.get("score") or {}).get("games") or [[], []]
    mine, other = games[w - 1], games[2 - w]
    gap = rw - rl
    return {
        "headline": (f"Beats a player ranked {gap} places higher." if LANG == "en"
                     else f"Vence um jogador {gap} lugares acima no ranking."),
        "winner": {"name": pw.get("name", ""), "rank": rw},
        "loser": {"name": pl.get("name", ""), "rank": rl},
        "score": "  ".join(f"{a}-{b}" for a, b in zip(mine, other)),
        "context": " · ".join(x for x in [round_pt(m.get("round")), m.get("tournament", "")] if x),
    }


GIANT_GAP = int(_env("GIANT_GAP", "50"))                  # surpresa gigante: o vencedor está pelo menos 50 lugares abaixo...
GIANT_VIEWS = int(_env("GIANT_VIEWS", "30000"))          # ...de um nome enorme (top 10 agora/na carreira, ou 30 mil+ visitas/mês na Wikipédia)


def giant_upset(m):
    """Surpresa gigante (decidido a 4/11/2026, Hijikata d. Djokovic): o derrotado é um nome muito conhecido e o vencedor está
    pelo menos GIANT_GAP lugares abaixo. Cartão com as caras dos dois. Devolve True/False."""
    w = winner_index(m)
    sets = (m.get("score") or {}).get("sets") or [0, 0]
    if not w or max(sets) < 2:
        return False
    pw, pl = m["players"]["p%d" % w], m["players"]["p%d" % (3 - w)]
    rw, rl = pw.get("ranking"), pl.get("ranking")
    if not (isinstance(rw, int) and isinstance(rl, int)) or rw - rl < GIANT_GAP:
        return False
    br = (extras.hist_entry(pl.get("name")) or {}).get("br")
    if rl <= 10 or (isinstance(br, int) and br <= 10):
        return True
    try:
        import reach
        return (reach.info(pl.get("name"), pl.get("birthday"), "tennis").get("views") or 0) >= GIANT_VIEWS
    except Exception:
        return False


POSTS_FILE = "posts.json"
POST_MIN_SCORE = float(_env("POST_MIN_SCORE", "4"))
STORY_PENALTY = float(_env("STORY_PENALTY", "3"))          # resultado sem história (sem final/meia/quarto/surpresa/viragem): -3
STORY_COMEBACK = float(_env("STORY_COMEBACK", "2"))        # viragem (perdeu o 1.º set e ganhou)
MAX_POSTS_PER_DAY = int(_env("MAX_POSTS_PER_DAY", "3"))
EXCEPTION_SCORE = float(_env("EXCEPTION_SCORE", "9"))     # com o limite diário cheio, só passam jogos desta pontuação ou mais
EXTRA_POSTS = int(_env("EXTRA_POSTS", "2"))               # e no máximo este número de posts extra por dia
QUEUE_BUFFER = int(_env("QUEUE_BUFFER", "3"))                # cartões a mais na fila, para o publisher poder escolher os melhores


def lisbon_day(ts=None):
    """Data (AAAA-MM-DD) em Lisboa para um instante (ou agora)."""
    from zoneinfo import ZoneInfo
    return datetime.datetime.fromtimestamp(ts if ts is not None else time.time(), ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d")


def interest(m):
    """Pontuação de interesse de um jogo terminado (só para escolher o que vale a pena publicar)."""
    import webapp
    sets = (m.get("score") or {}).get("sets") or [0, 0]
    w = winner_index(m)
    if not w or max(sets) < 2:                      # walkover / desistência: não publicar
        return 0.0, []
    score, why = 0.0, []
    if is_qual(m):                       # qualificação: só no site
        return 0.0, []
    lv = int(_priority(m))                          # a parte decimal é só desempate
    score += {0: 3, 1: 2, 2: 0.5, 3: 0}[lv]
    if lv <= 1:
        why.append({0: "tour", 1: "challenger"}[lv])
    rr = webapp._round_rank(m.get("round"))
    if rr in (0, 1, 2):
        score += {0: 3, 1: 2, 2: 1}[rr]
        why.append({0: "final", 1: "semifinal", 2: "quarterfinal"}[rr])
    ev = upset_event(m)
    if ev or giant_upset(m):
        score += 3
        why.append("upset")
        if giant_upset(m):
            why.append("giant")
    ranks = [(m["players"][k].get("ranking")) for k in ("p1", "p2")]
    best = min([r for r in ranks if isinstance(r, int)] or [9999])
    if best <= 100:
        score += 2
        why.append("top100")
        if best <= 50:
            score += 1
    elif best <= 150:                                # zona 100-150: perto do top 100, mais provável ter foto
        score += 1
    g = (m.get("score") or {}).get("games") or [[], []]
    if g[0] and len(g[0]) == len(g[1]):
        mine, other = (g[0], g[1]) if w == 1 else (g[1], g[0])
        if len(mine) >= 3 and mine[0] < other[0] and sum(a > b for a, b in zip(mine, other)) > sum(a < b for a, b in zip(mine, other)):
            # 5/11/2026: nas primeiras rondas de Challenger/ITF a viragem é comum (estava a encher as manhãs): +1 e continua "sem história";
            # no ATP/WTA e dos quartos em diante conta como história, como antes
            if lv == 0 or rr in (0, 1, 2):
                score += STORY_COMEBACK
                why.append("comeback")
            else:
                score += float(_env("STORY_COMEBACK_EARLY", "1"))
                why.append("comeback-early")
    # posts com história primeiro (decidido a 2/11/2026, a partir das estatísticas do Instagram: títulos, viragens e surpresas
    # têm 2-15x mais alcance do que um resultado simples). Vitória de 1.ª/2.ª ronda sem história fica só no site.
    if not set(why) & {"final", "semifinal", "quarterfinal", "upset", "comeback"}:
        score -= STORY_PENALTY
        why.append("no-story")
    try:                                              # alcance: jogadores mais conhecidos / identificáveis / promessas sobem na fila
        if os.environ.get("REACH_ENABLED", "1") != "0":
            import reach
            bs = []
            for k in ("p1", "p2"):
                p = m["players"][k]
                tp = extras._tape({"name": p.get("name"), "bd": p.get("birthday")})
                b, bw = reach.bonus(p.get("name"), p.get("birthday"), "tennis", handle_of(p.get("name"), p.get("birthday")),
                                    (extras.hist_entry(p.get("name")) or {}).get("br"), tp.get("age"))
                bs.append((b * (1 if k == "p%d" % w else 0.75), bw))      # ganhar a alguém famoso também dá alcance
            b, bw = max(bs, key=lambda x: x[0])
            if b > 0:
                score += b
                why.append("reach:" + "+".join(bw))
                m["_reach_pts"] = round(b, 2)             # o publisher precisa dele para a regra da manhã
    except Exception as e:
        print("Alcance: erro", type(e).__name__, e)
    return score, why


HANDLES_FILE = "handles.json"


def handle_of(name, birthday=None):
    """Perfil de Instagram: 1.º a lista verificada à mão (handles.json), 2.º a Wikidata (só com data de nascimento a bater certo).
    AUTO_HANDLES=0 desliga a Wikidata. Sem perfil = sem menção."""
    import fetch_photos
    data = _load_json(HANDLES_FILE, {})
    key = fetch_photos.slug(name or "")
    for k, v in data.items():
        if k.startswith("_"):
            continue
        h = (v or "").strip()
        if fetch_photos.slug(k) == key and re.fullmatch(r"@[A-Za-z0-9._]{1,30}", h):
            return h
    if os.environ.get("AUTO_HANDLES") != "0" and os.environ.get("FETCH_PHOTOS") == "1":
        try:
            return fetch_photos.fetch_handle(name, birthday, PHOTO_DIR)
        except Exception:
            return None
    return None


TOURN_HANDLES_FILE = "handles_torneios.json"


def tournament_handle(tournament):
    """Perfil de Instagram do torneio (lista manual handles_torneios.json: nome do torneio -> @perfil). Casa por nome sem acentos/maiúsculas."""
    import fetch_photos, webapp
    key = fetch_photos.slug(webapp.base_tournament(tournament or ""))
    for k, v in _load_json(TOURN_HANDLES_FILE, {}).items():
        h = (v or "").strip()
        if k.startswith("_") or not re.fullmatch(r"@[A-Za-z0-9._]{1,30}", h):
            continue
        ks = fetch_photos.slug(k)
        if "challenger" in key.split("-") and "challenger" not in ks.split("-"):
            continue                                                         # torneio do Tour não serve para um Challenger na mesma cidade
        if ks and (ks == key or set(ks.split("-")) <= set(key.split("-"))):      # todas as palavras da chave no nome (ex.: "ATP Basel")
            return h
    return None


def _who(p):
    fp, credit = find_photo(p)
    return {"name": p.get("name", ""), "rank": p.get("ranking"), "photo": fp, "credit": credit,
            "handle": handle_of(p.get("name", ""), p.get("birthday"))}


def _headline(why, ev):
    """Frase curta para o cartão, só a partir de factos verificados (sem inventar)."""
    if ev:
        return ev["headline"]
    if "final" in why:
        return "Wins the title." if LANG == "en" else "Vence o torneio."
    if "comeback" in why:
        return "Down a set, wins in three." if LANG == "en" else "Perdeu o 1.º set e vira."
    if "semifinal" in why:
        return "Into the final." if LANG == "en" else "Está na final."
    if "quarterfinal" in why:
        return "Into the semifinals." if LANG == "en" else "Está nas meias-finais."
    return ""


def _dup_final(m):
    """Um torneio só tem uma final por dia; várias 'finais' = rondas finais de qualificação mal classificadas."""
    import webapp
    if webapp._round_rank(m.get("round")) != 0:
        return False
    day = (m.get("updated_at") or "")[:10] or time.strftime("%Y-%m-%d", time.gmtime())
    t = m.get("tournament", "")
    for x in load_results():
        if (x.get("id") != m.get("id") and x.get("tournament") == t and x.get("date") == day
                and webapp._round_rank(x.get("round")) == 0 and webapp.classify(x)[1] == "singles"
                and x.get("tour") == m.get("tour") and x.get("gender") == m.get("gender")):
            return True
    return False


def _heal(results):
    """Corrige jogos já guardados que eram qualificação com nome de quadro principal:
    - torneio com 'qualif' ou 'playoff' no nome;
    - mais de 1 'final' singular no mesmo torneio/dia (só há uma final por torneio);
    - mais de 2 meias-finais singulares no mesmo torneio em 2 dias seguidos;
    - nos torneios com várias 'finais' num dia, as meias-finais/quartos dos 3 dias anteriores também são qualificação;
    - ids marcados à mão em qualifying_ids.json."""
    import webapp
    manual = {str(i) for i in _load_json("qualifying_ids.json", []) if not isinstance(i, str) or not i.startswith("_")}

    def mark(r):
        r["q"] = True
        if webapp._round_rank(r.get("round")) <= 2:
            r["round"] = "Qualifying " + (r.get("round") or "").lower().replace("quarterfinals", "quarter-finals").replace("semifinals", "semi-finals")

    def day_n(d, n):
        try:
            return time.strftime("%Y-%m-%d", time.gmtime(time.mktime(time.strptime(d, "%Y-%m-%d")) + n * 86400))
        except Exception:
            return d

    sing = [r for r in results if webapp.classify(r)[1] == "singles"]
    for r in sing:
        nm = (r.get("tournament") or "").lower()
        if str(r.get("id")) in manual or "qualif" in nm or "playoff" in nm:
            mark(r)
    key = lambda r: (r.get("tournament"), r.get("gender"))
    by_t = {}
    for r in sing:        # a API marcou como qualificação e não há jogos de quadro principal anteriores deste torneio
        if r.get("fq") and not r.get("q") and webapp._round_rank(r.get("round")) <= 2:
            prev = [x for x in sing if x.get("tournament") == r.get("tournament") and x.get("gender") == r.get("gender")
                    and not x.get("q") and x.get("date", "") < r.get("date", "") and webapp._round_rank(x.get("round")) > webapp._round_rank(r.get("round"))
                    and x.get("date", "") >= day_n(r.get("date", ""), -8)]
            if not prev:
                mark(r)
    for r in sing:
        by_t.setdefault(key(r), []).append(r)
    for rows in by_t.values():
        finals = [r for r in rows if not r.get("q") and webapp._round_rank(r.get("round")) == 0]
        by_day = {}
        for r in finals:
            by_day.setdefault(r.get("date"), []).append(r)
        qual_days = [d for d, rs in by_day.items() if len(rs) > 1]
        for d in qual_days:
            for r in by_day[d]:
                mark(r)
            lo = day_n(d, -3)
            for r in rows:
                if not r.get("q") and lo <= r.get("date", "") <= d and webapp._round_rank(r.get("round")) in (1, 2):
                    mark(r)
        sfs = [r for r in rows if not r.get("q") and webapp._round_rank(r.get("round")) == 1]
        for r in sfs:
            near = [x for x in sfs if abs((time.mktime(time.strptime(x["date"], "%Y-%m-%d")) - time.mktime(time.strptime(r["date"], "%Y-%m-%d"))) / 86400) <= 1]
            if len(near) > 2:
                for x in near:
                    mark(x)
    return results


def maybe_post(m, out_dir, force=False):
    """Se o jogo for suficientemente interessante (e não houver já posts a mais hoje), gera o cartão com foto."""
    from photo_cards import render_match_photo
    from captions import save_caption
    import webapp
    import re as _re
    print(f"Jogo {m.get('id')}: ronda='{m.get('round')}' código={m.get('round_code')} marcado_qualificação={m.get('is_qualifying')} -> qualificação={is_qual(m)}")
    _g, _k, _lv, _tag = webapp.classify(webapp.api_view(m))
    if _lv not in POST_LEVELS and not force:
        print(f"Jogo {m.get('id')}: nível '{_lv}' não gera posts (POST_LEVELS={','.join(sorted(POST_LEVELS))}), fica só no site.")
        return None
    if _lv == "tour" and not force:
        _w0 = winner_index(m)
        _rk = ((m.get("players") or {}).get("p%d" % _w0) or {}).get("ranking") if _w0 else None
        if isinstance(_rk, int) and _rk <= TOUR_MIN_RANK:
            print(f"Jogo {m.get('id')}: Tour, vencedor ranking {_rk} (<= {TOUR_MIN_RANK}), fica só no site.")
            return None
    if _lv == "itf" and not force:
        _n = _re.search(r"(\d+)", _tag or "")
        if not _n or int(_n.group(1)) < MIN_ITF_TIER:
            print(f"Jogo {m.get('id')}: {_tag or 'ITF'} abaixo de {MIN_ITF_TIER}, fica só no site.")
            return None
    if _dup_final(m) and not force:
        print(f"Jogo {m.get('id')}: 'final' duvidosa (outras finais no mesmo torneio e dia), fica só no site.")
        return None
    score, why = interest(m)
    # prioridade a jogos COM imagem: com foto licenciada ganha bónus; sem foto precisa de mais interesse
    _w = winner_index(m)
    has_photo = bool(_w and find_post_photo(m["players"]["p%d" % _w], dry=True)[0])   # 9/11/2026: só conta foto que passe o filtro de qualidade
    score += PHOTO_BONUS if has_photo else 0
    if has_photo and "final" not in why:              # 5/11/2026: a mesma foto em posts seguidos estraga o feed (finais/títulos: sem castigo). Se a melhor opção
        try:                                          # (a usada há mais tempo) saiu há pouco, é porque não há outra: perde pontos
            _age = (time.time() - find_post_photo(m["players"]["p%d" % _w], dry=True)[2]) / 86400
            if _age < PHOTO_REPEAT_DAYS:                  # 9/11/2026 (Afonso): foto repetida há pouco -> não publica (finais sim)
                print(f"Jogo {m.get('id')}: a única foto boa do vencedor saiu há {_age:.1f} dias, não publica (só finais repetem).")
                return None
        except Exception as e:
            print("Foto repetida: erro", type(e).__name__)
    if REQUIRE_PHOTO and not has_photo:
        print(f"Jogo {m.get('id')}: sem foto licenciada do vencedor, fica só no site.")
        return None
    need = POST_MIN_SCORE + (0 if has_photo else NO_PHOTO_EXTRA)
    if score < need and not force:
        print(f"Jogo {m.get('id')}: interesse {score:g} (< {need:g}{'' if has_photo else ', sem foto'}), fica só no site.")
        return None
    today = time.strftime("%Y-%m-%d", time.gmtime())
    posts = _load_json(POSTS_FILE, {})
    _bad = {x.get("id") for x in _heal(load_results()) if x.get("q")}       # posts de qualificação (publicados por engano) não contam para o limite
    # Os cartões são feitos à medida que os jogos acabam e ficam numa fila; o publisher escolhe os melhores e só publica
    # entre SEND_FROM e SEND_TO (hora de Lisboa). Aqui só se limita quantos se fazem por dia (para não gastar legendas à toa).
    _lday = lisbon_day()
    def _day_of(day_key, e):                      # dia de Lisboa em que o cartão foi feito (posts antigos sem "created": o dia da fila)
        return lisbon_day(e["created"]) if e.get("created") else day_key
    n_today = sum(1 for k, v in posts.items() for e in v
                  if str(e.get("id")).isdigit() and e.get("id") not in _bad and _day_of(k, e) == _lday)
    _cap = MAX_POSTS_PER_DAY + EXTRA_POSTS + QUEUE_BUFFER
    if n_today >= _cap + 2 and not force:
        print(f"Jogo {m.get('id')}: interesse {score:g}, mas já há {n_today} cartões hoje na fila (máximo).")
        return None
    _men_first = (os.environ.get("MEN_FIRST") or "1").strip() != "0"
    if n_today >= _cap and score < EXCEPTION_SCORE and not force and not (_men_first and _g == "men"):
        print(f"Jogo {m.get('id')}: interesse {score:g}, já há {n_today} cartões hoje na fila (só entram {EXCEPTION_SCORE:g}+).")
        return None
    w = winner_index(m)
    pw, pl = m["players"]["p%d" % w], m["players"]["p%d" % (3 - w)]
    g = (m.get("score") or {}).get("games") or [[], []]
    sets = list(zip(g[w - 1], g[2 - w]))
    ev = upset_event(m)
    _, _, _, tag = webapp.classify(webapp.api_view(m))
    _wd = _who(pw)
    _fp, _cr = find_post_photo(pw)                   # alterna as fotos do vencedor de post para post
    if _fp:
        _wd.update(photo=_fp, credit=_cr)
    d = {"winner": _wd, "loser": _who(pl), "sets": sets,
         "tournament": m.get("tournament", ""), "round": round_pt(m.get("round")),
         "level": tag.upper(), "tag": "UPSET" if ev else "", "headline": _headline(why, ev)}
    try:                                              # vencedor com 20 anos ou menos: a idade entra no título do cartão ("Into the final. At 17.")
        _ag = extras._tape({"name": pw.get("name"), "bd": pw.get("birthday")}).get("age")
        if isinstance(_ag, int) and 14 <= _ag <= int(os.environ.get("AGE_HEADLINE_MAX") or "20"):
            d["headline"] = (d["headline"] + " " if d["headline"] else "") + (f"At {_ag}." if d["headline"] else f"At just {_ag}.")
    except Exception as e:
        print("Idade no cartão: erro", e)
    pdir = os.path.join(out_dir, "post")
    os.makedirs(pdir, exist_ok=True)
    _facts = dict(slim(m), reasons=why)
    _facts.update(_past_context(m, w))
    d["style"] = _env("RESULT_STYLE", "C")   # 9/11/2026: um só modelo para resultados (C = moderno, placar em vidro); títulos: campeão; surpresa gigante: o seu
    _title = "final" in why and not ev and bool(_wd.get("photo"))
    if _title and _env("TITLE_STYLE", "3") in ("1", "2", "3"):  # títulos: sempre o painel lateral com a foto grande (o post da Harriet Dart: 3,9 mil visualizações)
        d["style"] = _env("TITLE_STYLE", "3")
    if d["style"] in ("2", "3", "C"):                          # desenhos novos: data, etiqueta e frase do jogo
        try:                                                      # data do jogo (não a do dia em que o cartão é feito)
            d["date"] = datetime.date.fromisoformat((m.get("updated_at") or "")[:10]).strftime("%d %b %Y").upper()
        except ValueError:
            d["date"] = time.strftime("%d %b %Y", time.gmtime()).upper()
        d["kicker"] = "UPSET" if ev else ("TITLE" if "final" in why else "WIN")
        d["round"] = d.get("round") or ""
        from captions import card_headline                       # 9/11/2026: IA sim, mas a soar a pessoa (sem "crown", "seizes"...); se falhar, frase fixa
        d["edit_head"] = card_headline(_facts) or (d.get("headline") or "").rstrip(".") or None
    png = None
    _card_style = None
    if "giant" in why and _wd.get("photo"):                     # surpresa gigante: as caras dos dois (derrotado a P&B)
        _ld = _who(pl)
        _lfp, _lcr = find_post_photo(pl)
        if _lfp:
            _ld.update(photo=_lfp, credit=_lcr)
        if _ld.get("photo"):
            import upset_card
            _last = (pl.get("name") or "").split()[-1] if pl.get("name") else ""
            dg = dict(d, loser=_ld, level=tag.upper(),
                      headline=(f"Down a set, still beat {_last}." if "comeback" in why else f"Beat {_last}.") if _last else d.get("headline"))
            if _env("RESULT_STYLE", "C") == "C":                  # 9/11/2026: surpresa gigante = modelo A (grafismo de TV + quem caiu)
                import modern_cards
                png = modern_cards.card_a({"sport": "tennis", "kicker": "GIANT UPSET", "level": tag.upper(), "tournament": d["tournament"],
                                           "round": d["round"], "date": d.get("date"),
                                           "winners": [{"name": pw.get("name"), "rank": pw.get("ranking"), "country": (pw.get("country") or "").upper()}],
                                           "losers": [{"name": pl.get("name"), "rank": pl.get("ranking"), "country": (pl.get("country") or "").upper()}],
                                           "sets": sets, "photo": _wd["photo"], "credit": __import__("photo_cards").credit_join(_wd.get("credit"), _ld.get("credit")),
                                           "loser_photo": _ld["photo"], "line": (dg.get("headline") or "").rstrip(".")}, os.path.join(pdir, f"final-{m.get('id')}.png"))
                _card_style = "A"
            else:
                png = upset_card.render_giant_upset(dg, os.path.join(pdir, f"final-{m.get('id')}.png"), _env("GIANT_STYLE", "C"))
            print(f"Jogo {m.get('id')}: surpresa gigante, cartão com os dois jogadores.")
    if not png and _title and _env("CHAMPION_CARD", "1") != "0":   # 9/11/2026: post próprio para campeões (foto, final e caminho até ao título)
        try:
            png = _champion_card(m, pw, pl, _wd, sets, tag, os.path.join(pdir, f"final-{m.get('id')}.png"))
            _card_style = "B" if png and _env("RESULT_STYLE", "C") == "C" else None
        except Exception as e:
            print("Cartão de campeão falhou:", type(e).__name__, e)
    _variants = []
    if not png:
        png = render_match_photo(d, os.path.join(pdir, f"final-{m.get('id')}.png"))
        try:
            import photo_cards
            _variants = photo_cards.render_variants(d, png)
        except Exception as e:
            print("Variantes do cartão falharam:", type(e).__name__, e)
    _facts["_interest"] = score
    _rw, _rl = pw.get("ranking"), pl.get("ranking")
    if isinstance(_rw, int):
        _facts["rank_winner"] = _rw
    if isinstance(_rl, int):
        _facts["rank_loser"] = _rl
    if isinstance(_rw, int) and isinstance(_rl, int) and _rw > _rl:
        _facts["ranking_gap"] = _rw - _rl
    from captions import save_pending
    save_pending(png, "final", _facts, mention=d["winner"].get("handle"), tournament=tournament_handle(m.get("tournament")))
    posts.setdefault(today, []).append({"id": m.get("id"), "score": score, "reach_pts": m.get("_reach_pts", 0), "reasons": why, "file": os.path.basename(png),
                                        "gender": _g, "created": time.time(), **({"alts": _variants} if _variants else {}), **({"style": _card_style} if _card_style else {})})
    keep = sorted(posts)[-14:]
    posts = {k: posts[k] for k in keep}
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"Post: {png} (interesse {score:g}: {', '.join(why)})")
    return png


PREVIEW_ENABLED = _env("PREVIEW_ENABLED", "1").strip().lower() in ("1", "true", "yes", "on")
PREVIEW_MAX_PER_DAY = int(_env("PREVIEW_MAX_PER_DAY", "1"))


def preview_finals(out_dir):
    """Antevisão de finais ('Who wins?'): usa os próximos jogos já guardados (sem gastar pedidos à API).
    Só finais de singulares (Tour/Challenger) marcadas para as próximas 18 h, com pelo menos uma foto licenciada.
    Não conta para o limite de posts de resultados. Desliga-se com PREVIEW_ENABLED=0."""
    import webapp
    from captions import save_caption
    from photo_cards import render_preview, render_preview_b
    if not PREVIEW_ENABLED:
        print("Antevisões: desligadas (PREVIEW_ENABLED=0).")
        return []
    today = time.strftime("%Y-%m-%d", time.gmtime())
    posts = _load_json(POSTS_FILE, {})
    done = {str(e.get("id")) for v in posts.values() for e in v}
    n_today = len([e for e in posts.get(today, []) if str(e.get("id")).startswith("preview-")])
    if n_today >= PREVIEW_MAX_PER_DAY:
        print(f"Antevisões: já há {n_today} hoje.")
        return []
    now = time.time()
    _res = load_results()
    finished = {str(x.get("id")) for x in _res}
    # só finais com pelo menos um jogador que tenha aparecido nos nossos posts dos últimos 7 dias (continuidade da história)
    _byid = {str(x.get("id")): x for x in _res}
    featured = set()
    for v in posts.values():
        for e in v:
            if not e.get("sent") or e.get("skipped") or not e.get("sent_at"):
                continue
            try:
                _ts = calendar.timegm(time.strptime(e["sent_at"], "%Y-%m-%d %H:%M"))
            except ValueError:
                continue
            if now - _ts > 7 * 86400:
                continue
            _r = _byid.get(str(e.get("id")))
            if _r:
                featured |= {webapp.slugify(_r["p1"]["name"]), webapp.slugify(_r["p2"]["name"])}
    cands = []
    for u in _load_json(UPCOMING_FILE, {}).get("matches", []):
        if webapp._round_rank(u.get("round")) != 0 or str(u.get("id")) in finished or f"preview-{u.get('id')}" in done:
            continue
        t = u.get("t") or ""
        try:
            ts = calendar.timegm(time.strptime(t[:16], "%Y-%m-%dT%H:%M"))
        except ValueError:
            continue
        if not (now - 1800 < ts < now + 18 * 3600):        # a começar nas próximas 18 h (ou há menos de 30 min)
            continue
        if not ({webapp.slugify(u["p1"]["name"]), webapp.slugify(u["p2"]["name"])} & featured):
            print(f"Antevisão {u['p1']['name']} vs {u['p2']['name']}: nenhum dos dois apareceu nos nossos posts desta semana, salto.")
            continue
        r = {"tournament": u.get("tp") or "", "gender": u.get("gender"), "tour": u.get("tour"), "date": t[:10],
             "p1": dict(u["p1"]), "p2": dict(u["p2"])}
        try:
            _, _, level, tag = webapp.classify(r)
        except Exception:
            level, tag = "", ""
        ranks = [p.get("rank") for p in (u["p1"], u["p2"])]
        prio = (0 if level == "tour" else 1, sum(x if isinstance(x, int) and x > 0 else 999 for x in ranks))
        cands.append((prio, ts, u, tag))
    for prio, ts, u, tag in sorted(cands, key=lambda c: c[0]):
        who = {}
        for k in ("p1", "p2"):
            fp, credit = find_post_photo(u[k])
            who[k] = {"name": u[k]["name"], "rank": u[k].get("rank"), "photo": fp, "credit": credit,
                      "handle": handle_of(u[k]["name"])}
        if not (who["p1"]["photo"] and who["p2"]["photo"]):
            print(f"Antevisão {u['p1']['name']} vs {u['p2']['name']}: falta foto licenciada de um dos jogadores, salto.")
            continue
        from captions import head_to_head
        h2h = head_to_head({"name": u["p1"]["name"], "country": u["p1"].get("country")},
                           {"name": u["p2"]["name"], "country": u["p2"].get("country")}, u.get("gender"))
        tname = re.sub(r"^(ATP|WTA)\s+", "", u.get("tp") or "")
        hhmm = time.strftime("%H:%M", time.gmtime(ts))
        day = "TODAY" if time.strftime("%Y-%m-%d", time.gmtime(ts)) == today else "TOMORROW"
        pid = f"preview-{u.get('id')}"
        pdir = os.path.join(out_dir, "post")
        os.makedirs(pdir, exist_ok=True)
        n_prev = sum(1 for v in posts.values() for x in v if str(x.get("id")).startswith("preview-"))
        render = render_preview          # 9/11/2026: só o desenho A (o B, em faixas, cortava as caras e ficava mal)
        png = render({"p1": who["p1"], "p2": who["p2"], "tournament": tname, "round": "Final",
                              "level": (tag or "").upper(), "when": f"{day} · {hhmm} UTC", "h2h": h2h}, os.path.join(pdir, pid + ".png"))
        facts = {"tournament": tname, "round": "Final", "level": tag, "starts_utc": f"{day.lower()} {hhmm} UTC",
                 "player_1": {"name": u["p1"]["name"], "country": u["p1"].get("country"), "ranking": u["p1"].get("rank")},
                 "player_2": {"name": u["p2"]["name"], "country": u["p2"].get("country"), "ranking": u["p2"].get("rank")}}
        if h2h:
            a_, b_ = h2h["p1_wins"], h2h["p2_wins"]
            lead = (f"{u['p1']['name']} leads {a_}-{b_}" if a_ > b_ else f"{u['p2']['name']} leads {b_}-{a_}" if b_ > a_
                    else (f"level at {a_}-{b_}" if a_ else "first career meeting"))
            facts["head_to_head"] = f"{lead} (official {h2h['source_name']} record)"
        tags = [h for h in (who["p1"]["handle"], who["p2"]["handle"]) if h]
        save_caption(png, "preview", facts, mention=" ".join(tags) or None, tournament=tournament_handle(u.get("tp")))
        posts.setdefault(today, []).append({"id": pid, "score": 0, "reasons": ["preview"], "file": os.path.basename(png)})
        with open(POSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
        print(f"Antevisão: {png} ({u['p1']['name']} vs {u['p2']['name']}, {tname})")
        return [png]
    print(f"Antevisões: {len(cands)} finais nas próximas 18 h, nenhuma publicada.")
    return []


def rising_cards(m, out_dir):
    """Notícia 'entra no top 100' (foto + número do ranking). Vai para out/post/."""
    from photo_cards import render_rank_news
    from captions import save_caption
    import webapp
    events = update_ranks(m)
    if not events:
        return []
    pdir = os.path.join(out_dir, "post")
    os.makedirs(pdir, exist_ok=True)
    paths = []
    for i, e in enumerate(events):
        pl = next((((m.get("players") or {}).get(k) or {}) for k in ("p1", "p2")
                   if ((m.get("players") or {}).get(k) or {}).get("name") == e["player"]), {"name": e["player"]})
        fp, credit = find_photo(pl)
        if REQUIRE_PHOTO and not fp:
            print(f"Notícia de ranking de {e['player']}: sem foto licenciada, não é publicada.")
            continue
        women = webapp.classify(webapp.api_view(m))[0] == "women"
        d = {"player": e["player"], "rank_now": e["rank_now"], "rank_before": e["rank_before"],
             "system": "WTA" if women else "ATP", "headline": e["headline"].rstrip("."),
             "context": e["context"], "photo": fp, "credit": credit}
        png = render_rank_news(d, os.path.join(pdir, f"news-rising-{m.get('id')}-{i}.png"))
        save_caption(png, "rising", e)
        paths.append(png)
    return paths


def upset_cards(m, out_dir):
    return []          # as surpresas agora são um jogo importante (ver maybe_post), com a etiqueta UPSET


def paced_ok():
    """Execuções da meia hora: só gastam 1 pedido se o consumo do dia estiver abaixo do ritmo (quota a diminuir ao longo do dia, com reserva)."""
    frac = ((time.time() / 3600 - QUOTA_RESET_UTC) % 24) / 24
    return quota_used() <= frac * (API_DAILY_LIMIT - QUOTA_RESERVE)


def run_results(out_dir, max_checks):
    import requests
    now = time.time()
    state = {k: t for k, t in load_state().items() if now - t < TRACK_MAX_AGE_H * 3600}
    prio, meta = {}, {}
    if not state:
        save_state(state)
        print("Sem jogos em acompanhamento. Corre primeiro com --live.")
        return
    os.makedirs(out_dir, exist_ok=True)
    checks = 0
    try:
        prio = load_prio()
        meta = load_meta()
        for mid in sorted(state, key=lambda k: (prio.get(k, 3), state[k])):     # Tour e Challenger primeiro
            if now - state[mid] < MIN_AGE_BEFORE_CHECK_S:
                continue                      # jogo acompanhado há pouco: é improvável que já tenha acabado
            if ESPN_ON and espn_candidate(meta.get(mid)):
                hit = None
                try:
                    import espn
                    pl = meta[mid].get("players") or {}
                    hit = espn.lookup(pl["p1"]["name"], pl["p2"]["name"])
                except Exception as e:
                    print(f"Jogo {mid}: ESPN com erro ({type(e).__name__}), vai pela API.")
                if hit and hit["clean"]:
                    m = espn.as_completed(meta[mid], hit)
                    if hit.get("tb"):
                        m["tb"] = hit["tb"]
                    print(f"Jogo {mid}: confirmado pelo ESPN (sem gastar pedidos).")
                    _count_free()
                    add_result(m)
                    maybe_post(m, out_dir)
                    del state[mid]
                    continue
                if hit and not hit["done"] and now - state[mid] < 4 * 3600:      # 4 h sem fecho no ESPN: confirma pela API
                    print(f"Jogo {mid}: ainda a decorrer segundo o ESPN ({hit['status']}), sem gastar pedidos.")
                    _count_free()
                    state[mid] = state.pop(mid)
                    continue
                # não encontrado, desistência/w.o. ou dados estranhos: confirma pela API (método antigo)
            if checks >= max_checks:
                if max_checks == 0:           # modo rápido (só ESPN): os outros jogos ficam para a execução normal
                    continue
                print(f"Limite de {max_checks} consultas atingido (poupa a quota diária).")
                break
            checks += 1
            try:
                m = fetch_match(mid)
            except requests.exceptions.HTTPError as e:
                code = e.response.status_code if e.response is not None else None
                if code in (404, 410):        # jogo removido/cancelado na API: deixa de ser acompanhado
                    print(f"Jogo {mid}: já não existe na API ({code}), removido do acompanhamento.")
                    del state[mid]
                    continue
                if code == 429:               # quota esgotada: pára e guarda o que já se sabe
                    print("Quota da API esgotada (429): a parar por agora.")
                    break
                print(f"Jogo {mid}: erro {code} da API, fica para a próxima.")
                state[mid] = state.pop(mid)
                continue
            except requests.exceptions.RequestException as e:
                print(f"Jogo {mid}: erro de rede ({type(e).__name__}), fica para a próxima.")
                state[mid] = state.pop(mid)
                continue
            if m.get("status") == "completed":
                add_result(m)                 # vai sempre para o site
                maybe_post(m, out_dir)        # só os mais interessantes geram cartão para o Instagram
                del state[mid]
            else:
                print(f"Jogo {mid}: ainda não terminou (estado: {m.get('status')}).")
                state[mid] = state.pop(mid)   # vai para o fim da fila: os outros jogos também são verificados
    finally:
        save_state(state)                     # mesmo com erro inesperado, o progresso não se perde
        save_prio({k: v for k, v in prio.items() if k in state})
        save_meta(meta, state)


def is_doubles_match(m):
    """Pares (a quota gratuita é pequena: só acompanhamos singulares)."""
    names = [((m.get("players") or {}).get(k) or {}).get("name", "") for k in ("p1", "p2")]
    return "DOUBLES" in (m.get("tournament") or "").upper() or any(" / " in n for n in names)


def _main_draw_underway(m):
    """True se já há jogos de quadro principal (rondas anteriores, não qualificação) deste torneio guardados em dias anteriores."""
    import webapp
    t, day = m.get("tournament", ""), (m.get("updated_at") or "")[:10] or time.strftime("%Y-%m-%d", time.gmtime())
    for x in load_results():
        if (x.get("tournament") == t and x.get("id") != m.get("id") and not x.get("q") and x.get("date", "") < day
                and x.get("date", "") >= time.strftime("%Y-%m-%d", time.gmtime(time.time() - 10 * 86400))
                and webapp._round_rank(x.get("round")) > 0):
            return True
    return False


def _qual_context(m):
    """Final/meia/quartos de um torneio que, no mesmo dia (±1), já tem jogos de qualificação guardados, sem a ronda anterior de quadro
    principal (final -> meia-final; meia -> quartos) jogada em dia anterior: é mais uma ronda de qualificação."""
    import webapp
    rk = webapp._round_rank(m.get("round"))
    if rk > 2:
        return False
    t, g = m.get("tournament", ""), m.get("gender")
    day = (m.get("updated_at") or "")[:10] or time.strftime("%Y-%m-%d", time.gmtime())

    def gap(d):
        try:
            return (time.mktime(time.strptime(day, "%Y-%m-%d")) - time.mktime(time.strptime(d, "%Y-%m-%d"))) / 86400
        except Exception:
            return 99
    rows = [x for x in load_results() if x.get("tournament") == t and x.get("gender") == g and x.get("id") != m.get("id")]
    if not any(x.get("q") and abs(gap(x.get("date", ""))) <= 1 for x in rows):
        return False
    return not any((not x.get("q")) and gap(x.get("date", "")) >= 1 and webapp._round_rank(x.get("round")) == rk + 1 for x in rows)


def is_qual(m):
    """Qualificação. A API marca por vezes jogos de quadro principal como qualificação, e dá o nome 'Final'/'Meias-finais' às últimas
    rondas da qualificação. Texto/código explícito = qualificação. Marcado como qualificação com ronda QF/SF/F só conta como quadro principal
    se o torneio já tiver jogos de quadro principal registados em dias anteriores (uma final nunca é o primeiro jogo do torneio)."""
    rc = str(m.get("round_code") or "").upper()
    rt = str(m.get("round") or "").lower()
    if "qualif" in rt or re.match(r"Q\d|QUAL|QR", rc):
        return True
    if _qual_context(m):
        return True
    if not m.get("is_qualifying"):
        return False
    if rc in ("QF", "SF", "F"):
        return not _main_draw_underway(m)
    return True


def _surname(name):
    """Apelido para textos curtos, com as partículas ('De Minaur', 'Van de Zandschulp', 'Da Silva')."""
    w = (name or "").split()
    if len(w) < 2:
        return name or ""
    i = len(w) - 1
    while i > 1 and w[i - 1].lower() in ("de", "da", "van", "von", "der", "del", "di", "du", "le", "la", "dos", "das"):
        i -= 1
    return " ".join(w[i:])


def _tier_rank(tag):
    """Ordem de importância de uma etiqueta de nível ('WTA 500', 'CHALLENGER 75', 'M25'...): menor = mais importante."""
    t = (tag or "").upper()
    if "SLAM" in t:
        return 0
    m = re.search(r"(\d+)", t)
    n = int(m.group(1)) if m else 0
    if t.startswith(("ATP", "WTA")) and n >= 250:
        return {1000: 1, 500: 2, 250: 3}.get(n, 3)
    if t.startswith("WTA") or "FINALS" in t:
        return 4
    if "CHALL" in t:
        return 5 + (200 - n) / 1000
    return 7 - n / 1000 if n else 8                 # ITF (M25/W75...): os de mais pontos primeiro


def _priority(m):
    """Menor = mais importante: Tour, Challenger, ITF; depois o resto. Qualificação vale menos."""
    import webapp
    _, _, level, _ = webapp.classify(webapp.api_view(m))
    # desempate: jogos com jogadores mais bem ranqueados primeiro (mais fotos livres, mais interesse)
    ranks = [((m.get("players") or {}).get(k) or {}).get("ranking") for k in ("p1", "p2")]
    best = min([r for r in ranks if isinstance(r, int)] or [900])
    pr = webapp.LEVEL_ORDER.get(level, 3) + (0.5 if is_qual(m) else 0) + min(best, 900) / 10000
    try:                                                # jogador muito pesquisado (Google / site): o jogo é confirmado primeiro dentro do nível
        import reach
        if any(webapp.slugify(((m.get("players") or {}).get(k) or {}).get("name") or "") in reach.searched_slugs() for k in ("p1", "p2")):
            pr -= 0.099
    except Exception:
        pass
    return pr


def has_portuguese(m):
    return any((m["players"][k].get("country") or "").lower() == "por" for k in ("p1", "p2"))


# Exemplos com a estrutura real da API (o segundo tem resultado inventado, só para testar)
SAMPLES = [
    {
        "id": "sample-live", "status": "live", "tournament": "W15 Campina Grande (Brazil)",
        "round": "W15 Campina Grande - 1/8-finals", "surface": "clay", "court": "Court 3", "format": "BO3",
        "players": {
            "p1": {"name": "Arias Valentina Mediorreal", "country": "col", "ranking": 850},
            "p2": {"name": "Julia Camargo Silva Konishi", "country": "bra", "ranking": 663},
        },
        "score": {"games": [[5, 7, 4], [7, 6, 1]], "sets": [1, 1], "points": ["40", "30"], "server": 2},
    },
    {
        "id": "sample-final", "status": "completed", "tournament": "Estoril Open",
        "round": "Estoril Open - Semi-finals", "surface": "clay", "court": "Court Central", "format": "BO3",
        "players": {
            "p1": {"name": "Nuno Borges", "country": "por", "ranking": 40},
            "p2": {"name": "Jaume Munar", "country": "esp", "ranking": 60},
        },
        "score": {"games": [[6, 3, 7], [4, 6, 5]], "sets": [2, 1]},
    },
]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="usar jogos ao vivo da API")
    ap.add_argument("--pt", action="store_true", help="só jogos com jogadores portugueses")
    ap.add_argument("--max", type=int, default=5, help="máximo de cartões (ou de jogos novos a acompanhar com --track-only)")
    ap.add_argument("--track-only", action="store_true", help="com --live: só acompanha jogos (não gera cartões de jogos a decorrer)")
    ap.add_argument("--out", default="cards", help="pasta de saída")
    ap.add_argument("--results", action="store_true", help="gerar cartões finais dos jogos acompanhados")
    ap.add_argument("--max-checks", type=int, default=10, help="máx. de consultas em --results")
    ap.add_argument("--paced", action="store_true", help="com --results: só consulta a API se o consumo do dia estiver abaixo do ritmo")
    ap.add_argument("--page", action="store_true", help="gerar a pasta site/ (index.html + results.html)")
    ap.add_argument("--upcoming", action="store_true", help="atualizar a lista de próximos jogos (a cada 3 h)")
    ap.add_argument("--previews", action="store_true", help="antevisão das finais das próximas 18 h ('Who wins?')")
    ap.add_argument("--player", help="com --page: filtrar por nome de jogador")
    ap.add_argument("--lang", choices=["en", "pt"], default="en", help="idioma dos cartões")
    a = ap.parse_args()
    T = I18N[a.lang]
    LANG = a.lang

    if a.upcoming:
        refresh_upcoming()
        try:
            refresh_fixtures()
        except Exception as e:
            print("Ordem de jogo: erro", e)
        try:
            refresh_player_stats()
        except Exception as e:
            print("Fichas dos jogadores: erro", e)
        sys.exit(0)

    if a.previews:
        try:
            preview_finals(a.out)
        except Exception as e:
            print("Antevisões: erro", type(e).__name__, e)
        sys.exit(0)

    if a.page:
        paths = build_site("site", a.player)
        print(f"Gerado: {len(paths)} páginas em site/")
        sys.exit(0)

    if a.results:
        mc = a.max_checks
        if a.paced and not paced_ok():
            print(f"Ritmo da quota: {quota_used()} pedidos já usados, esta execução não gasta pedidos em confirmações.")
            mc = 0
        run_results(a.out, mc)
        sys.exit(0)

    try:
        matches = fetch_live() if a.live else SAMPLES
    except Exception as e:
        print(f"Não consegui obter jogos ao vivo ({e}); salto este passo.")
        sys.exit(0)
    if a.live:
        matches = sorted([m for m in matches if not is_doubles_match(m)], key=_priority)
    if a.live:
        try:
            save_live(matches)
        except Exception as e:
            print("A guardar jogos a decorrer: erro", e)
    all_matches = matches
    if a.pt:
        matches = [m for m in matches if has_portuguese(m)]
    if not matches:
        if a.live:
            print("Sem jogos de singulares ao vivo neste momento.")
            sys.exit(0)
        sys.exit("Nenhum jogo encontrado com estes filtros.")

    os.makedirs(a.out, exist_ok=True)
    shown = matches[: a.max]
    for m in ([] if a.track_only else shown):
        print("Gerado:", render_card(m, os.path.join(a.out, f"{m['id']}.png")))
    if a.live:
        for m in all_matches:
            for pth in rising_cards(m, a.out):
                print("Notícia:", pth)
        if a.track_only:
            state = load_state()
            prio = load_prio()
            added = 0
            for m in [m for m in matches if is_live(m) and str(m["id"]) not in state]:
                if added >= a.max:
                    break
                mp = int(_priority(m))
                if mp > TRACK_MAX_PRIO:
                    continue
                if len(state) >= MAX_TRACKED:
                    # lista cheia: um jogo de Tour/Challenger tira o lugar ao de menor prioridade (ITF/resto)
                    victims = [k for k in state if prio.get(k, 3) > max(mp, 1)]
                    if mp > 1 or not victims:
                        continue
                    victim = max(victims, key=lambda k: (prio.get(k, 3), -state[k]))
                    del state[victim]
                    prio.pop(victim, None)
                state[str(m["id"])] = time.time()
                prio[str(m["id"])] = mp
                added += 1
            meta = load_meta()
            for m in matches:                       # retrato atualizado (ranking/ronda) dos jogos na fila
                if str(m.get("id")) in state:
                    meta[str(m["id"])] = snap(m)
            save_state(state)
            save_prio({k: v for k, v in prio.items() if k in state})
            save_meta(meta, state)
            print(f"Acompanhados: {len(state)} (+{added} novos, máx. {MAX_TRACKED}).")
        else:
            track([m["id"] for m in shown if is_live(m)])
