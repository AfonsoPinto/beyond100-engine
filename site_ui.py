"""Peças de página comuns ao ténis e ao padel (o mesmo molde, só mudam as cores, que vêm das variáveis --g --deep --c --v --s --e
de cada site). Usar estas em vez de inventar estilos por vertente."""
import html
import re

esc = html.escape

CSS = """
nav div a.ntop.on{color:var(--v)}
/* cartões "Playing now" (ténis e padel, mesmo molde) */
.lvg{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin-bottom:10px}
.lv{background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:10px 14px}
.lv .lh{font-size:.74rem;color:var(--s);margin-bottom:4px;display:flex;align-items:center;gap:6px}
.lv .lh>span:first-child{white-space:nowrap;flex:none}.lv .lh .lgo{margin-left:auto;color:var(--v);font-size:1.1rem;line-height:1}
.lv .pl{display:flex;justify-content:space-between;align-items:center;padding:3px 0}
.lv .who{display:flex;align-items:center;gap:8px;min-width:0;flex:1}.lv .who>div{min-width:0}.lv .who .nm{display:block;line-height:1.2}.lv .who small{display:block;margin:0;color:var(--s)}
.lv .sc{display:flex;gap:4px;white-space:nowrap;margin-left:8px;font:700 .95rem Georgia,serif;color:var(--v)}.lv .sc span,.lv .sc b{min-width:1.3em;text-align:center}
.lv .sc b:not(.on){color:var(--c)}.lv .sc i{font-size:.6em;vertical-align:super;font-style:normal;color:var(--s)}.lv .sc .tm{font:700 .8rem system-ui;color:var(--v)}
a.lv{display:block;text-decoration:none;color:inherit;transition:border-color .15s}a.lv:hover{border-color:var(--v)}

.ui-hero{display:flex;gap:16px;align-items:center;padding:6px 0 18px}.ui-hero .em svg{width:84px;height:84px;display:block}
.ui-hero h1{margin:0 0 4px;font-size:1.7rem;line-height:1.15}.ui-hero h1 em{color:var(--v)}.ui-hero p{margin:0;color:var(--s);font-size:.92rem}
.ui-hero .cta{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.ui-hero .cta a{display:inline-flex;align-items:center;gap:6px;border-radius:999px;padding:8px 14px;font:700 .85rem system-ui;text-decoration:none;border:1px solid var(--e);color:var(--c)}
.ui-hero .cta a.go{background:var(--v);border-color:var(--v);color:var(--g)}
.ui-sec{display:flex;justify-content:space-between;align-items:baseline;gap:10px;margin:26px 0 10px;font:700 1.25rem Georgia,serif;color:var(--v)}
.ui-sec a{font:600 .82rem system-ui;color:var(--s);text-decoration:none;white-space:nowrap}
.ui-row{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(210px,72%);gap:10px;overflow-x:auto;padding:2px 0 10px;scroll-snap-type:x mandatory;scrollbar-width:none}
.ui-row::-webkit-scrollbar{display:none}.ui-row>*{scroll-snap-align:start}
.ui-champ{display:flex;flex-direction:column;gap:5px;text-decoration:none;color:inherit;background:var(--deep);border:1px solid var(--e);border-radius:18px;padding:14px;min-width:0}
.ui-champ .top{display:flex;align-items:center;gap:10px}.ui-champ .av,.ui-champ .ini{width:46px;height:46px;border-radius:50%;object-fit:cover;flex:none;
background:rgba(255,255,255,.08);display:grid;place-items:center;font:800 .85rem system-ui;color:var(--v)}
.ui-champ .tag{align-self:flex-start;background:var(--v);color:var(--g);font:800 .62rem system-ui;letter-spacing:.08em;padding:3px 8px;border-radius:6px;text-transform:uppercase}
.ui-champ small{font:700 .66rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--v)}
.ui-champ b{font:700 1.08rem/1.2 Georgia,serif}.ui-champ .w{font:700 1rem/1.2 system-ui;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.ui-champ .n{color:var(--s);font-size:.8rem}
.ui-quick{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:24px 0 6px}
.ui-quick a{background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:13px;text-decoration:none;color:inherit}
.ui-quick b{display:block;font:700 1rem Georgia,serif}.ui-quick span{color:var(--s);font-size:.8rem}
.ui-mt{display:flex;gap:12px;align-items:stretch;background:var(--deep);border:1px solid var(--e);border-radius:18px;padding:12px 14px;text-decoration:none;color:inherit;min-width:0}
a.ui-mt:hover{border-color:var(--v)}.ui-mt.live{border-color:rgba(229,72,77,.7);box-shadow:0 0 0 1px rgba(229,72,77,.25) inset}
.ui-mt .mtt{flex:none;width:54px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;border-right:1px solid var(--e);padding-right:10px;margin-right:2px}
.ui-mt .mtt time,.ui-mt .mtt b{font:800 1rem system-ui;color:var(--v);letter-spacing:.01em}.ui-mt .mtt small{font:600 .62rem system-ui;color:var(--s);text-transform:uppercase;letter-spacing:.08em;text-align:center}
.ui-mt .mtb{flex:1;min-width:0}.ui-mt .mth{display:flex;align-items:center;gap:6px;font:600 .72rem system-ui;color:var(--s);margin-bottom:4px;flex-wrap:wrap}
.ui-mt .mth .ct{border:1px solid var(--e);border-radius:999px;padding:1px 8px}.ui-mt .lvb{background:#cf3339;color:#fff;font:800 .6rem system-ui;letter-spacing:.08em;padding:2px 7px;border-radius:999px}
.ui-mt .ft{background:rgba(255,255,255,.08);color:var(--c);font:800 .6rem system-ui;letter-spacing:.08em;padding:2px 7px;border-radius:999px;text-transform:uppercase}
.ui-mt .pl{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:3px 0;border:0!important;color:inherit}.ui-mt .pl .nm{font:600 .95rem system-ui;color:var(--c);text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.ui-mt .pl .who{display:flex;align-items:center;gap:6px;min-width:0;flex:1}.ui-mt .pl small{color:var(--s);font:600 .72rem system-ui;flex:none}
.ui-mt .pl.w .nm{color:var(--v)}.ui-mt .pl.l .nm{color:var(--s)}
.ui-mt .sc{display:flex;gap:4px;flex:none}.ui-mt .sc span{min-width:22px;height:22px;padding:0 4px;display:inline-flex;align-items:center;justify-content:center;border-radius:6px;background:rgba(255,255,255,.06);font:700 .8rem system-ui;color:var(--c)}
.ui-mt .sc span.on{background:var(--v);color:var(--g)}.ui-mt .sc sup{font-size:.62em;align-self:flex-start;margin:3px 0 0 1px;opacity:.8}
.ui-mts{display:grid;gap:8px;grid-template-columns:minmax(0,1fr)}@media(min-width:760px){.ui-mts{grid-template-columns:1fr 1fr}}
.ui-rk{display:grid;gap:6px;grid-template-columns:minmax(0,1fr)}.ui-rk .r[hidden]{display:none}.ui-rk .r{min-width:0;display:flex;align-items:center;gap:12px;background:var(--deep);border:1px solid var(--e);border-radius:14px;padding:9px 12px}
.ui-rk .rn{flex:none;width:34px;font:800 1rem system-ui;color:var(--v);text-align:center}.ui-rk .r.t3 .rn{font-size:1.25rem}
.ui-rk .av,.ui-rk .ini{width:34px;height:34px;border-radius:50%;object-fit:cover;flex:none;background:rgba(255,255,255,.08)}
.ui-rk .rw{flex:1;min-width:0}.ui-rk .rw span.nm a{display:inline;color:inherit;text-decoration:none}.ui-stk{display:flex;flex:none}.ui-stk>*{box-shadow:0 0 0 2px var(--deep)}.ui-stk>*+*{margin-left:-12px}.ui-rk .rw>a,.ui-rk .rw span.nm{display:block;font:600 .95rem/1.2 system-ui;color:var(--c);text-decoration:none;overflow-wrap:anywhere}
.ui-rk .rw small{color:var(--s);font-size:.74rem}.ui-rk .rp{flex:none;text-align:right;font:700 .9rem system-ui}.ui-rk .rp small{display:block;color:var(--s);font:600 .66rem system-ui;text-transform:uppercase;letter-spacing:.06em}
.ui-rk .rm{flex:none;min-width:40px;text-align:center;border-radius:999px;padding:3px 8px;font:800 .72rem system-ui;background:rgba(255,255,255,.06);color:var(--s)}
.ui-rk .rm.up{background:rgba(217,242,61,.16);color:var(--v)}.ui-rk .rm.dn{background:rgba(229,72,77,.16);color:#f3a0a0}
.ui-sb{background:var(--deep);border:1px solid var(--e);border-radius:20px;padding:6px 14px 10px;margin:14px 0}.ui-sb.live{border-color:rgba(229,72,77,.55)}
.ui-sb .hd,.ui-sb .r{display:flex;align-items:center;gap:10px}.ui-sb .hd{justify-content:flex-end;padding:6px 0 2px}
.ui-sb .cols{display:flex;gap:6px;flex:none}.ui-sb .cols>*{width:34px;text-align:center}.ui-sb .hd .cols>*{font:700 .62rem system-ui;letter-spacing:.1em;color:var(--s);text-transform:uppercase}
.ui-sb .r{padding:10px 0}.ui-sb .r+.r{border-top:1px solid var(--e)}.ui-sb .who{flex:1;min-width:0;display:flex;align-items:center;gap:10px}
.ui-sb .who .av{width:40px;height:40px;border-radius:50%;object-fit:cover;flex:none}.ui-sb .who b{display:block;font:700 1.02rem/1.2 system-ui;color:var(--c)}
.ui-sb .who b a{color:inherit;text-decoration:none}.ui-sb .who small{display:block;color:var(--s);font:600 .74rem system-ui;margin-top:2px}
.ui-sb .r.l .who b{color:var(--s)}.ui-sb .srv{width:8px;height:8px;border-radius:50%;background:var(--v);flex:none;visibility:hidden}.ui-sb .r.sv .srv{visibility:visible}
.ui-sb .cols span{height:34px;display:inline-flex;align-items:center;justify-content:center;border-radius:9px;background:rgba(255,255,255,.06);font:800 1rem system-ui;color:var(--c)}
.ui-sb .cols span.on{background:var(--v);color:var(--g)}.ui-sb .cols span.cur{box-shadow:0 0 0 2px var(--v) inset;background:none;color:var(--v)}
.ui-sb .cols span sup{font-size:.6em;align-self:flex-start;margin:5px 0 0 1px;opacity:.8}.ui-sb .cols span.gp{background:none;color:var(--v);font-size:.95rem}
.ui-sb .nt{color:var(--s);font:600 .72rem system-ui;margin:6px 0 0}
.ui-cmp{display:grid;gap:14px;background:var(--deep);border:1px solid var(--e);border-radius:20px;padding:16px}
.ui-cmp .hh{display:flex;justify-content:space-between;font:700 .8rem system-ui;color:var(--s)}.ui-cmp .hh b{color:var(--c)}
.ui-cmp .c{display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:4px 10px}.ui-cmp .c>b{font:800 1.05rem system-ui;color:var(--c)}.ui-cmp .c>b:last-of-type{text-align:right}
.ui-cmp .c>span{font:600 .74rem system-ui;color:var(--s);text-align:center;text-transform:uppercase;letter-spacing:.06em}
.ui-cmp .bar{grid-column:1/-1;display:flex;gap:4px;height:6px}.ui-cmp .bar i{display:block;border-radius:6px;background:rgba(255,255,255,.12)}.ui-cmp .bar i.hi{background:var(--v)}
.ui-cmp .c.tx>b{font-size:.95rem}
.ui-seg{display:flex;gap:4px;background:var(--deep);border:1px solid var(--e);border-radius:999px;padding:4px;margin:12px 0}
.ui-seg button{flex:1;border:0;background:none;color:var(--s);font:700 .9rem system-ui;padding:9px;border-radius:999px;cursor:pointer}.ui-seg button.on{background:var(--v);color:var(--g)}
.ui-dc{display:flex;align-items:center;gap:12px;background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:10px 14px;margin:12px 0 0}
.ui-dc .ic{flex:none;width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:rgba(217,242,61,.14);color:var(--v)}
.ui-dc .ic svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.ui-dc small{display:block;font:700 .64rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--s)}.ui-dc b{font:700 1.02rem system-ui;color:var(--c)}.ui-dc b a{color:inherit}
.ui-dc .st{margin-left:auto;flex:none;border-radius:999px;padding:3px 10px;font:800 .7rem system-ui}.ui-dc .st.up{background:rgba(217,242,61,.16);color:var(--v)}.ui-dc .st.dn{background:rgba(229,72,77,.16);color:#f3a0a0}
.ui-row.wide{grid-auto-columns:minmax(270px,88%)}@media(min-width:760px){.ui-row.wide{grid-auto-columns:calc(50% - 5px)}.ui-row{grid-auto-columns:calc(33.3% - 7px)}.ui-quick{grid-template-columns:repeat(4,1fr)}}
"""


