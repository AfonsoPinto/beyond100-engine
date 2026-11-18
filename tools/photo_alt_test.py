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
for p in miss[:6] + [{"name": "Agustin Tapia", "short_name": "Tapia"}]:
    sur = (p.get("short_name") or p["name"].split()[-1]).lower()
    hits = []
    for q in (f'"{p["name"]}" padel', p["name"]):
        try:
            r = requests.get("https://api.openverse.org/v1/images/", params={"q": q, "license": LIC, "page_size": 20}, timeout=30,
                             headers={"User-Agent": "Beyond100/1.0 (beyond100tennis.com)"})
            res = (r.json().get("results") or []) if r.status_code == 200 else []
            print("  openverse", q, r.status_code, len(res), [((x.get("title") or "")[:40], x.get("source")) for x in res[:3]])
        except Exception as e:
            res = []; print("erro", e)
        for x in res:
            txt = " ".join([x.get("title") or ""] + [t.get("name", "") for t in x.get("tags") or []]).lower()
            if sur in txt and "padel" in txt and x["id"] not in [h["id"] for h in hits]:
                hits.append(x)
        time.sleep(1.2)
    if hits:
        won += 1
        h = hits[0]
        print(f"+ {p['name']}: {len(hits)} candidata(s) — \"{(h.get('title') or '')[:60]}\" {h.get('license')} {h.get('source')} {h.get('foreign_landing_url')}")
    else:
        print(f"- {p['name']}: nada")
print(f"RESUMO: {won} de {len(miss)} jogadores sem foto têm candidata na Openverse (a confirmar à mão: identidade e qualidade)")
# exemplo: resultado com a foto livre da cidade do torneio
from padel.posts import place_photo
ph = None
for c_ in ("Aguascalientes", "Aguascalientes City", "Mexico City", "Dubai", "Milan"):
    ph = place_photo(c_); print("foto do local:", c_, ph)
    if ph: city_ = c_; break
if ph:
    d = {"kicker": "Win", "level": "FIP PLATINUM", "round": "Round of 32", "tournament": "FIP Platinum Aguascalientes", "city": city_,
         "date": "17 NOV 2026", "winners": [{"id": 1, "name": "Javier Valdes", "short_name": "Valdes", "nationality": "CL"}, {"id": 2, "name": "Renzo Gabriel Nuñez", "short_name": "Nuñez", "nationality": "AR"}],
         "losers": [{"id": 3, "name": "Juanlu Esbri", "short_name": "Esbri", "nationality": "ES"}, {"id": 4, "name": "Pol Hernandez", "short_name": "Hernandez", "nationality": "ES"}],
         "sets": [(7, 6), (4, 6), (6, 3)], "photo": {"path": ph["path"], "credit": ph.get("credit")}, "ranks": {}, "note": ""}
    os.environ["PADEL_RESULT_STYLE"] = "C"
    cards.result_card(d, os.path.join(out, "exemplo_foto_local.jpg"))
    print("exemplo feito")
