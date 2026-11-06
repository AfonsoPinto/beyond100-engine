"""Carrossel semanal em estilo "bento" (cartões arredondados de tamanhos diferentes, letra Inter Display).
Escolhido em 1/11/2026. O estilo antigo continua disponível com CAROUSEL_STYLE=classic."""
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps

import photo_cards as pc
import webapp

W, H = 1080, 1350
BG, GREEN, DEEP, CREAM, VOLT, SOFT = (10, 34, 26), (15, 61, 46), (9, 40, 30), (247, 242, 230), (217, 242, 61), (157, 176, 167)
DOT_OFF = (40, 80, 64)
_INTER = ["/usr/share/fonts/opentype/inter/", "/usr/share/fonts/truetype/inter/", "fonts/"]
_FILES = {"black": ["InterDisplay-Black.otf", "Inter-Black.otf", "InterDisplay-Black.ttf", "Inter-Black.ttf"],
          "bold": ["InterDisplay-Bold.otf", "Inter-Bold.otf", "InterDisplay-Bold.ttf", "Inter-Bold.ttf"],
          "semi": ["InterDisplay-SemiBold.otf", "Inter-SemiBold.otf", "InterDisplay-SemiBold.ttf", "Inter-SemiBold.ttf"],
          "med": ["InterDisplay-Medium.otf", "Inter-Medium.otf", "InterDisplay-Medium.ttf", "Inter-Medium.ttf"]}
PHOTO_DIR = os.environ.get("PHOTO_DIR", "photos")


def f(weight, size):
    for d in _INTER:
        for n in _FILES[weight]:
            if os.path.exists(d + n):
                return ImageFont.truetype(d + n, size)
    return pc.font(pc.SANS_B, size)                                 # recurso: a sans de sempre


def fit(d, text, weight, size, max_w, min_size=18):
    while size > min_size and d.textlength(text, font=f(weight, size)) > max_w:
        size -= 2
    return f(weight, size)


def photo(name):
    fp = os.path.join(PHOTO_DIR, webapp.slugify(name or "") + ".jpg")
    try:
        return Image.open(fp).convert("RGB") if os.path.exists(fp) else None
    except Exception:
        return None


def credit_of(name):
    try:
        c = json.load(open(os.path.join(PHOTO_DIR, "credits.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return c.get(webapp.slugify(name or "") + ".jpg")


def tile(d, box, fill, r=36):
    d.rounded_rectangle(box, radius=r, fill=fill)


def paste_round(img, ph, box, r=36, gray=False, centering=(0.5, 0.25)):
    x0, y0, x1, y1 = [int(v) for v in box]
    p = ImageOps.fit(ph, (x1 - x0, y1 - y0), centering=centering)
    if gray:
        p = ImageOps.grayscale(p).convert("RGB")
    m = Image.new("L", p.size)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, p.width - 1, p.height - 1], radius=r, fill=255)
    img.paste(p, (x0, y0), m)


def circle(img, ph, cx, cy, r, ring):
    p = ImageOps.fit(ph, (2 * r, 2 * r), centering=(0.5, 0.22))
    m = Image.new("L", p.size)
    ImageDraw.Draw(m).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
    ImageDraw.Draw(img).ellipse([cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4], fill=ring)
    img.paste(p, (cx - r, cy - r), m)


def base(rng, credits=()):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 82), "BEYOND100", font=f("black", 28), fill=CREAM, anchor="ls")
    d.text((W - 60, 82), rng.upper(), font=f("semi", 24), fill=SOFT, anchor="rs")
    return img, d


def footer(img, credits):
    d = ImageDraw.Draw(img)
    cr = pc.credit_join(*[c for c in credits if c]) if credits else None
    d.text((W / 2, 1306 if cr else 1316), "Follow @beyond100.tennis", font=f("bold", 26), fill=SOFT, anchor="mm")
    if cr:
        d.text((W / 2, 1338), cr, font=fit(d, cr, "med", 17, W - 80, 11), fill=SOFT, anchor="mm")


def dots(img, i, n):
    d = ImageDraw.Draw(img)
    for k in range(n):
        x = W / 2 - (n - 1) * 13 + k * 26
        d.ellipse([x - 6, 1268, x + 6, 1280], fill=VOLT if k == i else DOT_OFF)


def _sur(name):
    p = (name or "?").split()
    return " ".join(p[1:]) if len(p) > 1 else p[0]


def _score_list(r):
    w = r["winner"]
    return [f"{a}-{b}" for a, b in zip(r["games"][w - 1], r["games"][2 - w])]


def rng_of(wd):
    return f"{wd['start'].strftime('%b %d')} – {wd['end'].strftime('%b %d')}".replace(" 0", " ")


