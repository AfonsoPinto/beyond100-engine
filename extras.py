"""Extras do site: estatísticas acumuladas, páginas de jogador, "a decorrer agora", destaques e newsletter.

Estatísticas acumuladas (stats.json) guardam só CONTADORES agregados (por superfície, país, nível, jogador),
nunca os jogos em bruto: dá para analisar o histórico sem manter um conjunto de dados da API.
"""
import datetime as dt
import html
import json
import os
import re
import time

import i18n_site
import webapp
import site_ui

STATS_FILE = "stats.json"
LIVE_FILE = "live.json"
LIVE_MAX_AGE_H = 3
esc = html.escape


def L(tx, key, **kw):
    """Texto traduzido (tx) com valor por defeito em inglês."""
    return ((tx or {}).get(key) or i18n_site.EN[key]).format(**kw)


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


# ---------- estatísticas acumuladas ----------
def _bump(d, key, **inc):
    row = d.setdefault(key, {})
    for k, v in inc.items():
        row[k] = row.get(k, 0) + v
    return row


def update_stats(r):
    """Chamado uma vez por jogo terminado (singulares). Só soma contadores."""
    if r.get("winner") not in (1, 2) or webapp.classify(r)[1] != "singles" or r.get("q"):
        return
    st = webapp.match_stats(r)
    if not st:
        return
    data = _load(STATS_FILE, {})
    counted = set(data.get("ids", []))
    if str(r.get("id")) in counted:
        return
    counted.add(str(r.get("id")))
    badges, _, tbs, _, _ = st
    gender, _, level, _ = webapp.classify(r)
    surf = (r.get("surface") or "unknown").lower()
    sets = len(r["games"][0])
    w, l = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
    data.setdefault("since", time.strftime("%Y-%m-%d", time.gmtime()))
    data["matches"] = data.get("matches", 0) + 1
    _bump(data.setdefault("surface", {}), surf, n=1, three=1 if sets >= 3 else 0, tb=1 if tbs else 0,
          bagel=1 if "bagel" in badges else 0, comeback=1 if "comeback" in badges else 0)
    _bump(data.setdefault("level", {}), level or "other", n=1, three=1 if sets >= 3 else 0)
    cw = (w.get("country") or "").upper()
    if cw:
        _bump(data.setdefault("country_w", {}), cw, w=1)
    cl = (l.get("country") or "").upper()
    if cl:
        _bump(data.setdefault("country_w", {}), cl, l=1)
    for p, won in ((w, True), (l, False)):
        row = _bump(data.setdefault("players", {}), webapp.slugify(p["name"]), w=1 if won else 0, l=0 if won else 1)
        row["name"], row["c"] = p["name"], (p.get("country") or "").upper()
    wk = dt.date.fromisoformat(r.get("date") or time.strftime("%Y-%m-%d", time.gmtime())).isocalendar()
    _bump(data.setdefault("weeks", {}), f"{wk[0]}-W{wk[1]:02d}", n=1)
    data["ids"] = sorted(counted)[-20000:]
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def stats_page(tx, tr=None):
    d = _load(STATS_FILE, {})
    if d.get("matches", 0) < 5:
        return f'<section class="page-h"><h1>{esc(L(tx, "x_stats"))}</h1><p class="empty">{esc(L(tx, "x_stats_empty"))}</p></section>'
    names = dict({"hard": "Hard", "clay": "Clay", "grass": "Grass", "carpet": "Carpet", "unknown": "Other"}, **((tr or {}).get("surfaces") or {}))

    def pct(a, b):
        return f"{round(100 * a / b)}%" if b else "–"
    rows = "".join(
        f'<tr><td class="pn">{esc(names.get(k, k.title()))}</td><td>{v["n"]}</td><td>{pct(v.get("three", 0), v["n"])}</td>'
        f'<td>{pct(v.get("tb", 0), v["n"])}</td><td>{pct(v.get("comeback", 0), v["n"])}</td></tr>'
        for k, v in sorted(d.get("surface", {}).items(), key=lambda kv: -kv[1]["n"]))
    lv = {"tour": "Tour", "challenger": "Challenger", "itf": "ITF"}
    lrows = "".join(
        f'<tr><td class="pn">{esc(lv.get(k, k.title()))}</td><td>{v["n"]}</td><td>{pct(v.get("three", 0), v["n"])}</td></tr>'
        for k, v in sorted(d.get("level", {}).items(), key=lambda kv: -kv[1]["n"]))
    ctry = sorted(d.get("country_w", {}).items(), key=lambda kv: (-kv[1].get("w", 0), kv[0]))[:12]
    crow = "".join(
        f'<tr><td class="pn">{esc(c)}</td><td>{v.get("w", 0)}</td><td>{v.get("l", 0)}</td>'
        f'<td>{pct(v.get("w", 0), v.get("w", 0) + v.get("l", 0))}</td></tr>' for c, v in ctry)
    tiles = [(d["matches"], L(tx, "x_t_matches")),
             (len(d.get("players", {})), L(tx, "x_t_players")),
             (sum(v.get("tb", 0) for v in d.get("surface", {}).values()), L(tx, "x_t_tb")),
             (sum(v.get("comeback", 0) for v in d.get("surface", {}).values()), L(tx, "x_t_comebacks"))]
    th = "".join(f'<div class="nbox"><b>{v}</b><span>{esc(l)}</span></div>' for v, l in tiles)
    return (f'<section class="page-h"><h1>{esc(L(tx, "x_stats"))}</h1><p>{esc(L(tx, "x_stats_lead", d=d.get("since", "")))}</p></section>'
            f'<div class="numgrid">{th}</div>'
            f'<h2 class="dh">{esc(L(tx, "x_by_surface"))}</h2><table class="pt"><thead><tr><th>{esc(L(tx, "x_surface"))}</th>'
            f'<th>{esc(L(tx, "x_matches"))}</th><th>{esc(L(tx, "x_3sets"))}</th><th>{esc(L(tx, "x_tb"))}</th>'
            f'<th>{esc(L(tx, "x_comeback"))}</th></tr></thead><tbody>{rows}</tbody></table>'
            f'<h2 class="dh">{esc(L(tx, "x_by_level"))}</h2><table class="pt"><thead><tr><th>{esc(L(tx, "x_level"))}</th>'
            f'<th>{esc(L(tx, "x_matches"))}</th><th>{esc(L(tx, "x_3sets"))}</th></tr></thead><tbody>{lrows}</tbody></table>'
            f'<h2 class="dh">{esc(L(tx, "x_countries"))}</h2><table class="pt"><thead><tr><th>{esc(L(tx, "x_country"))}</th>'
            f'<th>{esc(L(tx, "x_w"))}</th><th>{esc(L(tx, "x_l"))}</th><th>{esc(L(tx, "x_winrate"))}</th></tr></thead>'
            f'<tbody>{crow}</tbody></table>')


FULL_RANKINGS_FILE = "rankings_full.json"


def have_full_rankings():
    """Há página de Rankings quando há o ranking oficial (top 150 ATP/WTA, do ESPN) ou o ficheiro rankings_full.json."""
    er = _load("espn_rank.json", {})
    return bool(er.get("atp") or er.get("wta") or _load(FULL_RANKINGS_FILE, {}).get("players"))


def rankings_page(tx, ranks, linkable=(), results=()):
    """Top 150 oficial ATP/WTA (ESPN: pontos, posição anterior) + para lá do 150, o último ranking visto nos nossos jogos."""
    import site_more
    er = _load("espn_rank.json", {})
    sex = {}
    for r in results or []:
        for k in ("p1", "p2"):
            if " / " not in r[k]["name"] and r.get("gender") in ("men", "women"):
                sex.setdefault(webapp.slugify(r[k]["name"]), r["gender"])
    def nm(n):
        sl = webapp.slugify(n)
        return f'<a href="/p/{sl}.html">{esc(n)}</a>' if sl in linkable else f'<span class="nm">{esc(n)}</span>'
    def av(n):
        return webapp.avatar(n) or f'<span class="ini"></span>'
    def cn(c):
        return f'{site_more.flag(c, 11)}{esc(site_more.country_name((c or "").upper()))}' if c else ""
    tabs, panes = "", ""
    for i, (lg, label, g) in enumerate((("atp", "ATP", "men"), ("wta", "WTA", "women"))):
        top = er.get(lg) or []
        have = {webapp.slugify(x["n"]) for x in top}
        climb = sorted([x for x in top if isinstance(x.get("prev"), int) and x["prev"] > x["r"]], key=lambda x: (x["r"] - x["prev"], x["r"]))[:6]
        cards = "".join(site_ui.champ_card(f'/p/{webapp.slugify(x["n"])}.html' if webapp.slugify(x["n"]) in linkable else "#", f'▲ {x["prev"] - x["r"]}',
                                           f'#{x["prev"]} → #{x["r"]}', label + " ranking", esc(x["n"]), f'{x["pts"]:,} points', av(x["n"])) for x in climb)
        rows = "".join(site_ui.rank_row(x["r"], av(x["n"]), nm(x["n"]), cn(x.get("c")), f'{x["pts"]:,}',
                                        (x["prev"] - x["r"]) if isinstance(x.get("prev"), int) else None) for x in top)
        beyond = sorted([v for v in (ranks or {}).values() if isinstance(v.get("rank"), int) and v["rank"] > (len(top) or 0) and v.get("name")
                         and sex.get(webapp.slugify(v["name"])) == g and webapp.slugify(v["name"]) not in have], key=lambda v: v["rank"])[:400]
        brow = "".join(site_ui.rank_row(v["rank"], av(v["name"]), nm(v["name"]), cn(v.get("country")) + (f' · seen {esc(v["date"][8:10])}/{esc(v["date"][5:7])}' if v.get("date") else ""),
                                        f'{v["pts"]:,}' if isinstance(v.get("pts"), int) else "", v.get("mv")) for v in beyond)
        upd = er.get(lg + "_upd") or ""
        tabs += f'<button class="{"on" if i == 0 else ""}" data-p="{lg}">{label}</button>'
        panes += (f'<div class="rkp" id="rk-{lg}"{"" if i == 0 else " hidden"}>'
                  + (f'{site_ui.sec("Climbers this week")}<div class="ui-row">{cards}</div>' if cards else "")
                  + (f'{site_ui.sec(f"Top {len(top)}")}<p class="mut2">Official {label} ranking{(" of " + esc(upd[8:10] + "/" + upd[5:7])) if upd else ""}, with the move since the week before.</p>'
                     f'<div class="ui-rk rkl">{rows}</div>' if top else "")
                  + (f'{site_ui.sec(f"Beyond {len(top) or 100}")}<p class="mut2">The latest ranking we have seen for each player in the matches we follow '
                     f'(Challenger, ITF and tour), and when.</p><div class="ui-rk rkl">{brow}</div>' if brow else "")
                  + '</div>')
    if not tabs:
        return f'<section class="page-h"><h1>{esc(L(tx, "x_rankings"))}</h1><p class="empty">{esc(L(tx, "x_stats_empty"))}</p></section>'
    return (f'<section class="page-h"><h1>{esc(L(tx, "x_rankings"))}</h1><p>The official ATP and WTA top 150, and beyond it, every ranking we have seen in our matches. '
            f'<a href="/players.html">Players in form →</a></p><div class="ui-seg rkt">{tabs}</div><input id="q" class="srch" placeholder="{esc(L(tx, "search"))}"></section>{panes}'
            '<script>(()=>{const q=document.getElementById("q"),N=40;'
            'function cut(){document.querySelectorAll(".rkl").forEach(l=>{const rs=[...l.children].filter(r=>r.classList.contains("r"));const v=q.value.trim().toLowerCase();let n=0;'
            'rs.forEach(r=>{const m=!v||r.textContent.toLowerCase().includes(v);r.hidden=!m||(!v&&!l.open&&n>=N);if(m)n++});'
            'let b=l.querySelector(".more");if(!b){b=document.createElement("button");b.className="more";b.textContent="Show all";b.onclick=()=>{l.open=true;cut()};l.appendChild(b)}'
            'b.hidden=!!v||l.open||rs.length<=N})}'
            'document.querySelectorAll(".rkt button").forEach(b=>b.onclick=()=>{document.querySelectorAll(".rkt button").forEach(x=>x.classList.toggle("on",x===b));'
            'document.querySelectorAll(".rkp").forEach(p=>p.hidden=p.id!=="rk-"+b.dataset.p)});q.addEventListener("input",cut);cut()})()</script>')


def match_title(r):
    w = r["winner"]
    a, b = r["p%d" % w]["name"], r["p%d" % (3 - w)]["name"]
    sc = " ".join(f"{x}-{y}" for x, y in zip(r["games"][w - 1], r["games"][2 - w]))
    return f'{a} beat {b} {sc} · {webapp.base_tournament(r.get("tournament", ""))} · Beyond100'


def _nl_inline(title):
    try:
        import nl_cta
        return nl_cta.inline(title)
    except Exception:
        return ""


