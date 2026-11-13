"""Páginas do site Beyond100: classificação dos jogos + página de resultados com filtros (JS no browser)."""
import html
import json
import re

LEVEL_ORDER = {"tour": 0, "challenger": 1, "itf": 2, "other": 3}
LEVEL_LABEL = {"tour": "Tour", "challenger": "Challenger", "itf": "ITF", "other": "Other"}


def base_tournament(t):
    """Tira o tipo de prova do fim do nome ('... MEN DOUBLES' -> '...') para agrupar singulares e pares."""
    t = re.sub(r"\s+(WOMEN|MEN|MIXED|BOYS|GIRLS)?\s*(SINGLES|DOUBLES)\s*$", "", t.strip(), flags=re.I)
    return re.sub(r"\s+", " ", t).strip()


AVATARS = set()          # slugs de jogadores com foto no site (preenchido por result_card.build_site)


def avatar(name, cls="av"):
    sl = slugify(name or "")
    if sl in AVATARS:
        return f'<img class="{cls}" src="/img/{sl}.jpg" alt="{html.escape(name)}" loading="lazy" width="28" height="28">'
    return ""


def name_html(p, r, esc=html.escape):
    """Nome do jogador; em singulares liga à página do jogador (/p/nome.html)."""
    if classify(r)[1] == "singles" and p.get("name"):
        return f'{avatar(p["name"])}<a class="nm" href="/p/{slugify(p["name"])}.html">{esc(p["name"])}</a>'
    return f'<span class="nm">{esc(p["name"])}</span>'


def mh_html(r, meta, esc=html.escape):
    """Linha de cabeçalho do cartão; em singulares é uma ligação para a página do jogo (/m/id.html)."""
    if r.get("id") is not None and classify(r)[1] == "singles":
        try:
            import tennis_videos
            hl = tennis_videos.highlight_for(r) if r.get("winner") in (1, 2) else None
        except Exception:
            hl = None
        badge = ('<span style="background:#d9f23d;color:#0a221a;border-radius:999px;padding:1px 8px;font-weight:800;margin-right:6px;'
                 'white-space:nowrap">▶ Highlights</span>') if hl else ""
        return f'<a class="mh" href="/m/{r["id"]}.html">{badge}{esc(meta)} ›</a>'
    return f'<div class="mh">{esc(meta)}</div>'


CUR_RANKS = {}   # nome -> último ranking conhecido (preenchido no build)


def who_tag(p):
    """'GRE · #69': país e ranking (o ranking só aparece se a API o deu quando o jogo terminou)."""
    c = (p.get("country") or "").upper()
    rk = p.get("rank")
    if isinstance(rk, int) and rk > 0:
        rtxt = f"#{rk}"
    else:   # jogos antigos sem ranking: usa o último ranking conhecido, marcado com *
        cur = CUR_RANKS.get(p.get("name") or "")
        rtxt = f"#{cur}*" if isinstance(cur, int) and cur > 0 else ""
    return " · ".join(x for x in [c, rtxt] if x)


def slugify(t):
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-") or "torneio"


_CATS = None


def _cat_norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"\s+\d+\s*$", "", s.strip())
    return re.sub(r"[^a-z]+", " ", s).strip()


def _plus(iso, days):
    import datetime
    return (datetime.date.fromisoformat(iso) + datetime.timedelta(days=days)).isoformat()


_ALIAS = {"cherbourg": "cherbourg en cotentin", "genova": "genoa", "santa cruz": "santa cruz de la sierra", "st tropez": "saint tropez",
          "francavilla": "francavilla al mare", "morelos": "cuernavaca", "heilbronn": "bad rappenau", "alicante": "alicante", "tyler": "tyler"}


def category_label(r, gender, prefix=None):
    """Etiqueta da categoria (ex. 'Challenger 100', 'WTA 500', 'ATP 250') a partir de categorias_torneios.json (calendários oficiais)
    e categorias_manual.json (correções à mão, ganham); None se desconhecida. A cidade do torneio pode estar em qualquer parte da chave."""
    global _CATS
    if _CATS is None:
        _CATS = []
        try:
            import os
            base = os.path.dirname(os.path.abspath(__file__))
            for fn in ("categorias_torneios.json", "categorias_manual.json"):          # o manual vem por último e ganha
                try:
                    with open(os.path.join(base, fn), encoding="utf-8") as f:
                        for e in json.load(f):
                            _CATS.append((e.get("g", "m"), " " + _cat_norm(e["city"]) + " ", e["start"], e.get("days", 10), e["label"]))
                except (OSError, ValueError):
                    pass
        except Exception:
            pass
    name = r.get("tournament") or ""
    name = re.split(r"\s+(?:Chall|WTA|ATP)|\s+-\s+|,", name, maxsplit=1, flags=re.I)[0]
    city = _cat_norm(name)
    city = _ALIAS.get(city, city)
    if not city:
        return None
    needle = " " + city + " "
    g = "w" if gender == "women" else "m"
    d = (r.get("date") or "")[:10]
    best = None
    for eg, key, start, days, label in _CATS:
        if eg != g or (prefix and not label.startswith(prefix)):
            continue
        if needle in key and _plus(start, -3) <= d <= _plus(start, days + 3):
            best = label
    return best


def classify(r):
    """Deduz género, formato e nível a partir do nome do torneio e dos jogadores."""
    t = (r.get("tournament") or "").upper()
    names = (r["p1"]["name"], r["p2"]["name"])
    kind = "doubles" if ("DOUBLES" in t or any(" / " in n for n in names)) else "singles"
    gender = None
    if "MIXED" in t:
        gender = "mixed"
    elif "WOMEN" in t or "WTA" in t or "GIRLS" in t or re.search(r"\bW\d{2,3}\b", t):
        gender = "women"
    elif re.search(r"\bMEN\b", t) or "ATP" in t or "BOYS" in t or "CHALLENGER" in t or re.search(r"\bM\d{2,3}\b", t):
        gender = "men"
    m = re.search(r"\b([MW])\s?(\d{2,3})\b", t)
    if "CHALLENGER" in t or re.search(r"WTA\s*(125|100)", t):
        level, tag = "challenger", "Challenger" if "CHALLENGER" in t else "WTA 125"
    elif m or "ITF" in t:
        level, tag = "itf", ("ITF " + m.group(1) + m.group(2)) if m else "ITF"
    elif "ATP" in t or "WTA" in t or "GRAND SLAM" in t:
        level, tag = "tour", "ATP" if "ATP" in t else "WTA"
    else:
        level, tag = "other", ""
    # a API traz o circuito (tour) e o género: é mais fiável do que o nome do torneio
    if r.get("gender") in ("men", "women"):
        gender = r["gender"]
    tour = (r.get("tour") or "").lower()
    if tour:
        if "challenger" in tour or "125" in tour:
            level, tag = "challenger", ("WTA 125" if gender == "women" else "Challenger")
            if gender != "women":
                tag = category_label(r, gender, "Challenger") or tag
        elif tour in ("atp", "wta"):
            level, tag = "tour", tour.upper()
            if tour == "wta":
                tag = category_label(r, "women", "WTA") or tag
            elif gender != "women":
                tag = category_label(r, "men", "ATP") or tag
        elif "itf" in tour:
            level, tag = "itf", (("ITF " + m.group(1) + m.group(2)) if m else "ITF")
    return gender, kind, level, tag


