"""Páginas extra do site: próxima semana, países, pesquisa e botões de partilha. Só dados que o site já tem."""
import datetime
import html
import json
import os
import urllib.parse

import webapp

esc = html.escape

COUNTRIES = {
    "ARG": "Argentina", "AUS": "Australia", "AUT": "Austria", "BEL": "Belgium", "BIH": "Bosnia and Herzegovina", "BLR": "Belarus",
    "BOL": "Bolivia", "BRA": "Brazil", "BUL": "Bulgaria", "CAN": "Canada", "CHI": "Chile", "CHN": "China", "COL": "Colombia",
    "CRO": "Croatia", "CYP": "Cyprus", "CZE": "Czechia", "DEN": "Denmark", "ECU": "Ecuador", "EGY": "Egypt", "ESP": "Spain",
    "EST": "Estonia", "FIN": "Finland", "FRA": "France", "GBR": "Great Britain", "GEO": "Georgia", "GER": "Germany", "GRE": "Greece",
    "HKG": "Hong Kong", "HUN": "Hungary", "IND": "India", "INA": "Indonesia", "IRL": "Ireland", "ISR": "Israel", "ITA": "Italy",
    "JPN": "Japan", "KAZ": "Kazakhstan", "KOR": "South Korea", "LAT": "Latvia", "LTU": "Lithuania", "MEX": "Mexico", "MDA": "Moldova",
    "MON": "Monaco", "NED": "Netherlands", "NOR": "Norway", "NZL": "New Zealand", "PAR": "Paraguay", "PER": "Peru", "PHI": "Philippines",
    "POL": "Poland", "POR": "Portugal", "ROU": "Romania", "RSA": "South Africa", "RUS": "Russia", "SLO": "Slovenia", "SRB": "Serbia",
    "SUI": "Switzerland", "SVK": "Slovakia", "SWE": "Sweden", "THA": "Thailand", "TPE": "Chinese Taipei", "TUN": "Tunisia",
    "TUR": "Türkiye", "UKR": "Ukraine", "URU": "Uruguay", "USA": "United States", "UZB": "Uzbekistan", "VEN": "Venezuela",
    "BAR": "Barbados", "DOM": "Dominican Republic", "MAR": "Morocco", "LUX": "Luxembourg", "ISL": "Iceland", "MNE": "Montenegro",
    "MKD": "North Macedonia", "ARM": "Armenia", "QAT": "Qatar", "UAE": "United Arab Emirates", "VIE": "Vietnam", "MAS": "Malaysia",
    "SGP": "Singapore", "PUR": "Puerto Rico", "CRC": "Costa Rica", "GUA": "Guatemala", "ESA": "El Salvador", "ALG": "Algeria",
    "ZIM": "Zimbabwe", "NGR": "Nigeria", "KEN": "Kenya", "IRI": "Iran", "PAK": "Pakistan", "LBN": "Lebanon", "JOR": "Jordan",
}


ISO2 = {"ARG": "ar", "AUS": "au", "AUT": "at", "BEL": "be", "BIH": "ba", "BLR": "by", "BOL": "bo", "BRA": "br", "BUL": "bg", "CAN": "ca",
        "CHI": "cl", "CHN": "cn", "COL": "co", "CRO": "hr", "CYP": "cy", "CZE": "cz", "DEN": "dk", "ECU": "ec", "EGY": "eg", "ESP": "es",
        "EST": "ee", "FIN": "fi", "FRA": "fr", "GBR": "gb", "GEO": "ge", "GER": "de", "GRE": "gr", "HKG": "hk", "HUN": "hu", "IND": "in",
        "INA": "id", "IRL": "ie", "ISR": "il", "ITA": "it", "JPN": "jp", "KAZ": "kz", "KOR": "kr", "LAT": "lv", "LTU": "lt", "MEX": "mx",
        "MDA": "md", "MON": "mc", "NED": "nl", "NOR": "no", "NZL": "nz", "PAR": "py", "PER": "pe", "PHI": "ph", "POL": "pl", "POR": "pt",
        "ROU": "ro", "RSA": "za", "RUS": "ru", "SLO": "si", "SRB": "rs", "SUI": "ch", "SVK": "sk", "SWE": "se", "THA": "th", "TPE": "tw",
        "TUN": "tn", "TUR": "tr", "UKR": "ua", "URU": "uy", "USA": "us", "UZB": "uz", "VEN": "ve", "BAR": "bb", "DOM": "do", "MAR": "ma",
        "LUX": "lu", "ISL": "is", "MNE": "me", "MKD": "mk", "ARM": "am", "QAT": "qa", "UAE": "ae", "VIE": "vn", "MAS": "my", "SGP": "sg",
        "PUR": "pr", "CRC": "cr", "GUA": "gt", "ESA": "sv", "ALG": "dz", "ZIM": "zw", "NGR": "ng", "KEN": "ke", "IRI": "ir", "PAK": "pk",
        "LBN": "lb", "JOR": "jo"}