def match_page(r, results, tr, tx):
    tr = dict(tr, _tx=tx)
    w = r["winner"]
    tname = webapp.base_tournament(r.get("tournament", ""))
    rd = tr["rounds"].get((r.get("round") or "").lower(), r.get("round") or "")
    surf = tr["surfaces"].get(r.get("surface"), "")
    meta = " · ".join(x for x in [r.get("date", ""), rd, surf] if x)
    gender, _, level, tag = webapp.classify(r)
    head = (f'<section class="page-h"><p><a href="/t/{webapp.slugify(tname)}.html">← {esc(tname)}</a></p>'
            f'<h1>{(f"<span class=tag>{esc(tag)}</span> ") if tag else ""}{esc(r["p%d" % w]["name"])} <span style="color:var(--s);font-weight:400">d.</span> '
            f'{esc(r["p%d" % (3 - w)]["name"])}</h1><p>{esc(meta)}</p></section>')
    nsets = len(r["games"][0])
    rows = ""
    for i in (1, 2):
        p = r["p%d" % i]
        cells = "".join(f'<td class="{"wn" if r["games"][i - 1][k] > r["games"][2 - i][k] else ""}">{r["games"][i - 1][k]}{webapp.tbsup(r, i - 1, k)}</td>'
                        for k in range(nsets))
        rows += (f'<tr class="{"win" if w == i else ""}"><td class="pn">{webapp.avatar(p["name"], "av")}'
                 f'<a class="nm" href="/p/{webapp.slugify(p["name"])}.html">{esc(p["name"])}</a> '
                 f'<small>{who_html(p)}</small></td>{cells}</tr>')
    import site_ui
    board = site_ui.scoreboard([{"name": f'<a href="/p/{webapp.slugify(r["p%d" % i]["name"])}.html">{esc(r["p%d" % i]["name"])}</a>',
                                  "sub": who_html(r["p%d" % i]), "av": webapp.avatar(r["p%d" % i]["name"], "av"), "won": w == i} for i in (1, 2)],
                               r["games"], r.get("tb"))
    board += match_stats_html(r["p1"], r["p2"], r["games"][0], r["games"][1], r.get("tb"), results, skip_id=r.get("id"))
    st = webapp.match_stats(r)
    facts = ""
    if st:
        badges, pct, tbs, total, margin = st
        gw, gl = sum(r["games"][w - 1]), sum(r["games"][2 - w])
        sets_w = sum(a > b for a, b in zip(r["games"][w - 1], r["games"][2 - w]))
        items = [("Sets", f"{sets_w}-{nsets - sets_w}"), ("Games", f"{gw}-{gl}"),
                 ("Tie-breaks", str(tbs)), ("Total games", str(total))]
        names = {"comeback": "Comeback (lost the first set)", "bagel": "Bagel set (6-0)", "breadstick": "Breadstick set (6-1)",
                 "super": "Match tie-break"}
        extra = [names[b] for b in badges if b in names]
        facts = ('<div class="bd" style="margin-top:10px">' + "".join(f"<i>{esc(e)}</i>" for e in extra) + "</div>") if extra else ""
    sa, sb = webapp.slugify(r["p1"]["name"]), webapp.slugify(r["p2"]["name"])
    h2h = [x for x in results if x.get("id") != r.get("id") and x.get("winner") in (1, 2)
           and {webapp.slugify(x["p1"]["name"]), webapp.slugify(x["p2"]["name"])} == {sa, sb}]
    hh = ""
    if h2h:
        hh = ('<h2 class="dh">Other meetings we tracked</h2><section class="tg">' +
              "".join(webapp.match_html(x, tr) for x in sorted(h2h, key=lambda x: x.get("date", ""), reverse=True)[:5]) + "</section>")
    try:
        import tennis_videos
        vid = tennis_videos.highlight_block(r)
    except Exception as e:
        print("Highlights do jogo falharam:", r.get("id"), e)
        vid = ""
    i = board.find('<h2 class="ui-sec"')
    board = board[:i] + facts + board[i:] if i > 0 else board + facts
    return head + vid + board + _nl_inline("Enjoyed this match? Get the week's best in one email") + hh


# ---------- página de jogador ----------
def players_index(results):
    """nome -> {slug, country, rank, matches[]} (só singulares terminados)."""
    out = {}
    for r in results:
        if webapp.classify(r)[1] != "singles" or r.get("winner") not in (1, 2):
            continue
        for i in (1, 2):
            p = r["p%d" % i]
            e = out.setdefault(webapp.slugify(p["name"]), {"name": p["name"], "country": (p.get("country") or "").upper(),
                                                          "rank": None, "rank_date": "", "matches": []})
            e["matches"].append((i, r))
            if isinstance(p.get("rank"), int) and r.get("date", "") >= e["rank_date"]:
                e["rank"], e["rank_date"] = p["rank"], r.get("date", "")
    return out


def hist_entry(name):
    global _HIST
    if _HIST is None:
        _HIST = _load("history.json", {}) if os.environ.get("HISTORY") != "0" else {}
    return (_HIST.get("p") or {}).get(webapp.slugify(name or ""))


