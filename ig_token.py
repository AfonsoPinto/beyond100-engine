"""Token do Instagram (API com login do Instagram): verificar e renovar.

  python ig_token.py check     -> confirma que o token funciona (mostra o @ da conta, nunca o token)
  python ig_token.py refresh   -> renova o token (mais 60 dias). Se a Meta devolver um token diferente, grava-o no segredo
                                  IG_ACCESS_TOKEN do GitHub (precisa do segredo GH_SECRETS_TOKEN: token fino com 'Secrets: Read and write').
Variáveis: IG_ACCESS_TOKEN, GRAPH_HOST (por omissão graph.instagram.com), GH_SECRETS_TOKEN, GITHUB_REPOSITORY.
"""
import base64
import os
import sys

import requests

HOST = (os.environ.get("GRAPH_HOST") or "graph.instagram.com").strip()
TOK = (os.environ.get("IG_ACCESS_TOKEN") or "").strip()


def check():
    r = requests.get(f"https://{HOST}/me", params={"fields": "user_id,username", "access_token": TOK}, timeout=30)
    if r.status_code != 200:
        print("::error::O token do Instagram não funciona:", r.status_code, r.text[:300].replace("\n", " "))
        return 1
    j = r.json()
    print(f"Token OK: @{j.get('username')} (id {j.get('user_id') or j.get('id')}).")
    return 0


def put_secret(name, value):
    from nacl import encoding, public
    repo, gh = os.environ["GITHUB_REPOSITORY"], os.environ["GH_SECRETS_TOKEN"]
    h = {"Authorization": f"Bearer {gh}", "Accept": "application/vnd.github+json"}
    k = requests.get(f"https://api.github.com/repos/{repo}/actions/secrets/public-key", headers=h, timeout=30)
    k.raise_for_status()
    k = k.json()
    box = public.SealedBox(public.PublicKey(k["key"].encode(), encoding.Base64Encoder()))
    enc = base64.b64encode(box.encrypt(value.encode())).decode()
    r = requests.put(f"https://api.github.com/repos/{repo}/actions/secrets/{name}", headers=h,
                     json={"encrypted_value": enc, "key_id": k["key_id"]}, timeout=30)
    r.raise_for_status()


def refresh():
    r = requests.get(f"https://{HOST}/refresh_access_token", params={"grant_type": "ig_refresh_token", "access_token": TOK}, timeout=30)
    if r.status_code != 200:
        msg = r.text[:300].replace("\n", " ")
        if "24 hours" in msg or "too soon" in msg.lower():
            print("Token renovado há menos de 24 h; nada a fazer.")
            return 0
        print("::error::Não consegui renovar o token do Instagram:", r.status_code, msg)
        return 1
    j = r.json()
    new = j.get("access_token") or ""
    days = int(j.get("expires_in", 0)) // 86400
    print(f"Token renovado: válido por mais {days} dias.")
    if new and new != TOK:
        print(f"::add-mask::{new}")
        if not os.environ.get("GH_SECRETS_TOKEN"):
            print("::error::A Meta devolveu um token novo, mas falta o segredo GH_SECRETS_TOKEN para o gravar no GitHub. Gera outro token em Generate token e atualiza IG_ACCESS_TOKEN à mão.")
            return 1
        put_secret("IG_ACCESS_TOKEN", new)
        print("Segredo IG_ACCESS_TOKEN atualizado.")
    return 0


if __name__ == "__main__":
    if not TOK:                      # a publicação vai pelo Make (PUBLISH_BACKEND=webhook): sem token próprio, não há nada a renovar
        print("IG_ACCESS_TOKEN não está definido: a publicação usa o Make, nada a renovar.")
        sys.exit(0)
    sys.exit({"check": check, "refresh": refresh}.get(sys.argv[1] if len(sys.argv) > 1 else "check", check)())