FLAG_CDN = "https://cdn.jsdelivr.net/npm/flag-icons@7.2.1/flags/4x3/"


def flag(code, h=14):
    """Bandeira em SVG (imagem, funciona também no Windows, onde os emojis de bandeiras não aparecem). Russos e bielorrussos sem bandeira."""
    c = (code or "").upper()
    iso = ISO2.get(c) or (c.lower() if len(c) == 2 else None)
    if not iso or c in ("RUS", "BLR", "RU", "BY"):
        return ""
    return (f'<img src="{FLAG_CDN}{iso}.svg" alt="" width="{round(h * 4 / 3)}" height="{h}" loading="lazy" onerror="this.remove()" '
            f'style="vertical-align:-2px;margin-right:7px;border-radius:2px">')


def country_name(code):
    c = (code or "").upper()
    return COUNTRIES.get(c, c)


def _recent(results, days):
    cut = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
    return [r for r in results if (r.get("date") or "") >= cut and not r.get("q") and webapp.classify(r)[1] == "singles"
            and r.get("winner") in (1, 2)]


def in_form(results, linkable, n=12):
    wins = {}
    for r in _recent(results, 14):
        p = r["p%d" % r["winner"]]
        k = webapp.slugify(p["name"])
        e = wins.setdefault(k, {"name": p["name"], "country": p.get("country"), "w": 0, "rank": p.get("rank")})
        e["w"] += 1
    rows = sorted((e for e in wins.values() if e["w"] >= 3), key=lambda e: (-e["w"], e["rank"] or 9999))[:n]
    return rows


def _plink(name, linkable):
    s = webapp.slugify(name)
    return f'<a href="/p/{s}.html">{esc(name)}</a>' if s in linkable else esc(name)


def next_week_page(results, linkable, risers=None):
    cal = []
    try:
        cal = json.load(open("categorias_torneios.json", encoding="utf-8"))
    except Exception:
        pass
    today = datetime.date.today()
    mon_this = today - datetime.timedelta(days=today.weekday())
    mon_next = mon_this + datetime.timedelta(days=7)

    def block(mon, title):
        evs = [e for e in cal if e.get("start") == mon.isoformat()]
        if not evs:
            return ""
        evs.sort(key=lambda e: (0 if e["label"].startswith(("ATP", "WTA")) else 1, e["label"], e["city"]))
        rows = "".join(f'<tr><td class="pn">{esc(e["city"].title())}</td><td>{esc(e["label"])} · {"Women" if e.get("g") == "w" else "Men"}</td></tr>'
                       for e in evs)
        return (f'<h2 class="dh">{esc(title)} · {mon.strftime("%d %b")}</h2>'
                f'<table class="pt"><thead><tr><th>Tournament</th><th>Level</th></tr></thead><tbody>{rows}</tbody></table>')
    form = in_form(results, linkable)
    fr = "".join(f'<tr><td class="pn">{_plink(e["name"], linkable)}</td><td>{flag(e.get("country"))}{esc(country_name(e.get("country")))}</td>'
                 f'<td>{("#" + str(e["rank"])) if e.get("rank") else "–"}</td><td><b>{e["w"]}</b></td></tr>' for e in form)
    rz = "".join(f'<tr><td class="pn">{_plink(x["name"], linkable)}</td><td>#{x["rank_before"]} → #{x["rank_now"]}</td><td><b>+{x["rise"]}</b></td></tr>'
                 for x in (risers or [])[:10])
    return ('<section class="page-h"><h1>Next week</h1><p>The tournaments coming up on the ATP Challenger, ITF and WTA tours, '
            'plus the players arriving in form. Updated every day.</p></section>'
            + block(mon_next, "Next week") + block(mon_this, "This week")
            + (f'<h2 class="dh">In form (last 14 days)</h2><table class="pt"><thead><tr><th>Player</th><th>Country</th><th>Ranking</th>'
               f'<th>Wins</th></tr></thead><tbody>{fr}</tbody></table>' if fr else "")
            + (f'<h2 class="dh">Climbing</h2><table class="pt"><thead><tr><th>Player</th><th>Ranking</th><th>Places</th></tr></thead>'
               f'<tbody>{rz}</tbody></table><p class="cr">Rankings as recorded in the matches we tracked.</p>' if rz else ""))


