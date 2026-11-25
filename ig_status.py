"""Estado da publicação no Instagram (25/11/2026). A Make publica e, com um módulo "Webhook response" no fim de cada caminho,
responde ao motor com {"ok": true, "ig_id": "..."} ou, no tratamento de erros, {"ok": false, "error": "..."}.
Sem esse módulo a Make só responde "Accepted" e o resultado fica "desconhecido" (como antes).
Guarda ig_status.json (repositório de dados): último sucesso e último erro por conta; o admin mostra-o e a Guarda avisa por email."""
import json
import time

FILE = "ig_status.json"


def parse(resp):
    """(ok, mensagem): ok True/False quando a Make responde em JSON; None quando só diz 'Accepted'."""
    try:
        j = resp.json()
    except Exception:
        return None, (getattr(resp, "text", "") or "")[:120]
    if isinstance(j, dict) and "ok" in j:
        ok = j.get("ok") in (True, "true", "1", 1)
        return ok, str(j.get("error") or j.get("ig_id") or "")[:300]
    return None, ""


def record(account, pid, ok, msg=""):
    try:
        d = json.load(open(FILE, encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    a = d.setdefault(account, {})
    now = time.time()
    if ok is True:
        a["last_ok"] = {"ts": now, "id": str(pid)}
        a["fails_in_row"] = 0
    elif ok is False:
        a["last_error"] = {"ts": now, "id": str(pid), "msg": msg}
        a["fails_in_row"] = int(a.get("fails_in_row") or 0) + 1
    else:
        a["last_sent_unconfirmed"] = {"ts": now, "id": str(pid)}
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
