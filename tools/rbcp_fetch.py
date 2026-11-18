"""Busca as fotos do Red Bull Content Pool pedidas pelo browser (rbcp/inbox.json no repositório privado) e guarda-as em
rbcp/photos/<productId>.jpg com os dados (crédito, jogadores, torneio, data do download = início da licença de 6 meses).
Sem IA: só descarrega e mede a imagem. Nunca imprime os links (são de acesso privado)."""
import json, os, sys, requests
from PIL import Image
base = sys.argv[1] if len(sys.argv) > 1 else "."
inbox = os.path.join(base, "rbcp", "inbox.json"); lib = os.path.join(base, "rbcp", "photos"); os.makedirs(lib, exist_ok=True)
meta_f = os.path.join(base, "rbcp", "photos.json")
meta = json.load(open(meta_f)) if os.path.exists(meta_f) else {}
items = json.load(open(inbox)) if os.path.exists(inbox) else []
left = []
for it in items:
    pid = it["productId"]; fn = os.path.join(lib, pid + ".jpg")
    try:
        r = requests.get(it["url"], timeout=60)
        ok = r.status_code == 200 and r.headers.get("content-type", "").startswith("image")
        print(pid, "estado", r.status_code, r.headers.get("content-type"), len(r.content) // 1024, "KB")
        if not ok: left.append(it); continue
        open(fn, "wb").write(r.content)
        w, h = Image.open(fn).size; print("  medidas", w, "x", h)
        meta[pid] = {k: it.get(k) for k in ("assetId", "persons", "title", "event", "credit", "usage", "downloaded")}
    except Exception as e:
        print(pid, "falhou", type(e).__name__); left.append(it)
json.dump(meta, open(meta_f, "w"), ensure_ascii=False, indent=1)
json.dump(left, open(inbox, "w"), ensure_ascii=False)
print("guardadas:", len(items) - len(left), "| por buscar:", len(left))
