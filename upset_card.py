"""Cartão de SURPRESA GIGANTE (o derrotado é um nome muito conhecido): as caras dos dois jogadores.
Vencedor a cores e em destaque; derrotado a preto e branco. Só fotos licenciadas, com o crédito das duas.
render_giant_upset(d, out, variant="A"|"B"|"C"); d = o mesmo de photo_cards.render_match_photo."""
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

import photo_cards as pc

W, H = pc.W, pc.H
RED = pc.RED_TAG


def _ph(who, size, centering=(0.5, 0.2), grey=False):
    im, ok = pc._photo_or_monogram(size, who, centering)
    if grey and ok:
        im = ImageOps.grayscale(im).convert("RGB")
        im = ImageEnhance.Brightness(im).enhance(0.72)
    return im


def _shade(img, box, a0, a1, col=(5, 22, 17), vertical=True):
    x0, y0, x1, y1 = box
    ov = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    n = (y1 - y0) if vertical else (x1 - x0)
    for i in range(n):
        a = int(a0 + (a1 - a0) * i / max(1, n - 1))
        if vertical:
            od.line([(0, i), (x1 - x0, i)], fill=col + (a,))
        else:
            od.line([(i, 0), (i, y1 - y0)], fill=col + (a,))
    img.paste(ov, (x0, y0), ov)


