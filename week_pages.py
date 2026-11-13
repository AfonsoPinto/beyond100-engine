"""Páginas semanais "The week beyond the top 100" (13/11/2026, SEO: conteúdo novo todas as semanas, aberto ao Google).

Cada semana tem a sua página permanente (/week/2026-w46.html) e há um arquivo (/week/). Os dados da semana são os da
newsletter (newsletter.week_data: campeões, surpresas, subidas no ranking oficial, qualifiers, próximos torneios) e ficam
guardados em weeks/<ano>-W<nn>.json (repositório de dados), para as semanas passadas não mudarem.
Texto factual escrito pelo código (sem IA), com ligações para as páginas dos jogadores, dos jogos e dos torneios.
"""
import datetime as dt
import glob
import html
import json
import os

esc = html.escape
WEEKS_DIR = "weeks"

CSS = """
.wk-hero{margin:8px 0 18px}.wk-hero h1{margin:0 0 8px}.wk-hero p{color:var(--s);max-width:70ch;line-height:1.6}
.wk-nums{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:10px 0 26px}
.wk-nums div{background:var(--deep);border:1px solid var(--e);border-radius:18px;padding:14px 16px}
.wk-nums b{display:block;font:900 1.9rem system-ui;color:var(--v);font-variant-numeric:tabular-nums}.wk-nums span{color:var(--s);font-size:.82rem}
.wk-list{display:flex;flex-direction:column;gap:8px;margin:10px 0 24px}
.wk-row{display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center;background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:12px 14px;text-decoration:none;color:var(--c)}
.wk-row:hover{border-color:var(--v)}.wk-row .tg{font:800 .72rem system-ui;letter-spacing:.06em;color:#0e3a2d;background:var(--v);border-radius:999px;padding:3px 9px;white-space:nowrap}
.wk-row .tg.up{background:#ff8a78;color:#3a0d06}.wk-row b{display:block}.wk-row small{color:var(--s)}.wk-row .sc{font:800 .95rem system-ui;color:var(--v);white-space:nowrap}
.wk-arch{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.wk-arch a{display:block;background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:14px;text-decoration:none;color:var(--c)}
.wk-arch a b{display:block;font-size:1.05rem}.wk-arch a small{color:var(--s)}
@media (max-width:600px){.wk-nums{grid-template-columns:1fr 1fr}}
"""