def hero(emblem_svg, h1a, h1b, text, ctas=()):
    """Topo compacto: emblema à esquerda, título e frase à direita, botões opcionais [(label, href, primary)]."""
    c = "".join(f'<a class="{"go" if p else ""}" href="{esc(h)}">{esc(l)}</a>' for l, h, p in ctas)
    return (f'<section class="ui-hero"><div class="em">{emblem_svg}</div><div><h1>{esc(h1a)} <em>{esc(h1b)}</em></h1>'
            f'<p>{esc(text)}</p>{f"<div class=cta>{c}</div>" if c else ""}</div></section>')


def sec(title, link=None, label=""):
    return f'<h2 class="ui-sec"><span>{title}</span>{f"<a href={esc(link)!r}>{esc(label)} →</a>" if link else ""}</h2>'


def champ_card(href, tag, place, label, winner, note, avatar_html=""):
    """Cartão de campeão: etiqueta, foto + nome do campeão em destaque, depois o torneio e o resultado."""
    return (f'<a class="ui-champ" href="{esc(href)}"><span class="tag">{esc(tag)}</span><div class="top">{avatar_html}'
            f'<div style="min-width:0"><small>{esc(label)}</small><div class="w">{winner}</div></div></div>'
            f'<b>{esc(place)}</b><div class="n">{esc(note)}</div></a>')


