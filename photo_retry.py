"""Volta a procurar fotos (licença livre, Wikimedia) para jogadores que ficaram marcados como 'sem foto'.
Por omissão: o top 100 ATP/WTA (ESPN) que ainda não tem foto. Usa o fetch_photo do site (mesmas regras de identidade e licença)."""
import glob, json, os
import fetch_photos as fp

names = [x.strip() for x in (os.environ.get("NAMES") or "").split("|") if x.strip()]
if not names:
    er = json.load(open("espn_rank.json"))
    names = [x["n"] for lg in ("atp", "wta") for x in er.get(lg, []) if x["r"] <= 100]
todo = [n for n in names if not os.path.exists(os.path.join(fp.PHOTO_DIR, fp.slug(n) + ".jpg"))]
for f in glob.glob(os.path.join(fp.PHOTO_DIR, "misses*.json")):          # tira-os da lista de 'sem foto' para tentar já
    d = json.load(open(f))
    for n in todo:
        d.pop(fp.slug(n), None)
    json.dump(d, open(f, "w"))
got = []
for n in todo:
    if fp.fetch_photo(n, None, fp.PHOTO_DIR):
        got.append(n)
        print("foto:", n)
print(f"Fotos novas: {len(got)} de {len(todo)} sem foto.")
