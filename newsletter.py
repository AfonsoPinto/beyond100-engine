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
        ties = {}
        for m in load_matches().values():
            if m.get("round") == 1 and m.get("winner") in ("team_1", "team_2") and (m.get("played_at") or "") >= start:
                t = tours.get(str(m.get("tid"))) or {}
                tie = m.get("tie")
                if isinstance(tie, dict):                          # 10/11/2026: Mundial (seleções): o campeão é o país
                    w = tie.get("winner")
                    if w in ("team_1", "team_2"):
                        k = (t.get("name"), tie.get(w))
                        ties.setdefault(k, set()).add(m.get("category"))
                    continue
                ps = ((m.get("players") or {}).get(m["winner"]) or [])
                pchamps.append({"t": t.get("name"), "cat": m.get("category"), "pair": " / ".join(p.get("name") for p in ps)})
        for (tn, nation), cats in ties.items():
            pchamps.insert(0, {"t": tn, "cat": " and ".join(sorted(cats, key=lambda c: c != "men")), "pair": nation, "nation": True})
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
    for rel in (f"photos/{sl}.jpg",):
        if os.path.exists(rel):
            return f"{SITE}/img/big/{sl}.jpg"
    return ""


FONT = "Inter,'Helvetica Neue',Helvetica,Arial,sans-serif"
CARD, LINE = "#0b2e24", "#1f4a3d"


def _h2(t, c=VOLT):
    return (f'<tr><td style="padding:34px 28px 10px"><div style="font:800 12px {FONT};letter-spacing:2.5px;color:{c};text-transform:uppercase">{esc(t)}</div></td></tr>')


def _row(left, title, sub, href="", tag_color=VOLT):
    a0, a1 = (f'<a href="{esc(href)}" style="color:{CREAM};text-decoration:none">', "</a>") if href else ("", "")
    return (f'<tr><td style="padding:0 28px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-bottom:1px solid {LINE}">'
            f'<tr><td width="64" style="padding:14px 0;font:800 18px {FONT};color:{tag_color};vertical-align:middle;white-space:nowrap">{left}</td>'
            f'<td style="padding:14px 0 14px 8px"><div style="font:700 17px/1.3 {FONT};color:{CREAM}">{a0}{title}{a1}</div>'
            f'<div style="font:500 13px/1.4 {FONT};color:{SOFT};margin-top:3px">{sub}</div></td></tr></table></td></tr>')