def quick(items):
    """[(href, título, descrição)]"""
    return '<div class="ui-quick">' + "".join(f'<a href="{esc(h)}"><b>{esc(t)}</b><span>{esc(d)}</span></a>' for h, t, d in items) + "</div>"


PLAYER_CSS = """
.ui-ph{display:grid;grid-template-columns:116px minmax(0,1fr);gap:16px;align-items:center;background:var(--deep);border:1px solid var(--e);
border-radius:24px;padding:14px;margin:4px 0 12px}
.ui-ph .pic{width:116px;height:145px;border-radius:18px;object-fit:cover;display:block;background:rgba(255,255,255,.06)}
.ui-ph .pic.sq{height:116px}.ui-ph .pic.ini{display:grid;place-items:center;font:800 2rem Georgia,serif;color:var(--v)}
.ui-ph h1{margin:0 0 4px;font-size:1.55rem;line-height:1.12}
.ui-ph .sub{color:var(--s);font-size:.86rem;line-height:1.35}
.ui-ph .rk{display:inline-flex;align-items:center;gap:6px;margin-top:8px;background:var(--v);color:var(--g);font:800 .9rem system-ui;border-radius:999px;padding:4px 11px}
.ui-ph .rk small{font:700 .72rem system-ui;opacity:.75}
.ui-form{display:flex;gap:4px;margin-top:9px}.ui-form i{width:20px;height:20px;border-radius:6px;display:grid;place-items:center;font:800 .6rem system-ui;font-style:normal;
background:rgba(255,255,255,.08);color:var(--s)}.ui-form i.w{background:var(--v);color:var(--g)}
.ui-ph .cr{grid-column:1/-1;margin:0;font-size:.7rem;color:var(--s);opacity:.8}
.ui-tiles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:0 0 14px}
.ui-tiles div{background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:10px 6px;text-align:center;min-width:0}
.ui-tiles b{display:block;font:800 1.2rem/1.1 Georgia,serif;color:var(--v);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ui-tiles span{display:block;margin-top:4px;font:700 .58rem system-ui;letter-spacing:.08em;text-transform:uppercase;color:var(--s)}
.ui-back{display:inline-block;margin:2px 0 8px;color:var(--v);font:600 .88rem system-ui;text-decoration:none}
"""