# ------------------------------------------------------------------ slides
def cover(wd):
    img, d = base(rng_of(wd))
    tile(d, [60, 120, W - 60, 600], GREEN)
    d.text((100, 300), "The week", font=f("black", 130), fill=CREAM, anchor="ls")
    d.text((100, 380), "beyond the top 100", font=f("med", 46), fill=VOLT, anchor="ls")
    d.text((100, 540), "Swipe →", font=f("semi", 30), fill=SOFT, anchor="ls")
    credits = []
    star = next((r for r in wd["finals"] if photo(r["p%d" % r["winner"]]["name"])), None)
    tile(d, [60, 630, 520, 1230], DEEP)
    if star:
        nm = star["p%d" % star["winner"]]["name"]
        paste_round(img, photo(nm), [60, 630, 520, 1230])
        lab = f"{nm.split()[-1]} · {webapp.base_tournament(star.get('tournament', ''))}"
        d.rounded_rectangle([80, 1150, 500, 1210], radius=30, fill=VOLT)
        d.text((290, 1180), lab, font=fit(d, lab, "bold", 26, 380), fill=GREEN, anchor="mm")
        credits.append(credit_of(nm))
    else:
        d.text((290, 930), "🎾", font=f("black", 120), fill=VOLT, anchor="mm")
    s = wd["stats"]
    for k, (n, lab, c, fc) in enumerate([(s["matches"], "matches", VOLT, GREEN), (wd["tournaments"], "tournaments", GREEN, CREAM),
                                        (len(wd["finals"]), "finals", GREEN, CREAM)]):
        y0 = 630 + k * 205
        tile(d, [550, y0, W - 60, y0 + 185], c)
        d.text((590, y0 + 120), str(n), font=f("black", 96), fill=fc, anchor="ls")
        d.text((W - 90, y0 + 112), lab, font=f("semi", 30), fill=fc, anchor="rs")
    return img, credits


LAYOUTS = {1: [(60, 240, W - 60, 1180)],
           2: [(60, 240, W - 60, 700), (60, 720, W - 60, 1180)],
           3: [(60, 240, W - 60, 700), (60, 720, 540, 1180), (560, 720, W - 60, 1180)],
           4: [(60, 240, 540, 700), (560, 240, W - 60, 700), (60, 720, 540, 1180), (560, 720, W - 60, 1180)],
           5: [(60, 240, 540, 700), (560, 240, W - 60, 700), (60, 720, 540, 1180), (560, 720, W - 60, 950), (560, 970, W - 60, 1180)]}


def champions(wd):
    img, d = base(rng_of(wd))
    d.text((60, 200), "Champions", font=f("black", 92), fill=CREAM, anchor="ls")
    fin = wd["finals"][:5]
    credits = []
    for k, (r, box) in enumerate(zip(fin, LAYOUTS[len(fin)])):
        w = r["winner"]
        win, los = r["p%d" % w], r["p%d" % (3 - w)]
        x0, y0, x1, y1 = box
        tile(d, box, VOLT if k == 0 else GREEN)
        fc = GREEN if k == 0 else CREAM
        big = (y1 - y0) > 300
        ph = photo(win["name"])
        if big and ph:
            circle(img, ph, x0 + 110, y0 + 120, 70, fc)
            credits.append(credit_of(win["name"]))
        d = ImageDraw.Draw(img)
        _, _, _, tag = webapp.classify(r)
        t = webapp.base_tournament(r.get("tournament", ""))
        lab = (f"{tag} · {t}" if tag and tag not in t else t).upper()
        ty = y1 - 150 if big else y0 + 70
        d.text((x0 + 36, ty), lab, font=fit(d, lab, "bold", 22, x1 - x0 - 72, 14), fill=fc, anchor="ls")
        d.text((x0 + 36, ty + 52), win["name"], font=fit(d, win["name"], "black", 44, x1 - x0 - 72), fill=fc, anchor="ls")
        d.text((x0 + 36, ty + 100), "  ".join(_score_list(r)) + f"   d. {_sur(los['name'])}", font=fit(d, "  ".join(_score_list(r)) + f"   d. {_sur(los['name'])}", "semi", 30, x1 - x0 - 72, 16), fill=fc, anchor="ls")
    return img, credits


def duel(wd, r, title, note):
    img, d = base(rng_of(wd))
    d.text((60, 200), title, font=fit(d, title, "black", 80, W - 120), fill=CREAM, anchor="ls")
    w = r["winner"]
    credits = []
    for k, p in enumerate((r["p%d" % w], r["p%d" % (3 - w)])):
        x0 = 60 + k * 490
        tile(d, [x0, 240, x0 + 470, 760], GREEN)
        ph = photo(p["name"])
        if ph:
            paste_round(img, ph, [x0, 240, x0 + 470, 760], gray=(k == 1))
            credits.append(credit_of(p["name"]))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([x0 + 20, 680, x0 + 450, 740], radius=30, fill=VOLT if k == 0 else DEEP)
        d.text((x0 + 235, 710), p["name"], font=fit(d, p["name"], "bold", 30, 400), fill=GREEN if k == 0 else SOFT, anchor="mm")
    s = _score_list(r)
    n = len(s)
    gap = 20
    tw = (W - 120 - gap * (n - 1)) / n
    for k, v in enumerate(s):
        x0 = 60 + k * (tw + gap)
        a, b = (int(x) for x in v.split("-")[:2]) if v.count("-") == 1 and all(x.isdigit() for x in v.split("-")) else (1, 0)
        won = a > b
        tile(d, [x0, 790, x0 + tw, 1040], VOLT if won else GREEN)
        d.text((x0 + tw / 2, 915), v, font=fit(d, v, "black", 100, tw - 30), fill=GREEN if won else CREAM, anchor="mm")
    t = webapp.base_tournament(r.get("tournament", ""))
    msg = f"{t} · {r.get('round', '')} · {note}" if note else f"{t} · {r.get('round', '')}"
    tile(d, [60, 1070, W - 60, 1230], DEEP)
    d.text((100, 1165), msg, font=fit(d, msg, "semi", 34, W - 200, 18), fill=SOFT, anchor="ls")
    return img, credits


