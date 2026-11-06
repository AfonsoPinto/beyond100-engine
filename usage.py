"""Consumo da quota da Live Tennis API (o pedido /usage não gasta quota). Guarda só números em usage.json para o admin."""
import json
import time

import requests

import result_card as rc


def _nums(v, prefix="", out=None):
    out = {} if out is None else out
    if isinstance(v, dict):
        for k, x in v.items():
            _nums(x, f"{prefix}{k}.", out)
    elif isinstance(v, (int, float)) and not isinstance(v, bool):
        out[prefix[:-1]] = v
    elif isinstance(v, str) and len(v) <= 40 and any(w in prefix.lower() for w in ("tier", "plan", "reset", "period")):
        out[prefix[:-1]] = v
    return out


USAGE_EVERY_H = float(__import__("os").environ.get("USAGE_EVERY_H") or "6")


def main():
    # o /usage conta para a quota (ao contrário do que diz a documentação): consultar só de USAGE_EVERY_H em USAGE_EVERY_H horas
    try:
        last = json.load(open("usage.json", encoding="utf-8")).get("ts", 0)
    except (OSError, ValueError):
        last = 0
    if time.time() - last < USAGE_EVERY_H * 3600:
        print("Quota da API: consultada há pouco, salto (cada consulta conta como pedido).")
        return
    try:                                     # perto do limite: não gastar um pedido só para ver a quota
        if rc.quota_used() >= rc.API_DAILY_LIMIT - rc.LIVE_RESERVE - 4:
            print("Quota da API: perto do limite, não consulto.")
            return
    except Exception:
        pass
    rec = {"ts": time.time()}
    try:
        r = requests.get(f"{rc.API_BASE}/usage", headers=rc._headers(), timeout=20)
        rec["status"] = r.status_code
        if r.ok:
            rec["fields"] = _nums(r.json())
        hd = {k.lower(): v for k, v in r.headers.items() if "ratelimit" in k.lower()}
        if hd:
            rec["headers"] = hd
    except Exception as e:
        rec["error"] = type(e).__name__
    # histórico (para descobrir a que horas a quota renova: a API usa a meia-noite do fuso da conta, não a UTC)
    try:
        prev = json.load(open("usage.json", encoding="utf-8"))
    except (OSError, ValueError):
        prev = {}
    hist = prev.get("hist") or []
    calls = (rec.get("fields") or {}).get("today.calls")
    if isinstance(calls, (int, float)):
        if hist and calls < hist[-1][1]:                # a contagem desceu: a quota renovou entre as duas leituras
            rec["reset_seen"] = [hist[-1][0], rec["ts"]]
        hist.append([rec["ts"], calls])
    rec["hist"] = hist[-96:]
    if "reset_seen" not in rec and prev.get("reset_seen"):
        rec["reset_seen"] = prev["reset_seen"]
    with open("usage.json", "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
    print("Quota da API:", json.dumps(rec, ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
