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


CORAL, SKY, CARD, LINE = "#ff8a78", "#9fd3ff", "#0b2e24", "#1f4a3d"
FONT = "Inter,'Helvetica Neue',Helvetica,Arial,sans-serif"
TIGHT = "font-feature-settings:'tnum';letter-spacing:-0.5px"


def _photo_file(name):
    """Foto do jogador que passa no filtro de qualidade dos posts (nítida, grande, sem grupo) + crédito."""
    sl = slug(name)
    fp = f"photos/{sl}.jpg"
    if not os.path.exists(fp):
        return None, None
    try:
        import photo_quality
        if not photo_quality.card_ok(fp, name):
            return None, None
    except Exception:
        pass
    return fp, _load("photos/credits.json", {}).get(f"{sl}.jpg")


def _assets(d, out="site/newsletter"):
    """Imagens próprias da newsletter (renderizadas como os cartões do Instagram, por isso iguais em qualquer cliente de email):
    a capa do campeão da semana e miniaturas redondas dos jogadores. Vão para o site em /newsletter/w<semana>/."""
    from PIL import Image, ImageDraw, ImageOps
    import modern_cards as mc
    wk = f"w{d['week']}"
    od = os.path.join(out, wk)
    os.makedirs(od, exist_ok=True)
    url = lambda fn: f"{SITE}/newsletter/{wk}/{fn}"
    res = {"hero": "", "thumbs": {}}
    top = d.get("top")
    fp, cr = _photo_file(top["name"]) if top else (None, None)
    if fp:
        P = mc.PALETTE["tennis"]
        W_, H_ = 1200, 1380
        img = Image.new("RGBA", (W_, H_), P["bg"] + (255,))
        img.alpha_composite(mc._photo(fp, (W_, H_), (0.5, 0.18)))
        img = mc._grad(img, 0, 300, (0, 0, 0), 150, 0)
        img = mc._grad(img, 560, H_, P["bg"], 0, 255).convert("RGB")
        dr = ImageDraw.Draw(img, "RGBA")
        mc._chips(dr, 64, 64, ["TITLE", f"#{top['rank']}" if top.get("rank") else "", (top.get("t") or "").upper()], P, 30)
        nm = top["name"].split()
        if len(nm) > 1:
            dr.text((66, 930), " ".join(nm[:-1]).upper(), font=mc.F("bold", 46), fill=P["cream"], anchor="ls")
        mc._paste_sq(img, nm[-1].upper(), "black", 240, P["cream"] + (255,), 56, 1150, W_ - 120, sx=0.72, anchor="lb")
        dr = ImageDraw.Draw(img, "RGBA")
        x = 64
        for st in (top.get("score") or "").split():
            a_, _, b_ = st.partition("-")
            won = a_[:1].isdigit() and b_[:1].isdigit() and int(a_[:1]) > int(b_[:1])
            f = mc.F("black", 96)
            dr.text((x, 1270), st, font=f, fill=P["acc"] if won else P["soft"], anchor="ls")
            x += dr.textlength(st, font=f) + 44
        dr.text((66, 1330), f"def. {top.get('loser') or ''}", font=mc.F("semi", 32), fill=P["cream"], anchor="ls")
        if cr:
            dr.text((W_ - 64, 1330), cr, font=mc._fit(dr, cr, "med", 20, 520, 12), fill=P["soft"], anchor="rs")
        img.save(os.path.join(od, "hero.jpg"), quality=86, optimize=True, progressive=True)
        res["hero"] = url("hero.jpg")
    names = [c["name"] for c in d.get("others", [])] + [u["w"] for u in d.get("upsets", [])] + [x["n"] for lg in ("atp", "wta") for x in d["climb"][lg]]
    for n in dict.fromkeys(names):
        fp, _ = _photo_file(n)
        if not fp:
            continue
        s = 160
        im = ImageOps.fit(Image.open(fp).convert("RGB"), (s, s), Image.LANCZOS, centering=(0.5, 0.2))
        mk = Image.new("L", (s * 4, s * 4), 0)
        ImageDraw.Draw(mk).ellipse([0, 0, s * 4 - 1, s * 4 - 1], fill=255)
        bg = Image.new("RGB", (s, s), (11, 46, 36))          # fundo igual ao cartão (sem transparência, que o Outlook estraga)
        bg.paste(im, (0, 0), mk.resize((s, s), Image.LANCZOS))
        fn = f"{slug(n)}.jpg"
        bg.save(os.path.join(od, fn), quality=85)
        res["thumbs"][n] = url(fn)
    return res


