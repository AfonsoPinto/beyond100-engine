"""Ficha de jogador, versão 2 (13/11/2026): peças comuns ao ténis e ao padel (as cores vêm das variáveis --g --deep --c --v --s --e
de cada site, por isso as duas fichas ficam iguais).

Ideias do desenho aprovado no quadro "Ficha do jogador · nova versão":
- topo com foto grande, o que aconteceu de mais recente (ex.: "Champion · Taipei"), nome que nunca parte a meio, factos em pílulas;
- cartão do ranking logo a seguir (o que as pessoas pesquisam no Google), com número grande, variação, pontos e gráfico da carreira;
- separadores fixos (Overview · Results · Stats · About) que levam a cada parte da página;
- torneios agrupados (da qualificação à final), estatísticas em barras e a tabela ano a ano;
- em computador, duas colunas (resultados à esquerda, números à direita).
Sem fontes de fora (system-ui), para a página continuar tão rápida como antes. Todo o conteúdo fica no HTML (nada é carregado depois),
para o Google ler tudo; o que é longo fica em <details>, que o Google também lê."""
import html
import re

esc = html.escape

CSS = """
.pv{--pr:22px;min-width:0}
.pv *{box-sizing:border-box}
@media(min-width:960px){.pv{width:min(1180px,calc(100vw - 48px));margin-left:calc(50% - min(590px,calc(50vw - 24px)))}}
.pv-back{display:inline-block;margin:2px 0 10px;color:var(--v);font:700 .88rem system-ui;text-decoration:none}
.pv-top{display:grid;gap:14px;grid-template-columns:minmax(0,1fr)}
@media(min-width:960px){.pv-top{grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:18px}}
.pv-hero{position:relative;overflow:hidden;border-radius:28px;background:var(--deep);border:1px solid var(--e);min-height:440px;display:flex;align-items:flex-end}
.pv-hero.np{min-height:300px;background:radial-gradient(110% 90% at 90% 0,var(--e) 0,var(--deep) 60%)}
.pv-hero img.big{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:55% 18%}
.pv-hero:not(.np)::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.35) 0,transparent 22%,transparent 42%,var(--deep) 92%)}
.pv-hero .ini{position:absolute;right:-12px;top:-30px;font:900 13rem/1 system-ui;color:var(--v);opacity:.08;letter-spacing:-.06em}
.pv-hero .tx{position:relative;z-index:1;padding:20px 18px 18px;display:flex;flex-direction:column;gap:10px;width:100%}
.pv-hero h1{margin:0;font:900 var(--fs,2.9rem)/.92 system-ui,-apple-system,"Segoe UI",sans-serif;letter-spacing:-.025em;text-transform:uppercase;color:#fff;
text-shadow:0 2px 14px rgba(0,0,0,.35)}
.pv-hero h1 span{display:block;white-space:nowrap}
.pv-pill{align-self:flex-start;display:inline-flex;align-items:center;gap:7px;background:var(--v);color:var(--g);font:800 .74rem system-ui;letter-spacing:.05em;
text-transform:uppercase;border-radius:999px;padding:6px 12px;text-decoration:none}
.pv-pill.ghost{background:rgba(255,255,255,.14);color:#fff}
.pv-chips{display:flex;flex-wrap:wrap;gap:6px}
.pv-chips span,.pv-chips a{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.12);color:#eef2ee;border-radius:999px;padding:5px 11px;
font:500 .82rem system-ui;text-decoration:none;backdrop-filter:blur(6px)}
.pv-chips img{border-radius:2px}
.pv-cr{position:absolute;right:12px;top:12px;z-index:1;margin:0;font:500 .66rem system-ui;color:rgba(255,255,255,.85);background:rgba(0,0,0,.38);
padding:3px 8px;border-radius:7px;max-width:70%}.pv-cr a{color:inherit}
@media(min-width:960px){.pv-hero{align-items:center;min-height:460px}.pv-hero img.big{left:auto;width:74%;
-webkit-mask-image:linear-gradient(90deg,transparent 0,rgba(0,0,0,.06) 14%,rgba(0,0,0,.3) 28%,rgba(0,0,0,.72) 44%,#000 60%);
mask-image:linear-gradient(90deg,transparent 0,rgba(0,0,0,.06) 14%,rgba(0,0,0,.3) 28%,rgba(0,0,0,.72) 44%,#000 60%)}
.pv-hero:not(.np)::after{background:linear-gradient(0deg,rgba(0,0,0,.25),transparent 30%)}.pv-hero .tx{padding:34px;max-width:58%}
.pv-cr{top:auto;bottom:12px}}
.pv-card{background:var(--deep);border:1px solid var(--e);border-radius:var(--pr);padding:18px}
.pv-lab{font:800 .7rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--s)}
.pv-rank{display:flex;flex-direction:column}.pv-rank.nc{align-self:start}.pv-rank.nc .pv-minis{margin-top:16px;padding-top:0}
.pv-rank .num{display:flex;align-items:baseline;gap:10px;margin-top:4px}
.pv-rank .num b{font:900 4.4rem/.95 system-ui;letter-spacing:-.04em;color:var(--v)}
.pv-rank .num .ch{font:800 .95rem system-ui}.pv-up{color:var(--v)}.pv-dn{color:#ff9a8a}
.pv-rank .num .pts{margin-left:auto;text-align:right;font:500 .78rem system-ui;color:var(--s)}.pv-rank .num .pts strong{display:block;font:800 1.6rem system-ui;color:var(--c)}
.pv-rank svg{display:block;width:100%;height:110px;flex:1 1 110px;min-height:110px;margin-top:12px;overflow:visible}
.pv-axis{display:flex;justify-content:space-between;gap:8px;font:500 .72rem system-ui;color:var(--s);margin-top:6px}
.pv-minis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:auto;padding-top:16px}
.pv-minis div{background:var(--g);border-radius:14px;padding:10px 12px;min-width:0}
.pv-minis b{display:block;font:800 1.25rem/1.15 system-ui;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pv-minis span{font:500 .72rem system-ui;color:var(--s)}
.pv-src{font:500 .7rem system-ui;color:var(--s);opacity:.85;margin-top:8px}
.pv-tabs{position:sticky;top:0;z-index:5;display:flex;justify-content:flex-start;align-items:center;gap:8px;overflow-x:auto;scrollbar-width:none;margin:18px -16px 0;padding:10px 16px;
background:color-mix(in srgb,var(--g) 92%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--e)}
.pv-tabs::-webkit-scrollbar{display:none}
.pv-tabs a{flex:none;margin:0;text-decoration:none;color:var(--c);font:700 .86rem system-ui;padding:9px 15px;border-radius:999px;border:1px solid var(--e)}
.pv-tabs a.on{background:var(--c);color:var(--g);border-color:var(--c)}
@media(min-width:960px){.pv-tabs{margin:20px 0 0;padding:10px 0}}
.pv-cols{display:grid;gap:22px;grid-template-columns:minmax(0,1fr);grid-template-areas:"main" "side" "about";margin-top:20px}
.pv-main{grid-area:main}.pv-side{grid-area:side}.pv-about{grid-area:about;display:flex;flex-direction:column;gap:12px;min-width:0}
@media(min-width:960px){.pv-cols{grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);grid-template-areas:"main side" "about side";grid-template-rows:auto 1fr;align-items:start}.pv-about{margin-top:-8px}}
.pv-main,.pv-side{display:flex;flex-direction:column;gap:14px;min-width:0}
.pv h2.pv-h{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin:14px 0 0;font:850 1.3rem system-ui;letter-spacing:-.01em;scroll-margin-top:70px}
.pv h2.pv-h small{font:500 .82rem system-ui;color:var(--s)}.pv h2.pv-h a{font:700 .84rem system-ui;color:var(--v);text-decoration:none}
.pv-form{display:grid;grid-template-columns:repeat(var(--n,6),minmax(0,1fr));gap:6px}
.pv-form i{font-style:normal;text-align:center;border-radius:12px;padding:8px 0;background:rgba(255,255,255,.07);color:var(--s)}
.pv-form i.w{background:var(--v);color:var(--g)}.pv-form i b{display:block;font:900 .95rem system-ui}.pv-form i small{display:block;font:700 .64rem system-ui;opacity:.8}
.pv-note{font:500 .74rem system-ui;color:var(--s)}
.pv-ev{background:var(--deep);border:1px solid var(--e);border-radius:var(--pr);overflow:hidden}
.pv-ev .hd{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:14px 16px}
.pv-ev .hd b{display:block;font:800 1.05rem system-ui}.pv-ev .hd b a{color:inherit;text-decoration:none}.pv-ev .hd span{font:500 .78rem system-ui;color:var(--s)}
.pv-ev .hd .pv-badge{flex:none;font:800 .74rem system-ui;border-radius:999px;padding:5px 10px;background:rgba(255,255,255,.1);color:var(--c);white-space:nowrap}
.pv-ev .hd .pv-badge.pv-ttl{background:var(--v);color:var(--g)}
.pv-row{position:relative;display:grid;grid-template-columns:40px minmax(0,1fr) auto 14px;gap:10px;align-items:center;padding:11px 16px;border-top:1px solid var(--e)}
.pv-row:hover{background:rgba(255,255,255,.03)}
.pv-row .pv-rd{font:800 .7rem system-ui;color:var(--s)}
.pv-row .pv-op{min-width:0;display:block}.pv-row .pv-op b{display:block;font:600 .93rem system-ui;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pv-row .pv-op b a{position:relative;z-index:2;color:inherit;text-decoration:none}.pv-row .pv-op b a:hover{text-decoration:underline}
.pv-row .pv-op span{display:block;font:500 .74rem system-ui;color:var(--s)}
.pv-row .pv-sc{border:0;font:800 .95rem system-ui;font-variant-numeric:tabular-nums;color:var(--v);text-decoration:none;white-space:nowrap}
.pv-row .pv-sc::after{content:"";position:absolute;inset:0;z-index:1}.pv-row .pv-sc i{font-style:normal;margin-left:.45em}.pv-row .pv-sc i:first-child{margin-left:0}.pv-row .pv-sc sup{font-size:.62em;opacity:.8}
.pv-row.u .pv-sc{color:var(--c);font-size:.8rem}.pv-row.l .pv-sc{color:#ff9a8a}.pv-row .pv-wl{font:900 .7rem system-ui;color:var(--s)}.pv-row.l .pv-wl{color:#ff9a8a}
.pv-more{border:1px solid var(--e);border-radius:var(--pr);background:transparent}
.pv-more>summary{cursor:pointer;list-style:none;padding:13px 16px;font:700 .9rem system-ui;color:var(--v);text-align:center}
.pv-more>summary::-webkit-details-marker{display:none}.pv-more[open]>summary{border-bottom:1px solid var(--e)}
.pv-more .in{display:flex;flex-direction:column;gap:12px;padding:12px}
.pv-two{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.pv-big{font:900 1.9rem/1.1 system-ui;letter-spacing:-.02em;margin:2px 0}
.pv-sub{font:500 .78rem system-ui;color:var(--s)}.pv-sub a{color:inherit}
.pv-bars{display:flex;flex-direction:column;gap:12px}
.pv-bar .t{display:flex;justify-content:space-between;gap:8px;font:600 .84rem system-ui}.pv-bar .t span{font-weight:500;color:var(--s);font-variant-numeric:tabular-nums}
.pv-bar .tr{height:8px;background:var(--g);border-radius:999px;margin-top:6px;overflow:hidden}.pv-bar .tr i{display:block;height:100%;border-radius:999px;background:var(--v)}
.pv-three{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.pv-three div{background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:12px 6px;text-align:center;min-width:0}
.pv-three span{display:block;font:500 .74rem system-ui;color:var(--s)}.pv-three b{display:block;font:800 1.1rem system-ui}.pv-three i{font:800 .72rem system-ui;font-style:normal;color:var(--v)}
.pv-yrs{width:100%;border-collapse:collapse;font:500 .88rem system-ui;font-variant-numeric:tabular-nums}
.pv-yrs td,.pv-yrs th{padding:8px 4px;border-top:1px solid var(--e);text-align:left}.pv-yrs th{font:800 .68rem system-ui;letter-spacing:.1em;text-transform:uppercase;color:var(--s);border-top:0}
.pv-yrs td:last-child,.pv-yrs th:last-child{text-align:right}
.pv-share{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;border:1px solid var(--e);background:transparent;color:var(--c);
font:700 .9rem system-ui;padding:13px;border-radius:14px;cursor:pointer}
.pv-share:hover{border-color:var(--v)}
.pv-about p{margin:0;font:400 1rem/1.7 system-ui;color:var(--c);opacity:.92;max-width:70ch}.pv-about p a{color:var(--v)}
.pv-links{display:flex;flex-wrap:wrap;gap:8px}
.pv-links a,.pv-links span{display:inline-flex;align-items:center;gap:6px;background:var(--deep);border:1px solid var(--e);border-radius:999px;padding:7px 12px;
font:600 .84rem system-ui;color:var(--c);text-decoration:none}.pv-links b{color:var(--v)}.pv-links span a{border:0;background:none;padding:0}.pv-links a:hover{border-color:var(--v)}
.pv-next{display:flex;justify-content:space-between;align-items:center;gap:10px}.pv-next b{font:800 1.05rem system-ui}
.pv .nlc{margin:8px 0}
.pv h2.ui-sec{margin:14px 0 0}.pv h2.ui-sec,.pv h2.ui-sec span{font:850 1.3rem system-ui!important;color:var(--c)!important;letter-spacing:-.01em}.pv .pd-elo{margin:0}
.pv h2.dh{font:850 1.3rem system-ui;color:var(--c)}
@media(min-width:960px){.pv-side .nlc{flex-direction:column;align-items:flex-start;gap:14px}.pv-side .nlc-cov{display:none}}
"""