def bio_line(name):
    """Idade, mão e altura (dados públicos do Tennis Abstract), ex.: 'Age 27 · Right-handed · 1.85 m'."""
    b = (hist_entry(name) or {}).get("bio") or {}
    bits = []
    dob = str(b.get("dob") or "")
    if len(dob) >= 8 and dob[:8].isdigit():
        t = time.gmtime()
        age = t.tm_year - int(dob[:4]) - ((t.tm_mon, t.tm_mday) < (int(dob[4:6]), int(dob[6:8])))
        if 14 <= age <= 50:
            bits.append(f"Age {age}")
    try:                                           # o que faltar vem do perfil do ESPN (ATP/WTA)
        import espn_sync
        ep = espn_sync.profile_for(name)
    except Exception:
        ep = {}
    if not bits and ep:
        age = _age(ep.get("bd")) if ep.get("bd") else (ep["age"] + int((time.time() - ep.get("age_ts", time.time())) // (365.25 * 86400))
                                                     if isinstance(ep.get("age"), int) else None)
        if age and 14 <= age <= 50:
            bits.append(f"Age {age}")
    hand = {"R": "Right-handed", "L": "Left-handed"}.get(b.get("hand") or ep.get("hand"))
    if hand:
        bits.append(hand)
    h = b.get("h") if isinstance(b.get("h"), int) else ep.get("h")
    if isinstance(h, int) and 150 <= h <= 215:
        bits.append(f"{h / 100:.2f} m")
    if isinstance(ep.get("kg"), int) and 40 <= ep["kg"] <= 130:
        bits.append(f"{ep['kg']} kg")
    if isinstance(ep.get("debut"), int) and 1990 < ep["debut"] <= time.gmtime().tm_year:
        bits.append(f"Pro since {ep['debut']}")
    return " · ".join(bits)


LINKABLE = set()      # slugs com página de jogador (preenchido por result_card.build_site)


def plink(name):
    """Nome com link para a página do jogador, se existir."""
    s_ = webapp.slugify(name or "")
    return f'<a href="/p/{s_}.html">{esc(name)}</a>' if s_ in LINKABLE else esc(name or "")


_DATA_TO = None


def data_to():
    """Até quando vão os dados de carreira (ex.: 'June 2026'), a partir de history.json."""
    global _DATA_TO
    if _DATA_TO is None:
        hist = _HIST or {}
        d = (hist.get("meta") or {}).get("data_to") or ""
        if not d:
            ds = [f.get("d", "") for f in hist.get("finals") or []]
            ms = [m for v in (hist.get("p") or {}).values() for m, _ in (v.get("rk") or [])[-1:]]
            d = max(ds + [x + "-01" for x in ms] + [""])
        try:
            _DATA_TO = dt.date.fromisoformat(d[:10]).strftime("%B %Y") if d else ""
        except ValueError:
            _DATA_TO = ""
    return _DATA_TO


def career_block(name, women=False):
    """Carreira (agregada) a partir de history.json; vazio se não houver histórico."""
    h = hist_entry(name)
    if not h or not (h.get("w", 0) + h.get("l", 0)):
        return ""
    m = (_HIST.get("meta") or {"from": "?", "to": "?"})
    tot = h["w"] + h["l"]
    pct = round(100 * h["w"] / tot) if tot else 0
    titles = sum(v[2] for v in h.get("t", {}).values())
    box = lambda v, k: f'<div class="nbox"><b>{esc(str(v))}</b><span>{esc(k)}</span></div>'
    grid = ('<div class="numgrid">' + box(f'{h["w"]}-{h["l"]}', f'career {m["from"]} to {data_to() or m["to"]} ({pct}%)') +
            box(titles, "titles") + box(f'#{h["br"]}' if h.get("br") else "–", "best ranking") + "</div>")
    cup = lambda k: "Billie Jean King Cup" if women and k == "Davis Cup" else k     # no WTA a taça por equipas é a BJK Cup
    lv = "".join(f"<span>{esc(cup(k))} <b>{a}-{b}</b>{f' · {t} 🏆' if t else ''}</span>" for k, (a, b, t) in
                 sorted(h.get("t", {}).items(), key=lambda kv: -(kv[1][0] + kv[1][1])))
    sf = "".join(f"<span>{esc(k)} <b>{a}-{b}</b></span>" for k, (a, b) in sorted(h.get("s", {}).items(), key=lambda kv: -(kv[1][0] + kv[1][1])))
    ys = "".join(f'<tr><td class="pn">{y}</td><td>{a}-{b}</td></tr>' for y, (a, b) in sorted(h.get("y", {}).items(), reverse=True))
    bw = f'<p class="topw">Best career win: <b>{plink(h["bw"][1])}</b> (#{h["bw"][0]}, {h["bw"][2]})</p>' if h.get("bw") else ""
    return (f'<h2 class="dh">{esc(name)} career stats</h2>{grid}<div class="sfs">{lv}</div><div class="sfs">{sf}</div>{bw}'
            f'<table class="pt"><thead><tr><th>Year</th><th>W-L</th></tr></thead><tbody>{ys}</tbody></table>'
            f'<p class="cr">Career data to {esc(data_to() or "mid-2026")}: <a href="https://www.tennisabstract.com">Tennis Abstract</a> / Jeff Sackmann, '
            f'<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a> · main draw matches only, '
            f'aggregated by Beyond100.</p>')


_HIST = None


def next_match_block(name):
    """Próximo jogo do jogador (a partir de upcoming.json, já guardado pelo robô; não gasta pedidos à API)."""
    key = webapp.slugify(name or "")
    now = time.strftime("%Y-%m-%dT%H:%M", time.gmtime(time.time() - 3 * 3600))
    best = None
    for u in _load("upcoming.json", {}).get("matches", []):
        for i in (1, 2):
            if webapp.slugify((u.get("p%d" % i) or {}).get("name", "")) == key and (u.get("t") or "") >= now:
                if best is None or (u.get("t") or "") < (best[0].get("t") or ""):
                    best = (u, u.get("p%d" % (3 - i)) or {})
    if not best:
        return ""
    u, opp = best
    t = u.get("t") or ""
    when = site_ui.ltime(t, f"{t[8:10]}/{t[5:7]} · {t[11:16]} UTC", "dm") if len(t) >= 16 else ""
    rk = f" (#{opp['rank']})" if isinstance(opp.get("rank"), int) and opp["rank"] > 0 else ""
    tour = re.sub(r"^(ATP|WTA)\s+", "", u.get("tp") or "")
    bits = " · ".join(x for x in [esc(u.get("round") or ""), esc(tour), when] if x)
    return (f'<div class="nbox" style="text-align:left;margin:0 0 14px"><span>Next match</span>'
            f'<b style="font-size:1.25rem">vs {esc(opp.get("name", "?"))}{esc(rk)}</b><span>{bits}</span></div>')


def ranking_block(name, ms, current=None):
    """Bloco 'Ranking' logo a seguir ao topo da página: o que quem pesquisa '<nome> ranking' quer ver (Search Console, 5/11/2026).
    Ranking atual (com a data em que o vimos), melhor ranking da carreira (com o mês), mudança desde o ranking anterior,
    onde começou o ano e o gráfico da evolução. Só números que temos; o que faltar não aparece."""
    r = RANKS.get(webapp.slugify(name or "")) or {}
    h = hist_entry(name) or {}
    cur = current if isinstance(current, int) and current > 0 else (r.get("rank") if isinstance(r.get("rank"), int) else None)
    if not cur and not h.get("br"):
        return rank_chart(name, ms, current)
    box = lambda v, k: f'<div class="nbox"><b>{v}</b><span>{esc(k)}</span></div>'
    boxes = []
    if cur:
        when = r.get("date") or ""
        try:
            when = dt.date.fromisoformat(when).strftime("%d %b %Y") if when else ""
        except ValueError:
            pass
        boxes.append(box(f"No. {cur}", "current ranking" + (f" ({when})" if when else "")))
    br = h.get("br")
    rk = h.get("rk") or []
    best_m = ""
    if rk:
        bm = min(rk, key=lambda x: (x[1], x[0]))
        if not br or bm[1] <= br:
            br = bm[1]
            try:
                best_m = dt.date.fromisoformat(bm[0] + "-01").strftime("%b %Y")
            except ValueError:
                best_m = ""
    if isinstance(cur, int) and isinstance(br, int) and cur < br:
        br, best_m = cur, "now"
    if br:
        boxes.append(box(f"No. {br}", "career high" + (f" ({best_m})" if best_m else "")))
    prev = r.get("prev")
    if isinstance(prev, int) and isinstance(cur, int) and prev != cur and r.get("rank") == cur:
        d = prev - cur
        boxes.append(box(f'<span class="{"up" if d > 0 else "dn"}">{"▲" if d > 0 else "▼"}{abs(d)}</span>', f"since No. {prev}"))
    yr = time.strftime("%Y")
    start = next((v for m, v in sorted(rk) if m.startswith(yr)), None)
    if isinstance(start, int) and isinstance(cur, int) and start != cur:
        boxes.append(box(f"No. {start}", f"start of {yr}"))
    head = f'<h2 class="dh">{esc(name)} ranking</h2>'
    return head + '<div class="numgrid">' + "".join(boxes) + "</div>" + rank_chart(name, ms, cur).replace('<h2 class="dh">Ranking</h2>', "", 1)


def rank_chart(name, ms, current=None):
    """Gráfico simples do ranking ao longo do tempo, com o ranking que o jogador tinha em cada jogo que acompanhámos."""
    pts, career = {}, False
    for m, rk in ((hist_entry(name) or {}).get("rk") or []):
        pts[m + "-01"], career = rk, True                # evolução mensal desde há vários anos (Tennis Abstract)
    for i, r in ms:
        rk = (r.get("p%d" % i) or {}).get("rank")
        d = r.get("date") or ""
        if isinstance(rk, int) and rk > 0 and d and (not career or d[:7] + "-01" not in pts or d > max(pts)):
            pts[d] = rk                                  # completa com os jogos mais recentes que acompanhámos
    if isinstance(current, int) and current > 0:
        pts.setdefault(time.strftime("%Y-%m-%d", time.gmtime()), current)   # ranking atual (ranks.json) como último ponto
    if len(pts) < 3:
        return ""
    ds = sorted(pts)
    if ds[0] == ds[-1] or len(set(pts.values())) < 2:
        return ""
    W_, H_, pad = 600, 170, 26
    d0, d1 = dt.date.fromisoformat(ds[0][:10]), dt.date.fromisoformat(ds[-1][:10])
    span = max(1, (d1 - d0).days)
    lo, hi = min(pts.values()), max(pts.values())
    rng = max(1, hi - lo)
    xy = []
    for d in ds:
        x = pad + (W_ - 2 * pad) * (dt.date.fromisoformat(d[:10]) - d0).days / span
        y = pad + (H_ - 2 * pad) * (pts[d] - lo) / rng               # ranking melhor (número menor) fica em cima
        xy.append((round(x, 1), round(y, 1)))
    line = " ".join(f"{x},{y}" for x, y in xy)
    lx, ly = xy[-1]
    svg = (f'<svg viewBox="0 0 {W_} {H_}" width="100%" role="img" aria-label="Ranking over time">'
           f'<line x1="{pad}" y1="{pad}" x2="{W_ - pad}" y2="{pad}" stroke="currentColor" stroke-opacity=".15"/>'
           f'<line x1="{pad}" y1="{H_ - pad}" x2="{W_ - pad}" y2="{H_ - pad}" stroke="currentColor" stroke-opacity=".15"/>'
           f'<text x="{pad}" y="{pad - 8}" font-size="13" fill="currentColor" fill-opacity=".6">#{lo}</text>'
           f'<text x="{pad}" y="{H_ - 6}" font-size="13" fill="currentColor" fill-opacity=".6">#{hi}</text>'
           f'<polyline points="{line}" fill="none" stroke="var(--v)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>'
           f'<circle cx="{lx}" cy="{ly}" r="5" fill="var(--v)"/></svg>')
    first, last = pts[ds[0]], pts[ds[-1]]
    best = min(pts.values())
    note = f"#{first} in {ds[0][:7]} → #{last} in {ds[-1][:7]} · best #{best}"
    src = ("monthly ranking: Tennis Abstract (CC BY-NC-SA 4.0) + matches we tracked" if career else "from the matches we tracked")
    return (f'<h2 class="dh">Ranking</h2><div class="nbox" style="text-align:left">{svg}'
            f'<span>{esc(note)}</span><span style="display:block;margin-top:4px;text-transform:none;letter-spacing:0;opacity:.7">{esc(src)}</span></div>')


def _flag(code):
    import site_more
    c = (code or "").upper()
    return (f'<a href="/c/{c.lower()}.html" title="{esc(site_more.country_name(c))}">{site_more.flag(c, 16)}</a>' if site_more.flag(c) else "")


def player_page(e, tr, tx, ranks_by_name=None):
    tr = dict(tr, _tx=tx)
    ms = sorted(e["matches"], key=lambda x: (x[1].get("date", ""), -webapp._round_rank(x[1].get("round"))), reverse=True)
    w = sum(1 for i, r in ms if r["winner"] == i)
    l = len(ms) - w
    form = "".join(f'<i class="{"fw" if r["winner"] == i else "fl"}">{"W" if r["winner"] == i else "L"}</i>' for i, r in ms[:8])
    rk = ranks_by_name.get(e["name"]) if ranks_by_name else None
    rank = (rk or {}).get("rank") or e["rank"]
    meta = " · ".join(x for x in [e["country"], f"#{rank}" if rank else ""] if x)
    surf = {}
    for i, r in ms:
        s = (r.get("surface") or "").title()
        if s:
            row = surf.setdefault(s, [0, 0])
            row[0 if r["winner"] == i else 1] += 1
    sh = "".join(f"<span>{esc(k)} <b>{a}-{b}</b></span>" for k, (a, b) in surf.items())
    best = None
    for i, r in ms:
        if r["winner"] == i:
            opp = r["p%d" % (3 - i)]
            if isinstance(opp.get("rank"), int) and (best is None or opp["rank"] < best[0]):
                best = (opp["rank"], opp["name"])
    bh = f'<p class="topw">Best win: <b>{plink(best[1])}</b> (#{best[0]})</p>' if best else ""
    body = "".join(webapp.match_html(r, tr) for _, r in ms[:30])
    import site_ui
    sl = webapp.slugify(e["name"])
    rk_int = rank if isinstance(rank, int) else None
    pct = f"{round(100 * w / len(ms))}%" if ms else "–"
    streak = 0
    for i, r in ms:
        if r["winner"] != i:
            break
        streak += 1
    sub = _flag(e["country"]) + esc(" · ".join(x for x in [e["country"], bio_line(e["name"]) or ""] if x))
    rr = RANKS.get(sl) or {}
    now = []
    if rk_int:
        now.append((f"No. {rk_int}", "rank", ""))
        prev = rr.get("prev")
        if isinstance(prev, int) and prev != rk_int and rr.get("rank") == rk_int:
            d = prev - rk_int
            now.append((f'{"▲" if d > 0 else "▼"}{abs(d)}', "this week", "up" if d > 0 else "dn"))
        if isinstance(rr.get("pts"), int) and rr.get("rank") == rk_int:
            now.append((f'{rr["pts"]:,}', "points", ""))
    now.append((f"{w}-{l}", f"last {len(ms)}" if len(ms) != 1 else "last match", ""))
    if len(now) < 4:
        now.append((pct, "win rate", ""))
    if len(now) < 4:
        now.append((f"W{streak}" if streak else "–", "streak", ""))
    h_ = hist_entry(e["name"]) or {}
    car = []
    if h_.get("w", 0) + h_.get("l", 0):
        br, bm_ = h_.get("br"), ""
        rkh = h_.get("rk") or []
        if rkh:
            bm = min(rkh, key=lambda x: (x[1], x[0]))
            if not br or bm[1] <= br:
                br = bm[1]
                try:
                    bm_ = dt.date.fromisoformat(bm[0] + "-01").strftime("%b %Y")
                except ValueError:
                    bm_ = ""
        if isinstance(rk_int, int) and isinstance(br, int) and rk_int < br:
            br, bm_ = rk_int, "now"
        if br:
            car.append((f"No. {br}", "high" + (f" · {bm_}" if bm_ else ""), ""))
        car.append((f'{h_["w"]}-{h_["l"]}', "all levels", ""))
        car.append((str(sum(v[2] for v in (h_.get("t") or {}).values() if len(v) > 2)), "titles", ""))
        if h_.get("bw"):
            car.append((esc(h_["bw"][1].split()[-1]), f'best win · No. {h_["bw"][0]}', ""))
    table = [("Now", now)] + ([("Career", car)] if car else [])
    hero = site_ui.player_hero("/players.html", tx.get("players", "Players"), f"/img/big/{sl}.jpg" if sl in webapp.AVATARS else "",
                               e["name"], sub, rk_int, "", [r["winner"] == i for i, r in ms[:8]],
                               [(f"{w}-{l}", "won-lost"), (pct, "win rate"), (f"W{streak}" if streak else "–", "streak"), (len(ms), "matches")],
                               credit_line(e["name"]).replace('<p class="cr">', "").replace("</p>", ""), square=True, table=table)
    try:
        import tennis_videos
        vids = tennis_videos.cards([r for _, r in ms], "▶ Highlights", 12)
    except Exception:
        vids = ""
    women = any(r.get("gender") == "women" or r.get("tour") == "wta" for _, r in ms)
    yr = (ms[0][1].get("date") or "")[:4] if ms else ""
    nl_box = _nl_inline(f"Following {e['name']}? Get the whole week in one email")
    return (hero + profile_block(e, ms, rk_int, women) +
            f'{ranking_block(e["name"], ms, rk_int)}{next_match_block(e["name"])}{vids}{season_line(PSTATS_BY_NAME.get(sl))}<div class="sfs">{sh}</div>{bh}{career_block(e["name"], women)}'
            f'{nl_box}'
            f'<h2 class="dh">{esc(e["name"])} results{f" {yr}" if yr else ""}</h2><section class="tg">{body}</section>{related_block(e, rk_int)}')


def _ord_round(rd):
    """Ronda em texto corrido: 'the quarter-finals', 'the second round'..."""
    r = (rd or "").lower()
    named = {"final": "the final", "semi-finals": "the semi-finals", "semifinals": "the semi-finals", "quarter-finals": "the quarter-finals",
             "quarterfinals": "the quarter-finals", "1/8-finals": "the last 16", "round of 16": "the last 16", "1/16-finals": "the last 32",
             "round of 32": "the last 32", "1/32-finals": "the last 64", "round of 64": "the last 64", "round of 128": "the first round"}
    return named.get(r, f"the {r}" if r else "")


def profile_block(e, ms, rank=None, women=False):
    """Resumo em texto corrido no topo da página do jogador (SEO, 7/11/2026). Escrito a partir dos dados que já temos
    (ranking, melhor ranking, carreira, último torneio), sem IA e sem inventar: o que faltar não entra."""
    import site_more
    name = e["name"]
    first = name.split()[0] if name else name
    he, his, him = ("she", "her", "her") if women else ("he", "his", "him")
    h = hist_entry(name) or {}
    r = RANKS.get(webapp.slugify(name)) or {}
    out = []
    try:
        import espn_sync
        ep = espn_sync.profile_for(name)
    except Exception:
        ep = {}
    b = h.get("bio") or {}
    dob = str(b.get("dob") or "")
    age = None
    if len(dob) >= 8 and dob[:8].isdigit():
        t = time.gmtime()
        age = t.tm_year - int(dob[:4]) - ((t.tm_mon, t.tm_mday) < (int(dob[4:6]), int(dob[6:8])))
    elif ep.get("bd"):
        age = _age(ep["bd"])
    age = age if isinstance(age, int) and 14 <= age <= 50 else None
    cty = site_more.country_name(e.get("country") or "") if e.get("country") else ""
    tour = "WTA" if women else "ATP"
    if cty.startswith(("United ", "Netherlands", "Czech Republic", "Philippines", "Dominican Republic", "Bahamas")):
        cty = "the " + cty
    s1 = esc(name) + " is a " + (f"{age}-year-old " if age else "") + "tennis player" + (f" from {esc(cty)}" if cty else "")
    if isinstance(rank, int):
        when = r.get("date") or ""
        try:
            when = dt.date.fromisoformat(when).strftime("%-d %B %Y") if when else ""
        except ValueError:
            when = ""
        s1 += f", ranked <b>No. {rank}</b> in the {tour} rankings" + (f" ({when})" if when else "")
        prev = r.get("prev")
        if isinstance(prev, int) and prev != rank and r.get("rank") == rank:
            d = prev - rank
            s1 += f", {'up' if d > 0 else 'down'} {abs(d)} place{'s' if abs(d) != 1 else ''} on the previous week"
    out.append(s1 + ".")
    rk = h.get("rk") or []
    if rk:
        bm = min(rk, key=lambda x: (x[1], x[0]))
        if not (isinstance(rank, int) and rank < bm[1]):
            try:
                mon = dt.date.fromisoformat(bm[0] + "-01").strftime("%B %Y")
            except ValueError:
                mon = ""
            out.append(f"{his.capitalize()} career high is No. {bm[1]}" + (f", first reached in {mon}" if mon else "") + ".")
        else:
            out.append(f"That is the highest {he} has ever been ranked.")
    tot = h.get("w", 0) + h.get("l", 0)
    if tot >= 20:
        m = (_HIST.get("meta") or {})
        y0 = min((y for y in (h.get("y") or {}) if y.isdigit()), default=str(m.get("from", 2015)))
        bits = f"Since {y0}, {first} has a {h['w']}-{h['l']} record in main-draw matches"
        surf = [(k, a, b_) for k, (a, b_) in (h.get("s") or {}).items() if a + b_ >= 20]
        if len(surf) > 1:
            k, a, b_ = max(surf, key=lambda x: x[1] / (x[1] + x[2]))
            bits += f", with {his} best results on {k.lower()} courts ({a}-{b_})"
        out.append(bits + ".")
        fl = h.get("fl") or 0
        tl = {k: v[2] for k, v in (h.get("t") or {}).items() if len(v) > 2 and v[2]}
        titles = sum(tl.values())
        lvl = {"Tour": f"{tour} Tour", "Grand Slam": "Grand Slam", "Masters 1000": "Masters 1000", "Challenger": "Challenger" if not women else "WTA 125",
               "ITF": "ITF", "Tour Finals": "Tour Finals"}
        brk = ", ".join(f"{n} {lvl.get(k, k)}" for k, n in sorted(tl.items(), key=lambda kv: -kv[1]))
        if titles:
            one = next(iter(tl)) if len(tl) == 1 else None
            where = (f", all at {lvl.get(one, one)} level" if titles > 1 else f" at {lvl.get(one, one)} level") if one else (f" ({brk})" if brk else "")
            out.append(f"{he.capitalize()} has won {titles} title{'s' if titles != 1 else ''} in that time" + where
                       + (f", from {fl} finals" if fl > titles else "") + ".")
        elif fl:
            out.append(f"{he.capitalize()} has reached {fl} final{'s' if fl != 1 else ''} in that time, still looking for a first title.")
    if h.get("bw"):
        out.append(f"{his.capitalize()} biggest win came against world No. {h['bw'][0]} {plink(h['bw'][1])} in {h['bw'][2]}.")
    # último torneio: até onde chegou, melhor vitória e quem o parou
    if ms:
        t0 = webapp.base_tournament(ms[0][1].get("tournament", ""))
        run = [(i, x) for i, x in ms if webapp.base_tournament(x.get("tournament", "")) == t0 and abs((dt.date.fromisoformat(ms[0][1]["date"][:10]) - dt.date.fromisoformat(x["date"][:10])).days) <= 12]
        main = [(i, x) for i, x in run if not x.get("q")]
        qual = any(x.get("q") for _, x in run)
        last_i, last = run[0]
        won_last = last.get("winner") == last_i
        mon = ""
        try:
            mon = dt.date.fromisoformat(last["date"][:10]).strftime("%B %Y")
        except ValueError:
            pass
        wins = [(x["p%d" % (3 - i)]) for i, x in main if x.get("winner") == i]
        best = min((o for o in wins if isinstance(o.get("rank"), int)), key=lambda o: o["rank"], default=None)
        opp = last["p%d" % (3 - last_i)]
        rd = _ord_round(last.get("round"))
        s = f"Most recently, at {esc(t0)}" + (f" in {mon}" if mon else "") + f", {he}"
        if main and qual:
            s += " came through qualifying and"
        if not main:
            s += (f" won {his} qualifying match against {plink(opp['name'])}" if won_last else f" lost in qualifying to {plink(opp['name'])}")
        elif won_last and (last.get("round") or "").lower() == "final":
            s += f" won the title, beating {plink(opp['name'])} in the final"
        elif won_last:
            s += f" beat {'No. ' + str(opp['rank']) + ' ' if isinstance(opp.get('rank'), int) else ''}{plink(opp['name'])}" + (f" in {rd}" if rd else "")
        elif not wins:
            s += f" lost to {plink(opp['name'])}" + (f" in {rd}" if rd and rd != "the first round" else " in the first round")
        else:
            s += f" reached {rd}" if rd else " played"
            if best and best is not opp:
                s += f", beating No. {best['rank']} {plink(best['name'])}"
            s += f" before losing to {plink(opp['name'])}"
        out.append(s + ".")
    if len(out) < 2:
        return ""
    return f'<h2 class="dh">About {esc(name)}</h2><p class="about">' + " ".join(out) + "</p>"


PIDX = {}           # slug -> entrada de players_index (preenchido por result_card.build_site), para as ligações entre jogadores


def related_block(e, rank=None):
    """Ligações a páginas relacionadas (SEO e navegação, 5/11/2026): adversários frequentes (com o registo entre os dois)
    e jogadores do mesmo país com ranking próximo. Só jogadores com página."""
    import site_more
    me = webapp.slugify(e["name"])
    opp = {}
    for i, r in e["matches"]:
        o = r["p%d" % (3 - i)]["name"]
        k = webapp.slugify(o)
        x = opp.setdefault(k, [o, 0, 0])
        x[1 if r["winner"] == i else 2] += 1
    freq = sorted([v for k, v in opp.items() if k in LINKABLE and v[1] + v[2] >= 2], key=lambda v: -(v[1] + v[2]))[:5]
    out = ""
    if freq:
        out += ('<h2 class="dh">Frequent opponents</h2><div class="sfs">'
                + "".join(f'<span>{plink(n)} <b>{a}-{b}</b></span>' for n, a, b in freq) + "</div>")
    c = e.get("country") or ""
    if c and PIDX:
        mates = [(v.get("rank") or 9999, v["name"]) for k, v in PIDX.items()
                 if k != me and k in LINKABLE and (v.get("country") or "") == c]
        if mates:
            r0 = rank if isinstance(rank, int) else 500
            mates.sort(key=lambda x: (abs(x[0] - r0), x[0]))
            pick = sorted(mates[:6])
            out += (f'<h2 class="dh">More players from {esc(site_more.country_name(c))}</h2><div class="sfs">'
                    + "".join(f'<span>{plink(n)}{f" <b>#{rk}</b>" if rk < 9999 else ""}</span>' for rk, n in pick)
                    + f'<span><a href="/c/{c.lower()}.html">All →</a></span></div>')
    return out


CREDITS = {}        # slug -> "Photo: Autor / licença" (preenchido por result_card.build_site)


def credit_line(name):
    c = CREDITS.get(webapp.slugify(name or ""))
    return f'<p class="cr">{esc(c)} · <a href="/credits.html">credits</a></p>' if c else ""


def credits_page(tx=None):
    rows = "".join(f'<tr><td class="pn">{esc(v["name"])}</td><td>{esc(v["credit"])}</td>'
                   f'<td>{("<a href=" + chr(34) + esc(v["page"]) + chr(34) + ">source</a>") if v.get("page") else ""}</td></tr>'
                   for _, v in sorted(CREDIT_ROWS.items()))
    return (f'<section class="page-h"><h1>{esc(L(tx, "x_credits"))}</h1><p>{esc(L(tx, "x_credits_p"))}</p></section>'
            f'<table class="pt"><thead><tr><th>{esc(L(tx, "player"))}</th><th>{esc(L(tx, "x_credit"))}</th>'
            f'<th>{esc(L(tx, "x_source"))}</th></tr></thead><tbody>{rows}</tbody></table>')


CREDIT_ROWS = {}


# ---------- "a decorrer agora" ----------
def live_rows():
    d = _load(LIVE_FILE, {})
    if time.time() - d.get("ts", 0) > LIVE_MAX_AGE_H * 3600:
        return []
    return [m for m in d.get("matches") or [] if m.get("id") is not None]


def _fl(code, h=12):
    import site_more
    return site_more.flag(code, h)


RANKS = {}          # slug -> registo de ranks.json (preenchido por result_card.build_site)


def rank_move(name, rank=None, pts=False):
    """'▲12' / '▼5' desde a última vez que o ranking mudou (ranks.json); só a seta se só soubermos o sentido."""
    r = RANKS.get(webapp.slugify(name or "")) or {}
    if not r or (isinstance(rank, int) and isinstance(r.get("rank"), int) and r["rank"] != rank):
        return ""
    out = ""
    prev, cur = r.get("prev"), r.get("rank")
    if isinstance(prev, int) and isinstance(cur, int) and prev != cur:
        d = prev - cur
        out = (f'<span class="{"up" if d > 0 else "dn"}" title="{"+" if d > 0 else ""}{d} places since {esc(r.get("prev_date", ""))}">'
               f'{"▲" if d > 0 else "▼"}{abs(d)}</span>')
    elif r.get("mv") in ("up", "down"):
        out = f'<span class="{"up" if r["mv"] == "up" else "dn"}">{"▲" if r["mv"] == "up" else "▼"}</span>'
    if pts and isinstance(r.get("pts"), int) and r["pts"] > 0:
        out += f' <span class="rpts">{r["pts"]:,} pts</span>'
    return (" " + out) if out else ""


def who_html(p, move=False):
    """Bandeira + 'CZE · #21' (+ variação do ranking, se move=True)."""
    return f'{_fl(p.get("country"))}{esc(webapp.who_tag(p))}{rank_move(p.get("name"), p.get("rank")) if move else ""}'


LIVE_JS = r"""<script>(()=>{const W=document.getElementById("lvwrap");if(!W)return;const N=+W.dataset.n||8,G=W.querySelector(".lvg"),U=W.querySelector(".lvu");
const nk=s=>(s||"").normalize("NFKD").replace(/[^A-Za-z\s-]/g,"").toLowerCase().split(/[\s-]+/).filter(Boolean);
const ks=s=>{const w=nk(s);return w.length?[w.join(""),w[0][0]+w[w.length-1]]:[]};
const same=(a,b)=>{const A=ks(a);return ks(b).some(k=>A.includes(k))};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const sc=(s,o,tb)=>s.map((x,i)=>`<span>${x}${tb&&tb[i]!=null&&i<s.length-1&&x==6&&o[i]==7?`<sup>${tb[i]}</sup>`:""}</span>`).join("");
const fl=f=>f?`<img src="https://flagcdn.com/${f}.svg" alt="" width="16" height="12" loading="lazy" style="vertical-align:-2px;margin-right:7px;border-radius:2px">`:"";
let miss=0;const again=()=>{if(++miss<=6)setTimeout(tick,5000);else if(!seen&&S)S.innerHTML='<span class="dot"></span> In progress · the live score shows up here as soon as the first points are played (checking every 30 s)'};
async function tick(){if(document.hidden)return;let j;try{const r=await fetch("/api/tennis/live",{cache:"no-store"});if(!r.ok)return again();j=await r.json()}catch(e){return again()}
 const cards=[...G.querySelectorAll(".lv")];let added=0;const got=new Set();
 for(const m of [...(j.matches||[]),...(j.fin||[]).map(x=>Object.assign({},x,{done:1}))]){let hit=null,flip=false;
  for(const c of cards){const a=c.dataset.a,b=c.dataset.b;if(!a)continue;if(same(a,m.p[0].n)&&same(b,m.p[1].n)){hit=c;break}if(same(a,m.p[1].n)&&same(b,m.p[0].n)){hit=c;flip=true;break}}
  const s=flip?[m.s[1],m.s[0]]:m.s,tb=flip?[m.tb[1],m.tb[0]]:m.tb;
  if(hit){got.add(hit);const z=hit.querySelectorAll(".sc");if(z.length==2){z[0].innerHTML=sc(s[0],s[1],tb[0]);z[1].innerHTML=sc(s[1],s[0],tb[1])}hit.classList.add("rt");
   if(m.done&&!hit.dataset.fin){hit.dataset.fin=1;hit.style.opacity=".75";const h=hit.querySelector(".lh");if(h)h.insertAdjacentHTML("beforeend",' <b style="color:#d9f23d">· Final</b>');
    const w=flip?(m.w===0?1:m.w===1?0:null):m.w;const pl=hit.querySelectorAll(".pl");if(w!=null&&pl[1-w])pl[1-w].style.opacity=".6"}continue}
  if(m.done||cards.length+added>=N)continue;added++;
  const d=document.createElement("div");d.className="lv rt";d.dataset.a=m.p[0].n;d.dataset.b=m.p[1].n;
  d.innerHTML=`<div class="lh"><span class="tag">${m.lg.toUpperCase()}</span> ${esc(m.t)} · ${esc(m.r)}</div>`+[0,1].map(i=>`<div class="pl"><div class="who"><div><span class="nm">${esc(m.p[i].n)}</span><small>${fl(m.p[i].f)}${esc(m.p[i].c)}</small></div></div><div class="sc">${sc(m.s[i],m.s[1-i],m.tb[i])}</div></div>`).join("");
  G.appendChild(d)}
 for(const c of cards){const t=(c.querySelector(".tag")||{}).textContent||"";if(/^(ATP|WTA) (250|500|1000)\b/.test(t)&&!got.has(c))c.style.display="none"}   // ATP/WTA que o ESPN já não tem: acabou há horas, sai da lista
 if([...G.querySelectorAll(".lv")].some(c=>c.style.display!=="none")){W.hidden=false;if(U)U.textContent="live · "+new Date(j.ts).toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit"})}}
tick();const T=setInterval(tick,30000);document.addEventListener("visibilitychange",tick)})()</script>"""


def live_block(tx=None, n=8):
    """Faixa 'Playing now'. Os jogos vêm do live.json (cada 30 min, todos os circuitos); no browser, os ATP/WTA são atualizados a cada 30 s
    pelo ESPN (/api/tennis/live, sem quota) e os que faltam são acrescentados. Sem jogos no live.json fica escondida até o ESPN ter algum."""
    d = _load(LIVE_FILE, {})
    rows = live_rows()
    when = time.strftime("%H:%M", time.gmtime(d.get("ts", time.time())))
    items = ""
    for m in rows[:n]:
        a, b = m["p1"], m["p2"]
        ga, gb = m["games"]
        sa = "".join(f"<span>{int(x)}</span>" for x in ga)
        sb = "".join(f"<span>{int(x)}</span>" for x in gb)
        items += (f'<a class="lv" href="/live/{m["id"]}.html" data-a="{esc(a["name"])}" data-b="{esc(b["name"])}"><div class="lh"><span class="tag">{esc(m.get("tag", ""))}</span> '
                  f'{esc(m.get("tournament", ""))} · {esc(m.get("round", ""))}<span class="lgo">›</span></div>'
                  f'<div class="pl"><div class="who">{webapp.avatar(a["name"])}<div><span class="nm">{esc(a["name"])}</span><small>{who_html(a, True)}</small></div></div><div class="sc">{sa}</div></div>'
                  f'<div class="pl"><div class="who">{webapp.avatar(b["name"])}<div><span class="nm">{esc(b["name"])}</span><small>{who_html(b, True)}</small></div></div><div class="sc">{sb}</div></div></a>')
    upd = esc(L(tx, "x_updated", t=when)) if rows else ""
    return (f'<div id="lvwrap" data-n="{n}"{"" if rows else " hidden"}>'
            f'<h2 class="sec" id="live-now"><span><span class="dot" style="display:inline-block;margin-right:8px"></span>{esc(L(tx, "x_playing"))}</span><small><span class="lvu">{upd}</span> · <a href="/order-of-play.html">Order of play</a></small></h2>'
            f'<div class="lvg">{items}</div>'
            + (f'<p style="margin:10px 0 0"><a class="lmore" href="/order-of-play.html">+{len(rows) - n} more on court now →</a></p>' if len(rows) > n else "")
            + '</div>' + LIVE_JS)


PSTATS, PSTATS_BY_NAME = {}, {}     # player_stats.json (preenchido por result_card.build_site)


def season_line(ps):
    """'2026 season: 23-12 · Hard 13-8 · Clay 10-4 · 1 title' (ficha da API)."""
    ss = [x for x in (ps or {}).get("seasons") or [] if isinstance(x.get("w"), int) and isinstance(x.get("l"), int) and x["w"] + x["l"] > 0]
    if not ss:
        return ""
    x = ss[0]
    bits = [f'<b>{x["w"]}-{x["l"]}</b>']
    for sf, (a, b) in sorted((x.get("s") or {}).items(), key=lambda kv: -sum(v or 0 for v in kv[1])):
        if isinstance(a, int) and isinstance(b, int) and a + b:
            bits.append(f"{sf.title()} {a}-{b}")
    if x.get("t"):
        bits.append(f'{x["t"]} title{"s" if x["t"] > 1 else ""}')
    if isinstance(x.get("rk"), int) and x["rk"] > 0 and str(x.get("y")) != time.strftime("%Y", time.gmtime()):
        bits.append(f"year-end #{x['rk']}")
    return f'<p class="ssn"><span>{esc(str(x.get("y") or ""))} season</span> {" · ".join(bits)}</p>'


def _age(bd):
    try:
        y, mo, da = (int(x) for x in str(bd)[:10].split("-"))
    except ValueError:
        return None
    t = time.gmtime()
    a = t.tm_year - y - ((t.tm_mon, t.tm_mday) < (mo, da))
    return a if 14 <= a <= 50 else None


def _pcard(p):
    import site_more
    name = p["name"]
    h = hist_entry(name) or {}
    _rk = p.get("rank") if isinstance(p.get("rank"), int) and p["rank"] > 0 else None
    bits = [x for x in [esc(site_more.country_name((p.get("country") or "").upper())),
                        (f"#{_rk}" + rank_move(name, _rk, pts=True)) if _rk else "",
                        f"Age {_age(p.get('bd'))}" if _age(p.get("bd")) else ""] if x]
    ps = PSTATS.get(str(p.get("pid"))) or PSTATS_BY_NAME.get(webapp.slugify(name)) or {}
    bio = bio_line(name)
    bio = [x for x in bio.split(" · ") if not x.startswith("Age")] if bio else []
    if not any("handed" in x for x in bio):
        hd = {"R": "Right-handed", "L": "Left-handed"}.get(p.get("hand") or ps.get("hand"))
        if hd:
            bio.append(hd)
    bh = {1: "one-handed backhand", 2: "two-handed backhand"}.get(p.get("bh") or ps.get("bh"))
    if bh:
        bio.append(bh)
    if not any(x.endswith(" m") for x in bio) and isinstance(ps.get("h"), int) and 150 <= ps["h"] <= 215:
        bio.append(f"{ps['h'] / 100:.2f} m")
    if isinstance(p.get("itf"), int) and p["itf"] > 0:
        bio.append(f"ITF #{p['itf']}")
    bio = " · ".join(bio)
    titles = sum(v[2] for v in (h.get("t") or {}).values()) if h.get("t") else None
    facts = []
    if h.get("br"):
        facts.append(f'<div class="nbox"><b>#{h["br"]}</b><span>career high</span></div>')
    if titles is not None:
        facts.append(f'<div class="nbox"><b>{titles}</b><span>titles</span></div>')
    if h.get("w", 0) + h.get("l", 0):
        facts.append(f'<div class="nbox"><b>{h["w"]}-{h["l"]}</b><span>career W-L</span></div>')
    sl = webapp.slugify(name)
    more = season_line(ps) + (f'<a class="lmore" href="/p/{sl}.html">Full profile →</a>' if sl in LINKABLE else "")
    return (f'<div class="lpc"><div class="ph">{webapp.avatar(name, "avl")}<div><h3>{plink(name)}</h3>'
            f'<p>{_fl(p.get("country"), 14)}{" · ".join(bits)}</p>{("<p class=cr>" + esc(bio) + "</p>") if bio else ""}{credit_line(name)}</div></div>'
            f'{("<div class=numgrid>" + "".join(facts) + "</div>") if facts else ""}{more}</div>')


def _tape(p):
    """Idade, altura, mão e época (o que soubermos: Tennis Abstract, ESPN, ficha da API)."""
    name = p.get("name") or ""
    b = (hist_entry(name) or {}).get("bio") or {}
    try:
        import espn_sync
        ep = espn_sync.profile_for(name)
    except Exception:
        ep = {}
    ps = PSTATS.get(str(p.get("pid"))) or PSTATS_BY_NAME.get(webapp.slugify(name)) or {}
    age = _age(p.get("bd")) or _age(ep.get("bd"))
    if not age and len(str(b.get("dob") or "")) >= 8:
        d = str(b["dob"])
        age = _age(f"{d[:4]}-{d[4:6]}-{d[6:8]}")
    if not age and isinstance(ep.get("age"), int):
        age = ep["age"]
    h = b.get("h") if isinstance(b.get("h"), int) else ep.get("h") if isinstance(ep.get("h"), int) else ps.get("h")
    hand = {"R": "Right", "L": "Left"}.get(b.get("hand") or ep.get("hand") or ps.get("hand") or p.get("hand"))
    ss = [s for s in ps.get("seasons") or [] if isinstance(s.get("w"), int) and isinstance(s.get("l"), int)]
    season = (ss[0]["w"], ss[0]["l"], ss[0].get("y")) if ss else None
    return {"age": age, "h": h if isinstance(h, int) and 150 <= h <= 215 else None, "hand": hand, "season": season}


def match_stats_html(a, b, ga, gb, tb=None, results=(), live=False, skip_id=None):
    """'Match stats' por baixo do placar: sets, jogos e tie-breaks (calculados do resultado; no direto atualizam pelo ESPN),
    e o 'tale of the tape': ranking, idade, altura, mão, época e confronto direto nos jogos que seguimos."""
    import site_ui
    n = max(len(ga), len(gb))
    done = lambda k: (not live) or k < n - 1
    sa = sum(1 for k in range(n) if done(k) and k < len(ga) and k < len(gb) and webapp._set_done(ga[k], gb[k]) and ga[k] > gb[k])
    sb = sum(1 for k in range(n) if done(k) and k < len(ga) and k < len(gb) and webapp._set_done(ga[k], gb[k]) and gb[k] > ga[k])
    tba = sum(1 for k in range(min(len(ga), len(gb))) if ga[k] == 7 and gb[k] == 6)
    tbb = sum(1 for k in range(min(len(ga), len(gb))) if gb[k] == 7 and ga[k] == 6)
    rows = [("Sets won", sa, sb, str(sa), str(sb), "sets"), ("Games won", sum(ga), sum(gb), str(sum(ga)), str(sum(gb)), "games")]
    if tba + tbb:
        rows.append(("Tie-breaks won", tba, tbb, str(tba), str(tbb), "tbs"))
    match = site_ui.compare((esc(a["name"].split()[-1]), esc(b["name"].split()[-1])), rows)
    ta, tb_ = _tape(a), _tape(b)
    rk = lambda p: f'#{p["rank"]}' if isinstance(p.get("rank"), int) and p["rank"] > 0 else "–"
    tape = [("Ranking", None, None, rk(a), rk(b), "rk")]
    if ta["age"] or tb_["age"]:
        tape.append(("Age", None, None, str(ta["age"] or "–"), str(tb_["age"] or "–"), "age"))
    if ta["h"] or tb_["h"]:
        tape.append(("Height", None, None, f'{ta["h"] / 100:.2f} m' if ta["h"] else "–", f'{tb_["h"] / 100:.2f} m' if tb_["h"] else "–", "h"))
    if ta["hand"] or tb_["hand"]:
        tape.append(("Plays", None, None, ta["hand"] or "–", tb_["hand"] or "–", "hand"))
    if ta["season"] or tb_["season"]:
        f_ = lambda s: f"{s[0]}-{s[1]}" if s else "–"
        y = (ta["season"] or tb_["season"])[2]
        tape.append((f"{y} season" if y else "Season", (ta["season"] or (0, 0))[0], (tb_["season"] or (0, 0))[0], f_(ta["season"]), f_(tb_["season"]), "ssn"))
    sla, slb = webapp.slugify(a["name"]), webapp.slugify(b["name"])
    hw = [0, 0]
    for r in results or []:
        if r.get("id") == skip_id or r.get("winner") not in (1, 2):
            continue
        n1, n2 = webapp.slugify(r["p1"]["name"]), webapp.slugify(r["p2"]["name"])
        if {n1, n2} == {sla, slb}:
            wn = webapp.slugify(r["p%d" % r["winner"]]["name"])
            hw[0 if wn == sla else 1] += 1
    if sum(hw):
        tape.append(("Head to head", hw[0], hw[1], str(hw[0]), str(hw[1]), "h2h"))
    return (f'{site_ui.sec("Match stats")}{match}'
            f'{site_ui.sec("Tale of the tape")}{site_ui.compare((esc(a["name"].split()[-1]), esc(b["name"].split()[-1])), tape)}'
            '<p class="mut2" style="margin-top:8px">Calculated from the score and the data we track. Aces, breaks and serve stats are not available from our sources.</p>')


LIVEPAGE_JS = r"""<script>(()=>{const B=document.querySelector(".ui-sb[data-a]");if(!B)return;const S=document.querySelector(".lstat");let seen=false,gone=0;
const nk=s=>(s||"").normalize("NFKD").replace(/[^A-Za-z\s-]/g,"").toLowerCase().split(/[\s-]+/).filter(Boolean);
const ks=s=>{const w=nk(s);return w.length?[w.join(""),w[0][0]+w[w.length-1]]:[]};const same=(a,b)=>{const A=ks(a);return ks(b).some(k=>A.includes(k))};
const rows=()=>[...B.querySelectorAll(".r")];const cur=()=>rows().map(r=>[...r.querySelectorAll(".cols span:not(.gp)")].map(c=>parseInt(c.textContent)).join(","));
const done=(x,y)=>(Math.max(x,y)>=6&&Math.abs(x-y)>=2)||(Math.max(x,y)==7&&Math.min(x,y)>=5)||(Math.max(x,y)>=10&&Math.abs(x-y)>=2);
function stat(k,a,b){const c=document.querySelector(`.ui-cmp .c[data-k="${k}"]`);if(!c)return;const v=c.querySelectorAll(":scope>b");v[0].textContent=a;v[1].textContent=b;
 const i=c.querySelectorAll(".bar i");if(i.length==2&&a+b>0){const p=Math.round(100*a/(a+b));i[0].style.width=p+"%";i[1].style.width=(100-p)+"%";i[0].className=a>b||(a==b&&a)?"hi":"";i[1].className=b>a||(a==b&&a)?"hi":""}else if(i.length==2){i[0].style.width="50%";i[1].style.width="50%"}}
let miss=0;const again=()=>{if(++miss<=6)setTimeout(tick,5000);else if(!seen&&S)S.innerHTML='<span class="dot"></span> In progress · live score unavailable right now · last update '+B.dataset.w+' UTC'};
async function tick(){if(document.hidden)return;let j;try{const r=await fetch("/api/tennis/live",{cache:"no-store"});if(!r.ok)return again();j=await r.json()}catch(e){return again()}
 const a=B.dataset.a,b=B.dataset.b;const m=(j.matches||[]).find(m=>(same(a,m.p[0].n)&&same(b,m.p[1].n))||(same(a,m.p[1].n)&&same(b,m.p[0].n)));
 const F=!m&&(j.fin||[]).find(m=>(same(a,m.p[0].n)&&same(b,m.p[1].n))||(same(a,m.p[1].n)&&same(b,m.p[0].n)));
 if(F){const f=same(a,F.p[1].n),s=f?[F.s[1],F.s[0]]:F.s,t=f?[F.tb[1],F.tb[0]]:F.tb,w=F.w<0?-1:(f?1-F.w:F.w),n=s[0].length;
  B.classList.remove("live");B.querySelector(".hd .cols").innerHTML=[...Array(n)].map((_,k)=>`<i>S${k+1}</i>`).join("");const nt=B.querySelector(".nt");if(nt)nt.remove();
  rows().forEach((r,i)=>{r.classList.remove("sv");r.classList.toggle("w",w===i);r.classList.toggle("l",w>=0&&w!==i);r.querySelector(".cols").innerHTML=s[i].map((x,k)=>{const y=s[1-i][k];return `<span class="${x>y?"on":""}">${x}${t[i]&&t[i][k]!=null&&x==6&&y==7?`<sup>${t[i][k]}</sup>`:""}</span>`}).join("")});
  let sa=0,sb=0;for(let k=0;k<n;k++){s[0][k]>s[1][k]?sa++:sb++}stat("sets",sa,sb);stat("games",s[0].reduce((p,q)=>p+q,0),s[1].reduce((p,q)=>p+q,0));
  const wn=w>=0?(w===0?a:b):"";if(S)S.innerHTML='<span class="dot" style="background:var(--s)"></span> Final'+(wn?' · '+wn.replace(/</g,"")+' wins':'')+' · the full match page follows at the next site update';clearInterval(T);return}
 if(!m){if(!seen)again();if(seen&&++gone>=2&&S)S.innerHTML='<span class="dot"></span> Match finished · the final result appears here in a few minutes';return}
 seen=true;gone=0;miss=0;const f=same(a,m.p[1].n),s=f?[m.s[1],m.s[0]]:m.s,t=f?[m.tb[1],m.tb[0]]:m.tb,n=s[0].length,sv=m.sv==null?null:(f?1-m.sv:m.sv);
 const fresh=Date.now()-(+B.dataset.pt||0)*1000<600000;const keep=fresh&&cur().join("|")===[s[0].join(","),s[1].join(",")].join("|");
 B.querySelector(".hd .cols").innerHTML=[...Array(n)].map((_,k)=>`<i>S${k+1}</i>`).join("")+(keep&&B.querySelector(".gp")?"<i>Pts</i>":"");
 rows().forEach((r,i)=>{const gp=r.querySelector(".gp"),c=r.querySelector(".cols");
  c.innerHTML=s[i].map((x,k)=>{const y=s[1-i][k];return `<span class="${k==n-1?"cur":x>y?"on":""}">${x}${t[i]&&t[i][k]!=null&&x==6&&y==7?`<sup>${t[i][k]}</sup>`:""}</span>`}).join("");
  if(gp&&keep)c.appendChild(gp);if(sv!=null)r.classList.toggle("sv",sv===i)});
 if(!keep){const nt=B.querySelector(".nt");if(nt)nt.remove()}
 let sa=0,sb=0,ta=0,tb=0;for(let k=0;k<n;k++){const x=s[0][k],y=s[1][k];if(k<n-1&&done(x,y)){x>y?sa++:sb++}if(x==7&&y==6)ta++;if(y==7&&x==6)tb++}
 stat("sets",sa,sb);stat("games",s[0].reduce((p,q)=>p+q,0),s[1].reduce((p,q)=>p+q,0));stat("tbs",ta,tb);
 if(S)S.innerHTML='<span class="dot"></span> In progress · live score, updated '+new Date(j.ts).toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit",second:"2-digit"})}
tick();const T=setInterval(tick,30000);document.addEventListener("visibilitychange",tick)})()</script>"""


def live_page(m, results, tr, tx, tslugs=()):
    import site_ui                                  # antes de qualquer uso (há outro import mais abaixo na função)
    tr = dict(tr, _tx=tx)
    d = _load(LIVE_FILE, {})
    when = time.strftime("%H:%M", time.gmtime(d.get("ts", time.time())))
    a, b = m["p1"], m["p2"]
    ga, gb = m["games"]
    tname = m.get("tournament", "")
    ts = webapp.slugify(webapp.base_tournament(tname))
    back = f'<p><a href="/t/{ts}.html">← {esc(tname)}</a></p>' if ts in tslugs else '<p><a href="/">← Home</a></p>'
    surf = tr["surfaces"].get(m.get("surface"), "") if m.get("surface") else ""
    fmt = {"BO3": "Best of 3", "BO5": "Best of 5"}.get(m.get("format") or "", "")
    io = {True: "Indoor", False: "Outdoor"}.get(m.get("indoor"), "")
    meta = " · ".join(x for x in [m.get("round", ""), surf, io, m.get("court") or "", fmt] if x)
    since = ""
    la = m.get("live_at") or ""
    try:
        t0 = dt.datetime.fromisoformat(la.replace("Z", "+00:00"))
        mins = int((d.get("ts", time.time()) - t0.timestamp()) // 60)
        if 0 < mins < 8 * 60:
            since = (f" · started {site_ui.ltime(la, t0.strftime('%H:%M') + ' UTC')} " + (f"({mins // 60}h {mins % 60:02d}m)" if mins >= 60 else f"({mins} min)"))
    except ValueError:
        pass
    head = (f'<section class="page-h">{back}<h1>{(f"<span class=tag>{esc(m.get("tag", ""))}</span> ") if m.get("tag") else ""}'
            f'{esc(a["name"])} <span style="color:var(--s);font-weight:400">vs</span> {esc(b["name"])}</h1><p>{esc(meta)}</p>'
            f'<p class="lstat"><span class="dot"></span> In progress{since} · checking the live score…</p></section>')
    pts = m.get("points") or []
    has_pts = isinstance(pts, list) and len(pts) == 2 and any(str(x) not in ("", "0", "None") for x in pts)
    has_pts = has_pts and time.time() - d.get("ts", 0) < 600          # pontos com mais de 10 min enganam: não se mostram
    n = max(len(ga), len(gb))
    import site_ui
    pls = [{"name": plink(p["name"]), "sub": who_html(p, True), "av": webapp.avatar(p["name"], "av"), "serve": m.get("server") == i}
           for i, p in ((1, a), (2, b))]
    note = f'Points as of {when} UTC' if has_pts else ""
    board = (site_ui.scoreboard(pls, [ga, gb], None, pts if has_pts else None, live=True, note=note,
                                attrs=f'data-a="{esc(a["name"])}" data-b="{esc(b["name"])}" data-pt="{int(d.get("ts", 0))}" data-w="{when}"')
             + match_stats_html(a, b, ga, gb, None, results, live=True) + LIVEPAGE_JS)
    # quem vai à frente (sets e depois jogos do set em curso)
    sw = [sum(1 for k in range(n - 1) if k < len(ga) and k < len(gb) and (ga, gb)[j][k] > (gb, ga)[j][k]) for j in (0, 1)]
    cur = (ga[-1] if ga else 0, gb[-1] if gb else 0)
    # só conta como "à frente" com mais sets, ou com 2+ jogos de vantagem no set em curso (evita avisos ao 2-1 do primeiro set)
    lead = (1 if sw[0] > sw[1] else 2 if sw[1] > sw[0] else
            1 if cur[0] - cur[1] >= 2 else 2 if cur[1] - cur[0] >= 2 else 0)
    ra, rb = a.get("rank"), b.get("rank")
    upset = ""
    if lead and isinstance(ra, int) and isinstance(rb, int) and ra > 0 and rb > 0:
        lr, tr_ = (ra, rb) if lead == 1 else (rb, ra)
        if lr - tr_ >= 20:
            upset = (f'<div class="upw"><b>Upset watch</b> {esc((a if lead == 1 else b)["name"])} (#{lr}) leads '
                     f'{esc((b if lead == 1 else a)["name"])} (#{tr_})</div>')
    # caminho até este jogo (rondas anteriores neste torneio, nos últimos 14 dias)
    cut = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 14 * 86400))
    road = ""
    for p in (a, b):
        ps = webapp.slugify(p["name"])
        ms = [r for r in results if r.get("date", "") >= cut and r.get("winner") in (1, 2)
              and webapp.slugify(webapp.base_tournament(r.get("tournament", ""))) == ts
              and ps in (webapp.slugify(r["p1"]["name"]), webapp.slugify(r["p2"]["name"]))]
        ms.sort(key=lambda r: (r.get("date", ""), -webapp._round_rank(r.get("round"))), reverse=True)
        if ms:
            road += f'<h3 class="lrh">{esc(p["name"])}</h3><section class="tg">' + "".join(webapp.match_html(r, tr) for r in ms[:5]) + "</section>"
    road = f'<h2 class="dh">Road to this match</h2>{road}' if road else ""
    players = f'<h2 class="dh">The players</h2><div class="lpg">{_pcard(a)}{_pcard(b)}</div>'
    # quadro (quartos até à final) com os jogos que temos deste torneio + os que estão a decorrer agora
    g_ = m.get("gender")
    same = lambda r: (webapp.slugify(webapp.base_tournament(r.get("tournament", ""))) == ts
                      and (not g_ or webapp.classify(r)[0] in (None, g_)))
    tsing = [r for r in results if r.get("date", "") >= cut and r.get("winner") in (1, 2) and same(r)
             and webapp.classify(r)[1] == "singles"]
    today = time.strftime("%Y-%m-%d", time.gmtime())
    for x in live_rows():
        if webapp.slugify(webapp.base_tournament(x.get("tournament", ""))) == ts and (not g_ or x.get("gender") in (None, g_)):
            tsing.append({"id": x["id"], "date": today, "round": x.get("round", ""), "tournament": x.get("tournament", ""),
                          "p1": x["p1"], "p2": x["p2"], "games": x["games"], "_live": True})
    _skip = {str(r.get("id")) for r in results} | {str(x.get("id")) for x in live_rows()}
    tsing += webapp.scheduled_for(tname, _load("upcoming.json", {}).get("matches", []), _skip, g_)
    tsing.sort(key=lambda r: (r.get("date", ""), -webapp._round_rank(r.get("round"))), reverse=True)
    draw = webapp.bracket_html(tsing, tr, tx) if tx.get("f_bracket") else ""
    if draw:
        draw += (f'<p class="topw"><a class="lmore" href="/t/{ts}.html">All results from {esc(tname)} →</a></p>' if ts in tslugs else "")
    follow = ""
    refresh = ('<script>(function(){var t0=Date.now(),P=300000;function go(){if(!document.hidden)location.reload()}'
               'setInterval(go,P);document.addEventListener("visibilitychange",function(){if(!document.hidden&&Date.now()-t0>P)location.reload()})})();</script>')
    try:
        import tennis_videos
        g0, _k, lv0, tg0 = webapp.classify(m) if m.get("p1") else (None, None, None, "")
        watch = tennis_videos.watch_block(tname, m.get("tag") or tg0, m.get("gender") or g0, lv0)
    except Exception as e:
        print("Watch live falhou:", m.get("id"), e)
        watch = ""
    return head + board + watch + upset + players + draw + road + follow + refresh


