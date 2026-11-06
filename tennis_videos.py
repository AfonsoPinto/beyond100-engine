"""Beyond100 (ténis): vídeos oficiais do YouTube, sem chave nem quota e SEM gastar pedidos da API de ténis.
Lê os feeds RSS públicos dos canais oficiais (ATP Challenger, Tennis TV, WTA, ATP Tour) e guarda-os em tennis_videos.json
(acumulado: cada feed só mostra os últimos 15 vídeos, por isso lê a cada atualização).
- highlight_for(r): o resumo oficial de um jogo (os dois apelidos no título, publicado até 5 dias depois do jogo);
- stream_for(tournament): a transmissão em direto no YouTube de hoje desse torneio (cidade no título), se houver;
- watch_live(tag): onde ver em direto (Challenger TV, 125Live da WTA, ITF Live): só ligação, não podem ser embebidos."""
import html
import json
import os
import re
import time
import unicodedata

FILE = "tennis_videos.json"
CHANNELS = {"UCT12ocLoA-sqRfs12yQM2Bg": "ATP Challenger", "UCbcxFkd6B9xUU54InHv4Tig": "Tennis TV",
            "UCaBIVVpHjq6j3tSyxwTE-8Q": "WTA", "UCY_5h5zaSwN7Or4kIJDYNXA": "ATP Tour"}
UA = {"User-Agent": "Mozilla/5.0 (compatible; Beyond100/0.1; +https://beyond100tennis.com)"}
LIVE_LINKS = {
    "challenger": ("Challenger TV", "https://www.atptour.com/en/atp-challenger-tour/challenger-tv", "Every ATP Challenger match streams free (free ATP account)."),
    "wta125": ("WTA 125Live", "https://www.wtatennis.com/streaming", "WTA 125 events stream on 125Live (up to two courts, free WTA account)."),
    "itf": ("ITF World Tennis Tour Live", "https://www.itftennis.com/en/world-tennis-tour-live/", "Selected ITF World Tennis Tour courts stream on the ITF site."),
}


def sync():
    import requests
    try:
        db = json.load(open(FILE, encoding="utf-8"))
    except (OSError, ValueError):
        db = {}
    new = 0
    for cid, cname in CHANNELS.items():
        r = None
        for attempt in range(3):                                  # os feeds do YouTube falham às vezes (404/500) para o GitHub
            try:
                r = requests.get("https://www.youtube.com/feeds/videos.xml", params={"channel_id": cid}, headers=UA, timeout=15)
                if r.status_code == 200:
                    break
                print("Vídeos ténis:", cname, "HTTP", r.status_code)
            except Exception as e:
                print("Vídeos ténis:", cname, type(e).__name__)
            time.sleep(2 + 3 * attempt)
        if r is None or r.status_code != 200:                     # plano B: o mesmo feed pela Cloudflare (função do site)
            try:
                site = (os.environ.get("SITE_URL") or "https://beyond100tennis.com").rstrip("/")
                r = requests.get(f"{site}/api/padel/yt/{cid}", headers=UA, timeout=20)
                print("Vídeos ténis:", cname, "via Cloudflare", r.status_code)
            except Exception as e:
                print("Vídeos ténis:", cname, "via Cloudflare falhou", type(e).__name__)
                continue
        if r is None or r.status_code != 200:
            continue
        for vid, title, pub in re.findall(r"<entry>.*?<yt:videoId>(.*?)</yt:videoId>.*?<title>(.*?)</title>.*?<published>(.*?)</published>", r.text, re.S):
            if vid not in db:
                db[vid] = {"title": html.unescape(title), "published": pub, "channel": cname}
                new += 1
    cut = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 120 * 86400))
    db = {k: v for k, v in db.items() if (v.get("published") or "") >= cut}
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=0)
    print(f"Vídeos ténis: {new} novos ({len(db)} guardados).")
    return new


_DB = None


def _db():
    global _DB
    if _DB is None:
        try:
            _DB = json.load(open(FILE, encoding="utf-8"))
        except (OSError, ValueError):
            _DB = {}
    return _DB


def _n(s):
    return " " + re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).strip() + " "


def _surname(name):
    t = _n(name).split()
    if not t:
        return ""
    # apelidos compostos ("de Minaur", "Van de Zandschulp"): fica o último bloco com partículas
    i = len(t) - 1
    while i > 1 and t[i - 1] in ("de", "da", "van", "von", "der", "del", "di", "le", "la", "dos", "du"):
        i -= 1
    return " ".join(t[i:])


