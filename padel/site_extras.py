"""Beyond Padel, extras do site: imagens de partilha (OG), créditos das fotos, próxima semana, estatísticas e recordes,
e a entrada dos jogadores/torneios de padel na pesquisa global (search.json, partilhada com o ténis)."""
import datetime as dt
import json
import os
import time

from PIL import Image, ImageDraw, ImageOps

from padel import cards
from padel.site import (CAT, LEVEL, LEVEL_SHORT, LEVEL_ORDER, esc, flag, country_name, plink, ppath, tpath, pair_path,
                        team_players, tour_meta, date_range, match_html, sets_of, rank_str, winners_html, shell, avatar, disp)

HERE = os.path.dirname(os.path.abspath(__file__))
OW, OH = 1200, 630
BLUE, DEEP, CREAM, VOLT, SOFT, EDGE = cards.BLUE, cards.DEEP, cards.CREAM, cards.VOLT, cards.SOFT, cards.EDGE
font, fit = cards.font, cards.fit


# ------------------------------------------------------------------ OG (1200x630)
def _og_base(photo=None):
    img = Image.new("RGB", (OW, OH), BLUE)
    if photo:
        ph = ImageOps.fit(Image.open(photo).convert("RGB"), (480, OH), centering=(0.5, 0.25))
        img.paste(ph, (OW - 480, 0))
        ov = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        for x in range(OW - 480, OW - 300):
            od.line([(x, 0), (x, OH)], fill=(12, 46, 74, int(255 * (1 - (x - (OW - 480)) / 180))))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    else:
        em = Image.open(os.path.join(HERE, "emblem.jpg")).convert("RGB").resize((400, 400), Image.LANCZOS)
        img.paste(em, (OW - 460, (OH - 400) // 2))
    d = ImageDraw.Draw(img)
    d.text((60, 70), "BEYOND PADEL", font=font(cards.SERIF_B, 30), fill=VOLT, anchor="ls")
    d.text((60, OH - 50), "beyond100tennis.com/padel", font=font(cards.SANS_B, 24), fill=SOFT, anchor="ls")
    return img, d


def _lines(d, x, y, text, fnt, size, maxw, minsize, color, maxlines=2, gap=1.12):
    words, lines, cur = (text or "").split(), [], ""
    f = font(fnt, size)
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    if len(lines) > maxlines:
        return _lines(d, x, y, text, fnt, size - 6, maxw, minsize, color, maxlines, gap) if size - 6 >= minsize else _draw(d, x, y, lines[:maxlines], f, color, size, gap)
    return _draw(d, x, y, lines, f, color, size, gap)


def _draw(d, x, y, lines, f, color, size, gap):
    for ln in lines:
        d.text((x, y), ln, font=f, fill=color, anchor="ls")
        y += int(size * gap)
    return y


def _tag(d, x, y, label, fill=VOLT, fg=BLUE):
    f = font(cards.SANS_B, 22)
    tw = d.textlength(label, font=f) + 28
    d.rounded_rectangle([x, y, x + tw, y + 38], radius=19, fill=fill)
    d.text((x + tw / 2, y + 19), label, font=f, fill=fg, anchor="mm")
    return x + tw + 10


def og_generic(fp):
    img, d = _og_base()
    y = _lines(d, 60, 230, "Every player.", cards.SERIF_B, 76, 640, 40, CREAM, 1)
    _lines(d, 60, y + 4, "Every draw.", cards.SERIF_I, 76, 640, 40, VOLT, 1)
    _lines(d, 60, 450, "Results, draws, order of play and rankings from Premier Padel and the CUPRA FIP Tour.",
           cards.SANS_B, 26, 620, 18, SOFT, 3, 1.35)
    img.save(fp, quality=80, optimize=True)


def _winners(t):
    out = []
    for cat, v in (t.get("winners") or {}).items():
        ps = v if isinstance(v, list) else []
        nm = " / ".join((p.get("short_name") or p.get("name") or "") for p in ps if isinstance(p, dict))
        if nm:
            out.append((CAT.get(cat, cat), nm, ps))
    return out


def og_tournament(t, fp):
    win = _winners(t)
    photo = None
    for _, _, ps in win:
        for p in ps:
            path, _, off = cards.photo_of(p.get("id"))
            if path and not off:
                photo = path
                break
        if photo:
            break
    img, d = _og_base(photo)
    maxw = 640 if photo else 640
    _tag(d, 60, 110, LEVEL_SHORT.get(t.get("level"), "PADEL"))
    y = _lines(d, 60, 230, t.get("name") or "", cards.SERIF_B, 64, maxw, 34, CREAM, 2)
    _lines(d, 60, y + 6, f"{t.get('location') or ''} · {date_range(t)}".strip(" ·").upper(), cards.SANS_B, 24, maxw, 16, VOLT, 1)
    y += 70
    if win:
        for cat, nm, _ in win[:2]:
            d.text((60, y), f"CHAMPIONS · {cat.upper()}", font=font(cards.SANS_B, 22), fill=SOFT, anchor="ls")
            _lines(d, 60, y + 40, nm, cards.SERIF_B, 36, maxw, 22, CREAM, 1)
            y += 90
    else:
        st = {"live": "Live this week: results, draw and order of play", "pending": "Draw, order of play and results"}.get(t.get("status"), "Results and draw")
        _lines(d, 60, y + 10, st, cards.SERIF_I, 34, maxw, 22, CREAM, 2)
    img.save(fp, quality=80, optimize=True)


def og_player(p, r, path_photo, fp):
    img, d = _og_base(path_photo)
    _tag(d, 60, 110, f"{CAT.get(p.get('category'), 'PADEL').upper()}")
    y = _lines(d, 60, 250, p.get("name") or "", cards.SERIF_B, 70, 640, 36, CREAM, 2)
    rk = (r or {}).get("ranking")
    sub = " · ".join(x for x in [country_name(p.get("nationality")), f"World No. {rk}" if rk else "", f"{(r or {}).get('points')} pts" if (r or {}).get("points") else ""] if x)
    _lines(d, 60, y + 10, sub.upper(), cards.SANS_B, 26, 640, 16, VOLT, 1)
    _lines(d, 60, y + 80, "Ranking, partners and every result", cards.SERIF_I, 34, 640, 22, CREAM, 1)
    img.save(fp, quality=80, optimize=True)


OG_CACHE = os.path.join(HERE, "data", "og")
OG_VER = "3"


def _cached(key_obj, fn, render, od):
    """Só desenha de novo quando os dados da imagem mudam (cache em padel/data/og, guardada entre execuções)."""
    import hashlib
    import shutil
    key = hashlib.sha1((OG_VER + json.dumps(key_obj, sort_keys=True, ensure_ascii=False, default=str)).encode()).hexdigest()[:16]
    cp = os.path.join(OG_CACHE, fn)
    if _KEYS.get(fn) != key or not os.path.exists(cp):
        render(cp)
        _KEYS[fn] = key
    shutil.copy(cp, os.path.join(od, fn))


_KEYS = {}


def build_og(db, out):
    """Gera as imagens e devolve {path_da_página: url_da_imagem}. Jogadores: só os que têm foto livre ou estão no top 100."""
    od = os.path.join(out, "padel", "og")
    os.makedirs(od, exist_ok=True)
    os.makedirs(OG_CACHE, exist_ok=True)
    kf = os.path.join(OG_CACHE, "keys.json")
    try:
        _KEYS.update(json.load(open(kf, encoding="utf-8")))
    except (OSError, ValueError):
        pass
    og_generic(os.path.join(out, "padel", "og.png"))
    m, used = {}, set()
    for t in db.tours.values():
        fn = f"t-{t.get('id')}.jpg"
        try:
            ph = [cards.photo_of(p.get("id"))[0] for _, _, ps in _winners(t) for p in ps]
            _cached([t.get(k) for k in ("name", "level", "location", "start_date", "end_date", "status", "winners")] + ph, fn,
                    lambda cp, t=t: og_tournament(t, cp), od)
            m[tpath(t)] = f"/padel/og/{fn}"
            used.add(fn)
        except Exception as e:
            print("OG torneio", t.get("id"), type(e).__name__, e)
    for pid, p in db.pinfo.items():
        r = db.rank_of.get(pid) or {}
        path, _, _ = cards.photo_of(pid)
        if not p.get("name") or not db.by_p.get(pid) or not (path or (r.get("ranking") or 999) <= 100):
            continue
        fn = f"p-{pid}.jpg"
        try:
            _cached([p.get("name"), p.get("category"), p.get("nationality"), r.get("ranking"), r.get("points"), path], fn,
                    lambda cp, p=p, r=r, path=path: og_player(p, r, path, cp), od)
            m[ppath(p)] = f"/padel/og/{fn}"
            used.add(fn)
        except Exception as e:
            print("OG jogador", pid, type(e).__name__, e)
    for fn in list(_KEYS):                                         # limpa imagens que já não são usadas
        if fn not in used:
            _KEYS.pop(fn, None)
            try:
                os.remove(os.path.join(OG_CACHE, fn))
            except OSError:
                pass
    with open(kf, "w", encoding="utf-8") as f:
        json.dump(_KEYS, f, sort_keys=True)
    return m


# ------------------------------------------------------------------ créditos
def page_credits(db):
    try:
        cr = json.load(open(os.path.join(HERE, "photos", "credits.json"), encoding="utf-8"))
    except (OSError, ValueError):
        cr = {}
    rows = ""
    for pid, c in sorted(cr.items(), key=lambda kv: (db.pinfo.get(kv[0]) or {}).get("name") or ""):
        p = db.pinfo.get(pid) or {"id": pid, "name": f"Player {pid}"}
        src = f'<a href="{esc(c.get("page"))}" rel="nofollow noopener" target="_blank">source</a>' if c.get("page") else ""
        crd = (c.get("credit") or "").replace("Photo: ", "")
        rows += f'<tr><td class="pn">{plink(p)}</td><td>{esc(crd)}</td><td>{src}</td></tr>'
    body = ('<section class="page-h"><h1>Photo credits</h1><p>The player photos on our cards and pages are freely licensed '
            '(public domain, CC0, CC BY or CC BY-SA), mostly from Wikimedia Commons. Thank you to every photographer. '
            'If you are the author of a photo and want it credited differently or removed, write to us on '
            '<a href="https://www.instagram.com/beyond100.padel/">Instagram</a>.</p></section>'
            f'<table class="pt"><thead><tr><th>Player</th><th>Photographer · licence</th><th></th></tr></thead><tbody>{rows}</tbody></table>')
    return shell("Photo credits · Beyond Padel", body, "/padel/credits.html", tab="")


# ------------------------------------------------------------------ próxima semana
def page_next_week(db):
    today = dt.date.today()
    lim = (today + dt.timedelta(days=10)).isoformat()
    ts = [t for t in db.tours.values() if t.get("status") in ("pending", "live") and today.isoformat() < (t.get("start_date") or "") <= lim]
    ts.sort(key=lambda t: (t.get("start_date") or "", LEVEL_ORDER.get(t.get("level"), 9)))
    body = ('<section class="page-h"><h1>Next week</h1><p>Tournaments starting in the next days, with last year\'s champions '
            'and the first matches as soon as the draw is out.</p></section>')
    if not ts:
        body += '<p class="empty">No tournaments in the next days in our calendar.</p>'
    for t in ts:
        body += f'<div class="pd-card"><h3><a href="{tpath(t)}">{esc(t.get("name"))}</a></h3>{tour_meta(t)}'
        eds = sorted([e for e in (db.editions.get(str(t["id"])) or []) if str(e.get("id")) != str(t["id"]) and e.get("winners")],
                     key=lambda e: e.get("start_date") or "", reverse=True)
        if eds:
            body += f'<p class="pd-note" style="margin:8px 0 2px">Last edition ({esc((eds[0].get("start_date") or "")[:4])}):</p>' + winners_html(eds[0], db)
        ms = [m for m in db.by_t.get(str(t["id"]), []) if (m.get("draw") or "main") == "main"]
        if ms:
            first = max(m.get("round") or 0 for m in ms)
            fm = sorted([m for m in ms if m.get("round") == first], key=lambda m: (m.get("category") or "", m.get("index") or 0))
            body += f'<p class="pd-note" style="margin:10px 0 0">Draw is out · {len(fm)} first-round matches</p>' + "".join(match_html(m, db) for m in fm[:8])
        body += "</div>"
    return shell("Padel next week: upcoming tournaments · Beyond Padel", body, "/padel/next-week.html", tab="next-week")


# ------------------------------------------------------------------ estatísticas e recordes
def compute_stats(db):
    pl, pairs, countries, upsets = {}, {}, {}, []
    done = sorted([m for m in db.matches if m.get("winner") in ("team_1", "team_2") and (m.get("draw") or "main") == "main"],
                  key=lambda m: (m.get("played_at") or "", -(m.get("round") or 99)))
    for m in done:
        w = m["winner"]
        lo = "team_2" if w == "team_1" else "team_1"
        for tm in ("team_1", "team_2"):
            won = tm == w
            for p in team_players(m, tm):
                e = pl.setdefault(str(p.get("id")), {"p": p, "w": 0, "l": 0, "t": 0, "streak": 0, "best": 0, "cat": m.get("category")})
                e["w" if won else "l"] += 1
                e["streak"] = e["streak"] + 1 if won else 0
                e["best"] = max(e["best"], e["streak"])
                if won and m.get("round") == 1:
                    e["t"] += 1
                    c = p.get("nationality") or "?"
                    countries[c] = countries.get(c, 0) + 1
        W, L = team_players(m, w), team_players(m, lo)
        if len(W) == 2:
            k = "-".join(sorted(str(p.get("id")) for p in W))
            e = pairs.setdefault(k, {"team": W, "w": 0, "t": 0, "cat": m.get("category")})
            e["w"] += 1
            e["t"] += 1 if m.get("round") == 1 else 0
        rw = [(db.rank_of.get(str(p.get("id"))) or {}).get("ranking") for p in W]
        rl = [(db.rank_of.get(str(p.get("id"))) or {}).get("ranking") for p in L]
        if all(rw) and all(rl) and len(rw) == 2 and len(rl) == 2:
            gap = sum(rw) - sum(rl)
            if gap > 0:
                upsets.append((gap, m))
    upsets.sort(key=lambda x: -x[0])
    return pl, pairs, countries, upsets


def _ptable(rows, cols):
    head = "".join(f"<th>{c}</th>" for c in cols)
    return f'<table class="pt"><thead><tr><th>#</th>{head}</tr></thead><tbody>' + "".join(
        f'<tr><td>{i}</td>' + "".join(f"<td{' class=pn' if j == 0 else ''}>{c}</td>" for j, c in enumerate(r)) + "</tr>" for i, r in enumerate(rows, 1)) + "</tbody></table>"


def _scard(title, rows, sub=""):
    """Cartão de recorde: o nº 1 em destaque (foto, nome, valor grande) e a lista 2-8 compacta. rows = [(players, value, note, link)]."""
    if not rows:
        return ""
    ps, val, note, link = rows[0]
    av = "".join(avatar(p, "st-av") for p in ps[:2])
    nm = " / ".join(esc(p.get("name") if len(ps) == 1 else disp(p)) for p in ps)
    fl = flag(ps[0].get("nationality"), 12) + (esc(country_name(ps[0].get("nationality"))) if len(ps) == 1 else "")
    h = (f'<div class="st-card"><h3>{esc(title)}{f"<small>{esc(sub)}</small>" if sub else ""}</h3>'
         f'<a class="st-lead" href="{link}"><span class="st-avs">{av}</span><span class="st-who"><b>{nm}</b><span>{fl}</span></span>'
         f'<span class="st-val"><em>{esc(str(val))}</em>{f"<small>{esc(note)}</small>" if note else ""}</span></a><ol class="st-rows">')
    for i, (ps, val, note, link) in enumerate(rows[1:8], 2):
        nm = " / ".join(esc(disp(p)) for p in ps)
        h += (f'<li><a href="{link}"><span class="n">{i}</span><span class="nm">{flag(ps[0].get("nationality"), 11)}{nm}</span>'
              f'<span class="v">{esc(str(val))}{f" <small>{esc(note)}</small>" if note else ""}</span></a></li>')
    return h + "</ol></div>"


STATS_JS = """<script>(function(){var s=document.getElementById('st-seg');if(!s)return;s.onclick=function(e){var b=e.target.closest('button');if(!b)return;
[].forEach.call(s.querySelectorAll('button'),function(x){x.className=x===b?'on':''});
[].forEach.call(document.querySelectorAll('.st-pane'),function(p){p.hidden=p.dataset.cat!==b.dataset.cat})}})();</script>"""


def page_stats(db):
    pl, pairs, countries, upsets = compute_stats(db)
    body = ('<section class="page-h"><h1>Stats &amp; records</h1><p>Every main-draw match in our database: Premier Padel and the '
            'FIP Tour (Platinum, Gold, Silver) of the last months.</p></section>'
            '<div class="pd-seg" id="st-seg"><button class="on" data-cat="men">Men</button><button data-cat="women">Women</button></div>')
    for cat in ("men", "women"):
        ps = [e for e in pl.values() if e["cat"] == cat]
        if not ps:
            continue
        one = lambda e, v, n="": ([e["p"]], v, n, ppath(e["p"]))
        cards = _scard("Most titles", [one(e, e["t"], f'{e["w"]}-{e["l"]}') for e in sorted([e for e in ps if e["t"]], key=lambda e: (-e["t"], -e["w"]))])
        cards += _scard("Most wins", [one(e, e["w"], f'{e["l"]} lost') for e in sorted(ps, key=lambda e: (-e["w"], e["l"]))])
        cards += _scard("Best win rate", [one(e, f'{round(100 * e["w"] / (e["w"] + e["l"]))}%', f'{e["w"]}-{e["l"]}')
                                          for e in sorted([e for e in ps if e["w"] + e["l"] >= 10], key=lambda e: (-e["w"] / (e["w"] + e["l"]), -e["w"]))], "10+ matches")
        cards += _scard("Longest winning streak", [one(e, e["best"], "ongoing" if e["streak"] == e["best"] else "")
                                                   for e in sorted([e for e in ps if e["best"] >= 3], key=lambda e: (-e["best"], -e["streak"]))], "wins in a row")
        cards += _scard("Best pairs", [(e["team"], e["t"], f'{e["w"]} wins', pair_path(e["team"]))
                                       for e in sorted([e for e in pairs.values() if e["cat"] == cat], key=lambda e: (-e["t"], -e["w"]))], "titles together")
        body += f'<div class="st-pane" data-cat="{cat}"{" hidden" if cat == "women" else ""}><div class="st-grid">{cards}</div></div>'
    if upsets:
        body += ('<h2 class="dh">Biggest upsets</h2><p class="pd-note">The winning pair\'s ranking compared with the pair they beat '
                 '(sum of both players\' current ranking).</p><div class="pd-card">')
        for gap, m in upsets[:8]:
            body += f'<p class="pd-note" style="margin:10px 0 0"><b style="color:var(--v)">+{gap} places</b></p>' + match_html(m, db, show_tour=True)
        body += "</div>"
    if countries:
        cs = sorted(countries.items(), key=lambda kv: -kv[1])[:10]
        mx = cs[0][1]
        body += ('<h2 class="dh">Titles by country</h2><div class="pd-card st-bars">' + "".join(
            f'<div><span class="nm">{flag(c, 12)}{esc(country_name(c))}</span><span class="bar"><i style="width:{max(4, round(100 * n / mx))}%"></i></span><b>{n}</b></div>'
            for c, n in cs) + '</div><p class="pd-note">Each player of a winning pair counts one title.</p>')
    body += STATS_JS
    return shell("Padel stats and records · Beyond Padel", body, "/padel/stats.html", tab="stats",
                 desc="Most titles, most wins, best win rate, winning streaks, best pairs and biggest upsets in Premier Padel and the FIP Tour.")


# ------------------------------------------------------------------ pesquisa global
def add_to_search(db, out):
    fp = os.path.join(out, "search.json")
    try:
        items = json.load(open(fp, encoding="utf-8"))
    except (OSError, ValueError):
        items = []
    items = [x for x in items if not str(x.get("u", "")).startswith("/padel/")]
    items += [{"n": p.get("name"), "u": ppath(p), "k": "Padel · " + country_name(p.get("nationality"))}
              for pid, p in db.pinfo.items() if p.get("name") and db.by_p.get(pid)]
    items += [{"n": t.get("name"), "u": tpath(t), "k": "Padel tournament"} for t in db.tours.values() if t.get("name")]
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, separators=(",", ":"))
    return len(items)
