"""Google Search Console (grátis): o que as pessoas pesquisam no Google antes de chegar ao site (últimos 28 dias).
Guarda gsc.json: {"ts", "queries": [{q, clicks, impressions, position}], "pages": [{page, clicks, impressions}]}.
Precisa do segredo GSC_KEY (JSON de uma conta de serviço do Google Cloud com a Search Console API ativa,
adicionada como utilizador da propriedade no Search Console). Sem segredo: não faz nada."""
import datetime as dt
import json
import os
import time

import requests

SITE = os.environ.get("GSC_SITE") or "sc-domain:beyond100tennis.com"


def _token(info):
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    cred = service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    cred.refresh(Request())
    return cred.token


def _query(tok, dims, n):
    end = dt.date.today() - dt.timedelta(days=2)
    start = end - dt.timedelta(days=27)
    r = requests.post(f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote(SITE, safe='')}/searchAnalytics/query",
                      headers={"Authorization": f"Bearer {tok}"}, timeout=30,
                      json={"startDate": str(start), "endDate": str(end), "dimensions": dims, "rowLimit": n})
    r.raise_for_status()
    return r.json().get("rows") or []


def daily(tok, days=90, padel=None):
    """Evolução dia a dia (vezes que aparecemos, cliques, posição média), últimos 'days' dias: dá logo um gráfico com história.
    padel=True/False: só as páginas de padel (/padel/) ou só as de ténis (11/11/2026)."""
    end = dt.date.today() - dt.timedelta(days=2)
    start = end - dt.timedelta(days=days - 1)
    body = {"startDate": str(start), "endDate": str(end), "dimensions": ["date"], "rowLimit": days}
    if padel is not None:
        body["dimensionFilterGroups"] = [{"filters": [{"dimension": "page", "operator": "contains" if padel else "notContains", "expression": "/padel/"}]}]
    r = requests.post(f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote(SITE, safe='')}/searchAnalytics/query",
                      headers={"Authorization": f"Bearer {tok}"}, timeout=30, json=body)
    r.raise_for_status()
    return [{"d": x["keys"][0], "i": x.get("impressions", 0), "c": x.get("clicks", 0), "p": round(x.get("position", 0), 1)}
            for x in sorted(r.json().get("rows") or [], key=lambda x: x["keys"][0])]


HEALTH_URLS = ["https://beyond100tennis.com/", "https://beyond100tennis.com/padel/", "https://beyond100tennis.com/results"]


def health():
    """Saúde do site (PageSpeed Insights no telemóvel, com YT_API_KEY) + vídeos de padel bloqueados nos países principais."""
    key = os.environ.get("YT_API_KEY")
    out = {"ts": time.time(), "pages": [], "videos": {}}
    if not key:
        return out
    urls = list(HEALTH_URLS)
    try:                                                    # + a página de jogador mais pesquisada
        pop = sorted((json.load(open("popular.json", encoding="utf-8")).get("tennis") or {}).items(), key=lambda kv: -kv[1])
        if pop:
            urls.append(f"https://beyond100tennis.com/p/{pop[0][0]}")
    except (OSError, ValueError):
        pass
    for u in urls:
        try:
            r = requests.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed", timeout=120,
                             params={"url": u, "key": key, "strategy": "mobile", "category": ["performance", "seo", "accessibility", "best-practices"]})
            j = r.json()["lighthouseResult"]
            c, a = j["categories"], j["audits"]
            out["pages"].append({"url": u, "perf": round((c["performance"]["score"] or 0) * 100), "seo": round((c["seo"]["score"] or 0) * 100),
                                 "a11y": round((c["accessibility"]["score"] or 0) * 100), "bp": round((c["best-practices"]["score"] or 0) * 100),
                                 "lcp": a["largest-contentful-paint"]["displayValue"], "kb": round(a["total-byte-weight"]["numericValue"] / 1024)})
        except Exception as e:
            out["pages"].append({"url": u, "error": type(e).__name__})
    try:
        emb = json.load(open("padel/data/yt_embed.json", encoding="utf-8"))
        out["videos"] = {"checked": len(emb), "ok": sum(1 for v in emb.values() if v[0] == 200),
                         "blocked_country": sum(1 for v in emb.values() if v[0] == 451),
                         "no_embed": sum(1 for v in emb.values() if v[0] in (401, 403)), "gone": sum(1 for v in emb.values() if v[0] == 404)}
    except (OSError, ValueError):
        pass
    return out