# ---------- ordem de jogo (fixtures.json) ----------
def order_of_play_page(results):
    d = _load("fixtures.json", {})
    rows = d.get("matches") or []
    try:                                           # ATP/WTA (e WTA 125) pelo ESPN: nomes completos, court, hora e resultado; substitui os da API
        import espn_sync
        er = espn_sync.oop_rows()
        if er:
            seen = {k for x in er for k in espn_sync._pair_keys(x["p1"]["name"], x["p2"]["name"])}
            rows = [x for x in rows if not any(k in seen for k in espn_sync._pair_keys(x["p1"]["name"], x["p2"]["name"]))] + er
    except Exception as e:
        print("Ordem de jogo (ESPN): erro", e)
    done = {str(r.get("id")): r for r in results}
    live = {str(m.get("id")) for m in live_rows()}
    today = time.strftime("%Y-%m-%d", time.gmtime())
    days = {}
    for x in rows:
        day = x.get("day") or (x.get("t") or "")[:10]
        if day < today:
            continue
        days.setdefault(day, {}).setdefault((x.get("tour") or "", x.get("tp") or ""), []).append(x)
    LV = {"atp": 0, "wta": 1, "challenger": 2, "itf": 3}
    body = ""
    for day in sorted(days)[:3]:
        label = "Today" if day == today else dt.date.fromisoformat(day).strftime("%A %d %B")
        body += f'<h2 class="dh">{esc(label)}</h2>'
        for (tour, tp), ms in sorted(days[day].items(), key=lambda kv: (LV.get(kv[0][0], 9), kv[0][1])):
            items = ""
            for x in sorted(ms, key=lambda x: (x.get("t") or "", webapp._round_rank(x.get("round")))):
                mid = str(x.get("id"))
                t = x.get("t") or ""
                st = str(x.get("status") or "").lower()
                r = done.get(mid)
                s_, tb_, w = x.get("s"), x.get("tb"), x.get("w") or 0
                if r and r.get("games"):
                    s_, tb_, w = r["games"], r.get("tb"), r.get("winner") or 0
                is_live = mid in live or st == "live"
                if is_live:
                    badge, w = '<span class="lvb">LIVE</span>', 0
                elif r or st == "completed":
                    badge = '<span class="ft">Final</span>'
                elif st in ("", "scheduled", "upcoming", "not_started"):
                    badge = ""
                else:
                    badge = f'<span class="ft">{esc(st.title())}</span>'
                href = f"/live/{mid}.html" if mid in live else f"/m/{mid}.html" if r else ""
                tm = (f'<time class="lt" datetime="{esc(t)}">{esc(t[11:16])}</time><small>UTC</small>' if len(t) >= 16
                      else '<b>TBC</b><small>time</small>')
                pls = []
                for i in (1, 2):
                    p = x["p%d" % i]
                    sub = f'{_fl(p.get("country"), 11)}{("#" + str(p["rank"])) if isinstance(p.get("rank"), int) else ""}'
                    ch = site_ui.chips(s_[i - 1], s_[2 - i], (tb_ or [[], []])[i - 1], done=not is_live) if s_ and s_[0] else '<div class="sc"></div>'
                    pls.append((f'<span class="nm">{esc(p.get("name") or "")}</span>', sub, ch, ("w" if w == i else "l") if w in (1, 2) else ""))
                items += site_ui.match_tile(tm, x.get("round") or "", pls, badge, href, x.get("court") or "",
                                            f'data-a="{esc(x["p1"]["name"])}" data-b="{esc(x["p2"]["name"])}"', live=is_live)
            tag = {"atp": "ATP", "wta": "WTA", "challenger": "Challenger", "itf": "ITF"}.get(tour, tour.upper())
            if tour == "challenger" and ms and ms[0].get("gender") == "women":
                tag = "WTA 125"
            body += f'<h3 class="opt"><span class="tag">{esc(tag)}</span><span>{esc(tp)}</span></h3><div class="ui-mts">{items}</div>'
    if not body:
        body = '<p class="empty">The order of play is not out yet. Check back later.</p>'
    upd = time.strftime("%H:%M UTC", time.gmtime(d["ts"])) if d.get("ts") else ""
    js = ('<script>document.querySelectorAll("time.lt[datetime]").forEach(function(e){var d=new Date(e.getAttribute("datetime"));'
          'if(!isNaN(d))e.textContent=d.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",hour12:false})});</script>' + OOP_LIVE_JS)
    return (f'<section class="page-h"><h1>Order of play</h1><p>Start times for the next matches on the ATP, WTA, Challenger and ITF tours, '
            f'in your local time. Updated {esc(upd)}; times can change through the day. ATP and WTA scores update live.</p></section>{body}{js}')