def api_view(m):
    """Jogo cru da API -> dicionário que o classify() percebe (nome, circuito, género)."""
    pl = m.get("players") or {}
    import time
    return {"tournament": m.get("tournament", ""), "tour": m.get("tour"), "gender": m.get("gender"),
            "date": (m.get("updated_at") or "")[:10] or time.strftime("%Y-%m-%d", time.gmtime()),
            "p1": {"name": (pl.get("p1") or {}).get("name", "")}, "p2": {"name": (pl.get("p2") or {}).get("name", "")}}


def _round_rank(rd):
    s = (rd or "").lower()
    if "qualif" in s or re.match(r"q\d", s.strip()): return 9      # qualificação nunca é "final"
    if "semi" in s: return 1
    if "quarter" in s or "1/4" in s: return 2
    if "final" in s and "1/" not in s: return 0
    m = re.search(r"1/(\d+)", s)
    if m: return 2 + {"8": 1, "16": 2, "32": 3, "64": 4, "128": 5}.get(m.group(1), 6)
    return 9


def _set_done(a, b):
    hi, lo = max(a, b), min(a, b)
    return (hi >= 10 and hi - lo >= 2) or (hi >= 6 and hi - lo >= 2) or (hi == 7 and lo in (5, 6))


def match_stats(r):
    """Estatísticas derivadas do resultado (sem dados extra da API).
    Devolve (distintivos, % de jogos ganhos pelo vencedor, nº de tie-breaks, jogos totais, margem) ou None se o jogo não está completo."""
    w = r.get("winner")
    g = r.get("games") or [[], []]
    if w not in (1, 2) or not g[0] or len(g[0]) != len(g[1]):
        return None
    mine, other = (g[0], g[1]) if w == 1 else (g[1], g[0])
    if not all(_set_done(a, b) for a, b in zip(mine, other)):
        return None                      # desistência / resultado incompleto: não tiramos conclusões
    if sum(a > b for a, b in zip(mine, other)) <= sum(a < b for a, b in zip(mine, other)):
        return None                      # resultado incoerente com o vencedor
    badges = []
    if mine[0] < other[0]:
        badges.append("comeback")
    if any(b == 0 and a >= 6 for a, b in zip(mine, other)) or any(a == 0 and b >= 6 for a, b in zip(mine, other)):
        badges.append("bagel")
    elif any((a, b) in ((6, 1), (1, 6)) for a, b in zip(mine, other)):
        badges.append("breadstick")
    sets = list(zip(g[0], g[1]))
    super_tb = any(max(a, b) >= 10 for a, b in sets)
    tbs = sum(1 for a, b in sets if (a, b) in ((7, 6), (6, 7)))
    if super_tb:
        badges.append("super")
    if tbs:
        badges.append("tb")
    tot_w, tot_o = sum(mine), sum(other)
    return badges, round(100 * tot_w / (tot_w + tot_o)), tbs, tot_w + tot_o, tot_w - tot_o


def prepare(results, tr):
    """Lista compacta para o browser."""
    out = []
    for r in results:
        gender, kind, level, tag = classify(r)
        rd = (r.get("round") or "")
        out.append({
            "id": r.get("id"), "d": r.get("date", ""), "t": base_tournament(r.get("tournament", "")),
            "rd": tr["rounds"].get(rd.lower(), rd), "ro": _round_rank(rd),
            "sf": tr["surfaces"].get(r.get("surface"), ""),
            "a": r["p1"]["name"], "ac": who_tag(r["p1"]),
            "b": r["p2"]["name"], "bc": who_tag(r["p2"]),
            "as": slugify(r["p1"]["name"]), "bs": slugify(r["p2"]["name"]),
            "g": r["games"], "w": r.get("winner"), **({"tb": r["tb"]} if r.get("tb") else {}),
            "sx": gender or "", "k": kind, "lv": level, "tag": tag,
            "sl": slugify(base_tournament(r.get("tournament", ""))),
            "fin": (rd.strip().lower() in ("final", "finals")) and kind == "singles",
            "win": (r["p%d" % r["winner"]]["name"] if r.get("winner") in (1, 2) else ""),
        })
        try:
            import tennis_videos
            if kind == "singles" and r.get("winner") in (1, 2) and tennis_videos.highlight_for(r):
                out[-1]["v"] = 1
        except Exception:
            pass
        st = match_stats(r)
        out[-1]["bd"], out[-1]["dom"], out[-1]["tbn"] = (st[0], st[1], st[2]) if st else ([], None, 0)
        out[-1]["_c"] = (st[4], -st[3]) if (st and kind == "singles" and len(r["games"][0]) >= 2
                                            and (len(r["games"][0]) >= 3 or st[2])) else None
    best = {}
    for o in out:
        if o["_c"] is not None and (o["d"] not in best or o["_c"] < best[o["d"]]["_c"]):
            best[o["d"]] = o
    for o in best.values():
        o["bd"].append("closest")
    for o in out:
        o.pop("_c", None)
    return out


def _date_key(r):
    return (r.get("date", ""), -_round_rank(r.get("round")))      # mais tarde = mais recente


def player_table(results):
    """Vitórias/derrotas e sequência por jogador (só singulares terminados)."""
    stats = {}
    for r in sorted([x for x in results if classify(x)[1] == "singles" and x.get("winner") in (1, 2)], key=_date_key):
        for i in (1, 2):
            p = r["p%d" % i]
            st = stats.setdefault(p["name"], {"name": p["name"], "c": (p.get("country") or "").upper(),
                                              "w": 0, "l": 0, "seq": [], "last": "", "t": "", "g": classify(r)[0] or "", "rk": None})
            won = r["winner"] == i
            if isinstance(p.get("rank"), int) and p["rank"] > 0:
                st["rk"] = p["rank"]
            st["w" if won else "l"] += 1
            st["seq"].append(won)
            st["last"], st["t"] = r.get("date", ""), base_tournament(r.get("tournament", ""))
    out = []
    for st in stats.values():
        n, cur = 0, st["seq"][-1]
        for v in reversed(st["seq"]):
            if v != cur:
                break
            n += 1
        st["streak"] = ("W" if cur else "L") + str(n)
        st["sn"] = n if cur else -n
        out.append(st)
    out.sort(key=lambda x: (-x["w"], x["l"], x["name"]))
    return out