TABS_JS = ("<script>(function(){var t=document.querySelector('.pv-tabs');if(!t||!('IntersectionObserver' in window))return;"
           "var a=[].slice.call(t.querySelectorAll('a'));var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){"
           "a.forEach(function(x){x.classList.toggle('on',x.getAttribute('href')=='#'+e.target.id)})}})},{rootMargin:'-30% 0px -60% 0px'});"
           "a.forEach(function(x){var s=document.getElementById(x.getAttribute('href').slice(1));if(s)io.observe(s)})})();"
           "document.addEventListener('click',function(e){var b=e.target.closest('.pv-share');if(!b)return;var u=location.href.split('#')[0],"
           "d={title:document.title,url:u};if(navigator.share){navigator.share(d).catch(function(){})}else if(navigator.clipboard){"
           "navigator.clipboard.writeText(u);b.lastChild.textContent=' Link copied'}});</script>")


def _name_size(name):
    """Tamanho do nome para que a palavra mais comprida caiba numa linha (nunca parte a meio, como 'WATANUK/I')."""
    longest = max((len(w) for w in (name or "?").split()), default=1)
    return ("2.9rem" if longest <= 8 else "2.45rem" if longest <= 10 else "2.1rem" if longest <= 12 else "1.75rem" if longest <= 15 else "1.45rem")