OOP_LIVE_JS = r"""<script>(()=>{const R=[...document.querySelectorAll(".ui-mt[data-a]")];if(!R.length)return;
const nk=s=>(s||"").normalize("NFKD").replace(/[^A-Za-z\s-]/g,"").toLowerCase().split(/[\s-]+/).filter(Boolean);
const ks=s=>{const w=nk(s);return w.length?[w.join(""),w[0][0]+w[w.length-1]]:[]};const same=(a,b)=>{const A=ks(a);return ks(b).some(k=>A.includes(k))};
const ch=(a,o,t)=>a.map((x,i)=>`<span class="${i<a.length-1&&x>o[i]?"on":""}">${x}${t&&t[i]!=null&&x==6&&o[i]==7?`<sup>${t[i]}</sup>`:""}</span>`).join("");
let miss=0;const again=()=>{if(++miss<=6)setTimeout(tick,5000);else if(!seen&&S)S.innerHTML='<span class="dot"></span> In progress · live score unavailable right now · last update '+B.dataset.w+' UTC'};
async function tick(){if(document.hidden)return;let j;try{const r=await fetch("/api/tennis/live",{cache:"no-store"});if(!r.ok)return again();j=await r.json()}catch(e){return again()}
 for(const m of j.matches||[])for(const c of R){const a=c.dataset.a,b=c.dataset.b,f=same(a,m.p[1].n)&&same(b,m.p[0].n);if(!(f||(same(a,m.p[0].n)&&same(b,m.p[1].n))))continue;
  const s=f?[m.s[1],m.s[0]]:m.s,t=f?[m.tb[1],m.tb[0]]:m.tb,z=c.querySelectorAll(".pl .sc");
  if(z.length==2){z[0].innerHTML=ch(s[0],s[1],t[0]);z[1].innerHTML=ch(s[1],s[0],t[1])}
  c.classList.add("live");const sb=c.querySelector(".sb");if(sb)sb.innerHTML='<span class="lvb">LIVE</span>';break}}
tick();const T=setInterval(tick,30000);document.addEventListener("visibilitychange",tick)})()</script>"""


