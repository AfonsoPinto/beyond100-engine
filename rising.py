"""Carrossel "Rising this week": os 3 jogadores que mais subiram no ranking, com os rankings que registámos nos jogos.

  python rising.py out          -> gera se for o dia/hora (RISING_DAY, por omissão 2 = quarta; RISING_HOUR, 18 UTC)
  python rising.py out --force  -> gera já (teste)

Regras: só dados de results.json (o ranking que o jogador tinha em cada jogo); subida = ranking mais antigo entre
há 35 e há 7 dias menos o ranking mais recente dos últimos 7 dias; pelo menos 10 lugares; só jogadores com foto
licenciada (o crédito aparece no slide). Sempre 5 slides (a Make precisa de um número fixo). Desliga-se com RISING_ENABLED=0.
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageDraw, ImageOps

import photo_cards as pc
import webapp
import weekly
from captions import make_caption

RISING_DAY = int(os.environ.get("RISING_DAY") or "2")
RISING_HOUR = int(os.environ.get("RISING_HOUR") or "18")
MIN_RISE = 10
W, H = pc.W, pc.H


def risers(results, today):
    new_cut, old_lo = (today - timedelta(days=7)).isoformat(), (today - timedelta(days=35)).isoformat()
    now, old, info = {}, {}, {}
    for r in results:
        if r.get("q") or webapp.classify(r)[1] != "singles" or (r.get("src") == "espn" and os.environ.get("POSTS_USE_ESPN", "1") != "1"):
            continue
        d = r.get("date") or ""
        for i in (1, 2):
            p = r.get("p%d" % i) or {}
            rk, nm = p.get("rank"), p.get("name")
            if not nm or not isinstance(rk, int) or rk <= 0:
                continue
            k = webapp.slugify(nm)
            if d >= new_cut:
                if k not in now or d >= now[k][0]:
                    now[k] = (d, rk)
                    info[k] = {"name": nm, "country": p.get("country"), "tournament": webapp.base_tournament(r.get("tournament", "")),
                               "won": r.get("winner") == i}
            elif d >= old_lo:
                if k not in old or d < old[k][0]:
                    old[k] = (d, rk)
    out = []
    for k, (d, rk) in now.items():
        if k in old and old[k][1] - rk >= MIN_RISE:
            out.append(dict(info[k], slug=k, rank_now=rk, rank_before=old[k][1], rise=old[k][1] - rk, since=old[k][0]))
    return sorted(out, key=lambda x: (-x["rise"], x["rank_now"]))


def _photo(slug):
    fp = os.path.join(weekly.PHOTO_DIR, slug + ".jpg")
    if not os.path.exists(fp):
        return None, None
    cr = weekly._load(os.path.join(weekly.PHOTO_DIR, "credits.json"), {}).get(slug + ".jpg")
    return (fp, cr) if cr else (None, None)          # sem crédito registado não se usa (a licença exige-o)


def slide_cover(rs, start, end):
    img = pc._gradient()
    pc._court(img)
    pc._header(img)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 430), "RISING", font=pc.font(pc.SERIF_B, 170), fill=CREAM, anchor="mm")
    d.text((W / 2, 570), "THIS WEEK", font=pc.font(pc.SANS_B, 52), fill=pc.VOLT, anchor="mm")
    rng = f"{start.strftime('%b %d')} – {end.strftime('%b %d')}".replace(" 0", " ")
    d.text((W / 2, 650), rng, font=pc.font(pc.SERIF_I, 50), fill=pc.SOFT, anchor="mm")
    for i, x in enumerate(rs):
        weekly._circle(img, x["name"], 270 + i * 270, 860, 100)
        d = ImageDraw.Draw(img)
        d.text((270 + i * 270, 1010), f"+{x['rise']}", font=pc.font(pc.SERIF_B, 56), fill=pc.VOLT, anchor="mm")
        d.text((270 + i * 270, 1062), weekly._last(x["name"]).upper(), font=pc.fit(d, weekly._last(x["name"]).upper(), pc.SANS_B, 28, 240, 16), fill=CREAM, anchor="mm")
    d.text((W / 2, 1150), "Swipe →", font=pc.font(pc.SANS_B, 34), fill=CREAM, anchor="mm")
    credits = " · ".join(c for c in (_photo(x["slug"])[1] for x in rs) if c)
    pc._footer(img, credits[:90] or None)
    return img


def slide_player(x, n):
    img = pc._gradient()
    pc._court(img)
    pc._header(img)
    fp, cr = _photo(x["slug"])
    ph = ImageOps.fit(Image.open(fp).convert("RGB"), (560, 700), centering=(0.5, 0.2))
    m = Image.new("L", ph.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, ph.width - 1, ph.height - 1), radius=40, fill=255)
    img.paste(ph, (60, 170), m)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((60, 170, 620, 870), radius=40, outline=CREAM, width=4)
    d.text((80, 140), f"#{n} RISER", font=pc.font(pc.SANS_B, 26), fill=pc.VOLT, anchor="lm")
    cx = 850
    d.text((cx, 300), "+" + str(x["rise"]), font=pc.fit(d, "+" + str(x["rise"]), pc.SERIF_B, 170, 380, 80), fill=pc.VOLT, anchor="mm")
    d.text((cx, 410), "PLACES", font=pc.font(pc.SANS_B, 30), fill=SOFT, anchor="mm")
    d.text((cx, 540), f"#{x['rank_before']}", font=pc.font(pc.SERIF_B, 64), fill=SOFT, anchor="mm")
    d.polygon([(cx - 22, 600), (cx + 22, 600), (cx, 640)], fill=pc.VOLT)
    d.text((cx, 710), f"#{x['rank_now']}", font=pc.font(pc.SERIF_B, 96), fill=CREAM, anchor="mm")
    parts = x["name"].upper().split()
    first, last = " ".join(parts[:-1]), parts[-1]
    if first:
        d.text((W / 2, 950), first, font=pc.fit(d, first, pc.SANS_B, 36, 900, 20), fill=SOFT, anchor="mm")
    d.text((W / 2, 1025), last, font=pc.fit(d, last, pc.SERIF_B, 96, 940, 40), fill=CREAM, anchor="mm")
    ctx = " · ".join(v for v in [x.get("country"), ("Latest: " + x["tournament"]) if x.get("tournament") else ""] if v)
    d.text((W / 2, 1110), ctx, font=pc.fit(d, ctx, pc.SERIF_I, 36, 920, 22), fill=SOFT, anchor="mm")
    d.text((W / 2, 1170), f"Ranking we recorded on {x['since']} vs this week", font=pc.font(pc.SANS_B, 22), fill=SOFT, anchor="mm")
    pc._footer(img, cr)
    return img


SOFT, CREAM = pc.SOFT, pc.CREAM


def run(out_dir="out", force=False):
    if os.environ.get("RISING_ENABLED", "1").strip() in ("0", "no", "off", "false"):
        print("Rising this week: desligado.")
        return None
    now = datetime.now(timezone.utc)
    if not force and not (now.weekday() == RISING_DAY and now.hour >= RISING_HOUR):
        print("Rising this week: ainda não é a hora.")
        return None
    rid = f"rising-{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    queue = weekly._load(weekly.CAROUSELS_FILE, [])
    if not force and any(c["id"] == rid for c in queue):
        print("Rising this week: já existe o desta semana.")
        return None
    rs = [x for x in risers(weekly._load(weekly.RESULTS_FILE, []), now.date()) if _photo(x["slug"])[0]][:3]
    if len(rs) < 3:
        print(f"Rising this week: só {len(rs)} jogadores com subida e foto licenciada, salto.")
        return None
    import tennis_bento
    slides = None
    if tennis_bento.on():
        try:
            import weekly_bento
            rng = f"{(now.date() - timedelta(days=6)).strftime('%b %d')} – {now.date().strftime('%b %d')}".replace(" 0", " ")
            parts = ([tennis_bento.rising_cover(rs, rng, _photo)] + [tennis_bento.rising_player(x, i, _photo) for i, x in enumerate(rs, 1)]
                     + [weekly_bento.cta({"start": now.date() - timedelta(days=6), "end": now.date()})])
            slides = []
            for i, (im, cr) in enumerate(parts):
                weekly_bento.dots(im, i, len(parts))
                weekly_bento.footer(im, cr)
                slides.append(im)
        except Exception as e:
            print("Rising bento falhou, uso o clássico:", type(e).__name__, e)
            slides = None
    if not slides:
        slides = [slide_cover(rs, now.date() - timedelta(days=6), now.date())] + [slide_player(x, i) for i, x in enumerate(rs, 1)] + [weekly.slide_cta()]
        for i, im in enumerate(slides):
            weekly._dots(im, i, len(slides))
    os.makedirs("posts", exist_ok=True)
    os.makedirs(os.path.join(out_dir, "rising"), exist_ok=True)
    names = []
    for i, im in enumerate(slides, 1):
        nm = f"{rid}-{i}.jpg"
        im.convert("RGB").save(os.path.join("posts", nm), quality=92)
        im.save(os.path.join(out_dir, "rising", f"slide{i}.png"))
        names.append(nm)
    facts = {"risers": [{"name": x["name"], "country": x.get("country"), "rank_before": x["rank_before"], "rank_now": x["rank_now"],
                         "places_gained": x["rise"], "latest_tournament": x.get("tournament")} for x in rs],
             "period": f"{now.date() - timedelta(days=6)} to {now.date()}",
             "note": "rankings are the ones each player had in the matches we tracked"}
    cap = make_caption("rising_week", facts)
    queue = [c for c in queue if c["id"] != rid]
    queue.append({"id": rid, "kind": "rising", "images": names, "caption": cap, "sent": False,
                  "created": time.strftime("%Y-%m-%d %H:%M", time.gmtime())})
    with open(weekly.CAROUSELS_FILE, "w", encoding="utf-8") as f:
        json.dump(queue[-20:], f, ensure_ascii=False, indent=2)
    print(f"Rising this week {rid}: 5 slides na fila ({', '.join(x['name'] for x in rs)}).")
    return names


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "out", "--force" in sys.argv)
