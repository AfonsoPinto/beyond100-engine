"""Cartões de resultado "modernos" (proposta de 9/11/2026), iguais para ténis e padel (só mudam as cores).
  A "scorebug"  : foto a toda a altura, nome enorme em baixo e o resultado em colunas, como os grafismos de TV
  B "poster"    : foto em cima com corte inclinado, apelido gigante condensado e os sets em números grandes
  C "app"       : foto a toda a altura e um placar flutuante (vidro escuro) com os dois lados, como numa app de resultados
d = {sport, kicker, level, tournament, round, date, winners:[{name, short, country, rank}], losers:[...], sets:[(w,l)],
     photo, credit, line (frase curta, opcional), handle (opcional)}
Sem foto boa não há cartão (regra do Afonso, 9/11/2026)."""
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1080, 1350
INTER = "/usr/share/fonts/opentype/inter/"
PALETTE = {"tennis": {"bg": (8, 34, 26), "mid": (14, 58, 45), "acc": (217, 242, 61), "cream": (247, 242, 230), "soft": (176, 196, 183),
                      "brand": "BEYOND100", "follow": "@beyond100.tennis"},
           "padel": {"bg": (6, 26, 44), "mid": (12, 46, 74), "acc": (217, 242, 61), "cream": (247, 242, 230), "soft": (169, 192, 214),
                     "brand": "BEYOND PADEL", "follow": "@beyond100.padel"}}


