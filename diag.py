"""Diagnóstico: que dados trazem os endpoints gratuitos (torneios, calendário, jogador, jogo)? ~6 pedidos da quota.
Grava as chaves e um exemplo curto de cada um em diag_out.json (só dados públicos), para ser lido sem abrir os registos."""
import json
import time

import requests

import result_card as rc

OUT = {"ts": time.time(), "calls": {}}


def get(path, **params):
    try:
        r = requests.get(f"{rc.API_BASE}{path}", params=params, headers=rc._headers(), timeout=20)
        rec = {"status": r.status_code, "ratelimit": {k: v for k, v in r.headers.items() if "ratelimit" in k.lower()}}
        j = r.json() if r.headers.get("content-type", "").startswith("application/json") else None
        if r.status_code != 200:
            rec["body"] = (r.text or "")[:300]
        OUT["calls"][f"{path} {params or ''}".strip()] = rec
        return j if r.status_code == 200 else None
    except Exception as e:
        OUT["calls"][path] = {"error": type(e).__name__}
        return None


def shape(v, depth=0):
    """Estrutura: chaves com exemplo do valor (listas: só o 1.º elemento)."""
    if isinstance(v, dict):
        return {k: shape(x, depth + 1) for k, x in list(v.items())[:60]} if depth < 5 else "{...}"
    if isinstance(v, list):
        return [shape(v[0], depth + 1), f"... {len(v)} itens"] if v else []
    if isinstance(v, str):
        return v[:80]
    return v


def rows(j):
    return (j.get("data") if isinstance(j, dict) else j) or []


live = rows(get("/matches", status="live"))
OUT["match_live"] = shape(live[0]) if live else None
if live:
    OUT["match_by_id"] = shape(get(f"/matches/{live[0].get('id')}"))
    pid = ((live[0].get("players") or {}).get("p1") or {}).get("id")
    if pid:
        OUT["player_by_id"] = shape(get(f"/players/{pid}"))
fx = get("/fixtures")
OUT["fixtures"] = shape(fx)
ts = get("/tournaments")
OUT["tournaments"] = shape(ts)
tl = rows(ts)
if tl and isinstance(tl, list) and isinstance(tl[0], dict) and tl[0].get("id") is not None:
    OUT["tournament_by_id"] = shape(get(f"/tournaments/{tl[0]['id']}"))
with open("diag_out.json", "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
print(json.dumps(OUT, ensure_ascii=False)[:3000])
