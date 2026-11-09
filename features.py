"""Road to the Top 100, Power Ranking e Recordes da época: páginas do site e cartões semanais.
Só dados próprios (results.json e ranks.json, com o ranking que cada jogador tinha nos jogos que acompanhámos)."""
import datetime
import html
import json
import os
import sys
import time

from PIL import Image, ImageDraw

import photo_cards as pc
import webapp

esc = html.escape
G = {"men": "Men", "women": "Women"}


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _singles(results):
    return [r for r in results if not r.get("q") and r.get("winner") in (1, 2) and webapp.classify(r)[1] == "singles"]


def genders(results):
    out = {}
    for r in results:
        g = webapp.classify(r)[0]
        if g in ("men", "women"):
            for i in (1, 2):
                out[webapp.slugify(r["p%d" % i]["name"])] = g
    return out


def _plink(name, linkable):
    s = webapp.slugify(name)
    return f'<a href="/p/{s}.html">{esc(name)}</a>' if s in linkable else esc(name)


# ---------------------------------------------------------------- Road to the Top 100
def road(results, ranks, lo=101, hi=130):
    """{gender: [ {name, country, rank, prev, pts, gap, date} ]} com os rankings mais recentes que registámos."""
    gm = genders(results)
    best = {}
    for v in ranks.values():
        nm, rk = v.get("name"), v.get("rank")
        if not nm or not isinstance(rk, int):
            continue
        k = webapp.slugify(nm)
        if k not in best or v.get("ts", 0) > best[k].get("ts", 0):
            best[k] = v
    cut100 = {}
    for k, v in best.items():
        g = gm.get(k)
        if g and v["rank"] == 100 and isinstance(v.get("pts"), (int, float)):
            cut100[g] = v["pts"]
    out = {"men": [], "women": []}
    for k, v in best.items():
        g = gm.get(k)
        if g not in out or not (lo <= v["rank"] <= hi):
            continue
        pts = v.get("pts") if isinstance(v.get("pts"), (int, float)) else None
        gap = (cut100[g] - pts) if (g in cut100 and pts is not None and cut100[g] > pts) else None
        out[g].append({"name": v["name"], "slug": k, "country": v.get("country"), "rank": v["rank"], "prev": v.get("prev"),
                       "pts": pts, "gap": gap, "date": v.get("date", "")})
    for g in out:
        out[g].sort(key=lambda x: x["rank"])
    return out


def road_page(data, linkable, flag=lambda c: ""):
    def table(rows):
        if not rows:
            return '<p class="empty">No players in this range in our recent data.</p>'
        tr = ""
        for x in rows:
            mv = ""
            if isinstance(x.get("prev"), int) and x["prev"] != x["rank"]:
                d = x["prev"] - x["rank"]
                mv = f'<span class="{"up" if d > 0 else "dn"}">{"▲" if d > 0 else "▼"}{abs(d)}</span>'
            tr += (f'<tr><td><b>#{x["rank"]}</b></td><td class="pn">{flag(x.get("country"))}{_plink(x["name"], linkable)}</td>'
                   f'<td>{mv}</td><td>{(str(int(x["pts"])) + " pts") if x.get("pts") is not None else ""}'
                   f'{(" · " + str(int(x["gap"])) + " to go") if x.get("gap") else ""}</td></tr>')
        return f'<table class="pt"><thead><tr><th>Rank</th><th>Player</th><th>Move</th><th>Points</th></tr></thead><tbody>{tr}</tbody></table>'
    return ('<section class="page-h"><h1>Road to the Top 100</h1><p>The players ranked 101 to 130: the ones knocking on the door. '
            'Official ATP and WTA rankings of the week; “to go” is the gap in points to the player at No. 100.</p></section>'
            + "".join(f'<h2 class="dh">{G[g]}</h2>{table(data.get(g, []))}' for g in ("men", "women")))


# ---------------------------------------------------------------- Power Ranking
def power(results, ranks_latest, days=14, n=10):
    """Forma recente fora do top 100: vitórias, qualidade dos adversários e rondas finais. Fórmula simples e pública."""
    cut = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    st = {}
    for r in _singles(results):
        if (r.get("date") or "") < cut:
            continue
        rr = webapp._round_rank(r.get("round"))
        for i in (1, 2):
            p, o = r["p%d" % i], r["p%d" % (3 - i)]
            k = webapp.slugify(p["name"])
            e = st.setdefault(k, {"name": p["name"], "country": p.get("country"), "w": 0, "l": 0, "score": 0.0, "titles": 0,
                                  "best": None, "gender": webapp.classify(r)[0], "rank": p.get("rank"), "rd": ""})
            if isinstance(p.get("rank"), int) and (r.get("date") or "") >= e["rd"]:
                e["rank"], e["rd"] = p["rank"], r.get("date") or ""
            if r["winner"] == i:
                e["w"] += 1
                pr, orr = p.get("rank"), o.get("rank")
                e["score"] += 1 + (min(2.0, (pr - orr) / 100) if isinstance(pr, int) and isinstance(orr, int) and pr > orr else 0)
                if rr == 0:
                    e["score"] += 2
                    e["titles"] += 1
                elif rr == 1:
                    e["score"] += 0.5
                if isinstance(orr, int) and (e["best"] is None or orr < e["best"][0]):
                    e["best"] = (orr, o["name"])
            else:
                e["l"] += 1
                e["score"] -= 0.3
    out = {"men": [], "women": []}
    for k, e in st.items():
        rk = (ranks_latest.get(k) or e["rank"])
        if e["gender"] not in out or not isinstance(rk, int) or rk <= 100 or e["w"] < 3:
            continue
        out[e["gender"]].append(dict(e, slug=k, rank=rk, score=round(e["score"], 1)))
    for g in out:
        out[g] = sorted(out[g], key=lambda e: (-e["score"], e["l"], e["rank"]))[:n]
    return out