def F(weight, size):
    names = {"black": ["InterDisplay-Black.otf", "Inter-Black.otf"], "xb": ["InterDisplay-ExtraBold.otf", "Inter-ExtraBold.otf"],
             "bold": ["InterDisplay-Bold.otf", "Inter-Bold.otf"], "semi": ["InterDisplay-SemiBold.otf", "Inter-SemiBold.otf"],
             "med": ["InterDisplay-Medium.otf", "Inter-Medium.otf"]}[weight]
    for d in (INTER, os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/", "/usr/share/fonts/truetype/inter/"):
        for n in names:
            if os.path.exists(d + n):
                return ImageFont.truetype(d + n, size)
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


def _fit(d, text, weight, size, maxw, minsize=20):
    while size > minsize and d.textlength(text, font=F(weight, size)) > maxw:
        size -= 2
    return F(weight, size)


def _squeeze(text, weight, size, color, sx=0.78, track=-2):
    """Texto condensado (Inter Black comprimido na horizontal): imagem RGBA recortada."""
    f = F(weight, size)
    tmp = Image.new("RGBA", (int(len(text) * size * 1.1) + 40, int(size * 1.4)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    x = 0
    for ch in text:
        d.text((x, 0), ch, font=f, fill=color)
        x += d.textlength(ch, font=f) + track
    bb = tmp.getbbox() or (0, 0, 1, 1)
    tmp = tmp.crop(bb)
    return tmp.resize((max(1, int(tmp.width * sx)), tmp.height), Image.LANCZOS)


def _paste_sq(img, text, weight, size, color, x, y, maxw, sx=0.78, anchor="lt"):
    t = _squeeze(text, weight, size, color, sx)
    if t.width > maxw:
        t = t.resize((maxw, max(1, int(t.height * maxw / t.width))), Image.LANCZOS)
    if anchor == "lb":
        y -= t.height
    elif anchor == "rb":
        x -= t.width
        y -= t.height
    img.paste(t, (int(x), int(y)), t)
    return t.width, t.height


def _photo(fp, size, centering=(0.5, 0.22)):
    return ImageOps.fit(Image.open(fp).convert("RGB"), size, Image.LANCZOS, centering=centering).convert("RGBA")


def _grad(img, y0, y1, color, a0, a1):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for y in range(y0, y1):
        a = int(a0 + (a1 - a0) * (y - y0) / max(1, y1 - y0))
        d.line([(0, y), (img.width, y)], fill=color + (a,))
    return Image.alpha_composite(img, ov)


def _chips(d, x, y, labels, P, size=24):
    for i, lab in enumerate([l for l in labels if l]):
        f = F("bold", size)
        tw = d.textlength(lab, font=f) + 30
        fill, fg = (P["acc"], P["bg"]) if i == 0 else (P["cream"], P["bg"])
        d.rounded_rectangle([x, y, x + tw, y + size + 22], radius=(size + 22) // 2, fill=fill)
        d.text((x + tw / 2, y + (size + 22) / 2), lab, font=f, fill=fg, anchor="mm")
        x += tw + 10


def _side(ps, short=False):
    if len(ps) == 1:
        return ps[0]["name"]
    return " / ".join((p.get("short") or p["name"].split()[-1]) for p in ps)


def _meta(ps):
    return "  ·  ".join(" ".join(x for x in [p.get("country") or "", f"#{p['rank']}" if p.get("rank") else ""] if x) for p in ps)


def _footer(img, d, P, credit):
    d.text((60, H - 46), P["follow"], font=F("semi", 24), fill=P["cream"], anchor="ls")
    if credit:
        d.text((W - 60, H - 46), credit, font=_fit(d, credit, "med", 18, 560, 12), fill=P["soft"], anchor="rs")


# ------------------------------------------------------------------ A: scorebug
def card_a(d_, out):
    P = PALETTE[d_.get("sport", "tennis")]
    img = Image.new("RGBA", (W, H), P["bg"] + (255,))
    img.alpha_composite(_photo(d_["photo"], (W, H)))
    img = _grad(img, 0, 260, (0, 0, 0), 150, 0)
    img = _grad(img, 640, H, P["bg"], 0, 250).convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    d.text((60, 92), P["brand"], font=F("black", 30), fill=P["cream"], anchor="ls")
    _chips(d, 60, 128, [d_.get("kicker"), d_.get("level")], P)
    if d_.get("line"):
        d.text((60, 790), d_["line"].upper(), font=_fit(d, d_["line"].upper(), "bold", 30, W - 120), fill=P["acc"], anchor="ls")
    wname = _side(d_["winners"]).upper()
    _paste_sq(img, wname, "black", 150, P["cream"] + (255,), 56, 960, W - 120, anchor="lb")
    d = ImageDraw.Draw(img, "RGBA")
    d.text((60, 1000), _meta(d_["winners"]), font=F("semi", 26), fill=P["soft"], anchor="ls")
    # tabela de sets (estilo TV)
    y0, rows = 1050, [(d_["winners"], True), (d_["losers"], False)]
    n = len(d_["sets"])
    cw = 74
    x_sets = W - 60 - n * cw
    for k, (ps, win) in enumerate(rows):
        y = y0 + k * 82
        d.rounded_rectangle([60, y, W - 60, y + 72], radius=18, fill=(255, 255, 255, 34) if win else (0, 0, 0, 90))
        nm = _side(ps)
        d.text((88, y + 48), nm, font=_fit(d, nm, "bold" if win else "semi", 32, x_sets - 120), fill=P["cream"] if win else P["soft"], anchor="ls")
        for i, (a, b) in enumerate(d_["sets"]):
            v, o = (a, b) if win else (b, a)
            cx = x_sets + i * cw + cw / 2
            if v > o:
                d.rounded_rectangle([cx - 30, y + 10, cx + 30, y + 62], radius=12, fill=P["acc"])
            d.text((cx, y + 49), str(v), font=F("black", 36), fill=P["bg"] if v > o else (P["cream"] if win else P["soft"]), anchor="ms")
    sub = " · ".join(x for x in [d_.get("tournament"), d_.get("round"), d_.get("date")] if x).upper()
    d.text((60, 1236), sub, font=_fit(d, sub, "semi", 24, W - 120), fill=P["soft"], anchor="ls")
    _footer(img, d, P, d_.get("credit"))
    img.convert("RGB").save(out, quality=94)
    return out


# ------------------------------------------------------------------ B: poster
def card_b(d_, out):
    P = PALETTE[d_.get("sport", "tennis")]
    img = Image.new("RGBA", (W, H), P["bg"] + (255,))
    ph = _photo(d_["photo"], (W, 900))
    m = Image.new("L", (W, 900), 255)
    ImageDraw.Draw(m).polygon([(0, 900), (W, 760), (W, 900)], fill=0)       # corte inclinado em baixo
    img.paste(ph, (0, 0), m)
    img = _grad(img, 0, 240, (0, 0, 0), 140, 0)
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon([(0, 902), (W, 762), (W, 776), (0, 916)], fill=P["acc"])
    d.text((60, 92), P["brand"], font=F("black", 30), fill=P["cream"], anchor="ls")
    _chips(d, 60, 128, [d_.get("kicker"), d_.get("level")], P)
    w = d_["winners"]
    last = (w[0].get("short") or w[0]["name"].split()[-1]).upper() if len(w) == 1 else _side(w).upper()
    first = w[0]["name"].split()[0].upper() if len(w) == 1 else ""
    if first:
        d.text((62, 700), first, font=F("bold", 40), fill=P["cream"], anchor="ls")
    img = _grad(img, 560, 900, (0, 0, 0), 0, 120).convert("RGB")
    _paste_sq(img, last, "black", 210, P["cream"] + (255,), 52, 890, W - 110, sx=0.72, anchor="lb")
    d = ImageDraw.Draw(img, "RGBA")
    # sets em números grandes
    x = 60
    for a, b in d_["sets"]:
        s = f"{a}-{b}"
        f = F("black", 92)
        d.text((x, 1060), s, font=f, fill=P["acc"] if a > b else P["soft"], anchor="ls")
        x += d.textlength(s, font=f) + 40
    los = "def. " + _side(d_["losers"]) + ("  " + _meta(d_["losers"]) if _meta(d_["losers"]) else "")
    d.text((60, 1120), los, font=_fit(d, los, "semi", 30, W - 120), fill=P["cream"], anchor="ls")
    sub = " · ".join(x for x in [d_.get("tournament"), d_.get("round"), d_.get("date")] if x).upper()
    d.text((60, 1172), sub, font=_fit(d, sub, "semi", 24, W - 120), fill=P["soft"], anchor="ls")
    if d_.get("line"):
        d.text((60, 1226), d_["line"], font=_fit(d, d_["line"], "bold", 30, W - 120), fill=P["acc"], anchor="ls")
    _footer(img, d, P, d_.get("credit"))
    img.convert("RGB").save(out, quality=94)
    return out


# ------------------------------------------------------------------ C: app
def card_c(d_, out):
    P = PALETTE[d_.get("sport", "tennis")]
    img = Image.new("RGBA", (W, H), P["bg"] + (255,))
    img.alpha_composite(_photo(d_["photo"], (W, H)))
    img = _grad(img, 0, 260, (0, 0, 0), 140, 0)
    img = _grad(img, 700, H, (0, 0, 0), 0, 160)
    # placar flutuante em vidro
    box = (48, 860, W - 48, 1260)
    blur = img.crop(box).filter(ImageFilter.GaussianBlur(28))
    tint = Image.new("RGBA", blur.size, P["bg"] + (190,))
    glass = Image.alpha_composite(blur, tint)
    m = Image.new("L", blur.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, blur.width - 1, blur.height - 1], radius=36, fill=255)
    img.paste(glass, box[:2], m)
    img = img.convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle(box, radius=36, outline=(255, 255, 255, 60), width=2)
    d.text((60, 92), P["brand"], font=F("black", 30), fill=P["cream"], anchor="ls")
    _chips(d, 60, 128, [d_.get("kicker"), d_.get("level")], P)
    big = (d_.get("line") or _side(d_["winners"])).upper()          # sem frase do jogo: os nomes de quem ganhou
    if big:
        _paste_sq(img, big, "black", 96, P["cream"] + (255,), 60, 830, W - 120, anchor="lb")
        d = ImageDraw.Draw(img, "RGBA")
    x0, y0 = box[0] + 40, box[1] + 40
    sub = " · ".join(x for x in [d_.get("tournament"), d_.get("round")] if x).upper()
    d.text((x0, y0 + 20), sub, font=_fit(d, sub, "bold", 24, 640), fill=P["soft"], anchor="ls")
    d.text((box[2] - 40, y0 + 20), (d_.get("date") or "").upper(), font=F("semi", 22), fill=P["soft"], anchor="rs")
    n = len(d_["sets"])
    cw = 78
    xs = box[2] - 40 - n * cw
    for k, (ps, win) in enumerate([(d_["winners"], True), (d_["losers"], False)]):
        y = y0 + 60 + k * 130
        nm = _side(ps)
        d.text((x0, y + 52), nm, font=_fit(d, nm, "xb" if win else "semi", 44, xs - x0 - 60), fill=P["cream"] if win else P["soft"], anchor="ls")
        d.text((x0, y + 92), _meta(ps), font=F("med", 24), fill=P["soft"], anchor="ls")
        if win:
            d.ellipse([xs - 44, y + 30, xs - 26, y + 48], fill=P["acc"])
        for i, (a, b) in enumerate(d_["sets"]):
            v, o = (a, b) if win else (b, a)
            d.text((xs + i * cw + cw / 2, y + 62), str(v), font=F("black", 60), fill=P["acc"] if v > o else (255, 255, 255, 110), anchor="ms")
    _footer(img, d, P, d_.get("credit"))
    img.convert("RGB").save(out, quality=94)
    return out


# ------------------------------------------------------------------ campeão no mesmo estilo (9/11/2026)
def card_champion(d_, out):
    """d_ = {sport, name, rank, photo, credit, tournament, level, date, final:{opp, opp_rank, sets}, road:[(ronda, nome, rank)]}"""
    P = PALETTE[d_.get("sport", "tennis")]
    img = Image.new("RGBA", (W, H), P["bg"] + (255,))
    img.alpha_composite(_photo(d_["photo"], (W, H)))
    img = _grad(img, 0, 260, (0, 0, 0), 140, 0)
    img = _grad(img, 600, H, (0, 0, 0), 0, 170)
    road = [x for x in (d_.get("road") or []) if x[0] != "F"][-5:]       # a final já está na linha do resultado
    top = H - 100 - (200 + 50 * len(road))
    box = (48, top, W - 48, H - 90)
    blur = img.crop(box).filter(ImageFilter.GaussianBlur(28))
    glass = Image.alpha_composite(blur, Image.new("RGBA", blur.size, P["bg"] + (195,)))
    m = Image.new("L", blur.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, blur.width - 1, blur.height - 1], radius=36, fill=255)
    img.paste(glass, box[:2], m)
    img = img.convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle(box, radius=36, outline=(255, 255, 255, 60), width=2)
    d.text((60, 92), P["brand"], font=F("black", 30), fill=P["cream"], anchor="ls")
    _chips(d, 60, 128, ["CHAMPION", d_.get("level")], P)
    nm = d_["name"].split()
    first, last = (" ".join(nm[:-1]), nm[-1]) if len(nm) > 1 else ("", nm[0])
    if first:
        d.text((62, top - 170), first.upper(), font=F("bold", 38), fill=P["cream"], anchor="ls")
    _paste_sq(img, last.upper(), "black", 170, P["cream"] + (255,), 56, top - 24, W - 300, anchor="lb")
    d = ImageDraw.Draw(img, "RGBA")
    if d_.get("rank"):
        d.text((W - 60, top - 34), f"#{d_['rank']}", font=F("black", 64), fill=P["acc"], anchor="rs")
    x0, y0 = box[0] + 40, box[1] + 40
    sub = " · ".join(x for x in [d_.get("tournament"), "Final"] if x).upper()
    d.text((x0, y0 + 20), sub, font=_fit(d, sub, "bold", 24, 640), fill=P["soft"], anchor="ls")
    d.text((box[2] - 40, y0 + 20), (d_.get("date") or "").upper(), font=F("semi", 22), fill=P["soft"], anchor="rs")
    x = x0
    for a, b in d_["final"]["sets"]:
        s = f"{a}-{b}"
        f = F("black", 64)
        d.text((x, y0 + 100), s, font=f, fill=P["acc"] if a > b else P["soft"], anchor="ls")
        x += d.textlength(s, font=f) + 34
    opp = "def. " + (d_["final"].get("opp") or "") + (f"  #{d_['final']['opp_rank']}" if d_["final"].get("opp_rank") else "")
    d.text((x, y0 + 96), opp, font=_fit(d, opp, "semi", 28, box[2] - 40 - x), fill=P["cream"], anchor="ls")
    y = y0 + 150
    for rd, n_, rk in road:
        d.line([(x0, y - 4), (box[2] - 40, y - 4)], fill=(255, 255, 255, 40), width=1)
        d.text((x0, y + 34), rd, font=F("black", 26), fill=P["acc"], anchor="ls")
        d.text((x0 + 80, y + 34), n_, font=_fit(d, n_, "semi", 30, 560), fill=P["cream"], anchor="ls")
        if rk:
            d.text((box[2] - 40, y + 34), f"#{rk}", font=F("semi", 26), fill=P["soft"], anchor="rs")
        y += 50
    _footer(img, d, P, d_.get("credit"))
    img.convert("RGB").save(out, quality=94)
    return out