PLAYERS_CSS = """<style>
.pp-fire{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:6px 0 22px}
.pp-fire a{display:flex;flex-direction:column;gap:6px;padding:14px;border-radius:20px;background:rgba(0,0,0,.22);border:1px solid rgba(244,239,224,.12);text-decoration:none;color:inherit;min-width:0}
.pp-fire a:first-child{background:#d9f23a;color:#0e3a2d;border-color:#d9f23a}
.pp-fire small{font:800 .64rem system-ui;letter-spacing:.1em;text-transform:uppercase;opacity:.75}
.pp-fire b{font:800 1.9rem/1 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}.pp-fire span{font:700 .92rem/1.2 system-ui;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pp-fire em{font:600 .72rem system-ui;font-style:normal;opacity:.7}
.pp-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}
.pp-seg{display:inline-flex;border:1px solid rgba(244,239,224,.16);border-radius:999px;padding:3px}
.pp-seg button{border:0;background:none;color:inherit;opacity:.7;font:600 .85rem system-ui;padding:6px 13px;border-radius:999px;cursor:pointer}
.pp-seg button.on{background:#d9f23a;color:#0e3a2d;opacity:1}
.pp-q{flex:1 1 220px;min-width:0;background:rgba(0,0,0,.22);border:1px solid rgba(244,239,224,.16);border-radius:999px;color:inherit;font:500 .95rem system-ui;padding:10px 16px}
.pp-list{display:flex;flex-direction:column;gap:8px}
.pp-row{display:grid;grid-template-columns:40px minmax(0,1fr) auto;gap:12px;align-items:center;padding:10px 12px;border-radius:16px;
background:rgba(0,0,0,.18);border:1px solid rgba(244,239,224,.08);text-decoration:none;color:inherit}
.pp-row:hover{border-color:rgba(217,242,58,.5)}
.pp-row .av,.pp-row .ini{width:40px;height:40px;border-radius:50%;object-fit:cover;background:rgba(244,239,224,.1);display:grid;place-items:center;font:800 .8rem system-ui;color:#d9f23a}
.pp-row .who{min-width:0}.pp-row .who b{display:block;font:700 1rem/1.25 system-ui;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pp-row .who>span{display:block;font:500 .76rem system-ui;opacity:.65;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pp-row .rt{display:flex;flex-direction:column;align-items:flex-end;gap:5px}
.pp-row .wl{font:800 1.05rem system-ui;font-variant-numeric:tabular-nums;white-space:nowrap}
.pp-form{display:flex;gap:3px}.pp-form i{width:8px;height:8px;border-radius:50%;background:rgba(244,239,224,.22)}.pp-form i.w{background:#d9f23a}
.pp-hot{display:inline-block;font:800 .62rem system-ui;letter-spacing:.06em;background:#d9f23a;color:#0e3a2d;border-radius:999px;padding:1px 7px;margin-left:6px;vertical-align:2px}
.pp-more{display:block;margin:14px auto 0;background:none;border:1px solid rgba(244,239,224,.2);color:inherit;border-radius:999px;padding:9px 18px;font:600 .9rem system-ui;cursor:pointer}
@media (max-width:520px){.pp-fire b{font-size:1.5rem}.pp-fire span{font-size:.82rem}}
</style>"""

PLAYERS_JS = """<script>(function(){var L=document.getElementById('pl'),R=[].slice.call(L.children),g='',s='w',q='',n=60,m=document.getElementById('pmore');
function draw(){var v=R.filter(function(r){return (!g||r.dataset.g===g)&&(!q||r.dataset.n.indexOf(q)>=0)});
v.sort(function(a,b){return s==='w'?(b.dataset.w-a.dataset.w)||(a.dataset.l-b.dataset.l):s==='s'?(b.dataset.s-a.dataset.s)||(b.dataset.w-a.dataset.w):((+a.dataset.r||9999)-(+b.dataset.r||9999))});
R.forEach(function(r){r.hidden=true});v.forEach(function(r,i){r.hidden=i>=n;L.appendChild(r)});m.hidden=v.length<=n}
function seg(id,f){var e=document.getElementById(id);e.onclick=function(ev){var b=ev.target.closest('button');if(!b)return;
[].forEach.call(e.children,function(x){x.className=x===b?'on':''});f(b.dataset.v);n=60;draw()}}
seg('pg',function(v){g=v});seg('ps',function(v){s=v});
document.getElementById('pq').oninput=function(e){q=e.target.value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');draw()};
m.onclick=function(){n+=60;draw()};draw()})();</script>"""


def players_page(results, tx):
    esc = html.escape
    import unicodedata
    import site_more
    rows = player_table(results)
    if not rows:
        return f'<section class="page-h"><h1>{esc(tx.get("players", "Players"))}</h1><p class="empty">{esc(tx.get("empty", ""))}</p></section>'

    def ini(nm):
        return "".join(w[0] for w in nm.split()[:2] if w).upper()

    def rk(r):
        return CUR_RANKS.get(r["name"]) or r.get("rk")
    fire = sorted([r for r in rows if r["sn"] >= 3], key=lambda r: (-r["sn"], -r["w"]))[:3]
    hero = ""
    if fire:
        hero = '<h2 class="dh">On fire</h2><div class="pp-fire">' + "".join(
            f'<a href="/p/{slugify(r["name"])}.html"><small>{"Longest run" if i == 0 else "Win streak"}</small><b>{r["sn"]}</b>'
            f'<span>{esc(r["name"])}</span><em>wins in a row · {esc(r["t"])}</em></a>' for i, r in enumerate(fire)) + "</div>"
    items = ""
    for r in rows[:600]:
        rr = rk(r)
        key = unicodedata.normalize("NFKD", r["name"]).encode("ascii", "ignore").decode().lower()
        form = "".join(f'<i class="{"w" if x else ""}"></i>' for x in r["seq"][-5:])
        hot = f'<span class="pp-hot">W{r["sn"]}</span>' if r["sn"] >= 3 else ""
        av = avatar(r["name"], "av") or f'<span class="ini">{esc(ini(r["name"]))}</span>'
        sub = " · ".join(x for x in [f"#{rr}" if rr else "", r["t"], r["last"][5:] if r["last"] else ""] if x)
        items += (f'<a class="pp-row" href="/p/{slugify(r["name"])}.html" data-n="{esc(key)}" data-g="{esc(r["g"])}" data-w="{r["w"]}" data-l="{r["l"]}" '
                  f'data-s="{r["sn"]}" data-r="{rr or ""}">{av}<div class="who"><b>{site_more.flag(r["c"], 12) if r["c"] else ""}{esc(r["name"])}'
                  f'{hot}</b><span>{esc(sub)}</span></div>'
                  f'<div class="rt"><span class="wl">{r["w"]}–{r["l"]}</span><span class="pp-form" aria-label="last 5">{form}</span></div></a>')
    return (PLAYERS_CSS + f'<section class="page-h"><h1>{esc(tx.get("players", "Players"))}</h1>'
            f'<p>{esc(tx.get("players_lead", "Wins, losses and streaks from the matches we track."))}</p></section>{hero}'
            f'<div class="pp-bar"><input id="pq" class="pp-q" type="search" placeholder="{esc(tx.get("search", "Search a player"))}">'
            '<div class="pp-seg" id="pg"><button class="on" data-v="">All</button><button data-v="men">Men</button><button data-v="women">Women</button></div>'
            '<div class="pp-seg" id="ps"><button class="on" data-v="w">Most wins</button><button data-v="s">Streak</button><button data-v="r">Ranking</button></div></div>'
            f'<div class="pp-list" id="pl">{items}</div><button class="pp-more" id="pmore">Show more</button>' + PLAYERS_JS)


def week_numbers(results, days=7):
    """Números dos últimos `days` dias, para o bloco da página inicial."""
    import datetime as dt
    today = dt.datetime.now(dt.timezone.utc).date()
    start = (today - dt.timedelta(days=days - 1)).isoformat()
    rs = [r for r in results if r.get("date", "") >= start and classify(r)[1] == "singles"]
    n = {"matches": 0, "three": 0, "tb": 0, "comebacks": 0, "bagels": 0, "finals": 0}
    tourn, wins = set(), {}
    for r in rs:
        st = match_stats(r)
        if not st:
            continue
        n["matches"] += 1
        tourn.add(base_tournament(r.get("tournament", "")))
        n["three"] += 1 if len(r["games"][0]) >= 3 else 0
        n["tb"] += st[2]
        n["comebacks"] += 1 if "comeback" in st[0] else 0
        n["bagels"] += 1 if "bagel" in st[0] else 0
        n["finals"] += 1 if (r.get("round") or "").strip().lower() in ("final", "finals") else 0
        w = r["p%d" % r["winner"]]["name"]
        wins[w] = wins.get(w, 0) + 1
    top = max(wins.items(), key=lambda kv: (kv[1], kv[0])) if wins else None
    n["tournaments"] = len(tourn)
    n["top"] = top if top and top[1] >= 2 else None
    return n