def country_pages(index, results, tr, tx, min_players=3):
    """{code: (title, body, desc, n_players)} + página índice."""
    by = {}
    for slug, e in index.items():
        c = (e.get("country") or "").upper()
        if c:
            by.setdefault(c, []).append((slug, e))
    week = _recent(results, 7)
    pages = {}
    for c, ps in by.items():
        if len(ps) < min_players:
            continue
        ps.sort(key=lambda x: (x[1].get("rank") or 9999))
        rows = "".join(
            f'<tr><td class="pn"><a href="/p/{s}.html">{esc(e["name"])}</a></td><td>{("#" + str(e["rank"])) if e.get("rank") else "–"}</td>'
            f'<td>{sum(1 for i, r in e["matches"] if r["winner"] == i)}-{sum(1 for i, r in e["matches"] if r["winner"] != i)}</td>'
            f'<td>{esc(max((r.get("date", "") for _, r in e["matches"]), default=""))}</td></tr>' for s, e in ps[:120])
        names = {e["name"] for _, e in ps}
        wk = [r for r in week if r["p1"]["name"] in names or r["p2"]["name"] in names]
        wk.sort(key=lambda r: r.get("date", ""), reverse=True)
        body = (f'<section class="page-h"><p><a href="/countries.html">← Countries</a></p><h1>{flag(c, 30)}{esc(country_name(c))}</h1>'
                f'<p>{len(ps)} players from {esc(country_name(c))} in the matches we tracked on the Challenger, ITF and WTA tours.</p></section>'
                + (f'<h2 class="dh">This week</h2><section class="tg">{"".join(webapp.match_html(r, dict(tr, _tx=tx)) for r in wk[:20])}</section>' if wk else "")
                + f'<h2 class="dh">Players</h2><table class="pt"><thead><tr><th>Player</th><th>Ranking</th><th>W-L tracked</th><th>Last match</th></tr></thead><tbody>{rows}</tbody></table>')
        pages[c] = (f"{country_name(c)} players: results and rankings · Beyond100", body,
                    f"{country_name(c)} tennis players beyond the top 100: {len(ps)} players, this week's results, rankings and form on the Challenger, ITF and WTA tours.",
                    len(ps), (wk[0].get("date") if wk else ""))
    idx = "".join(f'<tr><td class="pn">{flag(c)}<a href="/c/{c.lower()}.html">{esc(country_name(c))}</a></td><td>{v[3]}</td></tr>'
                  for c, v in sorted(pages.items(), key=lambda kv: -kv[1][3]))
    index_body = ('<section class="page-h"><h1>Countries</h1><p>Players by country, with this week\'s results.</p></section>'
                  f'<table class="pt"><thead><tr><th>Country</th><th>Players</th></tr></thead><tbody>{idx}</tbody></table>')
    return pages, index_body


