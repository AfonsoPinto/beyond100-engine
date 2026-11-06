"""Cartão de "feature" (listas com contexto: Qualifier watch, Climbers, antevisões), o mesmo molde no ténis e no padel.
Em cima: foto REAL e livre do lugar (cidade-sede) ou do protagonista, com retratos redondos de jogadores (nome por baixo de cada um).
Em baixo: título grande, subtítulo e linhas modernas. Só fotos com licença livre e crédito; nada gerado por IA.

feature_card(d, out, theme="tennis")
d = {tags:[str], title, subtitle, place:{path,credit}|None, photos:[{path,credit,label}], rows:[{left,name,sub,right,hot}],
     section: str|None, foot: str|None}"""
from PIL import Image, ImageDraw

import photo_cards as pc

W, H = pc.W, pc.H
THEMES = {
    "tennis": {"top": (17, 66, 51), "bottom": (8, 34, 26), "deep": pc.DEEP, "edge": pc.EDGE, "ink": pc.GREEN, "soft": pc.SOFT,
               "shade": (8, 34, 26), "brand": "BEYOND100", "follow": "Follow @beyond100.tennis"},
    "padel": {"top": (16, 58, 92), "bottom": (6, 26, 44), "deep": (8, 34, 58), "edge": (36, 80, 122), "ink": (12, 46, 74), "soft": (169, 192, 214),
              "shade": (6, 26, 44), "brand": "BEYOND PADEL", "follow": "Follow @beyond100.padel"},
}
CREAM, VOLT = pc.CREAM, pc.VOLT


def _fill(fp, size, centering=(0.5, 0.25)):
    from PIL import ImageOps
    with Image.open(fp) as im:
        return ImageOps.fit(im.convert("RGB"), size, Image.LANCZOS, centering=centering)


