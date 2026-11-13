"""Página inicial, versão 2 (13/11/2026): peças comuns ao ténis e ao padel (cores das variáveis --g --deep --c --v --s --e).

- "Lead story": o acontecimento mais forte dos últimos dias (campeão de um torneio grande ou surpresa enorme), com foto grande;
- ao lado: quem somos (h1), pesquisa instantânea de jogadores (com foto e ranking) e os números da semana;
- campeões em cartões com foto; resultados agrupados por torneio; o resto dos blocos da página inicial com o mesmo estilo.
Sem fontes de fora; tudo no HTML para o Google."""
import html

esc = html.escape

CSS = """
.hm{min-width:0}
@media(min-width:960px){.hm{width:min(1180px,calc(100vw - 48px));margin-left:calc(50% - min(590px,calc(50vw - 24px)))}}
.hm h2.ui-sec,.hm h2.sec,.hm h2.dh{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin:30px 0 12px}
.hm h2.ui-sec span,.hm h2.sec>span,.hm h2.dh{font:850 1.35rem system-ui!important;color:var(--c)!important;letter-spacing:-.01em}
.hm h2.ui-sec a,.hm h2.sec a,.hm h2.sec small a,.hm h2.dh a{font:700 .86rem system-ui;color:var(--v);text-decoration:none}
.hm-top{display:grid;gap:14px;grid-template-columns:minmax(0,1fr);margin-top:4px}
@media(min-width:960px){.hm-top{grid-template-columns:minmax(0,1.45fr) minmax(0,1fr);gap:18px}}
.hm-lead{position:relative;display:flex;align-items:flex-end;min-height:440px;border-radius:28px;overflow:hidden;background:var(--deep);border:1px solid var(--e);
text-decoration:none;color:#fff}
.hm-lead img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 20%;transition:transform .5s}
.hm-lead:hover img{transform:scale(1.03)}
.hm-lead .ini{position:absolute;right:-10px;top:-30px;font:900 14rem/1 system-ui;color:var(--v);opacity:.1;letter-spacing:-.06em}
.hm-lead::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.25) 0,transparent 25%,transparent 40%,rgba(0,0,0,.85) 100%)}
.hm-lead .tx{position:relative;z-index:1;padding:22px;display:flex;flex-direction:column;gap:10px}
.hm-lead .kick{display:flex;flex-wrap:wrap;gap:6px}
.hm-lead .kick span{background:var(--v);color:var(--g);font:800 .72rem system-ui;letter-spacing:.06em;text-transform:uppercase;border-radius:999px;padding:5px 11px}
.hm-lead .kick span+span{background:rgba(255,255,255,.16);color:#fff}
.hm-lead h2{margin:0;font:900 2.2rem/1 system-ui;letter-spacing:-.025em;text-wrap:balance}
.hm-lead p{margin:0;font:500 .98rem/1.45 system-ui;color:rgba(255,255,255,.88);max-width:52ch}
.hm-lead .cr{position:absolute;z-index:1;right:12px;top:12px;font:500 .64rem system-ui;color:rgba(255,255,255,.85);background:rgba(0,0,0,.35);padding:3px 8px;border-radius:7px}
@media(min-width:960px){.hm-lead{min-height:500px}.hm-lead h2{font-size:3rem}.hm-lead .tx{padding:32px}}
.hm-side{display:flex;flex-direction:column;gap:12px;min-width:0}
.hm-intro{background:var(--deep);border:1px solid var(--e);border-radius:24px;padding:20px}
.hm-intro h1{margin:0 0 8px;font:900 1.75rem/1.05 system-ui;letter-spacing:-.02em;color:var(--c)}.hm-intro h1 em{font-style:normal;font-weight:900;color:var(--v)}
.hm-intro p{margin:0 0 14px;font:400 .95rem/1.5 system-ui;color:var(--s)}
.hm-cta{display:flex;flex-wrap:wrap;gap:8px}.hm-cta a{text-decoration:none;font:800 .88rem system-ui;border-radius:12px;padding:11px 15px;border:1px solid var(--e);color:var(--c)}
.hm-cta a.go{background:var(--v);color:var(--g);border-color:var(--v)}
.hm-search{position:relative}
.hm-search input{width:100%;box-sizing:border-box;background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:15px 16px 15px 46px;color:var(--c);
font:500 1rem system-ui;outline:none}.hm-search input:focus{border-color:var(--v)}
.hm-search svg{position:absolute;left:16px;top:16px;color:var(--s)}
.hm-sr{position:absolute;z-index:20;left:0;right:0;top:calc(100% + 6px);background:var(--deep);border:1px solid var(--e);border-radius:16px;overflow:hidden;
box-shadow:0 18px 40px rgba(0,0,0,.45)}
.hm-sr:empty{display:none}
.hm-sr a{display:flex;align-items:center;gap:12px;padding:10px 14px;text-decoration:none;color:var(--c);border-top:1px solid var(--e)}.hm-sr a:first-child{border-top:0}
.hm-sr a:hover,.hm-sr a.on{background:rgba(255,255,255,.05)}
.hm-sr img,.hm-sr .i{width:36px;height:36px;border-radius:50%;object-fit:cover;flex:none;background:var(--g);display:grid;place-items:center;font:800 .75rem system-ui;color:var(--s)}
.hm-sr b{display:block;font:700 .95rem system-ui}.hm-sr small{font:500 .78rem system-ui;color:var(--s)}.hm-sr .rk{margin-left:auto;font:800 .85rem system-ui;color:var(--v)}
.hm-nums{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.hm-nums a,.hm-nums div{background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:12px;text-decoration:none;color:var(--c);min-width:0}
.hm-nums b{display:block;font:900 1.5rem/1.1 system-ui;letter-spacing:-.02em}.hm-nums span{font:500 .74rem system-ui;color:var(--s)}
.hm-row{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:6px;scrollbar-width:none;margin:0 -16px;padding-left:16px;padding-right:16px}
.hm-row::-webkit-scrollbar{display:none}
@media(min-width:960px){.hm-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));overflow:visible;margin:0;padding:0}}
.hm-ch{position:relative;flex:0 0 72%;scroll-snap-align:start;aspect-ratio:4/5;border-radius:22px;overflow:hidden;display:flex;align-items:flex-end;text-decoration:none;color:#fff;
background:radial-gradient(110% 90% at 80% 0,var(--e) 0,var(--deep) 65%);border:1px solid var(--e)}
@media(min-width:600px){.hm-ch{flex-basis:40%}}
.hm-ch img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 20%;transition:transform .4s}.hm-ch:hover img{transform:scale(1.04)}
.hm-ch .ini{position:absolute;right:-8px;top:-16px;font:900 7rem/1 system-ui;color:var(--v);opacity:.12}
.hm-ch::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,transparent 35%,rgba(0,0,0,.85))}
.hm-ch .tg{text-transform:uppercase;position:absolute;z-index:1;left:12px;top:12px;background:var(--v);color:var(--g);font:800 .66rem system-ui;letter-spacing:.06em;border-radius:999px;padding:4px 9px}
.hm-ch .tx{position:relative;z-index:1;padding:14px;display:flex;flex-direction:column;gap:2px;min-width:0}
.hm-ch small{font:800 .66rem system-ui;letter-spacing:.1em;text-transform:uppercase;color:var(--v)}
.hm-ch b{font:900 1.25rem/1.05 system-ui;letter-spacing:-.01em}.hm-ch span{font:600 .82rem system-ui;color:rgba(255,255,255,.85)}
.hm-ch i{font:500 .76rem system-ui;font-style:normal;color:rgba(255,255,255,.7)}
.hm-res{display:grid;gap:12px;grid-template-columns:minmax(0,1fr)}
@media(min-width:960px){.hm-res{grid-template-columns:repeat(2,minmax(0,1fr));align-items:start}}
.hm .pv-wl{display:none}.hm .pv-row{grid-template-columns:40px minmax(0,1fr) auto}
.hm .numgrid{grid-template-columns:repeat(3,minmax(0,1fr))}.hm .nbox b{font:900 1.8rem system-ui;color:var(--v)}
@media(min-width:960px){.hm .numgrid{grid-template-columns:repeat(6,minmax(0,1fr))}}
.hm #lvwrap h2.sec>span{display:inline-flex;align-items:center}
.hm .lvg .nm,.hm .ui-spot b,.hm .ui-spot .ini,.hm .pd-spot b,.hm .pd-spot .ini,.hm h2.sec,.hm .ui-champ b,.hm .ui-quick b,.hm .padel-promo b{font-family:system-ui,-apple-system,"Segoe UI",sans-serif!important;font-weight:800}
.hm .ui-quick{margin-top:24px}
.hm h2.sec{font:850 1.35rem system-ui!important;color:var(--c)!important;letter-spacing:-.01em}
.hm .lvg .sc span,.hm #lvwrap h2.sec small{font-family:system-ui,-apple-system,"Segoe UI",sans-serif!important}.hm .lvg .sc span{font-weight:800}
.hm-more{background:var(--deep);border:1px solid var(--e);border-radius:20px;padding:14px 14px 6px}
.hm-more a{display:flex;align-items:center;gap:12px;padding:10px 0;text-decoration:none;color:var(--c);border-top:1px solid var(--e)}.hm-more .pv-lab+a{border-top:0;margin-top:6px}
.hm-more img,.hm-more .i{width:40px;height:40px;border-radius:50%;object-fit:cover;flex:none;display:grid;place-items:center;background:var(--g);font:800 .78rem system-ui;color:var(--s)}
.hm-more b{display:block;font:700 .92rem/1.25 system-ui}.hm-more small{font:500 .76rem system-ui;color:var(--s)}.hm-more a:hover b{color:var(--v)}
@media(min-width:960px){.hm .lvg{grid-template-columns:repeat(4,minmax(0,1fr))}.hm .ui-quick{grid-template-columns:repeat(4,minmax(0,1fr))}}
"""