def power_page(data, linkable, flag=lambda c: ""):
    def table(rows):
        if not rows:
            return '<p class="empty">Not enough matches yet.</p>'
        tr = "".join(f'<tr><td><b>{i}</b></td><td class="pn">{flag(e.get("country"))}{_plink(e["name"], linkable)} <small>#{e["rank"]}</small></td>'
                     f'<td>{e["w"]}-{e["l"]}</td><td>{("🏆" * e["titles"]) or ""}{(" best win: " + esc(e["best"][1]) + " #" + str(e["best"][0])) if e.get("best") else ""}</td>'
                     f'<td><b>{e["score"]}</b></td></tr>' for i, e in enumerate(rows, 1))
        return f'<table class="pt"><thead><tr><th>#</th><th>Player</th><th>W-L</th><th>Highlights</th><th>Score</th></tr></thead><tbody>{tr}</tbody></table>'
    return ('<section class="page-h"><h1>Power Ranking</h1><p>Our ranking of the players in the best form outside the top 100, over the last 14 days. '
            'Score: 1 per win, a bonus for beating better-ranked players (up to 2), +2 for a title, +0.5 for a semifinal win, −0.3 per loss. '
            'At least 3 wins to enter.</p></section>'
            + "".join(f'<h2 class="dh">{G[g]}</h2>{table(data.get(g, []))}' for g in ("men", "women")))


# ---------------------------------------------------------------- Recordes da época
def records(results, year=None, prefix=None):
    """Líderes do ano (ou do mês, com prefix='AAAA-MM')."""
    year = str(year or datetime.date.today().year)
    prefix = prefix or year
    P = {}
    for r in _singles(results):
        if not (r.get("date") or "").startswith(prefix):
            continue
        ms = webapp.match_stats(r)
        g = webapp.classify(r)[0]
        if g not in ("men", "women"):
            continue
        w = r["winner"]
        for i in (1, 2):
            p = r["p%d" % i]
            k = (g, webapp.slugify(p["name"]))
            e = P.setdefault(k, {"name": p["name"], "country": p.get("country"), "wins": 0, "titles": 0, "tb": 0, "comebacks": 0,
                                 "bagels": 0, "upset": 0, "upset_vs": ""})
            if i != w:
                continue
            e["wins"] += 1
            if webapp._round_rank(r.get("round")) == 0:
                e["titles"] += 1
            mine, other = (r["games"][0], r["games"][1]) if w == 1 else (r["games"][1], r["games"][0])
            e["tb"] += sum(1 for a, b in zip(mine, other) if (a, b) == (7, 6))
            e["bagels"] += sum(1 for a, b in zip(mine, other) if a >= 6 and b == 0)
            if ms and "comeback" in ms[0]:
                e["comebacks"] += 1
            pr, orr = p.get("rank"), r["p%d" % (3 - i)].get("rank")
            if isinstance(pr, int) and isinstance(orr, int) and pr - orr > e["upset"]:
                e["upset"], e["upset_vs"] = pr - orr, f'{r["p%d" % (3 - i)]["name"]} #{orr} as #{pr}'
    cats = [("wins", "Most wins"), ("titles", "Most titles"), ("comebacks", "Comeback wins (lost the first set)"),
            ("tb", "Tie-breaks won"), ("bagels", "6-0 sets won"), ("upset", "Biggest upset (ranking places)")]
    out = {}
    for g in ("men", "women"):
        out[g] = {}
        for key, _ in cats:
            rows = sorted((e for (gg, _k), e in P.items() if gg == g and e[key] > 0), key=lambda e: -e[key])[:5]
            out[g][key] = rows
    return out, cats, year


def records_page(data, linkable, flag=lambda c: ""):
    rec, cats, year = data
    body = (f'<section class="page-h"><h1>Season records {year}</h1><p>The leaders of the season in the matches we tracked on the Challenger, '
            f'ITF and WTA tours (main draws, singles). Updated every day.</p></section>')
    for g in ("men", "women"):
        body += f'<h2 class="dh">{G[g]}</h2><div class="numgrid" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">'
        for key, label in cats:
            rows = rec[g].get(key) or []
            li = "".join(f'<li style="margin:4px 0">{flag(e.get("country"))}{_plink(e["name"], linkable)} <strong style="color:var(--v)">{e[key]}</strong>'
                         f'{(" <small>(" + esc(e["upset_vs"]) + ")</small>") if key == "upset" else ""}</li>' for e in rows)
            body += (f'<div class="nbox" style="text-align:left"><span>{esc(label)}</span>'
                     f'<ol style="margin:8px 0 0;padding-left:20px">{li or "<li>–</li>"}</ol></div>')
        body += "</div>"
    return body