def _shade(img, y0, y1, a0, a1, col):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for y in range(y0, y1):
        od.line([(0, y), (img.width, y)], fill=col + (int(a0 + (a1 - a0) * (y - y0) / max(1, y1 - y0)),))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def feature_card(d, out, theme="tennis"):
    T = THEMES[theme]
    img = Image.new("RGB", (W, H))
    g = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        g.line([(0, y), (W, y)], fill=tuple(int(T["top"][i] + (T["bottom"][i] - T["top"][i]) * t) for i in range(3)))
    credits = []
    band = 640
    pl = d.get("place") or {}
    if pl.get("path"):
        img.paste(_fill(pl["path"], (W, band), (0.5, 0.5)), (0, 0))
        if pl.get("credit"):
            credits.append(pl["credit"])
    img = _shade(img, 0, 260, 170, 0, T["shade"])
    img = _shade(img, 300, band, 0, 255, T["shade"])
    phs = [p for p in d.get("photos") or [] if p and p.get("path")][:3]
    R = 118 if len(phs) <= 2 else 100
    for i, ph in enumerate(phs):
        cx, cy = W - 70 - R - i * (2 * R + 36), 360 if pl.get("path") else 330
        face = _fill(ph["path"], (2 * R, 2 * R), (0.5, 0.25))
        mask = Image.new("L", (2 * R, 2 * R), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255)
        dr_ = ImageDraw.Draw(img)
        dr_.ellipse([cx - R - 7, cy - R - 7, cx + R + 7, cy + R + 7], fill=VOLT)
        img.paste(face, (cx - R, cy - R), mask)
        if ph.get("credit"):
            credits.append(ph["credit"])
        lab = (ph.get("label") or "").upper()
        if lab:
            f_ = pc.fit(dr_, lab, pc.SANS_B, 20, 2 * R + 30, 12)
            tw = dr_.textlength(lab, font=f_) + 26
            dr_.rounded_rectangle([cx - tw / 2, cy + R + 14, cx + tw / 2, cy + R + 48], radius=17, fill=CREAM)
            dr_.text((cx, cy + R + 31), lab, font=f_, fill=T["ink"], anchor="mm")
    dr = ImageDraw.Draw(img)
    # marca e etiquetas (canto superior esquerdo, como no padel)
    f = pc.font(pc.SERIF_B, 30)
    bt = T["brand"]
    tw = sum(dr.textlength(c, font=f) for c in bt) + 8 * (len(bt) - 1)
    dr.rounded_rectangle([70, 46, 70 + tw + 56, 110], radius=32, fill=CREAM)
    pc.spaced(dr, 70 + (tw + 56) / 2, 78, bt, f, T["ink"], 8)
    x = 70
    for i, lab in enumerate([t for t in d.get("tags") or [] if t]):
        ft = pc.font(pc.SANS_B, 26)
        w_ = dr.textlength(lab, font=ft) + 36
        dr.rounded_rectangle([x, 150, x + w_, 196], radius=23, fill=VOLT if i == 0 else CREAM)
        dr.text((x + w_ / 2, 173), lab, font=ft, fill=T["ink"], anchor="mm")
        x += w_ + 12
    ty = 620 if pl.get("path") else 590                              # sem foto do lugar: o título sobe e as linhas ganham espaço
    t = (d.get("title") or "").upper()
    dr.text((70, ty), t, font=pc.fit(dr, t, pc.SANS_B, 96, W - 140, 44), fill=CREAM, anchor="ls")
    if d.get("subtitle"):
        s = d["subtitle"].upper()
        dr.text((70, ty + 48), s, font=pc.fit(dr, s, pc.SANS_B, 26, W - 140, 14), fill=VOLT, anchor="ls")
    rows = d.get("rows") or []
    y = ty + 92
    if d.get("section"):
        dr.text((76, y + 18), d["section"].upper(), font=pc.font(pc.SANS_B, 24), fill=T["soft"], anchor="ls")
        y += 36
    nsec = sum(1 for r in rows if r.get("section"))
    nreal = max(1, len(rows) - nsec)
    h = min(112, int((1196 - y - nsec * 44) / nreal) - 12)
    for r in rows:
        if r.get("section"):
            dr.text((76, y + 30), r["section"].upper(), font=pc.font(pc.SANS_B, 24), fill=T["soft"], anchor="ls")
            y += 44
            continue
        hot = r.get("hot")
        dr.rounded_rectangle([60, y, W - 60, y + h], radius=24, fill=T["deep"], outline=VOLT if hot else T["edge"], width=3 if hot else 2)
        k = h / 100
        dr.text((96, y + h / 2), str(r.get("left") or ""), font=pc.font(pc.SERIF_B, int(40 * k)), fill=VOLT, anchor="lm")
        right = str(r.get("right") or "")
        fr = pc.fit(dr, right, pc.SANS_B, int(30 * k), 300, 14)
        rw = dr.textlength(right, font=fr) if right else 0
        if right:
            pw = rw + 34
            dr.rounded_rectangle([W - 90 - pw, y + h / 2 - 24 * k, W - 90, y + h / 2 + 24 * k], radius=int(24 * k), fill=VOLT if hot else T["edge"])
            dr.text((W - 90 - pw / 2, y + h / 2), right, font=fr, fill=T["ink"] if hot else CREAM, anchor="mm")
        nm = r.get("name") or ""
        maxw = int(W - 90 - (rw + 34 if right else 0) - 30 - 190)
        if r.get("sub"):
            dr.text((190, y + h / 2 - 4), nm, font=pc.fit(dr, nm, pc.SERIF_B, int(38 * k), maxw, 16), fill=CREAM, anchor="ls")
            dr.text((190, y + h / 2 + 30 * k), r["sub"], font=pc.fit(dr, r["sub"], pc.SANS_B, int(22 * k), maxw, 12), fill=T["soft"], anchor="ls")
        else:
            dr.text((190, y + h / 2), nm, font=pc.fit(dr, nm, pc.SERIF_B, int(38 * k), maxw, 16), fill=CREAM, anchor="lm")
        y += h + 12
    cols = [(lab, rs) for lab, rs in d.get("cols") or [] if rs]          # duas colunas lado a lado (ex.: homens | mulheres)
    if cols:
        gap = 24
        cw = (W - 120 - gap * (len(cols) - 1)) / len(cols)
        n_ = max(len(rs) for _, rs in cols)
        hh = min(104, int((1196 - y - 40) / n_) - 12)
        for c_, (lab, rs) in enumerate(cols):
            x0 = 60 + c_ * (cw + gap)
            dr.text((x0 + 6, y + 26), lab.upper(), font=pc.font(pc.SANS_B, 24), fill=T["soft"], anchor="ls")
            yy = y + 44
            for r in rs:
                hot = r.get("hot")
                dr.rounded_rectangle([x0, yy, x0 + cw, yy + hh], radius=22, fill=T["deep"], outline=VOLT if hot else T["edge"], width=3 if hot else 2)
                dr.text((x0 + 24, yy + hh / 2), str(r.get("left") or ""), font=pc.font(pc.SERIF_B, 36), fill=VOLT, anchor="lm")
                right = str(r.get("right") or "")
                rw = 0
                if right:
                    fr = pc.font(pc.SANS_B, 20)
                    rw = dr.textlength(right, font=fr) + 24
                    dr.rounded_rectangle([x0 + cw - 18 - rw, yy + 14, x0 + cw - 18, yy + 44], radius=15, fill=VOLT if hot else T["edge"])
                    dr.text((x0 + cw - 18 - rw / 2, yy + 29), right, font=fr, fill=T["ink"] if hot else CREAM, anchor="mm")
                mw = int(cw - 76 - 24)
                nm = r.get("name") or ""
                dr.text((x0 + 76, yy + hh / 2 + (0 if not r.get("sub") else -4)), nm, font=pc.fit(dr, nm, pc.SERIF_B, 30, mw - rw - 8, 14),
                        fill=CREAM, anchor="ls" if r.get("sub") else "lm")
                if r.get("sub"):
                    dr.text((x0 + 76, yy + hh / 2 + 26), r["sub"], font=pc.fit(dr, r["sub"], pc.SANS_B, 20, mw, 12), fill=T["soft"], anchor="ls")
                yy += hh + 12
    if d.get("foot"):
        dr.text((W / 2, 1238), d["foot"], font=pc.fit(dr, d["foot"], pc.SERIF_I, 30, W - 140, 16), fill=CREAM, anchor="mm")
    dr.text((W / 2, 1292), T["follow"], font=pc.font(pc.SANS_B, 30), fill=CREAM, anchor="mm")
    cr = pc.credit_join(*credits)
    if cr:
        dr.text((W - 40, 1334), cr, font=pc.fit(dr, cr, pc.SANS_B, 18, W - 200, 12), fill=T["soft"], anchor="rm")
    img.save(out, quality=95)
    return out