def _pill(dr, x, y, text, fill, fg, size=26, anchor_right=False):
    f = pc.font(pc.SANS_B, size)
    tw = dr.textlength(text, font=f) + 36
    if anchor_right:
        x -= tw
    dr.rounded_rectangle([x, y, x + tw, y + size + 20], radius=(size + 20) // 2, fill=fill)
    dr.text((x + tw / 2, y + (size + 20) / 2), text, font=f, fill=fg, anchor="mm")
    return tw


def _rk(p):
    r = p.get("rank")
    return f"#{r}" if isinstance(r, int) and r > 0 else ""


def _credit(dr, d):
    cr = pc.credit_join(d["winner"].get("credit"), d["loser"].get("credit"))
    if cr:
        dr.text((W - 40, 1334), cr, font=pc.fit(dr, cr, pc.SANS_B, 17, W - 120, 11), fill=pc.SOFT, anchor="rm")


def _score_line(d):
    return "  ".join(f"{a}-{b}" for a, b in d["sets"])


def _variant_a(d):
    """Lado a lado: vencedor (60%, a cores) | derrotado (40%, preto e branco), bloco de texto por baixo."""
    win, los = d["winner"], d["loser"]
    img = pc._gradient((17, 66, 51), (8, 34, 26))
    WW, PH = 640, 900
    img.paste(_ph(win, (WW, PH)), (0, 0))
    img.paste(_ph(los, (W - WW, PH), grey=True), (WW, 0))
    _shade(img, (0, 0, W, 240), 170, 0)
    _shade(img, (0, 520, W, PH), 0, 255, (8, 34, 26))
    dr = ImageDraw.Draw(img)
    dr.rectangle([WW - 3, 0, WW + 3, PH - 120], fill=pc.VOLT)
    # "DEF." no meio da linha divisória
    dr.ellipse([WW - 56, 300, WW + 56, 412], fill=pc.VOLT)
    dr.text((WW, 356), "DEF.", font=pc.font(pc.SANS_B, 30), fill=pc.GREEN, anchor="mm")
    pc.spaced(dr, 70 + 140, 78, "BEYOND100", pc.font(pc.SERIF_B, 30), pc.CREAM, 8)
    x = 70
    x += _pill(dr, x, 140, "GIANT UPSET", RED, pc.CREAM) + 12
    if d.get("level"):
        _pill(dr, x, 140, d["level"], pc.VOLT, pc.GREEN)
    # nomes por cima das fotos
    dr.text((70, 790), (win.get("name") or "").upper(), font=pc.fit(dr, (win.get("name") or "").upper(), pc.SANS_B, 40, WW - 110, 20), fill=pc.CREAM, anchor="ls")
    dr.text((70, 836), _rk(win), font=pc.font(pc.SERIF_B, 40), fill=pc.VOLT, anchor="ls")
    ln = (los.get("name") or "").upper()
    dr.text((W - 50, 790), ln, font=pc.fit(dr, ln, pc.SANS_B, 32, W - WW - 80, 16), fill=pc.SOFT, anchor="rs")
    dr.text((W - 50, 836), _rk(los), font=pc.font(pc.SERIF_B, 40), fill=pc.SOFT, anchor="rs")
    head = (d.get("edit_head") or d.get("headline") or "").strip().rstrip(".").upper()
    y = 960
    if head:
        s = pc._sq_fit(head, 96, W - 140)
        pc._sq_text(img, 70, y, head, s, pc.CREAM)
        y += int(s * 0.95) + 28
    dr = ImageDraw.Draw(img)
    # resultado em fichas
    tx = 70
    for a, b in d["sets"]:
        won = a > b
        dr.rounded_rectangle([tx, y, tx + 150, y + 84], radius=20, fill=pc.VOLT if won else None, outline=pc.VOLT, width=3)
        dr.text((tx + 75, y + 42), f"{a}-{b}", font=pc.font(pc.SERIF_B, 42), fill=pc.GREEN if won else pc.CREAM, anchor="mm")
        tx += 166
    sub = " · ".join(v for v in [d.get("tournament"), d.get("round")] if v).upper()
    dr.text((70, y + 140), sub, font=pc.fit(dr, sub, pc.SANS_B, 28, W - 140, 16), fill=pc.SOFT, anchor="ls")
    if win.get("handle"):
        dr.text((W - 70, y + 140), win["handle"], font=pc.font(pc.SANS_B, 24), fill=pc.CREAM, anchor="rs")
    dr.text((W / 2, 1292), pc.BRAND, font=pc.font(pc.SANS_B, 28), fill=pc.CREAM, anchor="mm")
    _credit(dr, d)
    return img


def _variant_b(d):
    """Corte diagonal vertical: vencedor à esquerda (a cores), derrotado à direita (P&B); nomes e resultado em baixo."""
    win, los = d["winner"], d["loser"]
    img = pc._gradient((17, 66, 51), (8, 34, 26))
    PH = 980
    right = _ph(los, (560, PH), (0.5, 0.2), grey=True)
    img.paste(right, (W - 560, 0))
    left = _ph(win, (760, PH), (0.5, 0.15))
    mask = Image.new("L", (760, PH), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (760, 0), (560, PH), (0, PH)], fill=255)
    img.paste(left, (0, 0), mask)
    dr = ImageDraw.Draw(img)
    dr.line([(760, 0), (560, PH)], fill=pc.VOLT, width=10)
    _shade(img, (0, 0, W, 240), 170, 0)
    _shade(img, (0, 640, W, PH), 0, 255, (8, 34, 26))
    dr = ImageDraw.Draw(img)
    pc.spaced(dr, 70 + 140, 78, "BEYOND100", pc.font(pc.SERIF_B, 30), pc.CREAM, 8)
    x = 70
    x += _pill(dr, x, 140, "GIANT UPSET", RED, pc.CREAM) + 12
    if d.get("level"):
        _pill(dr, x, 140, d["level"], pc.VOLT, pc.GREEN)
    ln = (los.get("name") or "").upper()
    dr.text((W - 50, 880), ln, font=pc.fit(dr, ln, pc.SANS_B, 30, 420, 16), fill=pc.SOFT, anchor="rs")
    dr.text((W - 50, 926), _rk(los), font=pc.font(pc.SERIF_B, 40), fill=pc.SOFT, anchor="rs")
    wn = (win.get("name") or "").upper()
    s1 = pc._sq_fit(wn, 130, 560)
    pc._sq_text(img, 70, 930 - int(s1 * 0.95), wn, s1, pc.CREAM)
    dr = ImageDraw.Draw(img)
    y = 980
    # resultado grande numa linha, "def." antes
    dr.text((70, y + 40), "DEF.", font=pc.font(pc.SANS_B, 30), fill=pc.SOFT, anchor="ls")
    tx = 170
    for a, b in d["sets"]:
        t = f"{a}-{b}"
        f = pc.font(pc.SERIF_B, 64)
        dr.text((tx, y + 46), t, font=f, fill=pc.VOLT if a > b else pc.SOFT, anchor="ls")
        tx += dr.textlength(t, font=f) + 40
    if _rk(win):
        _pill(dr, W - 70, y - 4, f"RANKED {_rk(win)}", pc.VOLT, pc.GREEN, 26, anchor_right=True)
    head = (d.get("edit_head") or d.get("headline") or "").strip()
    sub = " · ".join(v for v in [d.get("tournament"), d.get("round")] if v).upper()
    if head:
        dr.text((70, 1130), head, font=pc.fit(dr, head, pc.SERIF_I, 40, W - 140, 18), fill=pc.CREAM, anchor="ls")
    dr.text((70, 1186), sub, font=pc.fit(dr, sub, pc.SANS_B, 28, 640, 16), fill=pc.VOLT, anchor="ls")
    if win.get("handle"):
        dr.text((W - 70, 1186), win["handle"], font=pc.font(pc.SANS_B, 24), fill=pc.CREAM, anchor="rs")
    dr.text((W / 2, 1292), pc.BRAND, font=pc.font(pc.SANS_B, 28), fill=pc.CREAM, anchor="mm")
    _credit(dr, d)
    return img