def hero(back_href, back_label, photo, name, chips, pill="", credit="", pill_href=""):
    """Topo: foto (ou iniciais), estado mais recente, nome e factos. chips: lista de HTML já escapado."""
    words = (name or "?").split()
    ini = "".join(w[0] for w in words[:2]).upper()
    pic = (f'<img class="big" src="{esc(photo)}" alt="{esc(name)}" width="600" height="750" fetchpriority="high">' if photo
           else f'<div class="ini" aria-hidden="true">{esc(ini)}</div>')
    pl = ""
    if pill:
        pl = (f'<a class="pv-pill" href="{esc(pill_href)}">{pill}</a>' if pill_href else f'<span class="pv-pill">{pill}</span>')
    ch = ('<div class="pv-chips">' + "".join(f"<span>{c}</span>" if not c.startswith("<a") else c for c in chips if c) + "</div>") if chips else ""
    big = _name_size(name)
    return (f'<a class="pv-back" href="{esc(back_href)}">← {esc(back_label)}</a>'
            f'<section class="pv-hero{"" if photo else " np"}">{pic}'
            f'<div class="tx">{pl}<h1 style="--fs:{big}">{" ".join(f"<span>{esc(w)}</span>" for w in words)}</h1>{ch}</div>'
            f'{f"<p class=pv-cr>{credit}</p>" if credit else ""}</section>')