def closest(wd):
    r = wd["closest"]
    st = webapp.match_stats(r)
    margin = st[4] if st else None
    note = ("won it with fewer games" if margin is not None and margin <= 0
            else f"{margin} game{'s' if margin != 1 else ''} apart" if margin is not None else "")
    return duel(wd, r, "Match of the week", note)


def dominant(wd):
    r = wd["dominant"]
    st = webapp.match_stats(r)
    return duel(wd, r, "Most dominant win", f"won {st[1]}% of the games" if st else "")


def tournaments(wd):
    img, d = base(rng_of(wd))
    d.text((60, 200), "Where the action was", font=fit(d, "Where the action was", "black", 80, W - 120), fill=CREAM, anchor="ls")
    counts = {}
    for r in wd["_rs"]:
        k = (webapp.base_tournament(r.get("tournament", "")), webapp.classify(r)[3])
        counts[k] = counts.get(k, 0) + 1
    y = 240
    for i, ((t, tag), n) in enumerate(sorted(counts.items(), key=lambda kv: -kv[1])[:6]):
        tile(d, [60, y, W - 60, y + 145], VOLT if i == 0 else GREEN)
        fc = GREEN if i == 0 else CREAM
        d.text((100, y + 55), (tag or "").upper(), font=f("bold", 22), fill=fc, anchor="ls")
        d.text((100, y + 105), t, font=fit(d, t, "black", 42, 640), fill=fc, anchor="ls")
        d.text((W - 100, y + 92), f"{n} matches", font=f("semi", 32), fill=fc, anchor="rs")
        y += 162
    return img, []


def numbers(wd):
    img, d = base(rng_of(wd))
    d.text((60, 200), "By the numbers", font=f("black", 88), fill=CREAM, anchor="ls")
    s = wd["stats"]
    items = [(s["three"], "third sets", (60, 240, 620, 700), VOLT), (s["tb"], "tie-breaks", (640, 240, W - 60, 700), GREEN),
             (s["comebacks"], "comebacks", (60, 720, 460, 1230), GREEN), (s["bagels"], "6-0 sets", (480, 720, W - 60, 1230), DEEP)]
    for n, lab, box, c in items:
        tile(d, box, c)
        fc = GREEN if c == VOLT else CREAM
        d.text((box[0] + 40, box[3] - 120), str(n), font=fit(d, str(n), "black", 170, box[2] - box[0] - 80), fill=fc, anchor="ls")
        d.text((box[0] + 44, box[3] - 60), lab, font=f("semi", 34), fill=fc, anchor="ls")
    return img, []


def cta(wd):
    img, d = base(rng_of(wd))
    tile(d, [60, 120, W - 60, 760], GREEN)
    d.text((100, 330), "Tennis beyond", font=f("black", 100), fill=CREAM, anchor="ls")
    d.text((100, 440), "the top 100", font=f("black", 100), fill=VOLT, anchor="ls")
    d.text((100, 540), "Results, stats and stories from", font=f("med", 38), fill=SOFT, anchor="ls")
    d.text((100, 590), "Challenger, ITF and WTA events.", font=f("med", 38), fill=SOFT, anchor="ls")
    tile(d, [60, 790, W - 60, 990], VOLT)
    d.text((W / 2, 890), "Follow · Save · Share", font=f("black", 56), fill=GREEN, anchor="mm")
    tile(d, [60, 1020, W - 60, 1230], DEEP)
    d.text((W / 2, 1125), "beyond100tennis.com", font=f("bold", 44), fill=CREAM, anchor="mm")
    return img, []


def build(wd):
    """Sempre 5 slides (a Make precisa de um número fixo): capa, 2 de conteúdo, números, apelo."""
    parts = [cover(wd), champions(wd) if wd["finals"] else tournaments(wd),
             closest(wd) if wd["closest"] else dominant(wd), numbers(wd), cta(wd)]
    out = []
    for i, (img, credits) in enumerate(parts):
        dots(img, i, len(parts))
        footer(img, credits)
        out.append(img)
    return out