def _variant_c(d):
    """Vencedor a toda a altura (como o desenho 2) e o derrotado num retrato redondo a P&B, riscado a vermelho."""
    win, los = d["winner"], d["loser"]
    img = _ph(win, (W, H), (0.5, 0.15))
    _shade(img, (0, 0, W, 260), 170, 0)
    _shade(img, (0, 560, W, H), 0, 245, (8, 34, 26))
    dr = ImageDraw.Draw(img)
    pc.spaced(dr, 70 + 140, 78, "BEYOND100", pc.font(pc.SERIF_B, 30), pc.CREAM, 8)
    x = 70
    x += _pill(dr, x, 140, "GIANT UPSET", RED, pc.CREAM) + 12
    if d.get("level"):
        _pill(dr, x, 140, d["level"], pc.VOLT, pc.GREEN)
    # derrotado: retrato redondo
    R, cx, cy = 150, W - 80 - 150, 420
    face = _ph(los, (2 * R, 2 * R), (0.5, 0.2), grey=True)
    m = Image.new("L", (2 * R, 2 * R), 0)
    ImageDraw.Draw(m).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255)
    dr.ellipse([cx - R - 9, cy - R - 9, cx + R + 9, cy + R + 9], fill=RED)
    img.paste(face, (cx - R, cy - R), m)
    dr = ImageDraw.Draw(img)
    ln = (los.get("name") or "").upper()
    lab = f"{ln} {_rk(los)}".strip()
    f = pc.fit(dr, lab, pc.SANS_B, 24, 2 * R + 60, 14)
    tw = dr.textlength(lab, font=f) + 30
    dr.rounded_rectangle([cx - tw / 2, cy + R + 18, cx + tw / 2, cy + R + 58], radius=20, fill=pc.CREAM)
    dr.text((cx, cy + R + 38), lab, font=f, fill=pc.GREEN, anchor="mm")
    dr.text((cx, cy - R - 34), "KNOCKED OUT", font=pc.font(pc.SANS_B, 24), fill=pc.CREAM, anchor="mm")
    # bloco de baixo (como o A): nome, título, resultado em fichas, torneio e @
    x, maxw = 70, W - 140
    nm = (win.get("name") or "").upper()
    s1 = pc._sq_fit(nm, 130, maxw)
    head = (d.get("edit_head") or d.get("headline") or "").strip().rstrip(".").upper()
    s2 = pc._sq_fit(head, 72, maxw) if head else 0
    y_tiles = 1080
    y_head = y_tiles - 30 - (int(s2 * 0.92) if head else 0)
    y_name = y_head - 16 - int(s1 * 0.92)
    pc._sq_text(img, x, y_name, nm, s1, pc.CREAM)
    if head:
        pc._sq_text(img, x, y_head, head, s2, pc.VOLT)
    dr = ImageDraw.Draw(img)
    tx = x
    for a, b in d["sets"]:
        won = a > b
        dr.rounded_rectangle([tx, y_tiles, tx + 150, y_tiles + 84], radius=20, fill=pc.VOLT if won else None, outline=pc.VOLT, width=3)
        dr.text((tx + 75, y_tiles + 42), f"{a}-{b}", font=pc.font(pc.SERIF_B, 42), fill=pc.GREEN if won else pc.CREAM, anchor="mm")
        tx += 166
    sub = " · ".join(v for v in [d.get("tournament"), d.get("round")] if v).upper()
    dr.text((x, 1222), sub, font=pc.fit(dr, sub, pc.SANS_B, 28, 640, 16), fill=pc.SOFT, anchor="ls")
    if win.get("handle"):
        dr.text((W - 70, 1222), win["handle"], font=pc.font(pc.SANS_B, 24), fill=pc.CREAM, anchor="rs")
    wr = _rk(win)
    if wr:
        _pill(dr, W - 70, y_name - 110, f"RANKED {wr}", pc.VOLT, pc.GREEN, 26, anchor_right=True)
    dr.text((W / 2, 1292), pc.BRAND, font=pc.font(pc.SANS_B, 28), fill=pc.CREAM, anchor="mm")
    _credit(dr, d)
    return img


def render_giant_upset(d, out_path, variant="C"):
    img = {"A": _variant_a, "B": _variant_b, "C": _variant_c}.get(str(variant).upper(), _variant_c)(d)
    img.convert("RGB").save(out_path, quality=95)
    return out_path
