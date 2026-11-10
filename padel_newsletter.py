"""Newsletter semanal de PADEL (10/11/2026, pedido do Afonso: uma para quem gosta de ténis, outra para quem gosta de padel).

Mesmo design da de ténis, em azul. Só dados que já temos (0 pedidos à Padel API):
  capa: campeões da semana (foto dos dois jogadores do par, se houver foto boa; senão capa desenhada)
  números da semana · campeões · surpresas (par com ranking muito pior ganha) · subidas no ranking oficial · Race · próximos torneios.
Lista própria no Buttondown (segunda conta grátis): BUTTONDOWN_PADEL_API_KEY. Ao domingo às 19h sai sozinha, como a de ténis.
Gera site/newsletter/padel.html (pré-visualização, noindex) e site/newsletter/cover-padel.jpg (capa dos convites do site).
"""
import datetime as dt
import json
import os

import newsletter as nl

STATE = "newsletter_padel_state.json"
LEVEL_ORDER = {"finals": 0, "major": 1, "p1": 2, "p2": 3, "fip_platinum": 4, "fip_gold": 5, "fip_silver": 6, "fip_other": 7}
PAL = {"G": "#0c2e4a", "DEEP": "#08223a", "SOFT": "#a9c0d6", "CARD": "#0b2740", "LINE": "#1d4466", "EDGE": "#24507a", "INK": "#08223a"}


def _other(t):
    return "team_2" if t == "team_1" else "team_1"


def _sets(m, w):
    return " ".join(f'{(x or {}).get(w)}-{(x or {}).get(_other(w))}' for x in (m.get("score") or []) if isinstance(x, dict))


def week_data(today=None):
    from padel.fetch import load_matches
    from padel import site as ps
    today = today or dt.date.today()
    start = (today - dt.timedelta(days=7)).isoformat()
    tours = nl._load("padel/data/tournaments.json", {})
    rk = nl._load("padel/data/rankings.json", {})
    rank_of = {}
    for cat in ("men", "women"):
        for x in (rk.get(cat) or {}).get("rows") or []:
            if isinstance(x.get("ranking"), int):
                rank_of[x["id"]] = x["ranking"]
    res = [m for m in load_matches().values() if (m.get("played_at") or "") >= start and m.get("winner") in ("team_1", "team_2")]
    champs, ties, ups = [], {}, []
    for m in res:
        t = tours.get(str(m.get("tid"))) or {}
        w = m["winner"]
        W, L = ps.team_players(m, w), ps.team_players(m, _other(w))
        if m.get("round") == 1:
            tie = m.get("tie")
            if isinstance(tie, dict):                              # Mundial (seleções): o campeão é o país
                if tie.get("winner") in ("team_1", "team_2"):
                    ties.setdefault((t.get("name"), tie.get(tie["winner"])), set()).add(m.get("category"))
                continue
            champs.append({"t": t.get("name"), "level": t.get("level"), "cat": m.get("category"), "pair": " / ".join(p.get("name") for p in W),
                           "pids": [p.get("id") for p in W], "short": [p.get("short_name") or (p.get("name") or "").split()[-1] for p in W],
                           "score": _sets(m, w), "loser": " / ".join(p.get("name") for p in L), "href": ps.mpath(m),
                           "rank": min([rank_of.get(p.get("id"), 999) for p in W] or [999])})
            continue
        if isinstance(m.get("tie"), dict) or len(W) != 2 or len(L) != 2:
            continue
        rw = [rank_of.get(p.get("id")) for p in W]
        rl = [rank_of.get(p.get("id")) for p in L]
        if None in rw or None in rl:
            continue
        aw, al = sum(rw) / 2, sum(rl) / 2
        if aw - al >= 30 and al <= 60:                             # surpresa: o par vencedor está, em média, 30+ lugares abaixo
            ups.append({"w": " / ".join(p.get("short_name") or p["name"].split()[-1] for p in W), "l": " / ".join(p.get("short_name") or p["name"].split()[-1] for p in L),
                        "wr": round(aw), "lr": round(al), "t": t.get("name"), "rd": m.get("round_name") or "", "score": _sets(m, w), "href": ps.mpath(m)})
    champs.sort(key=lambda c: (LEVEL_ORDER.get(c["level"], 9), c["cat"] != "men"))
    for (tn, nation), cats in ties.items():
        champs.insert(0, {"t": tn, "cat": " and ".join(sorted(cats, key=lambda c: c != "men")), "pair": nation, "nation": True, "short": [nation], "score": ""})
    ups.sort(key=lambda u: -(u["wr"] - u["lr"]))
    climb = {}
    for cat in ("men", "women"):
        rows = [x for x in (rk.get(cat) or {}).get("rows") or [] if (x.get("ranking_diff") or 0) > 0 and (x.get("ranking") or 999) <= 100]
        seen, out = set(), []
        for x in sorted(rows, key=lambda x: -x["ranking_diff"]):
            if x["id"] not in seen:
                seen.add(x["id"])
                out.append({"n": x["name"], "r": x["ranking"], "prev": x["ranking"] + x["ranking_diff"], "id": x["id"]})
        climb[cat] = out[:3]
    nxt = sorted([t for t in tours.values() if today.isoformat() < (t.get("start_date") or "") <= (today + dt.timedelta(days=8)).isoformat()],
                 key=lambda t: (t.get("start_date"), LEVEL_ORDER.get(t.get("level"), 9)))
    return {"week": today.isocalendar()[1], "date": today.isoformat(), "n_results": len(res), "pchamps": champs, "upsets": ups[:3],
            "climb": climb, "race": nl._load("padel/data/race.json", {}), "next_p": nxt[:4]}


