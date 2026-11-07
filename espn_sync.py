"""ESPN (grátis, sem chave, sem quota): quadros completos ATP/WTA, ordem de jogo com court e hora, campeão do ano anterior,
rankings ATP/WTA (top 150) e perfis de jogadores. Corre em cada atualização; nunca gasta pedidos da Live Tennis API.

Ficheiros:  espn.json          torneios a decorrer + todos os jogos de singulares (por jogar, a decorrer, terminados)
            espn_rank.json     rankings ATP/WTA (top 150) com pontos, posição anterior e tendência
            espn_players.json  perfis (altura, peso, mão, idade, ano de estreia), por id do ESPN
Os jogos terminados que ainda não temos entram no results.json (src="espn"); os que já temos ganham os tie-breaks.
Não é uma API oficial: se falhar, tudo continua como antes (estes ficheiros ficam simplesmente desatualizados)."""
import datetime as dt
import json
import os
import re
import time
from collections import Counter

from espn import _keys, norm

SB = "https://site.api.espn.com/apis/site/v2/sports/tennis/{lg}/scoreboard"
RK = "https://site.api.espn.com/apis/site/v2/sports/tennis/{lg}/rankings"
ATH = "https://site.web.api.espn.com/apis/common/v3/sports/tennis/{lg}/athletes/{aid}"
FILE, RANK_FILE, PROF_FILE = "espn.json", "espn_rank.json", "espn_players.json"
ID_BASE = 900_000_000
FIX_CC = {"ser": "srb", "rom": "rou", "tpo": "tpe"}       # códigos do ESPN que diferem dos do resto do site                         # ids dos jogos importados do ESPN (não colidem com os da Live Tennis API)
FRESH_H = 6                                   # dados mais velhos do que isto não são usados no site
RANK_EVERY_H = 12
PROF_PER_RUN = int(os.environ.get("ESPN_PROFILES_PER_RUN") or "30")
PROF_MAX_AGE_D = 45


def _load(p, d):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def _save(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))


def _get(url, **params):
    import requests
    try:
        r = requests.get(url, params=params or None, headers={"User-Agent": "Mozilla/5.0 (compatible; Beyond100/0.1)"}, timeout=25)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"ESPN: {url.split('/tennis/')[-1][:60]} indisponível ({type(e).__name__}).")
        return None


# ---------- rondas: nomes do ESPN -> os nossos ----------
def round_map(rounds):
    main = [int(m.group(1)) for r in rounds for m in [re.match(r"Round (\d+)$", r or "")] if m]
    top = max(main) if main else 0
    def qn(r):
        m = re.search(r"(\d+)", r)
        return 99 if "final" in r.lower() else int(m.group(1)) if m else 50
    quals = sorted({r for r in rounds if (r or "").lower().startswith("qualif")}, key=qn)

    def conv(r):
        rl = (r or "").lower()
        if rl.startswith("qualif"):
            back = len(quals) - 1 - quals.index(r)
            return {0: "Qualifying final", 1: "Qualifying semi-finals", 2: "Qualifying quarter-finals"}.get(back, f"Qualifying round {quals.index(r) + 1}")
        if rl.startswith("quarter"):
            return "Quarter-finals"
        if rl.startswith("semi"):
            return "Semi-finals"
        if rl.startswith("final"):
            return "Final"
        m = re.match(r"round (\d+)$", rl)
        if m and top:
            return f"1/{8 * 2 ** (top - int(m.group(1)))}-finals"
        return r or ""
    return conv


