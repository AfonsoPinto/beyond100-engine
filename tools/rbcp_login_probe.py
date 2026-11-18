"""Sondagem com login (Playwright, Chromium sem janela): entra com a conta do Afonso (secrets RBCP_EMAIL / RBCP_PASSWORD),
pesquisa "Augsburger" e regista só os caminhos dos pedidos à API (sem cabeçalhos, tokens ou dados pessoais).
Não descarrega fotos."""
import os, re, sys, json, asyncio
from playwright.async_api import async_playwright
EMAIL, PWD = os.environ.get("RBCP_EMAIL"), os.environ.get("RBCP_PASSWORD")
if not EMAIL or not PWD:
    print("faltam os secrets RBCP_EMAIL / RBCP_PASSWORD"); sys.exit(0)
calls = []
def clean(u):
    if "newseditor" in u and "?" in u:                        # mostra os nomes dos parâmetros da pesquisa (não os valores)
        from urllib.parse import urlparse, parse_qs
        q = parse_qs(urlparse(u).query); return re.sub(r"[?#].*", "", u) + " ?" + ",".join(f"{k}={v[0][:30]}" for k, v in q.items())
    return re.sub(r"[?#].*", "", u)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(locale="en-GB"); pg = await ctx.new_page()
        pg.on("request", lambda r: calls.append((r.method, clean(r.url))) if ("/api/" in r.url or "auth" in r.url or "login" in r.url or "token" in r.url) else None)
        await pg.goto("https://www.redbullcontentpool.com/", wait_until="networkidle")
        cfg = await pg.evaluate("fetch('/api/config').then(r=>r.ok?r.json():null).catch(()=>null)")
        if cfg: print("config (chaves):", sorted(cfg.keys())[:40] if isinstance(cfg, dict) else type(cfg))
        try: await pg.click("#onetrust-accept-btn-handler", timeout=6000)      # banner dos cookies
        except Exception: print("sem banner de cookies")
        # resposta pública da pesquisa: só as chaves (estrutura)
        async def keys_of(url):
            return await pg.evaluate("u=>fetch(u).then(r=>r.json().then(j=>[r.status, JSON.stringify(j).slice(0,1500)])).catch(e=>[0,String(e)])", url)
        # botão de login
        for sel in ["rbcp-user-icon cosmos-button", "text=Log in", "text=Login", "text=Sign in", "cosmos-button:has-text('Log')"]:
            try:
                await pg.click(sel, timeout=4000); break
            except Exception: pass
        await pg.wait_for_timeout(6000)
        print("página de login:", re.sub(r"[?#].*", "", pg.url))
        inputs = await pg.evaluate("Array.from(document.querySelectorAll('input')).map(i=>[i.type,i.name,i.id,i.autocomplete])")
        print("campos:", inputs)
        html = await pg.content()
        print("captcha?", any(k in html.lower() for k in ("recaptcha", "hcaptcha", "turnstile", "captcha")))
        try:
            await pg.wait_for_selector("input[name=username], input[type=email], #username", timeout=15000)
            await pg.fill("input[name=username], input[type=email], #username", EMAIL, timeout=8000)
            if not await pg.query_selector("input[type=password]"):
                await pg.click("button[type=submit], button[name=action]", timeout=5000); await pg.wait_for_timeout(2500)
            await pg.fill("input[type=password]", PWD, timeout=8000)
            await pg.click("button[type=submit], button[name=action]", timeout=5000)
            await pg.wait_for_timeout(9000)
        except Exception as e:
            print("login automático falhou:", type(e).__name__)
        print("depois do login:", re.sub(r"[?#].*", "", pg.url))
        print("captcha no login?", any(k in (await pg.content()).lower() for k in ("recaptcha", "hcaptcha", "turnstile", "captcha", "arkose")))
        who = await pg.evaluate("fetch('/api/auth/who-am-i').then(r=>r.status).catch(()=>0)")
        print("who-am-i:", who)
        await pg.goto("https://www.redbullcontentpool.com/search?q=Augsburger", wait_until="load"); await pg.wait_for_timeout(8000)
        imgs = await pg.evaluate("document.querySelectorAll('img').length")
        print("imagens na pesquisa:", imgs)
        su = [u for m, u in calls if "newseditor" in u and "/v2/search" in u]
        print("amostra da resposta da pesquisa:")
        if su:
            base = su[-1].split(" ?")[0]
            st, body = await keys_of(base + "?q=Augsburger&limit=2")
            print("  status", st); print("  ", body[:1500])
        await b.close()
    seen = []
    for m, u in calls:
        if (m, u) not in seen: seen.append((m, u))
    print("pedidos (método e caminho):")
    for m, u in seen[:80]: print("  ", m, u[:160])
asyncio.run(main())
