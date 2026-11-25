"""Fornecedor de IA para os textos (25/11/2026): Gemini (nível gratuito do Google AI Studio) quando existe GEMINI_API_KEY,
senão a Anthropic como antes. Os módulos continuam a montar o pedido no formato da Anthropic; aqui é traduzido.
Sem cartão associado ao projeto do Google, nunca há custos: se o limite gratuito acabar, o pedido falha e entra o texto sem IA.
LLM_PROVIDER=anthropic força a Anthropic."""
import json
import os

import requests

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
    m = payload.get("model") or ""
    model = (os.environ.get("GEMINI_MODEL_LITE") or "gemini-flash-lite-latest") if "haiku" in m else (os.environ.get("GEMINI_MODEL") or "gemini-flash-latest")
    body = {"contents": [{"role": "model" if x.get("role") == "assistant" else "user", "parts": _parts(x.get("content"))}
                         for x in payload.get("messages") or []],
            "generationConfig": {"maxOutputTokens": max(2048, int(payload.get("max_tokens") or 1000) * 3)}}
    if payload.get("system"):
        body["systemInstruction"] = {"parts": [{"text": payload["system"]}]}
    web = any(isinstance(t, dict) and "web_search" in str(t.get("type", "")) for t in payload.get("tools") or [])
    if web:
        body["tools"] = [{"google_search": {}}]
    try:
        r = requests.post(GEMINI_URL.format(model=model), headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "content-type": "application/json"},
                          json=body, timeout=timeout)
    except requests.RequestException as e:
        return _Resp(599, text=f"Gemini: {type(e).__name__}")
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