def sparkline(pts, W=560, H=120, label="Ranking over time"):
    """pts = [(x_frac 0..1, y_frac 0..1)] já normalizados (0 = melhor). Devolve o SVG do gráfico do cartão do ranking."""
    if len(pts) < 2:
        return ""
    xy = [(round(x * W, 1), round(y * H, 1)) for x, y in pts]
    best = min(xy, key=lambda p: (p[1], -p[0]))
    lx, ly = xy[-1]
    ve = 'vector-effect="non-scaling-stroke"'
    dot = lambda x, y, w, c: f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y}" stroke="{c}" stroke-width="{w}" stroke-linecap="round" {ve}/>'
    return (f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="{esc(label)}">'
            f'<line x1="0" y1="{best[1]}" x2="{W}" y2="{best[1]}" stroke="var(--v)" stroke-opacity=".25" stroke-dasharray="3 5" {ve}/>'
            f'<polyline points="{" ".join(f"{x},{y}" for x, y in xy)}" fill="none" stroke="var(--v)" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round" {ve}/>'
            + dot(*best, 10, "var(--v)") + dot(*best, 5, "var(--deep)") + dot(lx, ly, 15, "var(--deep)") + dot(lx, ly, 10, "var(--v)") + "</svg>")


def rank_card(label, rank, change=None, pts="", pts_label="points", chart="", axis=(), minis=(), src=""):
    """Cartão do ranking: número grande, variação, pontos, gráfico e 3 números pequenos [(valor, legenda)]."""
    if not rank and not chart and not minis:
        return ""
    chg = ""
    if isinstance(change, int) and change:
        chg = f'<span class="ch {"pv-up" if change > 0 else "pv-dn"}">{"▲" if change > 0 else "▼"} {abs(change)}</span>'
    p = f'<span class="pts"><strong>{esc(str(pts))}</strong>{esc(pts_label)}</span>' if pts not in ("", None) else ""
    num = f'<div class="num"><b>{esc(str(rank))}</b>{chg}{p}</div>' if rank else f'<div class="num">{p}</div>'
    ax = ('<div class="pv-axis">' + "".join(f"<span>{esc(a)}</span>" for a in axis) + "</div>") if axis and chart else ""
    mn = ('<div class="pv-minis">' + "".join(f'<div><b>{v}</b><span>{esc(k)}</span></div>' for v, k in list(minis)[:3]) + "</div>") if minis else ""
    s = f'<div class="pv-src">{src}</div>' if src else ""
    return f'<section class="pv-card pv-rank{"" if chart else " nc"}" aria-label="{esc(label)}"><div class="pv-lab">{esc(label)}</div>{num}{chart}{ax}{mn}{s}</section>'


