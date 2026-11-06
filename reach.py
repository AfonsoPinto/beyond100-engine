"""Bónus de ALCANCE de um jogador (ténis e padel): quem tem mais probabilidade de dar alcance a um post sobe na fila.
Sinais grátis e verificáveis (nenhum depende de adivinhar):
  1) popularidade na Wikipédia: visitas por mês à página em inglês (API de visitas da Wikimedia), via a ficha da Wikidata
     (a mesma identificação por nome + data de nascimento que usamos para as fotos; sem data só aceita um candidato único);
  2) perfil de Instagram conhecido (podemos identificá-lo -> notificação -> partilha);
  3) nome conhecido: já foi top 50 na carreira (ténis: histórico Tennis Abstract) ou está no top 10 (padel);
  4) jovem promessa: 20 anos ou menos;
  5) procurado no nosso site: página do jogador entre as 30 mais vistas dos últimos 14 dias (popular.json),
     ou o nome dele aparece nas pesquisas do Google que trazem pessoas ao site (gsc.json, Search Console).
O bónus tem teto (REACH_MAX, 2 pontos) para nunca passar por cima das regras de história (final, surpresa, viragem).
Cache em reach.json (30 dias por jogador); no máximo REACH_PER_RUN pesquisas novas por execução."""
import datetime as dt
import json
import os
import time

FILE = "reach.json"
MAX = float(os.environ.get("REACH_MAX") or "2")
PER_RUN = int(os.environ.get("REACH_PER_RUN") or "12")
TTL_D = 30
_cache, _new = None, [0]
Q_PADEL = "Q59716278"


def _load():
    global _cache
    if _cache is None:
        try:
            with open(FILE, encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, ValueError):
            _cache = {}
    return _cache


def save():
    if _cache is not None and _new[0]:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, separators=(",", ":"))


def _views(name, birthday=None, sport="tennis"):
    """(visitas/mês na Wikipédia em inglês, nº de Wikipédias) ou (0, 0). Só com identificação segura."""
    import fetch_photos as fp
    if sport == "tennis":
        e = fp._find_entity(name, birthday)
    else:                                                    # padel: profissão 'jogador de padel'
        found = fp._get(fp.WD, {"action": "wbsearchentities", "search": name, "language": "en", "type": "item", "limit": 7})
        ids = [x["id"] for x in found.get("search", [])]
        e = None
        if ids:
            ents = fp._get(fp.WD, {"action": "wbgetentities", "ids": "|".join(ids), "props": "claims"}).get("entities", {})
            cands = [ents.get(q, {}) for q in ids if Q_PADEL in fp._claim_ids(ents.get(q, {}), "P106")
                     and (not birthday or not fp._birth(ents.get(q, {})) or fp._birth(ents.get(q, {})) == birthday)]
            e = cands[0] if len(cands) == 1 else None
    if not e:
        return 0, 0
    sl = fp._get(fp.WD, {"action": "wbgetentities", "ids": e["id"], "props": "sitelinks"}).get("entities", {}).get(e["id"], {}).get("sitelinks", {})
    langs = sum(1 for k in sl if k.endswith("wiki") and k not in ("commonswiki", "specieswiki"))
    title = (sl.get("enwiki") or {}).get("title")
    if not title:
        return 0, langs
    import requests
    end = dt.date.today().replace(day=1) - dt.timedelta(days=1)
    start = (end - dt.timedelta(days=89)).replace(day=1)
    url = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
           f"{requests.utils.quote(title.replace(' ', '_'), safe='')}/monthly/{start:%Y%m%d}00/{end:%Y%m%d}00")
    r = requests.get(url, headers={"User-Agent": fp.UA}, timeout=20)
    items = r.json().get("items", []) if r.status_code == 200 else []
    v = int(sum(x.get("views", 0) for x in items) / max(1, len(items))) if items else 0
    return v, langs