def _norm(s):
    import unicodedata
    return " ".join(unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().split())


def todo(out):
    """'O que fazer esta semana': ações concretas a partir das pesquisas do Google, cruzadas com os nossos dados."""
    try:
        res = json.load(open("results.json", encoding="utf-8"))
        res = res if isinstance(res, list) else res.get("results", [])
    except (OSError, ValueError):
        res = []
    names = {}
    for r in res:
        for k in ("p1", "p2"):
            n = (r.get(k) or {}).get("name")
            if n:
                names[_norm(n)] = n
    try:
        up = json.load(open("upcoming.json", encoding="utf-8")).get("matches") or []
    except (OSError, ValueError):
        up = []
    playing = {}
    for m in up:
        for k in ("p1", "p2"):
            n = (m.get(k) or {}).get("name")
            if n:
                playing.setdefault(_norm(n), m)
    pages = {x["page"].rstrip("/").split("/")[-1].replace(".html", ""): x for x in out.get("pages") or []}
    acts, seen = [], set()

    def who(q):
        qn = _norm(q).replace(" ranking", "").replace(" 2026", "").strip()
        for nn, n in names.items():
            parts = nn.split()
            if qn == nn or (len(parts) >= 2 and set(qn.split()) == set(parts)):
                return n
        w = qn.replace(".", " ").split()
        if len(w) == 2 and len(w[0]) == 1:                  # "a parks": inicial + apelido, se só houver um jogador assim
            hits = [n for nn, n in names.items() if nn.split()[-1] == w[1] and nn.split()[0].startswith(w[0])]
            if len(hits) == 1:
                return hits[0]
        if len(qn.split()) == 1:                            # só o apelido: vale se houver um único jogador com esse apelido
            hits = [n for nn, n in names.items() if nn.split()[-1] == qn]
            if len(hits) == 1:
                return hits[0]
        return None
    for x in out.get("queries") or []:
        n = who(x["q"])
        key = n or x["q"]
        if key in seen or x["impressions"] < 10:
            continue
        slug = "-".join(_norm(n).split()) if n else ""
        if n and _norm(n) in playing:
            m = playing[_norm(n)]
            seen.add(key)
            acts.append({"kind": "playing", "q": x["q"], "who": n, "impr": x["impressions"], "pos": x["position"], "url": f"/p/{slug}",
                         "text": f"{n} joga esta semana ({m.get('tp') or ''}, {m.get('round') or ''}): muito pesquisado, prioridade na antevisão e no post."})
        elif n and x["position"] > 20:
            seen.add(key)
            acts.append({"kind": "page2", "q": x["q"], "who": n, "impr": x["impressions"], "pos": x["position"], "url": f"/p/{slug}",
                         "text": f"\"{x['q']}\": {x['impressions']} pesquisas mas estamos na posição {str(x['position']).replace('.', ',')} (2.ª página ou pior). Reforçar a página de {n}."})
        elif n and x["position"] <= 20 and x["clicks"] == 0:
            seen.add(key)
            acts.append({"kind": "noclick", "q": x["q"], "who": n, "impr": x["impressions"], "pos": x["position"], "url": f"/p/{slug}",
                         "text": f"\"{x['q']}\": aparecemos {x['impressions']} vezes na posição {str(x['position']).replace('.', ',')} e ninguém clicou. Título e topo da página de {n}."})
        elif not n and x["impressions"] >= 15:
            seen.add(key)
            acts.append({"kind": "missing", "q": x["q"], "impr": x["impressions"], "pos": x["position"],
                         "text": f"\"{x['q']}\": {x['impressions']} pesquisas e não temos uma página certa para isto."})
    order = {"playing": 0, "page2": 1, "noclick": 2, "missing": 3}
    acts.sort(key=lambda a: (order[a["kind"]], -a["impr"]))
    return acts[:20]


TEST_DAYS, TEST_MAX = 14, 15