HERO_CSS = """
.ui-hb{position:relative;min-height:400px;overflow:hidden;border-radius:24px;margin:4px 0 14px;border:1px solid var(--e);
background:radial-gradient(120% 90% at 85% 10%,var(--e) 0,var(--deep) 62%)}
.ui-hb .big{position:absolute;right:-30px;top:0;height:100%;width:72%;object-fit:cover;object-position:55% 15%;
-webkit-mask-image:linear-gradient(90deg,transparent 0,#000 38%);mask-image:linear-gradient(90deg,transparent 0,#000 38%)}
.ui-hb .ini{position:absolute;right:-10px;bottom:-40px;font:800 15rem/1 Georgia,serif;color:var(--v);opacity:.09;letter-spacing:-.05em}
.ui-hb .tx{position:relative;z-index:1;padding:34px 18px 34px;max-width:62%}
.ui-hb h1{font:800 2.5rem/1 Georgia,serif;margin:0 0 12px;text-transform:uppercase;letter-spacing:-.01em;color:#fff;text-shadow:0 2px 12px rgba(0,0,0,.4);overflow-wrap:anywhere}
.ui-hb .sub{color:#e6ece8;font-size:.84rem;line-height:1.5;text-shadow:0 1px 8px rgba(0,0,0,.6)}
.ui-hb .sub a{color:inherit}
.ui-hb .rk{display:inline-flex;align-items:baseline;gap:8px;margin-top:14px;background:var(--v);color:var(--g);font:800 1.15rem Georgia,serif;border-radius:14px;padding:8px 14px}
.ui-hb .rk small{font:800 .8rem system-ui}
.ui-hb .ui-form{margin-top:12px}
.ui-hb .cr{position:absolute;left:18px;right:18px;bottom:8px;margin:0;z-index:1;font-size:.68rem;color:var(--s);opacity:.9}.ui-hb .cr a{color:inherit}
@media(max-width:700px){.ui-hb{margin:4px -16px 14px;border-radius:0;border-width:1px 0}}
.ui-st{background:var(--deep);border:1px solid var(--e);border-radius:20px;overflow:hidden;margin:0 0 18px}
.ui-st .sr{display:grid;grid-template-columns:44px repeat(4,minmax(0,1fr));align-items:center}.ui-st .sr+.sr{border-top:1px solid var(--e)}
.ui-st .sl{align-self:stretch;display:grid;place-items:center;font:800 .6rem system-ui;letter-spacing:.1em;text-transform:uppercase;color:var(--g);background:var(--v);
writing-mode:vertical-rl;transform:rotate(180deg);padding:6px 0}
.ui-st .sr>div{padding:12px 4px;text-align:center;min-width:0}
.ui-st b{display:block;font:800 1.05rem/1.1 Georgia,serif;color:var(--c);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ui-st b.sm{font-size:.86rem}.ui-st b.up{color:var(--v)}.ui-st b.dn{color:#ff8a80}
.ui-st i{display:block;font:700 .56rem/1.3 system-ui;font-style:normal;letter-spacing:.06em;text-transform:uppercase;color:var(--s);margin-top:4px}
"""


