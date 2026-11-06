"""Lista pública (site/data/watch.json) dos jogos ATP/WTA do quadro principal que estão a decorrer ou começam em breve, pelo id do ESPN.
Serve ao /api/kick: quando um destes jogos acaba no ESPN, o site atualiza logo (sem esperar pela execução de hora a hora).
Só ids de jogos (dados públicos do ESPN); nada de chaves."""
import datetime as dt
import json
import os
import sys


def main(site="site"):
    try:
        d = json.load(open("espn.json", encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    now = dt.datetime.now(dt.timezone.utc)
    ids = []
    for m in d.get("matches") or []:
        if m.get("q") or m.get("state") not in ("pre", "in") or not m.get("cid"):
            continue
        try:
            t = dt.datetime.fromisoformat((m.get("t") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        if -14 <= (t - now).total_seconds() / 3600 <= 14 or m.get("state") == "in":
            ids.append(str(m["cid"]))
    os.makedirs(os.path.join(site, "data"), exist_ok=True)
    with open(os.path.join(site, "data", "watch.json"), "w", encoding="utf-8") as f:
        json.dump({"ts": int(now.timestamp()), "ids": sorted(set(ids))}, f, separators=(",", ":"))
    print(f"Watch list: {len(set(ids))} jogos ATP/WTA a vigiar.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "site")
