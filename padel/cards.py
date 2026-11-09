"""Beyond Padel: cartões para o Instagram (1080x1350), no estilo do Beyond100 mas em azul.
- result_card: campeões / surpresa / vitória (foto de um vencedor em cima, os dois pares e o resultado em baixo)
- preview_card: "Who wins?" de uma final (uma foto por par, quando há)
- list_card: listas semanais (Power Ranking, Rising, Road to the Top 50, recordes do mês)"""
import os

from PIL import Image, ImageDraw, ImageOps

import photo_cards as pc

W, H = 1080, 1350
BLUE, DEEP, CREAM, VOLT, SOFT, EDGE = (12, 46, 74), (8, 34, 58), (247, 242, 230), (217, 242, 61), (169, 192, 214), (36, 80, 122)
BRAND = "Follow @beyond100.padel"
PHOTOS = os.path.join(os.path.dirname(__file__), "photos")
font, fit, SERIF_B, SERIF_I, SANS_B = pc.font, pc.fit, pc.SERIF_B, pc.SERIF_I, pc.SANS_B


def _grad():
    g = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(g)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int((16, 58, 92)[i] + ((6, 26, 44)[i] - (16, 58, 92)[i]) * t) for i in range(3)))
    return g


def _shade(img, y0, y1, a0, a1):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for y in range(y0, y1):
        od.line([(0, y), (img.width, y)], fill=(6, 26, 44, int(a0 + (a1 - a0) * (y - y0) / max(1, y1 - y0))))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def _brand(img, y=78):
    d = ImageDraw.Draw(img)
    f = font(SERIF_B, 30)
    t = "BEYOND PADEL"
    tw = sum(d.textlength(c, font=f) for c in t) + 8 * (len(t) - 1)
    d.rounded_rectangle([70, y - 32, 70 + tw + 56, y + 32], radius=32, fill=CREAM)
    pc.spaced(d, 70 + (tw + 56) / 2, y, t, f, BLUE, 8)


def _tags(d, labels, y=150, x=70):
    for label, fill, fg in labels:
        if not label:
            continue
        f = font(SANS_B, 26)
        tw = d.textlength(label, font=f) + 36
        d.rounded_rectangle([x, y, x + tw, y + 46], radius=23, fill=fill)
        d.text((x + tw / 2, y + 23), label, font=f, fill=fg, anchor="mm")
        x += tw + 12


def _footer(img, credits):
    d = ImageDraw.Draw(img)
    d.text((W / 2, 1292), BRAND, font=font(SANS_B, 30), fill=CREAM, anchor="mm")
    cr = pc.credit_join(*credits) if credits else None
    if cr:
        d.text((W - 40, 1334), cr, font=fit(d, cr, SANS_B, 18, W - 200, 12), fill=SOFT, anchor="rm")


def photo_of(pid):
    """(caminho, crédito, fora_do_court) da foto livre do jogador, ou (None, None, False)."""
    import json
    fp = os.path.join(PHOTOS, f"{pid}.jpg")
    if not os.path.exists(fp):
        return None, None, False
    try:                                                           # 9/11/2026: fotos desfocadas/ampliadas ou pequenas não vão para posts
        import photo_quality
        why = []
        if not photo_quality.card_ok(fp, why=why):
            print(f"Padel: foto {pid} não serve para post ({why[0]}).")
            return None, None, False
    except ImportError:
        pass
    try:
        c = json.load(open(os.path.join(PHOTOS, "credits.json"), encoding="utf-8")).get(str(pid)) or {}
    except (OSError, ValueError):
        c = {}
    return fp, c.get("credit"), bool(c.get("offcourt"))


