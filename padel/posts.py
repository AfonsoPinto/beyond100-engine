"""Beyond Padel: escolhe, desenha e publica os posts do @beyond100.padel.

Regras (definidas com o Afonso):
- Torneios: FIP (Platinum, Gold, Silver) em qualquer jogo interessante; Premier Padel só finais e surpresas.
- Resultados normais só a partir das meias-finais; campeões e surpresas contam sempre.
- Surpresa: o par vencedor tem o ranking somado pior em 40+ lugares, ou um par sem cabeça de série elimina os cabeças de série 1 ou 2.
- Só posts com foto: pelo menos um dos vencedores tem foto livre (padel/photos).
- Bónus: nível do torneio (Platinum > Gold > Silver; Major > P1 > P2) e primeiro título do par/jogador.
- Máximo 4 resultados por dia, entre as 9h e as 23h de Lisboa, 45 min entre posts. Antevisões e posts semanais não contam.
- Antevisões "Who wins?" das finais só se um dos jogadores apareceu nos nossos posts nos últimos 7 dias.
Só publica com PADEL_PUBLISH=1 (o cenário do Make tem de saber enviar para a conta do padel).

Uso: python -m padel.posts make   (escolhe e desenha)  ·  python -m padel.posts send  (publica um, se for altura)"""
import datetime as dt
import json
import re
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from padel import cards  # noqa: E402
from padel.fetch import load_matches, load  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QFILE = os.path.join(os.path.dirname(__file__), "data", "posts.json")
POSTS_DIR = os.path.join(ROOT, "posts")
SITE = (os.environ.get("SITE_URL") or "https://beyond100tennis.com").rstrip("/")
PREMIER = {"major", "p1", "p2", "finals"}
LEVEL_PTS = {"finals": 4, "major": 4, "p1": 3, "p2": 2, "fip_platinum": 3, "fip_gold": 2, "fip_silver": 1}
LEVEL_TAG = {"major": "PREMIER MAJOR", "p1": "PREMIER P1", "p2": "PREMIER P2", "finals": "PREMIER FINALS",
             "fip_platinum": "FIP PLATINUM", "fip_gold": "FIP GOLD", "fip_silver": "FIP SILVER", "fip_other": "FIP"}
QUIET_ON = (os.environ.get("PADEL_QUIET_FIP") or "1").strip().lower() not in ("0", "no", "off", "false")   # FIP "outros" só em semanas sem Premier nem FIP Platinum/Gold


def quiet_week(t, tours):
    """True se, nas datas deste torneio, não houver nenhum Premier nem FIP Platinum/Gold a decorrer."""
    a, b = t.get("start_date") or "", t.get("end_date") or t.get("start_date") or ""
    if not a:
        return False
    for x in (tours or {}).values():
        if x is t or x.get("level") not in PREMIER | {"fip_platinum", "fip_gold"}:   # um FIP Silver não "enche" a semana
            continue
        xa, xb = x.get("start_date") or "", x.get("end_date") or x.get("start_date") or ""
        if xa and xa <= b and xb >= a:
            return False
    return True
CAT_NAME = {"men": "Men", "women": "Women"}
ROUND = {1: "Final", 2: "Semi-final", 4: "Quarter-final", 8: "Round of 16", 16: "Round of 32"}
env = lambda k, d: (os.environ.get(k) or "").strip() or d
MIN_SCORE = float(env("PADEL_MIN_SCORE", "4"))
SURPRISE_GAP = int(env("PADEL_SURPRISE_GAP", "40"))
MAX_DAY = int(env("PADEL_MAX_POSTS_PER_DAY", "4"))
FIP_MAX_DAY = int(env("PADEL_FIP_MAX_PER_DAY", "2"))   # 5/11/2026: dias só com FIP (sem Premier a decorrer): menos resultados por dia


def premier_on(tours, day=None):
    """True se hoje (Lisboa) houver um torneio Premier Padel a decorrer."""
    day = day or dt.date.today().isoformat()
    return any(x.get("level") in PREMIER and (x.get("start_date") or "") <= day <= (x.get("end_date") or x.get("start_date") or "")
               for x in (tours or {}).values())
QF_ON = env("PADEL_QF", "1").strip().lower() not in ("0", "no", "off", "false")   # quartos-de-final no Premier e FIP Platinum/Gold
SEND_FROM, SEND_TO = int(env("PADEL_SEND_FROM", "9")), int(env("PADEL_SEND_TO", "23"))
GAP_MIN = int(env("PADEL_SEND_GAP_MIN", "45"))


def qload():
    try:
        with open(QFILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"queue": [], "seen": {}}


def qsave(q):
    q["queue"] = q["queue"][-300:]
    cut = time.time() - 40 * 86400
    q["seen"] = {k: v for k, v in q.get("seen", {}).items() if v > cut}
    with open(QFILE, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=1)


def ranks():
    out = {}
    for v in load("rankings.json", {}).values():
        for row in (v or {}).get("rows", []):
            out[str(row.get("id"))] = row.get("ranking")
    return out


def team(m, t):
    return ((m.get("players") or {}).get(t) or [])


def other(t):
    return "team_2" if t == "team_1" else "team_1"


def best_photo(ps):
    """Foto de um dos jogadores (prefere fotos em court)."""
    found = []
    for p in ps:
        fp, cr, off = cards.photo_of(p.get("id"))
        if fp:
            found.append((off, {"path": fp, "credit": cr, "pid": p.get("id")}))
    def area(fp):
        try:
            with Image.open(fp) as im:
                return im.width * im.height
        except Exception:
            return 0
    from PIL import Image
    found.sort(key=lambda x: (x[0], -area(x[1]["path"])))           # em court primeiro, depois a de melhor resolução
    return found[0][1] if found else None


def rank_sum(ps, rk):
    return sum((rk.get(str(p.get("id"))) or 1500) for p in ps)


def titles_before(matches, pids, before):
    """Finais ganhas (nos nossos dados) por algum destes jogadores antes desta data."""
    n = 0
    for m in matches:
        if m.get("round") != 1 or not m.get("winner") or (m.get("played_at") or "") >= before:
            continue
        if {str(p.get("id")) for p in team(m, m["winner"])} & pids:
            n += 1
    return n