def stat_table(rows):
    """Tabela de números por baixo do topo (ténis e padel): [(rótulo, [(valor, legenda, classe), ...4]), ...]."""
    out = ""
    for lab, cells in rows:
        cells = [c for c in cells if c][:4]
        if not cells:
            continue
        cells += [("", "", "")] * (4 - len(cells))
        out += (f'<div class="sr"><span class="sl">{esc(lab)}</span>'
                + "".join(f'<div><b class="{c}{" sm" if len(re.sub("<[^>]+>|&[a-z]+;", "x", str(v))) > 8 else ""}">{v}</b><i>{esc(k)}</i></div>' if v != "" else "<div></div>"
                   for v, k, c in cells) + "</div>")
    return f'<div class="ui-st">{out}</div>' if out else ""


def player_hero(back_href, back_label, photo_src, name, sub, rank=None, rank_note="", form=(), tiles=(), credit_html="", square=False, table=None):
    """Topo da página de jogador (ténis e padel, modelo "B" escolhido a 7/11/2026): nome grande à esquerda, foto grande à direita
    a fundir-se com o fundo, ranking e forma; por baixo a tabela de números (table) ou, sem ela, os 4 números (tiles).
    sub: factos separados por " · " (um por linha)."""
    words = (name or "?").split()
    ini = "".join(w[0] for w in words[:2]).upper()
    longest = max((len(w) for w in words), default=1)
    fs = 2.5 if longest <= 8 else 2.15 if longest <= 10 else 1.85 if longest <= 12 else 1.55
    pic = (f'<img class="big" src="{esc(photo_src)}" alt="{esc(name)}" width="600" height="750" fetchpriority="high">' if photo_src
           else f'<div class="ini" aria-hidden="true">{esc(ini)}</div>')
    rk = f'<span class="rk">No. {rank}{f" <small>{esc(rank_note)}</small>" if rank_note else ""}</span>' if rank else ""
    fm = ('<div class="ui-form" aria-label="last matches">' + "".join(f'<i class="{"w" if x else ""}">{"W" if x else "L"}</i>' for x in form) + "</div>") if form else ""
    t = ('<div class="ui-tiles">' + "".join(f'<div><b>{esc(str(v))}</b><span>{esc(k)}</span></div>' for v, k in tiles) + "</div>") if tiles else ""
    if table:
        t = stat_table(table) or t
    sub_html = (sub or "").replace(" · ", "<br>")
    return (f'<style>{PLAYER_CSS}{HERO_CSS}</style><a class="ui-back" href="{esc(back_href)}">← {esc(back_label)}</a>'
            f'<section class="ui-hb">{pic}<div class="tx"><h1 style="font-size:{fs}rem">{"<br>".join(esc(w) for w in words)}</h1>'
            f'<div class="sub">{sub_html}</div>{rk}{fm}</div>'
            f'{f"<p class=cr>{credit_html}</p>" if credit_html else ""}</section>{t}')


