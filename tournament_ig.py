"""Perfis de Instagram dos torneios a partir da Wikidata (propriedade P2003), para o calendário em categorias_torneios.json.

Regras (conservadoras: na dúvida, não escreve):
  - só itens da Wikidata de ténis (P641 = ténis) cujo tipo (P31) é um "tournament"/"torneio", nunca pessoas;
  - liga o item à cidade pela localização (P276/P131) ou pelo nome do item;
  - uma cidade com 2+ torneios com Instagram diferente é ignorada (não dá para saber qual é qual);
  - nunca altera perfis que já existam em handles_torneios.json (os teus, escritos à mão, ganham sempre);
  - a chave segue o calendário: "ATP Basel", "WTA Tokyo", "Challenger Knoxville".
Uso: python tournament_ig.py [--apply]   (sem --apply só mostra o que encontrou)
"""
import json
import os
import re
import sys
import unicodedata

import requests

UA = f"Beyond100/0.1 (https://beyond100tennis.com; {os.environ.get('WIKI_CONTACT', 'contact-not-set')})"
FILE = "handles_torneios.json"
QUERY = """
SELECT ?item ?itemLabel ?ig ?typeLabel ?locLabel WHERE {
  ?item wdt:P2003 ?ig ; wdt:P641 wd:Q847 ; wdt:P31 ?type .
  FILTER NOT EXISTS { ?item wdt:P31 wd:Q5 }
  ?type rdfs:label ?tl . FILTER(LANG(?tl) = "en" && CONTAINS(LCASE(?tl), "tournament"))
  OPTIONAL { ?item wdt:P276|wdt:P131 ?loc . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}"""


def slug(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def main():
    apply = "--apply" in sys.argv
    cal = json.load(open("categorias_torneios.json", encoding="utf-8"))
    r = requests.get("https://query.wikidata.org/sparql", params={"query": QUERY, "format": "json"},
                     headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}, timeout=90)
    r.raise_for_status()
    rows = r.json()["results"]["bindings"]
    items = {}
    for b in rows:
        it = items.setdefault(b["item"]["value"], {"label": b["itemLabel"]["value"], "ig": set(), "types": set(), "locs": set()})
        it["ig"].add(b["ig"]["value"].strip().lstrip("@"))
        it["types"].add(b.get("typeLabel", {}).get("value", "").lower())
        if b.get("locLabel"):
            it["locs"].add(slug(b["locLabel"]["value"]))
    print(f"Wikidata: {len(items)} torneios de ténis com Instagram.")
    cities = {}
    for e in cal:
        cities.setdefault(slug(e["city"]), set()).add(("Challenger" if e["label"].lower().startswith("challenger")
                                                       else "WTA" if e["label"].upper().startswith("WTA") else "ATP"))
    found = {}
    for c, kinds in cities.items():
        hits = [it for it in items.values() if c in it["locs"] or c in slug(it["label"]).split("-")
                or (len(c.split("-")) > 1 and c in slug(it["label"]))]
        handles = {h for it in hits for h in it["ig"] if re.fullmatch(r"[A-Za-z0-9._]{1,30}", h)}
        if len(handles) != 1:
            if len(handles) > 1:
                print(f"  {c}: {len(handles)} perfis diferentes ({', '.join(sorted(handles))}), ignorado.")
            continue
        h = "@" + handles.pop()
        types = " ".join(t for it in hits for t in it["types"]) + " " + " ".join(slug(it["label"]) for it in hits)
        tour = ("Challenger" if "challenger" in types else "WTA" if "wta" in types else "ATP" if "atp" in types else None)
        if tour is None:
            if len(kinds) != 1:
                print(f"  {c}: {h} mas a cidade tem {sorted(kinds)} e o item não diz qual, ignorado.")
                continue
            tour = next(iter(kinds))
        if tour not in kinds:
            continue
        name = c.replace("-", " ").title()
        found[f"{tour} {name}"] = h
    cur = json.load(open(FILE, encoding="utf-8")) if os.path.exists(FILE) else {}
    have = {slug(k) for k in cur}
    new = {k: v for k, v in sorted(found.items()) if slug(k) not in have}
    for k, v in new.items():
        print(f"  novo: {k} -> {v}")
    print(f"Encontrados {len(found)}, novos {len(new)}.")
    if apply and new:
        cur.update(new)
        cur["_auto"] = "Os perfis sem nota nas _fontes vieram da Wikidata (P2003). Podes apagar ou corrigir qualquer um no admin > Perfis."
        json.dump(cur, open(FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Gravado em", FILE)


if __name__ == "__main__":
    main()