def _stats(items):
    cells = "".join(f'<td width="{100 // len(items)}%" style="padding:16px 8px;text-align:center;border-right:1px solid {LINE}">'
                    f'<div style="font:900 30px {FONT};color:{VOLT};letter-spacing:-1px">{v}</div>'
                    f'<div style="font:700 11px {FONT};color:{SOFT};letter-spacing:1.5px;text-transform:uppercase;margin-top:4px">{esc(k)}</div></td>'
                    for v, k in items)
    return (f'<tr><td style="padding:6px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'style="background:{CARD};border:1px solid {LINE};border-radius:18px"><tr>{cells}</tr></table></td></tr>')


def render(d):
    rows = _stats([(d["n_results"], "results"), (len(d["champs"]), "champions"), (len(d["upsets"]), "upsets")])
    # destaque: o campeão com o ranking mais "beyond" da semana
    top = (d["beyond"] or d["champs"] or [None])[0]
    if top:
        ph = _photo(top["name"])
        rows += _h2("Champion of the week")
        img = (f'<tr><td style="padding:0 28px"><img src="{ph}" width="544" alt="{esc(top["name"])}" style="display:block;width:100%;max-width:544px;height:auto;border-radius:22px 22px 0 0"></td></tr>'
               if ph else "")
        rows += img + (f'<tr><td style="padding:0 28px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CARD};border:1px solid {LINE};border-radius:{"0 0 22px 22px" if ph else "22px"}">'
                       f'<tr><td style="padding:22px 22px 24px">'
                       f'<div style="font:900 34px/1.05 {FONT};color:{CREAM};letter-spacing:-1px;text-transform:uppercase">{esc(top["name"])}</div>'
                       f'<div style="font:600 15px/1.5 {FONT};color:{SOFT};margin-top:10px">' + (f'<span style="color:{VOLT};font-weight:800">#{top["rank"]}</span> · ' if top.get("rank") else "")
                       + f'won <b style="color:{CREAM}">{esc(top["t"] or "")}</b>, beating {esc(top["loser"])}</div>'
                       f'<div style="font:900 30px {FONT};color:{VOLT};margin-top:12px;letter-spacing:-0.5px">{esc(top["score"])}</div>'
                       f'<div style="margin-top:16px"><a href="{SITE}/m/{top["id"]}.html" style="display:inline-block;background:{VOLT};color:{INK};font:800 13px {FONT};padding:10px 18px;border-radius:999px;text-decoration:none">Full match →</a></div>'
                       f'</td></tr></table></td></tr>')
    others = [c for c in d["champs"] if c is not top][:6]
    if others:
        rows += _h2("More champions")
        for c in others:
            rows += _row("TITLE", esc(c["name"]), esc(f'{c["t"]} · ' + (f'#{c["rank"]} · ' if c.get("rank") else "") + c["score"]), f'{SITE}/m/{c["id"]}.html')
    if d["upsets"]:
        rows += _h2("Upsets of the week")
        for u in d["upsets"]:
            rows += _row(f'#{u["wr"]}', esc(f'{u["w"]} beat {u["l"]}') + f' <span style="color:{SOFT};font-weight:600">#{u["lr"]}</span>',
                         esc(f'{u["t"]} · {u["score"]}'), f'{SITE}/m/{u["id"]}.html', "#ff8a78")
    if any(d["climb"].values()):
        rows += _h2("Climbers · official rankings")
        for lg in ("atp", "wta"):
            for x in d["climb"][lg]:
                rows += _row(f'▲{x["prev"] - x["r"]}', esc(x["n"]), esc(f'{lg.upper()} · No. {x["prev"]} → No. {x["r"]}' + (f' · {x["age"]} years old' if isinstance(x.get("age"), int) and x["age"] <= 21 else "")),
                             f'{SITE}/rankings.html')
    if d["quals"]:
        rows += _h2("Qualifier watch")
        for q in d["quals"]:
            rows += _row("Q", esc(q["name"]), esc(f'{q["tournament"]} · {q["wins"]} main-draw win{"s" if q["wins"] > 1 else ""}' + ("" if q["alive"] else " · out")))
    # padel (azul, como o site do padel)
    prow = ""
    for c in d["pchamps"][:4]:
        if c.get("nation"):
            prow += _row("WORLD", esc(f'{c["pair"]}: world champions'), esc(f'{c["t"]} · {c["cat"]}'), f"{SITE}/padel/", "#9fd3ff")
        else:
            prow += _row("TITLE", esc(c["pair"]), esc(f'{c["t"]} · {c["cat"]}'), f"{SITE}/padel/", "#9fd3ff")
    rr = (d["race"].get("men") or {}).get("rows") or []
    if rr:
        prow += _row("RACE", "Race to the Finals", esc("Top 8 pairs qualify · " + ", ".join(x["name"].split()[-1] for x in sorted(rr, key=lambda x: x["ranking"])[6:10]) + " on the bubble"), f"{SITE}/padel/rankings.html", "#9fd3ff")
    for t in d["next_p"][:3]:
        prow += _row("NEXT", esc(t.get("name")), esc(f'Starts {t.get("start_date")} · {t.get("location") or ""}'), f"{SITE}/padel/tournaments.html", "#9fd3ff")
    if prow:
        rows += _h2("Padel", "#9fd3ff") + prow
    if d["next_t"]:
        rows += _h2("Coming up in tennis")
        for e in d["next_t"][:4]:
            rows += _row("NEXT", esc(e.get("name")), esc(f'Starts {(e.get("start") or "")[:10]} · {e.get("city") or ""}'), f"{SITE}/order-of-play.html")
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Beyond100 Weekly · Week {d['week']}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&display=swap" rel="stylesheet"></head>
<body style="margin:0;background:#04150f"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#04150f"><tr><td align="center" style="padding:24px 8px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:{G};border-radius:28px">
<tr><td style="padding:30px 28px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
<td style="font:900 15px {FONT};color:{CREAM};letter-spacing:1px">BEYOND100</td>
<td align="right" style="font:700 12px {FONT};color:{SOFT};letter-spacing:1.5px">WEEK {d['week']}</td></tr></table></td></tr>
<tr><td style="padding:22px 28px 4px;font:900 44px/0.98 {FONT};color:{CREAM};letter-spacing:-1.5px;text-transform:uppercase">The week<br><span style="color:{VOLT}">beyond the top 100</span></td></tr>
<tr><td style="padding:12px 28px 18px;font:500 15px/1.5 {FONT};color:{SOFT}">Tennis and padel from the Challenger, ITF, WTA and FIP courts, in two minutes.</td></tr>
{rows}
<tr><td style="padding:34px 28px 10px"><a href="{SITE}" style="display:block;text-align:center;background:{VOLT};color:{INK};font:800 15px {FONT};padding:15px 22px;border-radius:999px;text-decoration:none">All results on beyond100tennis.com →</a></td></tr>
<tr><td style="padding:14px 28px 30px;font:500 12px/1.6 {FONT};color:{SOFT}">Follow <a href="https://www.instagram.com/beyond100.tennis/" style="color:{CREAM}">@beyond100.tennis</a> and <a href="https://www.instagram.com/beyond100.padel/" style="color:{CREAM}">@beyond100.padel</a>.<br>
Photos: licensed (Wikimedia Commons / authorised), credits on the site. You get this because you subscribed on our site. <a href="{{{{unsubscribe_url}}}}" style="color:{SOFT}">Unsubscribe</a></td></tr>
</table></td></tr></table></body></html>"""


STATE = "newsletter_state.json"


def draft(d, html_out):
    """Domingo a partir das 19h (Lisboa): cria a newsletter da semana como RASCUNHO no Buttondown (nada é enviado sem o Afonso).
    Precisa do segredo BUTTONDOWN_API_KEY no repositório do motor. Uma vez por semana (newsletter_state.json)."""
    key = (os.environ.get("BUTTONDOWN_API_KEY") or "").strip()
    print(f"Newsletter: chave do Buttondown {'presente' if key else 'em falta (BUTTONDOWN_API_KEY)'}.")
    from zoneinfo import ZoneInfo
    now = dt.datetime.now(ZoneInfo("Europe/Lisbon"))
    wk = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    st = _load(STATE, {})
    force = os.environ.get("NEWSLETTER_FORCE") == "1"
    if not key or st.get("draft") == wk or (not force and not (now.weekday() == 6 and now.hour >= 19)):
        return False
    import requests
    subj = f"The week beyond the top 100 · Week {d['week']}"
    try:
        r = requests.post("https://api.buttondown.com/v1/emails", headers={"Authorization": f"Token {key}"},
                          json={"subject": subj, "body": html_out, "status": "draft"}, timeout=30)
    except Exception as e:
        print("Newsletter: Buttondown falhou", type(e).__name__)
        return False
    if r.status_code >= 300:
        print(f"Newsletter: Buttondown respondeu {r.status_code}: {r.text[:200]}")
        return False
    st["draft"] = wk
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f)
    print(f"Newsletter: rascunho criado no Buttondown ({subj}).")
    return True


def main():
    d = week_data()
    out = render(d)
    with open("newsletter.html", "w", encoding="utf-8") as f:
        f.write(out)
    os.makedirs("site/newsletter", exist_ok=True)
    with open("site/newsletter/latest.html", "w", encoding="utf-8") as f:
        f.write(out.replace("<head>", "<head><meta name=robots content=noindex>", 1))
    print(f"Newsletter: semana {d['week']}, {len(d['champs'])} campeões, {len(d['upsets'])} surpresas, {len(d['pchamps'])} campeões de padel.")
    try:
        draft(d, out.replace("{{unsubscribe_url}}", "{{ unsubscribe_url }}"))
    except Exception as e:
        print("Newsletter: rascunho falhou", type(e).__name__, e)


if __name__ == "__main__":
    main()
