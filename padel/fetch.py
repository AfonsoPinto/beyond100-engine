"""Beyond Padel: sincroniza dados da Padel API (padelapi.org, plano gratuito: 2.000 pedidos/dia, 10/min) para padel/data/.
Corre a cada atualização com um teto de pedidos (PADEL_MAX_REQ, 20) e retoma onde ficou na seguinte.
Prioridade: torneios a decorrer > torneios acabados há pouco > próximos > rankings > jogadores > campeões anteriores > notícias > histórico."""
import json
import os
import time

import requests

BASE = "https://padelapi.org/api"
DATA = os.path.join(os.path.dirname(__file__), "data")
LEVELS = "major,p1,p2,finals,fip_platinum,fip_gold,fip_silver"
MAX_REQ = int(os.environ.get("PADEL_MAX_REQ") or "20")
GAP_S = float(os.environ.get("PADEL_GAP_S") or "6.3")           # 10 pedidos por minuto
DAY = 86400


class Budget(Exception):
    pass


class Api:
    def __init__(self):
        self.key = os.environ.get("PADEL_API_KEY")
        self.n = 0
        self.last = 0.0
        self.log = []

    def get(self, path, **params):
        if not self.key:
            raise Budget("sem PADEL_API_KEY")
        if self.n >= MAX_REQ:
            raise Budget("teto de pedidos desta execução")
        wait = GAP_S - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.time()
        self.n += 1
        r = requests.get(BASE + path, params=params, timeout=40,
                         headers={"Authorization": f"Bearer {self.key}", "Accept": "application/json",
                                  "User-Agent": "Beyond100/0.1 (beyond100tennis.com)"})
        self.log.append([path, r.status_code] + ([r.text[:200]] if r.status_code != 200 else []))
        if r.status_code == 429:
            raise Budget("429 da API")
        if r.status_code != 200:
            return None
        return r.json()

    def all_pages(self, path, max_pages=10, **params):
        out, page = [], 1
        while page <= max_pages:
            j = self.get(path, per_page=50, page=page, **params)
            if not j:
                break
            out += j.get("data") or []
            meta = j.get("meta") or {}
            if page >= int(meta.get("last_page") or 1):
                break
            page += 1
        return out


def load(name, default):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(name, obj):
    os.makedirs(os.path.dirname(os.path.join(DATA, name)), exist_ok=True)
    tmp = os.path.join(DATA, name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, os.path.join(DATA, name))


def load_matches():
    """Jogos guardados um ficheiro por torneio (padel/data/matches/<id>.json): cada execução só reescreve os torneios que mudaram."""
    out = {}
    d = os.path.join(DATA, "matches")
    if os.path.isdir(d):
        for fn in os.listdir(d):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(d, fn), encoding="utf-8") as f:
                        for m in json.load(f):
                            out[str(m["id"])] = m
                except (OSError, ValueError):
                    pass
    old = load("matches.json", {})                     # formato antigo (um ficheiro só): migra
    for k, m in old.items():
        out.setdefault(k, m)
    return out


SLIM = ("self", "url", "watchability", "started_time", "started_time_local", "duration", "connections")


def save_matches(matches, dirty):
    if os.path.exists(os.path.join(DATA, "matches.json")):
        dirty = dirty | {str(m.get("tid")) for m in matches.values()}
    for tid in dirty:
        rows = []
        for m in matches.values():
            if str(m.get("tid")) == tid:
                m = {k: v for k, v in m.items() if k not in SLIM}
                for team in ("team_1", "team_2"):
                    for p in ((m.get("players") or {}).get(team) or []):
                        for k in ("self", "connections"):
                            p.pop(k, None)
                rows.append(m)
        rows.sort(key=lambda m: (m.get("category") or "", -(m.get("round") or 0), m.get("index") or 0))
        save(os.path.join("matches", f"{tid}.json"), rows)
    if os.path.exists(os.path.join(DATA, "matches.json")):
        os.remove(os.path.join(DATA, "matches.json"))


EDGE = (os.environ.get("SITE_URL") or "https://beyond100tennis.com").rstrip("/") + "/api/padel/matches"