# ---------------------------------------------------------------- cartões semanais (posts)
def _list_card(title, sub, rows, out, foot):
    """rows: [(esquerda, nome, direita, destaque)]"""
    img = pc._gradient()
    pc._court(img)
    pc._header(img)
    d = ImageDraw.Draw(img)
    d.text((pc.W / 2, 200), title, font=pc.fit(d, title, pc.SERIF_B, 84, 960, 40), fill=pc.CREAM, anchor="mm")
    d.text((pc.W / 2, 270), sub, font=pc.fit(d, sub, pc.SANS_B, 30, 960, 18), fill=pc.VOLT, anchor="mm")
    h = min(118, int(860 / max(1, len(rows))))                  # poucas linhas: maiores e centradas (sem espaço morto em baixo)
    y = 330 + max(0, (860 - h * len(rows)) // 3)
    for left, name, right, hot in rows:
        if left is None:                         # linha de secção
            d.text((90, y + h / 2), name, font=pc.font(pc.SANS_B, 28), fill=pc.SOFT, anchor="lm")
            y += h
            continue
        d.rounded_rectangle([70, y + 6, pc.W - 70, y + h - 6], radius=20, fill=pc.DEEP, outline=pc.EDGE, width=2)
        k = h / 86                                                  # letra acompanha a altura da linha
        d.text((110, y + h / 2), left, font=pc.font(pc.SERIF_B, int(34 * k)), fill=pc.VOLT if hot else pc.CREAM, anchor="lm")
        fr = pc.fit(d, right, pc.SANS_B, int(29 * k), 280, 16)
        rw = d.textlength(right, font=fr)
        d.text((250, y + h / 2), name, font=pc.fit(d, name, pc.SERIF_B, int(38 * k), int(pc.W - 110 - rw - 40 - 250), 18), fill=pc.CREAM, anchor="lm")
        d.text((pc.W - 110, y + h / 2), right, font=fr, fill=pc.VOLT if hot else pc.SOFT, anchor="rm")
        y += h
    d.text((pc.W / 2, 1230), foot, font=pc.fit(d, foot, pc.SERIF_I, 32, 940, 18), fill=pc.SOFT, anchor="mm")
    pc._footer(img)
    img.save(out, quality=95)
    return out


def road_official(max_age_d=8):
    """Road to the Top 100 a partir do ranking OFICIAL da semana (espn_rank.json: ATP e WTA até ao 150), 9/11/2026.
    O antigo (ranks.json, ranking visto nos jogos) estava desatualizado: no post de 9/11 o Piros aparecia em 101 já sendo 99.
    {gender: [{name, rank, pts, prev, move, gap}]}, ou None se não houver ranking recente."""
    d = _load("espn_rank.json", {})
    if not d or time.time() - (d.get("ts") or 0) > max_age_d * 86400:
        return None
    out = {}
    for lg, g in (("atp", "men"), ("wta", "women")):
        xs = d.get(lg) or []
        p100 = next((x.get("pts") for x in xs if x.get("r") == 100), None)
        rows = []
        for x in xs:
            if not (101 <= (x.get("r") or 0) <= 130):
                continue
            prev = x.get("prev") if isinstance(x.get("prev"), int) else None
            rows.append({"name": x.get("n"), "rank": x["r"], "pts": x.get("pts"), "prev": prev,
                         "move": (prev - x["r"]) if prev else 0, "slug": webapp.slugify(x.get("n") or ""), "country": (x.get("c") or "").upper(),
                         "gap": (p100 - x["pts"]) if isinstance(p100, int) and isinstance(x.get("pts"), int) else None, "date": ""})
        out[g] = sorted(rows, key=lambda r: r["rank"])
    return out if any(out.values()) else None


def _modern_on():
    return (os.environ.get("RESULT_STYLE") or "C").upper() == "C"


def _hero_photo(name, dry=False):
    """Foto boa (filtro de qualidade) para o destaque de uma lista; None se não houver."""
    import result_card as rc
    try:
        r = rc.find_post_photo({"name": name}, dry=dry)
        return r[0], r[1]
    except Exception:
        return None, None


def road_card_official(data, out):
    """Cartão novo (fotos boas e ranking oficial). As fotos só se passarem o filtro de qualidade."""
    import result_card as rc
    import photo_cards
    d = {}
    for g in ("men", "women"):
        xs = [dict(x) for x in (data.get(g) or [])[:4]]
        if xs:
            fp, cr = rc.find_post_photo({"name": xs[0]["name"]})
            if fp:
                xs[0].update(photo=fp, credit=cr)
        d[g] = xs
    if sum(len(v) for v in d.values()) < 4:
        return None
    if _modern_on():                                             # 9/11/2026: mesmo estilo dos cartões novos
        import modern_cards
        gap = lambda x: "" if x.get("gap") is None else ("level on points with No. 100" if x["gap"] <= 0 else f"{x['gap']} pts behind No. 100")
        secs = [{"label": g, "hero": {"name": xs[0]["name"], "big": f"No. {xs[0]['rank']}", "move": xs[0].get("move") or 0,
                                      "sub": gap(xs[0]), "photo": xs[0].get("photo")},
                 "rows": [(x["rank"], x["name"], ("level" if (x.get("gap") is not None and x["gap"] <= 0) else f"−{x['gap']} pts" if x.get("gap") is not None else ""))
                          for x in xs[1:4]]} for g, xs in (("Men", d.get("men") or []), ("Women", d.get("women") or [])) if xs]
        return modern_cards.card_list({"sport": "tennis", "kicker": "OFFICIAL RANKINGS", "date": datetime.date.today().strftime("%-d %b %Y").upper(),
                                       "title": "Road to the Top 100", "sub": "Points behind No. 100 this week", "sections": secs,
                                       "credits": [x[0].get("credit") for x in d.values() if x and x[0].get("credit")]}, out)
    return photo_cards.render_road(d, datetime.date.today().strftime("%-d %b %Y"), out)


def road_card(data, out):
    rows = []
    for g in ("men", "women"):
        xs = data.get(g, [])[:5]
        if xs:
            rows.append((None, G[g].upper(), None, False))
            for x in xs:
                mv = ""
                if isinstance(x.get("prev"), int) and x["prev"] != x["rank"]:
                    dlt = x["prev"] - x["rank"]
                    mv = f"{'+' if dlt > 0 else '-'}{abs(dlt)} places"
                right = (f"{int(x['gap'])} pts to go" if x.get("gap") else mv)
                rows.append((f"#{x['rank']}", x["name"], right, bool(mv.startswith("+"))))
    if len(rows) < 4:
        return None
    import tennis_bento
    if tennis_bento.on():
        try:
            return tennis_bento.road_card(data, out, datetime.date.today().strftime("%b %d").replace(" 0", " "))
        except Exception as e:
            print("road bento falhou, uso o clássico:", type(e).__name__, e)
    return _list_card("ROAD TO THE TOP 100", "Knocking on the door this week", rows, out, "Rankings as recorded in their latest matches.")


def power_card(data, out):
    rows = []
    for g in ("men", "women"):
        xs = data.get(g, [])[:5]
        if xs:
            rows.append((None, G[g].upper(), None, False))
            for i, e in enumerate(xs, 1):
                rows.append((str(i), f"{e['name']}", f"{e['w']}-{e['l']}" + (f" · {e['titles']} title" + ("s" if e['titles'] > 1 else "") if e["titles"] else ""), i == 1))
    if len(rows) < 4:
        return None
    if _modern_on():                                             # 9/11/2026: estilo novo
        import modern_cards
        secs, crs = [], []
        for g in ("men", "women"):
            xs = data.get(g, [])[:4]
            if not xs:
                continue
            fp, cr = _hero_photo(xs[0]["name"])
            crs.append(cr)
            rec = lambda e: f"{e['w']}-{e['l']}" + (f" · {e['titles']} title" + ("s" if e["titles"] > 1 else "") if e["titles"] else "")
            secs.append({"label": G[g], "hero": {"name": xs[0]["name"], "big": "No. 1", "sub": rec(xs[0]) + (f" · ranked #{xs[0]['rank']}" if xs[0].get("rank") else ""),
                                                 "photo": fp},
                         "rows": [(i, e["name"], rec(e)) for i, e in enumerate(xs[1:4], 2)]})
        return modern_cards.card_list({"sport": "tennis", "kicker": "POWER RANKING", "date": datetime.date.today().strftime("%-d %b %Y").upper(),
                                       "title": "Best form outside the top 100", "sub": "Last 14 days · wins, opponents and titles",
                                       "sections": secs, "credits": crs}, out)
    import tennis_bento
    if tennis_bento.on():
        try:
            return tennis_bento.power_card(data, out, datetime.date.today().strftime("%b %d").replace(" 0", " "))
        except Exception as e:
            print("power bento falhou, uso o clássico:", type(e).__name__, e)
    return _list_card("POWER RANKING", "Best form outside the top 100 · last 14 days", rows, out, "Our formula: wins, quality of opponents, titles.")


# ---------------------------------------------------------------- Climbers (ranking oficial ATP/WTA do ESPN, top 150)
def climbers(n=3):
    """{"atp": [...], "wta": [...], "upd": {...}}: as maiores subidas da semana no ranking oficial (top 150, ESPN)."""
    er = _load("espn_rank.json", {})
    out = {"upd": {lg: er.get(lg + "_upd") for lg in ("atp", "wta")}}
    for lg in ("atp", "wta"):
        rows = [x for x in er.get(lg) or [] if isinstance(x.get("prev"), int) and x["prev"] > x["r"]]
        out[lg] = sorted(rows, key=lambda x: (x["r"] - x["prev"], x["r"]))[:n]
    return out


def climbers_card(data, out):
    import feature_card
    rows = []
    for lg in ("atp", "wta"):
        if data.get(lg):
            rows.append({"section": lg.upper()})
            for x in data[lg]:
                age = f"{x['age']} years old · " if isinstance(x.get("age"), int) and x["age"] <= 21 else ""
                rows.append({"left": f"▲{x['prev'] - x['r']}", "name": x["n"], "sub": f"{age}#{x['prev']} → #{x['r']}", "right": f"#{x['r']}",
                             "hot": x["r"] <= 100 < x["prev"]})
    if len(rows) < 4:
        return None
    if _modern_on():                                             # 9/11/2026: estilo novo
        import modern_cards
        secs, crs = [], []
        for lg in ("atp", "wta"):
            xs = data.get(lg) or []
            if not xs:
                continue
            fp, cr = _hero_photo(xs[0]["n"])
            crs.append(cr)
            secs.append({"label": lg.upper(), "hero": {"name": xs[0]["n"], "big": f"No. {xs[0]['r']}", "move": xs[0]["prev"] - xs[0]["r"],
                                                       "sub": f"from No. {xs[0]['prev']}" + (" · into the top 100" if xs[0]["r"] <= 100 < xs[0]["prev"] else ""), "photo": fp},
                         "rows": [(f"▲{x['prev'] - x['r']}", x["n"], f"No. {x['prev']} → {x['r']}") for x in xs[1:4]]})
        return modern_cards.card_list({"sport": "tennis", "kicker": "OFFICIAL RANKINGS", "date": datetime.date.today().strftime("%-d %b %Y").upper(),
                                       "title": "Climbers of the week", "sub": "Biggest jumps in the ATP and WTA top 150",
                                       "sections": secs, "credits": crs}, out)
    top = [x["n"] for lg in ("atp", "wta") for x in (data.get(lg) or [])[:1]] + [x["n"] for lg in ("atp", "wta") for x in (data.get(lg) or [])[1:]]
    return feature_card.feature_card({"tags": ["CLIMBERS OF THE WEEK", "OFFICIAL RANKINGS"], "title": "Biggest jumps", "subtitle": "ATP and WTA · top 150",
                                      "place": None, "photos": _photos(top, 3), "rows": rows,
                                      "foot": "Highlighted: new to the top 100."}, out)


# ---------------------------------------------------------------- Qualifier watch (um post por torneio ATP/WTA)
def qualifier_watch(min_alive=2):
    """Torneios ATP/WTA (ESPN) em que pelo menos `min_alive` qualifiers já ganharam no quadro principal.
    -> [{"key", "tournament", "gender", "n_q", "rows": [(nome, ranking, vitórias, ainda_em_prova)]}]"""
    import espn_sync
    from espn import norm
    d = espn_sync.data()
    rk = espn_sync.rank_lookup()
    out = []
    for e in d.get("events", []):
        ms = [m for m in d.get("matches", []) if m["eid"] == e["eid"]]
        for g in ("men", "women"):
            q = {norm(p["n"]): p["n"] for m in ms if m["g"] == g and m["q"] and m["w"] in (1, 2) and m["rr"].lower().startswith("qualifying final")
                 for i, p in enumerate(m["p"]) if m["w"] == i + 1}
            if not q:
                continue
            main = [m for m in ms if m["g"] == g and not m["q"]]
            wins, lost = {}, set()
            for m in main:
                for i, p in enumerate(m["p"]):
                    k = norm(p["n"])
                    if k in q and m["w"] in (1, 2):
                        if m["w"] == i + 1:
                            wins[k] = wins.get(k, 0) + 1
                        else:
                            lost.add(k)
            rows = sorted([(q[k], rk(q[k], e["lg"]), w, k not in lost) for k, w in wins.items()], key=lambda r: (-r[2], -r[3], r[1] or 9999))
            if len(rows) >= min_alive:
                out.append({"key": f"{e['eid']}-{g}", "tournament": e.get("name") or e.get("tp"), "tp": e.get("tp"), "gender": g, "lg": e["lg"],
                            "city": e.get("city"),
                            "n_q": len(q), "rows": rows})
    return out


def _photos(names, n=3):
    """Fotos licenciadas (rotação da galeria, para não repetir) dos primeiros nomes que as tiverem: [{path, credit, label}]."""
    import result_card as rc
    out = []
    for nm in names:
        try:
            fp, cr = rc.find_post_photo({"name": nm})
        except Exception:
            fp, cr = rc.find_photo({"name": nm})
        if fp:
            out.append({"path": fp, "credit": cr, "label": nm})
        if len(out) >= n:
            break
    return out


def _place(city):
    try:
        from padel.posts import place_photo
        return place_photo(city)
    except Exception as e:
        print("Foto da cidade:", type(e).__name__, e)
        return None


def qualifier_week():
    """Todos os qualifiers (ATP e WTA, homens e mulheres) que ganharam no quadro principal esta semana, os melhores primeiro."""
    rows = []
    for x in qualifier_watch(min_alive=1):
        for name, rank, w, alive in x["rows"]:
            rows.append({"name": name, "rank": rank, "wins": w, "alive": alive, "tournament": x["tournament"], "city": x.get("city"),
                         "lg": x["lg"], "gender": x["gender"]})
    rows.sort(key=lambda r: (-r["wins"], not r["alive"], r["rank"] or 9999))
    return rows


def qualifier_card(rows, out):
    import feature_card
    top = rows[:6]
    lines = [{"left": "Q", "name": r["name"], "sub": f'{r["tournament"]}' + (f' · #{r["rank"]}' if r["rank"] else ""),
              "right": f'{r["wins"]} win{"s" if r["wins"] > 1 else ""}' + ("" if r["alive"] else " · out"), "hot": r["alive"]} for r in top]
    tours = sorted({r["lg"].upper() for r in top})
    men = [r["name"] for r in top if r["gender"] == "men"][:1]
    women = [r["name"] for r in top if r["gender"] == "women"][:1]
    return feature_card.feature_card({"tags": ["QUALIFIER WATCH", " · ".join(tours)], "title": "Through qualifying",
                                      "subtitle": "and still winning this week", "place": _place(top[0].get("city")),
                                      "photos": _photos(men + women + [r["name"] for r in top], 2), "rows": lines,
                                      "foot": "Main-draw wins after coming through qualifying. Highlighted: still in."}, out)


def qualifier_posts(out_dir="out", force=False):
    """UM post por semana (quinta-feira, QUALWATCH_DAY/HOUR), com homens e mulheres de todos os torneios ATP/WTA juntos.
    Só sai com pelo menos 4 qualifiers e um deles com 2+ vitórias no quadro principal (senão não é história)."""
    import captions
    import result_card as rc
    if os.environ.get("QUALWATCH_ENABLED", "1").strip() in ("0", "no", "off", "false"):
        return []
    now = datetime.datetime.now(datetime.timezone.utc)
    day, hour = int(os.environ.get("QUALWATCH_DAY") or "3"), int(os.environ.get("QUALWATCH_HOUR") or "17")
    if not force and not (now.weekday() == day and now.hour >= hour):
        print("qualifier watch: ainda não é a hora.")
        return []
    pid = f"news-qual-{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    posts = rc._load_json(rc.POSTS_FILE, {})
    if not force and any(str(e.get("id")) == pid or str(e.get("id")).startswith("news-qual-") and k >= (now.date() - datetime.timedelta(days=now.weekday())).isoformat()
                         for k, v in posts.items() for e in v):
        print("qualifier watch: já saiu esta semana.")
        return []
    rows = qualifier_week()
    if len(rows) < 4 or max(r["wins"] for r in rows) < 2:
        print(f"qualifier watch: pouca história esta semana ({len(rows)} qualifiers).")
        return []
    os.makedirs(os.path.join(out_dir, "post"), exist_ok=True)
    png = os.path.join(out_dir, "post", pid + ".png")
    if not qualifier_card(rows, png):
        return []
    facts = {"week": pid[-8:], "players": [{"name": r["name"], "ranking": r["rank"], "tournament": r["tournament"], "main_draw_wins": r["wins"],
                                             "still_in": r["alive"], "tour": r["lg"].upper()} for r in rows[:6]]}
    captions.save_caption(png, "qualwatch", facts)
    posts.setdefault(time.strftime("%Y-%m-%d", time.gmtime()), []).append({"id": pid, "score": 0, "reasons": ["qualwatch"], "file": pid + ".png"})
    with open(rc.POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print("qualifier watch:", png)
    return [png]


def weekly_post(kind, out_dir="out", force=False):
    """Põe o cartão semanal na fila de posts (id news-<kind>-<semana>, fora do limite diário)."""
    import captions
    import result_card as rc
    if os.environ.get(f"{kind.upper()}_ENABLED", "1").strip() in ("0", "no", "off", "false"):
        print(f"{kind}: desligado.")
        return None
    day = int(os.environ.get(f"{kind.upper()}_DAY") or {"road": "0", "power": "1", "climbers": "0"}[kind])
    hour = int(os.environ.get(f"{kind.upper()}_HOUR") or {"road": "12", "power": "18", "climbers": "19"}[kind])
    now = datetime.datetime.now(datetime.timezone.utc)
    if not force and not (now.weekday() == day and now.hour >= hour):
        print(f"{kind}: ainda não é a hora.")
        return None
    pid = f"news-{kind}-{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    posts = rc._load_json(rc.POSTS_FILE, {})
    if not force and any(str(e.get("id")) == pid for v in posts.values() for e in v):
        print(f"{kind}: já saiu esta semana.")
        return None
    results = [r for r in rc._heal(rc.prune(rc.load_results())) if r.get("src") != "espn" or os.environ.get("POSTS_USE_ESPN", "1") == "1"]   # posts: sem os jogos só do ESPN
    os.makedirs(os.path.join(out_dir, "post"), exist_ok=True)
    png = os.path.join(out_dir, "post", pid + ".png")
    if kind == "road":
        data = road_official()
        if data:
            made = road_card_official(data, png)
        else:                                                   # sem ranking oficial recente: não publica (o antigo saía desatualizado)
            print("road: sem ranking oficial desta semana, não sai.")
            return None
        facts = {g: [{"name": x["name"], "ranking": x["rank"], "previous_ranking": x.get("prev"), "points_to_top100": x.get("gap")}
                     for x in data[g][:5]] for g in data}
    elif kind == "climbers":
        data = climbers()
        fresh = any((data["upd"].get(lg) or "") >= (now.date() - datetime.timedelta(days=8)).isoformat() for lg in ("atp", "wta"))
        made = climbers_card(data, png) if fresh else None       # ranking antigo (o ESPN não atualizou): não repete a semana anterior
        facts = {lg: [{"name": x["n"], "ranking": x["r"], "previous_ranking": x["prev"], "places_gained": x["prev"] - x["r"], "age": x.get("age")}
                      for x in data.get(lg) or []] for lg in ("atp", "wta")}
    else:
        latest = {webapp.slugify(v.get("name", "")): v.get("rank") for v in _load("ranks.json", {}).values()}
        data = power(results, latest)
        made = power_card(data, png)
        facts = {g: [{"position": i, "name": e["name"], "ranking": e["rank"], "won": e["w"], "lost": e["l"], "titles": e["titles"]}
                     for i, e in enumerate(data[g][:5], 1)] for g in data}
    if not made:
        print(f"{kind}: dados insuficientes esta semana.")
        return None
    captions.save_caption(png, kind, facts)
    today = time.strftime("%Y-%m-%d", time.gmtime())
    posts.setdefault(today, []).append({"id": pid, "score": 0, "reasons": [kind], "file": pid + ".png"})
    with open(rc.POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"{kind}: {png}")
    return png


# ---------------------------------------------------------------- post mensal: "The month in records"
SHORT = {"wins": "MOST WINS", "titles": "MOST TITLES", "comebacks": "COMEBACK WINS", "tb": "TIE-BREAKS WON", "bagels": "6-0 SETS",
         "upset": "BIGGEST UPSET"}


# Tema de cada mês (cor do topo, cor de destaque, desenho e frase): o calendário do ténis ao longo do ano
MONTHS = {
    1: ((58, 160, 224), (255, 214, 92), "sun", "Aussie summer"),
    2: ((74, 52, 120), (190, 170, 255), "ball", "Indoor season"),
    3: ((24, 140, 130), (255, 196, 92), "sun", "Sunshine swing"),
    4: ((196, 98, 58), (255, 214, 170), "clay", "Clay season begins"),
    5: ((178, 84, 48), (255, 206, 160), "clay", "Clay season"),
    6: ((86, 150, 58), (226, 244, 170), "grass", "Grass season"),
    7: ((64, 128, 48), (226, 244, 170), "grass", "Grass season"),
    8: ((44, 104, 180), (140, 210, 255), "sun", "Hard-court summer"),
    9: ((190, 120, 40), (255, 222, 150), "leaf", "Autumn swing"),
    10: ((176, 84, 34), (255, 196, 120), "leaf", "Autumn on tour"),
    11: ((30, 50, 96), (150, 180, 255), "ball", "Indoor finale"),
    12: ((90, 140, 180), (226, 242, 255), "snow", "Off-season"),
}


def _motif(d, kind, cx, cy, r, col):
    """Desenho simples (só formas) que identifica o mês."""
    import math
    if kind == "sun":
        d.ellipse([cx - r * 0.5, cy - r * 0.5, cx + r * 0.5, cy + r * 0.5], fill=col)
        for i in range(12):
            a = i * math.pi / 6
            d.line([(cx + math.cos(a) * r * 0.65, cy + math.sin(a) * r * 0.65), (cx + math.cos(a) * r, cy + math.sin(a) * r)], fill=col, width=6)
    elif kind == "ball":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=7)
        d.arc([cx - r * 1.6, cy - r, cx - r * 0.2, cy + r], -60, 60, fill=col, width=6)
        d.arc([cx + r * 0.2, cy - r, cx + r * 1.6, cy + r], 120, 240, fill=col, width=6)
    elif kind == "clay":
        d.rectangle([cx - r, cy - r * 0.7, cx + r, cy + r * 0.7], outline=col, width=6)
        d.line([(cx, cy - r * 0.7), (cx, cy + r * 0.7)], fill=col, width=6)
        d.line([(cx - r * 0.55, cy - r * 0.35), (cx + r * 0.55, cy - r * 0.35)], fill=col, width=4)
        d.line([(cx - r * 0.55, cy + r * 0.35), (cx + r * 0.55, cy + r * 0.35)], fill=col, width=4)
    elif kind == "grass":
        for i in range(7):
            x = cx - r + i * r / 3
            h = r * (0.9 + 0.5 * ((i * 37) % 5) / 5)
            d.polygon([(x - 8, cy + r * 0.7), (x + 8, cy + r * 0.7), (x + 14 * (1 if i % 2 else -1), cy + r * 0.7 - h)], fill=col)
    elif kind == "leaf":
        d.ellipse([cx - r * 0.55, cy - r, cx + r * 0.55, cy + r * 0.8], fill=col)
        d.line([(cx, cy - r * 0.8), (cx, cy + r)], fill=(0, 0, 0, 0) if False else (120, 60, 20), width=5)
        for k in (-0.4, 0, 0.4):
            d.line([(cx, cy + r * k), (cx - r * 0.35, cy + r * k - r * 0.25)], fill=(120, 60, 20), width=3)
            d.line([(cx, cy + r * k), (cx + r * 0.35, cy + r * k - r * 0.25)], fill=(120, 60, 20), width=3)
    elif kind == "snow":
        for i in range(3):
            a = i * math.pi / 3
            dx, dy = math.cos(a) * r, math.sin(a) * r
            d.line([(cx - dx, cy - dy), (cx + dx, cy + dy)], fill=col, width=6)
        d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=col)