def render(d, hero=""):
    """Usa as peças da newsletter de ténis com as cores do padel (azul)."""
    keep = {k: getattr(nl, k) for k in PAL}
    keep_defaults = (nl._panel.__defaults__,)
    try:
        for k, v in PAL.items():
            setattr(nl, k, v)
        nl._panel.__defaults__ = (PAL["CARD"], PAL["LINE"])
        return _render(d, hero)
    finally:
        for k, v in keep.items():
            setattr(nl, k, v)
        nl._panel.__defaults__ = keep_defaults[0]


def _render(d, hero):
    from padel import site as ps
    SITE, esc, FONT, VOLT, CREAM, SOFT, CARD, LINE, INK, DEEP = nl.SITE, nl.esc, nl.FONT, nl.VOLT, nl.CREAM, nl.SOFT, nl.CARD, nl.LINE, nl.INK, nl.DEEP
    SKY, CORAL, TIGHT = nl.SKY, nl.CORAL, nl.TIGHT
    _t, _tbl, _h2, _chip, _avatar, _item, _panel, _date = nl._t, nl._tbl, nl._h2, nl._chip, nl._avatar, nl._item, nl._panel, nl._date
    ch = d["pchamps"]
    cell = lambda v, k, bg, fg, sub: (f'<td width="33%" valign="top" style="padding:0 4px"><div style="background:{bg};border-radius:20px;padding:18px 16px 16px">'
                                       f'<div style="font:900 38px/1 {FONT};color:{fg};{TIGHT}">{v}</div>'
                                       f'<div style="font:800 11px {FONT};color:{fg};letter-spacing:1.5px;text-transform:uppercase;margin-top:10px;opacity:.85">{k}</div>'
                                       f'<div style="font:500 12px/1.35 {FONT};color:{fg};margin-top:4px;opacity:.7">{sub}</div></div></td>')
    rows = _t(_tbl('<tr>' + cell(d["n_results"], "matches", VOLT, INK, "Premier Padel and FIP")
                   + cell(len(ch), "champions", "#174a72", CREAM, "pairs and nations")
                   + cell(len(d["upsets"]), "upsets", CORAL, "#3a0d06", "30+ ranking places") + '</tr>'), "8px 20px 0")
    top = ch[0] if ch else None
    if top:
        rows += _h2("Champions of the week", "", SKY)
        href = SITE + (top.get("href") or "/padel/")
        if hero:
            rows += _t(f'<a href="{href}"><img src="{hero}" width="552" alt="{esc(top["pair"])}, champions in {esc(top.get("t") or "")}" '
                       f'style="display:block;width:100%;max-width:552px;height:auto;border-radius:24px;border:0"></a>')
        txt = (f'<b style="color:{CREAM}">{esc(top["pair"])}</b> are world champions: {esc(top.get("t") or "")}, {esc(top.get("cat") or "")}.' if top.get("nation") else
               f'<b style="color:{CREAM}">{esc(top["pair"])}</b> won <b style="color:{CREAM}">{esc(top.get("t") or "")}</b> ({esc(top.get("cat") or "")}): {esc(top.get("score") or "")} against {esc(top.get("loser") or "")}.')
        rows += _t(_tbl(f'<tr><td style="font:500 15px/1.55 {FONT};color:{SOFT}">{txt}</td>'
                        + (f'<td align="right" width="130" style="vertical-align:middle"><a href="{href}" style="display:inline-block;background:{CREAM};color:{INK};font:800 13px {FONT};padding:11px 16px;border-radius:999px;text-decoration:none"><span style="color:{INK}">Full match →</span></a></td>' if top.get("href") else "")
                        + '</tr>'), "16px 24px 0")
    others = ch[1:7]
    if others:
        rows += _h2("More champions", f"{len(ch)} TITLES", SKY)
        it = ""
        for i, c in enumerate(others):
            av = _avatar("", "WC" if c.get("nation") else ("M" if c.get("cat") == "men" else "W"), SKY)
            sub = esc(f'{c.get("t") or ""} · {c.get("cat") or ""}') + (f' · <span style="color:{CREAM}">{esc(c["score"])}</span>' if c.get("score") else "")
            it += _item(av, esc(c["pair"]), sub, _chip("World" if c.get("nation") else "Title", SKY, "#06233a"), SITE + (c.get("href") or "/padel/"), i == len(others) - 1)
        rows += _panel(it)
    if d["upsets"]:
        rows += _h2("Upsets of the week", "", CORAL)
        for u in d["upsets"]:
            rows += _t(f'<a href="{SITE}{u["href"]}" style="text-decoration:none">' + _tbl(
                f'<tr><td style="padding:18px 20px">' + _tbl(
                    f'<tr><td>{_chip(f"{u["wr"] - u["lr"]} places apart", CORAL, "#3a0d06")}</td><td align="right" style="font:600 12px {FONT};color:{SOFT}">{esc(u["t"] or "")} · {esc(u["rd"])}</td></tr>')
                + _tbl(f'<tr><td width="50%" style="padding-top:14px;vertical-align:top"><div style="font:900 34px/1 {FONT};color:{CORAL};{TIGHT}">#{u["wr"]}</div>'
                       f'<div style="font:700 15px/1.3 {FONT};color:{CREAM};margin-top:6px">{esc(u["w"])}</div></td>'
                       f'<td width="50%" align="right" style="padding-top:14px;vertical-align:top"><div style="font:900 34px/1 {FONT};color:{SOFT};{TIGHT};text-decoration:line-through">#{u["lr"]}</div>'
                       f'<div style="font:600 15px/1.3 {FONT};color:{SOFT};margin-top:6px">{esc(u["l"])}</div></td></tr>')
                + f'<div style="font:800 15px {FONT};color:{CREAM};margin-top:12px;{TIGHT}">{esc(u["score"]).replace(" ", "&nbsp;&nbsp;")}</div>'
                + f'<div style="font:500 11px {FONT};color:{SOFT};margin-top:6px">Average ranking of each pair.</div></td></tr>',
                f"background:{CARD};border:1px solid {LINE};border-left:4px solid {CORAL};border-radius:20px") + '</a>', "0 24px 10px")
    allc = [(c, x) for c in ("men", "women") for x in d["climb"].get(c) or []]
    if allc:
        rows += _h2("Climbers", "OFFICIAL RANKING", SKY)
        mx = max(x["prev"] - x["r"] for _, x in allc) or 1
        it = ""
        for i, (c, x) in enumerate(allc):
            up = x["prev"] - x["r"]
            w = max(8, round(100 * up / mx))
            bar = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:7px"><tr>'
                   f'<td width="{w}%" style="height:5px;background:{VOLT};border-radius:5px;font-size:0;line-height:0">&nbsp;</td>'
                   f'<td style="height:5px;font-size:0;line-height:0">&nbsp;</td></tr></table>')
            it += _item(_avatar("", "M" if c == "men" else "W", SKY), esc(x["n"]), f'{c.title()} · No. {x["prev"]} → <b style="color:{CREAM}">No. {x["r"]}</b>{bar}',
                        f'<span style="font:900 20px {FONT};color:{VOLT};{TIGHT}">▲{up}</span>', f'{SITE}{ps.ppath({"id": x["id"], "name": x["n"]})}', i == len(allc) - 1)
        rows += _panel(it)
    rr = (d["race"].get("men") or {}).get("rows") or []
    if rr:
        srt = sorted(rr, key=lambda x: x["ranking"])
        rows += _h2("Race to the Finals", "TOP 8 PAIRS QUALIFY", SKY)
        it = ""
        for i, x in enumerate(srt[5:10]):
            inside = x["ranking"] <= 8
            it += _item(f'<div style="width:48px;font:900 22px {FONT};color:{VOLT if inside else SOFT};{TIGHT}">#{x["ranking"]}</div>', esc(x["name"]),
                        esc(f'{x.get("points") or ""} points'), _chip("In" if inside else "Chasing", VOLT if inside else LINE, INK if inside else CREAM),
                        f"{SITE}/padel/rankings.html", i == len(srt[5:10]) - 1)
        rows += _panel(it)
    if d["next_p"]:
        rows += _h2("Coming up", "NEXT WEEK", SKY)
        nx = d["next_p"]
        rows += _panel("".join(_item(f'<div style="width:48px;text-align:center">{_date(t.get("start_date"))}</div>', esc(t.get("name")), esc(t.get("location") or ""),
                                     "", f"{SITE}{ps.tpath(t)}", i == len(nx) - 1) for i, t in enumerate(nx)))
    try:
        when = dt.date.fromisoformat(d["date"]).strftime("%-d %b %Y").upper()
    except ValueError:
        when = ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark">