def chips(mine, other, tb=None, done=True):
    """Sets de um jogador em fichas (a verde os que ganhou); tie-break como 7-6⁵ (pontos de quem perdeu o set)."""
    out = ""
    for k, x in enumerate(mine):
        y = other[k] if k < len(other) else None
        last = k == len(mine) - 1
        won = y is not None and x > y and (done or not last)
        t = tb[k] if tb and k < len(tb) else None
        sup = f"<sup>{int(t)}</sup>" if t is not None and x == 6 and y == 7 else ""
        out += f'<span class="{"on" if won else ""}">{x}{sup}</span>'
    return f'<div class="sc">{out}</div>'


def match_tile(time_html, meta, players, badge="", href="", court="", attrs="", live=False):
    """Cartão de jogo (ordem de jogo, próximos jogos): hora à esquerda; ronda, court e estado; dois jogadores com resultado.
    players = [(nome_html, sub_html, chips_html, 'w'|'l'|'')]"""
    tag = "a" if href else "div"
    hr = f' href="{esc(href)}"' if href else ""
    pls = "".join(f'<div class="pl {c}"><div class="who">{n}{f"<small>{s}</small>" if s else ""}</div>{ch}</div>' for n, s, ch, c in players)
    ct = f'<span class="ct">{esc(court)}</span>' if court else ""
    return (f'<{tag} class="ui-mt{" live" if live else ""}"{hr} {attrs}><div class="mtt">{time_html}</div><div class="mtb">'
            f'<div class="mth"><span>{esc(meta)}</span>{ct}<span class="sb">{badge}</span></div>{pls}</div></{tag}>')


