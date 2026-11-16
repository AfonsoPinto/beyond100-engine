"""Gera os Reels dos torneios grandes quando a final acaba e põe-nos no admin para publicar à mão (com música do Instagram).

  python -m reels.make site            deteta finais novas, gera os vídeos e copia-os para site/reels/
  python -m reels.make site --no-render  só copia os vídeos já feitos (atualizações rápidas)

Calendário (aprovado a 16/11/2026):
  - quadro do torneio ("Last 32. 1 title."): na noite da final; o quadro feminino passa para a manhã seguinte (09:30)
    quando o masculino do mesmo torneio também sai, para não haver dois Reels iguais na mesma noite;
  - ponto de campeonato: no dia seguinte às 12:30 (Lisboa); no padel, um por torneio (a final mais disputada).
Torneios: padel P1, P2, Majors e Finals; ténis Grand Slams, 1000 e 500 (ATP e WTA).
Custo: 0 pedidos à API (usa os resultados já guardados). Cada vídeo demora cerca de 1,5 min a gerar."""
import datetime as dt, json, os, shutil, subprocess, sys
from zoneinfo import ZoneInfo

STATE, DIR = "reels.json", "reel_files"          # os vídeos ficam em reel_files/ (reels/ é o código)
LIS = ZoneInfo("Europe/Lisbon")
KEEP = 24                                  # vídeos guardados no repositório (os mais antigos saem)
MAX_RENDER = 3                             # vídeos novos por execução, no máximo
DAYS_BACK = int(os.environ.get("REELS_DAYS_BACK", "2"))   # só finais recentes (nada de recuperar o passado)
PADEL_LEVELS = {"p1", "p2", "major", "finals", "tour_finals", "premier_finals"}
TENNIS_LABELS = {"ATP 1000", "ATP 500", "WTA 1000", "WTA 500"}
SLAMS = ("australian open", "roland garros", "french open", "wimbledon", "us open")
ORD = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}


def now(): return dt.datetime.now(dt.timezone.utc)
def iso(d): return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def at_lisbon(day, hh, mm): return dt.datetime.combine(day, dt.time(hh, mm), LIS)


def load():
    try: return json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError): return {"items": [], "done": []}


def situation(sets):
    """Resultado antes do último jogo, a partir do último set do vencedor (w, l)."""
    w, l = sets[-1]; n = ORD.get(len(sets), f"{len(sets)}th")
    if w == 7 and l == 6: return f"Tie-break in the {n} set"
    if w == 7 and l == 5: return f"6-5 in the {n} set"
    return f"5-{l} in the {n} set"


def drama(sets): return (len(sets), 1 if sets[-1] == (7, 6) else 0, -sum(w - l for w, l in sets))


