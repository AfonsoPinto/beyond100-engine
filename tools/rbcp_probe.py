"""Sondagem técnica (sem login, sem descarregar fotos): como o site do Red Bull Content Pool faz login e pesquisa.
Só imprime nomes de endpoints e o tipo de autenticação encontrados no código público do site."""
import re, requests
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
s = requests.Session(); s.headers.update(UA)
for u in ("https://www.redbullcontentpool.com/", "https://www.redbullcontentpool.com/robots.txt"):
    r = s.get(u, timeout=30); print("==", u, r.status_code, r.headers.get("content-type"), len(r.text))
    if u.endswith("robots.txt"): print(r.text[:1500])
    else:
        html = r.text
        print("title:", (re.findall(r"<title>(.*?)</title>", html) or [""])[0][:100])
        scripts = re.findall(r'<script[^>]+src="([^"]+)"', html)
        print("scripts:", scripts[:30])
        print("next/nuxt:", "__NEXT_DATA__" in html, "__NUXT__" in html)
        for m in sorted(set(re.findall(r'https?://[a-z0-9.-]+\.(?:redbull|rbmh|auth0|okta|redbullmediahouse|cloudfront|amazonaws)[a-z0-9./-]*', html)))[:40]: print("  url:", m)
seen = set(); pats = re.compile(r'(?:"|\')((?:https?:)?//[a-z0-9.-]+[a-z0-9./_-]*(?:api|graphql|auth|login|oauth|token|search|asset|download)[a-z0-9./_?=&-]*)(?:"|\')', re.I)
pats2 = re.compile(r'(?:"|\')(/(?:api|graphql|v\d)[a-z0-9./_-]*)(?:"|\')', re.I)
for src in scripts[:40]:
    u = src if src.startswith("http") else "https://www.redbullcontentpool.com/" + src.lstrip("/")
    try: js = s.get(u, timeout=30).text
    except Exception as e: print("js falhou", u, e); continue
    hits = set(pats.findall(js)) | set(pats2.findall(js))
    kw = [k for k in ("auth0", "okta", "cognito", "keycloak", "oidc", "openid", "client_id", "clientId", "recaptcha", "hcaptcha", "turnstile", "graphql", "Bearer", "x-api-key") if k in js]
    if hits or kw:
        print("--", u.split("/")[-1][:60], "| auth:", kw)
        for h in sorted(hits)[:40]:
            if h not in seen: seen.add(h); print("    ", h[:140])
print("== detalhe do main.js")
js = s.get("https://www.redbullcontentpool.com/" + [x for x in scripts if x.startswith("main")][0], timeout=30).text
for k in ("apiUrl", "apiBase", "baseUrl", "baseURL", "apiEndpoint", "clientId", "authority", "issuer", "redirectUri", "Bearer", "/oauth", "login", "/search", "download"):
    for m in list(re.finditer(re.escape(k), js))[:3]:
        print(f"[{k}]", js[max(0, m.start() - 120): m.end() + 160].replace("\n", " "))
doms = sorted(set(re.findall(r'https://[a-z0-9.-]+\.[a-z]{2,}', js)))
print("domínios:", doms[:60])
