"""Cartões com foto da Beyond100 (1080x1350), desenho próprio em verde e creme.

  render_match_photo(d, out)  -> jogo importante: foto a toda a largura + painel de resultado em baixo
  render_rank_news(d, out)    -> notícia de ranking: foto em painel + número do ranking + subida

Sem foto (a maioria dos jogadores de Challenger/ITF não tem licença livre), usa-se um monograma grande.
A foto é sempre passada por quem chama (já com licença verificada); aqui nada é descarregado.
"""
import os
import re
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1080, 1350
GREEN, DEEP, CREAM, VOLT = (14, 58, 45), (9, 40, 31), (247, 242, 230), (217, 242, 61)
SOFT, EDGE, LINE = (176, 196, 183), (44, 93, 76), (24, 78, 61)
BRAND = "Follow @beyond100.tennis"

SERIF_B = ["C:/Windows/Fonts/georgiab.ttf", "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
           "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
SERIF_I = ["C:/Windows/Fonts/georgiai.ttf", "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
           "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"]
SANS_B = ["C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
          "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fit(d, text, paths, size, max_w, min_size=24):
    f = font(paths, size)
    while d.textlength(text, font=f) > max_w and size > min_size:
        size -= 2
        f = font(paths, size)
    return f


def spaced(d, cx, cy, text, f, fill, track):
    ws = [d.textlength(c, font=f) for c in text]
    x = cx - (sum(ws) + track * (len(text) - 1)) / 2
    for c, w in zip(text, ws):
        d.text((x, cy), c, font=f, fill=fill, anchor="lm")
        x += w + track


def initials(name):
    parts = (name or "?").split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()


def _court(img, alpha_line=LINE):
    d = ImageDraw.Draw(img)
    x0, x1, y0, y1 = 170, 910, 120, 1240
    mid = (y0 + y1) // 2
    d.rectangle([x0, y0, x1, y1], outline=alpha_line, width=4)
    for x in (x0 + 74, x1 - 74):
        d.line([(x, y0), (x, y1)], fill=alpha_line, width=4)
    d.line([(x0 - 20, mid), (x1 + 20, mid)], fill=alpha_line, width=6)
    for y in (mid - 270, mid + 270):
        d.line([(x0 + 74, y), (x1 - 74, y)], fill=alpha_line, width=4)
    d.line([(540, mid - 270), (540, mid + 270)], fill=alpha_line, width=4)


def _gradient(top=(17, 66, 51), bottom=(8, 34, 26)):
    g = Image.new("RGB", (W, H))
    px = g.load()
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(W):
            px[x, y] = c
    return g


def _overlay(img, y0, y1, a0, a1):
    """Escurece uma faixa vertical (de a0 a a1 de opacidade preta) para o texto ler bem sobre a foto."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for y in range(y0, y1):
        a = int(a0 + (a1 - a0) * (y - y0) / max(1, y1 - y0))
        od.line([(0, y), (img.width, y)], fill=(5, 22, 17, a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def _header(img, y=78):
    d = ImageDraw.Draw(img)
    f = font(SERIF_B, 34)
    text = "BEYOND100"
    tw = sum(d.textlength(c, font=f) for c in text) + 10 * (len(text) - 1)
    d.rounded_rectangle([W / 2 - tw / 2 - 34, y - 36, W / 2 + tw / 2 + 34, y + 36], radius=36, fill=CREAM)
    spaced(d, W / 2, y, text, f, GREEN, 10)


PARTICLES = {"de", "da", "das", "do", "dos", "del", "della", "di", "du", "van", "von", "der", "den", "ter", "le", "la", "mc", "st", "st."}


def split_name(name):
    """('ALEX', 'DE MINAUR'): o apelido leva as partículas (de, van, da, von…) que estão antes dele."""
    toks = (name or "").split()
    if not toks:
        return "", ""
    i = len(toks) - 1
    while i > 1 and toks[i - 1].lower() in PARTICLES:
        i -= 1
    if i == 1 and len(toks) > 2 and toks[0].lower() not in PARTICLES and toks[1].lower() in PARTICLES:
        i = 1
    return " ".join(toks[:i]).upper(), " ".join(toks[i:]).upper()


def credit_join(*credits):
    """'Photos: A / CC BY-SA 4.0 · B / CC0' (um só 'Photo(s):', sem quebras de linha)."""
    cs = [" ".join(re.sub(r"^Photo:\s*", "", c or "").split()) for c in credits if c]
    cs = list(dict.fromkeys(c for c in cs if c))
    if not cs:
        return None
    return ("Photo: " if len(cs) == 1 else "Photos: ") + " · ".join(cs)


def _footer(img, credit=None):
    d = ImageDraw.Draw(img)
    credit = " ".join((credit or "").split())
    if not credit:
        d.text((W / 2, 1306), BRAND, font=font(SANS_B, 30), fill=CREAM, anchor="mm")
        return
    # crédito numa linha própria por baixo da marca, à direita (o ícone de marcações do Instagram fica à esquerda), sem sobrepor
    d.text((W / 2, 1292), BRAND, font=font(SANS_B, 30), fill=CREAM, anchor="mm")
    f = fit(d, credit, SANS_B, 18, W - 200, 12)
    d.text((W - 40, 1334), credit, font=f, fill=SOFT, anchor="rm")


def _photo_or_monogram(size, who, centering=(0.5, 0.22)):
    """Imagem do jogador do tamanho pedido: foto licenciada ou monograma sobre fundo escuro."""
    w, h = size
    if who.get("photo") and os.path.exists(who["photo"]):
        return ImageOps.fit(Image.open(who["photo"]).convert("RGB"), size, centering=centering), True
    im = _gradient((19, 72, 56), (8, 34, 26)).resize((max(w, 1), max(h, 1)))
    d = ImageDraw.Draw(im)
    d.text((w / 2, h * 0.46), initials(who.get("name")), font=font(SERIF_B, int(min(w, h) * 0.5)), fill=(30, 92, 73), anchor="mm")
    return im, False


# ------------------------------------------------------------------ jogo importante
def _modern_dict(d):
    win, los = d["winner"], d["loser"]
    return {"sport": "tennis", "kicker": (d.get("kicker") or ("UPSET" if d.get("tag") else "WIN")).upper(),
            "level": d.get("level"), "tournament": d.get("tournament"), "round": d.get("round"), "date": d.get("date"),
            "winners": [{"name": win.get("name"), "country": (win.get("country") or "").upper(), "rank": win.get("rank")}],
            "losers": [{"name": los.get("name"), "country": (los.get("country") or "").upper(), "rank": los.get("rank")}],
            "sets": d["sets"], "photo": win["photo"], "credit": win.get("credit"),
            "line": d.get("edit_head") or (d.get("headline") or "").rstrip(".")}


def render_variants(d, out_path):
    """10/11/2026 (Afonso: "os 3 posts de hoje foram iguais, devia alternar"): para resultados normais desenha também os
    modelos A (grafismo de TV) e B (cartaz) ao lado do C. O publisher escolhe, na hora, o que ainda não saiu nos 2 últimos.
    Ficheiros: <out>.A.png e <out>.B.png. Devolve os modelos feitos."""
    if str(d.get("style") or "").upper() != "C" or not (d.get("winner") or {}).get("photo"):
        return []
    import modern_cards
    base = os.path.splitext(out_path)[0]
    done = []
    for k, fn in (("A", modern_cards.card_a), ("B", modern_cards.card_b)):
        try:
            fn(_modern_dict(d), f"{base}.{k}.png")
            done.append(k)
        except Exception as e:
            print(f"Modelo {k} falhou:", type(e).__name__, e)
    return done


def render_match_photo(d, out_path):
    """d = {winner:{name,country,rank,photo,credit}, loser:{name,rank}, sets:[(w,l),...] do ponto de vista do vencedor,
            tournament, round, level (ex. 'CHALLENGER'), tag (ex. 'UPSET'), headline}"""
    style = str(d.get("style") or os.environ.get("CARD_STYLE", "1")).strip()
    if style.upper() == "C" and (d.get("winner") or {}).get("photo"):   # 9/11/2026: cartão moderno (placar em vidro), igual ao padel
        import modern_cards
        return modern_cards.card_c(_modern_dict(d), out_path)
    if style == "2":                                              # capa de revista (nome enorme + título editorial)
        return render_match_photo_v2(d, out_path)
    if style == "3":                                              # painel lateral
        return render_match_photo_v3(d, out_path)
    win, los = d["winner"], d["loser"]
    img, has_photo = _photo_or_monogram((W, H), win, centering=(0.5, 0.2))
    if has_photo:
        img = _overlay(img, 0, 330, 120, 0)
        img = _overlay(img, 640, H, 0, 215)
    else:
        _court(img)
    img = img.convert("RGB")
    _header(img)
    dr = ImageDraw.Draw(img)

    # etiquetas (nível e, se houver, UPSET)
    x = 70
    for label, fill, fg in [(d.get("level"), VOLT, GREEN), (d.get("tag"), RED_TAG, CREAM)]:
        if label:
            f = font(SANS_B, 26)
            tw = dr.textlength(label, font=f) + 36
            dr.rounded_rectangle([x, 150, x + tw, 196], radius=23, fill=fill)
            dr.text((x + tw / 2, 173), label, font=f, fill=fg, anchor="mm")
            x += tw + 12

    # painel de resultado
    px0, px1, py0, py1 = 70, 1010, 905, 1155
    dr.rounded_rectangle([px0, py0, px1, py1], radius=30, fill=CREAM)
    sets = d["sets"]
    tile, gap = 78, 10
    tiles_w = len(sets) * tile + (len(sets) - 1) * gap
    name_w = (px1 - px0) - 80 - tiles_w - 20
    rows = [(win, [s[0] for s in sets], [s[1] for s in sets], True), (los, [s[1] for s in sets], [s[0] for s in sets], False)]
    for i, (p, mine, other, is_w) in enumerate(rows):
        cy = py0 + 62 + i * 126
        nm = (p.get("name") or "").upper()
        rk = p.get("rank")
        rtxt = f"#{rk}" if isinstance(rk, int) and rk > 0 else ""
        rf = font(SANS_B, 26)
        rw = (dr.textlength(rtxt, font=rf) + 16) if rtxt else 0
        f = fit(dr, nm, SERIF_B, 50 if is_w else 44, name_w - rw, 26)
        col = GREEN if is_w else (96, 120, 108)
        dr.text((px0 + 40, cy), nm, font=f, fill=col, anchor="lm")
        if rtxt:
            dr.text((px0 + 40 + dr.textlength(nm, font=f) + 16, cy + 4), rtxt, font=rf, fill=(96, 120, 108), anchor="lm")
        tx0 = px1 - 40 - tiles_w
        for j, (a, b) in enumerate(zip(mine, other)):
            x0 = tx0 + j * (tile + gap)
            won = a > b
            if won:
                dr.rounded_rectangle([x0, cy - tile / 2, x0 + tile, cy + tile / 2], radius=18, fill=GREEN)
                dr.text((x0 + tile / 2, cy), str(a), font=font(SERIF_B, 44), fill=VOLT, anchor="mm")
            else:
                dr.rounded_rectangle([x0, cy - tile / 2, x0 + tile, cy + tile / 2], radius=18, outline=(190, 200, 192), width=3)
                dr.text((x0 + tile / 2, cy), str(a), font=font(SERIF_B, 44), fill=GREEN if is_w else (120, 140, 128), anchor="mm")
        if is_w and p.get("handle"):
            dr.text((px0 + 40, cy + 38), p["handle"], font=font(SANS_B, 22), fill=(96, 120, 108), anchor="lm")
        if i == 0:
            for xx in range(px0 + 40, px1 - 40, 14):
                dr.line([(xx, py0 + 125), (xx + 5, py0 + 125)], fill=(160, 176, 166), width=2)

    sub = " · ".join(x for x in [d.get("tournament"), d.get("round")] if x).upper()
    dr.text((W / 2, 1200), sub, font=fit(dr, sub, SANS_B, 30, 920, 20), fill=VOLT, anchor="mm")
    if d.get("headline"):
        dr.text((W / 2, 1246), d["headline"], font=fit(dr, d["headline"], SERIF_I, 36, 920, 24), fill=CREAM, anchor="mm")
    _footer(img, win.get("credit"))
    img.save(out_path, quality=95)
    return out_path


RED_TAG = (196, 52, 40)


# ------------------------------------------------------------------ notícia de ranking
def render_rank_news(d, out_path):
    """d = {player, country, rank_now, rank_before, system ('ATP'/'WTA'/''), headline, context, photo, credit}"""
    img = _gradient()
    _court(img)
    _header(img)
    dr = ImageDraw.Draw(img)

    # painel da foto (à esquerda)
    x0, y0, x1, y1 = 60, 190, 640, 1190
    ph, has_photo = _photo_or_monogram((x1 - x0, y1 - y0), {"name": d["player"], "photo": d.get("photo")})
    mask = Image.new("L", ph.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ph.width - 1, ph.height - 1], radius=40, fill=255)
    img.paste(ph, (x0, y0), mask)
    dr.rounded_rectangle([x0, y0, x1, y1], radius=40, outline=CREAM, width=4)

    # coluna da direita
    cx = (660 + 1030) / 2
    label = f"{d.get('system', '')} RANKING".strip()
    spaced(dr, cx, 262, label, font(SANS_B, 28), SOFT, 6)
    first, last = split_name(d["player"])
    if first:
        dr.text((cx, 360), first, font=fit(dr, first, SERIF_B, 46, 360, 26), fill=CREAM, anchor="mm")
    dr.text((cx, 428), last, font=fit(dr, last, SERIF_B, 78, 360, 34), fill=CREAM, anchor="mm")
    num = str(d["rank_now"])
    dr.text((cx, 640), num, font=fit(dr, num, SERIF_B, 250, 370, 120), fill=VOLT, anchor="mm")

    # selo de subida (círculo sobre a borda da foto)
    delta = (d.get("rank_before") or 0) - d["rank_now"]
    bx, by, r = x1, 960, 84
    dr.ellipse([bx - r, by - r, bx + r, by + r], fill=DEEP, outline=CREAM, width=5)
    if delta > 0:
        dr.polygon([(bx, by - 52), (bx - 22, by - 24), (bx + 22, by - 24)], fill=VOLT)
        dr.text((bx, by + 18), f"+{delta}", font=font(SANS_B, 52), fill=CREAM, anchor="mm")

    head = d.get("headline") or ""
    if head:
        f = fit(dr, head.upper(), SANS_B, 30, 380, 20)
        dr.text((cx, 800), head.upper(), font=f, fill=CREAM, anchor="mm")
    if d.get("context"):
        dr.text((cx, 850), d["context"], font=fit(dr, d["context"], SERIF_I, 30, 380, 20), fill=SOFT, anchor="mm")
    _footer(img, d.get("credit"))
    img.save(out_path, quality=95)
    return out_path


# ------------------------------------------------------------------ antevisão de final ("who wins?")
def render_preview(d, out_path):
    """d = {p1:{name,rank,photo,credit,handle}, p2:{...}, tournament, round ('FINAL'), level (ex. 'CHALLENGER 125'), when ('TODAY · 14:00 UTC')}
    Duas metades com foto (ou monograma), 'VS' ao centro, nomes e rankings em baixo e a pergunta 'Who wins?'."""
    img = _gradient()
    half = W // 2
    for i, key in enumerate(("p1", "p2")):
        ph, _ = _photo_or_monogram((half, 980), d[key], centering=(0.5, 0.2))
        img.paste(ph, (i * half, 0))
    img = _overlay(img, 0, 300, 140, 0)
    img = _overlay(img, 640, 980, 0, 230)
    dr = ImageDraw.Draw(img)
    dr.rectangle([half - 3, 0, half + 2, 980], fill=GREEN)
    dr.rectangle([0, 980, W, H], fill=GREEN)
    _header(img)
    dr = ImageDraw.Draw(img)
    # etiquetas
    x = 70
    for label, fill, fg in [(d.get("level"), VOLT, GREEN), ((d.get("round") or "FINAL").upper(), CREAM, GREEN)]:
        if label:
            f = font(SANS_B, 26)
            tw = dr.textlength(label, font=f) + 36
            dr.rounded_rectangle([x, 150, x + tw, 196], radius=23, fill=fill)
            dr.text((x + tw / 2, 173), label, font=f, fill=fg, anchor="mm")
            x += tw + 12
    # VS
    cy = 760
    dr.ellipse([half - 74, cy - 74, half + 74, cy + 74], fill=VOLT, outline=GREEN, width=8)
    dr.text((half, cy + 2), "VS", font=font(SERIF_B, 64), fill=GREEN, anchor="mm")
    # nomes
    for i, key in enumerate(("p1", "p2")):
        p = d[key]
        cx = half / 2 + i * half
        first, last = split_name(p.get("name"))
        if first:
            dr.text((cx, 878), first, font=fit(dr, first, SANS_B, 28, half - 80, 18), fill=SOFT, anchor="mm")
        dr.text((cx, 928), last, font=fit(dr, last, SERIF_B, 62, half - 80, 30), fill=CREAM, anchor="mm")
        rk = p.get("rank")
        if isinstance(rk, int) and rk > 0:
            dr.text((cx, 1030), f"#{rk}", font=font(SERIF_B, 70), fill=VOLT, anchor="mm")
        if p.get("handle"):
            dr.text((cx, 1088), p["handle"], font=fit(dr, p["handle"], SANS_B, 24, half - 80, 16), fill=SOFT, anchor="mm")
    h = d.get("h2h")
    if h:
        dr.text((W / 2, 1000), "HEAD TO HEAD", font=font(SANS_B, 22), fill=SOFT, anchor="mm")
        dr.text((W / 2, 1046), f"{h['p1_wins']} – {h['p2_wins']}", font=font(SERIF_B, 54), fill=CREAM, anchor="mm")
        dr.text((W / 2, 1090), h.get("source_name", ""), font=font(SANS_B, 20), fill=SOFT, anchor="mm")
    sub = " · ".join(x for x in [d.get("tournament"), d.get("when")] if x).upper()
    dr.text((W / 2, 1160), sub, font=fit(dr, sub, SANS_B, 30, 960, 18), fill=VOLT, anchor="mm")
    dr.text((W / 2, 1228), "Who wins? Tell us below.", font=font(SERIF_I, 44), fill=CREAM, anchor="mm")
    _footer(img, credit_join(d["p1"].get("credit"), d["p2"].get("credit")))
    img.save(out_path, quality=95)
    return out_path


def render_preview_b(d, out_path):
    """Variante B da antevisão: um jogador em cima, outro em baixo, faixa diagonal ao meio com a final, o H2H e a hora."""
    img = _gradient()
    for key, y0 in (("p1", 0), ("p2", 750)):
        ph, _ = _photo_or_monogram((W, 600), d[key], centering=(0.5, 0.25))
        img.paste(ph, (0, y0))
    img = _overlay(img, 0, 260, 150, 0)
    img = _overlay(img, 380, 600, 0, 210)
    img = _overlay(img, 1090, H, 0, 225)
    dr = ImageDraw.Draw(img)
    dr.polygon([(0, 560), (W, 500), (W, 850), (0, 910)], fill=GREEN)
    dr.line([(0, 560), (W, 500)], fill=VOLT, width=6)
    dr.line([(0, 910), (W, 850)], fill=VOLT, width=6)
    _header(img)
    dr = ImageDraw.Draw(img)
    f = font(SANS_B, 26)
    for label, fill, fg, x in [("WHO WINS?", VOLT, GREEN, 70)] + ([(d["level"], CREAM, GREEN, None)] if d.get("level") else []):
        tw = dr.textlength(label, font=f) + 36
        x = x if x is not None else 70 + dr.textlength("WHO WINS?", font=f) + 48
        dr.rounded_rectangle([x, 150, x + tw, 196], radius=23, fill=fill)
        dr.text((x + tw / 2, 173), label, font=f, fill=fg, anchor="mm")

    def who(p, y):
        first, last = split_name(p.get("name"))
        rk = p.get("rank")
        rt = f"#{rk}" if isinstance(rk, int) and rk > 0 else ""
        rw = dr.textlength(rt, font=font(SERIF_B, 64)) + 30 if rt else 0
        if first:
            dr.text((70, y - 66), first, font=fit(dr, first, SANS_B, 28, 900 - rw, 18), fill=SOFT, anchor="ls")
        dr.text((70, y), last, font=fit(dr, last, SERIF_B, 72, 940 - rw, 34), fill=CREAM, anchor="ls")
        if rt:
            dr.text((1010, y), rt, font=font(SERIF_B, 64), fill=VOLT, anchor="rs")
        if p.get("handle"):
            dr.text((70, y + 34), p["handle"], font=font(SANS_B, 22), fill=SOFT, anchor="ls")
    who(d["p1"], 470)
    who(d["p2"], 1190)
    top = " · ".join(x for x in [(d.get("round") or "Final"), d.get("tournament")] if x).upper()
    dr.text((W / 2, 640), top, font=fit(dr, top, SANS_B, 30, 900, 18), fill=VOLT, anchor="mm")
    h = d.get("h2h")
    mid = f"H2H  {h['p1_wins']} – {h['p2_wins']}" if h else "FOR THE TITLE"
    dr.text((W / 2, 720), mid, font=font(SERIF_B, 64), fill=CREAM, anchor="mm")
    sub = " · ".join(x for x in [("Official record · " + h["source_name"]) if h else "", d.get("when")] if x)
    dr.text((W / 2, 778), sub, font=fit(dr, sub, SANS_B, 22, 900, 16), fill=SOFT, anchor="mm")
    _footer(img, credit_join(d["p1"].get("credit"), d["p2"].get("credit")))
    img.save(out_path, quality=95)
    return out_path


# ------------------------------------------------------------------ jogo importante, desenho 2 (CARD_STYLE=2)
_HERE = os.path.dirname(os.path.abspath(__file__))
COND_B = [os.path.join(_HERE, "fonts", "BarlowCondensed-Bold.ttf"), os.path.join(_HERE, "fonts", "Oswald-Bold.ttf"),
          "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf"] + SANS_B


def _cond():
    """Fonte condensada e quanto comprimir na horizontal (as de recurso não são tão estreitas)."""
    for p in COND_B:
        if os.path.exists(p):
            return p, (1.0 if "Barlow" in p or "Oswald" in p else 0.8)
    return None, 0.8


def _sq_text(img, x, y, text, size, fill):
    """Texto condensado, alinhado à esquerda com o topo em y. Devolve a altura usada."""
    path, sx = _cond()
    f = ImageFont.truetype(path, size) if path else ImageFont.load_default()
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), text, font=f)
    layer = Image.new("RGBA", (bb[2] - bb[0] + 8, bb[3] + 8), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((-bb[0], 0), text, font=f, fill=fill)
    if sx != 1.0:
        layer = layer.resize((max(1, int(layer.width * sx)), layer.height))
    img.paste(layer, (int(x), int(y - bb[1])), layer)
    return bb[3] - bb[1]


def _sq_fit(text, size, max_w, min_size=40):
    path, sx = _cond()
    d = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    while size > min_size:
        f = ImageFont.truetype(path, size) if path else ImageFont.load_default()
        if d.textlength(text, font=f) * sx <= max_w:
            break
        size -= 4
    return size


def render_match_photo_v2(d, out_path):
    """Foto a toda a altura, nome enorme em letra condensada, título editorial, etiqueta vertical (WIN/UPSET/TITLE) e resultado numa linha.
    d = o mesmo de render_match_photo + date ('27 OCT 2026'), kicker, edit_head."""
    win, los = d["winner"], d["loser"]
    img, has_photo = _photo_or_monogram((W, H), win, centering=(0.5, 0.18))
    img = _overlay(img, 0, 260, 130, 0)
    img = _overlay(img, 540, H, 0, 245)
    dr = ImageDraw.Draw(img)
    f = font(SANS_B, 24)
    if d.get("date"):
        t = d["date"].upper()
        tw = dr.textlength(t, font=f) + 34
        dr.rounded_rectangle([50, 46, 50 + tw, 90], radius=22, outline=CREAM, width=2)
        dr.text((50 + tw / 2, 68), t, font=f, fill=CREAM, anchor="mm")
    top = " · ".join(x for x in [d.get("level"), (d.get("tournament") or "").upper()] if x)
    if top:
        tf = fit(dr, top, SANS_B, 24, 640, 16)
        tw = dr.textlength(top, font=tf) + 34
        dr.rounded_rectangle([W - 50 - tw, 46, W - 50, 90], radius=22, fill=VOLT)
        dr.text((W - 50 - tw / 2, 68), top, font=tf, fill=GREEN, anchor="mm")
    x, maxw = 120, W - 120 - 50
    nm = (win.get("name") or "").upper()
    s1 = _sq_fit(nm, 150, maxw)
    head = (d.get("edit_head") or d.get("headline") or "").strip().rstrip(".").upper()
    s2 = _sq_fit(head, 92, maxw) if head else 0
    sc = "  ".join(f"{a}-{b}" for a, b in d["sets"])
    rk = f" (#{los['rank']})" if isinstance(los.get("rank"), int) and los["rank"] > 0 else ""
    info = "  ·  ".join(v for v in [(d.get("round") or "").upper(), sc, f"VS {(los.get('name') or '').upper()}{rk}"] if v)
    # bloco de baixo para cima, para o nome nunca sair do cartão
    y_info = 1190
    y_head = y_info - 46 - (int(s2 * 0.9) if head else 0)
    y_name = y_head - 18 - int(s1 * 0.9)
    _sq_text(img, x, y_name, nm, s1, CREAM)
    if head:
        _sq_text(img, x, y_head, head, s2, VOLT)
    dr = ImageDraw.Draw(img)
    dr.text((x, y_info), info, font=fit(dr, info, SANS_B, 26, maxw, 16), fill=CREAM, anchor="ls")
    if win.get("handle"):
        dr.text((x, y_info + 38), win["handle"], font=font(SANS_B, 22), fill=SOFT, anchor="ls")
    # barra vertical com a etiqueta
    by0, by1 = y_name - 6, y_info + 8
    dr.rectangle([50, by0, 96, by1], fill=VOLT if (d.get("kicker") or "WIN") != "UPSET" else RED_TAG)
    lab = Image.new("RGBA", (by1 - by0, 46), (0, 0, 0, 0))
    ImageDraw.Draw(lab).text(((by1 - by0) / 2, 23), d.get("kicker") or "WIN", font=font(SANS_B, 24),
                             fill=GREEN if (d.get("kicker") or "WIN") != "UPSET" else CREAM, anchor="mm")
    lab = lab.rotate(90, expand=True)
    img.paste(lab, (50, by0), lab)
    dr = ImageDraw.Draw(img)
    dr.text((50, 1300), "BEYOND100", font=font(SERIF_B, 26), fill=CREAM, anchor="lm")
    dr.text((W - 50, 1300), BRAND, font=font(SANS_B, 24), fill=CREAM, anchor="rm")
    if win.get("credit"):
        dr.text((W - 50, 1334), win["credit"][:90], font=font(SANS_B, 17), fill=SOFT, anchor="rm")
    img.save(out_path, quality=95)
    return out_path


# ------------------------------------------------------------------ jogo importante, desenho 3: painel lateral
def render_match_photo_v3(d, out_path):
    """Painel verde à esquerda (marca, etiqueta, torneio, nome empilhado, ranking, resultado set a set) e foto à direita
    com o título editorial em baixo. d = o mesmo de render_match_photo_v2."""
    win, los = d["winner"], d["loser"]
    img = _gradient((17, 66, 51), (8, 34, 26))
    PW = 420
    ph, _ = _photo_or_monogram((W - PW, H), win, centering=(0.5, 0.2))
    img.paste(ph, (PW, 0))
    ov = Image.new("RGBA", (140, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for xx in range(140):
        od.line([(xx, 0), (xx, H)], fill=(8, 34, 26, int(200 * (1 - xx / 140))))
    img.paste(ov, (PW, 0), ov)
    ov = Image.new("RGBA", (W - PW, 330), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for yy in range(330):
        od.line([(0, yy), (W - PW, yy)], fill=(5, 22, 17, int(230 * yy / 330)))
    img.paste(ov, (PW, H - 330), ov)
    dr = ImageDraw.Draw(img)
    dr.rectangle((PW - 6, 0, PW, H), fill=VOLT)
    x, cw = 50, PW - 90
    dr.text((x, 80), "BEYOND100", font=font(SERIF_B, 30), fill=CREAM, anchor="lm")
    k = d.get("kicker") or "WIN"
    f = font(SANS_B, 24)
    tw = dr.textlength(k, font=f) + 34
    up = k == "UPSET"
    dr.rounded_rectangle([x, 150, x + tw, 194], radius=22, fill=RED_TAG if up else VOLT)
    dr.text((x + tw / 2, 172), k, font=f, fill=CREAM if up else GREEN, anchor="mm")
    if d.get("level"):
        dr.text((x, 240), d["level"], font=fit(dr, d["level"], SANS_B, 24, cw, 16), fill=SOFT, anchor="lm")
    t = (d.get("tournament") or "").upper()
    dr.text((x, 276), t, font=fit(dr, t, SANS_B, 34, cw, 18), fill=CREAM, anchor="lm")
    rd = (d.get("round") or "").upper()
    dr.text((x, 314), rd, font=fit(dr, rd, SANS_B, 24, cw, 16), fill=SOFT, anchor="lm")
    if d.get("date"):
        dr.text((x, 346), d["date"].upper(), font=font(SANS_B, 20), fill=SOFT, anchor="lm")
    first, last = split_name(win.get("name"))
    y = 430
    if first:
        s = _sq_fit(first, 70, cw)
        _sq_text(img, x, y, first, s, SOFT)
        y += int(s * 0.95) + 14
    s = _sq_fit(last, 130, cw)
    _sq_text(img, x, y, last, s, CREAM)
    y += int(s * 0.95) + 20
    dr = ImageDraw.Draw(img)
    if isinstance(win.get("rank"), int) and win["rank"] > 0:
        dr.text((x, y + 10), f"#{win['rank']}", font=font(SERIF_B, 48), fill=VOLT, anchor="lt")
        y += 80
    y += 30
    dr.text((x, y), "SCORE", font=font(SANS_B, 22), fill=SOFT, anchor="lt")
    y += 40
    rows = d["sets"][:5]
    big = 80 if len(rows) <= 3 else 62
    for a, b in rows:
        dr.text((x, y), str(a), font=font(SERIF_B, big), fill=CREAM, anchor="lt")
        dr.text((x + int(big * 0.88), y + int(big * 0.27)), "–", font=font(SERIF_B, int(big * 0.62)), fill=SOFT, anchor="lt")
        dr.text((x + int(big * 1.5), y), str(b), font=font(SERIF_B, big), fill=SOFT, anchor="lt")
        y += int(big * 1.2)
    lr = f" #{los['rank']}" if isinstance(los.get("rank"), int) and los["rank"] > 0 else ""
    dl = "def. " + (los.get("name") or "") + lr
    dr.text((x, y + 10), dl, font=fit(dr, dl, SANS_B, 26, cw + 30, 14), fill=SOFT, anchor="lt")
    if win.get("handle"):
        dr.text((x, y + 50), win["handle"], font=fit(dr, win["handle"], SANS_B, 22, cw + 30, 14), fill=SOFT, anchor="lt")
    head = (d.get("edit_head") or d.get("headline") or "").strip().rstrip(".").upper()
    if head:
        s = _sq_fit(head, 90, W - PW - 80)
        _sq_text(img, PW + 40, H - 190, head, s, VOLT)
    dr = ImageDraw.Draw(img)
    dr.text((W - 40, H - 50), BRAND, font=font(SANS_B, 24), fill=CREAM, anchor="rm")
    if win.get("credit"):
        dr.text((W - 40, H - 18), win["credit"][:90], font=font(SANS_B, 17), fill=SOFT, anchor="rm")
    img.save(out_path, quality=95)
    return out_path


# ------------------------------------------------------------------ campeão (9/11/2026)
def render_champion(d, out_path):
    """Post de campeão: foto grande do campeão, nome, torneio, resultado da final e o caminho até ao título (ronda a ronda).
    d = {name, rank, photo, credit, tournament, level, date, final:{opp, opp_rank, sets:[(a,b)]}, road:[(ronda, adversário, rank)],
         badge (opcional, só factos confirmados), note (opcional, ex.: "5 wins · 1 set dropped")}"""
    img = _gradient((17, 66, 51), (8, 34, 26))
    PH = 860
    ph, has = _photo_or_monogram((W, PH), {"photo": d.get("photo"), "name": d.get("name")}, centering=(0.5, 0.2))
    img.paste(ph, (0, 0))
    img = _overlay(img, 0, 240, 150, 0)
    img = _overlay(img, 380, PH, 0, 235)
    dr = ImageDraw.Draw(img)
    _header(img)
    f = font(SANS_B, 26)
    x = 70
    for label, fill, fg in [("CHAMPION", VOLT, GREEN), (d.get("level"), CREAM, GREEN)]:
        if not label:
            continue
        tw = dr.textlength(label, font=f) + 40
        dr.rounded_rectangle([x, 150, x + tw, 198], radius=24, fill=fill)
        dr.text((x + tw / 2, 174), label, font=f, fill=fg, anchor="mm")
        x += tw + 14
    first, last = split_name(d.get("name"))
    if first:
        dr.text((70, 640), first.upper(), font=fit(dr, first.upper(), SANS_B, 40, W - 140, 22), fill=CREAM, anchor="ls")
    dr.text((66, 760), last.upper(), font=fit(dr, last.upper(), SERIF_B, 132, W - 340, 60), fill=CREAM, anchor="ls")
    if isinstance(d.get("rank"), int):
        dr.text((W - 70, 760), f"#{d['rank']}", font=font(SERIF_B, 76), fill=VOLT, anchor="rs")
    sub = " · ".join(x_ for x_ in [d.get("tournament"), d.get("date")] if x_).upper()
    dr.text((70, 815), sub, font=fit(dr, sub, SANS_B, 30, W - 140, 18), fill=VOLT, anchor="ls")
    # painel de baixo: final (esquerda) e caminho até ao título (direita)
    y0 = PH + 30
    dr.text((70, y0), "FINAL", font=font(SANS_B, 22), fill=SOFT, anchor="lt")
    fx = 70
    for a, b in d["final"]["sets"][:5]:
        txt = f"{a}-{b}"
        dr.rounded_rectangle([fx, y0 + 40, fx + 120, y0 + 120], radius=16, fill=VOLT)
        dr.text((fx + 60, y0 + 80), txt, font=font(SERIF_B, 46), fill=GREEN, anchor="mm")
        fx += 134
    opp = d["final"].get("opp") or ""
    orank = f" #{d['final']['opp_rank']}" if isinstance(d["final"].get("opp_rank"), int) else ""
    dl = f"d. {opp}{orank}"
    dr.text((70, y0 + 150), dl, font=fit(dr, dl, SANS_B, 28, 440, 16), fill=CREAM, anchor="lt")
    if d.get("note"):
        dr.text((70, y0 + 196), d["note"], font=fit(dr, d["note"], SANS_B, 24, 440, 14), fill=SOFT, anchor="lt")
    if d.get("badge"):
        bf = font(SANS_B, 22)
        tw = dr.textlength(d["badge"], font=bf) + 34
        dr.rounded_rectangle([70, y0 + 240, 70 + tw, y0 + 282], radius=21, outline=VOLT, width=3)
        dr.text((70 + tw / 2, y0 + 261), d["badge"], font=bf, fill=VOLT, anchor="mm")
    rx = 560
    dr.line([(rx - 30, y0), (rx - 30, y0 + 300)], fill=EDGE, width=2)
    dr.text((rx, y0), "ROAD TO THE TITLE", font=font(SANS_B, 22), fill=SOFT, anchor="lt")
    road = d.get("road") or []
    yy = y0 + 42
    step = 52 if len(road) <= 5 else 44
    for rd, nm, rk in road[-6:]:
        dr.text((rx, yy), rd, font=font(SANS_B, 22), fill=VOLT, anchor="lt")
        t = nm + (f"  #{rk}" if isinstance(rk, int) else "")
        dr.text((rx + 70, yy - 2), t, font=fit(dr, t, SERIF_B, 28, W - rx - 110, 16), fill=CREAM, anchor="lt")
        yy += step
    _footer(img, d.get("credit") if has else None)
    img.save(out_path, quality=95)
    return out_path


# ------------------------------------------------------------------ Road to the Top 100 (9/11/2026)
def _circle(img, fp, box):
    x0, y0, x1, y1 = box
    s = x1 - x0
    ph = ImageOps.fit(Image.open(fp).convert("RGB"), (s, s), centering=(0.5, 0.2))
    m = Image.new("L", (s, s), 0)
    ImageDraw.Draw(m).ellipse([0, 0, s - 1, s - 1], fill=255)
    img.paste(ph, (x0, y0), m)


def render_road(data, date_label, out_path):
    """Ranking OFICIAL (ESPN) dos que estão logo a seguir ao top 100: por género, o primeiro em destaque (foto, se houver uma boa)
    e os 3 seguintes. A distância é em pontos para o n.º 100 dessa semana. data = {"men": [...], "women": [...]},
    cada um {name, rank, pts, gap, move, photo, credit}."""
    img = _gradient((17, 66, 51), (8, 34, 26))
    dr = ImageDraw.Draw(img)
    _header(img)
    dr = ImageDraw.Draw(img)
    dr.text((70, 215), "ROAD TO THE TOP 100", font=fit(dr, "ROAD TO THE TOP 100", SERIF_B, 76, W - 140, 40), fill=CREAM, anchor="ls")
    sub = f"Official rankings · {date_label}"
    dr.text((70, 262), sub, font=font(SANS_B, 28), fill=VOLT, anchor="ls")
    credits = []
    y = 320

    def gap_txt(x):
        if x.get("gap") is None:
            return ""
        return "level on points with No. 100" if x["gap"] <= 0 else f"{x['gap']} pts behind No. 100"

    def mv_txt(x):
        m = x.get("move")
        return "" if not m else (f"▲{m}" if m > 0 else f"▼{-m}")
    for g, label in (("men", "MEN"), ("women", "WOMEN")):
        xs = (data.get(g) or [])[:4]
        if not xs:
            continue
        dr.text((70, y + 22), label, font=font(SANS_B, 24), fill=SOFT, anchor="ls")
        y += 40
        top = xs[0]
        dr.rounded_rectangle([60, y, W - 60, y + 170], radius=28, fill=(22, 82, 63))
        tx = 100
        if top.get("photo"):
            _circle(img, top["photo"], (90, y + 20, 220, y + 150))
            dr = ImageDraw.Draw(img)
            credits.append(top.get("credit"))
            tx = 250
        dr.text((tx, y + 62), f"No. {top['rank']}", font=font(SERIF_B, 36), fill=VOLT, anchor="ls")
        mv = mv_txt(top)
        if mv:
            dr.text((tx + dr.textlength(f"No. {top['rank']}", font=font(SERIF_B, 36)) + 18, y + 60), mv, font=font(SANS_B, 26),
                    fill=VOLT if top["move"] > 0 else (255, 138, 128), anchor="ls")
        dr.text((tx, y + 112), top["name"], font=fit(dr, top["name"], SERIF_B, 50, W - tx - 100, 26), fill=CREAM, anchor="ls")
        dr.text((tx, y + 150), gap_txt(top), font=font(SANS_B, 26), fill=SOFT, anchor="ls")
        y += 186
        for x in xs[1:]:
            dr.text((100, y + 40), f"{x['rank']}", font=font(SERIF_B, 34), fill=VOLT, anchor="ls")
            dr.text((180, y + 40), x["name"], font=fit(dr, x["name"], SERIF_B, 34, 460, 20), fill=CREAM, anchor="ls")
            mv = mv_txt(x)
            if mv:
                dr.text((660, y + 38), mv, font=font(SANS_B, 22), fill=VOLT if x["move"] > 0 else (255, 138, 128), anchor="ls")
            gt = "level" if (x.get("gap") is not None and x["gap"] <= 0) else (f"−{x['gap']} pts" if x.get("gap") is not None else "")
            dr.text((W - 90, y + 38), gt, font=font(SANS_B, 26), fill=SOFT, anchor="rs")
            dr.line([(100, y + 58), (W - 90, y + 58)], fill=EDGE, width=1)
            y += 64
        y += 24
    _footer(img, credit_join(*[c for c in credits if c]) or None)
    img.save(out_path, quality=95)
    return out_path