def week_block(n, tx):
    esc = html.escape
    if n["matches"] < 3:
        return ""
    tiles = [(n["matches"], tx.get("w_matches", "matches")), (n["tournaments"], tx.get("w_tourn", "tournaments")),
             (n["three"], tx.get("w_three", "three-setters")), (n["tb"], tx.get("w_tb", "tie-breaks")),
             (n["comebacks"], tx.get("w_comeback", "comebacks")), (n["bagels"], tx.get("w_bagel", "6-0 sets"))]
    h = "".join(f'<div class="nbox"><b>{v}</b><span>{esc(str(l))}</span></div>' for v, l in tiles)
    top = (f'<p class="topw">{esc(tx.get("w_top", "Most wins"))}: <b>{esc(n["top"][0])}</b> ({n["top"][1]})</p>' if n["top"] else "")
    return (f'<h2 class="sec"><span>{esc(tx.get("week", "This week in numbers"))}</span>'
            f'<a href="players.html">{esc(tx.get("players", "Players"))} →</a></h2><div class="numgrid">{h}</div>{top}')


CSS = """
a.mh{display:block;text-decoration:none;color:inherit}a.mh:hover{color:var(--v)}.mt:has(a.mh){position:relative;cursor:pointer;transition:border-color .15s}.mt:has(a.mh):hover{border-color:var(--v)}a.mh::after{content:"";position:absolute;inset:0;z-index:1}.mt a.nm{position:relative;z-index:2}
.numgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:0 0 10px}
.nbox{background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:14px;text-align:center}
.nbox b{display:block;font:700 2rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--v)}
.nbox span{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--s)}
.topw{color:var(--s);margin:4px 0 22px}.topw b{color:var(--c)}
.about{color:var(--c);line-height:1.65;font-size:15.5px;margin:6px 0 24px;max-width:68ch}.about b{font-weight:700}.about a{color:inherit;text-decoration:underline;text-decoration-color:var(--s);text-underline-offset:3px}
.srch{width:100%;padding:12px 14px;border-radius:12px;border:1px solid var(--e);background:var(--deep);color:var(--c);font-size:1rem;margin-top:8px}
.pt{width:100%;border-collapse:collapse;margin:14px 0 30px}
.pt th{font:600 .75rem system-ui;letter-spacing:.08em;text-transform:uppercase;color:var(--s);text-align:left;padding:8px 6px;border-bottom:1px solid var(--e)}
.pt td{padding:10px 6px;border-bottom:1px solid #123f31}
.pt .pn{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-weight:700}.pt small{color:var(--s);font-weight:400}
.pt .hot{color:var(--v);font-weight:700}.pt .lt{color:var(--s);font-size:.85rem}
@media(max-width:560px){.pt .lt{display:none}.pt th:last-child{display:none}.numgrid{grid-template-columns:repeat(2,1fr)}}
:root{--g:#0e3a2d;--deep:#09281f;--c:#f7f2e6;--v:#d9f23d;--s:#b0c4b7;--e:#2c5d4c}
*{box-sizing:border-box}
body{margin:0;background:var(--g);color:var(--c);font:16px/1.5 system-ui,"Segoe UI",Arial,sans-serif}
a{color:inherit}
.wrap{max-width:860px;margin:0 auto;padding:0 16px}
nav{display:flex;justify-content:space-between;align-items:center;padding:20px 0}
.brand{font:700 1.15rem Georgia,"Times New Roman",serif;letter-spacing:.22em;text-decoration:none}
nav div a{margin-left:18px;color:var(--s);text-decoration:none;font-size:.95rem}
nav div a:hover,nav div a.on{color:var(--c)}
.hero{text-align:center;padding:24px 0 40px}
.emb{width:min(250px,64vw);height:auto}
h1{font:700 2.6rem/1.05 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:24px 0 12px;letter-spacing:-.01em}
h1 em{color:var(--v);font-weight:400}
.hero p{color:var(--s);max-width:34ch;margin:0 auto 26px}
.btn{display:inline-block;background:var(--v);color:var(--g);font-weight:700;padding:13px 24px;border-radius:999px;text-decoration:none;margin:4px}
.btn.ghost{background:none;color:var(--c);border:2px solid var(--c)}
h2.sec{font:700 1.4rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:12px 0 14px;display:flex;justify-content:space-between;align-items:baseline}
h2.sec a{font:500 .9rem system-ui;color:var(--v)}
.page-h{padding:10px 0 6px}.page-h h1{font-size:2.1rem;margin:0 0 6px;text-align:left}
.page-h p{color:var(--s);margin:0}
.filters{position:sticky;top:0;z-index:5;background:var(--g);padding:12px 0 10px;border-bottom:1px solid var(--e)}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:8px}
.seg{display:inline-flex;border:1px solid var(--e);border-radius:999px;overflow:hidden}
.seg button{background:none;border:0;color:var(--s);padding:7px 14px;font:600 .85rem system-ui;cursor:pointer}
.seg button.on{background:var(--v);color:var(--g)}
.filters select,.filters input{background:var(--deep);color:var(--c);border:1px solid var(--e);border-radius:999px;padding:8px 14px;font:500 .9rem system-ui;min-width:0}
.filters select{max-width:100%;flex:1 1 200px}.filters input{flex:1 1 160px}
.count{color:var(--s);font-size:.8rem}
.dh{font:700 1.05rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:26px 0 8px;color:var(--v)}
.tg{background:var(--deep);border:1px solid var(--e);border-radius:20px;padding:6px 16px 8px;margin:0 0 12px}
.th{margin:10px 0 2px;font:700 .95rem system-ui;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.tag{background:var(--v);color:var(--g);border-radius:6px;padding:1px 7px;font:800 .68rem system-ui;letter-spacing:.06em;text-transform:uppercase}
.mt{padding:8px 0}.mt+.mt{border-top:1px solid var(--e)}
.mh{color:var(--s);font-size:.78rem;margin-bottom:2px}
.pl{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:3px 0;color:var(--s)}
.pl.win{color:var(--c)}
.nm{font:700 1.02rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}.pl small{color:var(--s);margin-left:6px;font-size:.72rem}
.ch{display:flex;gap:5px;flex:none}
.ch b{min-width:32px;height:32px;border-radius:9px;border:1px solid var(--e);color:var(--s);display:grid;place-items:center;font:700 .95rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}.ch b{grid-auto-flow:column;gap:0}.ch b sup{font-size:.6em;font-weight:600;opacity:.75;align-self:start;margin-top:5px}
.ch b.on{background:var(--v);border-color:var(--v);color:var(--g)}
.bd{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0 2px}
.bd i{font:600 .68rem system-ui;font-style:normal;color:var(--v);border:1px solid var(--v);border-radius:999px;padding:1px 8px;letter-spacing:.03em}
.bd i.hot{background:var(--v);color:var(--g)}
.seg button.hl{color:var(--v)}.seg button.hl.on{color:var(--g)}
.strip{display:flex;gap:10px;overflow-x:auto;padding:14px 0 6px;scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch}
.tc{flex:0 0 200px;scroll-snap-align:start;text-align:left;background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:10px 12px;color:var(--c);cursor:pointer;display:flex;flex-direction:column;gap:3px;font:inherit}
.tc.on{border-color:var(--v);box-shadow:0 0 0 1px var(--v) inset}
.tc b{font:700 .92rem/1.2 system-ui;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;min-height:2.4em}
.tc small{color:var(--s);font-size:.72rem}.tc em{font:600 .76rem system-ui;font-style:normal;color:var(--v)}
.tt{display:flex;align-items:center;justify-content:space-between;min-height:20px}
.dot{width:8px;height:8px;border-radius:50%;background:var(--v);box-shadow:0 0 0 3px rgba(217,242,61,.25)}
.allbtn{background:none;border:1px solid var(--e);color:var(--c);border-radius:999px;padding:8px 14px;font:600 .85rem system-ui;cursor:pointer}
.allt{background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:10px;margin:8px 0}
.allt input{width:100%;background:var(--g);color:var(--c);border:1px solid var(--e);border-radius:999px;padding:8px 14px;margin-bottom:8px}
#alllist{max-height:260px;overflow:auto;display:flex;flex-direction:column}
#alllist button{background:none;border:0;border-top:1px solid var(--e);color:var(--c);text-align:left;padding:8px 4px;font:500 .88rem system-ui;cursor:pointer}
#alllist small{color:var(--s);margin-left:auto;white-space:nowrap;font-size:.78rem}
#alllist button{display:flex;align-items:center;gap:8px}#alllist .an{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.strip:not(.end){-webkit-mask-image:linear-gradient(to right,#000 calc(100% - 44px),transparent);mask-image:linear-gradient(to right,#000 calc(100% - 44px),transparent)}
.th a{text-decoration:none}.th a:hover{text-decoration:underline}
.champ{color:var(--v)!important;margin-top:6px!important}.champ b{color:var(--c)}
.page-h a{color:var(--v);text-decoration:none;font-size:.9rem}
.bk{display:grid;grid-template-columns:repeat(3,minmax(210px,1fr));gap:0 30px;overflow-x:auto;padding:4px 2px 12px}
.bc{display:grid;position:relative}
.bc.q{grid-template-rows:auto repeat(4,1fr)}.bc.s{grid-template-rows:auto repeat(2,2fr)}.bc.f{grid-template-rows:auto 4fr}
.bc h4{margin:0 0 8px;font:700 .72rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--v)}
.bcell{display:flex;align-items:center;padding:5px 0;position:relative}
.bc.q .bcell::after,.bc.s .bcell::after{content:"";position:absolute;right:-30px;width:30px;top:50%;border-top:1px solid var(--e)}
.bm.bup{border-style:dashed}.bwhen{display:block;font:600 .7rem system-ui;letter-spacing:.06em;color:var(--v);margin:4px 0 2px}
.bm.blink{display:block;text-decoration:none;color:inherit}.bm.blink:hover{border-color:var(--v)}
.bm.blive{display:block;text-decoration:none;color:inherit;border-color:var(--v)}.blv{display:inline-block;font:700 .62rem system-ui;letter-spacing:.12em;color:var(--g);background:var(--v);border-radius:6px;padding:1px 6px;margin:4px 0 2px}
.bm{background:var(--deep);border:1px solid var(--e);border-radius:12px;padding:4px 10px;width:100%}
.bm .pl{padding:3px 0;gap:8px}.bm .pl+.pl{border-top:1px solid var(--e)}
.bm .nm{font:700 .86rem system-ui;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.bm .ch b{min-width:24px;height:24px;border-radius:7px;font-size:.8rem}
.bm.tbd{color:var(--s);font:500 .8rem system-ui;text-align:center;padding:14px 10px;border-style:dashed}
.more{display:block;margin:20px auto;background:none;color:var(--c);border:2px solid var(--c);border-radius:999px;padding:10px 22px;font:700 .9rem system-ui;cursor:pointer}
.empty{color:var(--s);padding:24px 0}
footer{color:var(--s);font-size:.8rem;padding:28px 0 44px;border-top:1px solid var(--e);margin-top:28px}
@media(max-width:520px){h1{font-size:2.2rem}.ch b{min-width:28px;height:28px}.nm{font-size:.95rem}}

html,body{max-width:100%;overflow-x:hidden}
.wrap{min-width:0}
input,select,textarea{font-size:16px!important}
nav{flex-wrap:wrap;gap:8px 14px}
nav div{display:flex;flex-wrap:wrap;gap:4px 16px}
nav div a{margin-left:0!important}
.allt{max-width:100%;overflow:hidden}.allt input{max-width:100%}
#alllist{max-height:38vh}
@media(max-width:700px){
 .filters{position:static;border-bottom:0;padding:8px 0}
 .row{gap:6px;margin-bottom:6px}
 .seg button{padding:6px 11px;font-size:.82rem}
 h1{font-size:2.1rem}
 .brand{font-size:1rem;letter-spacing:.14em}
 nav div a{font-size:.88rem}
 .page-h h1{font-size:1.9rem}
}
"""

