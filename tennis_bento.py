"""Formatos do ténis em estilo "bento" (o mesmo do carrossel semanal): Power Ranking, Road to the Top 100,
recordes do mês e Rising. Escolhido a 1/11/2026; CAROUSEL_STYLE=classic volta aos antigos."""
import os

from PIL import Image, ImageDraw

import weekly_bento as B
from weekly_bento import f, fit, tile, W, H, BG, GREEN, DEEP, CREAM, VOLT, SOFT


def on():
    return (os.environ.get("CAROUSEL_STYLE") or "bento").lower() != "classic"


def _head(d, t1, t2, right):
    d.text((60, 82), "BEYOND100", font=f("black", 28), fill=CREAM, anchor="ls")
    d.text((W - 60, 82), right.upper(), font=f("semi", 24), fill=SOFT, anchor="rs")
    d.text((60, 200), t1, font=fit(d, t1, "black", 96, W - 120), fill=CREAM, anchor="ls")
    d.text((62, 250), t2, font=fit(d, t2, "med", 34, W - 120, 18), fill=VOLT, anchor="ls")


def _new():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def power_card(data, out, date_label):
    img, d = _new()
    _head(d, "Power Ranking", "Best form outside the top 100 · last 14 days", date_label)
    credits = []
    cols = [g for g in ("men", "women") if data.get(g)]
    if not cols:
        return None
    cw = (W - 120 - 20 * (len(cols) - 1)) / len(cols)
    for c, g in enumerate(cols):
        x0 = 60 + c * (cw + 20)
        xs = data[g][:5]
        top = xs[0]
        tile(d, [x0, 290, x0 + cw, 760], VOLT)
        ph = B.photo(top["name"])
        if ph and B.credit_of(top["name"]):
            B.paste_round(img, ph, [x0, 290, x0 + cw, 600])
            credits.append(B.credit_of(top["name"]))
            d = ImageDraw.Draw(img)
        else:
            d.text((x0 + 30, 520), "1", font=f("black", 220), fill=GREEN, anchor="ls")
        d.text((x0 + 30, 650), f"No. 1 · {g.upper()}", font=f("bold", 22), fill=GREEN, anchor="ls")
        d.text((x0 + 30, 700), top["name"], font=fit(d, top["name"], "black", 40, cw - 60), fill=GREEN, anchor="ls")
        sub = f"{top['w']}-{top['l']}" + (f" · {top['titles']} title{'s' if top['titles'] > 1 else ''}" if top["titles"] else "")
        d.text((x0 + 30, 740), sub, font=f("semi", 28), fill=GREEN, anchor="ls")
        y = 780
        for i, e in enumerate(xs[1:], 2):
            tile(d, [x0, y, x0 + cw, y + 100], GREEN, r=28)
            d.text((x0 + 30, y + 64), str(i), font=f("black", 40), fill=VOLT, anchor="ls")
            d.text((x0 + 80, y + 62), e["name"], font=fit(d, e["name"], "bold", 30, cw - 200), fill=CREAM, anchor="ls")
            d.text((x0 + cw - 30, y + 62), f"{e['w']}-{e['l']}", font=f("semi", 28), fill=SOFT, anchor="rs")
            y += 112
    B.footer(img, credits)
    img.save(out, quality=95)
    return out


def road_card(data, out, date_label):
    img, d = _new()
    _head(d, "Road to the Top 100", "Knocking on the door this week", date_label)
    y, rows = 300, 0
    for g in ("men", "women"):
        xs = data.get(g, [])[:3]
        if not xs:
            continue
        d.text((60, y + 10), g.upper(), font=f("bold", 24), fill=SOFT, anchor="ls")
        y += 30
        for x in xs:
            rows += 1
            tile(d, [60, y, W - 60, y + 112], GREEN, r=28)
            d.text((100, y + 72), f"#{x['rank']}", font=f("black", 44), fill=VOLT, anchor="ls")
            d.text((260, y + 52), x["name"], font=fit(d, x["name"], "bold", 34, 480), fill=CREAM, anchor="ls")
            prog = max(0.05, min(1.0, (130 - x["rank"]) / 30))
            d.rounded_rectangle([260, y + 72, 760, y + 86], radius=7, fill=DEEP)
            d.rounded_rectangle([260, y + 72, 260 + 500 * prog, y + 86], radius=7, fill=VOLT)
            right = ""
            if x.get("gap"):
                right = f"{int(x['gap'])} pts to go"
            elif isinstance(x.get("prev"), int) and x["prev"] != x["rank"]:
                dl = x["prev"] - x["rank"]
                right = f"{'+' if dl > 0 else '−'}{abs(dl)} places"
            d.text((W - 100, y + 66), right, font=fit(d, right, "semi", 26, 200, 16), fill=CREAM, anchor="rs")
            y += 124
        y += 20
    if rows < 3:
        return None
    d.text((60, 1225), "Rankings as recorded in their latest matches.", font=f("med", 24), fill=SOFT, anchor="ls")
    B.footer(img, [])
    img.save(out, quality=95)
    return out