def info(name, birthday=None, sport="tennis"):
    """{views, langs} da cache; pesquisa (com limite por execução) se faltar ou estiver velho."""
    import fetch_photos as fp
    c = _load()
    k = f"{sport}:{fp.slug(name or '')}"
    hit = c.get(k)
    if hit and time.time() - hit.get("ts", 0) < TTL_D * 86400:
        return hit
    if _new[0] >= PER_RUN or os.environ.get("REACH_LOOKUP", "1") == "0":
        return hit or {}
    _new[0] += 1
    try:
        v, n = _views(name, birthday, sport)
    except Exception as e:
        print("Alcance: falhou", name, type(e).__name__)
        return hit or {}
    c[k] = {"ts": time.time(), "views": v, "langs": n}
    save()
    return c[k]


_pop = None
POP_TOP = int(os.environ.get("REACH_POP_TOP") or "30")


def _popular(sport, name=None, pid=None):
    """True se a página do jogador está entre as POP_TOP mais vistas do nosso site (popular.json, últimos 14 dias)."""
    global _pop
    if _pop is None:
        try:
            with open("popular.json", encoding="utf-8") as f:
                d = json.load(f)
            _pop = {k: set(x for x, _ in sorted((d.get(k) or {}).items(), key=lambda kv: -kv[1])[:POP_TOP]) for k in ("tennis", "padel")}
        except (OSError, ValueError):
            _pop = {"tennis": set(), "padel": set()}
        try:                                                   # o que se pesquisa no Google antes de chegar ao site (gsc.json, Search Console)
            with open("gsc.json", encoding="utf-8") as f:
                _pop["q"] = [x.get("q", "").lower() for x in (json.load(f).get("queries") or [])[:150]]
        except (OSError, ValueError):
            _pop["q"] = []
    if name and any(name.lower() in q for q in _pop.get("q") or []):
        return True
    if sport == "padel":
        return pid is not None and str(pid) in _pop["padel"]
    import webapp
    return bool(name) and webapp.slugify(name) in _pop["tennis"]


def bonus(name, birthday=None, sport="tennis", handle=None, best_rank=None, age=None, pid=None):
    """(pontos, [razões]). Pontos somados ao interesse do jogo, com teto MAX."""
    pts, why = 0.0, []
    if _popular(sport, name, pid):
        pts, why = pts + 0.5, why + ["searched"]
    i = info(name, birthday, sport) if name else {}
    v = i.get("views") or 0
    if v >= 30000:
        pts, why = pts + 1.5, why + ["famous"]
    elif v >= 5000:
        pts, why = pts + 1.0, why + ["well-known"]
    elif v >= 1000:
        pts, why = pts + 0.5, why + ["known"]
    if handle:
        pts, why = pts + 0.5, why + ["taggable"]
    if isinstance(best_rank, int) and best_rank <= (50 if sport == "tennis" else 10):
        pts, why = pts + 0.5, why + ["big-name"]
    if isinstance(age, int) and age <= 20:
        pts, why = pts + 0.5, why + ["prospect"]
    return min(MAX, pts), why


_SS = None


def searched_slugs():
    """Jogadores de ténis que as pessoas procuram: nome nas pesquisas do Google (gsc.json, top 150) ou página entre as mais vistas
    do site (popular.json). Devolve um conjunto de slugs. Usado pelo motor: página sempre no Google e jogos acompanhados primeiro."""
    global _SS
    if _SS is not None:
        return _SS
    import webapp
    _SS = set()
    try:
        with open("gsc.json", encoding="utf-8") as f:
            qs = [x.get("q", "") for x in (json.load(f).get("queries") or [])[:150]]
    except (OSError, ValueError):
        qs = []
    try:
        with open("results.json", encoding="utf-8") as f:
            res = json.load(f)
        res = res if isinstance(res, list) else res.get("results", [])
    except (OSError, ValueError):
        res = []
    names = {(r.get(k) or {}).get("name") for r in res for k in ("p1", "p2")} - {None}
    low = {n.lower(): n for n in names}
    for q in qs:
        ql = q.lower().replace(" ranking", "").replace(" 2026", "").strip()
        n = low.get(ql) or next((v for k, v in low.items() if set(k.split()) == set(ql.split()) and len(ql.split()) >= 2), None)
        if n:
            _SS.add(webapp.slugify(n))
    _popular("tennis")                                          # carrega popular.json
    _SS |= set((_pop or {}).get("tennis") or set())
    return _SS
