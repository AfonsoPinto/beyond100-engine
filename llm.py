"""Fornecedor de IA para os textos (25/11/2026): Gemini (nível gratuito do Google AI Studio) quando existe GEMINI_API_KEY,
senão a Anthropic como antes. Os módulos continuam a montar o pedido no formato da Anthropic; aqui é traduzido.
Sem cartão associado ao projeto do Google, nunca há custos: se o limite gratuito acabar, o pedido falha e entra o texto sem IA.
LLM_PROVIDER=anthropic força a Anthropic."""
import datetime as dt
import json
import os
import time

import requests

LITE = lambda: os.environ.get("GEMINI_MODEL_LITE") or "gemini-flash-lite-latest"
# 26/11/2026 (teste real): o Flash principal só deixa ~20 pedidos grátis por dia; o Lite chega para tudo e escreve bem
MAIN = lambda: os.environ.get("GEMINI_MODEL") or "gemini-flash-lite-latest"
USAGE_FILE = "llm_usage.json"        # repositório de dados: pedidos do dia por modelo e por funcionalidade
PRIORITY = "high"                    # "high": textos dos posts e verificação; "low": textos de fundo (bios, traduções, descrições)
# Limite diário que nos impomos (pedidos por modelo). Os textos de fundo só usam até LOW_SHARE deste valor, para os posts
# terem sempre margem. Se o Google responder 429 (limite gratuito esgotado), o modelo fica parado até à meia-noite do Pacífico.
DAILY_CAP = int(os.environ.get("GEMINI_DAILY_CAP") or "200")
LOW_SHARE = float(os.environ.get("GEMINI_LOW_SHARE") or "0.6")


def _pt_day():
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=8)).strftime("%Y-%m-%d")     # os limites do Google reiniciam à meia-noite do Pacífico


def _usage():
    try:
        u = json.load(open(USAGE_FILE, encoding="utf-8"))
    except (OSError, ValueError):
        u = {}
    if u.get("day") != _pt_day():
        hist = (u.get("history") or {})
        if u.get("day"):
            hist[u["day"]] = {"calls": u.get("calls") or {}, "by": u.get("by") or {}, "limited": u.get("limited") or {}}
        u = {"day": _pt_day(), "calls": {}, "by": {}, "limited": {}, "history": dict(sorted(hist.items())[-30:])}
    return u


def _save(u):
    try:
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(u, f, indent=1)
    except OSError:
        pass


def allow(model, priority=None):
    """Há margem hoje para mais um pedido a este modelo, com esta prioridade?"""
    u = _usage()
    if u["limited"].get(model):
        return False
    n = u["calls"].get(model, 0)
    cap = DAILY_CAP if (priority or PRIORITY) == "high" else int(DAILY_CAP * LOW_SHARE)
    return n < cap


def remaining(priority="low", model=None):
    """Quantos pedidos ainda cabem hoje (para as tarefas de fundo decidirem quantos itens fazer)."""
    model = model or (MAIN() if priority == "high" else LITE())
    u = _usage()
    if u["limited"].get(model):
        return 0
    cap = DAILY_CAP if priority == "high" else int(DAILY_CAP * LOW_SHARE)
    return max(0, cap - u["calls"].get(model, 0))

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def provider():
    if os.environ.get("LLM_PROVIDER", "").strip().lower() == "anthropic" and os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else None


def key():
    """Algo verdadeiro quando há IA disponível (os módulos usam isto como 'há chave?')."""
    p = provider()
    return os.environ.get("ANTHROPIC_API_KEY") if p == "anthropic" else ("gemini" if p == "gemini" else None)


class _Resp:
    """Resposta com a mesma forma que requests.Response e o mesmo JSON que a Anthropic devolve."""

    def __init__(self, status, data=None, text=""):
        self.status_code, self._data, self.text = status, data or {}, text or json.dumps(data or {})

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}: {self.text[:200]}", response=self)


def _parts(content):
    if isinstance(content, str):
        return [{"text": content}]
    out = []
    for b in content or []:
        if isinstance(b, dict) and b.get("type") == "text":
            out.append({"text": b.get("text", "")})
        elif isinstance(b, str):
            out.append({"text": b})
    return out or [{"text": ""}]