def records_card(data, month_label, out, month_color=None):
    rec, cats, short = data
    img, d = _new()
    _head(d, f"{month_label.split()[0]} in records", "The month on tour, by the numbers", month_label.split()[-1])
    boxes = [(60, 290, 620, 700), (640, 290, W - 60, 700), (60, 720, 460, 1230), (480, 720, W - 60, 960), (480, 980, W - 60, 1230)]
    filled = 0
    for i, ((key, _label), box) in enumerate(zip(cats, boxes)):
        leaders = [(g, (rec.get(g, {}).get(key) or [None])[0]) for g in ("men", "women")]
        leaders = [(g, t) for g, t in leaders if t]
        if not leaders:
            continue
        filled += len(leaders)
        c = (month_color or VOLT) if i == 0 else (GREEN if i % 2 else DEEP)
        light = sum(c) / 3 > 150
        fc = GREEN if light else CREAM
        x0, y0, x1, y1 = box
        tile(d, box, c)
        d.text((x0 + 32, y0 + 56), short[key], font=fit(d, short[key], "bold", 22, x1 - x0 - 64, 14), fill=fc, anchor="ls")
        big = (y1 - y0) > 300
        n = len(leaders)
        slot = (y1 - y0 - 80) / n
        for k, (g, t) in enumerate(leaders):
            yb = y0 + 80 + slot * (k + 1) - 20
            num = str(t[key])
            fs = 110 if big and n == 1 else (84 if big else 56)
            nf = fit(d, num, "black", fs, (x1 - x0) * 0.45)
            d.text((x0 + 30, yb), num, font=nf, fill=fc, anchor="ls")
            nx = x0 + 30 + d.textlength(num, font=nf) + 18
            lab = ("Men · " if g == "men" else "Women · ") + t["name"]
            d.text((nx, yb - 4), lab, font=fit(d, lab, "semi", 28, x1 - nx - 24, 13), fill=fc, anchor="ls")
    if filled < 4:
        return None
    B.footer(img, [])
    img.save(out, quality=95)
    return out


def rising_cover(rs, rng, photo_fn):
    img, d = _new()
    _head(d, "Rising", "The biggest ranking climbs this week", rng)
    credits = []
    n = len(rs)
    cw = (W - 120 - 20 * (n - 1)) / n
    for i, x in enumerate(rs):
        x0 = 60 + i * (cw + 20)
        tile(d, [x0, 290, x0 + cw, 900], GREEN)
        fp, c = photo_fn(x["slug"])
        if fp:
            B.paste_round(img, Image.open(fp).convert("RGB"), [x0, 290, x0 + cw, 760])
            credits.append(c)
            d = ImageDraw.Draw(img)
        d.text((x0 + 26, 830), "+" + str(x["rise"]), font=f("black", 64), fill=VOLT, anchor="ls")
        last = x["name"].split()[-1]
        d.text((x0 + 26, 875), last, font=fit(d, last, "bold", 30, cw - 52), fill=CREAM, anchor="ls")
    tile(d, [60, 930, W - 60, 1230], VOLT)
    d.text((100, 1080), "Swipe for the stories →", font=f("black", 56), fill=GREEN, anchor="ls")
    d.text((100, 1150), "Places gained in the ranking in the last weeks", font=f("med", 30), fill=GREEN, anchor="ls")
    return img, credits


def rising_player(x, n, photo_fn):
    img, d = _new()
    d.text((60, 82), "BEYOND100 · RISING", font=f("black", 28), fill=CREAM, anchor="ls")
    d.text((W - 60, 82), f"#{n} RISER", font=f("semi", 24), fill=VOLT, anchor="rs")
    fp, c = photo_fn(x["slug"])
    if fp:
        B.paste_round(img, Image.open(fp).convert("RGB"), [60, 120, W - 60, 760])
        d = ImageDraw.Draw(img)
    nm = x["name"]
    tw = d.textlength(nm, font=f("bold", 30))
    d.rounded_rectangle([80, 680, 80 + 40 + tw, 740], radius=30, fill=VOLT)
    d.text((100, 722), nm, font=f("bold", 30), fill=GREEN, anchor="ls")
    tile(d, [60, 790, 540, 1230], VOLT)
    d.text((100, 1010), "+" + str(x["rise"]), font=fit(d, "+" + str(x["rise"]), "black", 190, 400), fill=GREEN, anchor="ls")
    d.text((104, 1080), "places", font=f("semi", 40), fill=GREEN, anchor="ls")
    ctx = " · ".join(v for v in [x.get("country"), x.get("tournament")] if v)
    if ctx:
        d.text((104, 1180), ctx, font=fit(d, ctx, "med", 26, 400, 14), fill=GREEN, anchor="ls")
    tile(d, [560, 790, W - 60, 1000], GREEN)
    d.text((600, 870), "BEFORE", font=f("bold", 22), fill=SOFT, anchor="ls")
    d.text((600, 960), f"#{x['rank_before']}", font=f("black", 76), fill=SOFT, anchor="ls")
    tile(d, [560, 1020, W - 60, 1230], DEEP)
    d.text((600, 1100), "NOW", font=f("bold", 22), fill=VOLT, anchor="ls")
    d.text((600, 1190), f"#{x['rank_now']}", font=f("black", 76), fill=CREAM, anchor="ls")
    return img, [c] if c else []