def parse(lg, j):
    events, matches = [], []
    for ev in (j or {}).get("events") or []:
        venue = ((ev.get("venue") or {}).get("displayName") or "")
        e = {"eid": str(ev.get("id")), "lg": lg, "name": ev.get("name") or "", "start": ev.get("date"), "end": ev.get("endDate"),
             "city": venue.split(",")[0].strip(), "prev": {}}
        for pw in ev.get("previousWinners") or []:
            typ = ((pw.get("type") or {}).get("text") or "")
            if "Singles" in typ and pw.get("displayName"):
                e["prev"]["women" if "Women" in typ else "men"] = pw["displayName"]
        n = 0
        for g in ev.get("groupings") or []:
            gname = ((g.get("grouping") or {}).get("displayName") or "")
            if "Singles" not in gname:
                continue
            gender = "women" if "Women" in gname else "men"
            comps = g.get("competitions") or []
            conv = round_map({(c.get("round") or {}).get("displayName") for c in comps})
            for c in comps:
                cp = c.get("competitors") or []
                if len(cp) != 2:
                    continue
                st = (c.get("status") or {}).get("type") or {}
                raw = (c.get("round") or {}).get("displayName") or ""
                p = []
                for x in cp:
                    a = x.get("athlete") or {}
                    cc = ((re.search(r"/([a-z]{3})\.png", (a.get("flag") or {}).get("href") or "") or [None, ""])[1])
                    cc = FIX_CC.get(cc, cc)
                    nm = a.get("displayName") or ""
                    if re.fullmatch(r"(tbd|tba|bye|qualifier|lucky loser|\?+)", nm.strip().lower()):
                        nm = ""                       # adversário ainda por definir
                    p.append({"n": nm, "c": cc, "aid": str(x.get("id") or a.get("id") or "") if nm else ""})
                ls = [x.get("linescores") or [] for x in cp]
                matches.append({"cid": str(c.get("id")), "eid": e["eid"], "lg": lg, "g": gender, "rr": raw, "round": conv(raw),
                                "q": raw.lower().startswith("qualif"), "t": c.get("startDate") or c.get("date") or "",
                                "tv": bool(c.get("timeValid")), "court": (c.get("venue") or {}).get("court") or "",
                                "state": st.get("state"), "status": st.get("name"), "done": bool(st.get("completed")), "p": p,
                                "s": [[int(float(v.get("value") or 0)) for v in l] for l in ls],
                                "tb": [[v.get("tiebreak") for v in l] for l in ls],
                                "w": 1 if cp[0].get("winner") else 2 if cp[1].get("winner") else 0})
                n += 1
        if n:
            events.append(e)
    return events, matches


# ---------- o nosso nome do torneio e o circuito (WTA 125 = 'challenger' feminino, como na Live Tennis API) ----------
def _pair_keys(a, b):
    return [frozenset((x, y)) for x in _keys(a) for y in _keys(b)]


def _index_known():
    import webapp
    idx = {}
    cut = (dt.date.today() - dt.timedelta(days=21)).isoformat()
    for r in _load("results.json", []):
        if r.get("date", "") >= cut and r.get("tour") in ("atp", "wta", "challenger"):
            for k in _pair_keys(r["p1"]["name"], r["p2"]["name"]):
                idx[k] = (webapp.base_tournament(r.get("tournament", "")), r.get("tour"), r.get("surface"))
    for fn in ("fixtures.json", "upcoming.json"):
        for u in _load(fn, {}).get("matches", []):
            if u.get("tour") in ("atp", "wta", "challenger") and u.get("tp"):
                for k in _pair_keys(u["p1"]["name"], u["p2"]["name"]):
                    idx.setdefault(k, (re.sub(r"^(ATP|WTA)\s+", "", u["tp"]), u.get("tour"), u.get("surface")))
    return idx


def name_events(events, matches):
    idx = _index_known()
    votes = {e["eid"]: Counter() for e in events}
    for m in matches:
        if m["p"][0]["n"] and m["p"][1]["n"]:
            for k in _pair_keys(m["p"][0]["n"], m["p"][1]["n"]):
                if k in idx:
                    votes[m["eid"]][idx[k]] += 1
                    break
    for e in events:
        v = votes.get(e["eid"])
        tp, tour, surf = v.most_common(1)[0][0] if v else (e["city"] or e["name"], e["lg"], None)
        e["tp"], e["tour"] = tp, (tour if tour in ("atp", "wta", "challenger") else e["lg"])
        if surf:
            e["surface"] = surf


