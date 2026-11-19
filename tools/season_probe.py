"""Sondagem (só contagens, sem dados nos registos): o ESPN dá a época inteira de 2026 (torneios, finais, rankings antigos)?"""
import json, urllib.request
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
            return json.load(r)
    except Exception as e:
        return {"_err": type(e).__name__}
for lg in ("atp", "wta"):
    tot_ev, fin = 0, 0
    for m in range(1, 12):
        d = get(f"https://site.api.espn.com/apis/site/v2/sports/tennis/{lg}/scoreboard?dates=2026{m:02d}01-2026{m:02d}28")
        evs = d.get("events") or []
        tot_ev += len(evs)
        for e in evs:
            for g in e.get("groupings") or []:
                for c in g.get("competitions") or []:
                    rd = ((c.get("round") or {}).get("displayName") or "").lower()
                    if rd == "final" and "singles" in ((g.get("grouping") or {}).get("displayName") or "").lower():
                        fin += 1
        print(lg, m, "eventos:", len(evs), "err:", d.get("_err"))
    print(lg, "TOTAL eventos", tot_ev, "finais de singulares", fin)
    r = get(f"https://site.api.espn.com/apis/site/v2/sports/tennis/{lg}/rankings?dates=20260105")
    rr = (r.get("rankings") or [{}])[0]
    print(lg, "ranking com data antiga:", bool(rr.get("ranks")), "n=", len(rr.get("ranks") or []), "data devolvida:", (rr.get("date") or rr.get("update") or "")[:10])
