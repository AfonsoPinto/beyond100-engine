"""Notícias automáticas da Beyond100: pesquisa na web, verifica e prepara 1 post por dia (cartão + legenda) para a fila normal.

Travas (sem aprovação humana, por isso são rígidas):
  - desligado por omissão: NEWS_ENABLED=1 (variável do GitHub, ou no admin > Definições);
  - no máximo NEWS_MAX_PER_DAY (1) por dia e uma pesquisa de NEWS_SCAN_HOURS em NEWS_SCAN_HOURS horas (20);
  - o código, e não a IA, confere as fontes: precisa de uma fonte oficial (ATP, WTA, ITF, Grand Slams...) ou de 2 meios de comunicação
    reconhecidos independentes; lesões e retiros exigem fonte oficial e pelo menos 2 fontes;
  - o acontecimento tem de ser dos últimos 3 dias; não repete jogadores já noticiados nos últimos 14 dias;
  - uma segunda chamada à IA, também com pesquisa web, volta a verificar cada afirmação; só publica se a resposta for 'pass';
  - as notícias têm SEMPRE foto licenciada de um dos jogadores (se não houver nenhuma, a história é recusada);
  - cartão e legenda só usam o texto verificado (sem inventar); as fontes ficam em news_log.json (visível no admin).
Uso: python news_scan.py out [--force] [--dry]
"""
import datetime
import json
import os
import re
import sys
import time
from urllib.parse import urlparse

import requests

import captions
from captions import API_URL, MODEL, _credit_check, _record

LOG = "news_log.json"
POSTS_FILE = "posts.json"
OFFICIAL = {"atptour.com", "wtatennis.com", "itftennis.com", "rolandgarros.com", "wimbledon.com", "usopen.org", "ausopen.com",
            "daviscup.com", "billiejeankingcup.com", "atpchallengertour.com", "olympics.com",
            # 11/11/2026: federações nacionais (fonte oficial para os seus jogadores)
            "fft.fr", "lta.org.uk", "usta.com", "tennis.com.au", "rfet.es", "federtennis.it", "dtb-tennis.de", "tennisportugal.pt",
            "cbt-tenis.com.br", "tenniscanada.com", "tennis.de", "tennis.nl", "tennisbelgium.be", "swisstennis.ch", "tennis.be"}
MAJOR = {"reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "theguardian.com", "lequipe.fr", "espn.com", "tennis.com",
         "skysports.com", "eurosport.com", "nytimes.com", "washingtonpost.com", "marca.com", "as.com", "tennismajors.com",
         # 11/11/2026: a lista era curta e recusava histórias verdadeiras (Hijikata d. Djokovic com ABC e Dawn, Tubello, Naná Silva)
         "abc.net.au", "cnn.com", "cnnbrasil.com.br", "independent.co.uk", "telegraph.co.uk", "elpais.com", "lemonde.fr", "lefigaro.fr",
         "gazzetta.it", "corrieredellosport.it", "mundodeportivo.com", "globo.com", "dawn.com", "theathletic.com", "nbcsports.com",
         "cbssports.com", "smh.com.au", "theage.com.au", "rtp.pt", "record.pt", "ojogo.pt", "abola.pt", "publico.pt", "francetvinfo.fr",
         "ubitennis.net", "ubitennis.com", "tennisnet.com", "puntodebreak.com", "tennisactu.net", "welovetennis.fr", "tennis365.com"}
CATS = {"comeback": "COMEBACK", "first_title": "FIRST TITLE", "ranking": "RISING", "retirement": "NEWS", "injury": "NEWS", "upset": "UPSET"}
SENSITIVE = {"retirement", "injury"}
TOOL = lambda n: {"type": "web_search_20250305", "name": "web_search", "max_uses": n}


def domain(url):
    h = (urlparse(url).hostname or "").lower()
    h = re.sub(r"^(www|m|amp)\.", "", h)
    parts = h.split(".")
    return ".".join(parts[-3:]) if len(parts) >= 3 and parts[-2] in ("co", "com", "net", "org", "gov", "edu", "ac") else ".".join(parts[-2:])