<title>The padel week · Week {d['week']}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&display=swap" rel="stylesheet">
<style>@media (max-width:480px){{.h1{{font-size:46px!important}}}}</style></head>
<body style="margin:0;padding:0;background:#03101c">
<div style="display:none;max-height:0;overflow:hidden">{len(ch)} champions, {len(d['upsets'])} upsets and the Race to the Finals: the padel week in two minutes.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#03101c"><tr><td align="center" style="padding:20px 8px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:{DEEP};border-radius:32px;border:1px solid {LINE}">
<tr><td style="padding:26px 24px 0">{_tbl(f'<tr><td style="font:900 14px {FONT};color:{CREAM};letter-spacing:1px">BEYOND PADEL</td><td align="right">{_chip(f"Weekly · No. {d['week']}", LINE, CREAM)}</td></tr>')}</td></tr>
<tr><td style="padding:30px 24px 0;font:700 12px {FONT};color:{SOFT};letter-spacing:2px">{when}</td></tr>
<tr><td class="h1" style="padding:8px 24px 0;font:900 56px/0.92 {FONT};color:{CREAM};letter-spacing:-2.5px;text-transform:uppercase">The<br><span style="color:{VOLT}">padel<br>week</span></td></tr>
<tr><td style="padding:16px 24px 22px;font:500 16px/1.5 {FONT};color:{SOFT}">Premier Padel and the CUPRA FIP Tour. Champions, upsets and the race, in two minutes.</td></tr>
{rows}
<tr><td style="padding:40px 24px 0">{_tbl(f'<tr><td style="background:{VOLT};border-radius:24px;padding:26px 24px"><div style="font:900 26px/1.05 {FONT};color:{INK};letter-spacing:-1px">Every pair.<br>Every draw.</div>'
    f'<div style="font:600 14px/1.5 {FONT};color:{INK};margin:8px 0 16px;opacity:.8">Live scores, draws and rankings for Premier Padel and the FIP Tour.</div>'
    f'<a href="{SITE}/padel/" style="display:inline-block;background:{INK};color:{VOLT};font:800 14px {FONT};padding:12px 20px;border-radius:999px;text-decoration:none"><span style="color:{VOLT}">Open Beyond Padel →</span></a></td></tr>')}</td></tr>
