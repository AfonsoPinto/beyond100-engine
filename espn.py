"""Resultados ATP/WTA (incl. WTA 125) a partir do scoreboard público do ESPN: grátis, sem chave, sem quota.
Serve para confirmar jogos do circuito principal sem gastar pedidos da Live Tennis API (que fica para Challenger/ITF).
Não é uma API oficial: se falhar ou não encontrar o jogo, quem chama volta ao método antigo (a API paga)."""
import datetime as dt
import re
import time
import unicodedata

URL = "https://site.api.espn.com/apis/site/v2/sports/tennis/{lg}/scoreboard"
_cache = {}


def norm(s):
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower())


def _keys(name):
    """Chaves para comparar nomes: nome completo, e 'inicial + apelido' (o ESPN e a API às vezes diferem nos nomes do meio)."""
    w = [norm(x) for x in re.split(r"[\s\-]+", name or "") if norm(x)]
    if not w:
        return set()
    k = {"".join(w), w[0][0] + w[-1], w[-1] + w[0][0]}
    if len(w) > 1:                       # a mesma pessoa com os nomes por outra ordem ("Wang Xinyu" / "Xinyu Wang", 7/11/2026)
        k.add("~" + "".join(sorted(w)))
    return k


def _day(lg, d):
    k = (lg, d)
    if k in _cache:
        return _cache[k]
    import requests
    rows = []
    try:
        r = requests.get(URL.format(lg=lg), params={"dates": d}, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        for ev in r.json().get("events") or []:
            for g in ev.get("groupings") or [{"competitions": ev.get("competitions") or []}]:
                gname = ((g.get("grouping") or {}).get("displayName") or "").lower()
                if "doubles" in gname:
                    continue
                for c in g.get("competitions") or []:
                    comp = c.get("competitors") or []
                    if len(comp) != 2:
                        continue
                    nm = [(x.get("athlete") or {}).get("displayName") or "" for x in comp]
                    if not all(nm):
                        continue
                    st = (c.get("status") or {}).get("type") or {}
                    rows.append({"t": ev.get("name"), "p": nm, "state": st.get("state"), "status": st.get("name"),
                                 "done": bool(st.get("completed")),
                                 "sets": [[int(float(ls.get("value") or 0)) for ls in (x.get("linescores") or [])] for x in comp],
                                 "tb": [[ls.get("tiebreak") for ls in (x.get("linescores") or [])] for x in comp],
                                 "winner": [bool(x.get("winner")) for x in comp]})
    except Exception as e:
        print(f"ESPN {lg} {d}: indisponível ({type(e).__name__}).")
        rows = None
    _cache[k] = rows
    return rows


def _days():
    t = dt.datetime.utcnow()
    return [(t - dt.timedelta(days=i)).strftime("%Y%m%d") for i in (0, 1)]


def lookup(p1, p2, leagues=("atp", "wta")):
    """Procura o jogo p1 vs p2. Devolve None (ESPN em baixo / jogo não encontrado) ou
    {"done": bool, "games": [[..p1..], [..p2..]], "winner": 1|2|0, "clean": bool, "status": str}.
    'clean' = acabou normalmente (sets coerentes com o vencedor); desistências e w.o. ficam para a API."""
    k1, k2 = _keys(p1), _keys(p2)
    if not k1 or not k2:
        return None
    for lg in leagues:
        for d in _days():
            rows = _day(lg, d)
            for m in rows or []:
                a, b = _keys(m["p"][0]), _keys(m["p"][1])
                if (k1 & a and k2 & b):
                    flip = False
                elif (k1 & b and k2 & a):
                    flip = True
                else:
                    continue
                ga, gb = m["sets"]
                ta, tb_ = m.get("tb") or [[], []]
                wa, wb = m["winner"]
                if flip:
                    ga, gb, wa, wb, ta, tb_ = gb, ga, wb, wa, tb_, ta
                won = [sum(1 for x, y in zip(ga, gb) if x > y), sum(1 for x, y in zip(ga, gb) if y > x)]
                win = 1 if wa else 2 if wb else 0
                need = 3 if len(ga) > 3 or max(won) == 3 else 2
                clean = (m["done"] and m["status"] == "STATUS_FINAL" and win in (1, 2) and len(ga) == len(gb) > 0
                         and won[win - 1] == need and won[2 - win] < need)
                return {"done": m["done"], "games": [ga, gb], "winner": win, "clean": clean, "status": m["status"],
                        "tb": [ta, tb_] if any(v is not None for v in ta + tb_) else None,
                        "t": m["t"], "lg": lg}
    return None


def as_completed(meta, hit):
    """Reconstrói o jogo no formato da Live Tennis API (o resto do código não muda) a partir do retrato guardado + resultado do ESPN."""
    m = dict(meta)
    ga, gb = hit["games"]
    won = [sum(1 for x, y in zip(ga, gb) if x > y), sum(1 for x, y in zip(ga, gb) if y > x)]
    m["status"] = "completed"
    m["score"] = {"games": [ga, gb], "sets": won}
    m["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    m["source"] = "espn"
    return m
