"""Auditoria: lista jogos guardados que podem ser de qualificação mas aparecem como quadro principal.
    python audit.py                 # só mostra o relatório
    python audit.py --apply 1,2,3   # acrescenta estes ids a qualifying_ids.json
Critério: ronda de quadro principal (final, meias, quartos) sem nenhum jogo anterior do mesmo torneio numa ronda mais cedo,
ou várias 'finais' singulares no mesmo torneio/dia. Falta de dados NÃO prova que seja qualificação: confirma antes de aplicar."""
import json
import os
import sys

import result_card as rc
import webapp


def main():
    rs = [r for r in rc.load_results() if webapp.classify(r)[1] == "singles"]
    by_t = {}
    for r in rs:
        by_t.setdefault((r.get("tournament"), r.get("gender")), []).append(r)
    sus = []
    for (t, g), rows in by_t.items():
        for r in rows:
            if r.get("q"):
                continue
            rk = webapp._round_rank(r.get("round"))
            if rk > 2:
                continue
            earlier = [x for x in rows if x is not r and x.get("date", "") < r.get("date", "") and not x.get("q")
                       and webapp._round_rank(x.get("round")) > rk]
            same_day_finals = [x for x in rows if x is not r and rk == 0 and webapp._round_rank(x.get("round")) == 0
                               and x.get("date") == r.get("date")]
            why = []
            if not earlier:
                why.append("sem jogos anteriores do torneio")
            if same_day_finals:
                why.append(f"{len(same_day_finals) + 1} finais no mesmo dia")
            if why:
                sus.append((r, "; ".join(why)))
    sus.sort(key=lambda x: (x[0].get("tournament") or "", x[0].get("date") or ""))
    print(f"Jogos singulares guardados: {len(rs)}. Suspeitos: {len(sus)}")
    print("id | data | torneio | ronda | jogo | marcador | motivo")
    for r, why in sus:
        sc = " ".join(f"{a}-{b}" for a, b in zip(r["games"][0], r["games"][1]))
        print(f'{r.get("id")} | {r.get("date")} | {r.get("tournament")} | {r.get("round")} | '
              f'{r["p1"]["name"]} v {r["p2"]["name"]} | {sc} | {why}')
    if "--apply" in sys.argv:
        ids = [int(x) for x in sys.argv[sys.argv.index("--apply") + 1].split(",") if x.strip().isdigit()]
        cur = rc._load_json("qualifying_ids.json", [])
        cur = [i for i in cur if not isinstance(i, str) or not i.startswith("_")]
        new = sorted(set(cur) | set(ids))
        with open("qualifying_ids.json", "w", encoding="utf-8") as f:
            json.dump(new, f)
        print("qualifying_ids.json:", new)


if __name__ == "__main__":
    main()