def _t(inner, pad="0 24px"):
    return f'<tr><td style="padding:{pad}">{inner}</td></tr>'


def _tbl(inner, style=""):
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:separate;{style}">{inner}</table>'


def _h2(t, n="", c=VOLT):
    num = f'<td align="right" style="font:700 12px {FONT};color:{SOFT};letter-spacing:1.5px">{esc(str(n))}</td>' if n != "" else ""
    return _t(_tbl(f'<tr><td style="font:800 12px {FONT};letter-spacing:2.5px;color:{c};text-transform:uppercase">'
                   f'<span style="display:inline-block;width:8px;height:8px;border-radius:8px;background:{c};margin-right:8px;vertical-align:1px"></span>{esc(t)}</td>{num}</tr>'),
              "40px 24px 14px")


def _chip(t, bg, fg=INK):
    return f'<span style="display:inline-block;background:{bg};color:{fg};font:800 11px {FONT};letter-spacing:1px;padding:5px 10px;border-radius:999px;text-transform:uppercase;white-space:nowrap">{t}</span>'


def _avatar(url, label, color):
    if url:
        return f'<img src="{url}" width="48" height="48" alt="" style="display:block;width:48px;height:48px;border-radius:48px;border:2px solid {color}">'
    return (f'<div style="width:48px;height:48px;border-radius:48px;background:{LINE};color:{color};font:900 16px/48px {FONT};text-align:center">{label}</div>')


def _item(av, title, sub, right="", href="", last=False):
    a0, a1 = (f'<a href="{esc(href)}" style="color:{CREAM};text-decoration:none">', "</a>") if href else ("", "")
    return (f'<tr><td width="60" style="padding:12px 0;vertical-align:middle{"" if last else f";border-bottom:1px solid {LINE}"}">{av}</td>'
            f'<td style="padding:12px 0;vertical-align:middle{"" if last else f";border-bottom:1px solid {LINE}"}"><div style="font:700 16px/1.3 {FONT};color:{CREAM}">{a0}{title}{a1}</div>'
            f'<div style="font:500 13px/1.45 {FONT};color:{SOFT};margin-top:2px">{sub}</div></td>'
            f'<td align="right" style="padding:12px 0 12px 10px;vertical-align:middle;white-space:nowrap{"" if last else f";border-bottom:1px solid {LINE}"}">{right}</td></tr>')


def _panel(rows, bg=CARD, line=LINE):
    return _t(_tbl(f'<tr><td style="padding:6px 18px">{_tbl(rows)}</td></tr>', f"background:{bg};border:1px solid {line};border-radius:22px"))


def _bento(d):
    cell = lambda v, k, bg, fg, sub: (f'<td width="33%" valign="top" style="padding:0 4px"><div style="background:{bg};border-radius:20px;padding:18px 16px 16px">'
                                       f'<div style="font:900 38px/1 {FONT};color:{fg};{TIGHT}">{v}</div>'
                                       f'<div style="font:800 11px {FONT};color:{fg};letter-spacing:1.5px;text-transform:uppercase;margin-top:10px;opacity:.85">{k}</div>'
                                       f'<div style="font:500 12px/1.35 {FONT};color:{fg};margin-top:4px;opacity:.7">{sub}</div></div></td>')
    beyond = len(d["beyond"])
    return _t(_tbl('<tr>' + cell(d["n_results"], "results", VOLT, INK, "tracked this week")
                   + cell(len(d["champs"]), "champions", "#174a3a", CREAM, f"{beyond} from outside the top 100" if beyond else "on tour")
                   + cell(len(d["upsets"]), "upsets", CORAL, "#3a0d06", "150+ ranking places") + '</tr>'), "8px 20px 0")