def _page_stats(tok, slug, start, end):
    """Cliques e aparições de uma página de jogador entre duas datas (Search Console, por página).
    slug: 'nome-do-jogador' (ténis, /p/...) ou um caminho começado por '/' (padel: /padel/p/66-agustin-tapia)."""
    r = requests.post(f"https://www.googleapis.com/webmasters/v3/sites/{requests.utils.quote(SITE, safe='')}/searchAnalytics/query",
                      headers={"Authorization": f"Bearer {tok}"}, timeout=30,
                      json={"startDate": str(start), "endDate": str(end), "dimensions": ["page"], "rowLimit": 10,
                            "dimensionFilterGroups": [{"filters": [{"dimension": "page", "operator": "contains", "expression": slug if slug.startswith("/") else f"/p/{slug}"}]}]})
    r.raise_for_status()
    rows = r.json().get("rows") or []
    c, i = sum(x.get("clicks", 0) for x in rows), sum(x.get("impressions", 0) for x in rows)
    return {"clicks": c, "impr": i, "ctr": round(c / i, 4) if i else 0}


def title_tests(tok, out, old):
    """11/11/2026 (Afonso: "se achas benéfico, avança"): páginas da lista "Ninguém clica" passam a ter um título com o que o Google
    não mostra (subida/descida da semana, data de atualização, próximo jogo). Ao fim de 14 dias compara com os 14 dias antes:
    se os cliques/CTR não melhorarem, o teste fica 'lost' e o site volta ao título normal. Guardado em gsc.json -> title_tests."""
    tests = dict(old.get("title_tests") or {})
    today = dt.date.today()
    lag = dt.timedelta(days=2)                                  # o Search Console tem ~2 dias de atraso
    acts = list(out.get("todo") or []) + list(((out.get("by_sport") or {}).get("padel") or {}).get("todo") or [])   # 12/11/2026: também o padel
    for a in acts:
        u = a.get("url") or ""
        if a.get("kind") != "noclick" or not (u.startswith("/p/") or u.startswith("/padel/p/")):
            continue
        slug = u[3:] if u.startswith("/p/") else u
        padel = slug.startswith("/padel/")
        if slug in tests or sum(1 for k, t in tests.items() if t.get("status") == "running" and k.startswith("/padel/") == padel) >= TEST_MAX:
            continue
        try:
            before = _page_stats(tok, slug, today - lag - dt.timedelta(days=TEST_DAYS - 1), today - lag)
        except Exception:
            continue
        tests[slug] = {"q": a.get("q"), "who": a.get("who"), "start": str(today), "status": "running", "before": before}
    for slug, t in tests.items():
        if t.get("status") != "running":
            continue
        st = dt.date.fromisoformat(t["start"])
        if today - lag < st + dt.timedelta(days=TEST_DAYS - 1):
            continue
        try:
            after = _page_stats(tok, slug, st, st + dt.timedelta(days=TEST_DAYS - 1))
        except Exception:
            continue
        b = t.get("before") or {}
        t["after"] = after
        won = after["clicks"] > b.get("clicks", 0) and (after["ctr"] >= b.get("ctr", 0))
        t["status"] = "won" if won else "lost"
        t["ended"] = str(today)
    return tests


def split_queries(rows):
    """Pesquisas por desporto (11/11/2026): com as dimensões pesquisa+página, cada pesquisa conta para o ténis ou para o padel
    conforme a página que o Google mostrou (/padel/ = padel). Posição média pesada pelas aparições."""
    acc = {"tennis": {}, "padel": {}}
    for x in rows:
        q, page = x["keys"][0], x["keys"][1]
        sp = "padel" if "/padel/" in page else "tennis"
        a = acc[sp].setdefault(q, {"q": q, "clicks": 0, "impressions": 0, "_pw": 0.0})
        a["clicks"] += x.get("clicks", 0)
        a["impressions"] += x.get("impressions", 0)
        a["_pw"] += x.get("position", 0) * x.get("impressions", 0)
    out = {}
    for sp, d in acc.items():
        L = []
        for a in d.values():
            a["position"] = round(a.pop("_pw") / a["impressions"], 1) if a["impressions"] else 0
            L.append(a)
        out[sp] = sorted(L, key=lambda a: -a["impressions"])
    return out