# ---------- rankings e perfis ----------
def refresh_rankings():
    old = _load(RANK_FILE, {})
    if time.time() - old.get("ts", 0) < RANK_EVERY_H * 3600:
        return old
    out = {"ts": time.time()}
    for lg in ("atp", "wta"):
        j = _get(RK.format(lg=lg))
        rk = (((j or {}).get("rankings") or [{}])[0])
        rows = []
        for x in rk.get("ranks") or []:
            a = x.get("athlete") or {}
            if not a.get("displayName") or not isinstance(x.get("current"), int):
                continue
            rows.append({"r": x["current"], "prev": x.get("previous"), "pts": int(x.get("points") or 0), "tr": x.get("trend") or "",
                         "n": a["displayName"], "c": FIX_CC.get((a.get("citizenshipCountry") or "").lower(), (a.get("citizenshipCountry") or "").lower()), "aid": str(a.get("id") or ""), "age": a.get("age")})
        if rows:
            out[lg] = rows
            out[lg + "_upd"] = (rk.get("update") or "")[:10]
        elif old.get(lg):
            out[lg], out[lg + "_upd"] = old[lg], old.get(lg + "_upd", "")
    if out.get("atp") or out.get("wta"):
        _save(RANK_FILE, out)
        print(f"ESPN rankings: ATP {len(out.get('atp') or [])}, WTA {len(out.get('wta') or [])}.")
        return out
    return old


def _dob(s, age):
    """'1/6/2001' é ambíguo (D/M ou M/D): só aceita a data se apenas uma das leituras bater com a idade dada pelo ESPN."""
    try:
        a, b, y = (int(x) for x in s.split("/"))
    except (ValueError, AttributeError):
        return None
    t = dt.date.today()
    ok = []
    for d, m in ((a, b), (b, a)):
        try:
            x = dt.date(y, m, d)
        except ValueError:
            continue
        if age is None or t.year - x.year - ((t.month, t.day) < (x.month, x.day)) == age:
            ok.append(x.isoformat())
    ok = sorted(set(ok))
    return ok[0] if len(ok) == 1 else None


def refresh_profiles(matches, ranks):
    data = _load(PROF_FILE, {})
    now = time.time()
    want = []
    for m in sorted(matches, key=lambda m: m["state"] != "in"):            # primeiro quem está a jogar
        for p in m["p"]:
            if p["aid"] and p["n"] and now - (data.get(p["aid"]) or {}).get("ts", 0) > PROF_MAX_AGE_D * 86400 and (m["lg"], p["aid"]) not in want:
                want.append((m["lg"], p["aid"]))
    got = 0
    for lg, aid in want[:PROF_PER_RUN]:
        j = _get(ATH.format(lg=lg, aid=aid))
        a = (j or {}).get("athlete") or {}
        if not a.get("displayName"):
            data[aid] = {"ts": now, "miss": 1}
            continue
        h = re.match(r"(\d+)'\s*(\d+)", a.get("displayHeight") or "")
        w = re.match(r"(\d+)", a.get("displayWeight") or "")
        age = a.get("age") if isinstance(a.get("age"), int) else None
        data[aid] = {"ts": now, "n": a["displayName"], "h": round(int(h.group(1)) * 30.48 + int(h.group(2)) * 2.54) if h else None,
                     "kg": round(int(w.group(1)) * 0.4536) if w else None, "hand": ((a.get("hand") or {}).get("abbreviation") or "")[:1] or None,
                     "debut": a.get("debutYear"), "age": age, "age_ts": now, "bd": _dob(a.get("displayDOB"), age)}
        got += 1
    if got:
        _save(PROF_FILE, data)
        print(f"ESPN perfis: +{got} (total {len(data)}).")


# ---------- jogos terminados -> results.json ----------
def _drop_dupes(results):
    """Tira as cópias do ESPN de jogos que já temos da API com os nomes por outra ordem (ex.: "Cheuk Ying Shek" / "Shek Ying Cheuk").
    Mesmo dia, mesmo resultado e o mesmo par de jogadores. Fica a linha da API."""
    def sig(r):
        g = r.get("games") or [[], []]
        return (r.get("date", "")[:10], tuple(sorted((tuple(g[0]), tuple(g[1])))))
    api = {}
    for r in results:
        if r.get("src") != "espn":
            for k in _pair_keys(r["p1"]["name"], r["p2"]["name"]):
                api.setdefault((k,) + sig(r), True)
    drop = [i for i, r in enumerate(results) if r.get("src") == "espn"
            and any((k,) + sig(r) in api for k in _pair_keys(r["p1"]["name"], r["p2"]["name"]))]
    for i in reversed(drop):
        del results[i]
    return len(drop)


