"""Avisa quando o saldo da Anthropic (estimado) está a acabar.
Usa spend.json (gasto estimado por dia, escrito por captions.py) e as variáveis do GitHub:
  ANTHROPIC_CREDIT_USD  saldo em USD no dia em que carregaste (ex.: 4.99)
  ANTHROPIC_CREDIT_DATE dia a que esse saldo se refere (AAAA-MM-DD)
  ANTHROPIC_ALERT_USD   avisa quando o saldo estimado desce abaixo disto (por omissão 1.5)
Termina com código 3 (o workflow então falha de propósito, e o GitHub envia email) no máximo uma vez por dia.
"""
import datetime
import json
import os
import sys

FILE = "spend.json"


def main():
    try:
        d = json.load(open(FILE, encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    today = datetime.date.today().isoformat()
    reason = ""
    try:
        credit = float(os.environ.get("ANTHROPIC_CREDIT_USD") or "")
        since = os.environ.get("ANTHROPIC_CREDIT_DATE") or ""
        alert = float(os.environ.get("ANTHROPIC_ALERT_USD") or 1.5)
    except ValueError:
        credit, since, alert = None, "", 1.5
    if d.get("credit_error") and (not since or d["credit_error"][:10] >= since):
        reason = "a Anthropic recusou um pedido por falta de saldo"
    elif credit is not None and since:
        spent = sum(v.get("usd", 0) for k, v in (d.get("days") or {}).items() if k >= since)
        left = credit - spent
        print(f"Saldo estimado: {left:.2f} USD (gasto estimado desde {since}: {spent:.2f}).")
        if left < alert:
            reason = f"saldo estimado {left:.2f} USD (abaixo de {alert:g})"
    else:
        print("Saldo não configurado (ANTHROPIC_CREDIT_USD e ANTHROPIC_CREDIT_DATE); sem verificação.")
    if not reason:
        return 0
    if d.get("alert_notified") == today:
        print("Alerta de saldo já enviado hoje:", reason)
        return 0
    d["alert_notified"] = today
    json.dump(d, open(FILE, "w", encoding="utf-8"), indent=1)
    print("::error::Saldo da Anthropic a acabar -", reason, "- carrega fundos em https://console.anthropic.com/settings/billing")
    return 3


if __name__ == "__main__":
    sys.exit(main())