JS = r"""
const D=JSON.parse(document.getElementById('data').textContent);
const UI=JSON.parse(document.getElementById('ui').textContent);
const AV=new Set(UI.av||[]);
const LV={tour:0,challenger:1,itf:2,other:3};
const st={sx:'all',k:'singles',lv:'all',t:'',q:'',h:'',n:60};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const $=id=>document.getElementById(id);
function load(){try{const p=new URLSearchParams(location.hash.slice(1));for(const k of ['sx','k','lv','t','q','h'])if(p.has(k))st[k]=p.get(k);}catch(e){}}
function save(){try{const p=new URLSearchParams();for(const k of ['sx','k','lv','t','q','h'])if(st[k]&&!((k==='sx'||k==='lv')&&st[k]==='all')&&!(k==='k'&&st[k]==='singles'))p.set(k,st[k]);history.replaceState(null,'','#'+p.toString());}catch(e){}}
function base(){return D.filter(r=>(st.sx==='all'||r.sx===st.sx)&&(st.k==='all'||r.k===st.k)&&(st.lv==='all'||r.lv===st.lv)&&(!st.h||r.bd.length>0));}
function matches(){const q=st.q.trim().toLowerCase();return base().filter(r=>(!st.t||r.t===st.t)&&(!q||(r.a+' '+r.b).toLowerCase().includes(q)));}
function seg(id,key,opts){$(id).innerHTML=opts.map(([v,l])=>`<button data-v="${v}" class="${st[key]===v?'on':''}">${esc(l)}</button>`).join('');
 $(id).onclick=e=>{const v=e.target.dataset&&e.target.dataset.v;if(v===undefined)return;st[key]=v;st.t='';st.n=60;draw();};}
function chips(r,i){return r.g[i].map((x,j)=>{const o=r.g[1-i][j],t=r.tb&&r.tb[i]?r.tb[i][j]:null;return `<b class="${x>o?'on':''}">${x}${t!=null&&x==6&&o==7?`<sup>${t}</sup>`:''}</b>`}).join('');}
function bdg(r){return r.bd.length?`<div class="bd">${r.bd.map(b=>{const l=b==='tb'?UI.bd.tb.replace('{n}',r.tbn)+(r.tbn>1?'s':''):UI.bd[b];return `<i class="${b==='closest'||b==='comeback'?'hot':''}">${esc(l)}</i>`}).join('')}</div>`:'';}
function mrow(r){const m=[r.rd,r.sf,r.dom?r.dom+'% '+UI.games:''].filter(Boolean).join(' · ');
 const p=(i,n,c,sl)=>`<div class="pl ${r.w===i+1?'win':''}"><div>${r.k==='singles'&&sl?`${AV.has(sl)?`<img class="av" src="/img/${esc(sl)}.jpg" alt="${esc(n)}" loading="lazy" width="28" height="28">`:''}<a class="nm" href="/p/${esc(sl)}.html">${esc(n)}</a>`:`<span class="nm">${esc(n)}</span>`}<small>${esc(c)}</small></div><div class="ch">${chips(r,i)}</div></div>`;
 return `<div class="mt">${r.k==='singles'&&r.id!=null?`<a class="mh" href="/m/${r.id}.html">${r.v?'<span style="background:#d9f23d;color:#0a221a;border-radius:999px;padding:1px 8px;font-weight:800;margin-right:6px;white-space:nowrap">▶ Highlights</span>':''}${esc(m)} ›</a>`:`<div class="mh">${esc(m)}</div>`}${p(0,r.a,r.ac,r.as)}${p(1,r.b,r.bc,r.bs)}${bdg(r)}</div>`;}
function draw(){
 seg('sx','sx',[['all',UI.all],['men',UI.men],['women',UI.women]]);
 seg('k','k',[['singles',UI.singles],['doubles',UI.doubles],['all',UI.all]]);
 seg('lv','lv',[['all',UI.all],['tour','Tour'],['challenger','Challenger'],['itf','ITF']]);
 seg('h','h',[['',UI.all],['1','\u2605 '+UI.hl]]);
 const pool=base();const ts={};
 pool.forEach(r=>{const o=ts[r.t]||(ts[r.t]={n:0,d:'',lv:r.lv,tag:r.tag,sf:r.sf,sl:r.sl,champ:''});o.n++;if(r.d>o.d)o.d=r.d;if(r.fin&&r.win)o.champ=r.win;});
 const names=Object.keys(ts).sort((x,y)=>ts[y].d.localeCompare(ts[x].d)||(LV[ts[x].lv]-LV[ts[y].lv])||x.localeCompare(y));
 if(st.t&&!ts[st.t])st.t='';
 const fd=d=>{try{return new Date(d+'T00:00:00Z').toLocaleDateString(UI.lang,{month:'short',day:'numeric',timeZone:'UTC'})}catch(e){return d}};
 const today=new Date();const age=d=>Math.round((Date.UTC(today.getFullYear(),today.getMonth(),today.getDate())-Date.parse(d+'T00:00:00Z'))/864e5);
 const recent=names.filter(n=>age(ts[n].d)<=10).sort((x,y)=>((age(ts[x].d)<=2?0:1)-(age(ts[y].d)<=2?0:1))||(LV[ts[x].lv]-LV[ts[y].lv])||ts[y].d.localeCompare(ts[x].d)||x.localeCompare(y));
 $('strip').innerHTML=recent.map(n=>{const o=ts[n];const live=age(o.d)<=2;
  return `<button class="tc ${n===st.t?'on':''}" data-t="${esc(n)}"><span class="tt">${o.tag?`<span class="tag">${esc(o.tag)}</span>`:''}${live?'<span class="dot"></span>':''}</span><b>${esc(n)}</b><small>${esc([o.sf,fd(o.d)].filter(Boolean).join(' · '))}</small><em>${o.champ?esc(UI.champ+': '+o.champ):o.n+' '+esc(o.n===1?UI.one:UI.matches)}</em></button>`;}).join('');
 $('strip').style.display=recent.length?'flex':'none';
 (function(){const el=$('strip');const f=()=>el.classList.toggle('end',el.scrollLeft+el.clientWidth>=el.scrollWidth-6);el.onscroll=f;f();})();
 $('strip').onclick=e=>{const c=e.target.closest('.tc');if(!c)return;const v=c.dataset.t;st.t=st.t===v?'':v;st.n=60;draw();};
 $('allbtn').textContent=(st.t?st.t+' ✕':UI.tours+' ('+names.length+')');
 $('allbtn').onclick=()=>{if(st.t){st.t='';st.n=60;draw();}else{const p=$('allt');p.hidden=!p.hidden;if(!p.hidden)$('tq').focus();}};
 const tq=$('tq').value.trim().toLowerCase();
 $('alllist').innerHTML=names.filter(n=>!tq||n.toLowerCase().includes(tq)).slice(0,200).map(n=>`<button data-t="${esc(n)}">${ts[n].tag?`<span class="tag">${esc(ts[n].tag)}</span> `:''}<span class="an">${esc(n)}</span> <small>${esc(fd(ts[n].d))} · ${ts[n].n} ${esc(ts[n].n===1?UI.one:UI.matches)}</small></button>`).join('');
 $('alllist').onclick=e=>{const c=e.target.closest('button');if(!c)return;st.t=c.dataset.t;st.n=60;$('allt').hidden=true;draw();};
 const all=matches();$('cnt').textContent=all.length+' '+(all.length===1?UI.one:UI.matches);
 const shown=all.slice(0,st.n);const days={};
 shown.forEach(r=>{((days[r.d]=days[r.d]||{})[r.t]=days[r.d][r.t]||[]).push(r);});
 let h='';
 Object.keys(days).sort().reverse().forEach(d=>{
  let label=d;try{label=new Date(d+'T12:00:00').toLocaleDateString(UI.lang,{weekday:'long',day:'numeric',month:'long'});}catch(e){}
  h+=`<h2 class="dh">${esc(label)}</h2>`;
  Object.keys(days[d]).sort((a,b)=>{const x=days[d][a][0],y=days[d][b][0];return (LV[x.lv]-LV[y.lv])||a.localeCompare(b);}).forEach(t=>{
   const ms=days[d][t].sort((a,b)=>a.ro-b.ro);const tag=ms[0].tag?`<span class="tag">${esc(ms[0].tag)}</span>`:'';
   h+=`<section class="tg"><h3 class="th">${tag}<a href="/t/${esc(ms[0].sl)}.html">${esc(t)}</a></h3>${ms.map(mrow).join('')}</section>`;});});
 if(!h)h=`<p class="empty">${esc(UI.empty)}</p>`;
 if(all.length>shown.length)h+=`<button class="more" id="more">${esc(UI.more)}</button>`;
 $('list').innerHTML=h;const mb=$('more');if(mb)mb.onclick=()=>{st.n+=60;draw();};
 save();}
load();$('q').value=st.q;
$('tq').oninput=()=>draw();
$('q').oninput=e=>{st.q=e.target.value;st.n=60;draw();};
draw();
"""


