"""Pesquisa única (25/11/2026): vídeos de ténis no YouTube com licença Creative Commons (CC BY), de 2026,
e se o canal parece ser do próprio jogador ou torneio. Só lê metadados (títulos, canais); não descarrega nada.
Custo: ~100 unidades da quota do YouTube por pesquisa (quota diária 10.000). Resultado em yt_cc.json (repositório privado)."""
import json
import os
import re
import time
import unicodedata

import requests

KEY = os.environ.get("YT_API_KEY")
API = "https://www.googleapis.com/youtube/v3/"
QUERIES = ["tennis challenger highlights", "atp challenger match", "itf tennis match", "itf world tennis tour",
           "wta 125 highlights", "tennis match highlights 2026", "tennis full match 2026", "challenger tennis 2026",
           "tennis tournament highlights", "padel highlights"]
MAX_SEARCHES = 20


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", t)


def get(path, **p):
    r = requests.get(API + path, params=dict(p, key=KEY), timeout=30)
    r.raise_for_status()
    return r.json()


def main():
    if not KEY:
        print("Sem YT_API_KEY.")
        return
    names = []
    try:
        er = json.load(open("espn_rank.json", encoding="utf-8"))
        names = [x["n"] for lg in ("atp", "wta") for x in (er.get(lg) or []) if 60 <= x.get("r", 0) <= 150]
    except (OSError, ValueError):
        pass
    queries = QUERIES + [f"{n} tennis" for n in names[:MAX_SEARCHES - len(QUERIES)]]
    found, n = {}, 0
    for q in queries[:MAX_SEARCHES]:
        try:
            j = get("search", part="snippet", q=q, type="video", videoLicense="creativeCommon",
                    publishedAfter="2026-01-01T00:00:00Z", maxResults=25, order="date")
        except Exception as e:
            print("Pesquisa falhou:", q, type(e).__name__)
            continue
        n += 1
        for it in j.get("items", []):
            vid = it["id"]["videoId"]
            s = it["snippet"]
            found.setdefault(vid, {"id": vid, "title": s["title"], "channel": s["channelTitle"], "channel_id": s["channelId"],
                                   "published": s["publishedAt"][:10], "query": q})
        time.sleep(0.2)
    # detalhes: duração e se é mesmo CC BY
    ids = list(found)
    for i in range(0, len(ids), 50):
        try:
            j = get("videos", part="status,contentDetails,statistics", id=",".join(ids[i:i + 50]))
        except Exception:
            continue
        for v in j.get("items", []):
            f = found[v["id"]]
            f["license"] = v["status"].get("license")
            f["duration"] = v["contentDetails"].get("duration")
            f["views"] = int(v.get("statistics", {}).get("viewCount", 0) or 0)
    # canal do próprio jogador/torneio? (nome do canal contém o apelido de um jogador do título, ou "tennis"/"open"/"club")
    nn = [norm(x) for x in names]
    for f in found.values():
        t, c = norm(f["title"]), norm(f["channel"])
        player_in_title = [x for x in nn if x and x in t]
        f["tennis"] = any(w in t for w in ("tennis", "challenger", "atp", "wta", "itf", "padel"))
        f["own_channel_guess"] = bool(any(p.split()[-1] in c for p in player_in_title)
                                      or re.search(r"\b(open|club|tennis academy|federation|federacao|federacion|tournament|cup)\b", c))
        f["broadcast_guess"] = bool(re.search(r"\b(highlights|full match|tennis tv|atp|wta)\b", t)) and not f["own_channel_guess"]
    out = {"ts": time.time(), "searches": n, "videos": sorted(found.values(), key=lambda f: (not f["own_channel_guess"], not f["tennis"], -f.get("views", 0)))}
    with open("yt_cc.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    tot = len(found)
    ten = sum(1 for f in found.values() if f["tennis"])
    own = sum(1 for f in found.values() if f["tennis"] and f["own_channel_guess"])
    print(f"YouTube CC BY: {n} pesquisas, {tot} vídeos, {ten} de ténis/padel, {own} de canais que parecem próprios (lista em yt_cc.json, privado).")


if __name__ == "__main__":
    main()