def edge_scores(live, matches, dirty_t, max_calls=6):
    """Junta os resultados frescos dos torneios a decorrer, lidos pela função da Cloudflare do site."""
    n = calls = 0
    dates = [day()] + ([day(-1)] if time.gmtime().tm_hour < 6 else [])
    for t in live:
        for d in dates:
            if calls >= max_calls:
                return n
            calls += 1
            try:
                r = requests.get(f"{EDGE}/{t['id']}", params={"date": d}, timeout=20, headers={"User-Agent": "Beyond100/0.1 (update)"})
                if r.status_code != 200:
                    continue
                rows = (r.json() or {}).get("matches") or []
            except Exception as e:
                print("Padel edge:", t.get("id"), type(e).__name__)
                continue
            for x in rows:
                m = matches.get(str(x.get("id")))
                if not m:
                    continue
                upd = {k: x.get(k) for k in ("status", "score", "winner", "court", "court_order", "schedule_label") if x.get(k) is not None}
                if any(m.get(k) != v for k, v in upd.items()):
                    m.update(upd)
                    dirty_t.add(str(t["id"]))
                    n += 1
    return n


def day(offset=0):
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() + offset * DAY))


def run():
    try:                                                               # highlights oficiais (feeds públicos do YouTube, sem quota)
        from padel import highlights
        highlights.sync()
    except Exception as e:
        print("Padel highlights falharam:", type(e).__name__, e)
    api = Api()
    st = load("state.json", {})
    tours = load("tournaments.json", {})
    matches = load_matches()
    dirty_t = set()
    players = load("players.json", {})
    ranks = load("rankings.json", {})
    editions = load("editions.json", {})
    news = load("news.json", {})
    videos = load("videos.json", {})
    entries = load("entries.json", {})
    race = load("race.json", {})
    elo = load("elo.json", {})
    now = time.time()
    changed = set()

    def put_matches(rows, tid):
        for m in rows:
            m["tid"] = tid
            m.pop("tournament", None)
            matches[str(m["id"])] = m
        dirty_t.add(str(tid))

    try:
        # 1) lista de torneios (janela de -200 a +60 dias), de 6 em 6 horas
        if now - st.get("tours_ts", 0) > 6 * 3600:
            rows = api.all_pages("/tournaments", max_pages=8, level=LEVELS, after_date=day(-200), before_date=day(60))
            for t in rows:
                old = tours.get(str(t["id"])) or {}
                t["_synced"] = old.get("_synced", 0)
                t["_full"] = old.get("_full", False)
                tours[str(t["id"])] = t
            st["tours_ts"] = now
            changed.add("tournaments")
        tl = sorted(tours.values(), key=lambda t: t.get("start_date") or "")
        live = [t for t in tl if t.get("status") == "live" or (t.get("start_date", "") <= day() <= t.get("end_date", ""))]
        # 1b) resultados de hoje de TODOS os torneios a decorrer, pela Cloudflare (o mesmo caminho do site, cache de 5 min):
        #     rápido e sem a espera de 6 s por pedido; só atualiza jogos que já conhecemos (estado, resultado, vencedor, court, hora)
        fresh = edge_scores(live, matches, dirty_t)
        if fresh:
            print(f"Padel: {fresh} jogos atualizados pela Cloudflare.")
        api.last = time.time()                                         # dá folga ao limite de 10/min antes dos pedidos diretos
        # 2) torneios a decorrer: jogos novos (quadro a avançar) — leitura incremental a cada 3 h por torneio;
        #    os resultados já vieram pela Cloudflare
        for t in [t for t in live if not t.get("_full") or now - t.get("_synced", 0) > float(os.environ.get("PADEL_LIVE_FULL_H") or 3) * 3600]:
            since = t.get("_synced")
            params = {"updated_after": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(since - 600))} if since and t.get("_full") else {}
            rows = api.all_pages(f"/tournaments/{t['id']}/matches", max_pages=6, **params)
            put_matches(rows, t["id"])
            t["_synced"], t["_full"] = now, True
            changed.add("tournaments")
        # 3) acabados nos últimos 4 dias e ainda não lidos depois de acabar: leitura completa final
        for t in [t for t in tl if t.get("status") == "finished" and t.get("end_date", "") >= day(-4)
                  and t.get("_synced", 0) < _ts(t.get("end_date")) + DAY]:
            put_matches(api.all_pages(f"/tournaments/{t['id']}/matches", max_pages=6), t["id"])
            t["_synced"], t["_full"] = now, True
            changed.add("tournaments")
        # 4) próximos (começam nos próximos 3 dias): quadro e horários, de 6 em 6 horas
        for t in [t for t in tl if t.get("status") == "pending" and day() <= t.get("start_date", "") <= day(3)
                  and now - t.get("_synced", 0) > 6 * 3600]:
            put_matches(api.all_pages(f"/tournaments/{t['id']}/matches", max_pages=4), t["id"])
            t["_synced"] = now
            changed.add("tournaments")
        # 4c) torneios dos próximos 10 dias: edições anteriores (campeões em título) uma vez, e lista de inscritos
        #     (com cabeças de série) uma vez por dia, uma página por execução (cabe no teto de pedidos)
        for t in [t for t in tl if t.get("status") == "pending" and day() <= t.get("start_date", "") <= day(10)]:
            tid = str(t["id"])
            if tid not in editions:
                editions[tid] = api.all_pages(f"/tournaments/{tid}/editions", max_pages=1)
                changed.add("editions")
            e = entries.get(tid) or {}
            if e.get("next") or now - e.get("ts", 0) > DAY:
                page = e.get("next") or 1
                j = api.get(f"/tournaments/{tid}/players", per_page=50, page=page)
                if j:
                    rows = (e.get("rows") if page > 1 else []) or []
                    rows += [{k: x.get(k) for k in ("id", "name", "nationality", "ranking", "points", "draw", "position")}
                             | {"pair": ((x.get("connections") or {}).get("pair") or "").rsplit("/", 1)[-1]} for x in j.get("data") or []]
                    last = int((j.get("meta") or {}).get("last_page") or 1)
                    entries[tid] = {"ts": now if page >= last else e.get("ts", 0), "rows": rows, "next": page + 1 if page < last else None}
                    changed.add("entries")
        # 4b) vídeos (transmissões de cada court por dia, no YouTube oficial): Premier Padel a decorrer de 6 em 6 h
        #     e acabados há menos de 10 dias uma última vez; os FIP Silver/Gold não costumam ter
        for t in [t for t in tl if (t.get("level") or "") in ("major", "p1", "p2", "finals") and
                  (t.get("status") == "live" or (t.get("status") == "finished" and t.get("end_date", "") >= day(-10)))]:
            v = videos.get(str(t["id"])) or {}
            due = 2 * 3600 if t.get("status") == "live" else (0 if v.get("ts", 0) < _ts(t.get("end_date")) + DAY else 10 ** 9)
            if now - v.get("ts", 0) > due:
                rows = api.all_pages(f"/tournaments/{t['id']}/videos", max_pages=2)
                videos[str(t["id"])] = {"ts": now, "rows": [{k: x.get(k) for k in ("id", "name", "url", "photo_url", "type", "started_at")} for x in rows]}
                changed.add("videos")
        # 5) rankings oficiais (semanais): top 500 de cada categoria, uma página por vez
        for cat in ("men", "women"):
            r = ranks.get(cat) or {}
            if now - r.get("ts", 0) > DAY or r.get("next_page"):
                page = r.get("next_page") or 1
                while page <= 10:
                    j = api.get("/rankings", category=cat, per_page=50, page=page)
                    if not j:
                        break
                    rows = j.get("data") or []
                    if page == 1:
                        r = {"rows": [], "date": (rows[0] if rows else {}).get("date")}
                    r["rows"] = [x for x in r.get("rows", []) if x.get("ranking") not in {y.get("ranking") for y in rows}] + rows
                    last = int((j.get("meta") or {}).get("last_page") or 1)
                    page += 1
                    r["next_page"] = page if page <= min(10, last) else None
                    ranks[cat] = r
                    changed.add("rankings")
                    if not r["next_page"]:
                        r["ts"] = now
                        break
        # 5b) ranking Race (corrida ao Finals): top 50 de cada categoria, uma vez por dia (2 pedidos)
        for cat in ("men", "women"):
            r = race.get(cat) or {}
            if now - r.get("ts", 0) > DAY:
                j = api.get("/rankings", category=cat, type="race", per_page=50, page=1)
                if j and j.get("data"):
                    race[cat] = {"ts": now, "date": j["data"][0].get("date"),
                                 "rows": [{k: x.get(k) for k in ("id", "name", "nationality", "ranking", "ranking_diff", "points")} for x in j["data"]]}
                    changed.add("race")
        # 5c) ranking Elo (força de jogo, grátis): top 200 de cada categoria, uma vez por dia, uma página por execução (8 pedidos/dia)
        for cat in ("men", "women"):
            r = elo.get(cat) or {}
            if now - r.get("ts", 0) > DAY or r.get("next"):
                page = r.get("next") or 1
                j = api.get("/rankings", category=cat, type="elo", per_page=50, page=page)
                if j and j.get("data"):
                    rows = [{k: x.get(k) for k in ("id", "name", "ranking", "points")} for x in j["data"]]
                    keep = [] if page == 1 else [x for x in r.get("rows", []) if x.get("id") not in {y["id"] for y in rows}]
                    last = min(4, int((j.get("meta") or {}).get("last_page") or 1))
                    elo[cat] = {"ts": now if page >= last else r.get("ts", 0), "date": j["data"][0].get("date") if page == 1 else r.get("date"),
                                "rows": keep + rows, "next": page + 1 if page < last else None}
                    changed.add("elo")
                break                                                   # uma categoria/página por execução
        # 6) fichas dos jogadores que aparecem nos jogos (idade, altura, mão, lado, Elo, naturalidade), até 6 por execução
        seen = []
        for m in sorted(matches.values(), key=lambda m: m.get("played_at") or "", reverse=True):
            for team in ("team_1", "team_2"):
                for p in ((m.get("players") or {}).get(team) or []):
                    pid = str(p.get("id"))
                    if pid and pid not in seen and now - (players.get(pid) or {}).get("_ts", 0) > 14 * DAY:
                        seen.append(pid)
        for pid in seen[:6]:
            j = api.get(f"/players/{pid}")
            if j:
                p = j.get("data", j)
                p["_ts"] = now
                players[pid] = p
                changed.add("players")
        # 6b) top 200 de cada categoria: parceiros ao longo da carreira (com datas) e rankings Race e Elo, de 30 em 30 dias,
        #     2 jogadores por execução (4 pedidos)
        top = sorted([x for cat in ("men", "women") for x in ((ranks.get(cat) or {}).get("rows") or []) if (x.get("ranking") or 999) <= 200],
                     key=lambda x: x.get("ranking") or 999)
        due = [str(x["id"]) for x in top if now - (players.get(str(x["id"])) or {}).get("_pairs_ts", 0) > 30 * DAY]
        for pid in due[:2]:
            j = api.get(f"/players/{pid}/pairs", per_page=50)
            k = api.get(f"/players/{pid}/rankings")
            p = players.setdefault(pid, {"id": int(pid)})
            if j:
                p["pairs_hist"] = [{"id": x.get("id"), "status": x.get("status"), "first": x.get("first_match_at"), "last": x.get("last_match_at"),
                                    "points": x.get("points"), "players": [{"id": q.get("id"), "name": q.get("name"), "short_name": q.get("short_name"),
                                                                            "nationality": q.get("nationality")} for q in x.get("players") or []]}
                                   for x in (j.get("data") or [])][:30]
            for x in (k if isinstance(k, list) else (k or {}).get("data") or []):
                if x.get("type") in ("race", "elo"):
                    p[x["type"]] = {"ranking": x.get("ranking"), "points": x.get("points"), "date": x.get("date")}
            p["_pairs_ts"] = now
            changed.add("players")
        # 7) edições anteriores (campeões de anos passados), uma vez por torneio da janela
        for t in [t for t in tl if str(t["id"]) not in editions and t.get("start_date", "") >= day(-30)][:3]:
            editions[str(t["id"])] = api.all_pages(f"/tournaments/{t['id']}/editions", max_pages=1)
            changed.add("editions")
        # 8) notícias dos torneios a decorrer, de 12 em 12 horas
        for t in [t for t in tl if t.get("status") == "live"]:
            n = news.get(str(t["id"])) or {}
            if now - n.get("ts", 0) > 12 * 3600:
                j = api.get(f"/tournaments/{t['id']}/news", language="en")
                news[str(t["id"])] = {"ts": now, "rows": (j or {}).get("data") or []}
                changed.add("news")
        # 9) histórico: torneios acabados ainda nunca lidos (dos mais recentes para os mais antigos), com o que sobrar do teto
        for t in sorted([t for t in tl if t.get("status") == "finished" and not t.get("_full")],
                        key=lambda t: t.get("end_date") or "", reverse=True):
            put_matches(api.all_pages(f"/tournaments/{t['id']}/matches", max_pages=6), t["id"])
            t["_synced"], t["_full"] = now, True
            changed.add("tournaments")
    except Budget as e:
        print("Padel:", e)
    save_matches(matches, dirty_t)
    for name, obj in (("tournaments", tours), ("players", players), ("rankings", ranks),
                      ("editions", editions), ("news", news), ("videos", videos), ("entries", entries), ("race", race), ("elo", elo)):
        if name in changed:
            save(name + ".json", obj)
    st["last_run"] = now
    st["last_requests"] = api.n
    st["last_log"] = api.log[-30:]
    days = st.setdefault("req_by_day", {})
    days[day()] = days.get(day(), 0) + api.n
    st["req_by_day"] = dict(sorted(days.items())[-14:])
    save("state.json", st)
    print(f"Padel: {api.n} pedidos · {len(tours)} torneios · {len(matches)} jogos · {len(players)} fichas · "
          f"rankings {', '.join(f'{k}={len(v.get('rows', []))}' for k, v in ranks.items())}")


def _ts(d):
    try:
        return time.mktime(time.strptime(d, "%Y-%m-%d"))
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    run()