def highlight_for(r):
    """O vídeo de resumo oficial deste jogo (singulares), ou None."""
    if " / " in r["p1"]["name"] or " / " in r["p2"]["name"]:
        return None
    a, b = _surname(r["p1"]["name"]), _surname(r["p2"]["name"])
    if len(a) < 3 or len(b) < 3 or a == b:
        return None
    d = r.get("date") or ""
    best = None
    for vid, v in _db().items():
        segs = [_n(x) for x in re.split(r"[;|]", v["title"])]            # 'Wong vs Jasika; Atmane vs Harris | Seoul ... Highlights'
        if not any(f" {a} " in x and f" {b} " in x and re.search(r" (vs?|takes on|beats|defeats|downs|edges|stuns|upsets|ousts|tops|d) ", x) for x in segs):
            continue
        t = _n(v["title"])
        p = (v.get("published") or "")[:10]
        if d and not (d <= p <= _plus(d, 5)):
            continue
        sc = (2 if "highlight" in t else 0) + (1 if "extended" in t else 0) + (2 if ";" not in v["title"] else 0)   # vídeo só deste jogo primeiro
        if best is None or sc > best[0]:
            best = (sc, vid, v)
    return dict(best[2], id=best[1]) if best else None


def _plus(iso, days):
    import datetime as dt
    try:
        return (dt.date.fromisoformat(iso) + dt.timedelta(days=days)).isoformat()
    except ValueError:
        return iso


GENERIC = {"challenger", "open", "cup", "trophy", "tennis", "men", "women", "mens", "womens", "singles", "doubles", "itf", "wta", "atp",
           "tour", "world", "international", "internationaux", "indoor", "the", "and", "city", "grand", "prix", "ch", "tournament"}


def city_words(tname):
    return [w for w in _n(re.sub(r"\b[MW]\d{2,3}\b|\b\d+\b", " ", tname or "")).split() if len(w) >= 4 and w not in GENERIC]


def stream_for(tname):
    """Transmissão em direto no YouTube (canais oficiais) deste torneio, publicada nas últimas 14 h."""
    ws = city_words(tname)
    if not ws:
        return None
    cut = time.strftime("%Y-%m-%dT%H:%M", time.gmtime(time.time() - 14 * 3600))
    for vid, v in sorted(_db().items(), key=lambda kv: kv[1].get("published", ""), reverse=True):
        t = _n(v["title"])
        if (v.get("published") or "") < cut or not re.search(r" live | court | centre | center | day \d", t) or re.search(r" vs? ", t) and "highlight" in t:
            continue
        if any(f" {w} " in t for w in ws):
            return dict(v, id=vid)
    return None


def provider(tag, gender=None, level=None):
    t = (tag or "").upper()
    if level == "challenger" or "CHALLENGER" in t or "WTA 125" in t:
        return "wta125" if (gender == "women" or "WTA" in t) else "challenger"
    if level == "itf" or t.startswith("ITF"):
        return "itf"
    return None


def embed(vid, title, autoplay=False):
    return (f'<div style="position:relative;padding-top:56.25%;border-radius:16px;overflow:hidden;background:#000;margin:12px 0">'
            f'<iframe src="https://www.youtube-nocookie.com/embed/{html.escape(vid)}?rel=0{"&autoplay=1&mute=1" if autoplay else ""}" title="{html.escape(title)}" '
            f'style="position:absolute;inset:0;width:100%;height:100%;border:0" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" '
            f'allowfullscreen loading="lazy"></iframe></div>')


def watch_block(tname, tag, gender=None, level=None, live=True):
    """Bloco 'Watch live' para um torneio a decorrer: o stream do YouTube embebido, se houver; senão a ligação oficial."""
    s = stream_for(tname)
    if s:
        return (f'<h2 class="dh"><span class="dot" style="display:inline-block;margin-right:8px"></span>Watch live</h2>'
                + embed(s["id"], s["title"], autoplay=False) + f'<p class="topw">{html.escape(s["title"])} · {html.escape(s["channel"])} on YouTube</p>')
    k = provider(tag, gender, level)
    if not k or not live:
        return ""
    name, url, note = LIVE_LINKS[k]
    return (f'<a class="wlive" href="{url}" target="_blank" rel="noopener" style="display:flex;align-items:center;gap:12px;margin:14px 0;'
            f'padding:14px 16px;border-radius:16px;background:#d9f23d;color:#0a221a;text-decoration:none">'
            f'<span style="font-size:1.4rem">▶</span><span style="flex:1"><b style="display:block">Watch live on {html.escape(name)} ↗</b>'
            f'<small style="opacity:.8">{html.escape(note)}</small></span></a>')


