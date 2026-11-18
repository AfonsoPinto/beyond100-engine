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
    u = re.sub(r"[?#].*", "", u); return u
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); ctx = await b.new_context(locale="en-GB"); pg = await ctx.new_page()
        pg.on("request", lambda r: calls.append((r.method, clean(r.url))) if ("/api/" in r.url or "auth" in r.url or "login" in r.url or "token" in r.url) else None)
        await pg.goto("https://www.redbullcontentpool.com/", wait_until="networkidle")
        cfg = await pg.evaluate("fetch('/api/config').then(r=>r.ok?r.json():null).catch(()=>null)")
        if cfg: print("config (chaves):", sorted(cfg.keys())[:40] if isinstance(cfg, dict) else type(cfg))
        # botão de login
        for sel in ["text=Log in", "text=Login", "text=Sign in", "rbcp-user-icon cosmos-button", "cosmos-button:has-text('Log')"]:
            try:
                await pg.click(sel, timeout=4000); break
            except Exception: pass
        await pg.wait_for_load_state("networkidle")
        print("página de login:", re.sub(r"[?#].*", "", pg.url))
        inputs = await pg.evaluate("Array.from(document.querySelectorAll('input')).map(i=>[i.type,i.name,i.id,i.autocomplete])")
        print("campos:", inputs)
        html = await pg.content()
        print("captcha?", any(k in html.lower() for k in ("recaptcha", "hcaptcha", "turnstile", "captcha")))
        try:
            await pg.fill("input[type=email], input[name*=mail i], input[name=username], input[id*=mail i]", EMAIL, timeout=8000)
            try: await pg.click("button[type=submit]", timeout=3000); await pg.wait_for_timeout(2500)
            except Exception: pass
            await pg.fill("input[type=password]", PWD, timeout=8000)
            await pg.click("button[type=submit]", timeout=5000)
            await pg.wait_for_load_state("networkidle"); await pg.wait_for_timeout(4000)
        except Exception as e:
            print("login automático falhou:", type(e).__name__)
        print("depois do login:", re.sub(r"[?#].*", "", pg.url))
        who = await pg.evaluate("fetch('/api/auth/who-am-i').then(r=>r.status).catch(()=>0)")
        print("who-am-i:", who)
        await pg.goto("https://www.redbullcontentpool.com/search?q=Augsburger", wait_until="networkidle"); await pg.wait_for_timeout(5000)
        imgs = await pg.evaluate("document.querySelectorAll('img').length")
        print("imagens na pesquisa:", imgs)
        await b.close()
    seen = []
    for m, u in calls:
        if (m, u) not in seen: seen.append((m, u))
    print("pedidos (método e caminho):")
    for m, u in seen[:80]: print("  ", m, u[:160])
asyncio.run(main())