def _date(s):
    try:
        x = dt.date.fromisoformat((s or "")[:10])
        return f'<div style="font:900 22px/1 {FONT};color:{CREAM};{TIGHT}">{x.day}</div><div style="font:800 10px {FONT};color:{SOFT};letter-spacing:1.5px;margin-top:3px">{x.strftime("%b").upper()}</div>'
    except ValueError:
        return ""


def render(d, assets=None):
    A = assets or {"hero": "", "thumbs": {}}
    th = A["thumbs"]
    top = d.get("top")
    rows = _bento(d)
    if top:
        rows += _h2("Champion of the week")
        if A["hero"]:
            rows += _t(f'<a href="{SITE}/m/{top["id"]}.html"><img src="{A["hero"]}" width="552" alt="{esc(top["name"])}, champion in {esc(top.get("t") or "")}: {esc(top["score"])}" '
                       f'style="display:block;width:100%;max-width:552px;height:auto;border-radius:24px;border:0"></a>')
        else:
            rows += _panel(_item(_avatar("", "T", VOLT), esc(top["name"]), esc(f'{top.get("t")} · def. {top["loser"]}'), f'<span style="font:900 18px {FONT};color:{VOLT}">{esc(top["score"])}</span>', last=True))
        rows += _t(_tbl(f'<tr><td style="font:500 15px/1.55 {FONT};color:{SOFT}">'
                        + (f'Ranked <b style="color:{CREAM}">#{top["rank"]}</b> and still the last one standing in <b style="color:{CREAM}">{esc(top.get("t") or "")}</b>. ' if top.get("rank") else "")
                        + f'Final: {esc(top["score"])} against {esc(top["loser"])}.</td>'
                        f'<td align="right" width="130" style="vertical-align:middle"><a href="{SITE}/m/{top["id"]}.html" style="display:inline-block;background:{CREAM};color:{INK};font:800 13px {FONT};padding:11px 16px;border-radius:999px;text-decoration:none">Full match →</a></td></tr>'),
                   "16px 24px 0")
    if d["others"]:
        rows += _h2("More champions", f'{len(d["champs"])} TITLES')
        it = ""
        for i, c in enumerate(d["others"]):
            beyond = isinstance(c.get("rank"), int) and c["rank"] > 100
            it += _item(_avatar(th.get(c["name"]), "T", VOLT), esc(c["name"]), esc(c["t"] or "") + f' · <span style="color:{CREAM}">{esc(c["score"])}</span>',
                        _chip(f'#{c["rank"]}', VOLT if beyond else LINE, INK if beyond else CREAM) if c.get("rank") else "",
                        f'{SITE}/m/{c["id"]}.html', i == len(d["others"]) - 1)
        rows += _panel(it)
    if d["upsets"]:
        rows += _h2("Upsets of the week", "", CORAL)
        for u in d["upsets"]:
            gap = u["wr"] - u["lr"]
            rows += _t(f'<a href="{SITE}/m/{u["id"]}.html" style="text-decoration:none">' + _tbl(
                f'<tr><td style="padding:18px 20px">' + _tbl(
                    f'<tr><td>{_chip(f"{gap} places apart", CORAL, "#3a0d06")}</td><td align="right" style="font:600 12px {FONT};color:{SOFT}">{esc(u["t"] or "")}</td></tr>')
                + _tbl(f'<tr><td width="50%" style="padding-top:14px;vertical-align:top"><div style="font:900 34px/1 {FONT};color:{CORAL};{TIGHT}">#{u["wr"]}</div>'
                       f'<div style="font:700 15px/1.3 {FONT};color:{CREAM};margin-top:6px">{esc(u["w"])}</div></td>'
                       f'<td width="50%" align="right" style="padding-top:14px;vertical-align:top"><div style="font:900 34px/1 {FONT};color:{SOFT};{TIGHT};text-decoration:line-through">#{u["lr"]}</div>'
                       f'<div style="font:600 15px/1.3 {FONT};color:{SOFT};margin-top:6px">{esc(u["l"])}</div></td></tr>')
                + f'<div style="font:800 15px {FONT};color:{CREAM};margin-top:12px;{TIGHT}">{esc(u["score"]).replace(" ", "&nbsp;&nbsp;")}</div></td></tr>',
                f"background:{CARD};border:1px solid {LINE};border-left:4px solid {CORAL};border-radius:20px") + '</a>', "0 24px 10px")
    if any(d["climb"].values()):
        rows += _h2("Climbers", "OFFICIAL RANKINGS")
        allc = [(lg, x) for lg in ("atp", "wta") for x in d["climb"][lg]]
        mx = max(x["prev"] - x["r"] for _, x in allc) or 1
        it = ""
        for i, (lg, x) in enumerate(allc):
            up = x["prev"] - x["r"]
            w = max(8, round(100 * up / mx))
            bar = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:7px"><tr>'
                   f'<td width="{w}%" style="height:5px;background:{VOLT};border-radius:5px;font-size:0;line-height:0">&nbsp;</td>'
                   f'<td style="height:5px;font-size:0;line-height:0">&nbsp;</td></tr></table>')
            young = f' · {x["age"]} yo' if isinstance(x.get("age"), int) and x["age"] <= 21 else ""
            it += _item(_avatar(th.get(x["n"]), lg.upper(), VOLT), esc(x["n"]), f'{lg.upper()} · No. {x["prev"]} → <b style="color:{CREAM}">No. {x["r"]}</b>{young}{bar}',
                        f'<span style="font:900 20px {FONT};color:{VOLT};{TIGHT}">▲{up}</span>', f'{SITE}/rankings.html', i == len(allc) - 1)
        rows += _panel(it)
    if d["quals"]:
        rows += _h2("Qualifier watch", "FROM QUALIFYING")
        it = ""
        for i, q in enumerate(d["quals"]):
            it += _item(_avatar("", "Q", VOLT), esc(q["name"]), esc(q["tournament"]),
                        _chip(f'{q["wins"]} win{"s" if q["wins"] > 1 else ""}' + ("" if q["alive"] else " · out"), VOLT if q["alive"] else LINE, INK if q["alive"] else CREAM),
                        "", i == len(d["quals"]) - 1)
        rows += _panel(it)
    # padel: bloco azul, como o site do padel
    pit = []
    for c in d["pchamps"][:4]:
        if c.get("nation"):
            pit.append((_avatar("", "WC", SKY), esc(f'{c["pair"]}: world champions'), esc(f'{c["t"]} · {c["cat"]}'), _chip("World", SKY, "#06233a")))
        else:
            pit.append((_avatar("", "T", SKY), esc(c["pair"]), esc(f'{c["t"]} · {c["cat"]}'), _chip("Title", SKY, "#06233a")))
    rr = (d["race"].get("men") or {}).get("rows") or []
    if rr:
        bub = ", ".join(x["name"].split()[-1] for x in sorted(rr, key=lambda x: x["ranking"])[6:10])
        pit.append((_avatar("", "8", SKY), "Race to the Finals", esc(f"Top 8 pairs qualify · on the bubble: {bub}"), _chip("Race", "#173f61", CREAM)))
    for t in d["next_p"][:3]:
        pit.append((f'<div style="width:48px;text-align:center">{_date(t.get("start_date"))}</div>', esc(t.get("name")), esc(t.get("location") or ""), _chip("Next", "#173f61", CREAM)))
    if pit:
        rows += _h2("Padel", "BEYOND PADEL", SKY)
        rows += _panel("".join(_item(a, b, c, r, f"{SITE}/padel/", i == len(pit) - 1) for i, (a, b, c, r) in enumerate(pit)), "#0b2740", "#1d4466")
    if d["next_t"]:
        rows += _h2("Coming up in tennis")
        nx = d["next_t"][:4]
        rows += _panel("".join(_item(f'<div style="width:48px;text-align:center">{_date(e.get("start"))}</div>', esc(e.get("name")), esc(e.get("city") or ""),
                                     "", f"{SITE}/order-of-play.html", i == len(nx) - 1) for i, e in enumerate(nx)))
    try:
        when = dt.date.fromisoformat(d["date"]).strftime("%-d %b %Y").upper()
    except ValueError:
        when = ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark">