def tbsup(r, i, k):
    """Pontos do tie-break do jogador i (0/1) no set k, como '<sup>5</sup>', só em sets 7-6 com o dado guardado."""
    t = r.get("tb")
    try:
        a, b = r["games"][i][k], r["games"][1 - i][k]
        v = t[i][k] if t else None
    except (IndexError, TypeError, KeyError):
        return ""
    return f"<sup>{int(v)}</sup>" if v is not None and a == 6 and b == 7 else ""      # convenção: 7-6⁵ (pontos de quem perdeu o set)


def match_html(r, tr, esc=html.escape):
    lines = []
    for i in (0, 1):
        p = r["p%d" % (i + 1)]
        chips = ""
        for k, (a_, b_) in enumerate(zip(r["games"][0], r["games"][1])):
            mine, other = (a_, b_) if i == 0 else (b_, a_)
            chips += f'<b class="{"on" if mine > other else ""}">{mine}{tbsup(r, i, k)}</b>'
        lines.append(f'<div class="pl {"win" if r.get("winner") == i + 1 else ""}"><div>{name_html(p, r, esc)}'
                     f'<small>{esc(who_tag(p))}</small></div><div class="ch">{chips}</div></div>')
    rd = r.get("round") or ""
    meta = " · ".join(x for x in [r.get("date", ""), tr["rounds"].get(rd.lower(), rd), tr["surfaces"].get(r.get("surface"), "")] if x)
    st = match_stats(r)
    bd = ""
    if st:
        names = {"comeback": "b_comeback", "bagel": "b_bagel", "breadstick": "b_breadstick", "super": "b_super"}
        tags = [tr["_tx"][names[b]] for b in st[0] if b in names]
        if st[2]:
            tags.append(tr["_tx"]["b_tb"].format(n=st[2]) + ("s" if st[2] > 1 else ""))
        bd = ('<div class="bd">' + "".join(f"<i>{esc(t)}</i>" for t in tags) + "</div>") if tags else ""
        meta += f' · {st[1]}% {tr["_tx"]["f_games"]}'
    return f'<div class="mt">{mh_html(r, meta, esc)}{lines[0]}{lines[1]}{bd}</div>'