def order_of_play_ld(site_base):
    """Dados estruturados (schema.org SportsEvent) dos jogos marcados, para o Google poder mostrar a hora do jogo."""
    out = []
    now = time.strftime("%Y-%m-%dT%H:%M", time.gmtime())
    live = {str(m.get("id")) for m in live_rows()}
    for x in _load("fixtures.json", {}).get("matches", []):
        a, b, t = x["p1"]["name"], x["p2"]["name"], x.get("t") or ""
        if len(t) < 16 or (t < now and str(x.get("id")) not in live) or "." in a.split()[0] or "." in b.split()[0]:
            continue
        ts = webapp.slugify(webapp.base_tournament(x.get("tp") or ""))
        ev = {"@context": "https://schema.org", "@type": "SportsEvent", "name": f"{a} vs {b}" + (f", {x['tp']}" if x.get("tp") else ""),
              "sport": "Tennis", "startDate": t, "eventStatus": "https://schema.org/EventScheduled",
              "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
              "location": {"@type": "Place", "name": x.get("tp") or "Tennis court"},
              "competitor": [{"@type": "Person", "name": a}, {"@type": "Person", "name": b}],
              "url": f"{site_base}/live/{x['id']}.html" if str(x.get("id")) in live else f"{site_base}/order-of-play.html",
              "description": " · ".join(v for v in [x.get("round"), x.get("tp")] if v)}
        if ts:
            ev["superEvent"] = {"@type": "SportsEvent", "name": x.get("tp"), "url": f"{site_base}/t/{ts}.html"}
        out.append(ev)
        if len(out) >= 40:
            break
    return out


