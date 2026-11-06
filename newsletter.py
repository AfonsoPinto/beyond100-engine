"""Newsletter semanal Beyond100 (ténis + padel), montada só com os dados que já temos. Não envia nada:
gera site/newsletter/latest.html (pré-visualização no site) e newsletter.html (HTML de email, CSS em linha, pronto para colar
no Buttondown/Brevo ou para enviar por API mais tarde).

Secções: campeões da semana para lá do top 100 · surpresas · subidas no ranking (oficial) · qualifiers · padel (campeões, Race)
· próxima semana. Fotos só licenciadas (as do site, com crédito)."""
import datetime as dt
import html
import json
import os
import re

SITE = (os.environ.get("SITE_URL") or "https://beyond100tennis.com").rstrip("/")
esc = html.escape
G, DEEP, CREAM, VOLT, SOFT, EDGE, INK = "#0e3a2d", "#09281f", "#f7f2e6", "#d9f23d", "#b0c4b7", "#2c5d4c", "#0e3a2d"
BLUE = "#0c2e4a"


def _load(p, d):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def slug(s):
    import unicodedata
    t = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def _score(r):
    w = r["winner"]
    a, b = r["games"][w - 1], r["games"][2 - w]
    return " ".join(f"{x}-{y}" for x, y in zip(a, b))


def week_data(today=None):
    today = today or dt.date.today()
    start = (today - dt.timedelta(days=7)).isoformat()
    res = [r for r in _load("results.json", []) if r.get("date", "") >= start and r.get("winner") in (1, 2)
           and " / " not in r["p1"]["name"] and not r.get("q")]
    champs = []
    for r in res:
        if (r.get("round") or "").lower() in ("final", "finals"):
            w = r["p%d" % r["winner"]]
            champs.append({"name": w["name"], "rank": w.get("rank"), "country": (w.get("country") or "").upper(), "t": r.get("tournament"),
                           "tour": r.get("tour"), "gender": r.get("gender"), "score": _score(r), "id": r.get("id"),
                           "loser": r["p%d" % (3 - r["winner"])]["name"]})
    beyond = sorted([c for c in champs if isinstance(c["rank"], int) and c["rank"] > 100], key=lambda c: -c["rank"])
    ups = []
    try:
        import extras
        best = lambda n: (extras.hist_entry(n) or {}).get("br")
    except Exception:
        best = lambda n: None
    for r in res:
        w, l = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
        b = best(w["name"])
        if isinstance(b, int) and b <= 100:                      # regresso de lesão (ranking baixo, mas já foi top 100): não é surpresa
            continue
        if isinstance(w.get("rank"), int) and w["rank"] > 1000:    # rankings acima de 1000 são quase sempre regressos/inatividade
            continue
        if isinstance(w.get("rank"), int) and isinstance(l.get("rank"), int) and w["rank"] - l["rank"] >= 150:
            ups.append({"w": w["name"], "wr": w["rank"], "l": l["name"], "lr": l["rank"], "t": r.get("tournament"), "score": _score(r), "id": r.get("id")})
    ups.sort(key=lambda u: -(u["wr"] - u["lr"]))
    er = _load("espn_rank.json", {})
    climb = {lg: sorted([x for x in er.get(lg) or [] if isinstance(x.get("prev"), int) and x["prev"] > x["r"]], key=lambda x: x["r"] - x["prev"])[:3]
             for lg in ("atp", "wta")}
    try:
        import features
        quals = features.qualifier_week()[:4]
    except Exception:
        quals = []
    # padel
    tours = _load("padel/data/tournaments.json", {})
    pchamps = []
    try:
        from padel.fetch import load_matches
        for m in load_matches().values():
            if m.get("round") == 1 and m.get("winner") in ("team_1", "team_2") and (m.get("played_at") or "") >= start:
                t = tours.get(str(m.get("tid"))) or {}
                ps = ((m.get("players") or {}).get(m["winner"]) or [])
                pchamps.append({"t": t.get("name"), "cat": m.get("category"), "pair": " / ".join(p.get("name") for p in ps)})
    except Exception as e:
        print("Newsletter: padel indisponível", e)
    race = _load("padel/data/race.json", {})
    nxt_t = [e for e in _load("espn.json", {}).get("events", []) if (e.get("start") or "")[:10] > today.isoformat()]
    nxt_p = sorted([t for t in tours.values() if today.isoformat() < (t.get("start_date") or "") <= (today + dt.timedelta(days=8)).isoformat()],
                   key=lambda t: t.get("start_date"))
    return {"week": today.isocalendar()[1], "date": today.isoformat(), "champs": champs, "beyond": beyond, "upsets": ups[:3],
            "climb": climb, "quals": quals, "pchamps": pchamps, "race": race, "next_t": nxt_t, "next_p": nxt_p, "n_results": len(res)}