<tr><td style="padding:22px 24px 4px"><a href="https://www.instagram.com/beyond100.padel/" style="text-decoration:none">{_chip("@beyond100.padel", LINE, CREAM)}</a></td></tr>
<tr><td style="padding:14px 24px 30px;font:500 12px/1.6 {FONT};color:{SOFT}">Data: Padel API. Photos: licensed (Wikimedia Commons / authorised), credits on the site. You get this because you subscribed on our site. <a href="{{{{unsubscribe_url}}}}" style="color:{SOFT}"><span style="color:{SOFT}">Unsubscribe</span></a></td></tr>
</table></td></tr></table></body></html>"""


def main():
    d = week_data()
    os.makedirs("site/newsletter", exist_ok=True)
    hero = ""
    try:
        wk = f"w{d['week']}"
        os.makedirs(f"site/newsletter/{wk}", exist_ok=True)
        if nl._padel_cover(d, "site/newsletter", big=f"site/newsletter/{wk}/padel-hero.jpg"):
            hero = f"{nl.SITE}/newsletter/{wk}/padel-hero.jpg"
    except Exception as e:
        print("Newsletter padel: capa falhou", type(e).__name__, e)
    out = render(d, hero)
    with open("site/newsletter/padel.html", "w", encoding="utf-8") as f:
        f.write(out.replace("<head>", "<head><meta name=robots content=noindex>", 1))
    print(f"Newsletter padel: semana {d['week']}, {d['n_results']} jogos, {len(d['pchamps'])} campeões, {len(d['upsets'])} surpresas.")
    nl._status(d, "BUTTONDOWN_PADEL_API_KEY", STATE, {"matches": d["n_results"], "champions": len(d["pchamps"]), "upsets": len(d["upsets"])})
    try:
        nl.draft(d, out.replace("{{unsubscribe_url}}", "{{ unsubscribe_url }}"), "BUTTONDOWN_PADEL_API_KEY", STATE,
                 f"The padel week · Week {d['week']}", d["n_results"] >= 20 and bool(d["pchamps"]))
    except Exception as e:
        print("Newsletter padel: envio falhou", type(e).__name__, e)


if __name__ == "__main__":
    main()