<title>The week beyond the top 100 · Week {d['week']}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;600;700;800;900&display=swap" rel="stylesheet">
<style>@media (max-width:480px){{.h1{{font-size:46px!important}}}}</style></head>
<body style="margin:0;padding:0;background:#03110c">
<div style="display:none;max-height:0;overflow:hidden">{len(d['champs'])} champions, {len(d['upsets'])} upsets and the week's biggest climbers, from the courts beyond the top 100.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#03110c"><tr><td align="center" style="padding:20px 8px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background:{DEEP};border-radius:32px;border:1px solid {LINE}">
<tr><td style="padding:26px 24px 0">{_tbl(f'<tr><td style="font:900 14px {FONT};color:{CREAM};letter-spacing:1px">BEYOND100</td><td align="right">{_chip(f"Weekly · No. {d['week']}", LINE, CREAM)}</td></tr>')}</td></tr>
<tr><td style="padding:30px 24px 0;font:700 12px {FONT};color:{SOFT};letter-spacing:2px">{when}</td></tr>
<tr><td class="h1" style="padding:8px 24px 0;font:900 56px/0.92 {FONT};color:{CREAM};letter-spacing:-2.5px;text-transform:uppercase">The week<br><span style="color:{VOLT}">beyond<br>the top 100</span></td></tr>
<tr><td style="padding:16px 24px 22px;font:500 16px/1.5 {FONT};color:{SOFT}">Challenger, ITF, WTA 125 and FIP padel. Everything that mattered, in two minutes.</td></tr>
{rows}
<tr><td style="padding:40px 24px 0">{_tbl(f'<tr><td style="background:{VOLT};border-radius:24px;padding:26px 24px"><div style="font:900 26px/1.05 {FONT};color:{INK};letter-spacing:-1px">Every player.<br>Every draw.</div>'
    f'<div style="font:600 14px/1.5 {FONT};color:{INK};margin:8px 0 16px;opacity:.8">Live scores, draws and rankings for over 2,000 players.</div>'
    f'<a href="{SITE}" style="display:inline-block;background:{INK};color:{VOLT};font:800 14px {FONT};padding:12px 20px;border-radius:999px;text-decoration:none">Open beyond100tennis.com →</a></td></tr>')}</td></tr>
