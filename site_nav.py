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
