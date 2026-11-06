"""Volta a pôr na fila de posts jogos que já estão em results.json (ex.: depois de um erro que impediu os cartões).
Lê requeue.json (lista de ids), gera os cartões com as regras normais (sem forçar) e esvazia a lista.
O publisher depois escolhe e publica-os na janela normal, espaçados."""
import json
import os

import result_card as rc

FILE = "requeue.json"


def main():
    try:
        ids = [str(x) for x in json.load(open(FILE, encoding="utf-8"))]
    except (OSError, ValueError):
        return
    if not ids:
        return
    rows = {str(r.get("id")): r for r in rc.load_results()}
    for mid in ids:
        row = rows.get(mid)
        if not row or row.get("winner") not in (1, 2):
            print(f"Requeue {mid}: não encontrado ou sem vencedor.")
            continue
        g = row["games"]
        sets = [sum(a > b for a, b in zip(g[0], g[1])), sum(b > a for a, b in zip(g[0], g[1]))]
        pl = {k: {"name": row[k]["name"], "country": row[k].get("country"), "ranking": row[k].get("rank"), "birthday": row[k].get("bd")}
              for k in ("p1", "p2")}
        m = {"id": row["id"], "tournament": row.get("tournament", ""), "round": row.get("round", ""), "surface": row.get("surface"),
             "tour": row.get("tour"), "gender": row.get("gender"), "updated_at": row.get("date", ""), "players": pl,
             "score": {"games": g, "sets": sets}, "winner": row["winner"], "status": "finished"}
        print(f"Requeue {mid}:", rc.maybe_post(m, "out") or "não gerou cartão")
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump([], f)


if __name__ == "__main__":
    main()