# ---------- páginas de torneio: a jogar agora + campeões anteriores ----------
def _hist_all():
    hist_entry("")                                  # garante que _HIST está carregado
    return _HIST or {}


def tournament_extras(name, gender):
    ts = webapp.slugify(webapp.base_tournament(name))
    live = [m for m in live_rows() if webapp.slugify(webapp.base_tournament(m.get("tournament", ""))) == ts
            and (not gender or not m.get("gender") or m.get("gender") == gender)]
    out = ""
    if live:
        cards = ""
        for m in live:
            a, b = m["p1"], m["p2"]
            sa = "".join(f"<span>{int(x)}</span>" for x in m["games"][0])
            sb = "".join(f"<span>{int(x)}</span>" for x in m["games"][1])
            cards += (f'<a class="lv" href="/live/{m["id"]}.html"><div class="lh">{esc(m.get("round", ""))}<span class="lgo">›</span></div>'
                      f'<div class="pl"><div class="who"><div><span class="nm">{esc(a["name"])}</span><small>{who_html(a, True)}</small></div></div><div class="sc">{sa}</div></div>'
                      f'<div class="pl"><div class="who"><div><span class="nm">{esc(b["name"])}</span><small>{who_html(b, True)}</small></div></div><div class="sc">{sb}</div></div></a>')
        out += f'<h2 class="dh"><span class="dot" style="display:inline-block;margin-right:8px"></span>Playing now</h2><div class="lvg">{cards}</div>'
    champs = ""
    g = {"men": "m", "women": "w"}.get(gender or "")
    fins = [f for f in _hist_all().get("finals") or [] if webapp.slugify(re.sub(r"\s+CH$", "", f.get("t") or "")) == ts
            and (not g or f.get("g") == g)]
    fins.sort(key=lambda f: f.get("d", ""), reverse=True)
    if fins:
        seen, rows = set(), ""
        for f in fins:
            y = (f.get("d") or "")[:4]
            if y in seen:
                continue
            seen.add(y)
            wr = f" <small>#{f['wr']}</small>" if f.get("wr") else ""
            rows += (f'<tr><td class="pn">{esc(y)}</td><td><b>{plink(f.get("w"))}</b>{wr}</td>'
                     f'<td class="mut2">d. {plink(f.get("l"))} {esc(f.get("sc") or "")}</td></tr>')
            if len(seen) >= 10:
                break
        champs = (f'<h2 class="dh">Past champions</h2><table class="pt"><tbody>{rows}</tbody></table>'
                f'<p class="cr">Finals to {esc(data_to() or "mid-2026")}: Tennis Abstract / Jeff Sackmann, CC BY-NC-SA 4.0.</p>')
    return out, champs


# ---------- destaques ----------
def highlights(results, ranks, tr, tx, days=7):
    tr = dict(tr, _tx=tx)
    today = dt.datetime.now(dt.timezone.utc).date()
    start = (today - dt.timedelta(days=days - 1)).isoformat()
    best, gap = None, 0
    for r in results:
        if r.get("date", "") < start or webapp.classify(r)[1] != "singles" or r.get("winner") not in (1, 2):
            continue
        if not webapp.match_stats(r):
            continue
        wn, ls = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
        if isinstance(wn.get("rank"), int) and isinstance(ls.get("rank"), int):
            g = wn["rank"] - ls["rank"]
            if g > gap and g >= 40:
                best, gap = r, g
    out = ""
    if best:
        wn_ = best["p%d" % best["winner"]]["name"]
        out += (f'<h2 class="sec"><span>{esc(L(tx, "x_upset"))}</span></h2>{webapp.avatar(wn_, "avl") if webapp.slugify(wn_) in webapp.AVATARS else ""}'
                f'<p class="topw">{esc(L(tx, "x_upset_line", a=best["p%d" % best["winner"]]["rank"], b=best["p%d" % (3 - best["winner"])]["rank"], g=gap))}</p>'
                f'<section class="tg">{webapp.match_html(best, tr)}</section>')
    cutoff = (today - dt.timedelta(days=30)).isoformat()
    rise = [v for v in (ranks or {}).values()
            if v.get("prev") and v["rank"] < v["prev"] and v.get("date", "") >= cutoff and v["prev"] - v["rank"] >= 5]
    rise.sort(key=lambda v: -(v["prev"] - v["rank"]))
    if rise:
        items = "".join(
            f'<div class="rs">{webapp.avatar(v["name"])}<span class="nm">{esc(v["name"])}</span> <small>{esc((v.get("country") or "").upper())}</small>'
            f'<b>#{v["prev"]} → #{v["rank"]}</b></div>' for v in rise[:5])
        out += f'<h2 class="sec"><span>{esc(L(tx, "x_climbing"))}</span></h2><div class="rsg">{items}</div>'
    return out


# ---------- newsletter ----------
def newsletter_block(tx=None):
    url = os.environ.get("NEWSLETTER_URL", "").strip()
    user = re.sub(r"[^A-Za-z0-9_-]", "", os.environ.get("NEWSLETTER_USER") or "")
    if user and not url:
        url = f"https://buttondown.com/api/emails/embed-subscribe/{user}"       # Buttondown (gratuito): só precisas do utilizador
    if not url.startswith("https://"):
        return ""
    return (f'<section class="nl"><h2>{esc(L(tx, "x_nl_h"))}</h2><p>{esc(L(tx, "x_nl_p"))}</p>'
            f'<form action="{esc(url)}" method="post" target="_blank"><input type="email" name="email" required '
            f'placeholder="you@example.com" aria-label="Email"><input type="hidden" name="embed" value="1"><button type="submit">{esc(L(tx, "x_subscribe"))}</button></form></section>')


def ticker(results, n=16):
    """Faixa com os últimos resultados a passar na página de entrada (links para a página de cada jogo, quando existe)."""
    cut = (dt.date.today() - dt.timedelta(days=45)).isoformat()
    rows = [r for r in results if r.get("winner") in (1, 2) and r.get("games") and not r.get("q")][:n]
    if len(rows) < 4:
        return ""
    items = ""
    for r in rows:
        w = r["winner"]
        sc = " ".join(f"{a}-{b}" for a, b in zip(r["games"][w - 1], r["games"][2 - w]))
        txt = (f'<b>{esc(r["p%d" % w]["name"])}</b> d. {esc(r["p%d" % (3 - w)]["name"])} <em>{esc(sc)}</em>'
               f' · {esc(webapp.base_tournament(r.get("tournament", "")))}')
        link = r.get("id") is not None and (r.get("date") or "") >= cut
        items += (f'<a class="tk" href="/m/{r["id"]}.html">{txt}</a>' if link else f'<span class="tk">{txt}</span>')
    return f'<div class="tick" aria-label="Latest results"><div class="tw">{items}<span aria-hidden="true">{items}</span></div></div>'