def source_ok(story):
    """Regra de fontes aplicada pelo código."""
    doms = {domain(u) for u in story.get("sources", []) if str(u).startswith("http")}
    off, maj = doms & OFFICIAL, doms & MAJOR
    if story.get("category") in SENSITIVE:
        return bool(off) and len(doms) >= 2
    return bool(off) or len(maj) >= 2


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def ask(system, user, searches, max_tokens=2500, model=None, feature="news"):
    model = model or MODEL
    key = os.environ["ANTHROPIC_API_KEY"]
    r = requests.post(API_URL, headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                      json={"model": model, "max_tokens": max_tokens, "system": system, "tools": [TOOL(searches)],
                            "messages": [{"role": "user", "content": user}]}, timeout=180)
    _credit_check(r)
    if r.status_code >= 400:
        print("Notícias: pesquisa indisponível:", r.status_code, r.text[:200].replace("\n", " "))
        return None
    j = r.json()
    _record(model, j.get("usage"), feature)
    text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None


RESEARCH = (
    "You are the news desk of Beyond100, a tennis account about players and tournaments beyond the top 100 (Challenger, ITF, WTA, ATP). "
    "Use web search (at most 3 searches) to find up to 2 genuinely newsworthy, VERIFIED stories from the last 48 hours in these categories: "
    "comeback (a return after a long absence or injury, or a first win back), first_title (a player's first title at a level), "
    "ranking (a player entering the top 100 or a big rise), upset (a surprising result with real context), "
    "retirement or injury (only when officially announced). Prefer players in the provided list, but any relevant story is welcome. "
    "Rules: the right person (check country/age; many players share names); every claim must be stated in your sources; official sources "
    "(atptour.com, wtatennis.com, itftennis.com, grand slam or tournament sites) are best, otherwise at least two independent major outlets; "
    "no rumours, opinions, predictions, personal-life details or health details beyond what is officially announced. "
    "Write in English, paraphrased (never copy sentences). headline: max 12 words, factual, no clickbait. summary: max 35 words, 1-2 sentences. "
    'Reply with JSON only: {"stories":[{"category":"comeback|first_title|ranking|upset|retirement|injury","headline":"...","summary":"...",'
    '"players":[{"name":"...","country":"..."}],"event_date":"YYYY-MM-DD","sources":["https://..."]}]}. If nothing solid, return {"stories":[]}.'
)
VERIFY = (
    "You are a strict fact-checker. You get a draft tennis news story (headline, summary, players, sources). Use web search (at most 3 searches) "
    "to check every claim independently: right person, right event, dates, numbers and wording. Reject anything unsupported, exaggerated, "
    "speculative, outdated (older than 3 days) or that reveals private details. Reply with JSON only: "
    '{"verdict":"pass|fail","problems":["..."]}. Use "pass" only if every claim is confirmed. '
    "If the input has official_rankings, those are the official ATP/WTA rankings: they are authoritative for ranking numbers, so a ranking "
    "claim that matches them is confirmed even if some media give a different number."
)


def official_ranks(names):
    """11/11/2026: ranking oficial (ESPN, já guardado em espn_rank.json) dos jogadores da notícia, para a verificação não falhar
    quando os jornais não concordam (caso Dart: 83 vs 84)."""
    import unicodedata
    plain = lambda t: "".join(c for c in unicodedata.normalize("NFKD", t or "") if not unicodedata.combining(c)).lower().strip()
    er = load("espn_rank.json", {})
    want = {plain(n) for n in names}
    out = []
    for lg in ("atp", "wta"):
        upd = er.get(f"{lg}_upd") or ""
        for x in er.get(lg) or []:
            if plain(x.get("n")) in want:
                out.append(f'{x["n"]}: {lg.upper()} No. {x["r"]}' + (f' (previous No. {x["prev"]})' if x.get("prev") else "") + (f", ranking of {upd}" if upd else ""))
    return out