def interest(m, tour, rk, matches, tours=None):
    lv = tour.get("level")
    if lv == "fip_other" and not (QUIET_ON and quiet_week(tour, tours)):
        return None                                   # FIP "outros": só nas semanas mortas (sem Premier nem FIP Platinum/Gold)
    w = m.get("winner")
    if w not in ("team_1", "team_2") or (m.get("draw") or "main") != "main" or not m.get("score"):
        return None
    W, L = team(m, w), team(m, other(w))
    gap = rank_sum(W, rk) - rank_sum(L, rk)
    seeds = m.get("seeds") or {}
    sw, sl = str(seeds.get(w) or ""), str(seeds.get(other(w)) or "")
    surprise = gap >= SURPRISE_GAP or (sl in ("1", "2") and not sw.isdigit())
    try:                                              # Elo (grátis): o par vencedor tinha 30% ou menos de hipóteses pela nossa estimativa
        from padel import elo as _elo
        ec = _elo.chance(W, L)
    except Exception:
        ec = None
    elo_upset = ec is not None and ec <= float(env("PADEL_ELO_UPSET", "0.30"))
    surprise = surprise or elo_upset
    rnd = m.get("round") or 99
    champion = rnd == 1
    # alargado a 2/11/2026 (mais posts): Premier e FIP Platinum/Gold a partir dos quartos; FIP Silver a partir das meias; surpresas sempre
    deep = 4 if (lv in PREMIER or lv in ("fip_platinum", "fip_gold")) and QF_ON else 2          # FIP "outros" (semana morta): como o Silver, das meias em diante
    if not (rnd <= deep or surprise):
        return None
    first = champion and titles_before(matches, {str(p.get("id")) for p in W}, m.get("played_at") or "") == 0
    score = {1: 6, 2: 4, 4: 2}.get(rnd, 1) + LEVEL_PTS.get(lv, 0)
    why = []
    if champion:
        why.append("title")
    if surprise:
        score += 3 + min(3, max(0, gap) / 80)
        why.append("upset")
        if elo_upset:
            why.append("elo")
    if first:
        score += 2
        why.append("first_title")
    try:                                              # alcance (mesma regra do ténis): mais conhecidos / top 10 / promessas sobem na fila
        if env("REACH_ENABLED", "1") != "0":
            import reach
            pl = load("players.json", {})
            bs = []
            for grp, f_ in ((W, 1), (L, 0.75)):
                for x in grp:
                    pp_ = pl.get(str(x.get("id"))) or {}
                    lk = pp_.get("links") or {}
                    hd = lk.get("instagram") if isinstance(lk, dict) else None
                    b, bw = reach.bonus(x.get("name"), (pp_.get("birthdate") or "")[:10] or None, "padel", hd, rk.get(str(x.get("id"))), pp_.get("age"), pid=x.get("id"))
                    bs.append((b * f_, bw))
            b, bw = max(bs, key=lambda t: t[0]) if bs else (0, [])
            if b > 0:
                score += b
                why.append("reach:" + "+".join(bw))
    except Exception as ex:
        print("Padel alcance: erro", type(ex).__name__, ex)
    return {"score": round(score, 1), "why": why, "gap": gap, "surprise": surprise, "champion": champion, "first": first,
            "seed_w": sw, "seed_l": sl, "elo_w": None if ec is None else round(ec * 100)}


def kicker(info, m):
    if info["first"]:
        return "First title"
    if info["champion"]:
        return "Champions"
    if info["surprise"]:
        return "Upset"
    return "Into the final" if m.get("round") == 2 else "Win"


def note_for(info, W, L, rk):
    if info["first"]:
        return "A first title in our records for this pair"
    if info["surprise"] and info["seed_l"] in ("1", "2") and not info["seed_w"].isdigit():
        return f"Unseeded pair knock out the No. {info['seed_l']} seeds"
    if info["surprise"] and info["gap"] >= SURPRISE_GAP:
        return f"Ranked {info['gap']} places lower combined"
    if info.get("elo_w") is not None and "elo" in info["why"]:
        return f"Only a {info['elo_w']}% chance before the match (Elo estimate)"
    return ""


def make():
    q = qload()
    seen = q.setdefault("seen", {})
    tours = load("tournaments.json", {})
    matches = list(load_matches().values())
    rk = ranks()
    today = time.strftime("%Y-%m-%d", time.gmtime())
    since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 2 * 86400))
    os.makedirs(POSTS_DIR, exist_ok=True)
    made = 0
    if not q.get("intro_queued"):                                  # os 3 posts de apresentação saem antes de tudo (como no ténis)
        q["intro_queued"] = True
        for i in (1, 2, 3):
            q["queue"].append({"id": f"intro-{i}", "kind": "intro", "n": i, "score": 0, "created": time.time(),
                               "image": f"padel-intro-{i}.jpg", "sent": False})
    for m in sorted(matches, key=lambda m: m.get("played_at") or ""):
        mid = str(m.get("id"))
        if mid in seen or (m.get("played_at") or "") < since or m.get("status") not in ("finished", "retired"):
            continue
        seen[mid] = time.time()
        t = tours.get(str(m.get("tid"))) or {}
        info = interest(m, t, rk, matches, tours)
        if not info or info["score"] < MIN_SCORE:
            continue
        if info["champion"]:                                       # finais: homens e mulheres no mesmo post (como o ténis)
            r = champions_post(q, m, t, matches, rk, seen, info)
            if r is not None:
                made += r
                continue
        w = m["winner"]
        W, L = team(m, w), team(m, other(w))
        ph = best_photo(W)
        if not ph:
            print(f"Padel {mid}: {'/'.join(p.get('short_name') or '' for p in W)} sem foto livre, não sai.")
            continue
        sets = [(s.get(w), s.get(other(w))) for s in m["score"]]
        try:
            date = dt.date.fromisoformat(m.get("played_at")).strftime("%d %b %Y").upper()
        except (TypeError, ValueError):
            date = ""
        fn = f"padel-r-{mid}.jpg"
        cards.result_card({"kicker": kicker(info, m), "level": LEVEL_TAG.get(t.get("level"), ""), "round": ROUND.get(m.get("round"), m.get("round_name") or ""),
                           "tournament": short_name(t), "city": t.get("location"), "date": date, "winners": W, "losers": L, "sets": sets,
                           "photo": ph, "ranks": rk, "note": note_for(info, W, L, rk)}, os.path.join(POSTS_DIR, fn))
        facts = {"tournament": t.get("name"), "level": LEVEL_TAG.get(t.get("level"), ""), "city": t.get("location"), "country": t.get("country"),
                 "category": m.get("category"), "round": ROUND.get(m.get("round"), m.get("round_name")),
                 "winners": [{"name": p.get("name"), "country": p.get("nationality"), "ranking": rk.get(str(p.get("id")))} for p in W],
                 "losers": [{"name": p.get("name"), "country": p.get("nationality"), "ranking": rk.get(str(p.get("id")))} for p in L],
                 "score": " ".join(f"{a}-{b}" for a, b in sets), "seed_winners": info["seed_w"] or None, "seed_losers": info["seed_l"] or None,
                 "reasons": info["why"], "winners_pre_match_chance_pct_elo_estimate": info.get("elo_w"), "photo_of": next((p.get("name") for p in W if p.get("id") == ph["pid"]), None)}
        q["queue"].append({"id": f"r-{mid}", "kind": "result", "score": info["score"], "created": time.time(), "image": fn,
                           "facts": facts, "sent": False, "players": [str(p.get("id")) for p in W + L], "photo_pids": [str(ph["pid"])]})
        made += 1
        print(f"Padel {mid}: cartão ({info['score']}: {', '.join(info['why']) or 'round'}).")
    made += make_previews(q, tours, matches, rk)
    made += make_tour_preview(q, tours, rk)
    for _f in (lambda: make_new_pairs(q, tours, matches, rk), lambda: make_race(q, tours, matches, rk), lambda: make_top10(q, rk)):
        try:
            made += _f()
        except Exception as ex:
            print("Padel notícias (dados): erro", type(ex).__name__, ex)
    made += make_weekly(q, matches, rk)
    qsave(q)
    site_posts = os.path.join(ROOT, "site", "posts")              # o site já foi montado antes: copia as imagens novas
    if os.path.isdir(os.path.join(ROOT, "site")):
        import shutil
        os.makedirs(site_posts, exist_ok=True)
        for e in q["queue"]:
            src = os.path.join(POSTS_DIR, e["image"])
            if not e.get("sent") and os.path.exists(src):
                shutil.copy(src, site_posts)
    print(f"Padel: {made} posts novos na fila.")


