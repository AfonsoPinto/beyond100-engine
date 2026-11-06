"""Beyond Padel: busca semanal automática de fotos livres (Wikimedia) para jogadores que ainda não têm foto.

Só entra uma foto quando é seguro quanto a QUEM está na imagem:
  1) o jogador está identificado na Wikidata como jogador de padel (Q59716278), com o mesmo nome e, quando
     ambos têm data de nascimento, a mesma data; com dois candidatos possíveis, não entra nada;
  2) a foto vem da própria Wikidata (P18) ou da categoria do jogador na Commons (P373);
  3) o nome do ficheiro tem o apelido do jogador;
  4) licença livre (CC0, domínio público, CC BY, CC BY-SA) e tamanho mínimo (lado menor >= 500 px).
Fotos recusadas à mão: padel/photos/blocked.json (lista de ids). Registo: padel/photos/scan_log.json.

Uso: python -m padel.photo_scan [--dry]   (--dry: só escreve o relatório, não descarrega)"""
import json
import os
import re
import sys
import time
import unicodedata

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetch_photos import UA  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTOS = os.path.join(HERE, "photos")
DATA = os.path.join(HERE, "data")
API = "https://commons.wikimedia.org/w/api.php"
SPARQL = "https://query.wikidata.org/sparql"
FREE = re.compile(r"^(CC0|Public domain|PDM|CC BY(-SA)? \d)", re.I)
MIN_SIDE = 500
MAX_NEW = int(os.environ.get("PADEL_PHOTO_SCAN_MAX") or "40")
SEARCH_TOP = int(os.environ.get("PADEL_PHOTO_SEARCH_TOP") or "250")


def norm(s):
    return re.sub(r"[^a-z ]", "", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()).split()


def get(url, params):
    for i in range(3):
        try:
            r = requests.get(url, params=params, headers={"User-Agent": UA, "Accept": "application/json"}, timeout=60)
            r.raise_for_status()
            time.sleep(0.25)
            return r.json()
        except Exception as e:
            print("erro", url, type(e).__name__, e)
            time.sleep(3 * (i + 1))
    return {}


def wikidata_padel():
    q = """SELECT ?p ?pLabel ?alt ?img ?cat ?dob WHERE {
      ?p wdt:P106 wd:Q59716278 .
      OPTIONAL { ?p wdt:P18 ?img }
      OPTIONAL { ?p wdt:P373 ?cat }
      OPTIONAL { ?p wdt:P569 ?dob }
      OPTIONAL { ?p skos:altLabel ?alt . FILTER(LANG(?alt) IN ("en","es","pt","it","fr")) }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "en,es,pt,it,fr". }
    }"""
    j = get(SPARQL, {"query": q, "format": "json"})
    out = {}
    for b in (j.get("results") or {}).get("bindings", []):
        qid = b["p"]["value"].rsplit("/", 1)[-1]
        e = out.setdefault(qid, {"qid": qid, "names": set(), "dob": "", "images": [], "cat": ""})
        for k in ("pLabel", "alt"):
            if b.get(k):
                e["names"].add(b[k]["value"])
        if b.get("dob"):
            e["dob"] = b["dob"]["value"][:10]
        if b.get("cat"):
            e["cat"] = b["cat"]["value"]
        if b.get("img"):
            f = requests.utils.unquote(b["img"]["value"].rsplit("/", 1)[-1])
            if f not in e["images"]:
                e["images"].append(f)
    return list(out.values())


def same_person(player, wd):
    """Nome igual (primeiro e último nome do jogador presentes num dos nomes da Wikidata) e, se houver, mesma data de nascimento."""
    pn = norm(player.get("name"))
    if len(pn) < 2:
        return False
    sh = norm(player.get("short_name") or "")
    last = sh[0] if sh else pn[-1]
    ok = any({pn[0], pn[-1]} <= set(norm(n)) or {pn[0], last} <= set(norm(n)) for n in wd["names"])
    if not ok:
        return False
    b = (player.get("birthdate") or "")[:10]
    return not (b and wd["dob"] and b != wd["dob"])