def tabs(items):
    """[(id, rótulo)] — ligações para as partes da página."""
    return ('<nav class="pv-tabs" aria-label="Sections">' + "".join(f'<a href="#{i}"{" class=on" if k == 0 else ""}>{esc(t)}</a>'
                                                                  for k, (i, t) in enumerate(items)) + "</nav>")


def form(items):
    """[(ganhou, texto pequeno)] — os últimos jogos, do mais recente para o mais antigo."""
    if not items:
        return ""
    return (f'<div class="pv-form" style="--n:{max(len(items), 5)}" aria-label="Last matches, newest first">'
            + "".join(f'<i class="{"w" if w else ""}"><b>{"W" if w else "L"}</b><small>{esc(s)}</small></i>' for w, s in items) + "</div>")


def event(title_html, sub, badge, rows, title_badge=False):
    """Um torneio: cabeçalho e uma linha por jogo. rows = [(ronda, nome_html, sub, resultado_html, href, ganhou)]."""
    b = f'<span class="pv-badge{" pv-ttl" if title_badge else ""}">{esc(badge)}</span>' if badge else ""
    out = f'<div class="pv-ev"><div class="hd"><div><b>{title_html}</b><span>{esc(sub)}</span></div>{b}</div>'
    for rd, nm, s, sc, href, won in rows:
        scs = f'<a class="pv-sc" href="{esc(href)}">{sc}</a>' if href else f'<span class="pv-sc">{sc}</span>'
        cls = " u" if won is None else "" if won else " l"
        out += (f'<div class="pv-row{cls}"><span class="pv-rd">{esc(rd)}</span><span class="pv-op"><b>{nm}</b>'
                f'<span>{esc(s)}</span></span>{scs}<span class="pv-wl">{"" if won is None else "W" if won else "L"}</span></div>')
    return out + "</div>"