def champions_post(q, m, t, matches, rk, seen, info):
    """Final de um torneio: se a outra final (homens/mulheres) do mesmo torneio também já acabou, faz UM cartão com os dois pares
    campeões; se ainda vai ser jogada nas próximas horas, espera por ela (devolve 0 e volta a tentar na próxima atualização).
    Devolve None quando não há outra final (segue o cartão normal)."""
    tid = str(m.get("tid"))
    other_f = [x for x in matches if str(x.get("tid")) == tid and x.get("round") == 1 and (x.get("draw") or "main") == "main"
               and x.get("category") != m.get("category")]
    if not other_f:
        return None
    o = other_f[0]
    if o.get("winner") not in ("team_1", "team_2"):
        if o.get("status") in ("walkover", "retired", "cancelled") or (o.get("played_at") or "") < (m.get("played_at") or ""):
            return None
        seen.pop(str(m.get("id")), None)                          # ainda não acabou: espera (a outra final é no mesmo dia ou depois)
        print(f"Padel {m.get('id')}: final feita, à espera da outra final do torneio para o post único de campeões.")
        return 0
    pid = f"c-{tid}"
    if any(e["id"] == pid for e in q["queue"]):
        seen[str(o.get("id"))] = time.time()
        return 0
    fins = []
    for x in sorted([m, o], key=lambda x: x.get("category") != "men"):
        w = x["winner"]
        W, L = team(x, w), team(x, other(w))
        fins.append({"label": "Men" if x.get("category") == "men" else "Women", "winners": W, "losers": L,
                     "sets": [(s.get(w), s.get(other(w))) for s in x["score"]], "photo": best_photo(W)})
    if not any(f["photo"] for f in fins):
        return None
    seen[str(o.get("id"))] = time.time()
    try:
        date = dt.date.fromisoformat(max(m.get("played_at") or "", o.get("played_at") or "")).strftime("%d %b %Y").upper()
    except (TypeError, ValueError):
        date = ""
    fn = f"padel-{pid}.jpg"
    cards.champions_card({"level": LEVEL_TAG.get(t.get("level"), ""), "tournament": short_name(t), "city": t.get("location"), "date": date,
                          "finals": fins, "ranks": rk}, os.path.join(POSTS_DIR, fn))
    facts = {"tournament": t.get("name"), "level": LEVEL_TAG.get(t.get("level"), ""), "city": t.get("location"), "country": t.get("country"),
             "round": "Final", "finals": [{"category": f["label"].lower(),
                                           "winners": [{"name": p.get("name"), "country": p.get("nationality"), "ranking": rk.get(str(p.get("id")))} for p in f["winners"]],
                                           "losers": [{"name": p.get("name"), "country": p.get("nationality"), "ranking": rk.get(str(p.get("id")))} for p in f["losers"]],
                                           "score": " ".join(f"{a}-{b}" for a, b in f["sets"])} for f in fins]}
    q["queue"].append({"id": pid, "kind": "result", "score": info["score"] + 2, "created": time.time(), "image": fn,
                       "facts": facts, "sent": False, "players": [str(p.get("id")) for f in fins for p in f["winners"] + f["losers"]]})
    print(f"Padel {pid}: cartão de campeões (homens e mulheres).")
    return 1


def short_name(t):
    import re
    n = t.get("name") or ""
    n = re.sub(r"^(FIP\s+(Platinum|Gold|Silver|Bronze)\s+)", "", n, flags=re.I)
    return n[:40]


def featured_players(q, days=7):
    cut = time.time() - days * 86400
    out = set()
    for e in q.get("queue", []):
        if e.get("sent") and not e.get("skipped") and (e.get("sent_ts") or 0) >= cut:
            out |= set(e.get("players") or [])
    return out


PLACES = os.path.join(os.path.dirname(__file__), "photos", "places")


def place_photo(city):
    """Foto REAL e livre da cidade-sede (imagem principal da Wikidata, licença verificada na Commons), guardada em photos/places.
    {"path", "credit"} ou None. Nunca usa fotos oficiais do torneio (não têm licença livre)."""
    import fetch_photos as fp
    if not city:
        return None
    os.makedirs(PLACES, exist_ok=True)
    key = fp.slug(city)
    path = os.path.join(PLACES, key + ".jpg")
    cred = load_json_file(os.path.join(PLACES, "credits.json"))
    if os.path.exists(path):
        return {"path": path, "credit": cred.get(key, "")}
    try:
        s = fp._get(fp.WIKIDATA if hasattr(fp, "WIKIDATA") else "https://www.wikidata.org/w/api.php",
                    {"action": "wbsearchentities", "search": city, "language": "en", "type": "item", "limit": 5})
        for hit in s.get("search") or []:
            if (hit.get("label") or "").lower() != city.lower():
                continue
            e = fp._get("https://www.wikidata.org/w/api.php", {"action": "wbgetentities", "ids": hit["id"], "props": "claims"})
            cl = ((e.get("entities") or {}).get(hit["id"]) or {}).get("claims") or {}
            img = next((((c.get("mainsnak") or {}).get("datavalue") or {}).get("value") for c in cl.get("P18") or []), None)
            if not img or not cl.get("P17"):                   # só lugares (têm país) com imagem principal
                continue
            q_ = fp._get(fp.COMMONS, {"action": "query", "titles": "File:" + img, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1600})
            for pg in (q_.get("query") or {}).get("pages", {}).values():
                ii = (pg.get("imageinfo") or [{}])[0]
                md = ii.get("extmetadata") or {}
                lic = (md.get("LicenseShortName") or {}).get("value", "")
                if not fp.license_ok(lic) or (ii.get("width") or 0) < 1200:
                    continue
                fp._download(ii.get("thumburl") or ii["url"], path)
                artist = re.sub(r"<[^>]+>", "", (md.get("Artist") or {}).get("value", "")).strip()[:50] or "Wikimedia Commons"
                cred[key] = f"{artist} / {lic}"
                with open(os.path.join(PLACES, "credits.json"), "w", encoding="utf-8") as f:
                    json.dump(cred, f, ensure_ascii=False, indent=1)
                return {"path": path, "credit": cred[key]}
    except Exception as ex:
        print("Padel: foto da cidade falhou:", city, type(ex).__name__, ex)
    return None


