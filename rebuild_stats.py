"""Recalcula as estatísticas acumuladas (stats.json) sem os jogos de qualificação e grava as correções no arquivo e nos resultados.
    python rebuild_stats.py"""
import json
import os

import extras
import result_card as rc


def main():
    arc = []
    if os.path.exists(rc.ARCHIVE_FILE):
        arc = json.load(open(rc.ARCHIVE_FILE, encoding="utf-8"))
    cur = rc.load_results()
    byid = {str(r.get("id")): r for r in arc}
    for r in cur:
        byid[str(r.get("id"))] = r
    rows = rc._heal(sorted(byid.values(), key=lambda r: r.get("date", "")))
    nq = sum(1 for r in rows if r.get("q"))
    with open(rc.ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, separators=(",", ":"))
    keep = {str(r["id"]) for r in cur}
    with open(rc.RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted([r for r in rows if str(r.get("id")) in keep], key=lambda r: r.get("date", ""), reverse=True),
                  f, ensure_ascii=False, indent=2)
    since = min([r.get("date", "") for r in rows if r.get("date")] or [""])
    if os.path.exists(extras.STATS_FILE):
        os.remove(extras.STATS_FILE)
    for r in rows:
        extras.update_stats(r)
    if since and os.path.exists(extras.STATS_FILE):
        d = json.load(open(extras.STATS_FILE, encoding="utf-8"))
        d["since"] = since
        json.dump(d, open(extras.STATS_FILE, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"Jogos no arquivo: {len(rows)}; qualificação: {nq}; estatísticas recalculadas desde {since}.")


if __name__ == "__main__":
    main()