SEARCH_JS = r"""<script>(function(){var q=document.getElementById("hmq"),o=document.getElementById("hmr");if(!q)return;var d=null,k=-1,src=q.dataset.src,pf=q.dataset.pref||"";
function f(s){return(s||"").normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase()}
function load(){if(!d)fetch(src).then(function(r){return r.json()}).then(function(j){d=j;go()}).catch(function(){})}
function e(s){return String(s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
function go(){var v=f(q.value.trim());k=-1;if(v.length<2||!d){o.innerHTML="";return}
 var r=d.filter(function(x){return f(x.n).indexOf(v)>=0}).sort(function(a,b){var pa=pf&&a.u.indexOf(pf)==0?0:1,pb=pf&&b.u.indexOf(pf)==0?0:1,sa=f(a.n).indexOf(v)==0?0:1,sb=f(b.n).indexOf(v)==0?0:1;return pa-pb||sa-sb||(a.r||9999)-(b.r||9999)}).slice(0,7);
 o.innerHTML=r.map(function(x){var ini=x.n.split(" ").slice(0,2).map(function(w){return w[0]||""}).join("");
  return '<a href="'+e(x.u)+'">'+(x.i?'<img src="'+e(x.i)+'" alt="" loading="lazy">':'<span class="i">'+e(ini)+'</span>')+'<span><b>'+e(x.n)+'</b><small>'+e(x.k||"")+'</small></span>'+(x.r?'<span class="rk">No. '+x.r+'</span>':'')+'</a>'}).join("")||'<a href="#" onclick="return false"><span><b>No match</b><small>Try another spelling</small></span></a>'}
q.addEventListener("focus",load);q.addEventListener("input",function(){load();go()});
q.addEventListener("keydown",function(ev){var a=o.querySelectorAll("a");if(!a.length)return;if(ev.key=="ArrowDown"||ev.key=="ArrowUp"){ev.preventDefault();k=(k+(ev.key=="ArrowDown"?1:-1)+a.length)%a.length;
 a.forEach(function(x,i){x.classList.toggle("on",i==k)})}else if(ev.key=="Enter"&&a[k<0?0:k]){location.href=a[k<0?0:k].href}else if(ev.key=="Escape"){o.innerHTML=""}});
document.addEventListener("click",function(ev){if(!ev.target.closest(".hm-search"))o.innerHTML=""})})();</script>"""