def highlight_block(r):
    h = highlight_for(r)
    if not h:
        return ""
    import yt_player
    box = yt_player.box([{"id": h["id"]}], "pd-video").replace('class="pd-video"', 'class="pd-video" style="position:relative;padding-top:56.25%;border-radius:16px;overflow:hidden;background:#000;margin:12px 0"', 1)
    box = box.replace("<iframe ", '<iframe style="position:absolute;inset:0;width:100%;height:100%;border:0" ', 1)
    return (f'<style>.pd-video iframe{{position:absolute;inset:0;width:100%;height:100%;border:0}}</style><h2 class="dh">▶ Highlights</h2>' + box +
            f'<p class="topw">{html.escape(h["title"])} · official video, {html.escape(h["channel"])} on YouTube</p>' + yt_player.JS)


CARD_CSS = """<style>.thl{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(230px,72%);gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;margin:8px 0 18px}
.thl::-webkit-scrollbar{display:none}.thl a{scroll-snap-align:start;display:flex;flex-direction:column;border-radius:16px;overflow:hidden;background:rgba(0,0,0,.22);border:1px solid rgba(255,255,255,.12);text-decoration:none;color:inherit}
.thl .th{position:relative}.thl img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;background:#000}
.thl i{position:absolute;left:10px;bottom:10px;width:38px;height:38px;border-radius:50%;background:#d9f23d;color:#0a221a;display:grid;place-items:center;font-style:normal}
.thl .tx{padding:9px 12px 11px;display:flex;flex-direction:column;gap:2px}.thl small{font:700 .66rem system-ui;letter-spacing:.08em;text-transform:uppercase;color:#d9f23d}
.thl b{font:700 .98rem system-ui}.thl span{font-size:.8rem;opacity:.75}@media(min-width:800px){.thl{grid-auto-columns:minmax(230px,30%)}}
.thl.grid{grid-auto-flow:row;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));overflow:visible}</style>"""


def cards(rs, title="▶ Match highlights", limit=20, grid=False):
    """Linha de miniaturas dos jogos (singulares) que têm resumo oficial; cada uma leva à página do jogo."""
    out = []
    for r in rs:
        if r.get("id") is None or r.get("winner") not in (1, 2):
            continue
        h = highlight_for(r)
        if h:
            out.append((r, h))
    if not out:
        return ""
    out.sort(key=lambda rh: rh[0].get("date", ""), reverse=True)
    out = out[:limit]
    def one(r, h):
        w = r["winner"]
        a, b = r["p%d" % w]["name"], r["p%d" % (3 - w)]["name"]
        sc = " ".join(f"{x}-{y}" for x, y in zip(r["games"][w - 1], r["games"][2 - w]))
        return (f'<a href="/m/{r["id"]}.html"><div class="th"><img src="https://i.ytimg.com/vi/{html.escape(h["id"])}/mqdefault.jpg" alt="" loading="lazy" width="320" height="180"><i>▶</i></div>'
                f'<div class="tx"><small>{html.escape(r.get("round") or "")} · {html.escape(r.get("date") or "")}</small><b>{html.escape(a)} <span>d.</span> {html.escape(b)}</b>'
                f'<span>{html.escape(sc)} · {html.escape(h.get("channel") or "")}</span></div></a>')
    return (CARD_CSS + (f'<h2 class="dh">{html.escape(title)} <small style="font:600 .8rem system-ui;opacity:.7">{len(out)} match{"es" if len(out) != 1 else ""} with video</small></h2>' if title else "")
            + f'<div class="thl{" grid" if grid else ""}">' + "".join(one(r, h) for r, h in out) + "</div>")


def page(results):
    """/highlights.html: todos os jogos com resumo oficial no YouTube (o mesmo que /padel/highlights.html)."""
    body = cards(results, "All match highlights", limit=120, grid=True)
    head = ('<section class="page-h"><h1>Highlights</h1><p>Official match highlights from the ATP Challenger, Tennis TV, ATP Tour and WTA '
            'channels on YouTube. Tap a match to watch it with the full score.</p></section>')
    return head + (body or '<p class="empty">No match highlights yet. They appear here as soon as the official channels publish them.</p>')


if __name__ == "__main__":
    sync()