# ------------------------------------------------------------------ finais de ténis
def tennis_finals():
    sys.path.insert(0, os.getcwd())
    import webapp
    try: rs = json.load(open("results.json", encoding="utf-8"))
    except (OSError, ValueError): return []
    lim = (now() - dt.timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    out = []
    for r in rs:
        if r.get("round") != "Final" or r.get("q") or r.get("tour") not in ("atp", "wta") or r["date"] < lim: continue
        if " / " in r["p1"]["name"] or " / " in r["p2"]["name"]: continue           # pares não
        name = r["tournament"].split(",")[0].strip()
        slam = any(s in name.lower() for s in SLAMS)
        label = None if slam else webapp.category_label(r, r.get("gender"))
        if not slam and label not in TENNIS_LABELS: continue
        wi = r["winner"] - 1; li = 1 - wi
        sets = [(r["games"][wi][i], r["games"][li][i]) for i in range(len(r["games"][0]))]
        champ = r["p" + str(r["winner"])]["name"]
        surf = r.get("surface") or "hard"
        indoor = r.get("indoor")
        chip = (("INDOOR " if indoor else "OUTDOOR ") if indoor is not None else "") + surf.upper() + ("" if indoor is not None else " COURT")
        rows = 24 if slam else 20 if label and label.endswith("1000") else 14
        tag = "Grand Slam" if slam else label
        out.append(dict(key=f"t-{r['id']}", sport="tennis", gender=r.get("gender") or ("women" if r["tour"] == "wta" else "men"),
                        tour_key=f"t-{name}-{r['date'][:7]}", date=r["date"], name=name, tag=tag, champ=champ, sets=sets,
                        bracket=dict(sport="tennis", tid=name, cat=r["tour"], name=f"{name} · {tag}", date=r["date"]),
                        venue=dict(sport="tennis", setting="indoor" if indoor in (True, None) else "day", surface=surf if surf in ("hard", "clay", "grass") else "hard",
                                   rows=rows, board=f"{name.upper()}  ·  {tag.upper()}  ·  FINAL", brand="BEYOND 100", handle="@beyond100.tennis",
                                   kick=f"{name.upper()} · FINAL", chip=chip, sit=situation(sets), champ=champ.upper(),
                                   score="  ".join(f"{a}-{b}" for a, b in sets), title="CHAMPION")))
    return out


# ------------------------------------------------------------------ finais de padel
def padel_finals():
    D = "padel/data"
    try: T = json.load(open(f"{D}/tournaments.json", encoding="utf-8"))
    except (OSError, ValueError): return []
    try: VEN = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "padel", "venues.json"), encoding="utf-8"))
    except (OSError, ValueError): VEN = {}
    lim = (now() - dt.timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")
    out = []
    for tid, t in T.items():
        if (t.get("level") or "").lower() not in PADEL_LEVELS: continue
        try: ms = json.load(open(f"{D}/matches/{tid}.json", encoding="utf-8"))
        except (OSError, ValueError): continue
        name = (t.get("name") or "").replace(" 2026", "").replace(" 2027", "").strip()
        for m in ms:
            if m.get("round") != 1 or m.get("draw") != "main" or m.get("status") != "finished" or (m.get("played_at") or "") < lim: continue
            if not m.get("score"): continue
            wk = m["winner"]; lk = "team_2" if wk == "team_1" else "team_1"
            sets = [(int(s[wk].split("(")[0]), int(s[lk].split("(")[0])) for s in m["score"]]
            champ = " / ".join(p["short_name"] for p in m["players"][wk])
            v = VEN.get(str(tid)) or {}
            setting = v.get("setting") or "indoor"            # sem dados do recinto: visual de pavilhão, sem o afirmar na etiqueta
            hour = int((m.get("scheduled_at_local") or "T20")[11:13] or 20)
            if setting == "outdoor": setting = "night" if hour >= 18 else "day"
            chip = (f"{'INDOOR' if setting == 'indoor' else 'OUTDOOR'} · {v['venue'].upper()}" if v.get("venue") else (t.get("location") or name).upper())
            g = m.get("category") or "men"
            lvl = t["level"].lower()
            out.append(dict(key=f"p-{tid}-{g}", sport="padel", gender=g, tour_key=f"p-{tid}", date=m["played_at"], name=name,
                            tag=lvl.upper(), champ=champ, sets=sets,
                            bracket=dict(sport="padel", tid=str(tid), cat=g, name=name, date=m["played_at"]),
                            venue=dict(sport="padel", setting=setting, surface="padel", rows=16 if lvl == "major" else 14 if lvl in ("p1", "finals") else 10,
                                       board=f"{name.upper()}  ·  FINAL", brand="BEYOND PADEL", handle="@beyond100.padel",
                                       kick=f"{name.upper()} · {'WOMEN' if g == 'women' else 'MEN'}'S FINAL", chip=chip, sit=situation(sets),
                                       champ=champ.upper(), score="  ".join(f"{a}-{b}" for a, b in sets), title="CHAMPIONS")))
    return out


# ------------------------------------------------------------------ legendas
def caption(kind, f, extra=None):
    tags = {"padel": "#padel #premierpadel #padelpro", "tennis": "#tennis " + ("#wta" if f["gender"] == "women" else "#atp")}[f["sport"]]
    site = "beyond100tennis.com/padel" if f["sport"] == "padel" else "beyond100tennis.com"
    score = " ".join(f"{a}-{b}" for a, b in f["sets"])
    verb = "win" if f["sport"] == "padel" else "wins"
    tname = f["name"] if f["sport"] == "padel" else f"{f['name']} ({f['tag']})"
    if kind == "bracket":
        lines = [f"Last 32 to champion in 20 seconds. {f['champ']} {verb} {tname}, {score} 🏆"]
        for rn, lo, wi in (extra or {}).get("ups", [])[:2]:
            lines.append(f"Upset · {rn[0] + rn[1:].lower()}: {lo} out, beaten by {wi}.")
        lines += ["", f"Every draw and result: {site}", "", tags]
    else:
        lines = [f"Championship point at {tname}. {f['champ']} {verb} the final {score}.",
                 "Rally illustrated · score and title real.", "", f"All results: {site}", "", tags]
    return "\n".join(lines)


# ------------------------------------------------------------------ geração
def ffmpeg_ok():
    if shutil.which("ffmpeg"): return True
    subprocess.run("sudo apt-get install -y -qq ffmpeg >/dev/null 2>&1", shell=True)
    return bool(shutil.which("ffmpeg"))


def render(kind, f, path):
    if kind == "bracket":
        b = f["bracket"]
        cmd = [sys.executable, "-m", "reels.bracket", "--sport", b["sport"], "--tid", b["tid"], "--cat", b["cat"], "--name", b["name"], "--date", b["date"], "--out", path]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if p.returncode != 0: raise RuntimeError((p.stderr or p.stdout).strip().splitlines()[-1] if (p.stderr or p.stdout).strip() else "erro")
        try: return json.loads(p.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError): return {}
    cfg = dict(f["venue"], out=path)
    tmp = path + ".json"; json.dump(cfg, open(tmp, "w"))
    try:
        p = subprocess.run([sys.executable, "-m", "reels.point", tmp], capture_output=True, text=True, timeout=600)
    finally:
        os.remove(tmp)
    if p.returncode != 0: raise RuntimeError((p.stderr or "erro").strip().splitlines()[-1])
    return {}


def plan(finals, st):
    """Que vídeos fazer e para quando."""
    jobs = []
    by_t = {}
    for f in finals: by_t.setdefault(f["tour_key"], []).append(f)
    for tk, fs in by_t.items():
        both = {f["gender"] for f in fs} >= {"men", "women"}
        if fs[0]["sport"] == "padel" and not both:
            # no padel há sempre as duas finais: espera pela segunda (ou pelo fim do dia da primeira)
            if now() < at_lisbon(dt.date.fromisoformat(fs[0]["date"]), 23, 30): continue
        for f in fs:
            day = dt.date.fromisoformat(f["date"])
            due = max(now(), at_lisbon(day + dt.timedelta(days=1), 9, 30)) if (both and f["gender"] == "women") else now()
            jobs.append(("bracket", f, f"{f['key']}-bracket", due))
        # ponto de campeonato: ténis um por final; padel um por torneio (a final mais disputada)
        pts = fs if fs[0]["sport"] == "tennis" else [max(fs, key=lambda f: (drama(f["sets"]), f["gender"] == "women"))]
        for f in pts:
            day = dt.date.fromisoformat(f["date"])
            jobs.append(("point", f, f"{f['tour_key'] if f['sport'] == 'padel' else f['key']}-point", at_lisbon(day + dt.timedelta(days=1), 12, 30)))
    return [j for j in jobs if j[2] not in st["done"]]


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "site"
    st = load(); os.makedirs(DIR, exist_ok=True)
    if "--no-render" not in sys.argv:
        finals = []
        for fn in (tennis_finals, padel_finals):
            try: finals += fn()
            except Exception as e: print(f"reels: {fn.__name__} falhou: {e}")
        jobs = plan(finals, st)
        if jobs and not ffmpeg_ok():
            print("reels: ffmpeg indisponível, fica para a próxima execução"); jobs = []
        for kind, f, rid, due in jobs[:MAX_RENDER]:
            path = os.path.join(DIR, rid + ".mp4")
            try:
                extra = render(kind, f, path)
            except Exception as e:
                print(f"reels: {rid} não foi feito ({e})")
                st["done"].append(rid)                 # não insistir num quadro incompleto
                continue
            st["items"].append(dict(id=rid, kind=kind, sport=f["sport"], gender=f["gender"], tournament=f["name"], champ=f["champ"],
                                    file=os.path.basename(path), due=iso(due), made=iso(now()), caption=caption(kind, f, extra), posted=None))
            st["done"].append(rid)
            print(f"reels: {rid} feito ({kind}, para {due.astimezone(LIS):%d/%m %H:%M})")
        # só os mais recentes ficam
        st["items"] = st["items"][-KEEP:]
        keep = {i["file"] for i in st["items"]}
        for fn in os.listdir(DIR):
            if fn.endswith(".mp4") and fn not in keep: os.remove(os.path.join(DIR, fn))
        st["done"] = st["done"][-400:]
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if os.path.isdir(DIR) and os.path.isdir(out_dir):
        shutil.copytree(DIR, os.path.join(out_dir, "reels"), dirs_exist_ok=True)


if __name__ == "__main__":
    main()