MULTI = re.compile(r"\b(and|y|e|et|und|vs|versus|with|con)\b|&|,", re.I)


def single_person(title):
    """Títulos com mais de uma pessoa ('X and Y', 'X y Y', 'X, Y') ficam de fora: não se sabe quem é quem."""
    return not MULTI.search(re.sub(r"\.[a-z]+$", "", title, flags=re.I).replace("_", " "))


def commons_search(player):
    """Jogadores sem item na Wikidata: ficheiros da Commons com o NOME COMPLETO no título e 'padel' no título ou nas categorias."""
    pn = norm(player.get("name"))
    if len(pn) < 2:
        return []
    j = get(API, {"action": "query", "list": "search", "srnamespace": 6, "srlimit": 20, "format": "json",
                  "srsearch": f'"{player.get("name")}" padel'})
    out = []
    for h in (j.get("query") or {}).get("search", []):
        t = h["title"].replace("File:", "")
        tn = norm(re.sub(r"\.[a-z]+$", "", t, flags=re.I))
        if pn[0] in tn and pn[-1] in tn and re.search(r"\.(jpe?g|png)$", t, re.I):
            out.append(t)
    return out


def surname_in_title(player, title):
    t = " ".join(norm(re.sub(r"\.[a-z]+$", "", title, flags=re.I)))
    toks = [x for x in norm(player.get("short_name") or "") + norm(player.get("name"))[1:] if len(x) >= 4]
    return bool(toks) and any(x in t.split() or x in t for x in toks)


def file_info(files):
    out = {}
    for i in range(0, len(files), 40):
        chunk = files[i:i + 40]
        j = get(API, {"action": "query", "titles": "|".join("File:" + f for f in chunk), "prop": "imageinfo",
                      "iiprop": "url|extmetadata|size", "iiurlwidth": 1600, "format": "json"})
        for pg in ((j.get("query") or {}).get("pages") or {}).values():
            ii = (pg.get("imageinfo") or [{}])[0]
            md = ii.get("extmetadata") or {}
            out[pg.get("title", "").replace("File:", "")] = {
                "license": (md.get("LicenseShortName") or {}).get("value") or "",
                "artist": re.sub(r"<[^>]+>", "", (md.get("Artist") or {}).get("value") or "").strip(),
                "date": re.sub(r"<[^>]+>", "", (md.get("DateTimeOriginal") or {}).get("value") or "")[:10],
                "w": ii.get("width") or 0, "h": ii.get("height") or 0, "url": ii.get("thumburl") or ii.get("url"),
                "page": ii.get("descriptionurl")}
    return out


def category_files(cat):
    j = get(API, {"action": "query", "list": "categorymembers", "cmtitle": "Category:" + cat, "cmtype": "file", "cmlimit": 50, "format": "json"})
    return [m["title"].replace("File:", "") for m in (j.get("query") or {}).get("categorymembers", [])
            if re.search(r"\.(jpe?g|png)$", m["title"], re.I)]


def targets():
    """Jogadores sem foto: os que aparecem nos jogos e/ou no top 300, por ordem de ranking."""
    players = json.load(open(os.path.join(DATA, "players.json"), encoding="utf-8")) if os.path.exists(os.path.join(DATA, "players.json")) else {}
    ranks = json.load(open(os.path.join(DATA, "rankings.json"), encoding="utf-8")) if os.path.exists(os.path.join(DATA, "rankings.json")) else {}
    rows = {str(x["id"]): x for c in ranks.values() for x in (c or {}).get("rows", [])}
    have = {f[:-4] for f in os.listdir(PHOTOS) if f.endswith(".jpg")}
    try:
        blocked = {str(x) for x in json.load(open(os.path.join(PHOTOS, "blocked.json")))}
    except (OSError, ValueError):
        blocked = set()
    out = {}
    for pid, r in rows.items():
        if (r.get("ranking") or 999) <= 300:
            out[pid] = dict(r, **{k: v for k, v in (players.get(pid) or {}).items() if v})
    for pid, p in players.items():
        out.setdefault(pid, p)
    return sorted([p for pid, p in out.items() if pid not in have and pid not in blocked and p.get("name")],
                  key=lambda p: (rows.get(str(p.get("id")), {}).get("ranking") or 9999))