def _photo(name):
    sl = slug(name)
    return f"{SITE}/img/{sl}.jpg" if os.path.exists(os.path.join("photos", sl + ".jpg")) else ""


def _h2(t, c=VOLT):
    return f'<tr><td style="padding:28px 24px 8px;font:700 13px Arial,sans-serif;letter-spacing:2px;color:{c};text-transform:uppercase">{esc(t)}</td></tr>'


def _row(left, title, sub, href=""):
    a0, a1 = (f'<a href="{esc(href)}" style="color:{CREAM};text-decoration:none">', "</a>") if href else ("", "")
    return (f'<tr><td style="padding:6px 24px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{DEEP};border:1px solid {EDGE};border-radius:14px">'
            f'<tr><td width="54" style="padding:14px 0 14px 16px;font:700 20px Georgia,serif;color:{VOLT};vertical-align:middle">{left}</td>'
            f'<td style="padding:14px 16px 14px 6px"><div style="font:700 17px Georgia,serif;color:{CREAM}">{a0}{title}{a1}</div>'
            f'<div style="font:13px Arial,sans-serif;color:{SOFT};margin-top:3px">{sub}</div></td></tr></table></td></tr>')


def render(d):
    rows = ""
    # destaque: o campeão com o ranking mais "beyond" da semana
    top = (d["beyond"] or d["champs"] or [None])[0]
    if top:
        ph = _photo(top["name"])
        img = (f'<tr><td style="padding:0 24px"><img src="{ph}" width="552" alt="{esc(top["name"])}" style="display:block;width:100%;max-width:552px;height:auto;border-radius:18px 18px 0 0"></td></tr>'
               if ph else "")
        rows += img + (f'<tr><td style="padding:0 24px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{VOLT};border-radius:{"0 0 18px 18px" if ph else "18px"}">'
                       f'<tr><td style="padding:18px 20px"><div style="font:700 12px Arial,sans-serif;letter-spacing:2px;color:{INK}">CHAMPION OF THE WEEK</div>'
                       f'<div style="font:700 28px Georgia,serif;color:{INK};margin:6px 0 4px">{esc(top["name"])}</div>'
                       f'<div style="font:15px Arial,sans-serif;color:{INK}">' + (f'Ranked #{top["rank"]} · ' if top.get("rank") else "")
                       + f'won {esc(top["t"] or "")}, beating {esc(top["loser"])} {esc(top["score"])}</div>'
                       f'<div style="margin-top:12px"><a href="{SITE}/m/{top["id"]}.html" style="font:700 14px Arial,sans-serif;color:{INK}">Full match →</a></div></td></tr></table></td></tr>')
    others = [c for c in d["champs"] if c is not top][:6]
    if others:
        rows += _h2("More champions")
        for c in others:
            rows += _row("🏆", esc(c["name"]), esc(f'{c["t"]} · ' + (f'#{c["rank"]} · ' if c.get("rank") else "") + c["score"]), f'{SITE}/m/{c["id"]}.html')
    if d["upsets"]:
        rows += _h2("Upsets of the week")
        for u in d["upsets"]:
            rows += _row(f'#{u["wr"]}', esc(f'{u["w"]} beat {u["l"]} (#{u["lr"]})'), esc(f'{u["t"]} · {u["score"]}'), f'{SITE}/m/{u["id"]}.html')
    if any(d["climb"].values()):
        rows += _h2("Climbers in the official rankings")
        for lg in ("atp", "wta"):
            for x in d["climb"][lg]:
                rows += _row(f'▲{x["prev"] - x["r"]}', esc(x["n"]), esc(f'{lg.upper()} · #{x["prev"]} → #{x["r"]}' + (f' · {x["age"]} years old' if isinstance(x.get("age"), int) and x["age"] <= 21 else "")),
                             f'{SITE}/rankings.html')
    if d["quals"]:
        rows += _h2("Qualifier watch")
        for q in d["quals"]:
            rows += _row("Q", esc(q["name"]), esc(f'{q["tournament"]} · {q["wins"]} main-draw win{"s" if q["wins"] > 1 else ""}' + ("" if q["alive"] else " · out")))
    # padel
    prow = ""
    for c in d["pchamps"][:4]:
        prow += _row("🏆", esc(c["pair"]), esc(f'{c["t"]} · {c["cat"]}'), f"{SITE}/padel/")
    rr = (d["race"].get("men") or {}).get("rows") or []
    if rr:
        prow += _row("🏁", "Race to the Finals", esc("Top 8 pairs qualify · " + ", ".join(x["name"].split()[-1] for x in sorted(rr, key=lambda x: x["ranking"])[6:10]) + " on the bubble"), f"{SITE}/padel/rankings.html")
    for t in d["next_p"][:3]:
        prow += _row("📅", esc(t.get("name")), esc(f'Starts {t.get("start_date")} · {t.get("location") or ""}'), f"{SITE}/padel/tournaments.html")
    if prow:
        rows += _h2("Padel", "#9fd3ff") + prow
    if d["next_t"]:
        rows += _h2("Coming up in tennis")
        for e in d["next_t"][:4]:
            rows += _row("📅", esc(e.get("name")), esc(f'Starts {(e.get("start") or "")[:10]} · {e.get("city") or ""}'), f"{SITE}/order-of-play.html")
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Beyond100 Weekly · Week {d['week']}</title></head>
<body style="margin:0;background:#06201a"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#06201a"><tr><td align="center" style="padding:24px 8px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:{G};border-radius:24px">
<tr><td style="padding:28px 24px 6px"><span style="display:inline-block;background:{CREAM};color:{G};font:700 14px Georgia,serif;letter-spacing:5px;padding:8px 16px;border-radius:999px">BEYOND100</span></td></tr>
<tr><td style="padding:10px 24px 2px;font:700 34px Georgia,serif;color:{CREAM}">The week beyond the top 100</td></tr>
<tr><td style="padding:0 24px 18px;font:14px Arial,sans-serif;color:{SOFT}">Week {d['week']} · {d['n_results']} results we tracked in tennis and padel, in two minutes.</td></tr>
{rows}
<tr><td style="padding:28px 24px"><a href="{SITE}" style="display:inline-block;background:{VOLT};color:{INK};font:700 15px Arial,sans-serif;padding:12px 22px;border-radius:999px;text-decoration:none">All results on beyond100tennis.com</a></td></tr>
<tr><td style="padding:0 24px 28px;font:12px Arial,sans-serif;color:{SOFT}">Follow <a href="https://www.instagram.com/beyond100.tennis/" style="color:{CREAM}">@beyond100.tennis</a> and <a href="https://www.instagram.com/beyond100.padel/" style="color:{CREAM}">@beyond100.padel</a>.<br>
Photos: licensed (Wikimedia Commons / authorised), credits on the site. You get this because you subscribed on our site. <a href="{{{{unsubscribe_url}}}}" style="color:{SOFT}">Unsubscribe</a></td></tr>
</table></td></tr></table></body></html>"""


def main():
    d = week_data()
    out = render(d)
    with open("newsletter.html", "w", encoding="utf-8") as f:
        f.write(out)
    os.makedirs("site/newsletter", exist_ok=True)
    with open("site/newsletter/latest.html", "w", encoding="utf-8") as f:
        f.write(out.replace("<head>", "<head><meta name=robots content=noindex>", 1))
    print(f"Newsletter: semana {d['week']}, {len(d['champs'])} campeões, {len(d['upsets'])} surpresas, {len(d['pchamps'])} campeões de padel.")


if __name__ == "__main__":
    main()