def find_photo(players):
    """Foto licenciada de um dos jogadores da notícia: (caminho, crédito, nome) ou None. Tenta a que já existe e, se não, procura uma livre."""
    try:
        import fetch_photos
    except Exception:
        return None
    for p in players:
        name = p.get("name", "")
        if not name:
            continue
        try:
            key = fetch_photos.slug(name)
            path = os.path.join("photos", key + ".jpg")
            if not os.path.exists(path) and os.environ.get("FETCH_PHOTOS") == "1":
                path = fetch_photos.fetch_photo(name) or path
            if os.path.exists(path):
                credit = (load(os.path.join("photos", "credits.json"), {}) or {}).get(key + ".jpg")
                return path, credit, name
        except Exception as e:
            print("Notícias: foto de", name, "falhou:", type(e).__name__)
    return None


def candidates(limit=30):
    """Jogadores que acompanhámos nos últimos 3 dias (só para orientar a pesquisa)."""
    res = load("results.json", [])
    cut = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
    out, seen = [], set()
    for r in reversed(res if isinstance(res, list) else []):
        if (r.get("date") or "") < cut or r.get("q"):
            continue
        for k in ("p1", "p2"):
            p = r.get(k) or {}
            n = p.get("name")
            if n and n not in seen:
                seen.add(n)
                out.append(f"{n} ({p.get('country') or '?'}, rank {p.get('rank') or '?'}) - {r.get('tournament', '')}")
        if len(out) >= limit:
            break
    return out[:limit]