def load_json_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def photo_uses(q, days=60):
    """Quantas vezes a foto de cada jogador saiu nos posts recentes (para não repetir sempre as mesmas)."""
    rkf = load("rankings.json", {})
    by_name = {(x.get("name") or "").lower(): str(x.get("id")) for cat in ("men", "women") for x in ((rkf.get(cat) or {}).get("rows") or [])}
    cut = time.time() - days * 86400
    n = {}
    for e in q.get("queue") or []:
        if e.get("created", 0) < cut:
            continue
        pids = list(e.get("photo_pids") or [])
        po = ((e.get("facts") or {}).get("photo_of") or "").lower()
        if po and by_name.get(po):
            pids.append(by_name[po])
        fin = (e.get("facts") or {}).get("finals")
        for x in (fin if isinstance(fin, list) else []):           # nos posts "race", 'finals' é o nome do torneio (texto)
            po = ((x.get("photo_of") if isinstance(x, dict) else "") or "").lower()
            if po and by_name.get(po):
                pids.append(by_name[po])
        for pid in set(pids):
            n[pid] = n.get(pid, 0) + 1
    return n


def make_tour_preview(q, tours, rk):
    """Na véspera (ou no 1.º dia) de um Premier ou FIP Platinum: post com os cabeças de série (lista de inscritos) e os campeões em título.
    Só sai com pelo menos uma foto REAL licenciada de um cabeça de série; sem foto, não há post."""
    if env("PADEL_TOUR_PREVIEW", "1") in ("0", "no", "off", "false"):
        return 0
    entries, editions, rkf = load("entries.json", {}), load("editions.json", {}), load("rankings.json", {})
    short = {}                                                    # apelido oficial (short_name) tirado dos jogos: 'Brea', 'Triay', 'Di Nenno'
    for m in load_matches().values():
        for tm in ("team_1", "team_2"):
            for x in ((m.get("players") or {}).get(tm) or []):
                if x.get("short_name"):
                    short.setdefault(str(x.get("id")), x["short_name"])
    cat_of = {str(x.get("id")): cat for cat in ("men", "women") for x in ((rkf.get(cat) or {}).get("rows") or [])}
    done = {e["id"] for e in q["queue"]}
    d0, d1 = time.strftime("%Y-%m-%d", time.gmtime()), time.strftime("%Y-%m-%d", time.gmtime(time.time() + 86400))
    n = 0
    for t in tours.values():
        tid = str(t.get("id"))
        if (t.get("level") not in PREMIER | {"fip_platinum"} or t.get("start_date") not in (d0, d1) or f"tp-{tid}" in done
                or (entries.get(tid) or {}).get("next")):         # lista de inscritos ainda incompleta: espera
            continue
        rows = [r for r in (entries.get(tid) or {}).get("rows") or [] if r.get("draw") == "main" and r.get("pair")]
        pairs = {}
        for r in rows:
            r = dict(r, short=short.get(str(r["id"])))
            pairs.setdefault((cat_of.get(str(r["id"]), "men"), r["pair"]), []).append(r)
        cols, top8 = [], {}
        for cat in ("men", "women"):
            ps = sorted([v for (c_, _), v in pairs.items() if c_ == cat and len(v) == 2], key=lambda v: min(x.get("position") or 999 for x in v))
            if ps:
                cols.append((cat, [(min(x.get("position") or 0 for x in v), v) for v in ps[:4]]))
                top8[cat] = ps[:8]
        if not cols:
            continue
        uses, photos = photo_uses(q), []
        for cat, ps in top8.items():                               # fotos reais: a menos usada nos posts recentes, entre os 8 primeiros pares
            cand = []
            for i, v in enumerate(ps):
                for x in v:
                    fp_, cr_, off_ = cards.photo_of(x.get("id"))
                    if fp_:
                        cand.append((uses.get(str(x.get("id")), 0), off_, i, {"path": fp_, "credit": cr_, "pid": x.get("id"), "label": x.get("name")}))
            if cand:
                photos.append(sorted(cand, key=lambda c: c[:3])[0][3])
        if not photos:
            print(f"Padel antevisão {t.get('name')}: sem foto licenciada dos cabeças de série, não sai.")
            continue
        eds = sorted([e for e in editions.get(tid) or [] if str(e.get("id")) != tid and isinstance(e.get("winners"), dict)],
                     key=lambda e: e.get("start_date") or "", reverse=True)
        champs = []
        if eds:
            for cat in ("men", "women"):
                ws = [x for x in eds[0]["winners"].get(cat) or [] if isinstance(x, dict)]
                if ws:
                    champs.append(" / ".join(x.get("short_name") or (x.get("name") or "").split()[-1] for x in ws))
        try:
            when = "STARTS " + dt.date.fromisoformat(t["start_date"]).strftime("%a %d %b").upper()
        except (KeyError, ValueError):
            when = ""
        fn = f"padel-tp-{tid}.jpg"
        cards.tour_preview_card({"level": LEVEL_TAG.get(t.get("level"), ""), "tournament": short_name(t), "when": when, "photos": photos,
                                 "place": place_photo(t.get("location")), "city": t.get("location"),
                                 "cols": [(CAT_NAME.get(c_, c_), rows_) for c_, rows_ in cols], "champions": " · ".join(champs), "ranks": rk},
                                os.path.join(POSTS_DIR, fn))
        facts = {"tournament": t.get("name"), "level": LEVEL_TAG.get(t.get("level"), ""), "city": t.get("location"), "starts": t.get("start_date"),
                 "prize": (t.get("prize") or {}).get("amount"),
                 "top_seeds": {c_: [{"seed": s, "pair": [x.get("name") for x in v], "short": [x.get("short") or x.get("name") for x in v]} for s, v in rows_] for c_, rows_ in cols},
                 "defending_champions": champs, "defending_year": (eds[0].get("start_date") or "")[:4] if eds else None}
        q["queue"].append({"id": f"tp-{tid}", "kind": "tour_preview", "score": 0, "created": time.time(), "image": fn, "sent": False, "facts": facts,
                           "photo_pids": [str(x["pid"]) for x in photos]})
        n += 1
        print(f"Padel antevisão: {t.get('name')} ({fn}).")
    return n


# ---------------------------------------------------------------- notícias a partir dos dados (grátis, sem IA, factos da Padel API)
NO_AI = {"newpairs", "race", "top10"}                              # legendas por modelo de texto (custo zero)