def _gemini(payload, timeout):
    """Tenta o modelo principal; se o Google estiver sobrecarregado (500/503) ou demorar demais, tenta de novo e depois o modelo Lite."""
    m = payload.get("model") or ""
    first = LITE() if "haiku" in m else MAIN()
    tries = [first, first] + ([LITE()] if first != LITE() else [])
    r = None
    for k, model in enumerate(tries):
        r = _gemini_once(payload, timeout, model)
        if r.status_code not in (429, 500, 502, 503, 504, 599):
            return r
        time.sleep(4 + 4 * k if r.status_code != 429 else 20)    # 429 por minuto: espera um pouco e tenta (o Lite tem limites próprios)
    return r


def _gemini_once(payload, timeout, model):
    body = {"contents": [{"role": "model" if x.get("role") == "assistant" else "user", "parts": _parts(x.get("content"))}
                         for x in payload.get("messages") or []],
            "generationConfig": {"maxOutputTokens": max(2048, int(payload.get("max_tokens") or 1000) * 3)}}
    if payload.get("system"):
        body["systemInstruction"] = {"parts": [{"text": payload["system"]}]}
    web = any(isinstance(t, dict) and "web_search" in str(t.get("type", "")) for t in payload.get("tools") or [])
    if web:
        # 26/11/2026 (teste real): a pesquisa Google não está incluída no nível gratuito (429 "exceeded your current quota").
        # Sem pesquisa não há factos verificados: estes pedidos (contexto web, frente a frente, notícias) ficam sem IA.
        if os.environ.get("GEMINI_SEARCH", "0") != "1":
            return _Resp(501, text="Gemini: pesquisa web não incluída no nível gratuito")
        body["tools"] = [{"google_search": {}}]
    import sys
    feature = payload.get("_feature") or getattr(sys.modules.get("captions"), "FEATURE", None) or "other"
    if not allow(model):
        return _Resp(429, text=f"Gemini: limite diário que definimos atingido para {model} ({PRIORITY})")
    u = _usage()
    u["calls"][model] = u["calls"].get(model, 0) + 1
    u["by"][feature] = u["by"].get(feature, 0) + 1
    _save(u)
    try:
        r = requests.post(GEMINI_URL.format(model=model), headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "content-type": "application/json"},
                          json=body, timeout=timeout)
    except requests.RequestException as e:
        return _Resp(599, text=f"Gemini: {type(e).__name__}")
    if r.status_code == 429:                       # limite gratuito do Google esgotado: para este modelo até amanhã (hora do Pacífico)
        txt = (r.text or "")
        if "PerDay" in txt or "per day" in txt.lower():   # só o limite DIÁRIO pára o modelo até amanhã (o por minuto passa sozinho)
            u = _usage()
            u["limited"][model] = time.strftime("%H:%M", time.gmtime())
            _save(u)
            print(f"Gemini: limite gratuito de {model} esgotado hoje; textos sem IA até amanhã.")
    if r.status_code >= 400:
        return _Resp(r.status_code, text="Gemini: " + (r.text or "")[:300])
    j = r.json()
    cand = (j.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in (cand.get("content") or {}).get("parts") or [] if not p.get("thought"))
    u = j.get("usageMetadata") or {}
    searches = len(((cand.get("groundingMetadata") or {}).get("webSearchQueries")) or []) if web else 0
    return _Resp(200, {"model": "gemini:" + model, "content": [{"type": "text", "text": text}],
                       "stop_reason": cand.get("finishReason"),
                       "usage": {"input_tokens": u.get("promptTokenCount", 0), "output_tokens": u.get("candidatesTokenCount", 0),
                                 "server_tool_use": {"web_search_requests": searches}}})


def post(url, headers=None, json=None, timeout=60, **kw):
    """Substitui requests.post(API_URL, ...) da Anthropic."""
    if provider() == "gemini":
        return _gemini(json or {}, timeout)
    return requests.post(url, headers=headers, json=json, timeout=timeout, **kw)
