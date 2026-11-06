"""Histórico de carreira agregado por jogador (sem guardar jogos individuais).

Fonte: bases de dados de Jeff Sackmann (Tennis Abstract), licença CC BY-NC-SA 4.0
  https://github.com/JeffSackmann/tennis_atp  e  https://github.com/JeffSackmann/tennis_wta
Uso só enquanto o site não tiver rendimento comercial (anúncios, afiliados, patrocínios).
Desligar: variável HISTORY=0 (o site volta aos dados próprios) e apagar history.json.

    python history.py            # descarrega e agrega (no máx. 1 vez por semana)
    python history.py --force
"""
import csv, io, json, os, re, sys, time, unicodedata

OUT = "history.json"
YEARS = int(os.environ.get("HISTORY_YEARS") or "12")
EVERY_D = 7
BASE = "https://raw.githubusercontent.com/JeffSackmann/{repo}/master/{f}"
MIRROR = os.environ.get("HISTORY_MIRROR_URL") or "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main/{sub}/{f}"
FILES = [("tennis_atp", "atp_matches_{y}.csv", "atp"), ("tennis_atp", "atp_matches_qual_chall_{y}.csv", "chall"),
         ("tennis_atp", "atp_matches_futures_{y}.csv", "itf"),
         ("tennis_wta", "wta_matches_{y}.csv", "wta"), ("tennis_wta", "wta_matches_qual_itf_{y}.csv", "itf")]
LVL = {"G": "Grand Slam", "M": "Masters 1000", "A": "Tour", "P": "Tour", "PM": "Tour", "F": "Tour Finals", "O": "Olympics",
       "C": "Challenger", "I": "Tour", "T": "Tour", "W": "Tour"}