def records_card(data, month_label, out, month=None):
    """Grelha 2x3 de "fichas": cada categoria com o número em grande e o líder de homens e de mulheres."""
    rec, cats, _ = data
    import tennis_bento
    if tennis_bento.on():
        try:
            return tennis_bento.records_card((rec, cats, SHORT), month_label, out, MONTHS.get(month or 0, (None,))[0])
        except Exception as e:
            print("records bento falhou, uso o clássico:", type(e).__name__, e)
    img = pc._gradient((12, 52, 40), (6, 28, 21))
    d = ImageDraw.Draw(img)
    bg, accent, motif, tag = MONTHS.get(month or 0, (pc.VOLT, pc.VOLT, None, ""))
    light = sum(bg) / 3 > 150
    fg = pc.GREEN if light else pc.CREAM
    # cabeçalho com a cor e o desenho do mês
    d.rectangle([0, 0, pc.W, 230], fill=bg)
    if motif:
        _motif(d, motif, 120, 115, 62, accent)
        _motif(d, motif, pc.W - 120, 115, 62, accent)
    d.text((pc.W / 2, 62), "THE MONTH IN RECORDS", font=pc.font(pc.SANS_B, 36), fill=fg, anchor="mm")
    d.text((pc.W / 2, 140), month_label.upper(), font=pc.fit(d, month_label.upper(), pc.SERIF_B, 92, 640 if motif else 960, 44), fill=fg, anchor="mm")
    d.text((pc.W / 2, 205), (tag.upper() + " · " if tag else "") + "BEYOND THE TOP 100", font=pc.font(pc.SANS_B, 22), fill=accent if not light else pc.DEEP, anchor="mm")
    tile_col = accent if motif else pc.VOLT
    x0, y0, tw, th, gap = 50, 270, 480, 300, 20
    filled = 0
    for i, (key, _label) in enumerate(cats):
        col, row = i % 2, i // 2
        x, y = x0 + col * (tw + gap), y0 + row * (th + gap)
        d.rounded_rectangle([x, y, x + tw, y + th], radius=26, fill=pc.DEEP, outline=pc.EDGE, width=2)
        d.text((x + 28, y + 36), SHORT[key], font=pc.font(pc.SANS_B, 24), fill=tile_col, anchor="lm")
        yy = y + 90
        for g in ("men", "women"):
            top = (rec.get(g, {}).get(key) or [None])[0]
            if not top:
                continue
            filled += 1
            d.text((x + 28, yy + 34), str(top[key]), font=pc.font(pc.SERIF_B, 72), fill=pc.CREAM, anchor="lm")
            nx = x + 28 + d.textlength(str(top[key]), font=pc.font(pc.SERIF_B, 72)) + 22
            d.text((nx, yy + 16), "M" if g == "men" else "W", font=pc.font(pc.SANS_B, 20), fill=pc.SOFT, anchor="lm")
            d.text((nx, yy + 48), top["name"], font=pc.fit(d, top["name"], pc.SERIF_B, 34, x + tw - nx - 24, 18), fill=pc.CREAM, anchor="lm")
            yy += 100
    if filled < 4:
        return None
    d.text((pc.W / 2, 1255), "From the matches we tracked · main draws · singles", font=pc.font(pc.SERIF_I, 30), fill=pc.SOFT, anchor="mm")
    d.text((pc.W / 2, 1306), pc.BRAND, font=pc.font(pc.SANS_B, 30), fill=pc.CREAM, anchor="mm")
    img.save(out, quality=95)
    return out