def _bm(r, tx, esc=html.escape):
    """Cartão compacto de um jogo no quadro."""
    if r is None:
        return f'<div class="bm tbd">{esc(tx["f_tbd"])}</div>'
    rows = ""
    for i in (0, 1):
        p = r["p%d" % (i + 1)]
        chips = "".join(f'<b class="{"on" if (a if i == 0 else b) > (b if i == 0 else a) else ""}">{a if i == 0 else b}{tbsup(r, i, k)}</b>'
                        for k, (a, b) in enumerate(zip(r["games"][0], r["games"][1])))
        rows += (f'<div class="pl {"win" if r.get("winner") == i + 1 else ""}"><span class="nm">{esc(p["name"])}</span>'
                 f'<div class="ch">{chips}</div></div>')
    if r.get("_up"):                                # jogo marcado (ainda por jogar): nomes + hora
        t = r["_up"]
        import site_ui
        when = site_ui.ltime(t, f'{t[8:10]}/{t[5:7]} · {t[11:16]} UTC', "dm") if len(t) >= 16 else ""
        names = "".join(f'<div class="pl"><span class="nm">{esc(r["p%d" % i]["name"])}</span></div>' for i in (1, 2))
        return f'<div class="bm bup"><span class="bwhen">{when}</span>{names}</div>'
    if r.get("_live"):                              # jogo a decorrer (página /live/): destacado e com link
        return f'<a class="bm blive" href="/live/{r["id"]}.html"><span class="blv">LIVE</span>{rows}</a>'
    if r.get("id") is not None and r.get("winner") in (1, 2):   # jogo terminado: abre a página do jogo
        return f'<a class="bm blink" href="/m/{r["id"]}.html">{rows}</a>'
    return f'<div class="bm">{rows}</div>'


def bracket_html(singles, tr, tx):
    """Quadro dos quartos de final até à final, só com os jogos que temos (o resto fica 'por apurar')."""
    by = {0: [], 1: [], 2: []}
    for r in singles:
        k = _round_rank(r.get("round"))
        if k in by:
            by[k].append(r)
    if not any(by.values()):
        return ""
    fin = by[0][:1]
    sfs = by[1][:2]
    qfs = by[2][:4]
    # ordena os quartos para ficarem ao lado da meia-final em que o vencedor jogou
    def sf_index(q):
        w = q["p%d" % q["winner"]]["name"] if q.get("winner") in (1, 2) else None
        for i, sf in enumerate(sfs):
            if w and w in (sf["p1"]["name"], sf["p2"]["name"]):
                return i
        return 9
    qfs = sorted(qfs, key=sf_index)
    slots_q = [None] * 4
    used = set()
    for q in qfs:                                  # coloca cada quarto nos 2 lugares da sua meia-final
        base = sf_index(q)
        spots = [base * 2, base * 2 + 1] if base < 2 else [0, 1, 2, 3]
        for sp in spots:
            if sp < 4 and sp not in used:
                slots_q[sp] = q; used.add(sp); break
    # meias-finais ordenadas pelo índice
    sfo = sfs + [None] * (2 - len(sfs))
    lab = lambda k, d: tr["rounds"].get(k, d)
    col = lambda title, cls, cells: (f'<div class="bc {cls}"><h4>{html.escape(title)}</h4>'
                                       + "".join(f'<div class="bcell">{_bm(c, tx)}</div>' for c in cells) + '</div>')
    return (f'<h2 class="dh">{html.escape(tx["f_bracket"])}</h2><div class="bk">'
            + col(lab("1/4-finals", "Quarterfinals"), "q", slots_q)
            + col(lab("semi-finals", "Semifinals"), "s", sfo)
            + col(lab("final", "Final"), "f", fin + [None] * (1 - len(fin)))
            + '</div>')


def _upcoming_html(name, ups, tx):
    """Próximos jogos (com adversário já definido) deste torneio. Só aparecem jogos ainda por jogar."""
    esc = html.escape
    n = slugify(name)
    keep = []
    for u in ups or []:
        tp = slugify(re.sub(r"^(atp|wta|challenger|itf)\s+", "", (u.get("tp") or "").lower()))
        if tp and (tp == n or tp in n or n in tp):
            keep.append(u)
    keep.sort(key=lambda u: (u.get("t") or "", _round_rank(u.get("round"))))
    if not keep:
        return ""
    import site_ui
    import site_more
    rows = ""
    for u in keep[:16]:
        t = (u.get("t") or "")
        tm = (f'<time class="lt" datetime="{esc(t)}">{esc(t[11:16])}</time><small class="ld" data-d="{esc(t)}">{esc(t[8:10])}/{esc(t[5:7])}</small>'
              if len(t) >= 16 else '<b>TBC</b>')
        pls = [(f'<span class="nm">{esc(p["name"])}</span>',
                f'{site_more.flag(p.get("country"), 11)}{("#" + str(p["rank"])) if isinstance(p.get("rank"), int) else ""}', "", "")
               for p in (u["p1"], u["p2"])]
        rows += site_ui.match_tile(tm, u.get("round") or "", pls, court=u.get("court") or "")
    js = ('<script>document.querySelectorAll(".ui-mt time.lt[datetime]").forEach(function(e){var d=new Date(e.getAttribute("datetime"));'
          'if(isNaN(d))return;e.textContent=d.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",hour12:false});var s=e.nextElementSibling;'
          'if(s&&s.classList.contains("ld")){var t=new Date();s.textContent=d.toDateString()===t.toDateString()?"Today":d.toLocaleDateString([],{weekday:"short"})}})</script>')
    return f'{site_ui.sec(esc(tx.get("next", "Next matches")), "/order-of-play.html", "Order of play")}<div class="ui-row wide">{rows}</div>{js}'


def scheduled_for(name, ups, skip_ids=(), gender=None):
    """Jogos marcados (quartos em diante, adversário definido) deste torneio, no formato do quadro."""
    import time as _t
    n = slugify(name)
    now = _t.strftime("%Y-%m-%dT%H:%M", _t.gmtime(_t.time() - 3 * 3600))
    out = []
    for u in ups or []:
        tp = slugify(re.sub(r"^(atp|wta|challenger|itf)\s+", "", (u.get("tp") or "").lower()))
        if not tp or not (tp == n or tp in n or n in tp) or str(u.get("id")) in skip_ids:
            continue
        if gender and u.get("gender") and u["gender"] != gender:
            continue
        if (u.get("t") or "") < now or _round_rank(u.get("round")) > 2:
            continue
        out.append({"id": u.get("id"), "round": u.get("round") or "", "date": (u.get("t") or "")[:10],
                    "p1": u["p1"], "p2": u["p2"], "games": [[], []], "_up": u.get("t") or ""})
    return out