def _key(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _range(key):
    y, w = key.split("-W")
    mon = dt.date.fromisocalendar(int(y), int(w), 1)
    sun = mon + dt.timedelta(days=6)
    return mon, sun


def save_current():
    """Guarda os dados da semana em curso (a newsletter atualiza-os a cada atualização completa)."""
    import newsletter
    today = dt.date.today()
    d = newsletter.week_data(today, today - dt.timedelta(days=today.weekday()))
    key = _key(today)
    os.makedirs(WEEKS_DIR, exist_ok=True)
    keep = {k: d.get(k) for k in ("week", "date", "champs", "beyond", "upsets", "climb", "quals", "next_t", "n_results")}
    with open(os.path.join(WEEKS_DIR, f"{key}.json"), "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, separators=(",", ":"))
    return key


def _plink(name):
    import extras
    return extras.plink(name)


def _intro(d, mon, sun):
    ch, bey, ups = d.get("champs") or [], d.get("beyond") or [], d.get("upsets") or []
    last = min(sun, dt.date.today())
    bits = [f"From {mon.strftime('%-d')} to {last.strftime('%-d %B %Y')}, we followed {d.get('n_results') or 0} matches on the Challenger, ITF and WTA tours."]
    if ch:
        bits.append((f"{len(ch)} players won a title" if len(ch) > 1 else "One player won a title")
                    + ((f", {len(bey)} of them from outside the top 100." if len(bey) > 1 else ", from outside the top 100." if len(ch) == 1 else ", one of them from outside the top 100.") if bey else "."))
    if bey:
        b = bey[0]
        bits.append(f"The lowest-ranked champion was {b['name']}, No. {b['rank']}, who won {b.get('t') or 'a title'} ({b.get('score') or ''}).")
    if ups:
        u = ups[0]
        bits.append(f"The biggest upset: {u['w']} (No. {u['wr']}) beat {u['l']} (No. {u['lr']}) in {u.get('t') or ''}.")
    return " ".join(bits)


def page(key, d):
    mon, sun = _range(key)
    ch, ups, quals = d.get("champs") or [], d.get("upsets") or [], d.get("quals") or []
    climb = d.get("climb") or {}
    nums = (f'<div class="wk-nums"><div><b>{d.get("n_results") or 0}</b><span>matches tracked</span></div><div><b>{len(ch)}</b><span>champions</span></div>'
            f'<div><b>{len(d.get("beyond") or [])}</b><span>champions outside the top 100</span></div><div><b>{len(ups)}</b><span>upsets (150+ places)</span></div></div>')
    body = (f'<section class="wk-hero"><p class="mut2">Week {int(key[-2:])} · {mon.strftime("%-d %b")} – {sun.strftime("%-d %b %Y")}</p>'
            f'<h1>The week beyond the top 100</h1><p>{esc(_intro(d, mon, sun))}</p></section>' + nums)
    if ch:
        rows = "".join(f'<div class="wk-row"><span class="tg">TITLE</span><span><b>{_plink(c["name"])}</b><small>{esc(c.get("t") or "")}'
                       + (f' · No. {c["rank"]}' if c.get("rank") else "") + f' · beat {esc(c.get("loser") or "")}</small></span>'
                       f'<a class="sc" href="/m/{c["id"]}.html">{esc(c.get("score") or "")} ›</a></div>' for c in sorted(ch, key=lambda c: -(c.get("rank") or 0)))
        body += f'<h2 class="dh">Champions</h2><div class="wk-list">{rows}</div>'
    if ups:
        rows = "".join(f'<div class="wk-row"><span class="tg up">+{u["wr"] - u["lr"]}</span><span><b>{_plink(u["w"])} <small>No. {u["wr"]}</small></b>'
                       f'<small>beat {esc(u["l"])} (No. {u["lr"]}) · {esc(u.get("t") or "")}</small></span><a class="sc" href="/m/{u["id"]}.html">{esc(u.get("score") or "")} ›</a></div>'
                       for u in ups)
        body += f'<h2 class="dh">Upsets of the week</h2><div class="wk-list">{rows}</div>'
    cl = [(lg, x) for lg in ("atp", "wta") for x in climb.get(lg) or []]
    if cl:
        rows = "".join(f'<div class="wk-row"><span class="tg">▲{x["prev"] - x["r"]}</span><span><b>{_plink(x["n"])}</b>'
                       f'<small>{lg.upper()} · No. {x["prev"]} → No. {x["r"]}</small></span><span></span></div>' for lg, x in cl)
        body += f'<h2 class="dh">Climbers · official rankings</h2><div class="wk-list">{rows}</div>'
    if quals:
        rows = "".join(f'<div class="wk-row"><span class="tg">Q</span><span><b>{_plink(q["name"])}</b><small>{esc(q.get("tournament") or "")} · '
                       f'{q.get("wins")} main-draw win{"s" if q.get("wins", 0) > 1 else ""}{"" if q.get("alive") else " · out"}</small></span><span></span></div>' for q in quals)
        body += f'<h2 class="dh">Through qualifying</h2><div class="wk-list">{rows}</div>'
    body += ('<p class="mut2">Every Sunday this page becomes the week\'s newsletter. <a href="/week/">All weeks ›</a> · '
             '<a href="/results.html">All results ›</a> · <a href="/rankings.html">Rankings ›</a></p>')
    title = f"Tennis beyond the top 100: week {int(key[-2:])}, {mon.strftime('%-d')}–{sun.strftime('%-d %b %Y')} · Beyond100"
    desc = _intro(d, mon, sun)[:300]
    return f"<style>{CSS}</style>" + body, title, desc


def make(out_dir, shell, tx, crumbs):
    """Escreve /week/<ano>-w<nn>.html para todas as semanas guardadas e o arquivo /week/index.html. Devolve [(caminho, lastmod)]."""
    try:
        save_current()
    except Exception as e:
        print("Semana: dados da semana falharam", type(e).__name__, e)
    files = sorted(glob.glob(os.path.join(WEEKS_DIR, "*.json")), reverse=True)
    os.makedirs(os.path.join(out_dir, "week"), exist_ok=True)
    out, arch = [], ""
    for fp in files:
        key = os.path.basename(fp)[:-5]
        try:
            d = json.load(open(fp, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        body, title, desc = page(key, d)
        rel = f"week/{key.lower()}.html"
        mon, sun = _range(key)
        thin = (d.get("n_results") or 0) < 30 or not (d.get("champs") or d.get("upsets"))   # início da semana: ainda fora do Google
        with open(os.path.join(out_dir, rel), "w", encoding="utf-8") as f:
            f.write(shell(title, body, tx, root="../", path=rel, desc=desc, noindex=thin,
                          ld=[crumbs([("All weeks", "week/index.html"), (f"Week {int(key[-2:])}", rel)])]))
        if not thin:
            out.append((os.path.join(out_dir, rel), str(min(sun, dt.date.today()))))
        arch += (f'<a href="/{rel}"><b>Week {int(key[-2:])}, {mon.year}</b><small>{mon.strftime("%-d %b")} – {sun.strftime("%-d %b")} · '
                 f'{len(d.get("champs") or [])} champions · {len(d.get("upsets") or [])} upsets</small></a>')
    if arch:
        body = (f"<style>{CSS}</style><section class=\"wk-hero\"><h1>The week beyond the top 100</h1><p>Every week of tennis beyond the top 100 "
                "in one page: champions, upsets, the biggest climbers in the official rankings and the qualifiers who made it through.</p></section>"
                f'<div class="wk-arch">{arch}</div>')
        with open(os.path.join(out_dir, "week", "index.html"), "w", encoding="utf-8") as f:
            f.write(shell("The week beyond the top 100: every week of Challenger, ITF and WTA tennis · Beyond100", body, tx, root="../",
                          path="week/index.html", desc="Weekly recaps of tennis beyond the top 100: champions, upsets, ranking climbers and qualifiers."))
        out.append((os.path.join(out_dir, "week", "index.html"), str(dt.date.today())))
    return out
