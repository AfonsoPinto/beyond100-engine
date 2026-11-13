"""Rankings, versão 2 (13/11/2026): pódio dos 3 primeiros com foto grande e subidas da semana em cartões com foto.
Comum ao ténis e ao padel (cores das variáveis de cada site)."""
import html

esc = html.escape

CSS = """
.rk-pod{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:14px 0 6px;align-items:end}
.rk-pod>a,.rk-pod>div{position:relative;display:flex;align-items:flex-end;aspect-ratio:3/4;border-radius:20px;overflow:hidden;text-decoration:none;color:#fff;
background:radial-gradient(110% 90% at 80% 0,var(--e) 0,var(--deep) 65%);border:1px solid var(--e)}
.rk-pod>.n1{aspect-ratio:3/3.6;border-color:var(--v)}
@media(min-width:700px){.rk-pod{grid-template-columns:1fr 1.15fr 1fr}.rk-pod>.n1{order:2;aspect-ratio:3/4}.rk-pod>.n2{order:1;aspect-ratio:3/3.6}.rk-pod>.n3{order:3;aspect-ratio:3/3.4}}
.rk-pod .ph{position:absolute;inset:0;display:flex}.rk-pod .ph img{flex:1;min-width:0;height:100%;object-fit:cover;object-position:50% 18%}
.rk-pod .ini{position:absolute;right:-6px;top:-14px;font:900 5.5rem/1 system-ui;color:var(--v);opacity:.12}
.rk-pod>*::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,transparent 40%,rgba(0,0,0,.85))}
.rk-pod .no{position:absolute;z-index:1;left:10px;top:10px;min-width:34px;height:34px;border-radius:12px;display:grid;place-items:center;background:var(--v);color:var(--g);
font:900 1.05rem system-ui;padding:0 8px}
.rk-pod .tx{position:relative;z-index:1;padding:10px 12px;display:flex;flex-direction:column;gap:2px;min-width:0}
.rk-pod b{font:900 1rem/1.05 system-ui;overflow-wrap:anywhere}.rk-pod small{font:600 .74rem system-ui;color:rgba(255,255,255,.82)}
@media(min-width:700px){.rk-pod b{font-size:1.2rem}}
.rk-cl{display:flex;gap:10px;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;margin:0 -16px;padding:0 16px 6px}.rk-cl::-webkit-scrollbar{display:none}
.rk-cl a{position:relative;flex:0 0 42%;scroll-snap-align:start;aspect-ratio:4/5;border-radius:18px;overflow:hidden;display:flex;align-items:flex-end;text-decoration:none;color:#fff;
background:radial-gradient(110% 90% at 80% 0,var(--e) 0,var(--deep) 65%);border:1px solid var(--e)}
@media(min-width:700px){.rk-cl{margin:0;padding:0 0 6px}.rk-cl a{flex-basis:23%}}
.rk-cl img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:50% 18%}.rk-cl .ini{position:absolute;right:-6px;top:-12px;font:900 4.5rem/1 system-ui;color:var(--v);opacity:.12}
.rk-cl a::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,transparent 35%,rgba(0,0,0,.85))}
.rk-cl .up{position:absolute;z-index:1;left:8px;top:8px;background:var(--v);color:var(--g);font:900 .78rem system-ui;border-radius:999px;padding:4px 9px}
.rk-cl .tx{position:relative;z-index:1;padding:10px;display:flex;flex-direction:column;gap:1px;min-width:0}
.rk-cl b{font:850 .95rem/1.1 system-ui}.rk-cl small{font:600 .74rem system-ui;color:rgba(255,255,255,.82)}
.tv-ch{display:grid;gap:12px;grid-template-columns:minmax(0,1fr);margin:6px 0 10px}@media(min-width:700px){.tv-ch.two{grid-template-columns:1fr 1fr}}
.tv-ch .hm-lead{min-height:360px}.tv-ch.two .hm-lead h2{font-size:1.9rem}
.rk-f{display:flex;gap:8px;margin:10px 0 4px}.rk-f input{flex:1;min-width:0;margin:0}.rk-f select{background:var(--deep);border:1px solid var(--e);color:var(--c);
border-radius:14px;padding:0 12px;font:600 .9rem system-ui;max-width:42%}
"""


def podium(items):
    """[(posição, [fotos], iniciais, nome, sub, href)] — os 3 primeiros."""
    h = ""
    for k, (n, photos, ini, name, sub, href) in enumerate(items[:3]):
        ph = "".join(f'<img src="{esc(x)}" alt="" loading="lazy" width="600" height="750">' for x in photos)
        ph = f'<span class="ph">{ph}</span>' if ph else f'<span class="ini" aria-hidden="true">{esc(ini)}</span>'
        tag = "a" if href else "div"
        h += (f'<{tag} class="n{k + 1}"{f" href={esc(href)!r}" if href else ""}>{ph}<span class="no">{n}</span>'
              f'<span class="tx"><b>{esc(name)}</b><small>{sub}</small></span></{tag}>')
    return f'<div class="rk-pod">{h}</div>' if h else ""


def climbers(items):
    """[(subida, [fotos], iniciais, nome, sub, href)]"""
    h = ""
    for up, photos, ini, name, sub, href in items:
        ph = f'<img src="{esc(photos[0])}" alt="" loading="lazy" width="600" height="750">' if photos else f'<span class="ini" aria-hidden="true">{esc(ini)}</span>'
        lab = f"▲ {up}" if isinstance(up, int) else esc(str(up))
        h += (f'<a href="{esc(href or "#")}">{ph}<span class="up">{lab}</span><span class="tx"><b>{esc(name)}</b><small>{sub}</small></span></a>')
    return f'<div class="rk-cl">{h}</div>' if h else ""


def country_filter(countries, sid="rkc"):
    """<select> com os países (nome visível), para filtrar as linhas pelo texto."""
    return (f'<select id="{sid}" aria-label="Country"><option value="">All countries</option>'
            + "".join(f'<option value="{esc(c)}">{esc(c)}</option>' for c in countries) + "</select>")


def champions(cards):
    """Cartões grandes dos campeões de um torneio (1 ou 2: homens e mulheres). cards = HTML de home_ui.lead."""
    cards = [c for c in cards if c]
    if not cards:
        return ""
    import home_ui
    return f'<style>{home_ui.CSS}{CSS}</style><div class="tv-ch{" two" if len(cards) > 1 else ""}">{"".join(cards)}</div>'
