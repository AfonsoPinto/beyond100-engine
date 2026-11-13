"""Navegação comum ao ténis e ao padel (o mesmo molde nas duas vertentes, só mudam as cores).
- bar(sport, active): barra fixa em baixo no telemóvel, com ícones: Home · Results · Today · Videos · Players · Stats
- live_pill(href): botão vermelho LIVE no topo, só quando há jogos a decorrer
- CSS: o estilo das duas coisas (cores por vertente em variáveis)."""

ICONS = {
    "home": '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
    "results": '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 9h6M7 15h6M16 9h1M16 15h1"/>',
    "today": '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4M8 14h3"/>',
    "videos": '<circle cx="12" cy="12" r="9"/><path d="M10 8.5v7l6-3.5z" fill="currentColor"/>',
    "players": '<path d="M5 20V12M12 20V5M19 20v-6"/>',
    "stats": '<path d="M4 19h16M6 16l4-5 3 3 5-7"/>',
}
LABELS = (("home", "Home"), ("results", "Results"), ("today", "Today"), ("videos", "Videos"), ("players", "Rankings"), ("stats", "Stats"))
LINKS = {
    "tennis": {"home": "/index.html", "results": "/results.html", "today": "/order-of-play.html", "videos": "/highlights.html",
               "players": "/rankings.html", "stats": "/stats.html"},
    "padel": {"home": "/padel/index.html", "results": "/padel/results.html", "today": "/padel/order-of-play.html",
              "videos": "/padel/highlights.html", "players": "/padel/rankings.html", "stats": "/padel/stats.html"},
}
THEME = {"tennis": ("rgba(9,40,30,.94)", "rgba(244,239,224,.62)", "#d9f23a", "rgba(244,239,224,.14)"),
         "padel": ("rgba(8,30,52,.94)", "#a9c0d6", "#d9f23d", "#24507a")}

CSS = """.nb{display:none}
.nlive{display:inline-flex;align-items:center;gap:6px;background:#cf3339;color:#fff!important;font:800 .72rem system-ui;letter-spacing:.06em;
text-transform:uppercase;padding:5px 10px;border-radius:999px;text-decoration:none;margin-right:10px}
.nlive[hidden]{display:none!important}
.nlive i{width:7px;height:7px;border-radius:50%;background:#fff;animation:npulse 1.4s infinite}@keyframes npulse{50%{opacity:.3}}
nav:has(.nlive)>div{display:flex;align-items:center;white-space:nowrap}
@media (max-width:720px){
.ntop{display:none!important}nav>div{display:flex;align-items:center;gap:12px;white-space:nowrap}
body{padding-bottom:calc(76px + env(safe-area-inset-bottom))}
.nb{display:grid;grid-template-columns:repeat(6,1fr);position:fixed;left:0;right:0;bottom:0;z-index:60;background:var(--nb-bg);
-webkit-backdrop-filter:blur(16px);backdrop-filter:blur(16px);border-top:1px solid var(--nb-edge);padding:6px 2px calc(6px + env(safe-area-inset-bottom))}
.nb a{display:flex;flex-direction:column;align-items:center;gap:3px;padding:5px 0;text-decoration:none;color:var(--nb-fg);font:600 .64rem system-ui}
.nb svg{width:23px;height:23px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.nb a.on{color:var(--nb-on)}.nb a.on svg{stroke-width:2.3}
}
@media (max-width:420px){nav:has(.nlive) .brand{font-size:.92rem;letter-spacing:.14em}.nlive{margin-right:4px}}"""


def bar(sport, active):
    bg, fg, on, edge = THEME[sport]
    links = LINKS[sport]
    return (f'<nav class="nb" aria-label="Sections" style="--nb-bg:{bg};--nb-fg:{fg};--nb-on:{on};--nb-edge:{edge}">' + "".join(
        f'<a class="{"on" if active == k else ""}" href="{links[k]}"{" aria-current=page" if active == k else ""}>'
        f'<svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[k]}</svg><span>{lab}</span></a>' for k, lab in LABELS) + "</nav>")


def live_pill(href, on=False, show=True, sport="tennis", tids=()):
    """Botão LIVE. O HTML traz o estado da última atualização (show); no browser confirma-se com os dados ao vivo e o botão
    esconde-se (ou aparece) conforme haja mesmo jogos em court agora (5/11/2026: não aparece sem jogos a decorrer)."""
    t = ",".join(str(x) for x in tids)
    return (f'<a class="nlive{" on" if on else ""}" href="{href}" data-sport="{sport}" data-tids="{t}"{"" if show else " hidden"}><i></i>Live</a>'
            + LIVE_CHECK_JS)


LIVE_CHECK_JS = """<script>(function(){var b=document.querySelector('.nlive[data-sport]');if(!b||b._ck)return;b._ck=1;
function set(on){b.hidden=!on}
function tennis(){fetch('/api/tennis/live',{cache:'no-store'}).then(function(r){return r.ok?r.json():null}).then(function(j){if(j)set((j.matches||[]).length>0)}).catch(function(){})}
function padel(){var ids=(b.dataset.tids||'').split(',').filter(Boolean),d=new Date().toISOString().slice(0,10);if(!ids.length){set(false);return}
 Promise.all(ids.map(function(id){return fetch('/api/padel/matches/'+id+'?date='+d).then(function(r){return r.ok?r.json():{matches:[]}}).catch(function(){return {matches:[]}})}))
 .then(function(rs){set(rs.some(function(r){return (r.matches||[]).some(function(m){return m.score&&m.score.length&&!m.winner&&['finished','walkover','retired','cancelled'].indexOf(m.status)<0})}))})}
function go(){if(!document.hidden)(b.dataset.sport==='padel'?padel:tennis)()}go();setInterval(go,120000)})()</script>"""


