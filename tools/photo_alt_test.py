"""Teste (18/11/2026): quantos jogadores de padel sem foto ganhariam uma foto livre pela Openverse, e exemplo de cartão
com a foto livre da cidade do torneio no lugar da foto do jogador. Só lê; não muda dados nem publica."""
import json, os, sys, time, urllib.parse
import requests
sys.path.insert(0, os.getcwd())
from padel import cards
out = sys.argv[1] if len(sys.argv) > 1 else "out"; os.makedirs(out, exist_ok=True)
R = json.load(open("padel/data/rankings.json", encoding="utf-8"))
miss = []
for g in ("men", "women"):
    for p in (R.get(g) or {}).get("rows", [])[:50]:
        if not cards.photo_of(p["id"])[0]: miss.append(p)
print(f"Top 50 + 50 do ranking: {len(miss)} sem foto utilizável")
LIC = "cc0,pdm,by,by-sa"
won = 0
for p in miss:
    sur = (p.get("short_name") or p["name"].split()[-1]).lower()
    hits = []
    for q in (p["name"], f'{p["name"].split()[0]} {p.get("short_name") or p["name"].split()[-1]}'):
        try:
            r = requests.get("https://api.openverse.org/v1/images/", params={"q": q, "license": LIC, "page_size": 20}, timeout=30,
                             headers={"User-Agent": "Beyond100/1.0 (beyond100tennis.com)"})
            res = (r.json().get("results") or []) if r.status_code == 200 else []
        except Exception as e:
            res = []; print("erro", e)
        for x in res:
            txt = " ".join([x.get("title") or ""] + [t.get("name", "") for t in x.get("tags") or []]).lower()
            first = p["name"].split()[0].lower()
            ttl = (x.get("title") or "").lower()
            if sur in ttl and (first in ttl or "padel" in txt) and x["id"] not in [h["id"] for h in hits]:
                hits.append(x)
        time.sleep(1.2)
    if hits:
        won += 1
        h = hits[0]
        print(f"+ {p['name']}: {len(hits)} — " + " | ".join(f"{(x.get('title') or '')[:40]} [{x.get('license')} {x.get('source')} {x.get('width')}x{x.get('height')}]" for x in hits[:3]))
    else:
        print(f"- {p['name']}: nada")
print(f"RESUMO: {won} de {len(miss)} jogadores sem foto têm candidata na Openverse (a confirmar à mão: identidade e qualidade)")