def monthly_records_post(out_dir="out", force=False):
    import captions
    import result_card as rc
    if os.environ.get("RECORDS_ENABLED", "1").strip() in ("0", "no", "off", "false"):
        print("records: desligado.")
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    hour = int(os.environ.get("RECORDS_HOUR") or "12")
    if not force and not (now.day == 1 and now.hour >= hour):
        print("records: só no dia 1 de cada mês.")
        return None
    last = (now.date().replace(day=1) - datetime.timedelta(days=1))
    pref = last.strftime("%Y-%m")
    pid = f"news-records-{pref}"
    posts = rc._load_json(rc.POSTS_FILE, {})
    if not force and any(str(e.get("id")) == pid for v in posts.values() for e in v):
        print("records: já saiu este mês.")
        return None
    results = [r for r in rc._heal(rc.prune(rc.load_results())) if r.get("src") != "espn" or os.environ.get("POSTS_USE_ESPN", "1") == "1"]
    data = records(results, last.year, pref)
    os.makedirs(os.path.join(out_dir, "post"), exist_ok=True)
    png = os.path.join(out_dir, "post", pid + ".png")
    if not records_card(data, last.strftime("%B %Y"), png, last.month):
        print("records: dados insuficientes.")
        return None
    rec, cats, _ = data
    facts = {"month": last.strftime("%B %Y"),
             "leaders": {g: {SHORT[k].lower(): {"name": rec[g][k][0]["name"], "value": rec[g][k][0][k]} for k, _ in cats if rec[g].get(k)}
                         for g in ("men", "women")}}
    captions.save_caption(png, "records", facts)
    today = time.strftime("%Y-%m-%d", time.gmtime())
    posts.setdefault(today, []).append({"id": pid, "score": 0, "reasons": ["records"], "file": pid + ".png"})
    with open(rc.POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print("records:", png)
    return png


if __name__ == "__main__":
    _out = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "out"
    for k in ("road", "power", "climbers"):
        try:
            weekly_post(k, _out, "--force" in sys.argv)
        except Exception as e:
            print(k, "falhou:", type(e).__name__, e)
    try:
        qualifier_posts(_out)
    except Exception as e:
        print("qualifier watch falhou:", type(e).__name__, e)
    try:
        monthly_records_post(_out, "--force" in sys.argv)
    except Exception as e:
        print("records falhou:", type(e).__name__, e)