EXTRA_CSS = """
.court{position:relative;height:110px;margin:-6px auto 6px;max-width:520px}
.court .cl{position:absolute;left:0;right:0;bottom:18px;height:2px;background:var(--e)}
.court .net{position:absolute;left:50%;bottom:18px;width:3px;height:44px;background:var(--s);opacity:.55}
.court .ball{position:absolute;bottom:20px;left:4%;width:20px;height:20px;border-radius:50%;background:var(--v);box-shadow:0 0 16px rgba(217,242,61,.45);
  animation:bx 2.6s linear infinite alternate,by .65s cubic-bezier(.3,0,.7,1) infinite alternate}
.court .bsh{position:absolute;bottom:12px;left:4%;width:20px;height:6px;border-radius:50%;background:#000;opacity:.3;animation:bx 2.6s linear infinite alternate}
@keyframes bx{from{left:4%}to{left:92%}}
@keyframes by{from{bottom:20px}to{bottom:90px}}
.hero .hw{display:inline-block;animation:hpop .6s both}
@keyframes hpop{from{opacity:0;transform:translateY(10px) scale(.85)}to{opacity:1;transform:none}}
.hero .hfade{animation:hfade .8s .9s both}
@keyframes hfade{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
.tick{overflow:hidden;white-space:nowrap;border-top:1px solid var(--e);border-bottom:1px solid var(--e);background:var(--deep);padding:12px 0;margin:4px 0 30px}
.tick .tw{display:inline-block;animation:marq 70s linear infinite}
.tick .tk{margin:0 24px;color:var(--c);font-size:.95rem;text-decoration:none}.tick a.tk:hover{color:var(--v)}
.tick .tk em{color:var(--v);font-style:normal;font-weight:700}
.tick:hover .tw{animation-play-state:paused}
@keyframes marq{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){.court .ball,.court .bsh,.tick .tw,.hero .hw,.hero .hfade{animation:none!important}}

.sb td,.sb th{text-align:center}.pt.sb th:last-child{display:table-cell}.sb td.pn{text-align:left}.sb .wn{color:var(--v);font-weight:700}.sb tr.win .pn{color:var(--c)}
.up{color:var(--v);font-weight:700}.dn{color:#ff9a8a;font-weight:700}
.av{width:26px;height:26px;border-radius:50%;object-fit:cover;vertical-align:middle;margin-right:8px;border:1px solid var(--e);background:var(--deep)}
.avl{width:84px;height:84px;border-radius:50%;object-fit:cover;border:2px solid var(--v);margin:6px 0}
.ph{display:flex;gap:16px;align-items:center}.ph h1{margin:0}.ph p{margin:2px 0}
.cr{font-size:.72rem;color:var(--s)}.cr a{color:var(--s)}

a.nm{text-decoration:none;color:inherit}a.nm:hover{text-decoration:underline}
.form i{font-style:normal;font-size:.9rem;margin:0 1px;padding:1px 5px;border-radius:6px}
.fw{background:var(--v);color:var(--g)}.fl{border:1px solid var(--e);color:var(--s)}
.sfs{display:flex;flex-wrap:wrap;gap:6px 16px;color:var(--s);margin:6px 0}.sfs b{color:var(--c)}
.lvg{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin-bottom:10px}
.lv{background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:10px 14px}
.lv .lh{font-size:.74rem;color:var(--s);margin-bottom:4px}
.lv .pl{display:flex;justify-content:space-between;align-items:center;padding:3px 0}
.lv .who{display:flex;align-items:center;gap:8px;min-width:0;flex:1}.lv .who>div{min-width:0}.lv .who .nm{display:block;line-height:1.2}.lv .who small{display:block;margin:0}.lv .sc{display:flex;gap:4px;white-space:nowrap;margin-left:8px;font:700 .95rem Georgia,serif;color:var(--v)}.lv .sc span{min-width:1.3em;text-align:center}
.sec small{color:var(--s);font-weight:400;font-size:.75rem}
@media(max-width:480px){nav div a{margin-left:11px;font-size:.86rem}nav .brand{font-size:1rem;letter-spacing:.16em}}
.lv.rt .sc{animation:lvp 1s}.lv .sc sup{font-size:.6em;margin-left:1px;color:var(--s)}@keyframes lvp{from{opacity:.4}to{opacity:1}}
a.lv{display:block;text-decoration:none;color:inherit;transition:border-color .15s}a.lv:hover{border-color:var(--v)}
.lv .lh{display:flex;align-items:center;gap:4px}.lv .lgo{margin-left:auto;color:var(--v);font-size:1.1rem;line-height:1}
.lstat{display:flex;align-items:center;gap:8px;font-size:.85rem;margin-top:8px!important}.lstat .dot{display:inline-block}
.lsb td.gp{color:var(--v);font-weight:700;border-left:1px solid var(--e)}.srv{color:var(--v);font-size:.7rem;margin-left:6px;vertical-align:2px}
.lsb small{display:block;color:var(--s);margin-top:2px}
.upw{background:var(--v);color:var(--g);border-radius:14px;padding:10px 14px;margin:12px 0;font-weight:600}.upw b{text-transform:uppercase;letter-spacing:.08em;font-size:.8rem;margin-right:6px}
.lpg{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.lpc{background:var(--deep);border:1px solid var(--e);border-radius:18px;padding:14px 16px}.lpc h3{margin:0;font:700 1.25rem Georgia,serif}.lpc h3 a{text-decoration:none}
.lpc .ph{align-items:center}.lpc .numgrid{grid-template-columns:repeat(3,1fr);gap:8px}.lpc .nbox{padding:10px 6px}.lpc .nbox b{font-size:1.35rem}.lpc .nbox span{font-size:.62rem}.lsb .pn a{text-decoration:none}.lpc p{margin:2px 0;color:var(--s)}.lpc .numgrid{margin:10px 0 4px}.lmore{color:var(--v);font-size:.9rem;text-decoration:none}
.rpts{color:var(--s);font-size:.85em}
.ops{display:grid;gap:2px}.op{display:flex;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid var(--e)}.op:last-child{border:0}
.op time{min-width:58px;font:700 .95rem system-ui;color:var(--v)}.opm{flex:1;min-width:0}.opm small{color:var(--s)}.mut2{color:var(--s);font-size:.85rem}.rktabs{display:flex;gap:6px;margin:12px 0}.rkt{flex:1;padding:10px;border-radius:999px;border:1px solid var(--e);background:none;color:var(--c);font-weight:700;cursor:pointer}.rkt.on{background:var(--v);color:var(--g);border-color:var(--v)}.rkcs{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}.rkc{display:flex;align-items:center;gap:10px;background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:10px 14px}.rkc>div{flex:1;min-width:0}.rkc small{display:block;color:var(--s)}.rkc .up{font-weight:700}.rk td:first-child{font-weight:700;color:var(--v);width:2.6em}.rk .eq{color:var(--s)}.rk .up{color:var(--v)}.rk .dn{color:#f3a0a0}.dch{margin:6px 0 0;color:var(--s)}.dch b{color:var(--c)}.dcs{font-size:.8rem;margin-left:6px;padding:2px 8px;border-radius:999px;border:1px solid var(--e)}.dcs.up{color:var(--v)}.dcs.dn{color:#f3a0a0}.ch b sup,.pt td sup,.bm b sup{font-size:.62em;margin-left:1px;opacity:.75;font-weight:600}.opt{display:flex;align-items:center;gap:8px;margin:18px 0 8px;font:700 1.05rem system-ui}.osc{color:var(--v);margin-left:6px;font-size:.9rem;white-space:nowrap}
.ogo{color:var(--v);text-decoration:none;font-size:1.3rem;padding:0 4px}.tag.olive{background:var(--v);color:var(--g)}
.ssn{margin:8px 0 6px!important;color:var(--c)!important;font-size:.92rem}.ssn span{color:var(--v);font-weight:700;text-transform:uppercase;letter-spacing:.08em;font-size:.72rem;margin-right:6px}
.lrh{font:700 .8rem system-ui;text-transform:uppercase;letter-spacing:.1em;color:var(--s);margin:14px 0 6px}
.rsg{display:grid;gap:6px;margin-bottom:16px}
.rs{display:flex;gap:8px;align-items:baseline;background:var(--deep);border:1px solid var(--e);border-radius:12px;padding:8px 14px}
.rs b{margin-left:auto;color:var(--v)}
.nl{background:var(--deep);border:1px solid var(--e);border-radius:18px;padding:18px;margin:26px 0;text-align:center}
.nl h2{margin:0 0 6px;font:700 1.25rem Georgia,serif}.nl p{color:var(--s);margin:0 0 12px}
.nl form{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.nl input{flex:1 1 200px;max-width:320px;padding:10px 14px;border-radius:999px;border:1px solid var(--e);background:var(--g);color:var(--c)}
.nl button{background:var(--v);color:var(--g);border:0;border-radius:999px;padding:10px 18px;font:700 .9rem system-ui;cursor:pointer}
"""


SPOT_CSS = """.ui-spot{display:grid;grid-auto-flow:column;grid-auto-columns:150px;gap:10px;overflow-x:auto;padding:2px 0 12px;scroll-snap-type:x mandatory;scrollbar-width:none}
.ui-spot::-webkit-scrollbar{display:none}
.ui-spot a{position:relative;display:block;aspect-ratio:4/5;border-radius:18px;overflow:hidden;border:1px solid var(--e);scroll-snap-align:start;text-decoration:none;
background:radial-gradient(120% 90% at 80% 10%,var(--e) 0,var(--deep) 65%)}
.ui-spot img{width:100%;height:100%;object-fit:cover;object-position:50% 18%;display:block}
.ui-spot .ini{position:absolute;inset:0;display:grid;place-items:center;font:800 3.4rem Georgia,serif;color:var(--v);opacity:.25}
.ui-spot .ov{position:absolute;left:0;right:0;bottom:0;padding:34px 10px 10px;background:linear-gradient(180deg,transparent,rgba(0,0,0,.78))}
.ui-spot b{display:block;font:800 .95rem/1.15 Georgia,serif;color:#fff}
.ui-spot small{display:block;margin-top:3px;font:700 .68rem system-ui;color:#e6ece8;letter-spacing:.02em}
.ui-spot .rk{position:absolute;top:8px;left:8px;background:var(--v);color:var(--g);font:800 .78rem system-ui;border-radius:999px;padding:3px 9px}
@media(min-width:760px){.ui-spot{grid-auto-columns:calc(16.66% - 9px)}}"""


def spotlight_players(n=8, lo=7.5, hi=25):
    """Jogadores que o Google já mostra perto da 1.ª página (posição lo–hi nas pesquisas de gsc.json), por aparições.
    Só jogadores com página no site (LINKABLE). Devolve [(slug, nome, aparições, posição média)]. (SEO, 7/11/2026)"""
    try:
        qs = _load("gsc.json", {}).get("queries") or []
    except Exception:
        qs = []
    names = {}
    for sl in LINKABLE:
        e = PIDX.get(sl)
        if e and e.get("name"):
            names[sl] = e["name"]
    by_set, by_ini = {}, {}
    for sl, nm in names.items():
        t = [x for x in re.split(r"[\s\-]+", nm.lower()) if x]
        if len(t) >= 2:
            by_set.setdefault(frozenset(t), sl)
            by_ini.setdefault((t[0][0], t[-1]), set()).add(sl)
    agg = {}
    for q in qs:
        pos, imp = q.get("position") or 99, q.get("impressions") or 0
        if not (lo <= pos <= hi):
            continue
        t = [x for x in re.split(r"[\s\-]+", (q.get("q") or "").lower().replace(".", " "))
             if x and x not in ("ranking", "rankings", "tennis", "wta", "atp", "live", "stats", "results") and not x.isdigit()]
        sl = by_set.get(frozenset(t)) if len(t) >= 2 else None
        if not sl and len(t) == 2:
            for a, b in ((t[0], t[1]), (t[1], t[0])):      # "a parks" / "parks a" -> Alycia Parks, só se for único
                c = by_ini.get((a[0], b)) if len(a) == 1 else None
                if c and len(c) == 1:
                    sl = next(iter(c))
        if sl:
            x = agg.setdefault(sl, [0, 0.0])
            x[0] += imp
            x[1] += imp * pos
    out = [(sl, names[sl], v[0], v[1] / v[0]) for sl, v in agg.items() if v[0]]
    out.sort(key=lambda x: -x[2])
    return out[:n]


def spotlight_block():
    """Bloco da página inicial: jogadores que estão a ser procurados e que estão quase na 1.ª página do Google.
    Ligações a partir da página inicial dão força a essas páginas."""
    import site_ui
    import site_more
    rows = spotlight_players()
    if len(rows) < 3:
        return ""
    cards = ""
    for sl, nm, _imp, _pos in rows:
        rk = (RANKS.get(sl) or {}).get("rank") or (PIDX.get(sl) or {}).get("rank")
        img = (f'<img src="/img/big/{sl}.jpg" alt="{esc(nm)}" loading="lazy" width="150" height="188">' if sl in webapp.AVATARS
               else f'<span class="ini">{esc("".join(w[0] for w in nm.split()[:2]).upper())}</span>')
        c = site_more.country_name((PIDX.get(sl) or {}).get("country") or "")
        cards += (f'<a href="/p/{sl}.html">{img}{f"<span class=rk>No. {rk}</span>" if isinstance(rk, int) else ""}'
                  f'<span class="ov"><b>{esc(nm)}</b><small>{esc(c) if c else "Ranking &amp; results"}</small></span></a>')
    return f'<style>{SPOT_CSS}</style>' + site_ui.sec("Players in the spotlight", "/players.html", "All players") + f'<div class="ui-spot">{cards}</div>'


ABOUT_CSS = """.ab h2{font:800 1.15rem Georgia,serif;color:var(--v);margin:26px 0 8px}.ab p,.ab li{line-height:1.65;color:var(--c);max-width:68ch}
.ab ul{padding-left:18px;margin:6px 0}.ab li{margin:4px 0}.ab a{color:inherit;text-decoration:underline;text-decoration-color:var(--s);text-underline-offset:3px}
.ab .lead{font-size:1.08rem}.ab .ig{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}.ab .ig a{text-decoration:none;background:var(--v);color:var(--g);
font:800 .9rem system-ui;border-radius:999px;padding:8px 14px}"""


def about_page():
    """Página "About Beyond100" (SEO / confiança, 7/11/2026): o que é, como funciona, de onde vêm os dados, contacto.
    Sem dados pessoais."""
    return (f'<style>{ABOUT_CSS}</style><section class="page-h"><h1>About Beyond100</h1></section><div class="ab">'
            '<p class="lead">Beyond100 follows the tennis that the big sites skip: Challenger, ITF and WTA 125 events, the players ranked '
            'outside the top 100 and the ones about to break in. Every result gets a page, every player gets a profile, and the best '
            'stories of the day go out on Instagram. Padel gets the same treatment, from Premier Padel to the FIP Tour.</p>'
            '<h2>What you will find</h2><ul>'
            '<li><a href="/results.html">Results</a>, <a href="/order-of-play.html">order of play</a> and live scores, newest first.</li>'
            '<li><a href="/players.html">Player pages</a> with the current ranking, career high, career record, form and every match we tracked.</li>'
            '<li><a href="/road.html">Road to the Top 100</a>, <a href="/power.html">Power Ranking</a> and <a href="/records.html">season records</a>.</li>'
            '<li><a href="/padel/">Padel</a>: results, rankings, pairs and an Elo rating for every player.</li></ul>'
            '<h2>How it works</h2>'
            '<p>The site updates itself every hour, and within minutes when a match we follow finishes. Rankings change as soon as new '
            'ones are published. The short summaries on player pages are written from the numbers and nothing else: if we do not have '
            'a figure, it is left out rather than guessed.</p>'
            '<h2>Where the data comes from</h2><ul>'
            '<li>Scores come from live match data feeds and can arrive late or, now and then, wrong. Tell us and we fix it.</li>'
            '<li>Career history up to mid-2026: <a href="https://www.tennisabstract.com">Tennis Abstract</a> / Jeff Sackmann, CC BY-NC-SA 4.0.</li>'
            '<li>Padel results, rankings and draws: <a href="https://padelapi.org">Padel API</a>.</li>'
            '<li>Photos come from Wikimedia Commons and Flickr under free licences, with the photographer credited under every photo and on '
            'the <a href="/credits.html">credits page</a>. We do not use AI-generated images.</li>'
            '<li>Highlights are YouTube videos, shown in YouTube\'s own player.</li></ul>'
            '<h2>Independent</h2>'
            '<p>Beyond100 is an independent project. It is not affiliated with the ATP, the WTA, the ITF, Premier Padel or the FIP.</p>'
            '<h2>Get in touch</h2>'
            '<p>Spotted a wrong score, or a photo of you that you would rather not see here? Send us a message on Instagram and we will sort it out.</p>'
            '<div class="ig"><a href="https://www.instagram.com/beyond100.tennis/">@beyond100.tennis</a>'
            '<a href="https://www.instagram.com/beyond100.padel/">@beyond100.padel</a></div></div>')