def main():
    out_dir = next((a for a in sys.argv[1:] if not a.startswith("--")), "out")
    force, dry = "--force" in sys.argv, "--dry" in sys.argv
    if os.environ.get("NEWS_ENABLED", "0").strip().lower() not in ("1", "true", "yes", "on") and not force:
        print("Notícias: desligadas (NEWS_ENABLED=1 para ligar).")
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Notícias: sem ANTHROPIC_API_KEY.")
        return 0
    log = load(LOG, {"items": []})
    today = datetime.date.today().isoformat()
    try:
        max_day = int(os.environ.get("NEWS_MAX_PER_DAY") or 1)
        gap_h = float(os.environ.get("NEWS_SCAN_HOURS") or 48)
    except ValueError:
        max_day, gap_h = 1, 20
    if not force:
        if sum(1 for i in log["items"] if i.get("date") == today and i.get("status") == "posted") >= max_day:
            print("Notícias: já houve notícia hoje.")
            return 0
        if time.time() - log.get("last_scan", 0) < gap_h * 3600:
            print("Notícias: pesquisa feita há pouco, salto.")
            return 0
    log["last_scan"] = time.time()
    cand = candidates()
    res = ask(RESEARCH, "Players we tracked in the last 3 days (name, country, ranking, tournament):\n" + "\n".join(cand or ["(none)"]), 3, feature="news-search")
    stories = (res or {}).get("stories") or []
    print(f"Notícias: {len(stories)} candidatas.")
    recent = {n.lower() for i in log["items"] if i.get("date", "") >= (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
              for n in i.get("players", [])}
    chosen = None
    for st in stories:
        why = ""
        cat, head, summ = st.get("category"), (st.get("headline") or "").strip(), (st.get("summary") or "").strip()
        names = [p.get("name", "") for p in st.get("players", []) if p.get("name")]
        try:
            age = (datetime.date.today() - datetime.date.fromisoformat(st.get("event_date", ""))).days
        except ValueError:
            age = 99
        if cat not in CATS or not head or not summ or not names:
            why = "dados incompletos"
        elif len(head.split()) > 16 or len(summ.split()) > 45:
            why = "texto demasiado longo"
        elif age > 3 or age < 0:
            why = "fora dos últimos 3 dias"
        elif not source_ok(st):
            why = "fontes insuficientes (precisa de fonte oficial ou 2 meios reconhecidos; lesões/retiros: oficial + 2)"
        elif any(n.lower() in recent for n in names):
            why = "jogador já noticiado nos últimos 14 dias"
        else:
            ph = find_photo(st.get("players", []))
            if not ph:
                why = "sem foto licenciada de nenhum dos jogadores (as notícias têm sempre foto)"
            else:
                st["_photo"] = ph
        if why:
            print(f"Notícia recusada ({head[:60]}): {why}.")
            log["items"].append({"date": today, "status": "rejected", "reason": why, "headline": head, "category": cat, "players": names, "sources": st.get("sources", [])})
            continue
        vin = {k: x for k, x in st.items() if k != "_photo"}
        orank = official_ranks(names)
        if orank:
            vin["official_rankings"] = orank
        v = ask(VERIFY, json.dumps(vin, ensure_ascii=False), 2, 1200, model=captions.FALLBACK_MODEL, feature="news-verify") or {}
        if v.get("verdict") != "pass":
            why = "verificação falhou: " + "; ".join(v.get("problems") or ["sem resposta"])[:200]
            print(f"Notícia recusada ({head[:60]}): {why}")
            log["items"].append({"date": today, "status": "rejected", "reason": why, "headline": head, "category": cat, "players": names, "sources": st.get("sources", [])})
            continue
        chosen = st
        break
    if not chosen:
        json.dump(log, open(LOG, "w", encoding="utf-8"), ensure_ascii=False, indent=1) if not dry else None
        print("Notícias: nada para publicar hoje.")
        return 0
    names = [p["name"] for p in chosen["players"] if p.get("name")]
    host_names = {"atptour.com": "ATP Tour", "wtatennis.com": "WTA", "itftennis.com": "ITF", "reuters.com": "Reuters", "apnews.com": "AP",
                  "bbc.com": "BBC", "bbc.co.uk": "BBC", "theguardian.com": "The Guardian", "lequipe.fr": "L'Équipe", "espn.com": "ESPN",
                  "tennis.com": "Tennis.com", "skysports.com": "Sky Sports", "eurosport.com": "Eurosport"}
    doms = []
    for u in chosen["sources"]:
        d_ = domain(u)
        if d_ not in doms:
            doms.append(d_)
    src_names = [host_names.get(x, x) for x in doms if x in OFFICIAL | MAJOR][:3]
    photo, credit, photo_name = chosen["_photo"]
    names = [photo_name] + [n for n in names if n != photo_name]
    slug = re.sub(r"[^a-z0-9]+", "-", names[0].lower()).strip("-")[:30]
    pid = f"news-{today}-{slug}"
    pdir = os.path.join(out_dir, "post")
    os.makedirs(pdir, exist_ok=True)
    png = os.path.join(pdir, pid + ".png")
    import news_card
    news_card.render_news({"badge": CATS[chosen["category"]], "headline": chosen["headline"], "summary": chosen["summary"],
                           "source": " · ".join(src_names), "photo": photo, "photo_credit": credit}, png)
    facts = {"category": chosen["category"], "headline": chosen["headline"], "summary": chosen["summary"],
             "players": [p for p in chosen["players"] if p.get("name")], "source_names": src_names}
    captions.save_caption(png, "news", facts)
    print("Notícia pronta:", png, "| fontes:", ", ".join(chosen["sources"]))
    if dry:
        return 0
    posts = load(POSTS_FILE, {})
    posts.setdefault(today, []).append({"id": pid, "score": 99, "reasons": ["news"], "file": pid + ".png"})
    json.dump(posts, open(POSTS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    log["items"].append({"date": today, "status": "posted", "headline": chosen["headline"], "summary": chosen["summary"], "category": chosen["category"],
                         "players": names, "sources": chosen["sources"], "post": pid})
    log["items"] = log["items"][-120:]
    json.dump(log, open(LOG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