def _tournament_top(singles, tag):
    import home_ui
    import rank_ui
    big = lambda n: f"/img/big/{slugify(n)}.jpg" if slugify(n) in AVATARS else ""
    ini = lambda n: "".join(w[0] for w in (n or "?").split()[:2]).upper()
    cards = []
    for r in singles:
        if r.get("winner") in (1, 2) and (r.get("round") or "").strip().lower() in ("final", "finals"):
            g = classify(r)[0]
            if any(c[0] == g for c in cards):
                continue
            W, L = r["p%d" % r["winner"]], r["p%d" % (3 - r["winner"])]
            sc = " ".join(f"{x}-{y}" for x, y in zip(r["games"][r["winner"] - 1], r["games"][2 - r["winner"]]))
            cards.append((g, home_ui.lead(f"/m/{r['id']}.html", big(W["name"]), ini(W["name"]), [tag or "", "Champion"], W["name"],
                                          f"Beat {L['name']} {sc} in the final · {r.get('date', '')}")))
    if cards:
        return rank_ui.champions([c for _, c in sorted(cards, key=lambda c: c[0] != "men")])
    # em curso: quem ainda não perdeu, na ronda mais adiantada
    lost = {slugify(r["p%d" % (3 - r["winner"])]["name"]) for r in singles if r.get("winner") in (1, 2)}
    best = {}
    for r in singles:
        if r.get("winner") not in (1, 2) or r.get("q"):
            continue
        W = r["p%d" % r["winner"]]
        k = slugify(W["name"])
        if k in lost:
            continue
        rr = _round_rank(r.get("round"))
        if k not in best or rr < best[k][0]:
            best[k] = (rr, W, r)
    if len(best) < 2:
        return ""
    try:                                                     # torneio parado há mais de 3 dias: não dizemos quem "ainda está"
        import datetime as _dt
        if (_dt.date.today() - _dt.date.fromisoformat(max(r.get("date", "") for r in singles)[:10])).days > 3:
            return ""
    except ValueError:
        return ""
    lo = min(v[0] for v in best.values())                    # só quem está na ronda mais adiantada ou na anterior (dados com falhas)
    top = sorted([v for v in best.values() if v[0] <= lo + 1], key=lambda x: (x[0], (x[1].get("rank") or 9999)))[:8]
    if len(top) < 2:
        return ""
    nxt = {1: "Into the final", 2: "Into the semi-finals", 3: "Into the quarter-finals"}
    items = [(nxt.get(rr, "Still in"), [big(W["name"])] if big(W["name"]) else [], ini(W["name"]), W["name"],
              f'{(W.get("country") or "").upper()}' + (f' · No. {W["rank"]}' if isinstance(W.get("rank"), int) else ""),
              f"/p/{slugify(W['name'])}.html") for rr, W, r in top]
    return f'<style>{rank_ui.CSS}</style><h2 class="dh">Still in the draw</h2>' + rank_ui.climbers(items)


def tournament_page(name, rs, tr, tx, upcoming=None):
    """Corpo da página de um torneio (singulares primeiro, pares depois)."""
    esc = html.escape
    tr = dict(tr, _tx=tx)
    first = rs[0]
    gender, _, level, tag = classify(first)
    singles = sorted([r for r in rs if classify(r)[1] == "singles"], key=lambda r: (r["date"], -_round_rank(r.get("round"))), reverse=True)
    doubles = [r for r in rs if classify(r)[1] == "doubles"]
    champ = next((r["p%d" % r["winner"]]["name"] for r in singles if r.get("winner") in (1, 2)
                  and (r.get("round") or "").strip().lower() in ("final", "finals")), "")
    surf = tr["surfaces"].get(first.get("surface"), "")
    dates = sorted(r["date"] for r in rs)
    sub = " · ".join(x for x in [surf, dates[0] if dates[0] == dates[-1] else f"{dates[0]} → {dates[-1]}"] if x)
    tagh = f'<span class="tag">{esc(tag)}</span> ' if tag else ""
    h = (f'<section class="page-h"><p><a href="../results.html">← {esc(tx["title"])}</a></p>'
         f'<h1>{tagh}{esc(name)}</h1><p>{esc(sub)}</p>'
         + (f'<p class="champ">{esc(tx["f_champion"])}: <b>{esc(champ)}</b></p>' if champ else "") + '</section>')
    try:                                                     # 13/11/2026: campeões com foto grande, ou quem ainda está em prova
        h += _tournament_top(singles, tag)
    except Exception as e:
        print("Topo do torneio falhou:", name, type(e).__name__, e)
    def sec(title, items):
        if not items:
            return ""
        body = "".join(match_html(r, tr) for r in items)
        return f'<h2 class="dh">{esc(title)}</h2><section class="tg">{body}</section>'
    _sched = scheduled_for(name, upcoming, {str(r.get("id")) for r in rs})
    h += _upcoming_html(name, upcoming, tx) + bracket_html(singles + _sched, tr, tx) + sec(tx["f_singles"], singles) + sec(tx["f_doubles"], doubles)
    return h


def results_page(results, tr, tx, lang):
    esc = html.escape
    data = prepare(results, tr)
    ui = {"all": tx["f_all"], "men": tx["f_men"], "women": tx["f_women"], "singles": tx["f_singles"],
          "doubles": tx["f_doubles"], "alltour": tx["f_alltour"], "matches": tx["f_matches"], "one": tx.get("f_match", "match"), "av": sorted(AVATARS),
          "more": tx["f_more"], "empty": tx["empty"], "lang": lang, "hl": tx["f_highlights"],
          "bd": {"comeback": tx["b_comeback"], "bagel": tx["b_bagel"], "breadstick": tx["b_breadstick"],
                 "super": tx["b_super"], "tb": tx["b_tb"], "closest": tx["b_closest"]}, "games": tx["f_games"],
          "champ": tx["f_champion"], "searchtour": tx["f_search_tour"], "tours": tx["f_tournaments"]}
    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    ui_json = json.dumps(ui, ensure_ascii=False).replace("</", "<\\/")
    fallback = "".join(
        f'<p class="empty">{esc(r["a"])} – {esc(r["b"])} · {esc(r["t"])}</p>'
        for r in [x for x in data if x["k"] == "singles"][:20])
    try:
        import tennis_videos
        hlrow = tennis_videos.cards(results, "▶ Latest match highlights", 12)
    except Exception:
        hlrow = ""
    return (f'<section class="page-h"><h1>{esc(tx["title"])}</h1><p>{esc(tx["lead"])}</p></section>{hlrow}'
            '<div class="filters">'
            '<div class="row"><div class="seg" id="sx"></div><div class="seg" id="k"></div></div>'
            '<div class="row"><div class="seg" id="lv"></div><div class="seg" id="h"></div></div>'
            f'<div class="row"><input id="q" type="search" placeholder="{esc(tx["f_player"])}" aria-label="{esc(tx["f_player"])}">'
            '<button class="allbtn" id="allbtn"></button><span class="count" id="cnt"></span></div></div>'
            '<div class="strip" id="strip"></div>'
            f'<div class="allt" id="allt" hidden><input id="tq" type="search" placeholder="{esc(tx["f_search_tour"])}"><div id="alllist"></div></div>'
            f'<div id="list"><noscript>{fallback}</noscript></div>'
            f'<script id="data" type="application/json">{data_json}</script>'
            f'<script id="ui" type="application/json">{ui_json}</script>'
            f'<script>{JS}</script>')