def import_results(events, matches, prev=None):
    import result_card as rc
    import extras
    import webapp
    ev = {e["eid"]: e for e in events}
    results = rc.load_results()
    dupes = _drop_dupes(results)
    rk = rank_lookup()
    names = {}
    for r in results:
        for k in _pair_keys(r["p1"]["name"], r["p2"]["name"]):
            names.setdefault(k, []).append(r)
    surf = {}
    for r in results:
        if r.get("surface"):
            surf.setdefault(webapp.slugify(webapp.base_tournament(r.get("tournament", ""))), r["surface"])
    new, tbs = [], 0
    for m in matches:
        a, b = m["p"][0]["n"], m["p"][1]["n"]
        if not (m["done"] and m["status"] == "STATUS_FINAL" and m["w"] in (1, 2) and a and b and m["s"][0]):
            continue
        e = ev.get(m["eid"]) or {}
        day = (m["t"] or "")[:10] or time.strftime("%Y-%m-%d", time.gmtime())
        tsl = webapp.slugify(e.get("tp") or "")
        have = None
        for k in _pair_keys(a, b):
            for r in names.get(k, []):
                try:
                    near = abs((dt.date.fromisoformat(r.get("date", "")[:10]) - dt.date.fromisoformat(day)).days) <= 3
                except ValueError:
                    near = False
                if webapp.slugify(webapp.base_tournament(r.get("tournament", ""))) == tsl or near:
                    have = r
                    break
            if have:
                break
        tb = m["tb"] if any(v is not None for l in m["tb"] for v in l) else None
        if have:
            if tb and not have.get("tb") and len(have.get("games", [[]])[0]) == len(m["s"][0]):
                flip = not (_keys(have["p1"]["name"]) & _keys(a))
                have["tb"] = [tb[1], tb[0]] if flip else tb
                tbs += 1
            continue
        row = {"_cid": m["cid"], "id": ID_BASE + int(m["cid"]), "date": day, "tournament": e.get("tp") or e.get("name", ""), "round": m["round"],
               "surface": e.get("surface") or surf.get(tsl),
               "p1": {"name": a, "country": m["p"][0]["c"] or None, "rank": rk(a, m["lg"]), "bd": profile_for(a).get("bd")},
               "p2": {"name": b, "country": m["p"][1]["c"] or None, "rank": rk(b, m["lg"]), "bd": profile_for(b).get("bd")},
               "games": m["s"], "winner": m["w"], "tour": e.get("tour") or m["lg"], "gender": m["g"], "q": m["q"], "fq": m["q"], "src": "espn"}
        if tb:
            row["tb"] = tb
        new.append(row)
        row = {k: v for k, v in row.items() if k != "_cid"}
        results.append(row)
        for k in _pair_keys(a, b):
            names.setdefault(k, []).append(row)
    if new or tbs or dupes:
        if dupes:
            print(f"ESPN: {dupes} jogo(s) repetido(s) retirado(s) (nomes por outra ordem)")
        rc.save_results(results)
        for row in new:
            try:
                extras.update_stats({k: v for k, v in row.items() if k != "_cid"})
            except Exception as ex:
                print("Estatísticas: erro", ex)
    print(f"ESPN: {len(new)} jogos novos no site, {tbs} com tie-breaks acrescentados.")
    _maybe_posts(new, prev or {})