def slug(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def _get(repo, fname):
    d = os.environ.get("HISTORY_DIR")
    if d:   # teste local
        p = os.path.join(d, fname)
        return open(p, encoding="utf-8").read() if os.path.exists(p) else None
    import requests
    for br in ("master", "main"):
        try:
            r = requests.get(BASE.format(repo=repo, f=fname).replace("/master/", f"/{br}/"), timeout=60,
                             headers={"User-Agent": "beyond100-history"})
        except Exception as e:
            print("Histórico: erro de rede", fname, e)
            return None
        if r.status_code == 200:
            return r.text
        _ERR.append(f"{fname}:{br}:{r.status_code}")
    # o repositório original deixou de estar disponível (404 desde ~setembro de 2026); cópia de arquivo, só se HISTORY_MIRROR=1
    if os.environ.get("HISTORY_MIRROR") == "1":
        sub = "wta" if repo.endswith("wta") else "atp"
        try:
            r = requests.get(MIRROR.format(sub=sub, f=fname), timeout=60, headers={"User-Agent": "beyond100-history"})
            if r.status_code == 200:
                return r.text
            _ERR.append(f"mirror:{fname}:{r.status_code}")
        except Exception as e:
            _ERR.append(f"mirror:{fname}:{type(e).__name__}")
    return None


_ERR = []


def _int(x):
    try:
        return int(float(x))
    except Exception:
        return None


RANK_FILES = [("tennis_atp", "atp_players.csv", ["atp_rankings_10s.csv", "atp_rankings_20s.csv", "atp_rankings_current.csv"]),
              ("tennis_wta", "wta_players.csv", ["wta_rankings_10s.csv", "wta_rankings_20s.csv", "wta_rankings_current.csv"])]


def _tracked():
    """Jogadores que o site acompanha (results.json + ranks.json): só esses recebem a evolução do ranking, para o ficheiro não crescer demais."""
    out = set()
    try:
        for r in json.load(open("results.json", encoding="utf-8")):
            for k in ("p1", "p2"):
                out.add(slug((r.get(k) or {}).get("name", "")))
    except Exception:
        pass
    try:
        for v in json.load(open("ranks.json", encoding="utf-8")).values():
            out.add(slug(v.get("name", "")))
    except Exception:
        pass
    out.discard("")
    return out


def _rankings_and_bio(P, now_y):
    """Evolução do ranking (1 ponto por mês, desde YEARS anos) e dados pessoais públicos (data de nascimento, mão, altura)."""
    want = _tracked()
    if not want:
        print("Histórico: sem lista de jogadores acompanhados, salto rankings.")
        return
    first_y = now_y - YEARS + 1
    n_rk = 0
    for repo, players_f, rank_fs in RANK_FILES:
        txt = _get(repo, players_f)
        if not txt:
            continue
        ids = {}
        for row in csv.DictReader(io.StringIO(txt)):
            name = f"{row.get('name_first', '')} {row.get('name_last', '')}".strip()
            sl = slug(name)
            if sl in want:
                ids[row.get("player_id")] = sl
                e = P.setdefault(sl, {"n": name, "c": row.get("ioc") or "", "w": 0, "l": 0, "s": {}, "y": {}, "t": {}, "fl": 0, "br": None, "bw": None})
                bio = {k: v for k, v in (("dob", row.get("dob")), ("hand", row.get("hand")), ("h", _int(row.get("height")))) if v and v not in ("U", "0")}
                if bio:
                    e["bio"] = bio
        series = {}
        for f in rank_fs:
            txt = _get(repo, f)
            if not txt:
                continue
            for row in csv.DictReader(io.StringIO(txt)):
                pid = row.get("player")
                if pid not in ids:
                    continue
                d = (row.get("ranking_date") or "")[:6]
                if len(d) < 6 or int(d[:4]) < first_y:
                    continue
                r = _int(row.get("rank"))
                if not r:
                    continue
                m = f"{d[:4]}-{d[4:6]}"
                cur = series.setdefault(ids[pid], {})
                if m not in cur or r < cur[m]:
                    cur[m] = r                      # melhor ranking desse mês
        for sl, mm in series.items():
            P[sl]["rk"] = [[m, mm[m]] for m in sorted(mm)]
            best = min(mm.values())
            if P[sl].get("br") is None or best < P[sl]["br"]:
                P[sl]["br"] = best
            n_rk += 1
    print(f"Histórico: evolução do ranking para {n_rk} jogadores acompanhados.")


FINALS = []          # finais de Tour/Challenger dos anos anteriores (para o post "This week in <ano>")


def build():
    now_y = time.gmtime().tm_year
    P = {}
    FINALS.clear()

    def pl(name, ioc):
        e = P.setdefault(slug(name), {"n": name, "c": ioc or "", "w": 0, "l": 0, "s": {}, "y": {}, "t": {}, "fl": 0, "br": None, "bw": None})
        if ioc and not e["c"]:
            e["c"] = ioc
        return e

    for y in range(now_y - YEARS + 1, now_y + 1):
        for repo, tpl, kind in FILES:
            txt = _get(repo, tpl.format(y=y))
            if not txt:
                continue
            for row in csv.DictReader(io.StringIO(txt)):
                rd = (row.get("round") or "").upper()
                if rd.startswith("Q") or rd == "RR" and kind == "x":
                    continue
                lvl = row.get("tourney_level") or ""
                lab = "ITF" if kind == "itf" else ("Challenger" if kind == "chall" else LVL.get(lvl, "Tour"))
                if lvl == "D":
                    lab = "Davis Cup"
                sf = (row.get("surface") or "").title()
                wn, ln = row.get("winner_name"), row.get("loser_name")
                if not wn or not ln:
                    continue
                W, Lz = pl(wn, row.get("winner_ioc")), pl(ln, row.get("loser_ioc"))
                wr, lr = _int(row.get("winner_rank")), _int(row.get("loser_rank"))
                for e, i in ((W, 0), (Lz, 1)):
                    e["w" if i == 0 else "l"] += 1
                    if sf:
                        e["s"].setdefault(sf, [0, 0])[i] += 1
                    e["y"].setdefault(str(y), [0, 0])[i] += 1
                    e["t"].setdefault(lab, [0, 0, 0])[i] += 1
                if rd == "F" and lab != "Davis Cup":
                    W["t"][lab][2] += 1
                    Lz["fl"] += 1
                    td = row.get("tourney_date") or ""
                    if lab in ("Challenger", "Tour", "Masters 1000", "Grand Slam") and len(td) == 8 and td.isdigit():
                        FINALS.append({"d": f"{td[:4]}-{td[4:6]}-{td[6:]}", "t": row.get("tourney_name") or "", "lv": lab,
                                       "g": "w" if repo.endswith("wta") else "m", "w": wn, "l": ln, "sc": row.get("score") or "",
                                       "wr": wr, "lr": lr})
                for e, r in ((W, wr), (Lz, lr)):
                    if r and (e["br"] is None or r < e["br"]):
                        e["br"] = r
                if lr and (W["bw"] is None or lr < W["bw"][0]):
                    W["bw"] = [lr, ln, y]
    P = {k: v for k, v in P.items() if k and v["w"] + v["l"] >= 5}
    try:
        _rankings_and_bio(P, now_y)
    except Exception as e:                       # o histórico de jogos continua a valer mesmo que isto falhe
        print("Histórico: rankings/bio falharam:", e)
    if not P:
        print("Histórico: nada descarregado. Primeiros erros:", _ERR[:6])
        return
    _last = max([f["d"] for f in FINALS] + [m + "-01" for v in P.values() for m, _ in (v.get("rk") or [])[-1:]] + [""])
    out = {"meta": {"from": now_y - YEARS + 1, "to": now_y, "data_to": _last, "built": time.time(), "v": 2}, "p": P, "finals": FINALS[-6000:]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Histórico: {len(P)} jogadores, {now_y - YEARS + 1}–{now_y}.")


if __name__ == "__main__":
    if os.environ.get("HISTORY") == "0":
        print("Histórico desligado (HISTORY=0).")
        sys.exit(0)
    try:
        _d = json.load(open(OUT))
        age = (time.time() - _d["meta"]["built"]) / 86400 if _d.get("p") and _d["meta"].get("v") == 2 else 999   # v2: rankings e bio
    except Exception:
        age = 999
    if age < EVERY_D and "--force" not in sys.argv:
        print(f"Histórico atualizado há {age:.1f} dias, salto.")
        sys.exit(0)
    try:
        build()
    except Exception as e:   # nunca falha o workflow
        print("Histórico: erro", e)