def rank_row(n, avatar_html, name_html, sub_html, pts="", move=None, pts_label="pts"):
    """Linha de ranking: posição, foto, nome (+ país), pontos e movimento (+3 / -2 / =)."""
    if move is False:
        mv = ""
    elif isinstance(move, int) and move:
        mv = f'<span class="rm {"up" if move > 0 else "dn"}">{"▲" if move > 0 else "▼"} {abs(move)}</span>'
    elif move in ("up", "down"):
        mv = f'<span class="rm {"up" if move == "up" else "dn"}">{"▲" if move == "up" else "▼"}</span>'
    else:
        mv = '<span class="rm">–</span>'
    pt = f'<div class="rp">{pts}<small>{esc(pts_label)}</small></div>' if pts != "" else ""
    return (f'<div class="r{" t3" if isinstance(n, int) and n <= 3 else ""}">{f'<span class="rn">{n}</span>' if n != "" else ""}{avatar_html}'
            f'<div class="rw">{name_html}<small>{sub_html}</small></div>{pt}{mv}</div>')


TROPHY = '<svg viewBox="0 0 24 24"><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z"/><path d="M17 5h3v2a3 3 0 0 1-3 3M7 5H4v2a3 3 0 0 0 3 3"/></svg>'


def defending(name_html, status="", up=True, label="Defending champion"):
    st = f'<span class="st {"up" if up else "dn"}">{esc(status)}</span>' if status else ""
    return f'<div class="ui-dc"><span class="ic">{TROPHY}</span><div><small>{esc(label)}</small><b>{name_html}</b></div>{st}</div>'


def scoreboard(players, sets, tb=None, points=None, live=False, note="", attrs=""):
    """Placar: uma linha por jogador (foto, nome, país/ranking, bolinha de serviço) e os sets em fichas; no direto o set em curso
    fica destacado e, se houver, os pontos do jogo. players = [{"name": html, "sub": html, "av": html, "won": bool, "serve": bool}]"""
    n = max(len(sets[0]), len(sets[1])) if sets else 0
    hd = "".join(f"<i>S{k + 1}</i>" for k in range(n)) + ("<i>Pts</i>" if points else "")
    rows = ""
    for i, p in enumerate(players):
        mine, oth = sets[i], sets[1 - i]
        cells = ""
        for k in range(n):
            x = mine[k] if k < len(mine) else ""
            y = oth[k] if k < len(oth) else ""
            last = k == n - 1
            cls = "cur" if live and last else ("on" if isinstance(x, int) and isinstance(y, int) and x > y else "")
            t = (tb[i][k] if tb and k < len(tb[i]) else None)
            sup = f"<sup>{int(t)}</sup>" if t is not None and x == 6 and y == 7 else ""
            cells += f'<span class="{cls}">{x}{sup}</span>'
        if points:
            cells += f'<span class="gp">{esc(str(points[i]))}</span>'
        st = ("w" if p.get("won") else "l") if any(q.get("won") for q in players) else ""
        rows += (f'<div class="r {st}{" sv" if p.get("serve") else ""}"><div class="who">{p.get("av", "")}<div><b>{p["name"]}</b>'
                 f'<small>{p.get("sub", "")}</small></div><span class="srv" title="Serving"></span></div><div class="cols">{cells}</div></div>')
    return (f'<div class="ui-sb{" live" if live else ""}" {attrs}><div class="hd"><div class="cols">{hd}</div></div>{rows}'
            + (f'<p class="nt">{note}</p>' if note else "") + "</div>")