def todo_padel(queries):
    """'O que fazer esta semana' do padel: pesquisas de jogadores de padel (lista oficial) cruzadas com as nossas fichas."""
    try:
        pl = json.load(open("padel/data/players.json", encoding="utf-8"))
        pl = list(pl.values()) if isinstance(pl, dict) else pl
    except (OSError, ValueError):
        pl = []
    names = {}
    for p in pl:
        if isinstance(p, dict) and p.get("name") and p.get("id"):
            names[_norm(p["name"])] = p
    acts, seen = [], set()
    for x in queries:
        qn = _norm(x["q"]).replace(" padel", "").replace(" ranking", "").replace(" 2026", "").strip()
        p = names.get(qn)
        if not p:
            hits = [v for k, v in names.items() if set(qn.split()) and set(qn.split()) <= set(k.split()) and len(qn.split()) >= 2]
            if not hits and len(qn.split()) == 1:                # só o apelido: vale se houver um único jogador com esse apelido
                hits = [v for k, v in names.items() if k.split()[-1] == qn]
            p = hits[0] if len(hits) == 1 else None
        key = (p or {}).get("name") or x["q"]
        if key in seen or x["impressions"] < 10:
            continue
        if p:
            try:
                from padel.site import ppath
                url = ppath(p).replace(".html", "")
            except Exception:
                url = f"/padel/p/{p['id']}-" + "-".join(_norm(p["name"]).split())
            if x["position"] > 20:
                seen.add(key)
                acts.append({"kind": "page2", "q": x["q"], "who": p["name"], "impr": x["impressions"], "pos": x["position"], "url": url,
                             "text": f"\"{x['q']}\": {x['impressions']} pesquisas mas estamos na posição {str(x['position']).replace('.', ',')} (2.ª página ou pior). Reforçar a ficha de {p['name']}."})
            elif x["clicks"] == 0:
                seen.add(key)
                acts.append({"kind": "noclick", "q": x["q"], "who": p["name"], "impr": x["impressions"], "pos": x["position"], "url": url,
                             "text": f"\"{x['q']}\": aparecemos {x['impressions']} vezes na posição {str(x['position']).replace('.', ',')} e ninguém clicou. Título e topo da ficha de {p['name']}."})
        elif x["impressions"] >= 15:
            seen.add(key)
            acts.append({"kind": "missing", "q": x["q"], "impr": x["impressions"], "pos": x["position"],
                         "text": f"\"{x['q']}\": {x['impressions']} pesquisas e não temos uma página certa para isto."})
    order = {"playing": 0, "page2": 1, "noclick": 2, "missing": 3}
    acts.sort(key=lambda a: (order[a["kind"]], -a["impr"]))
    return acts[:20]


INSPECT_N = int(os.environ.get("GSC_INSPECT_N") or "100")


def _candidates(out):
    """Páginas a verificar: as que já aparecem no Google, os jogadores mais vistos no site e as páginas principais."""
    base = "https://beyond100tennis.com"
    seen, urls = set(), []

    def add(u):
        u = u.split("#")[0].split("?")[0]
        u = u[:-5] if u.endswith(".html") else u
        if u.startswith(base) and u not in seen:
            seen.add(u)
            urls.append(u)
    for u in ["/", "/padel/", "/rankings", "/results", "/players", "/padel/rankings-men", "/padel/rankings-women"]:
        add(base + u)
    try:
        pop = json.load(open("popular.json", encoding="utf-8"))
        for k, _ in sorted((pop.get("tennis") or {}).items(), key=lambda kv: -kv[1])[:40]:
            add(f"{base}/p/{k}")
        names = pop.get("padel_names") or {}
        for k, _ in sorted((pop.get("padel") or {}).items(), key=lambda kv: -kv[1])[:15]:
            if names.get(k):
                add(f"{base}/padel/p/{k}-{names[k]}")
    except (OSError, ValueError):
        pass
    for x in out.get("pages") or []:
        add(x["page"])
    return urls[:INSPECT_N]