def more(label, inner):
    return f'<details class="pv-more"><summary>{esc(label)}</summary><div class="in">{inner}</div></details>' if inner else ""


def bars(label, items):
    """[(nome, 'V-D', percentagem)]"""
    items = [x for x in items if x]
    if not items:
        return ""
    return (f'<div class="pv-card"><div class="pv-lab">{esc(label)}</div><div class="pv-bars" style="margin-top:12px">'
            + "".join(f'<div class="pv-bar"><div class="t">{esc(n)}<span>{esc(wl)} · {p}%</span></div><div class="tr"><i style="width:{p}%"></i></div></div>'
                      for n, wl, p in items) + "</div></div>")


def three(items):
    """[(rótulo, valor, pequeno)] — 3 caixas (pisos)."""
    items = [x for x in items if x][:3]
    if not items:
        return ""
    return ('<div class="pv-three">' + "".join(f'<div><span>{esc(a)}</span><b>{esc(b)}</b><i>{esc(c)}</i></div>' for a, b, c in items) + "</div>")


def stat_card(label, big, sub_html=""):
    return f'<div class="pv-card"><div class="pv-lab">{esc(label)}</div><div class="pv-big">{esc(big)}</div><div class="pv-sub">{sub_html}</div></div>'


def h2(id_, title, right=""):
    return f'<h2 class="pv-h"{f" id={id_!r}" if id_ else ""}>{title}{right}</h2>'


def share(label="Share this profile"):
    return ('<button type="button" class="pv-share"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" '
            'aria-hidden="true"><path d="M12 3v13M7 8l5-5 5 5M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5"/></svg><span> ' + esc(label) + "</span></button>")


def page(top_left, top_right, tabs_html, main, side, bottom=""):
    """Junta tudo: topo (foto + ranking), separadores, duas colunas e o fundo (sobre o jogador, ligações)."""
    return (f'<style>{CSS}</style><div class="pv"><div class="pv-top"><div>{top_left}</div>{top_right}</div>{tabs_html}'
            f'<div class="pv-cols"><div class="pv-main">{main}</div><aside class="pv-side">{side}</aside><div class="pv-about">{bottom}</div></div></div>{TABS_JS}')


def score(games_me, games_op, tb_me=None, tb_op=None):
    """'7-6⁵ 6-4' do ponto de vista do jogador (tie-break: pontos de quem perdeu o set)."""
    out = []
    for k, (a, b) in enumerate(zip(games_me, games_op)):
        sup = ""
        src = tb_op if (a == 7 and b == 6) else tb_me if (a == 6 and b == 7) else None
        if src is not None:
            try:
                v = src[k]
            except (IndexError, TypeError, KeyError):
                v = None
            if v is not None:
                sup = f"<sup>{int(v)}</sup>"
        out.append(f"<i>{a}-{b}{sup}</i>")
    return "".join(out)


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "")