def _fill(fp, size, centering=(0.5, 0.25)):
    """Enche a área com a foto. Se a foto for pequena demais (teria de ser ampliada mais de 1,35x), não a estica:
    fundo com a mesma foto desfocada e escurecida, e a foto nítida por cima, no tamanho em que fica boa."""
    from PIL import ImageFilter
    im = Image.open(fp).convert("RGB")
    W_, H_ = size
    need = max(W_ / im.width, H_ / im.height)
    if need <= 1.35:
        return ImageOps.fit(im, size, centering=centering)
    bg = ImageOps.fit(im, size, centering=centering).filter(ImageFilter.GaussianBlur(28))
    bg = Image.blend(bg, Image.new("RGB", size, (6, 26, 44)), 0.45)
    sc = min(1.3, H_ * 0.96 / im.height, W_ * 0.96 / im.width)
    fg = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.LANCZOS)
    if fg.width < W_ * 0.5:                                        # retrato estreito: recorta um pouco em altura para ganhar largura
        sc2 = min(1.3, (W_ * 0.62) / im.width)
        fg = im.resize((int(im.width * sc2), int(im.height * sc2)), Image.LANCZOS)
        if fg.height > H_:
            top = int((fg.height - H_) * centering[1])
            fg = fg.crop((0, top, fg.width, top + H_))
    bg.paste(fg, ((W_ - fg.width) // 2, H_ - fg.height))
    return bg


def _code(p):
    return (p.get("nationality") or "").upper()


def _pair_lines(d, ps, ranks, x, y, size, color, max_w):
    for i, p in enumerate(ps):
        nm = p.get("name") or "?"
        f = fit(d, nm, SERIF_B, size, max_w - 150, int(size * 0.6))
        d.text((x, y + i * (size + 14)), nm, font=f, fill=color, anchor="ls")
        tail = " · ".join(v for v in [_code(p), f"#{ranks.get(str(p.get('id')))}" if ranks.get(str(p.get("id"))) else ""] if v)
        d.text((x + d.textlength(nm, font=f) + 16, y + i * (size + 14)), tail, font=font(SANS_B, 24), fill=SOFT, anchor="ls")


def _sets(d, sets, x_right, y, mine_first=True, win=True):
    n = len(sets)
    for k, (a, b) in enumerate(sets):
        cx = x_right - (n - 1 - k) * 92
        mine, oth = (a, b) if mine_first else (b, a)
        on = _g(mine) > _g(oth)
        d.rounded_rectangle([cx - 38, y - 46, cx + 38, y + 34], radius=16, fill=VOLT if on else None, outline=VOLT if on else EDGE, width=3)
        g = mine.split("(")[0]
        d.text((cx, y - 6), g, font=font(SERIF_B, 46), fill=BLUE if on else CREAM, anchor="mm")
        if "(" in mine:
            d.text((cx + 26, y - 30), mine.split("(")[1].rstrip(")"), font=font(SANS_B, 18), fill=BLUE if on else SOFT, anchor="mm")


def _g(x):
    try:
        return int(str(x).split("(")[0])
    except ValueError:
        return -1


def result_card(d, out_path):
    """d = {kicker, level, round, tournament, city, date, winners:[p,p], losers:[p,p], sets:[(w,l)], photo:{path,credit}, ranks:{id:rank}, note}"""
    img = _grad()
    ph = d.get("photo") or {}
    if ph.get("path"):
        img.paste(_fill(ph["path"], (W, 760), (0.5, 0.2)), (0, 0))
        img = _shade(img, 0, 260, 150, 0)
        img = _shade(img, 460, 760, 0, 255)
    dr = ImageDraw.Draw(img)
    _brand(img)
    _tags(dr, [(d.get("level"), VOLT, BLUE), ((d.get("round") or "").upper(), CREAM, BLUE)])
    k = (d.get("kicker") or "").upper()
    dr.text((70, 690), k, font=fit(dr, k, SANS_B, 92, W - 140, 50), fill=CREAM, anchor="ls")
    sub = " · ".join(x for x in [d.get("tournament"), d.get("city"), d.get("date")] if x).upper()
    dr.text((70, 740), sub, font=fit(dr, sub, SANS_B, 26, W - 140, 16), fill=VOLT, anchor="ls")
    ranks = d.get("ranks") or {}
    _pair_lines(dr, d["winners"], ranks, 70, 860, 50, CREAM, 640)
    _sets(dr, d["sets"], W - 110, 880, True)
    dr.line([(70, 960), (W - 70, 960)], fill=EDGE, width=2)
    _pair_lines(dr, d["losers"], ranks, 70, 1040, 40, SOFT, 640)
    _sets(dr, d["sets"], W - 110, 1060, False)
    if d.get("note"):
        dr.text((W / 2, 1200), d["note"], font=fit(dr, d["note"], SERIF_I, 38, W - 160, 22), fill=CREAM, anchor="mm")
    _footer(img, [ph.get("credit")] if ph.get("credit") else [])
    img.save(out_path, quality=95)
    return out_path


def _sur(p):
    """Apelido como o circuito o usa ("Josemaria", "Triay", "Brea"): o short_name da Padel API; sem ele, o apelido do nome.
    Antes usava a última palavra do nome e saía "MARTIN" / "PONS" / "SENESI" (nomes espanhóis com dois apelidos), 7/11/2026."""
    sn = (p.get("short_name") or p.get("short") or "").strip()
    if sn:
        return sn.split(". ", 1)[-1] if ". " in sn else sn
    first, last = pc.split_name(p.get("name"))
    return last or first or p.get("name") or "?"


def _disp(p):
    """Nome como o circuito o usa: primeiro nome + apelido curto ("Ariana Sanchez", não "Ariana Sanchez Fallada")."""
    nm = (p.get("name") or "?").split()
    return f"{nm[0]} {_sur(p)}" if len(nm) > 1 and _sur(p).lower() != nm[0].lower() else (p.get("name") or "?")


def preview_card(d, out_path):
    """d = {level, tournament, city, when, pairs:[[p,p],[p,p]], photos:[{path,credit}|None, ...], ranks, teams:[país, país]|None}
    Só com foto real dos dois pares (7/11/2026); sem isso não há post de antevisão."""
    phs = d.get("photos") or [None, None]
    both = all(ph and ph.get("path") for ph in phs[:2])
    teams = d.get("teams") or [None, None]
    ranks = d.get("ranks") or {}
    tags = [(d.get("level"), VOLT, BLUE), ("FINAL", CREAM, BLUE)]
    credits = []
    sub = " · ".join(x for x in [d.get("tournament"), d.get("when")] if x).upper()
    tail = lambda p: " · ".join(v for v in [_code(p), f"#{ranks.get(str(p.get('id')))}" if ranks.get(str(p.get("id"))) else ""] if v)
    if both:
        img = _grad()
        half = W // 2
        for i, ph in enumerate(phs[:2]):
            img.paste(_fill(ph["path"], (half, 860), (0.5, 0.2)), (i * half, 0))
            credits.append(ph.get("credit"))
        img = _shade(img, 0, 260, 150, 0)
        img = _shade(img, 560, 860, 0, 245)
        dr = ImageDraw.Draw(img)
        dr.rectangle([half - 3, 0, half + 2, 860], fill=BLUE)
        dr.rectangle([0, 860, W, H], fill=BLUE)
        _brand(img)
        _tags(dr, tags)
        cy = 700
        dr.ellipse([half - 70, cy - 70, half + 70, cy + 70], fill=VOLT, outline=BLUE, width=8)
        dr.text((half, cy + 2), "VS", font=font(SERIF_B, 60), fill=BLUE, anchor="mm")
        for i, pair in enumerate(d["pairs"]):
            cx = half / 2 + i * half
            if teams[i]:
                dr.text((cx, 800), teams[i].upper(), font=fit(dr, teams[i].upper(), SANS_B, 30, half - 80, 18), fill=VOLT, anchor="mm")
            for j, p in enumerate(pair):
                nm = _sur(p).upper()
                dr.text((cx, 920 + j * 92), nm, font=fit(dr, nm, SERIF_B, 46, half - 70, 24), fill=CREAM, anchor="mm")
                dr.text((cx, 960 + j * 92), tail(p), font=font(SANS_B, 22), fill=SOFT, anchor="mm")
        dr.text((W / 2, 1150), sub, font=fit(dr, sub, SANS_B, 28, 960, 16), fill=VOLT, anchor="mm")
        dr.text((W / 2, 1215), "Who wins? Tell us below.", font=font(SERIF_I, 44), fill=CREAM, anchor="mm")
    else:
        raise ValueError("preview_card precisa de foto dos dois pares")
    _footer(img, credits)
    img.save(out_path, quality=95)
    return out_path


def list_card(d, out_path):
    """d = {title, subtitle, rows:[{rank, name, code, value, sub}], note}"""
    img = _grad()
    dr = ImageDraw.Draw(img)
    _brand(img)
    t = d["title"].upper()
    dr.text((70, 230), t, font=fit(dr, t, SANS_B, 88, W - 140, 44), fill=CREAM, anchor="ls")
    if d.get("subtitle"):
        dr.text((70, 285), d["subtitle"].upper(), font=fit(dr, d["subtitle"].upper(), SANS_B, 26, W - 140, 16), fill=VOLT, anchor="ls")
    y = 360
    rows = d["rows"][:8]
    step = min(108, int(820 / max(1, len(rows))))
    for r in rows:
        dr.rounded_rectangle([60, y, W - 60, y + step - 14], radius=22, fill=DEEP, outline=EDGE, width=2)
        mid = y + (step - 14) / 2
        dr.text((110, mid), str(r.get("rank") or ""), font=font(SERIF_B, 44), fill=VOLT, anchor="mm")
        nm = r.get("name") or ""
        dr.text((170, mid - 10), nm, font=fit(dr, nm, SERIF_B, 40, 560, 22), fill=CREAM, anchor="lm")
        if r.get("sub"):
            dr.text((170, mid + 26), r["sub"], font=fit(dr, r["sub"], SANS_B, 22, 560, 14), fill=SOFT, anchor="lm")
        v = str(r.get("value") or "")
        dr.text((W - 100, mid), v, font=fit(dr, v, SERIF_B, 40, 260, 22), fill=VOLT, anchor="rm")
        y += step
    if d.get("note"):
        dr.text((W / 2, 1230), d["note"], font=fit(dr, d["note"], SERIF_I, 32, W - 160, 20), fill=CREAM, anchor="mm")
    _footer(img, [])
    img.save(out_path, quality=95)
    return out_path


def list2_card(d, out_path):
    """Lista semanal com homens e mulheres no mesmo cartão (como o Power Ranking do ténis).
    d = {title, subtitle, cols: [(label, rows)], note}; rows = [{rank, name, sub, value}] (até 6 por coluna)."""
    img = _grad()
    dr = ImageDraw.Draw(img)
    _brand(img)
    t = d["title"].upper()
    dr.text((70, 230), t, font=fit(dr, t, SANS_B, 88, W - 140, 44), fill=CREAM, anchor="ls")
    if d.get("subtitle"):
        dr.text((70, 285), d["subtitle"].upper(), font=fit(dr, d["subtitle"].upper(), SANS_B, 26, W - 140, 16), fill=VOLT, anchor="ls")
    cols = [(lab, rows[:6]) for lab, rows in d["cols"] if rows]
    gap = 24
    cw = (W - 120 - gap * (len(cols) - 1)) / len(cols)
    for c, (lab, rows) in enumerate(cols):
        x0 = 60 + c * (cw + gap)
        dr.text((x0 + 6, 350), lab.upper(), font=font(SANS_B, 26), fill=SOFT, anchor="ls")
        y = 372
        for i, r in enumerate(rows):
            top = i == 0
            h = 190 if top else 116
            dr.rounded_rectangle([x0, y, x0 + cw, y + h], radius=26, fill=VOLT if top else DEEP, outline=None if top else EDGE, width=2)
            fg, sub_c, val_c = (BLUE, BLUE, BLUE) if top else (CREAM, SOFT, VOLT)
            rk = str(r.get("rank") or "")
            v = str(r.get("value") or "")
            nm = r.get("name") or ""
            if top:
                dr.text((x0 + 28, y + 62), rk, font=font(SERIF_B, 56), fill=fg, anchor="ls")
                dr.text((x0 + cw - 28, y + 62), v, font=fit(dr, v, SERIF_B, 52, cw / 2, 26), fill=val_c, anchor="rs")
                dr.text((x0 + 28, y + 122), nm, font=fit(dr, nm, SERIF_B, 40, cw - 56, 22), fill=fg, anchor="ls")
                if r.get("sub"):
                    dr.text((x0 + 28, y + 162), r["sub"], font=fit(dr, r["sub"], SANS_B, 22, cw - 56, 14), fill=sub_c, anchor="ls")
            else:
                dr.text((x0 + 26, y + 70), rk, font=font(SERIF_B, 36), fill=VOLT, anchor="ls")
                vw = dr.textlength(v, font=font(SERIF_B, 32)) if v else 0
                dr.text((x0 + 74, y + 52), nm, font=fit(dr, nm, SERIF_B, 30, cw - 110 - vw, 16), fill=fg, anchor="ls")
                if r.get("sub"):
                    dr.text((x0 + 74, y + 88), r["sub"], font=fit(dr, r["sub"], SANS_B, 20, cw - 110 - vw, 12), fill=sub_c, anchor="ls")
                if v:
                    dr.text((x0 + cw - 24, y + 68), v, font=font(SERIF_B, 32), fill=val_c, anchor="rs")
            y += h + 14
    if d.get("note"):
        dr.text((W / 2, 1238), d["note"], font=fit(dr, d["note"], SERIF_I, 30, W - 160, 18), fill=CREAM, anchor="mm")
    _footer(img, [])
    img.save(out_path, quality=95)
    return out_path


def champions_card(d, out_path):
    """Campeões de um torneio num só cartão (homens e mulheres): duas fotos em cima, os dois pares campeões em baixo.
    d = {level, tournament, city, date, finals:[{label, winners, losers, sets, photo:{path,credit}}], ranks}"""
    img = _grad()
    fins = d["finals"][:2]
    credits = []
    withp = [f for f in fins if (f.get("photo") or {}).get("path")]
    split = len(fins) == 2 and len(withp) == 2               # 9/11/2026: só divide ao meio com foto dos dois lados (nada de metade vazia)
    pw = W // 2 if split else W
    for i, f in enumerate(fins if split else withp[:1]):
        ph = f.get("photo") or {}
        if ph.get("path"):
            img.paste(_fill(ph["path"], (pw, 600), (0.5, 0.2)), (i * pw, 0))
            if ph.get("credit"):
                credits.append(ph["credit"])
    img = _shade(img, 0, 240, 150, 0)
    img = _shade(img, 380, 600, 0, 255)
    dr = ImageDraw.Draw(img)
    if not split and withp:
        lab = withp[0]["label"].split(" · ")[0].upper()
        tw = dr.textlength(lab, font=font(SANS_B, 22)) + 28
        dr.rounded_rectangle([24, 530, 24 + tw, 566], radius=18, fill=CREAM)
        dr.text((24 + tw / 2, 548), lab, font=font(SANS_B, 22), fill=BLUE, anchor="mm")
    if split:
        dr.line([(pw, 0), (pw, 600)], fill=BLUE, width=6)
        for i, f in enumerate(fins):
            lab = f["label"].split(" · ")[0].upper()
            tw = dr.textlength(lab, font=font(SANS_B, 22)) + 28
            x = i * pw + 24
            dr.rounded_rectangle([x, 530, x + tw, 566], radius=18, fill=CREAM)
            dr.text((x + tw / 2, 548), lab, font=font(SANS_B, 22), fill=BLUE, anchor="mm")
    _brand(img)
    _tags(dr, [(d.get("level"), VOLT, BLUE), ("FINALS", CREAM, BLUE)])
    dr.text((70, 700), "CHAMPIONS", font=font(SANS_B, 92), fill=CREAM, anchor="ls")
    sub = " · ".join(x for x in [d.get("tournament"), d.get("city"), d.get("date")] if x).upper()
    dr.text((70, 748), sub, font=fit(dr, sub, SANS_B, 26, W - 140, 16), fill=VOLT, anchor="ls")
    ranks = d.get("ranks") or {}
    y = 800
    for i, f in enumerate(fins):
        if i:
            dr.line([(70, y - 18), (W - 70, y - 18)], fill=EDGE, width=2)
        dr.text((70, y + 20), f["label"].upper(), font=font(SANS_B, 22), fill=VOLT, anchor="ls")
        for k, p in enumerate(f["winners"]):
            nm = _disp(p)
            fnt = fit(dr, nm, SERIF_B, 40, 600, 24)
            dr.text((70, y + 70 + k * 50), nm, font=fnt, fill=CREAM, anchor="ls")
            rk = ranks.get(str(p.get("id")))
            tail = " · ".join(v for v in [_code(p), f"#{rk}" if rk else ""] if v)
            dr.text((70 + dr.textlength(nm, font=fnt) + 14, y + 70 + k * 50), tail, font=font(SANS_B, 22), fill=SOFT, anchor="ls")
        sc = "  ".join(f"{str(a).split('(')[0]}-{str(b).split('(')[0]}" for a, b in f["sets"])
        dr.text((W - 70, y + 92), sc, font=fit(dr, sc, SERIF_B, 52, 330, 30), fill=VOLT, anchor="rs")
        ls = "d. " + " / ".join(_disp(p) for p in f["losers"])
        dr.text((70, y + 160), ls, font=fit(dr, ls, SANS_B, 24, W - 140, 16), fill=SOFT, anchor="ls")
        y += 210
    _footer(img, credits[:2])
    img.save(out_path, quality=95)
    return out_path


def nations_card(d, out_path):
    """Final por seleções (Mundial da FIP), 9/11/2026: o campeão é o país, não um par. Foto de um jogador do país campeão em cima,
    o país em grande e, por categoria, o resultado da eliminatória e os jogos (rubbers).
    d = {level, tournament, city, date, photo:{path,credit}|None, ties:[{label, winner, loser, score:(a,b),
         rubbers:[{winners:[p,p], losers:[p,p], sets:[(a,b)], champ:bool}]}]}"""
    img = _grad()
    credits = []
    ph = d.get("photo") or {}
    if ph.get("path"):
        img.paste(_fill(ph["path"], (W, 660), (0.5, 0.2)), (0, 0))
        if ph.get("credit"):
            credits.append(ph["credit"])
    img = _shade(img, 0, 240, 150, 0)
    img = _shade(img, 420, 660, 0, 255)
    dr = ImageDraw.Draw(img)
    _brand(img)
    _tags(dr, [(d.get("level"), VOLT, BLUE), ("FINAL", CREAM, BLUE)])
    ties = d["ties"][:2]
    nations = {t["winner"] for t in ties}
    title = next(iter(nations)).upper() if len(nations) == 1 else "CHAMPIONS"
    dr.text((70, 640), title, font=fit(dr, title, SERIF_B, 120, W - 140, 60), fill=CREAM, anchor="ls")
    kick = ("WORLD CHAMPIONS · MEN AND WOMEN" if len(ties) == 2 else "WORLD CHAMPIONS") if len(nations) == 1 else ""
    if kick:
        dr.text((70, 692), kick, font=fit(dr, kick, SANS_B, 30, W - 140, 18), fill=VOLT, anchor="ls")
    sub = " · ".join(x for x in [d.get("tournament"), d.get("city"), d.get("date")] if x).upper()
    dr.text((70, 734), sub, font=fit(dr, sub, SANS_B, 22, W - 140, 14), fill=SOFT, anchor="ls")
    y = 790
    for i, t in enumerate(ties):
        if i:
            dr.line([(70, y - 14), (W - 70, y - 14)], fill=EDGE, width=2)
        a, b = t["score"]
        head = f'{t["label"].upper()} · {t["winner"].upper()} {a}-{b} {t["loser"].upper()}'
        dr.text((70, y + 22), head, font=fit(dr, head, SANS_B, 26, W - 140, 16), fill=VOLT, anchor="ls")
        y += 44
        for r in t["rubbers"]:
            col = CREAM if r["champ"] else SOFT
            wn = " / ".join(_sur(p) for p in r["winners"])
            ln = " / ".join(_sur(p) for p in r["losers"])
            sc = "  ".join(f"{str(x).split('(')[0]}-{str(z).split('(')[0]}" for x, z in r["sets"])
            line = f"{wn}  d.  {ln}"
            dr.text((70, y + 26), line, font=fit(dr, line, SERIF_B, 32, 690, 18), fill=col, anchor="ls")
            dr.text((W - 70, y + 26), sc, font=fit(dr, sc, SANS_B, 26, 250, 16), fill=col, anchor="rs")
            y += 48
        y += 30
    _footer(img, credits[:1])
    img.save(out_path, quality=95)
    return out_path


def tour_preview_card(d, out_path):
    """Antevisão de um torneio na véspera. Em cima: foto REAL e livre da cidade-sede (alusão ao torneio) e, em destaque, as fotos
    licenciadas de cabeças de série (com o nome de quem lá está). Em baixo: os 4 primeiros pares de cada categoria e os campeões em título.
    d = {level, tournament, city, when, place:{path,credit}|None, photos:[{path,credit,label}], cols:[(label, [(seed, [p,p])])], champions, ranks}"""
    img = _grad()
    credits = []
    pl = d.get("place") or {}
    if pl.get("path"):
        img.paste(_fill(pl["path"], (W, 640), (0.5, 0.5)), (0, 0))
        if pl.get("credit"):
            credits.append(pl["credit"])
    img = _shade(img, 0, 260, 170, 0)
    img = _shade(img, 300, 640, 0, 255)
    phs = [p for p in d.get("photos") or [] if p and p.get("path")][:2]
    R = 118                                                        # retratos redondos, à direita
    for i, ph in enumerate(phs):
        cx, cy = W - 70 - R - i * (2 * R + 36), 360
        face = _fill(ph["path"], (2 * R, 2 * R), (0.5, 0.25))
        mask = Image.new("L", (2 * R, 2 * R), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, 2 * R - 1, 2 * R - 1], fill=255)
        ring = ImageDraw.Draw(img)
        ring.ellipse([cx - R - 7, cy - R - 7, cx + R + 7, cy + R + 7], fill=VOLT)
        img.paste(face, (cx - R, cy - R), mask)
        if ph.get("credit"):
            credits.append(ph["credit"])
        dr_ = ImageDraw.Draw(img)
        lab = (ph.get("label") or "").upper()
        if lab:
            f_ = fit(dr_, lab, SANS_B, 20, 2 * R + 30, 12)
            tw = dr_.textlength(lab, font=f_) + 26
            dr_.rounded_rectangle([cx - tw / 2, cy + R + 14, cx + tw / 2, cy + R + 48], radius=17, fill=CREAM)
            dr_.text((cx, cy + R + 31), lab, font=f_, fill=BLUE, anchor="mm")
    dr = ImageDraw.Draw(img)
    _brand(img)
    _tags(dr, [(d.get("level"), VOLT, BLUE), (d.get("when"), CREAM, BLUE)])
    t = (d.get("tournament") or "").upper()
    dr.text((70, 620), t, font=fit(dr, t, SANS_B, 96, W - 140, 44), fill=CREAM, anchor="ls")
    if d.get("city"):
        dr.text((70, 668), ("Coming up in " + d["city"]).upper(), font=font(SANS_B, 26), fill=VOLT, anchor="ls")
    cols = [(lab, rows[:4]) for lab, rows in d["cols"] if rows]
    gap = 24
    cw = (W - 120 - gap * (len(cols) - 1)) / max(1, len(cols))
    ranks = d.get("ranks") or {}
    for c_, (lab, rows) in enumerate(cols):
        x0 = 60 + c_ * (cw + gap)
        dr.text((x0 + 6, 740), (lab + " · top seeds").upper(), font=font(SANS_B, 24), fill=SOFT, anchor="ls")
        y = 760
        for seed, pair in rows:
            dr.rounded_rectangle([x0, y, x0 + cw, y + 92], radius=22, fill=DEEP, outline=EDGE, width=2)
            dr.text((x0 + 26, y + 58), str(seed), font=font(SERIF_B, 40), fill=VOLT, anchor="ls")
            names = " / ".join(p.get("short") or (pc.split_name(p.get("name"))[1] or p.get("name") or "") for p in pair)
            dr.text((x0 + 76, y + 44), names, font=fit(dr, names, SERIF_B, 32, cw - 100, 16), fill=CREAM, anchor="ls")
            rk = " · ".join(f"#{ranks.get(str(p.get('id')))}" for p in pair if ranks.get(str(p.get("id"))))
            dr.text((x0 + 76, y + 76), rk, font=font(SANS_B, 20), fill=SOFT, anchor="ls")
            y += 104
    if d.get("champions"):
        ch = "Defending champions: " + d["champions"]
        dr.text((W / 2, 1238), ch, font=fit(dr, ch, SERIF_I, 30, W - 140, 16), fill=CREAM, anchor="mm")
    _footer(img, credits)
    img.save(out_path, quality=95)
    return out_path