def search_index(index, tournaments):
    items = []
    for s, e in index.items():                     # 13/11/2026: ranking e foto para a pesquisa instantânea (página inicial)
        if not s:
            continue
        x = {"n": e["name"], "u": f"/p/{s}.html", "k": country_name(e.get("country"))}
        if isinstance(e.get("rank"), int) and e["rank"] > 0:
            x["r"] = e["rank"]
        if s in webapp.AVATARS:
            x["i"] = f"/img/{s}.jpg"
        items.append(x)
    items += [{"n": t, "u": f"/t/{webapp.slugify(t)}.html", "k": "Tournament"} for t in tournaments]
    return items


SEARCH_BTN = ('<a href="#" id="b100s" aria-label="Search" title="Search (/)" style="display:inline-flex;vertical-align:middle">'
              '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">'
              '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.6-4.6"/></svg></a>')

SEARCH_HTML = ('<div id="b100sw" hidden style="margin:0 0 18px"><input id="b100q" class="srch" type="search" placeholder="Search players or tournaments" '
               'aria-label="Search players or tournaments" autocomplete="off" style="margin-top:0"><div id="b100r"></div></div>'
               '<script>(function(){var w=document.getElementById("b100sw"),q=document.getElementById("b100q"),o=document.getElementById("b100r"),'
               'b=document.getElementById("b100s"),d=null;'
               'function f(s){return s.normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase()}'
               'function load(){if(!d)fetch("/search.json").then(function(r){return r.json()}).then(function(j){d=j;go()}).catch(function(){})}'
               'function open(){w.hidden=false;q.focus();load()}'
               'function go(){var v=f(q.value.trim());if(v.length<2||!d){o.innerHTML="";return}'
               'var r=d.filter(function(x){return f(x.n).indexOf(v)>=0}).slice(0,8);'
               'o.innerHTML=r.map(function(x){return \'<a style="display:block;padding:9px 4px;border-bottom:1px solid var(--e)" href="\'+x.u+\'">\'+x.n.replace(/</g,"&lt;")+\' <small style="color:var(--s)">\'+x.k+"</small></a>"}).join("")||\'<p class="cr">No match.</p>\'}'
               'b.addEventListener("click",function(e){e.preventDefault();if(w.hidden)open();else w.hidden=true});'
               'document.addEventListener("keydown",function(e){if(e.key==="/"&&document.activeElement!==q){e.preventDefault();open()}if(e.key==="Escape")w.hidden=true});'
               'q.addEventListener("input",go)})();</script>')


SHARE_ICONS = {
    "wa": '<path d="M12 3a9 9 0 0 0-7.8 13.5L3 21l4.6-1.2A9 9 0 1 0 12 3z"/><path d="M8.6 8.2c.2-.5.5-.5.8-.5h.5c.2 0 .4 0 .6.5l.7 1.7c.1.2 0 .4-.1.6l-.5.6c-.1.1-.2.3 0 .5.5.9 1.2 1.6 2.1 2.1.2.1.4.1.5-.1l.6-.7c.2-.2.4-.2.6-.1l1.6.8c.3.1.4.3.3.6-.2 1-.9 1.6-1.9 1.6-2.9-.3-5.6-3-5.9-5.9 0-.6.1-1.1.4-1.7z" fill="currentColor" stroke="none"/>',
    "x": '<path d="M4 4l16 16M20 4L4 20" />',
    "fb": '<path d="M15 3h-2.5A3.5 3.5 0 0 0 9 6.5V9H7v3.5h2V21h3.5v-8.5H15l.5-3.5h-3V7a1 1 0 0 1 1-1H15z"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "share": '<path d="M12 3v12M7 8l5-5 5 5"/><path d="M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6"/>',
    "ig": '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor"/>',
}
SHARE_THEME = {"tennis": ("#0e3a2d", "@beyond100.tennis", "https://www.instagram.com/beyond100.tennis/"),
               "padel": ("#0c2e4a", "@beyond100.padel", "https://www.instagram.com/beyond100.padel/")}