def _short_of(matches):
    out = {}
    for m in matches:
        for tm in ("team_1", "team_2"):
            for x in ((m.get("players") or {}).get(tm) or []):
                if x.get("short_name"):
                    out.setdefault(str(x.get("id")), x["short_name"])
    return out


def _sn(p, short):
    nm = p.get("name") or ""
    sh = short.get(str(p.get("id"))) or (nm.split()[-1] if nm else "?")
    return f"{nm.split()[0][0]}. {sh}" if nm and nm.split()[0] != sh else sh


def _ph(ps, uses):
    """Fotos reais (licenciadas) destes jogadores, as menos usadas primeiro: [{path, credit, label, pid}]."""
    c = []
    for i, x in enumerate(ps):
        fp_, cr_, off_ = cards.photo_of(x.get("id"))
        if fp_:
            c.append((uses.get(str(x.get("id")), 0), off_, i, {"path": fp_, "credit": cr_, "label": x.get("name"), "pid": x.get("id")}))
    return [x[3] for x in sorted(c, key=lambda c: c[:3])]


def _queue(q, pid, kind, fn, facts, photos):
    q["queue"].append({"id": pid, "kind": kind, "score": 0, "created": time.time(), "image": fn, "sent": False, "facts": facts,
                       "photo_pids": [str(x["pid"]) for x in photos if x.get("pid")]})
    print(f"Padel {kind}: {fn}")


def make_new_pairs(q, tours, matches, rk):
    """'New pair alert' (só Premier, e só com foto real de um dos jogadores): na véspera, pares do quadro principal que nunca jogaram juntos nos nossos dados, com um jogador do
    top 50 e os dois já com jogos (com outros parceiros). Um post por torneio. Factos: lista de inscritos + jogos (Padel API)."""
    import feature_card
    entries, rkf = load("entries.json", {}), load("rankings.json", {})
    cat_of = {str(x.get("id")): cat for cat in ("men", "women") for x in ((rkf.get(cat) or {}).get("rows") or [])}
    done = {e["id"] for e in q["queue"]}
    d1, d2 = time.strftime("%Y-%m-%d", time.gmtime(time.time() + 86400)), time.strftime("%Y-%m-%d", time.gmtime(time.time() + 2 * 86400))
    together, last_partner = set(), {}
    for m in sorted(matches, key=lambda m: m.get("played_at") or ""):
        for tm in ("team_1", "team_2"):
            ps = team(m, tm)
            if len(ps) == 2:
                together.add(frozenset(str(x.get("id")) for x in ps))
                for a, b in ((ps[0], ps[1]), (ps[1], ps[0])):
                    last_partner[str(a.get("id"))] = b
    short, uses, n = _short_of(matches), photo_uses(q), 0
    for t in tours.values():
        tid = str(t.get("id"))
        if t.get("level") not in PREMIER or t.get("start_date") not in (d1, d2) or f"np-{tid}" in done or (entries.get(tid) or {}).get("next"):
            continue
        rows = [r for r in (entries.get(tid) or {}).get("rows") or [] if r.get("draw") == "main" and r.get("pair")]
        pairs = {}
        for r in rows:
            pairs.setdefault(r["pair"], []).append(r)
        new = []
        for v in pairs.values():
            if len(v) != 2 or frozenset(str(x["id"]) for x in v) in together:
                continue
            if not all(str(x["id"]) in last_partner for x in v):                 # os dois têm de ter jogos (senão não é 'novo par', é estreia)
                continue
            if min((x.get("ranking") or 999) for x in v) > 50:
                continue
            new.append(v)
        new.sort(key=lambda v: min(x.get("position") or 999 for x in v))
        if not new:
            continue
        photos = _ph([x for v in new for x in v], uses)[:2]
        if not photos:                                              # sem foto real de um jogador dos pares novos, não sai
            print(f"Padel new pairs {t.get('name')}: sem foto de nenhum jogador dos pares novos, não sai.")
            continue
        place = place_photo(t.get("location"))
        lines = []
        for v in new[:6]:
            prev = " · ".join(f"{_sn(x, short)} was with {_sn(last_partner[str(x['id'])], short)}" for x in v)
            seed = min(x.get("position") or 0 for x in v)
            lines.append({"left": str(seed) if seed else "·", "name": " / ".join(_sn(x, short) for x in v), "sub": prev, "right": "NEW PAIR",
                          "hot": True})
        fn = f"padel-np-{tid}.jpg"
        feature_card.feature_card({"tags": ["NEW PAIR ALERT", LEVEL_TAG.get(t.get("level"), "")], "title": short_name(t),
                                   "subtitle": "First tournament together", "place": place, "photos": photos, "rows": lines,
                                   "foot": "Pairs playing together for the first time in our records."}, os.path.join(POSTS_DIR, fn), theme="padel")
        facts = {"tournament": t.get("name"), "starts": t.get("start_date"),
                 "pairs": [{"pair": [x.get("name") for x in v], "previous_partners": [last_partner[str(x["id"])].get("name") for x in v],
                            "category": cat_of.get(str(v[0]["id"]), "men")} for v in new[:6]]}
        _queue(q, f"np-{tid}", "newpairs", fn, facts, photos)
        n += 1
    return n


