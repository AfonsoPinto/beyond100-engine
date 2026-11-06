"""Beyond Padel: highlights oficiais no YouTube, sem chave nem quota: lê os feeds RSS públicos dos canais oficiais
(Premier Padel e beIN SPORTS USA, que tem os direitos e publica os resumos de cada jogo) e guarda-os em
padel/data/highlights.json (acumulado; cada feed só mostra os últimos 15 vídeos, por isso lê a cada atualização).
Só canais oficiais/licenciados: nada de canais de terceiros que voltam a publicar vídeos de outros."""
import html
import json
import os
import re
import time

import requests

DATA = os.path.join(os.path.dirname(__file__), "data")
CHANNELS = {"UCK59dYVs3Wgwoe73nDTH6jw": "Premier Padel", "UC0YatYmg5JRYzXJPxIdRd8g": "beIN SPORTS USA",
            # canais de fãs (resumos de quase todos os jogos, também FIP): só entram quando não há resumo oficial do jogo
            "UCEHUQZWBGZg6tRcnsQ6YXpQ": "Flash Padel", "UCjoBK1Z0nmC1iBIamE-5uJA": "Orbit Padel"}
OFFICIAL = {"Premier Padel", "beIN SPORTS USA"}
UA = {"User-Agent": "Mozilla/5.0 (compatible; Beyond100/0.1; +https://beyond100tennis.com)"}


def classify(title, channel=""):
    """'match' (A/B vs C/D), 'day' (resumo do dia), 'stream' (transmissão/replay) ou 'clip'."""
    t = title or ""
    if channel and channel not in OFFICIAL and re.search(r"\bvs\.?\b", t, re.I) and re.search(r"[/&]", t):
        return "match"
    if re.search(r"\bvs\.?\b", t, re.I) and "/" in t and re.search(r"highlight", t, re.I):
        return "match"
    if re.search(r"day\s*\d+.*highlights|highlights.*day\s*\d+", t, re.I):
        return "day"
    if re.search(r"replay|court|pista|centre|center", t, re.I) and not re.search(r"highlight", t, re.I):
        return "stream"
    return "clip"


def sync():
    fp = os.path.join(DATA, "highlights.json")
    try:
        db = json.load(open(fp, encoding="utf-8"))
    except (OSError, ValueError):
        db = {}
    new = 0
    for cid, cname in CHANNELS.items():
        r = None
        for attempt in range(3):                                       # os feeds do YouTube falham às vezes (404/500): tenta de novo
            try:
                r = requests.get("https://www.youtube.com/feeds/videos.xml", params={"channel_id": cid}, headers=UA, timeout=15)
                if r.status_code == 200:
                    break
                print("Padel highlights:", cname, "HTTP", r.status_code)
            except Exception as e:
                print("Padel highlights:", cname, type(e).__name__)
            time.sleep(2 + 3 * attempt)
        if r is None or r.status_code != 200:                          # plano B: o mesmo feed lido pela Cloudflare (função do site)
            try:
                site = (os.environ.get("SITE_URL") or "https://beyond100tennis.com").rstrip("/")
                r = requests.get(f"{site}/api/padel/yt/{cid}", headers=UA, timeout=20)
                print("Padel highlights:", cname, "via Cloudflare", r.status_code)
            except Exception as e:
                print("Padel highlights:", cname, "via Cloudflare falhou", type(e).__name__)
                continue
        if r is None or r.status_code != 200:
            continue
        for vid, title, pub in re.findall(r"<entry>.*?<yt:videoId>(.*?)</yt:videoId>.*?<title>(.*?)</title>.*?<published>(.*?)</published>", r.text, re.S):
            title = html.unescape(title)
            if cname == "beIN SPORTS USA" and "padel" not in title.lower():
                continue                                               # o beIN também publica futebol
            if vid not in db:
                db[vid] = {"title": title, "published": pub, "channel": cname, "kind": classify(title, cname), "official": cname in OFFICIAL}
                new += 1
    cut = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 200 * 86400))
    db = {k: v for k, v in db.items() if (v.get("published") or "") >= cut}
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=0)
    print(f"Padel highlights: {new} novos ({len(db)} guardados).")
    return new


if __name__ == "__main__":
    sync()