def compare(names, rows):
    """Estatísticas lado a lado com barra. rows = [(label, a, b, a_txt, b_txt, key)]; a/b numéricos (barra) ou None (só texto)."""
    out = f'<div class="ui-cmp"><div class="hh"><b>{names[0]}</b><b>{names[1]}</b></div>'
    for label, a, b, at, bt, key in rows:
        bar = ""
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            pa = round(100 * a / (a + b)) if a + b > 0 else 50
            bar = (f'<div class="bar"><i class="{"hi" if a > b or (a == b and a) else ""}" style="width:{pa}%"></i>'
                   f'<i class="{"hi" if b > a or (a == b and a) else ""}" style="width:{100 - pa}%"></i></div>')
        out += f'<div class="c{"" if bar else " tx"}" data-k="{esc(key)}"><b>{at}</b><span>{esc(label)}</span><b>{bt}</b>{bar}</div>'
    return out + "</div>"


# Horas na hora de quem visita (5/11/2026): o HTML traz a hora em UTC (ou local do torneio) dentro de <time class="lt" datetime="ISO">;
# no browser passa para a hora do visitante. data-fmt="dm" mostra também o dia. Um <small>UTC</small> logo a seguir passa a "your time".
# 9/11/2026: vídeo apagado no YouTube -> a miniatura vem cinzenta (120x90) ou dá erro; o cartão desaparece em vez de ficar "..."
DEAD_YT_JS = r"""<script>(function(){var R=/i\.ytimg\.com\/vi\//;function hide(i){var a=i.closest('a')||i;a.style.display='none'}
function chk(i){if(i.tagName==='IMG'&&R.test(i.src)&&i.complete&&i.naturalWidth>0&&i.naturalWidth<=120)hide(i)}
document.addEventListener('load',function(e){chk(e.target)},true);
document.addEventListener('error',function(e){var i=e.target;if(i.tagName==='IMG'&&R.test(i.src))hide(i)},true);
[].forEach.call(document.querySelectorAll('img'),chk)})()</script>"""
LOCALTIME_JS = ("<script>(function(){function f(){document.querySelectorAll('time.lt[datetime]').forEach(function(e){if(e.dataset.lt)return;"
                "var d=new Date(e.getAttribute('datetime'));if(isNaN(d))return;var hm=d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',hour12:false});"
                "e.textContent=(e.dataset.fmt==='dm'?d.toLocaleDateString([],{day:'2-digit',month:'2-digit'})+' · ':'')+hm+(e.dataset.sfx||'');"
                "e.title='Your local time';e.dataset.lt=1;var n=e.nextElementSibling;if(n&&n.tagName==='SMALL'&&n.textContent.trim()==='UTC')n.textContent='your time'})}"
                "f();document.addEventListener('DOMContentLoaded',f);setTimeout(f,1500)})()</script>")


def ltime(iso, text, fmt="", sfx=""):
    """<time> que o browser converte para a hora do visitante; 'text' é o que aparece sem JavaScript."""
    import html as _h
    return (f'<time class="lt" datetime="{_h.escape(iso or "")}"{f" data-fmt={chr(34)}{fmt}{chr(34)}" if fmt else ""}'
            f'{f" data-sfx={chr(34)}{_h.escape(sfx)}{chr(34)}" if sfx else ""}>{_h.escape(text)}</time>')
