"""Procura já fotos extra (galeria) para os jogadores que mais aparecem nos posts, sem esperar pelo ciclo mensal.
Só Wikimedia Commons (gratuito). Uso: python refresh_galleries.py [N]  (por omissão os 40 mais frequentes)."""
import collections
import json
import os
import sys
import time

import fetch_photos as fp

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return d


results = {str(r.get("id")): r for r in load("results.json", [])}
posts = load("posts.json", {})
count = collections.Counter()
for es in posts.values():                                   # vencedores dos cartões de resultados (os que mais repetem foto)
    for e in es:
        r = results.get(str(e.get("id")))
        if r and r.get("winner") in (1, 2):
            count[r["p%d" % r["winner"]]["name"]] += 3
cut = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 30 * 86400))
for r in results.values():                                  # e quem mais ganha no último mês
    if r.get("date", "") >= cut and r.get("winner") in (1, 2):
        count[r["p%d" % r["winner"]]["name"]] += 1
done = 0
only = [x.strip() for x in (os.environ.get("NAMES") or "").split(",") if x.strip()]
if only:                                                    # nomes pedidos à mão: só esses
    count = collections.Counter({n: 1 for n in only})
for name, _ in count.most_common():
    key = fp.slug(name)
    if not any(os.path.exists(os.path.join("photos", key + ext)) for ext in (".jpg", ".jpeg", ".png", ".webp")):
        continue                                            # sem foto principal: a galeria não se aplica
    added = fp.gallery(name, photo_dir="photos", force=True)
    print(f"{name}: +{len(added)}")
    done += 1
    if done >= N:
        break
print(f"Galerias revistas: {done}.")