# ---------------------------------------------------------------- página do jogo, versão 2 (13/11/2026)
MATCH_CSS = """
.mv-hero{position:relative;border-radius:28px;overflow:hidden;background:var(--deep);border:1px solid var(--e)}
.mv-top{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:16px 16px 0}
.mv-top .pv-pill{text-decoration:none}.mv-top .pv-pill.ghost{background:rgba(255,255,255,.1);color:var(--c)}
.mv-sides{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;padding:14px 16px 0}
.mv-side{position:relative;border-radius:20px;overflow:hidden;aspect-ratio:4/5;background:radial-gradient(110% 90% at 80% 0,var(--e) 0,var(--g) 65%);
display:flex;align-items:flex-end;text-decoration:none;color:#fff}
.mv-side .ph{position:absolute;inset:0;display:flex}.mv-side .ph img{flex:1;min-width:0;height:100%;object-fit:cover;object-position:50% 18%}
.mv-side .ini{position:absolute;right:-6px;top:-18px;font:900 6.5rem/1 system-ui;color:var(--v);opacity:.12;letter-spacing:-.05em}
.mv-side::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,transparent 40%,rgba(0,0,0,.78) 100%)}
.mv-side.l .ph{filter:grayscale(.65) brightness(.62)}
.mv-side .nm{position:relative;z-index:1;padding:12px;display:flex;flex-direction:column;gap:3px;min-width:0;width:100%}
.mv-side .nm b{font:900 1.15rem/1.02 system-ui;letter-spacing:-.01em;text-transform:uppercase;overflow-wrap:anywhere}
.mv-side .nm span{font:600 .76rem system-ui;color:rgba(255,255,255,.82)}
.mv-side .wtag{position:absolute;z-index:1;left:10px;top:10px;background:var(--v);color:var(--g);font:900 .66rem system-ui;letter-spacing:.08em;border-radius:999px;padding:4px 9px}
.mv-board{padding:14px 16px 16px}
.mv-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;padding:8px 0}.mv-row+.mv-row{border-top:1px solid var(--e)}
.mv-row .who{min-width:0;font:700 1rem system-ui;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--s)}.mv-row.w .who{color:var(--c)}
.mv-row .who a{color:inherit;text-decoration:none}.mv-row .who small{font:500 .78rem system-ui;color:var(--s);margin-left:6px}
.mv-sets{display:flex;gap:6px}.mv-sets span{min-width:40px;height:44px;padding:0 6px;border-radius:12px;display:flex;align-items:center;justify-content:center;font:900 1.35rem system-ui;
background:rgba(255,255,255,.06);color:var(--s);font-variant-numeric:tabular-nums}.mv-sets span.on{background:var(--v);color:var(--g)}
.mv-sets sup{font-size:.5em;margin-left:1px;align-self:flex-start;margin-top:7px}
.mv-story p{margin:0;font:400 1.02rem/1.7 system-ui;max-width:70ch}.mv-story p a{color:var(--v)}
.mv-setbars{display:flex;flex-direction:column;gap:10px}
.mv-sb{display:grid;grid-template-columns:44px minmax(0,1fr) 54px;gap:10px;align-items:center;font:700 .82rem system-ui}
.mv-sb .lab{color:var(--s)}.mv-sb .tr{display:flex;height:10px;border-radius:999px;overflow:hidden;background:var(--g)}
.mv-sb .tr i{display:block;height:100%}.mv-sb .tr i.a{background:var(--v)}.mv-sb .tr i.b{background:rgba(255,255,255,.22)}.mv-sb .tr i.b.hi{background:#ff9a8a}
.mv-sb .sc{text-align:right;font-variant-numeric:tabular-nums}
.mv-roads{display:grid;gap:12px;grid-template-columns:minmax(0,1fr)}
@media(min-width:700px){.mv-roads{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(min-width:960px){
.mv-hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr) minmax(0,1fr);align-items:stretch}
.mv-top{grid-column:1/-1;justify-content:center;padding:18px 18px 0}
.mv-sides{display:contents}.mv-side{aspect-ratio:auto;min-height:400px;border-radius:0;margin:18px 0 0}
.mv-side.a{grid-column:1;grid-row:2;border-radius:0 0 0 28px}.mv-side.b{grid-column:3;grid-row:2;border-radius:0 0 28px 0}
.mv-side .nm b{font-size:1.6rem}
.mv-board{grid-column:2;grid-row:2;display:flex;flex-direction:column;justify-content:center;padding:26px 28px;margin-top:18px}
.mv-sets span{min-width:52px;height:56px;font-size:1.7rem}
}
"""