def lead(href, img, ini, kicks, headline, sub, credit=""):
    """Cartão grande do acontecimento do dia."""
    pic = f'<img src="{esc(img)}" alt="" width="600" height="750" fetchpriority="high">' if img else f'<span class="ini" aria-hidden="true">{esc(ini)}</span>'
    k = "".join(f"<span>{esc(x)}</span>" for x in kicks if x)
    return (f'<a class="hm-lead" href="{esc(href)}">{pic}{f"<span class=cr>{esc(credit)}</span>" if credit else ""}'
            f'<div class="tx"><div class="kick">{k}</div><h2>{esc(headline)}</h2><p>{esc(sub)}</p></div></a>')


def intro(h1a, h1b, text, ctas):
    c = "".join(f'<a class="{"go" if p else ""}" href="{esc(h)}">{esc(l)}</a>' for l, h, p in ctas)
    return f'<section class="hm-intro"><h1>{esc(h1a)} <em>{esc(h1b)}</em></h1><p>{esc(text)}</p><div class="hm-cta">{c}</div></section>'


def search(src="/search.json", placeholder="Search a player or tournament", pref=""):
    return ('<div class="hm-search"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true">'
            '<circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.6-4.6"/></svg>'
            f'<input id="hmq" type="search" data-src="{esc(src)}" data-pref="{esc(pref)}" placeholder="{esc(placeholder)}" aria-label="{esc(placeholder)}" autocomplete="off">'
            '<div class="hm-sr" id="hmr" role="listbox"></div></div>')


def nums(items):
    """[(valor, legenda, href)]"""
    out = ""
    for v, k, h in items[:3]:
        inner = f"<b>{esc(str(v))}</b><span>{esc(k)}</span>"
        out += f'<a href="{esc(h)}">{inner}</a>' if h else f"<div>{inner}</div>"
    return f'<div class="hm-nums">{out}</div>'


def champ(href, img, ini, tag, label, name, place, note):
    pic = f'<img src="{esc(img)}" alt="{esc(name)}" loading="lazy" width="600" height="750">' if img else f'<span class="ini" aria-hidden="true">{esc(ini)}</span>'
    return (f'<a class="hm-ch" href="{esc(href)}">{pic}{f"<span class=tg>{esc(tag)}</span>" if tag else ""}<div class="tx"><small>{esc(label)}</small>'
            f'<b>{esc(name)}</b><span>{esc(place)}</span><i>{esc(note)}</i></div></a>')


def page(top_lead, side, rest):
    return f'<style>{CSS}</style><div class="hm"><div class="hm-top">{top_lead}<div class="hm-side">{side}</div></div>{rest}</div>{SEARCH_JS}'
