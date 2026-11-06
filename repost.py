"""Refaz o post de um jogo já guardado (ex.: depois de corrigir a foto).
    python repost.py 209656
Remove o jogo da lista de publicados, volta a gerar o cartão (com a foto e menções atuais) e põe-no na fila.
O resto (preparar e enviar) é feito pelo mesmo workflow."""
import json
import os
import sys

import result_card as rc


def main(mid):
    row = next((r for r in rc.load_results() if str(r.get("id")) == str(mid)), None)
    if not row:
        sys.exit(f"Jogo {mid} não encontrado em results.json")
    w = row.get("winner")
    if w not in (1, 2):
        sys.exit("Jogo sem vencedor")
    g = row["games"]
    sets = [sum(a > b for a, b in zip(g[0], g[1])), sum(b > a for a, b in zip(g[0], g[1]))]
    pl = {}
    for k in ("p1", "p2"):
        p = row[k]
        pl[k] = {"name": p["name"], "country": p.get("country"), "ranking": p.get("rank"), "birthday": p.get("bd")}
    m = {"id": row["id"], "tournament": row.get("tournament", ""), "round": row.get("round", ""),
         "surface": row.get("surface"), "tour": row.get("tour"), "gender": row.get("gender"),
         "updated_at": row.get("date", ""), "players": pl,
         "score": {"games": g, "sets": sets}, "winner": w, "status": "finished"}
    posts = rc._load_json(rc.POSTS_FILE, {})
    for day in posts:
        posts[day] = [e for e in posts[day] if str(e.get("id")) != str(mid)]
    with open(rc.POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    out = rc.maybe_post(m, "out", force=True)
    print("Post refeito:", out or "NÃO foi gerado (ver mensagens acima; provavelmente sem foto livre do vencedor)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("uso: python repost.py <id do jogo>")
    main(sys.argv[1])
