"""Relatório (só leitura): quantos jogadores de padel têm fotos com licença livre na Wikimedia?
Wikidata (pessoas com profissão 'jogador de padel', Q59716278, e foto P18) + Wikimedia Commons (Category:Padel players).
Grava padel_photos_report.json. Não descarrega fotos nem gasta quotas de APIs pagas."""
import json
import re
import time

import requests

from fetch_photos import UA

API = "https://commons.wikimedia.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
FREE = re.compile(r"^(CC0|Public domain|PD|CC BY(-SA)? \d)", re.I)


def get(url, params):
    for i in range(3):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=60)
            r.raise_for_status()
            time.sleep(0.3)
            return r.json()
        except Exception as e:
            print("erro", url, type(e).__name__)
            time.sleep(3 * (i + 1))
    return {}


def wikidata_players():
    q = """SELECT ?p ?pLabel ?img ?countryLabel ?dob ?links WHERE {
      ?p wdt:P106 wd:Q59716278 .
      OPTIONAL { ?p wdt:P18 ?img }
      OPTIONAL { ?p wdt:P27 ?country }
      OPTIONAL { ?p wdt:P569 ?dob }
      OPTIONAL { ?p wikibase:sitelinks ?links }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,es,pt,it,fr". }
    }"""
    j = get(SPARQL, {"query": q, "format": "json"})
    out = {}
    for b in (j.get("results") or {}).get("bindings", []):
        pid = b["p"]["value"].rsplit("/", 1)[-1]
        e = out.setdefault(pid, {"name": b.get("pLabel", {}).get("value"), "country": b.get("countryLabel", {}).get("value"),
                                 "dob": (b.get("dob", {}).get("value") or "")[:10], "links": int(b.get("links", {}).get("value") or 0),
                                 "images": []})
        if b.get("img"):
            f = requests.utils.unquote(b["img"]["value"].rsplit("/", 1)[-1])
            if f not in e["images"]:
                e["images"].append(f)
    return out


def licenses(files):
    lic = {}
    files = list(dict.fromkeys(files))
    for i in range(0, len(files), 50):
        chunk = files[i:i + 50]
        j = get(API, {"action": "query", "titles": "|".join("File:" + f for f in chunk), "prop": "imageinfo",
                      "iiprop": "extmetadata|size", "format": "json"})
        for pg in ((j.get("query") or {}).get("pages") or {}).values():
            ii = (pg.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata") or {}
            name = pg.get("title", "").replace("File:", "")
            lic[name] = {"license": (md.get("LicenseShortName") or {}).get("value"), "w": ii.get("width"), "h": ii.get("height"),
                         "date": re.sub(r"<[^>]+>", "", (md.get("DateTimeOriginal") or {}).get("value") or "")[:10]}
    return lic


def commons_category(root="Category:Padel players", depth=2):
    seen, cats, files = set(), [root], {}
    frontier = [(root, 0)]
    while frontier:
        cat, d = frontier.pop(0)
        if cat in seen:
            continue
        seen.add(cat)
        cont = {}
        while True:
            j = get(API, {"action": "query", "list": "categorymembers", "cmtitle": cat, "cmlimit": 500, "format": "json", **cont})
            for m in (j.get("query") or {}).get("categorymembers", []):
                if m["ns"] == 14 and d < depth:
                    frontier.append((m["title"], d + 1))
                    cats.append(m["title"])
                elif m["ns"] == 6:
                    files.setdefault(cat, []).append(m["title"].replace("File:", ""))
            if "continue" not in j:
                break
            cont = j["continue"]
    return cats, files


def main():
    rep = {"ts": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}
    wd = wikidata_players()
    imgs = [f for e in wd.values() for f in e["images"]]
    lic = licenses(imgs)
    free_players = []
    for pid, e in wd.items():
        ok = [f for f in e["images"] if FREE.match((lic.get(f) or {}).get("license") or "")]
        e["free_images"] = ok
        if ok:
            free_players.append({"qid": pid, "name": e["name"], "country": e["country"], "dob": e["dob"], "links": e["links"],
                                 "file": ok[0], "license": lic[ok[0]]["license"], "photo_date": lic[ok[0]]["date"]})
    free_players.sort(key=lambda x: -x["links"])
    cats, files = commons_category()
    person_cats = {c: v for c, v in files.items() if c != "Category:Padel players"}
    by_lic = {}
    for v in lic.values():
        k = v.get("license") or "?"
        by_lic[k] = by_lic.get(k, 0) + 1
    rep["wikidata"] = {"players": len(wd), "with_photo": sum(1 for e in wd.values() if e["images"]),
                       "with_free_photo": len(free_players), "licenses": by_lic}
    rep["commons"] = {"categories": len(cats), "categories_with_files": len(person_cats),
                      "files": sum(len(v) for v in files.values()),
                      "top_categories": sorted(((c, len(v)) for c, v in person_cats.items()), key=lambda x: -x[1])[:60]}
    rep["free_players"] = free_players
    rep["players_without_photo_sample"] = sorted([e["name"] for e in wd.values() if not e["images"] and e["name"]])
    with open("padel_photos_report.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: rep[k] for k in ("wikidata", "commons")}, ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