def make_race(q, tours, matches, rk):
    """'Race to the Finals' (quinta, a partir das 12h UTC), até ao Finals: posições 6 a 10 da Race (os 8 primeiros pares vão ao Finals),
    homens e mulheres no mesmo cartão. Factos: ranking Race da Padel API."""
    import feature_card
    now = dt.datetime.utcnow()
    if now.weekday() != int(env("PADEL_RACE_DAY", "3")) or now.hour < int(env("PADEL_RACE_HOUR", "12")):
        return 0
    fin = sorted([t for t in tours.values() if t.get("level") == "finals" and (t.get("start_date") or "") > now.date().isoformat()],
                 key=lambda t: t.get("start_date"))
    if not fin:
        return 0
    fin = fin[0]
    pid = f"race-{now.strftime('%G-W%V')}"
    if pid in {e["id"] for e in q["queue"]}:
        return 0
    race = load("race.json", {})
    short, uses = _short_of(matches), photo_uses(q)
    last_partner = {}
    for m in sorted(matches, key=lambda m: m.get("played_at") or ""):
        for tm in ("team_1", "team_2"):
            ps = team(m, tm)
            if len(ps) == 2:
                for a_, b_ in ((ps[0], ps[1]), (ps[1], ps[0])):
                    last_partner[str(a_.get("id"))] = b_
    cols, who = [], []
    for cat in ("men", "women"):
        rows = sorted((race.get(cat) or {}).get("rows") or [], key=lambda x: x.get("ranking") or 999)
        if not rows:
            continue
        pos = {str(x["id"]): x["ranking"] for x in rows}
        used, pairs = set(), []
        for x in rows:                                          # um par = jogador + parceiro do último jogo; posição do par = a melhor dos dois
            if str(x["id"]) in used:
                continue
            mate = last_partner.get(str(x["id"]))
            used.add(str(x["id"]))
            if mate and str(mate.get("id")) in pos:
                used.add(str(mate.get("id")))
            pairs.append((x, mate))
        lines = []
        for i, (x, mate) in enumerate(pairs[:10], 1):
            if i < 6:
                continue
            who += [x] + ([mate] if mate else [])
            nm = _sn(x, short) + (f" / {_sn(mate, short)}" if mate else "")
            lines.append({"left": str(i), "name": nm, "sub": f'{int(x.get("points") or 0):,} pts', "right": "IN" if i <= 8 else "OUT", "hot": i <= 8})
        if lines:
            cols.append((f"{CAT_NAME[cat]} · top 8 qualify", lines))
    if not cols:
        return 0
    weeks = max(0, (dt.date.fromisoformat(fin["start_date"]) - now.date()).days // 7)
    photos = _ph(who, uses)[:2]
    place = place_photo(fin.get("location"))
    if not photos and not place:
        return 0
    fn = f"padel-{pid}.jpg"
    feature_card.feature_card({"tags": ["RACE TO THE FINALS", f"{weeks} WEEK{'S' if weeks != 1 else ''} TO GO"], "title": f"Race to {fin.get('location') or 'the Finals'}",
                               "subtitle": "On the bubble · pairs 6 to 10", "place": place, "photos": photos, "cols": cols,
                               "foot": "Official Race ranking. The top 8 pairs play the Finals."}, os.path.join(POSTS_DIR, fn), theme="padel")
    facts = {"finals": fin.get("name"), "finals_start": fin.get("start_date"), "weeks_to_go": weeks,
             "bubble": [{"line": l["name"], "position": l["left"], "status": l["right"], "category": lab} for lab, ls in cols for l in ls]}
    _queue(q, pid, "race", fn, facts, photos)
    return 1


def make_top10(q, rk):
    """'New in the top 10': quando sai o ranking oficial e alguém entra no top 10 (antes estava fora). Factos: ranking oficial da Padel API."""
    import feature_card
    rkf = load("rankings.json", {})
    uses, n = photo_uses(q), 0
    done = {e["id"] for e in q["queue"]}
    for cat in ("men", "women"):
        r = rkf.get(cat) or {}
        rows = r.get("rows") or []
        pid = f"t10-{cat}-{r.get('date')}"
        if not rows or pid in done:
            continue
        new = [x for x in rows if (x.get("ranking") or 99) <= 10 and (x.get("ranking_diff") or 0) > 0 and x["ranking"] + x["ranking_diff"] > 10]
        if not new:
            continue
        photos = _ph(new, uses)[:2]
        if not photos:                                             # sem foto real de quem entrou, não sai
            continue
        top = sorted([x for x in rows if (x.get("ranking") or 99) <= 10], key=lambda x: x["ranking"])
        ids = {str(x["id"]) for x in new}
        lines = [{"left": str(x["ranking"]), "name": x.get("name"), "sub": f'{int(x.get("points") or 0):,} points',
                  "right": f'▲{x["ranking_diff"]}' if str(x["id"]) in ids else "", "hot": str(x["id"]) in ids} for x in top[:10]]
        fn = f"padel-{pid}.jpg"
        nm = " & ".join(x["name"] for x in new[:2])
        feature_card.feature_card({"tags": ["NEW IN THE TOP 10", CAT_NAME[cat].upper()], "title": "Top 10", "subtitle": f"Welcome, {nm}",
                                   "place": None, "photos": photos, "rows": lines, "foot": "Official ranking of " + (r.get("date") or "")},
                                  os.path.join(POSTS_DIR, fn), theme="padel")
        facts = {"category": cat, "date": r.get("date"), "new": [{"name": x["name"], "ranking": x["ranking"], "previous": x["ranking"] + x["ranking_diff"]} for x in new]}
        _queue(q, pid, "top10", fn, facts, photos)
        n += 1
    return n


def make_previews(q, tours, matches, rk):
    done = {e["id"] for e in q["queue"]}
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if sum(1 for e in q["queue"] if e["kind"] == "preview" and time.strftime("%Y-%m-%d", time.gmtime(e["created"])) == today) >= 1:
        return 0
    feat = featured_players(q)
    n = 0
    for m in matches:
        if m.get("round") != 1 or m.get("status") not in ("scheduled", "pending") or f"p-{m.get('id')}" in done:
            continue
        if (m.get("played_at") or "") not in (today, time.strftime("%Y-%m-%d", time.gmtime(time.time() + 86400))):
            continue
        A, B = team(m, "team_1"), team(m, "team_2")
        if len(A) < 2 or len(B) < 2:
            continue
        ids = {str(p.get("id")) for p in A + B}
        if not ids & feat:
            continue
        pa, pb = best_photo(A), best_photo(B)
        if not (pa and pb):                 # só com foto real dos dois lados (7/11/2026: meio cartão vazio ou só texto parece feito por máquina)
            continue
        t = tours.get(str(m.get("tid"))) or {}
        when = (m.get("schedule_label") or (m.get("scheduled_at_local") or "")[11:16] or "").upper()
        fn = f"padel-p-{m.get('id')}.jpg"
        tie = m.get("tie") or {}
        lvl = "WORLD CUP" if "world cup" in (t.get("name") or "").lower() else LEVEL_TAG.get(t.get("level"), "")
        cards.preview_card({"level": lvl, "tournament": short_name(t), "when": when, "pairs": [A, B],
                            "photos": [pa, pb], "ranks": rk, "teams": [tie.get("team_1"), tie.get("team_2")] if tie else None},
                           os.path.join(POSTS_DIR, fn))
        q["queue"].append({"id": f"p-{m.get('id')}", "kind": "preview", "score": 0, "created": time.time(), "image": fn, "sent": False,
                           "players": list(ids), "facts": {"tournament": t.get("name"), "category": m.get("category"), "when": when,
                                                           "pair_1": [p.get("name") for p in A], "pair_2": [p.get("name") for p in B]}})
        n += 1
        break
    return n


def make_weekly(q, matches, rk):
    """Segunda: Power Ranking (melhor forma nos últimos 30 dias); terça: Rising (quem mais subiu no ranking);
    quarta: Road to the Top 50 (os mais perto de entrar). UM post por semana e tipo, com homens e mulheres lado a lado
    (como o Power Ranking do ténis)."""
    now = dt.datetime.utcnow()
    wk = now.strftime("%G-W%V")
    done = {e["id"] for e in q["queue"]}
    plan = {0: "power", 1: "rising", 2: "road"}
    kind = plan.get(now.weekday())
    if not kind or now.hour < 11:
        return 0
    pid = f"w-{kind}-{wk}"
    if pid in done or any(x in done for x in (f"w-{kind}-men-{wk}", f"w-{kind}-women-{wk}")):
        return 0
    cols, facts, title, sub, note = [], {}, "", "", ""
    for cat in ("men", "women"):
        rows, title, sub, note = weekly_rows(kind, cat, matches, rk)
        if len(rows) >= 5:
            cols.append(("Men" if cat == "men" else "Women", rows))
            facts[cat] = rows[:6]
    if not cols:
        return 0
    sub = sub.rsplit(" · ", 1)[0]                                    # sem 'men'/'women': o cartão tem as duas colunas
    fn = f"padel-{pid}.jpg"
    cards.list2_card({"title": title, "subtitle": sub, "cols": cols, "note": note}, os.path.join(POSTS_DIR, fn))
    q["queue"].append({"id": pid, "kind": "weekly", "score": 0, "created": time.time(), "image": fn, "sent": False,
                       "facts": {"feature": kind, "rows": facts}})
    return 1


def weekly_rows(kind, cat, matches, rk):
    CAT = {"men": "men", "women": "women"}[cat]
    rows_r = (load("rankings.json", {}).get(cat) or {}).get("rows") or []
    if kind == "rising":
        rr = sorted([r for r in rows_r if (r.get("ranking_diff") or 0) > 0], key=lambda r: -(r.get("ranking_diff") or 0))
        rr = [r for r in rr if (r.get("ranking") or 999) <= 150][:8]
        rows = [{"rank": i + 1, "name": r["name"], "sub": f'{r.get("nationality", "")} · now #{r["ranking"]}', "value": f'▲{r["ranking_diff"]}'}
                for i, r in enumerate(rr)]
        return rows, "Rising", f"Biggest ranking climbers · {CAT}", "Places gained in this week's official ranking"
    if kind == "road":
        rr = sorted([r for r in rows_r if 51 <= (r.get("ranking") or 0) <= 70], key=lambda r: r["ranking"])[:8]
        rows = [{"rank": r["ranking"], "name": r["name"], "sub": f'{r.get("nationality", "")} · {(r.get("points") or 0)} pts',
                 "value": (f'▲{r["ranking_diff"]}' if (r.get("ranking_diff") or 0) > 0 else "")} for r in rr]
        return rows, "Road to the Top 50", f"Knocking on the door · {CAT}", "Official ranking, positions 51 to 70"
    cut = (dt.date.today() - dt.timedelta(days=30)).isoformat()
    rec = {}
    for m in matches:
        if m.get("category") != cat or (m.get("played_at") or "") < cut or m.get("winner") not in ("team_1", "team_2"):
            continue
        for t in ("team_1", "team_2"):
            for p in team(m, t):
                e = rec.setdefault(str(p.get("id")), {"p": p, "w": 0, "l": 0, "t": 0})
                if m["winner"] == t:
                    e["w"] += 1
                    e["t"] += 1 if m.get("round") == 1 else 0
                else:
                    e["l"] += 1
    rr = sorted(rec.values(), key=lambda e: (-(e["w"] * 2 + e["t"] * 3 - e["l"]), -e["w"]))[:8]
    rows = [{"rank": i + 1, "name": e["p"].get("name"), "sub": f'{e["p"].get("nationality", "")}' + (f' · #{rk.get(str(e["p"].get("id")))}' if rk.get(str(e["p"].get("id"))) else "")
             + (f' · {e["t"]} title{"s" if e["t"] > 1 else ""}' if e["t"] else ""), "value": f'{e["w"]}-{e["l"]}'} for i, e in enumerate(rr)]
    return rows, "Power Ranking", f"Best form, last 30 days · {CAT}", "Wins and titles in Premier Padel and the FIP Tour"


# ------------------------------------------------------------------ legendas e envio
SYSTEM = ("You write Instagram captions for Beyond Padel (@beyond100.padel), an account about every player and every draw in professional padel "
          "(Premier Padel and the CUPRA FIP Tour). Voice: write like a real person who follows padel closely and is telling a friend what just happened: "
          "normal, complete sentences, plain words, a little emotion only when the result deserves it. It must not read like an ad, a press release or AI. "
          "Banned style: runs of short three-word sentences, slogan lines, 'No more scrolling', em dashes, words like stunning, incredible, masterclass, epic. "
          "Format: 2 or 3 lines in total (what happened, then the one or two most interesting details); a question only when it comes naturally (about one post in three); "
          "then 3-4 specific hashtags (#padel, the tournament or circuit, player surnames; brand tag #BeyondPadel). 0 or 1 emoji. English. "
          "For kind=tour_preview: the tournament starts soon (facts.starts); present it with the top seeds of each category and the defending "
          "champions (defending_year), never predict a winner, ask readers who they back. "
          "Hard rules: use ONLY the facts in the JSON; never invent scores, rankings, history or quotes; copy the score exactly as given.")


INTRO = {
    1: "Padel beyond the big names. 🎾\n\nBeyond Padel covers every player and every draw: results, champions and rising players "
       "from Premier Padel and the CUPRA FIP Tour.\n\nSister account of @beyond100.tennis.\n\n#padel #BeyondPadel #PremierPadel #FIPTour",
    2: "What to expect here:\n\n• Results & champions, in clean cards\n• Upsets, when the underdogs win\n• Players to watch: "
       "our weekly Power Ranking and the biggest ranking climbers\n\nEvery player. Every draw.\n\n#padel #BeyondPadel #PremierPadel #FIPTour",
    3: "New here? Follow along for results from every draw, not just the finals.\n\nSave this post and share it with your padel group. 🙌\n"
       "Full results, draws and rankings: beyond100tennis.com/padel\n\n#padel #BeyondPadel #PremierPadel #FIPTour",
}


PADEL_FOLLOW = "Follow @beyond100.padel for every draw, not just the finals."


def caption(e):
    """Legenda + linha para seguir a conta (antes das hashtags), como no ténis."""
    t = _caption(e)
    if e["kind"] == "intro" or "follow @beyond100" in t.lower():
        return t
    lines = t.rstrip().split("\n")
    if lines and lines[-1].lstrip().startswith("#"):
        return "\n".join(lines[:-1]).rstrip() + "\n" + PADEL_FOLLOW + "\n\n" + lines[-1]
    return t.rstrip() + "\n" + PADEL_FOLLOW


def _caption(e):
    if e["kind"] == "intro":
        return INTRO[e["n"]]
    f = e.get("facts") or {}
    key = os.environ.get("ANTHROPIC_API_KEY") if e["kind"] not in NO_AI else None      # notícias de dados: modelo de texto, custo zero
    if key:
        try:
            import requests
            import captions
            model = captions.FALLBACK_MODEL if e["kind"] != "result" or e.get("score", 0) < 9 else captions.MODEL
            r = requests.post(captions.API_URL, timeout=40, headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                              json={"model": model, "max_tokens": 600, "system": SYSTEM,
                                    "messages": [{"role": "user", "content": json.dumps({"kind": e["kind"], "facts": f}, ensure_ascii=False)}]})
            r.raise_for_status()
            j = r.json()
            captions._record(j.get("model") or model, j.get("usage"), feature=f"padel-{e['kind']}")
            text = "".join(b.get("text", "") for b in j.get("content", []) if b.get("type") == "text").strip()
            if text and (e["kind"] != "result" or (f.get("score") or "") in text):
                return text
        except Exception as ex:
            print("Padel legenda: IA indisponível,", type(ex).__name__)
    return fallback(e)


def fallback(e):
    f = e.get("facts") or {}
    if e["kind"] == "result" and f.get("finals"):
        lines = [f"🏆 {f.get('tournament')} champions"]
        for x in f["finals"]:
            lines.append(f"{x['category'].title()}: {' / '.join(p['name'] for p in x['winners'])} · {x['score']}")
        return "\n".join(lines) + "\nWhich title impressed you more?\n#padel #BeyondPadel " + ("#PremierPadel" if (f.get("level") or "").startswith("PREMIER") else "#FIPTour")
    if e["kind"] == "result":
        w = " / ".join(p["name"] for p in f.get("winners", []))
        l = " / ".join(p["name"] for p in f.get("losers", []))
        head = "🏆 " + w + f" win {f.get('tournament')}" if "title" in (f.get("reasons") or []) else f"{w} beat {l}"
        return f"{head}\n{f.get('round')} · {f.get('score')} · {f.get('city') or ''}\nWhat did you make of it?\n#padel #BeyondPadel " + ("#PremierPadel" if (f.get("level") or "").startswith("PREMIER") else "#FIPTour")
    if e["kind"] == "newpairs":
        ps = f.get("pairs") or []
        lines = [f"{' / '.join(x['pair'])} (before: {' and '.join(x['previous_partners'])})" for x in ps[:4]]
        return (f"New pair alert 🆕 {f.get('tournament')}\nFirst tournament together:\n" + "\n".join(lines)
                + "\nWhich new partnership works best?\n#padel #BeyondPadel #PremierPadel")
    if e["kind"] == "race":
        b = f.get("bubble") or []
        ins = [x["line"] for x in b if x["status"] == "IN"][-2:]
        outs = [x["line"] for x in b if x["status"] == "OUT"][:2]
        return (f"Race to the Finals · {f.get('weeks_to_go')} weeks to go 🏁\nOnly the top 8 pairs make {f.get('finals')}.\n"
                + (f"Holding on: {', '.join(ins)}\n" if ins else "") + (f"Chasing: {', '.join(outs)}\n" if outs else "")
                + "Who makes it?\n#padel #BeyondPadel #PremierPadel")
    if e["kind"] == "top10":
        nw = f.get("new") or []
        return ("New in the top 10 ⬆️\n" + "\n".join(f"{x['name']}: #{x['previous']} → #{x['ranking']}" for x in nw)
                + f"\nOfficial {f.get('category')} ranking of {f.get('date')}.\nWho is next?\n#padel #BeyondPadel")
    if e["kind"] == "tour_preview":
        s = f.get("top_seeds") or {}
        bits = [f"{c_.title()}: " + " / ".join(" / ".join(x.get("short") or x["pair"]) for x in (s.get(c_) or [])[:1]) for c_ in ("men", "women") if s.get(c_)]
        ch = f.get("defending_champions") or []
        return (f"{f.get('tournament')} starts {f.get('starts')} 🎾\nTop seeds · " + " · ".join(bits) + "\n"
                + (f"Defending champions: {' · '.join(ch)}\n" if ch else "") + "Who are you backing?\n#padel #BeyondPadel #PremierPadel")
    if e["kind"] == "preview":
        return (f"Final day at {f.get('tournament')} 🎾\n{' / '.join(f.get('pair_1', []))} vs {' / '.join(f.get('pair_2', []))}\n"
                f"Who wins? Tell us below.\n#padel #BeyondPadel")
    return f"{(f.get('feature') or '').title()} of the week in padel.\nWho should be on this list next week?\n#padel #BeyondPadel"


def send():
    from zoneinfo import ZoneInfo
    if env("PADEL_PUBLISH", "0") != "1":
        print("Padel: PADEL_PUBLISH não está a 1, nada enviado.")
        return
    url = os.environ.get("MAKE_WEBHOOK_URL")
    if not url:
        return
    import requests
    q = qload()
    now = dt.datetime.now(ZoneInfo("Europe/Lisbon"))
    if not (SEND_FROM <= now.hour < SEND_TO):
        print("Padel: fora do horário de publicação.")
        return
    sent = [e for e in q["queue"] if e.get("sent") and not e.get("skipped")]
    last = max([e.get("sent_ts", 0) for e in sent], default=0)
    if time.time() - last < GAP_MIN * 60:
        return
    for e in q["queue"]:                                           # resultados com mais de 20 h já não saem
        if not e.get("sent") and e["kind"] == "result" and time.time() - e["created"] > 20 * 3600:
            e["sent"], e["skipped"] = True, "stale"
    day0 = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    res_today = sum(1 for e in sent if e["kind"] == "result" and e.get("sent_ts", 0) >= day0)
    cap = MAX_DAY if premier_on(load("tournaments.json", {}), now.date().isoformat()) else min(MAX_DAY, FIP_MAX_DAY)
    pend = [e for e in q["queue"] if not e.get("sent")]
    intro = sorted([e for e in pend if e["kind"] == "intro"], key=lambda e: e["n"])
    if intro:
        pend = intro[:1]                                           # apresentação primeiro, uma de cada vez, por ordem
    order = ([e for e in pend if e["kind"] == "intro"] + [e for e in pend if e["kind"] in ("preview", "tour_preview", "newpairs", "top10", "race")] + [e for e in pend if e["kind"] == "weekly"] +
             sorted([e for e in pend if e["kind"] == "result"], key=lambda e: -e.get("score", 0)))
    for e in order:
        if e["kind"] == "result" and res_today >= cap:
            continue
        img = f"{SITE}/posts/{e['image']}"
        try:
            if requests.head(img, timeout=20).status_code != 200:
                print(f"Padel {e['id']}: imagem ainda não está no site, fica para a próxima.")
                continue
            requests.post(url, json={"image_url": img, "caption": caption(e), "id": f"padel-{e['id']}", "account": "padel",
                                     "tag_username": "", "tag_tournament": "", "user_tags": []}, timeout=30).raise_for_status()
        except Exception as ex:
            print(f"Padel {e['id']}: falhou ({type(ex).__name__}).")
            break
        e["sent"], e["sent_ts"] = True, time.time()
        print(f"Padel {e['id']}: enviado.")
        break
    qsave(q)


if __name__ == "__main__":
    {"make": make, "send": send}.get(sys.argv[1] if len(sys.argv) > 1 else "make", make)()