def inspect(tok, out):
    """Inspeção de URL (grátis, 2000/dia): está no Google? se não, porquê. [{url, verdict, state, crawled, canon_google, canon_ours}]"""
    rows = []
    for u in _candidates(out):
        r = requests.post("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect", timeout=30,
                          headers={"Authorization": f"Bearer {tok}"}, json={"inspectionUrl": u, "siteUrl": SITE})
        if r.status_code != 200:
            rows.append({"url": u, "error": r.status_code})
            if r.status_code in (401, 403, 429):
                break
            continue
        ir = (r.json().get("inspectionResult") or {}).get("indexStatusResult") or {}
        rows.append({"url": u, "verdict": ir.get("verdict"), "state": ir.get("coverageState"), "crawled": (ir.get("lastCrawlTime") or "")[:10],
                     "canon_google": ir.get("googleCanonical"), "canon_ours": ir.get("userCanonical"), "robots": ir.get("robotsTxtState"),
                     "fetch": ir.get("pageFetchState")})
        time.sleep(0.2)
    ok = sum(1 for x in rows if x.get("verdict") == "PASS")
    print(f"Search Console: {ok} de {len(rows)} páginas no Google.")
    return {"ts": time.time(), "rows": rows}


def main():
    raw = os.environ.get("GSC_KEY")
    if not raw:
        print("Search Console: sem GSC_KEY (ignorado).")
        return
    try:
        tok = _token(json.loads(raw))
        qs = sorted(_query(tok, ["query"], 1000), key=lambda x: -x.get("impressions", 0))
        ps = sorted(_query(tok, ["page"], 1000), key=lambda x: -x.get("impressions", 0))
    except Exception as e:
        print("Search Console: falhou", type(e).__name__, str(e)[:200])
        return
    out = {"ts": time.time(), "queries": [{"q": x["keys"][0], "clicks": x.get("clicks", 0), "impressions": x.get("impressions", 0),
                                           "position": round(x.get("position", 0), 1)} for x in qs],
           "pages": [{"page": x["keys"][0], "clicks": x.get("clicks", 0), "impressions": x.get("impressions", 0)} for x in ps]}
    try:
        out["daily"] = daily(tok)
    except Exception as e:
        print("Search Console: evolução diária falhou", type(e).__name__)
    try:                                                    # 11/11/2026: ténis e padel separados (pesquisas, gráfico e ações)
        sq = split_queries(_query(tok, ["query", "page"], 5000))
        out["by_sport"] = {sp: {"queries": sq[sp]} for sp in ("tennis", "padel")}
        for sp in ("tennis", "padel"):
            try:
                out["by_sport"][sp]["daily"] = daily(tok, padel=(sp == "padel"))
            except Exception:
                pass
    except Exception as e:
        print("Search Console: separação ténis/padel falhou", type(e).__name__, str(e)[:200])
    try:
        out["todo"] = todo({"queries": (out.get("by_sport") or {}).get("tennis", {}).get("queries") or out["queries"], "pages": out["pages"]})
    except Exception as e:
        print("Search Console: lista de ações falhou", type(e).__name__, e)
    try:
        if out.get("by_sport"):
            out["by_sport"]["padel"]["todo"] = todo_padel(out["by_sport"]["padel"]["queries"])
    except Exception as e:
        print("Search Console: ações do padel falharam", type(e).__name__, e)
    try:
        try:
            old = json.load(open("gsc.json", encoding="utf-8"))
        except (OSError, ValueError):
            old = {}
        out["title_tests"] = title_tests(tok, out, old)
        print("Search Console: testes de títulos", {k: v.get("status") for k, v in out["title_tests"].items()})
    except Exception as e:
        print("Search Console: testes de títulos falharam", type(e).__name__, e)
    try:
        out["health"] = health()
    except Exception as e:
        print("Saúde do site falhou", type(e).__name__)
    try:
        out["index"] = inspect(tok, out)
    except Exception as e:
        print("Search Console: inspeção falhou", type(e).__name__, str(e)[:200])
    with open("gsc.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Search Console: {len(qs)} pesquisas, {len(ps)} páginas; top: {[x['q'] for x in out['queries'][:5]]}")


if __name__ == "__main__":
    main()