<tr><td style="padding:22px 24px 4px">{_tbl(f'<tr><td><a href="https://www.instagram.com/beyond100.tennis/" style="text-decoration:none">{_chip("@beyond100.tennis", LINE, CREAM)}</a> <a href="https://www.instagram.com/beyond100.padel/" style="text-decoration:none">{_chip("@beyond100.padel", "#173f61", CREAM)}</a></td></tr>')}</td></tr>
<tr><td style="padding:14px 24px 30px;font:500 12px/1.6 {FONT};color:{SOFT}">Photos: licensed (Wikimedia Commons / authorised), credits on the site. You get this because you subscribed on our site. <a href="{{{{unsubscribe_url}}}}" style="color:{SOFT}">Unsubscribe</a></td></tr>
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
    subj = ("[TEST] " if force else "") + f"The week beyond the top 100 · Week {d['week']}"
    try:
        r = requests.post("https://api.buttondown.com/v1/emails", headers={"Authorization": f"Token {key}"},
                          json={"subject": subj, "body": html_out, "status": "draft"}, timeout=30)
    except Exception as e:
        print("Newsletter: Buttondown falhou", type(e).__name__)
        return False
    if r.status_code >= 300:
        print(f"Newsletter: Buttondown respondeu {r.status_code}: {r.text[:200]}")
        return False
    if force:                                                   # teste manual: não conta como o rascunho da semana
        print(f"Newsletter: rascunho de TESTE criado no Buttondown ({subj}).")
        return True
    st["draft"] = wk
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f)
    print(f"Newsletter: rascunho criado no Buttondown ({subj}).")
    return True


def main():
    d = week_data()
    d["top"] = (d["beyond"] or d["champs"] or [None])[0]
    rest = [c for c in d["beyond"] + d["champs"] if c is not d["top"]]
    d["others"] = list({id(c): c for c in rest}.values())[:6]          # primeiro os de fora do top 100
    try:
        assets = _assets(d)
    except Exception as e:
        print("Newsletter: imagens falharam", type(e).__name__, e)
        assets = None
    out = render(d, assets)
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