def _maybe_posts(new, prev):
    """Os jogos novos do ESPN passam pelas MESMAS regras de post (result_card.maybe_post). Duas proteções:
    - só jogos que já tínhamos visto por jogar ou a decorrer numa leitura anterior (nunca o histórico da primeira leitura);
    - não publica jogos que estão na nossa fila de acompanhamento (esses são publicados pelo caminho normal, sem duplicar)."""
    if os.environ.get("POSTS_USE_ESPN", "1") != "1" or not new:
        return
    import result_card as rc
    if not hasattr(rc, "T"):
        rc.T, rc.LANG = rc.I18N["en"], "en"
    queued = set()
    meta = _load("tracked_meta.json", {})
    for v in meta.values():
        pl = v.get("players") or {}
        queued.update(_pair_keys((pl.get("p1") or {}).get("name", ""), (pl.get("p2") or {}).get("name", "")))
    for x in _load("live.json", {}).get("matches") or []:
        queued.update(_pair_keys(x["p1"]["name"], x["p2"]["name"]))
    n = 0
    for r in new:
        if prev.get(r["_cid"]) not in ("pre", "in"):
            continue
        if any(k in queued for k in _pair_keys(r["p1"]["name"], r["p2"]["name"])):
            continue
        m = {"id": r["id"], "tournament": r["tournament"], "round": r["round"], "tour": r["tour"], "gender": r["gender"],
             "surface": r.get("surface"), "is_qualifying": r["q"], "updated_at": r["date"] + time.strftime("T%H:%M:%SZ", time.gmtime()),
             "status": "completed", "source": "espn", "tb": r.get("tb"),
             "players": {k: {"name": r[k]["name"], "ranking": r[k]["rank"], "country": r[k]["country"], "birthday": r[k].get("bd")} for k in ("p1", "p2")},
             "score": {"games": r["games"], "sets": [sum(a > b for a, b in zip(*r["games"])), sum(b > a for a, b in zip(*r["games"]))]}}
        try:
            if rc.maybe_post(m, "out"):
                n += 1
        except Exception as e:
            print(f"ESPN post {r['id']}: erro {type(e).__name__} {e}")
    if n:
        print(f"ESPN: {n} cartões novos para a fila de posts (mesmas regras).")


# ---------- leitura (para o site) ----------
def data():
    d = _load(FILE, {})
    return d if time.time() - d.get("ts", 0) < FRESH_H * 3600 else {}


_RK, _PROF = None, None


def rank_lookup():
    """nome -> ranking: rankings do ESPN (top 150) e, para lá disso, o último ranking visto nos nossos jogos (ranks.json)."""
    global _RK
    if _RK is None:
        _RK = {}
        for r in _load("ranks.json", {}).values():
            if isinstance(r.get("rank"), int) and r.get("name"):
                _RK.setdefault(("", norm(r["name"])), r["rank"])
        er = _load(RANK_FILE, {})
        for lg in ("atp", "wta"):
            for x in er.get(lg) or []:
                _RK[(lg, norm(x["n"]))] = x["r"]
    return lambda name, lg: _RK.get((lg, norm(name))) or _RK.get(("", norm(name)))


def profile_for(name):
    global _PROF
    if _PROF is None:
        _PROF = {}
        for v in _load(PROF_FILE, {}).values():
            if v.get("n"):
                _PROF[norm(v["n"])] = v
    return _PROF.get(norm(name)) or {}


def _p(m, i, rk):
    p = m["p"][i]
    return {"name": p["n"], "country": p["c"] or None, "rank": rk(p["n"], m["lg"])}


def score_txt(m, i=0):
    """'6-1 7-6(3)' do ponto de vista do jogador i."""
    a, b = m["s"][i], m["s"][1 - i]
    out = []
    for k, (x, y) in enumerate(zip(a, b)):
        tbv = (m["tb"][i][k] if k < len(m["tb"][i]) else None, m["tb"][1 - i][k] if k < len(m["tb"][1 - i]) else None)
        lo = min(v for v in tbv if v is not None) if any(v is not None for v in tbv) else None
        out.append(f"{x}-{y}" + (f"({lo})" if lo is not None and max(x, y) == 7 and min(x, y) == 6 else ""))
    return " ".join(out)


