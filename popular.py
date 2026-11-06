"""Páginas de jogadores e torneios mais vistas no nosso site (últimos 14 dias), a partir de /api/popular (Cloudflare Web Analytics).
Guarda popular.json: {"ts", "tennis": {slug: views}, "padel": {id: views}, "tournaments": {path: views}}.
Usado pelo bónus de alcance (reach.py): quem as pessoas procuram no site sobe na fila. Grátis."""
import json
import os
import re
import time

import requests

SITE = (os.environ.get("SITE_URL") or "https://beyond100tennis.com").rstrip("/")


def main():
    try:
        r = requests.get(f"{SITE}/api/popular", timeout=30)
        d = r.json() if r.status_code == 200 else {}
    except Exception as e:
        print("Popular: indisponível", type(e).__name__)
        return
    out = {"ts": time.time(), "days": d.get("days"), "tennis": {}, "padel": {}, "tournaments": {}}
    for p in d.get("pages") or []:
        path, v = p.get("path") or "", int(p.get("views") or 0)
        m = re.match(r"^/p/([a-z0-9-]+?)(?:\.html)?$", path)   # a Cloudflare serve sem .html
        if m:
            out["tennis"][m.group(1)] = out["tennis"].get(m.group(1), 0) + v
            continue
        m = re.match(r"^/padel/p/(\d+)-([a-z0-9-]+)", path)
        if m:
            out["padel"][m.group(1)] = out["padel"].get(m.group(1), 0) + v
            out.setdefault("padel_names", {})[m.group(1)] = m.group(2).replace(".html", "")
            continue
        if path.startswith(("/t/", "/padel/t/")):
            out["tournaments"][path] = out["tournaments"].get(path, 0) + v
    with open("popular.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    top = sorted(out["tennis"].items(), key=lambda kv: -kv[1])[:5]
    print(f"Popular: {len(out['tennis'])} jogadores de ténis, {len(out['padel'])} de padel; top: {top}")


if __name__ == "__main__":
    main()
