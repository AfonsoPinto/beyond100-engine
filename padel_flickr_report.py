"""Relatório (só leitura): fotos de padel com licença livre no Flickr e no Openverse.
Usa a lista de jogadores do padel_photos_report.json (Wikidata). Grava padel_flickr_report.json. Não descarrega fotos."""
import collections
import json
import os
import re
import time

import requests

from fetch_photos import UA, slug

FLICKR = "https://api.flickr.com/services/rest/"
OPENVERSE = "https://api.openverse.org/v1/images/"
LIC = {"4": "CC BY 2.0", "5": "CC BY-SA 2.0", "9": "CC0 1.0", "10": "Public Domain Mark 1.0"}
KEY = os.environ.get("FLICKR_KEY")


def flickr(text, page=1, per=250):
    if not KEY:
        return {}
    try:
        r = requests.get(FLICKR, timeout=15, params={"method": "flickr.photos.search", "api_key": KEY, "text": text, "license": ",".join(LIC),
                                         "media": "photos", "content_type": 1, "sort": "relevance", "per_page": per, "page": page,
                                         "format": "json", "nojsoncallback": 1,
                                         "extras": "license,owner_name,tags,date_taken,url_l,o_dims"},
                         headers={"User-Agent": UA})
        time.sleep(0.4)
        return r.json().get("photos") or {}
    except Exception as e:
        print("flickr", text, type(e).__name__)
        return {}


OV_FAILS, OV_ERR = [0], []
T0 = time.time()


def openverse(q):
    if OV_FAILS[0] >= 20:                                  # o Openverse não responde: não insistir (evita esperas longas)
        return {"error": "skipped"}
    try:
        r = requests.get(OPENVERSE, params={"q": q, "page_size": 20},
                         headers={"User-Agent": UA}, timeout=120)
        time.sleep(3.2)                                   # sem chave: ~20 pedidos/min
        if r.status_code != 200:
            OV_FAILS[0] += 1
            time.sleep(30)
            OV_ERR.append(f"{r.status_code}: {(r.text or '')[:200]}")
            return {"error": r.status_code}
        OV_FAILS[0] = 0
        return r.json()
    except Exception as e:
        OV_FAILS[0] += 1
        OV_ERR.append(type(e).__name__)
        return {"error": type(e).__name__}


def has_name(name, text):
    return re.sub(r"[^a-z0-9]", "", slug(name)) in re.sub(r"[^a-z0-9]", "", slug(text))


def main():
    base = json.load(open("padel_photos_report.json", encoding="utf-8"))
    free = {p["name"] for p in base.get("free_players", [])}
    names = sorted(set(free) | set(base.get("players_without_photo_sample", [])))
    rep = {"ts": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "flickr_key": bool(KEY)}
    # 1) volume geral no Flickr
    gen, photos = {}, []
    for page in range(1, 5):
        j = flickr("padel", page)
        gen.setdefault("total", j.get("total"))
        photos += j.get("photo") or []
        if page >= int(j.get("pages") or 1):
            break
    lic = collections.Counter(LIC.get(str(p.get("license")), "?") for p in photos)
    owners = collections.Counter(p.get("ownername") for p in photos)
    years = collections.Counter((p.get("datetaken") or "")[:4] for p in photos)
    big = sum(1 for p in photos if int(p.get("width_l") or 0) >= 800)
    words = collections.Counter()
    for p in photos:                                      # pares de palavras com maiúscula nos títulos = possíveis nomes
        for m in re.findall(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+ [A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b", p.get("title") or ""):
            words[m] += 1
    rep["flickr_general"] = {"total_reported": gen.get("total"), "sampled": len(photos), "licenses": dict(lic), ">=800px": big,
                             "top_owners": owners.most_common(15), "years": dict(sorted(years.items())),
                             "title_name_pairs": words.most_common(60),
                             "sample": [{"title": p.get("title"), "owner": p.get("ownername"), "license": LIC.get(str(p.get("license"))),
                                         "taken": (p.get("datetaken") or "")[:10],
                                         "page": f"https://www.flickr.com/photos/{p.get('owner')}/{p.get('id')}"} for p in photos[:25]]}
    # 2) por jogador
    per = []
    for n in names:
        j = flickr(f'"{n}"', 1, 50)
        fl = [p for p in j.get("photo") or [] if has_name(n, (p.get("title") or "") + " " + (p.get("tags") or ""))]
        ov = openverse(n)
        ok_ = "error" not in ov
        ovr = [x for x in ov.get("results") or [] if (x.get("license") or "").lower() in ("by", "by-sa", "cc0", "pdm") and has_name(n, (x.get("title") or "") + " " + " ".join(t.get("name", "") for t in x.get("tags") or []))]
        per.append({"name": n, "ov_ok": ok_, "wikimedia_free": n in free, "flickr": len(fl), "openverse": len(ovr),
                    "openverse_sources": sorted({x.get("source") for x in ovr}),
                    "examples": [f"https://www.flickr.com/photos/{p.get('owner')}/{p.get('id')}" for p in fl[:2]] + [x.get("foreign_landing_url") for x in ovr[:2]]})
        print(n, len(fl), len(ovr))
    rep["players"] = per
    rep["openverse_status"] = "ok" if OV_FAILS[0] < 20 else "sem resposta (ignorado)"
    rep["openverse_answered"] = sum(1 for x in per if x.get("ov_ok"))
    rep["openverse_errors"] = OV_ERR[:5]
    rep["summary"] = {"players_checked": len(per),
                      "with_flickr": sum(1 for x in per if x["flickr"]), "with_openverse": sum(1 for x in per if x["openverse"]),
                      "new_vs_wikimedia": sorted(x["name"] for x in per if not x["wikimedia_free"] and (x["flickr"] or x["openverse"]))}
    ovg = openverse("padel")
    rep["openverse_general"] = {"result_count": ovg.get("result_count"), "error": ovg.get("error"),
                                "sample": [{"title": x.get("title"), "source": x.get("source"), "license": x.get("license"),
                                            "url": x.get("foreign_landing_url")} for x in (ovg.get("results") or [])[:20]]}
    with open("padel_flickr_report.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps(rep["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
