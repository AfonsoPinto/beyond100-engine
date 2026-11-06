"""
Cartões de NOTÍCIA da Beyond100 (1080x1350), escritos só a partir de dados
(ranking, resultado). Nada é inventado: cada campo vem do dicionário de entrada.

Uso:
    py news_card.py            # gera 2 exemplos FICTÍCIOS em news_samples/

Tipos:
    render_rising(d, out)  -> jogador que sobe / entra no top 100
    render_upset(d, out)   -> surpresa (jogador de ranking bem pior vence)
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350
GREEN, CREAM, VOLT, MUTED, DEEP = (14, 58, 45), (247, 242, 230), (217, 242, 61), (176, 196, 183), (9, 40, 31)

SERIF_B = ["C:/Windows/Fonts/georgiab.ttf", "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
           "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"]
SERIF_I = ["C:/Windows/Fonts/georgiai.ttf", "/System/Library/Fonts/Supplemental/Georgia Italic.ttf",
           "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"]
SANS_B = ["C:/Windows/Fonts/arialbd.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
          "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
SANS_R = ["C:/Windows/Fonts/arial.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
          "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
BRAND = "@beyond100.tennis"


def font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fit(d, text, paths, size, max_w, min_size=30):
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


def wrap(d, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def base(badge):
    im = Image.new("RGB", (W, H), GREEN)
    d = ImageDraw.Draw(im)
    d.rectangle([36, 36, W - 37, H - 37], outline=CREAM, width=3)
    d.rectangle([52, 52, W - 53, H - 53], outline=CREAM, width=1)
    spaced(d, W / 2, 125, "BEYOND100", font(SERIF_B, 40), CREAM, 10)
    bf = font(SANS_B, 32)
    bw = d.textlength(badge, font=bf) + 8 * (len(badge) - 1) + 80
    d.rounded_rectangle([W / 2 - bw / 2, 175, W / 2 + bw / 2, 237], radius=31, fill=VOLT)
    spaced(d, W / 2, 207, badge, bf, GREEN, 8)
    return im, d


def footer(d):
    d.ellipse([W / 2 - 9, 1228, W / 2 + 9, 1246], fill=VOLT)
    d.text((W / 2, 1280), BRAND, font=font(SANS_B, 34), fill=CREAM, anchor="mm")


def rank_box(d, x, y, w, h, label, rank, hot):
    if hot:
        d.rounded_rectangle([x, y, x + w, y + h], radius=34, fill=VOLT)
        c1, c2 = GREEN, GREEN
    else:
        d.rounded_rectangle([x, y, x + w, y + h], radius=34, outline=CREAM, width=3)
        c1, c2 = MUTED, CREAM
    d.text((x + w / 2, y + 48), label, font=font(SANS_B, 28), fill=c1, anchor="mm")
    d.text((x + w / 2, y + h / 2 + 28), f"#{rank}", font=font(SERIF_B, 120), fill=c2, anchor="mm")


# ---------- RISING ----------
def render_rising(data, out):
    im, d = base("RISING")
    f = font(SERIF_B, 84)
    y = 330
    for line in wrap(d, data["headline"], f, 860):
        d.text((W / 2, y), line, font=f, fill=CREAM, anchor="mm")
        y += 100
    d.text((W / 2, y + 40), data["player"], font=fit(d, data["player"], SERIF_I, 80, 860), fill=VOLT, anchor="mm")
    d.text((W / 2, y + 120), (data.get("country") or "").upper(), font=font(SANS_B, 30), fill=MUTED, anchor="mm")
    by = 760
    rank_box(d, 130, by, 340, 250, "BEFORE", data["rank_before"], False)
    rank_box(d, W - 130 - 340, by, 340, 250, "NOW", data["rank_now"], True)
    cy = by + 125                                           # seta
    d.polygon([(500, cy - 14), (545, cy - 14), (545, cy - 34), (582, cy), (545, cy + 34), (545, cy + 14), (500, cy + 14)], fill=VOLT)
    d.text((W / 2, 1100), data["context"], font=fit(d, data["context"], SANS_R, 34, 860), fill=MUTED, anchor="mm")
    footer(d)
    im.save(out, quality=95)
    return out


# ---------- UPSET ----------
def render_upset(data, out):
    im, d = base("UPSET")
    f = font(SERIF_B, 84)
    y = 330
    for line in wrap(d, data["headline"], f, 860):
        d.text((W / 2, y), line, font=f, fill=CREAM, anchor="mm")
        y += 100
    top = 650
    for i, (key, win) in enumerate([("winner", True), ("loser", False)]):
        p = data[key]
        yy = top + i * 190
        d.rounded_rectangle([110, yy, W - 110, yy + 160], radius=34, fill=DEEP if not win else None,
                            outline=VOLT if win else CREAM, width=4 if win else 2)
        d.rounded_rectangle([140, yy + 38, 310, yy + 122], radius=42, fill=VOLT if win else None,
                            outline=None if win else MUTED, width=2)
        d.text((225, yy + 80), f"#{p['rank']}", font=font(SERIF_B, 54), fill=GREEN if win else MUTED, anchor="mm")
        d.text((345, yy + 80), p["name"], font=fit(d, p["name"], SERIF_B, 56, 650), fill=CREAM if win else MUTED, anchor="lm")
    d.text((W / 2, 1060), data["score"], font=font(SERIF_B, 64), fill=VOLT, anchor="mm")
    d.text((W / 2, 1130), data["context"], font=fit(d, data["context"], SANS_R, 34, 860), fill=MUTED, anchor="mm")
    footer(d)
    im.save(out, quality=95)
    return out


# ---------- exemplos FICTÍCIOS ----------
SAMPLE_RISING = {
    "headline": "Breaks into the top 100 for the first time.",
    "player": "Marco Ellison", "country": "ita",
    "rank_before": 112, "rank_now": 98,
    "context": "Up 14 places · first Challenger final of the season",
}
SAMPLE_UPSET = {
    "headline": "A 141-place gap, closed in three sets.",
    "winner": {"name": "Tomás Verhoeven", "rank": 187},
    "loser": {"name": "Luis Marandi", "rank": 46},
    "score": "6-4  3-6  7-5",
    "context": "Round of 16 · Sample Challenger Open",
}


# ---------- NEWS (notícia verificada, com fontes) ----------
def _circle_photo(im, path, cx, cy, r):
    ph = Image.open(path).convert("RGB")
    side = min(ph.size)
    ph = ph.crop(((ph.width - side) // 2, 0, (ph.width - side) // 2 + side, side)).resize((2 * r, 2 * r))
    mask = Image.new("L", (2 * r, 2 * r), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
    ring = ImageDraw.Draw(im)
    ring.ellipse([cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8], fill=VOLT)
    im.paste(ph, (cx - r, cy - r), mask)


def render_news_plain(data, out):
    """data: badge, headline, summary, source ('ATP Tour · Reuters'), photo (caminho, opcional), photo_credit (opcional)."""
    im, d = base((data.get("badge") or "NEWS").upper())
    has_photo = bool(data.get("photo") and os.path.exists(data["photo"]))
    y = 300
    if has_photo:
        _circle_photo(im, data["photo"], W // 2, 480, 170)
        y = 720
        if data.get("photo_credit"):
            d.text((W / 2, 1190), data["photo_credit"], font=font(SANS_R, 22), fill=MUTED, anchor="mm")
    size = 76
    while True:
        f = font(SERIF_B, size)
        lines = wrap(d, data["headline"], f, 880)
        if len(lines) <= (3 if has_photo else 4) or size <= 48:
            break
        size -= 4
    lh = int(size * 1.18)
    if not has_photo:      # sem foto: centra o bloco de texto na área livre
        sf0 = font(SANS_R, 36)
        n_sum = len(wrap(d, data.get("summary", ""), sf0, 840)[:5])
        block = len(lines) * lh + 30 + n_sum * 52
        y = int(300 + (1080 - 300 - block) / 2 + lh / 2)
    for line in lines:
        d.text((W / 2, y), line, font=f, fill=CREAM, anchor="mm")
        y += lh
    y += 30
    sf = font(SANS_R, 36)
    sl = wrap(d, data.get("summary", ""), sf, 840)[: (3 if has_photo else 5)]
    for line in sl:
        d.text((W / 2, y), line, font=sf, fill=MUTED, anchor="mm")
        y += 52
    if data.get("source"):
        d.text((W / 2, 1140), "Source: " + data["source"], font=fit(d, "Source: " + data["source"], SANS_B, 30, 860, 22), fill=VOLT, anchor="mm")
    footer(d)
    im.save(out, quality=95)
    return out


def render_news_story_plain(data, out):
    """Versão vertical 1080x1920 para Stories do Instagram (mesmo conteúdo do cartão de notícia; foto obrigatória)."""
    SW, SH = 1080, 1920
    im = Image.new("RGB", (SW, SH), GREEN)
    d = ImageDraw.Draw(im)
    d.rectangle([36, 120, SW - 37, SH - 260], outline=CREAM, width=3)
    d.rectangle([52, 136, SW - 53, SH - 276], outline=CREAM, width=1)
    spaced(d, SW / 2, 230, "BEYOND100", font(SERIF_B, 44), CREAM, 12)
    badge = (data.get("badge") or "NEWS").upper()
    bf = font(SANS_B, 34)
    bw = d.textlength(badge, font=bf) + 8 * (len(badge) - 1) + 90
    d.rounded_rectangle([SW / 2 - bw / 2, 290, SW / 2 + bw / 2, 358], radius=34, fill=VOLT)
    spaced(d, SW / 2, 324, badge, bf, GREEN, 8)
    y = 560
    if data.get("photo") and os.path.exists(data["photo"]):
        _circle_photo(im, data["photo"], SW // 2, 640, 230)
        y = 960
        if data.get("photo_credit"):
            d.text((SW / 2, SH - 385), data["photo_credit"], font=font(SANS_R, 24), fill=MUTED, anchor="mm")
    d = ImageDraw.Draw(im)
    size = 80
    while True:
        f = font(SERIF_B, size)
        lines = wrap(d, data["headline"], f, 880)
        if len(lines) <= 4 or size <= 52:
            break
        size -= 4
    for line in lines:
        d.text((SW / 2, y), line, font=f, fill=CREAM, anchor="mm")
        y += int(size * 1.18)
    y += 40
    sf = font(SANS_R, 40)
    for line in wrap(d, data.get("summary", ""), sf, 840)[:5]:
        d.text((SW / 2, y), line, font=sf, fill=MUTED, anchor="mm")
        y += 58
    if data.get("source"):
        t = "Source: " + data["source"]
        d.text((SW / 2, SH - 435), t, font=fit(d, t, SANS_B, 32, 860, 24), fill=VOLT, anchor="mm")
    d.ellipse([SW / 2 - 9, SH - 350, SW / 2 + 9, SH - 332], fill=VOLT)
    d.text((SW / 2, SH - 303), BRAND, font=font(SANS_B, 36), fill=CREAM, anchor="mm")
    im.save(out, quality=95)
    return out


# ---------- NEWS, desenho A: foto a toda a largura + degradé (o usado por omissão) ----------
def _cover(photo, w, h, top=0.2):
    from PIL import ImageOps
    return ImageOps.fit(Image.open(photo).convert("RGB"), (w, h), centering=(0.5, top))


def _pill(d, x, y, text, size=30, track=6, h=60):
    f = font(SANS_B, size)
    w = d.textlength(text, font=f) + track * (len(text) - 1) + 60
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=VOLT)
    spaced(d, x + w / 2, y + h / 2, text, f, GREEN, track)
    return w


def _render_a(data, out, w, h, top_safe, bottom_safe, head_size, sum_size, tilt):
    """Foto a toda a largura; degradé verde-escuro em baixo; selo da categoria, título, resumo, fonte e crédito da foto."""
    im = _cover(data["photo"], w, h, tilt)
    start = int(h * 0.36)
    mask = Image.new("L", (1, h))
    for y in range(h):
        mask.putpixel((0, y), 0 if y < start else min(255, int((y - start) / (h - start) * 310)))
    im.paste(Image.new("RGB", (w, h), DEEP), (0, 0), mask.resize((w, h)))
    d = ImageDraw.Draw(im)
    bf = font(SERIF_B, 30)
    bw = d.textlength("BEYOND100", font=bf) + 10 * 8 + 90
    d.rounded_rectangle([w / 2 - bw / 2, top_safe, w / 2 + bw / 2, top_safe + 64], radius=32, fill=CREAM)
    spaced(d, w / 2, top_safe + 32, "BEYOND100", bf, GREEN, 10)
    _pill(d, 60, top_safe + 100, (data.get("badge") or "NEWS").upper())
    size = head_size
    while True:
        f = font(SERIF_B, size)
        lines = wrap(d, data["headline"], f, w - 160)
        if len(lines) <= 4 or size <= 48:
            break
        size -= 4
    sf = font(SANS_R, sum_size)
    sl = wrap(d, data.get("summary", ""), sf, w - 160)[:3]
    lh, sh = int(size * 1.2), int(sum_size * 1.4)
    block = len(lines) * lh + 24 + len(sl) * sh
    y = h - bottom_safe - 110 - block + lh // 2
    for line in lines:
        d.text((70, y), line, font=f, fill=CREAM, anchor="lm")
        y += lh
    y += 14
    for line in sl:
        d.text((70, y + 10), line, font=sf, fill=(215, 225, 218), anchor="lm")
        y += sh
    base_y = h - bottom_safe - 45
    lx = 70 if h > 1500 else 125            # no post, o ícone de "pessoas marcadas" do Instagram fica no canto inferior esquerdo
    if data.get("source"):
        t = "Source: " + data["source"]
        d.text((lx, base_y), t, font=fit(d, t, SANS_B, 28, w // 2 + 40, 20), fill=VOLT, anchor="lm")
    d.text((w - 70, base_y), BRAND, font=font(SANS_B, 28), fill=CREAM, anchor="rm")
    if data.get("photo_credit"):
        d.text((lx, base_y + 42), data["photo_credit"], font=font(SANS_R, 20), fill=MUTED, anchor="lm")
    im.save(out, quality=95)
    return out


def render_news(data, out):
    """Post 1080x1350. Sem foto (não deve acontecer) usa o desenho simples."""
    if not (data.get("photo") and os.path.exists(data["photo"])):
        return render_news_plain(data, out)
    return _render_a(data, out, 1080, 1350, 48, 50, 70, 34, 0.2)


def render_news_story(data, out):
    """Story 1080x1920 no mesmo desenho; deixa livres as zonas do Instagram (topo ~250 px, fundo ~340 px)."""
    if not (data.get("photo") and os.path.exists(data["photo"])):
        return render_news_story_plain(data, out)
    return _render_a(data, out, 1080, 1920, 250, 300, 80, 38, 0.15)

if __name__ == "__main__":
    os.makedirs("news_samples", exist_ok=True)
    print("Gerado:", render_rising(SAMPLE_RISING, "news_samples/rising.png"))
    print("Gerado:", render_upset(SAMPLE_UPSET, "news_samples/upset.png"))