def vs_hero(pills, sides, rows):
    """Topo da página do jogo. pills: [(texto, href, destaque)]; sides: 2 x {photos:[src], ini, name, sub, href, won};
    rows: 2 x (nome_html, sub, [(jogos, ganhou_set, tb_html)], ganhou)."""
    pl = "".join((f'<a class="pv-pill{"" if hi else " ghost"}" href="{esc(h)}">{t}</a>' if h else f'<span class="pv-pill{"" if hi else " ghost"}">{t}</span>')
                 for t, h, hi in pills if t)
    sd = ""
    for k, s in enumerate(sides):
        ph = "".join(f'<img src="{esc(x)}" alt="" width="600" height="750"{" fetchpriority=high" if k == 0 else ""}>' for x in s.get("photos") or [])
        ph = f'<div class="ph">{ph}</div>' if ph else f'<div class="ini" aria-hidden="true">{esc(s.get("ini") or "")}</div>'
        cls = f'mv-side {"a" if k == 0 else "b"}{"" if s.get("won") is None else " w" if s["won"] else " l"}'
        tag = '<span class="wtag">WINNER</span>' if s.get("won") else ""
        inner = f'{ph}{tag}<div class="nm"><b>{s["name"]}</b><span>{esc(s.get("sub") or "")}</span></div>'
        sd += f'<a class="{cls}" href="{esc(s["href"])}">{inner}</a>' if s.get("href") else f'<div class="{cls}">{inner}</div>'
    bd = ""
    for nm, sub, sets, won in rows:
        cells = "".join(f'<span class="{"on" if on else ""}">{g}{tb}</span>' for g, on, tb in sets)
        bd += f'<div class="mv-row{" w" if won else ""}"><div class="who">{nm}<small>{esc(sub)}</small></div><div class="mv-sets">{cells}</div></div>'
    return (f'<style>{CSS}{MATCH_CSS}</style><section class="mv-hero"><div class="mv-top">{pl}</div><div class="mv-sides">{sd}</div>'
            f'<div class="mv-board">{bd}</div></section>')


def set_bars(sets, names):
    """Barras set a set: [(jogos_a, jogos_b)]. names = (a, b) para a legenda."""
    out = ""
    for k, (a, b) in enumerate(sets):
        t = max(1, a + b)
        out += (f'<div class="mv-sb"><span class="lab">Set {k + 1}</span><div class="tr" aria-hidden="true"><i class="a" style="width:{100 * a / t:.0f}%"></i>'
                f'<i class="b{" hi" if b > a else ""}" style="width:{100 * b / t:.0f}%"></i></div><span class="sc">{a}-{b}</span></div>')
    return (f'<div class="pv-card"><div class="pv-lab" style="margin-bottom:12px">Set by set · {esc(names[0])} vs {esc(names[1])}</div>'
            f'<div class="mv-setbars">{out}</div></div>') if out else ""


def match_page(hero, story, main, side):
    return (f'<div class="pv">{hero}<div class="pv-cols" style="grid-template-areas:\'main\' \'side\'"><div class="pv-main">{story}{main}</div>'
            f'<aside class="pv-side">{side}</aside></div></div>'
            '<style>@media(min-width:960px){.pv .pv-cols{grid-template-areas:"main side"!important}}</style>' + TABS_JS)
