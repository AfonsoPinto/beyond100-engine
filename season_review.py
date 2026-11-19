"""Season in review 2026 (série de dezembro, aprovada pelo Afonso a 19/11/2026). Dados: ESPN (finais ATP e WTA de 2026),
guardados só no repositório privado. Sem IA.

  python season_review.py titles out.png      cartão "Most titles in 2026" (ATP e WTA)"""
import collections
import datetime as dt
import json
import os
import sys
import urllib.request

SB = "https://site.api.espn.com/apis/site/v2/sports/tennis/{lg}/scoreboard?dates={a}-{b}"
CACHE = "season_2026.json"


def _get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=40) as r:
        return json.load(r)


def finals(year=2026):
    """Finais de singulares de cada torneio do ano: [{lg, event, date, w:{n,c}, l:{n,c}}] (sem repetidos)."""
    if os.path.exists(CACHE):
        d = json.load(open(CACHE, encoding="utf-8"))
        if d.get("year") == year and time_ok(d.get("at")):
            return d["finals"]
    out, seen = [], set()
    for lg in ("atp", "wta"):
        for m in range(1, 13):
            a = dt.date(year, m, 1)
            b = (dt.date(year + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
            try:
                d = _get(SB.format(lg=lg, a=a.strftime("%Y%m%d"), b=b.strftime("%Y%m%d")))
            except Exception as e:
                print("ESPN", lg, m, type(e).__name__); continue
            for e in d.get("events") or []:
                for g in e.get("groupings") or []:
                    gn = ((g.get("grouping") or {}).get("displayName") or "").lower()
                    if "singles" not in gn:
                        continue
                    for c in g.get("competitions") or []:
                        if ((c.get("round") or {}).get("displayName") or "").lower() != "final" or c.get("id") in seen:
                            continue
                        if not ((c.get("status") or {}).get("type") or {}).get("completed"):
                            continue
                        comp = c.get("competitors") or []
                        win = [x for x in comp if x.get("winner")]
                        los = [x for x in comp if not x.get("winner")]
                        if not win or not los:
                            continue
                        ath = lambda x: {"n": (x.get("athlete") or {}).get("displayName"), "c": ((x.get("athlete") or {}).get("flag") or {}).get("alt")}
                        seen.add(c.get("id"))
                        out.append({"lg": lg, "event": e.get("name"), "date": (c.get("date") or "")[:10], "w": ath(win[0]), "l": ath(los[0])})
    json.dump({"year": year, "at": dt.datetime.utcnow().isoformat(), "finals": out}, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return out


def time_ok(at):
    try:
        return (dt.datetime.utcnow() - dt.datetime.fromisoformat(at)).days < 1
    except (TypeError, ValueError):
        return False


def titles_card(out):
    import features
    import modern_cards
    fs = finals()
    secs, crs = [], []
    for lg in ("atp", "wta"):
        c = collections.Counter(f["w"]["n"] for f in fs if f["lg"] == lg and f["w"]["n"])
        top = c.most_common(4)
        if not top:
            continue
        name, n = top[0]
        evs = [f["event"] for f in fs if f["lg"] == lg and f["w"]["n"] == name]
        fp, cr = features._hero_photo(name)
        crs.append(cr)
        secs.append({"label": lg.upper(), "hero": {"name": name, "big": f"{n} titles", "move": 0, "sub": ", ".join(e.split(" ")[0] for e in evs[:4]), "photo": fp},
                     "rows": [(str(k), nm, f"{k} title{'s' if k > 1 else ''}") for nm, k in top[1:4]]})
        print(lg, "títulos:", len([f for f in fs if f["lg"] == lg]), "finais;", len(c), "campeões diferentes")
    return modern_cards.card_list({"sport": "tennis", "kicker": "2026 IN REVIEW", "date": "SEASON 2026", "title": "Most titles",
                                   "sub": "ATP and WTA tour-level singles titles this season", "sections": secs, "credits": crs}, out)


if __name__ == "__main__":
    {"titles": titles_card}[sys.argv[1]](sys.argv[2])