def main(dry=False):
    wd = wikidata_padel()
    print(f"Wikidata: {len(wd)} jogadores de padel.")
    tg = targets()
    print(f"Sem foto: {len(tg)} jogadores.")
    plan = []
    for p in tg:
        cands = [w for w in wd if same_person(p, w)]
        if len(cands) > 1:
            continue
        if len(cands) != 1:
            continue
        w = cands[0]
        files = [f for f in w["images"] if surname_in_title(p, f) and single_person(f)]
        if not files and w["cat"]:
            files = [f for f in category_files(w["cat"]) if surname_in_title(p, f) and single_person(f)]
        if files:
            plan.append((p, w, files))
    done = {str(p.get("id")) for p, _, _ in plan}
    for p in tg[:SEARCH_TOP]:                                    # sem Wikidata: pesquisa pelo nome completo + padel
        if str(p.get("id")) in done:
            continue
        files = [f for f in commons_search(p) if single_person(f)]
        if files:
            plan.append((p, {"qid": "", "images": [], "cat": ""}, files))
    infos = file_info(sorted({f for _, _, fs in plan for f in fs}))
    log_fp = os.path.join(PHOTOS, "scan_log.json")
    try:
        log = json.load(open(log_fp, encoding="utf-8"))
    except (OSError, ValueError):
        log = []
    try:
        credits = json.load(open(os.path.join(PHOTOS, "credits.json"), encoding="utf-8"))
    except (OSError, ValueError):
        credits = {}
    added, report = 0, []
    for p, w, files in plan:
        ok = [(f, infos[f]) for f in files if f in infos and FREE.match(infos[f]["license"] or "") and min(infos[f]["w"], infos[f]["h"]) >= MIN_SIDE]
        if not ok:
            report.append({"id": p.get("id"), "name": p.get("name"), "qid": w["qid"], "skip": "sem licença livre ou foto pequena", "files": files[:3]})
            continue
        ok.sort(key=lambda x: (x[0] in w["images"], x[1]["date"], x[1]["w"] * x[1]["h"]), reverse=True)   # P18 primeiro, depois a mais recente
        f, info = ok[0]
        report.append({"id": p.get("id"), "name": p.get("name"), "qid": w["qid"], "file": f, "license": info["license"], "date": info["date"]})
        if dry or added >= MAX_NEW:
            continue
        try:
            r = requests.get(info["url"], headers={"User-Agent": UA}, timeout=60)
            r.raise_for_status()
            with open(os.path.join(PHOTOS, f"{p['id']}.jpg"), "wb") as fh:
                fh.write(r.content)
        except Exception as e:
            print("download falhou", f, e)
            continue
        credits[str(p["id"])] = {"credit": f"Photo: {info['artist'] or 'Unknown'} / {info['license']}", "page": info["page"],
                                 "license": info["license"], "offcourt": False, "auto": time.strftime("%Y-%m-%d")}
        log.append({"id": p["id"], "name": p.get("name"), "file": f, "page": info["page"], "license": info["license"],
                    "date": time.strftime("%Y-%m-%d"), "qid": w["qid"]})
        added += 1
        time.sleep(0.5)
    if not dry:
        json.dump(credits, open(os.path.join(PHOTOS, "credits.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(log[-500:], open(log_fp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump({"ts": time.time(), "dry": dry, "wikidata": len(wd), "targets": len(tg), "found": report},
              open(os.path.join(PHOTOS, "scan_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Padel fotos: {added} novas{' (simulação)' if dry else ''}; {len(report)} candidatos.")
    for x in report:
        print(" ", x)


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