def share_html(url, text, title="Share this result", sport="tennis", sub=""):
    """Cartão de partilha comum ao ténis e ao padel: botão Share (partilha nativa do telemóvel; no computador copia o link),
    WhatsApp, X, Facebook, copiar link e seguir no Instagram."""
    u, t = urllib.parse.quote(url, safe=""), urllib.parse.quote(text, safe="")
    dark, handle, ig = SHARE_THEME.get(sport, SHARE_THEME["tennis"])
    ico = lambda k: f'<svg viewBox="0 0 24 24" aria-hidden="true">{SHARE_ICONS[k]}</svg>'
    css = ("<style>.shr{margin:26px 0 8px;padding:18px;border-radius:22px;background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,.1)}"
           ".shr h3{margin:0 0 2px;font:700 1.05rem system-ui}.shr p{margin:0 0 14px;font:500 .84rem system-ui;opacity:.7}"
           ".shr .shb{display:flex;flex-wrap:nowrap;gap:8px;align-items:center}"
           ".shr a,.shr button{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:46px;border-radius:999px;cursor:pointer;"
           "text-decoration:none;color:inherit;font:700 .92rem system-ui;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.05)}"
           ".shr .ic{width:44px;height:44px;flex:none;padding:0}.shr svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}"
           ".shr .go{flex:1 1 auto;max-width:200px;background:#d9f23a;border-color:#d9f23a;color:var(--shr-dark);padding:0 14px;min-width:0}"
           ".shr .ig{margin-top:14px;padding-top:14px;border-top:1px solid rgba(255,255,255,.1);display:flex;align-items:center;justify-content:space-between;gap:10px}"
           ".shr .ig span{font:600 .86rem system-ui;opacity:.8}.shr .ig a{padding:0 16px;height:40px}"
           ".shr .ok{font:600 .8rem system-ui;color:#d9f23a;margin-top:8px}.shr .ok:empty{display:none}"
           "@media (max-width:520px){.shr .ig{flex-direction:column;align-items:stretch}.shr .ig span{text-align:center}}</style>")
    js = ("var d={title:document.title,text:this.dataset.t,url:this.dataset.u},o=this.closest('.shr').querySelector('.ok');"
          "if(navigator.share){navigator.share(d).catch(function(){})}else if(navigator.clipboard){navigator.clipboard.writeText(d.url);o.textContent='Link copied'}")
    cp = ("var o=this.closest('.shr').querySelector('.ok');if(navigator.clipboard){navigator.clipboard.writeText(this.dataset.u);o.textContent='Link copied'}return false")
    return (css + f'<section class="shr" style="--shr-dark:{dark}"><h3>{html.escape(title)}</h3>'
            + (f'<p>{html.escape(sub)}</p>' if sub else '<p>Send it to the group chat.</p>')
            + '<div class="shb">'
            f'<button class="go" type="button" data-u="{html.escape(url)}" data-t="{html.escape(text)}" onclick="{html.escape(js)}">{ico("share")}Share</button>'
            f'<a class="ic" href="https://wa.me/?text={t}%20{u}" target="_blank" rel="noopener" aria-label="WhatsApp" title="WhatsApp">{ico("wa")}</a>'
            f'<a class="ic" href="https://twitter.com/intent/tweet?text={t}&url={u}" target="_blank" rel="noopener" aria-label="X" title="X">{ico("x")}</a>'
            f'<a class="ic" href="https://www.facebook.com/sharer/sharer.php?u={u}" target="_blank" rel="noopener" aria-label="Facebook" title="Facebook">{ico("fb")}</a>'
            f'<a class="ic" href="#" data-u="{html.escape(url)}" onclick="{html.escape(cp)}" aria-label="Copy link" title="Copy link">{ico("link")}</a></div>'
            '<div class="ok" aria-live="polite"></div>'
            f'<div class="ig"><span>Stories, results and upsets every day</span><a href="{ig}" target="_blank" rel="noopener">{ico("ig")}Follow {handle}</a></div></section>')