def upcoming():
    """Jogos ATP/WTA por jogar com os dois jogadores definidos, no formato do upcoming.json."""
    d = data()
    if not d:
        return []
    ev = {e["eid"]: e for e in d.get("events", [])}
    rk = rank_lookup()
    now = time.strftime("%Y-%m-%dT%H:%M", time.gmtime(time.time() - 3 * 3600))
    out = []
    for m in d.get("matches", []):
        if m["state"] != "pre" or not (m["p"][0]["n"] and m["p"][1]["n"]) or (m["t"] or "") < now:
            continue
        e = ev.get(m["eid"]) or {}
        out.append({"id": ID_BASE + int(m["cid"]), "tp": e.get("tp", ""), "round": m["round"], "t": (m["t"] or "").replace("Z", ":00Z") if len(m["t"] or "") == 17 else m["t"],
                    "tour": e.get("tour") or m["lg"], "gender": m["g"], "court": m["court"], "p1": _p(m, 0, rk), "p2": _p(m, 1, rk), "src": "espn"})
    return out


def oop_rows(days=2):
    """Ordem de jogo ATP/WTA de hoje e amanhã: todos os jogos (por jogar, a decorrer e terminados), com court, hora e resultado."""
    d = data()
    if not d:
        return []
    ev = {e["eid"]: e for e in d.get("events", [])}
    rk = rank_lookup()
    today = dt.datetime.utcnow().date()
    keep = {(today + dt.timedelta(days=i)).isoformat() for i in range(days)}
    out = []
    for m in d.get("matches", []):
        t = m["t"] or ""
        if t[:10] not in keep or not (m["p"][0]["n"] and m["p"][1]["n"]):
            continue
        e = ev.get(m["eid"]) or {}
        st = {"pre": "scheduled", "in": "live", "post": "completed"}.get(m["state"], m["state"] or "")
        if m["status"] in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED"):
            st = m["status"].split("_", 1)[1].lower()
        out.append({"id": ID_BASE + int(m["cid"]), "tp": e.get("tp", ""), "round": m["round"], "t": (t.replace("Z", ":00Z") if len(t) == 17 else t) if m["tv"] else t[:10],
                    "day": t[:10], "status": st, "tour": e.get("tour") or m["lg"], "gender": m["g"], "court": m["court"],
                    "p1": _p(m, 0, rk), "p2": _p(m, 1, rk), "sc": score_txt(m) if m["s"][0] else "", "w": m["w"],
                    "s": m["s"], "tb": m["tb"], "src": "espn"})
    return out


def event_for(tp):
    """Torneio do ESPN com este nosso nome (ou None): nome oficial, datas."""
    import webapp
    sl = webapp.slugify(webapp.base_tournament(tp or ""))
    for ev in _load(FILE, {}).get("events", []):
        if webapp.slugify(ev.get("tp") or "") == sl:
            return ev
    return None


def defending(tp, gender=None):
    import webapp
    sl = webapp.slugify(webapp.base_tournament(tp or ""))
    for e in data().get("events", []):
        if webapp.slugify(e.get("tp") or "") == sl:
            g = gender if gender in ("men", "women") else ("women" if e["lg"] == "wta" else "men")
            return e.get("prev", {}).get(g)
    return None


def main():
    if os.environ.get("ESPN_ON", "1") == "0":
        print("ESPN desligado (ESPN_ON=0).")
        return
    events, matches = [], []
    for lg in ("atp", "wta"):
        e, m = parse(lg, _get(SB.format(lg=lg)))
        events += e
        matches += m
    if not events:
        print("ESPN: sem dados nesta execução (fica o que já havia).")
        return
    name_events(events, matches)
    prev = {m["cid"]: m.get("state") for m in _load(FILE, {}).get("matches", [])}   # estado na leitura anterior
    _save(FILE, {"ts": time.time(), "events": events, "matches": matches})
    print(f"ESPN: {len(events)} torneios, {len(matches)} jogos de singulares "
          f"({sum(m['state'] == 'pre' for m in matches)} por jogar, {sum(m['state'] == 'in' for m in matches)} a decorrer).")
    ranks = refresh_rankings()
    try:
        refresh_profiles(matches, ranks)
    except Exception as ex:
        print("ESPN perfis: erro", ex)
    import_results(events, matches, prev)


if __name__ == "__main__":
    main()