# 13/11/2026: camada moderna para todo o site (ténis e padel), carregada por último. Títulos sem serifa (o logótipo continua igual),
# números mais fortes, e as páginas de listas (resultados, ordem de jogo) mais largas no computador, em duas colunas.
MODERN_CSS = """
h1{font-weight:900;letter-spacing:-.025em}
.page-h h1{font-size:clamp(2rem,6vw,2.6rem);line-height:1.02;margin-bottom:10px}
h2.dh{font-weight:800;font-size:1.08rem;letter-spacing:-.005em}
h2.sec,.ui-sec{font-weight:850;letter-spacing:-.01em;color:var(--c)}.ui-sec a,h2.sec a{color:var(--v)}
.nm,.pd-gh b,.pd-champ b{font-weight:750}
.ch b,.pd-sc b,.pd-bm .s b,.pd-mside .sc b{font-weight:800;border-radius:10px}
.nbox b,.ui-tiles b,.ui-st b,.st-val em{font-weight:900;letter-spacing:-.02em}
@media(min-width:1100px){
.wrap>nav{width:min(1180px,calc(100vw - 48px));margin-left:calc(50% - min(590px,calc(50vw - 24px)))}
.wrap:has(#list),.wrap:has(.ui-mts),.wrap:has(.pd-day),.wrap:has(.pd-court){max-width:1180px}
#list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 16px;align-items:start}#list>*{grid-column:1/-1}#list>section.tg{grid-column:auto}
.pd-day{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 16px;align-items:start}.pd-day>*{grid-column:1/-1}.pd-day>.pd-card{grid-column:auto}
.ui-mts{grid-template-columns:repeat(3,minmax(0,1fr))!important}
}
"""
CSS += MODERN_CSS


# 13/11/2026: barra de baixo flutuante (telemóvel) e rodapé novo, iguais no ténis e no padel
NAV2_CSS = """
@media (max-width:720px){
body{padding-bottom:calc(92px + env(safe-area-inset-bottom))}
.nb{left:10px;right:10px;bottom:calc(10px + env(safe-area-inset-bottom));border-radius:24px;border:1px solid var(--nb-edge);padding:6px 4px;
box-shadow:0 14px 34px rgba(0,0,0,.45)}
.nb a{position:relative;border-radius:16px;margin:0 2px;padding:6px 0 5px}
.nb a.on{background:rgba(217,242,61,.12)}
.nb a.on::before{content:"";position:absolute;top:3px;left:50%;width:18px;height:3px;margin-left:-9px;border-radius:3px;background:var(--nb-on)}
}
footer.ft2{margin-top:40px;padding:30px 0 40px;border-top:1px solid var(--e);color:var(--s);font:400 .88rem/1.5 system-ui}
@media(min-width:1100px){footer.ft2{width:min(1180px,calc(100vw - 48px));margin-left:calc(50% - min(590px,calc(50vw - 24px)))}}
.ft2 .top{display:grid;gap:24px 16px;grid-template-columns:repeat(2,minmax(0,1fr))}.ft2 .br{grid-column:1/-1}
@media(min-width:760px){.ft2 .top{grid-template-columns:1.4fr repeat(3,minmax(0,1fr))}.ft2 .br{grid-column:auto}}
.ft2 .br b{display:block;font:700 1.05rem Georgia,"Times New Roman",serif;letter-spacing:.22em;color:var(--c)}
.ft2 .br p{margin:8px 0 14px;max-width:34ch}
.ft2 .cta{display:flex;flex-wrap:wrap;gap:8px}.ft2 .cta a{text-decoration:none;font:800 .84rem system-ui;border-radius:12px;padding:9px 13px;border:1px solid var(--e);color:var(--c)}
.ft2 .cta a.go{background:var(--v);border-color:var(--v);color:var(--g)}
.ft2 h3{margin:0 0 10px;font:800 .7rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--c)}
.ft2 ul{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:7px}.ft2 ul a{color:var(--s);text-decoration:none}.ft2 ul a:hover{color:var(--v)}
.ft2 .note{margin-top:26px;padding-top:16px;border-top:1px solid var(--e);font-size:.78rem;display:flex;flex-wrap:wrap;gap:6px 14px;justify-content:space-between}
.ft2 .note a{color:var(--s)}
"""
CSS += NAV2_CSS


def footer(brand, tagline, ctas, cols, note, extra=""):
    """Rodapé: marca + frase + botões, e colunas de ligações. ctas = [(texto, href, destaque)]; cols = [(título, [(texto, href)])]."""
    import html as _h
    e = _h.escape
    c = "".join(f'<a class="{"go" if g else ""}" href="{e(h)}">{e(t)}</a>' for t, h, g in ctas)
    cs = "".join(f'<div><h3>{e(t)}</h3><ul>' + "".join(f'<li><a href="{e(h)}">{e(x)}</a></li>' for x, h in links) + "</ul></div>" for t, links in cols)
    return (f'<footer class="ft2"><div class="top"><div class="br"><b>{e(brand)}</b><p>{e(tagline)}</p><div class="cta">{c}</div></div>{cs}</div>'
            f'<div class="note"><span>{note}</span>{extra}</div></footer>')
