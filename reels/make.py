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
VERSION = 2                                # 2 = com som
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


HQ_DIR = "reels_hq"


def hq_request(rid, venue):
    """18/11/2026 (Afonso: PoC aprovado, à experiência): guarda o cenário do ponto para a versão 3D (Blender).
    O pedido ao workflow reel_hq.yml sai depois de o estado estar guardado (hq_dispatch), para o workflow já o encontrar."""
    if (os.environ.get("REELS_HQ") or "0").strip() != "1":
        return False
    os.makedirs(HQ_DIR, exist_ok=True)
    json.dump(venue, open(os.path.join(HQ_DIR, rid + ".json"), "w", encoding="utf-8"), ensure_ascii=False)
    return True


def hq_dispatch():
    """Pede ao GitHub a versão 3D dos Reels em fila (hq = queued). O workflow só recebe o id; o cenário fica no repositório de dados."""
    tok, repo = os.environ.get("GH_DISPATCH_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    st = load(); changed = False
    for i in st["items"]:
        if i.get("hq") != "queued": continue
        if not tok or not repo:
            print("reels: sem token para pedir a versão 3D"); break
        try:
            import requests
            r = requests.post(f"https://api.github.com/repos/{repo}/actions/workflows/reel_hq.yml/dispatches", timeout=30,
                              headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"},
                              json={"ref": os.environ.get("HQ_REF", "main"), "inputs": {"id": i["id"]}})
            if r.status_code >= 300:
                print(f"reels: pedido da versão 3D de {i['id']} recusado ({r.status_code})"); i["hq"] = "failed"
            else:
                i["hq"] = "pending"; i["hq_at"] = iso(now())
                print(f"reels: versão 3D de {i['id']} pedida (pronta em ~3 h; até lá fica a versão normal)")
        except Exception as e:
            print(f"reels: pedido da versão 3D falhou ({type(e).__name__})"); continue
        changed = True
    if changed:
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


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
        # 19/11/2026 (Afonso): no padel só UM quadro por torneio (o da final mais disputada); no ténis, um por final
        brs = fs if fs[0]["sport"] == "tennis" else [max(fs, key=lambda f: (drama(f["sets"]), f["gender"] == "men"))]
        for f in brs:
            day = dt.date.fromisoformat(f["date"])
            due = max(now(), at_lisbon(day + dt.timedelta(days=1), 9, 30)) if (both and f["gender"] == "women" and f["sport"] == "tennis") else now()
            jobs.append(("bracket", f, f"{f['key']}-bracket", due))
        # ponto de campeonato: ténis um por final; padel um por torneio (a final mais disputada)
        pts = fs if fs[0]["sport"] == "tennis" else [max(fs, key=lambda f: (drama(f["sets"]), f["gender"] == "women"))]
        for f in pts:
            day = dt.date.fromisoformat(f["date"])
            # 19/11/2026: no padel o ponto 3D passa para 2 dias depois (o vídeo oficial do RBCP chega à segunda) e só sai se não houver vídeo
            jobs.append(("point", f, f"{f['tour_key'] if f['sport'] == 'padel' else f['key']}-point",
                         at_lisbon(day + dt.timedelta(days=2 if f["sport"] == "padel" else 1), 12, 30)))
    return [j for j in jobs if j[2] not in st["done"]]


# ------------------------------------------------------------------ publicação automática (pelo Make, como os posts)
def _today_lis(ts_dt): return ts_dt.astimezone(LIS).date() == now().astimezone(LIS).date()


def sent_today(sport):
    """Reels publicados hoje (Lisboa) numa conta: automáticos (reels.json) e os que marcaste à mão no admin."""
    st = load(); n = 0
    try: manual = set(json.load(open("reel_posted_ids.json", encoding="utf-8")))
    except (OSError, ValueError): manual = set()
    for i in st["items"]:
        if i["sport"] != sport: continue
        if i.get("posted"):
            try:
                if _today_lis(dt.datetime.strptime(i["posted"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)): n += 1
            except ValueError: pass
        elif i["id"] in manual:                    # marcado à mão no admin: conta no dia em que estava marcado
            try:
                if _today_lis(dt.datetime.strptime(i["due"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)): n += 1
            except ValueError: pass
    return n


def _posts_today(sport):
    """Posts (imagens e carrosséis) já publicados hoje nessa conta, com as mesmas contas dos publicadores."""
    day = now().astimezone(LIS).date()
    n = 0
    if sport == "tennis":
        try: arch = {str(x) for x in json.load(open("archived_posts.json", encoding="utf-8"))}
        except (OSError, ValueError): arch = set()
        for fn in ("posts.json", "carousels.json"):
            try: d = json.load(open(fn, encoding="utf-8"))
            except (OSError, ValueError): continue
            rows = [e for v in d.values() for e in v] if isinstance(d, dict) else d
            for e in rows:
                if not e.get("sent") or e.get("skipped") or str(e.get("id")) in arch or not e.get("sent_at"): continue
                try:
                    t = dt.datetime.strptime(e["sent_at"][:16], "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
                    if t.astimezone(LIS).date() == day: n += 1
                except ValueError: pass
    else:
        try: q = json.load(open("padel/data/posts.json", encoding="utf-8")).get("queue", [])
        except (OSError, ValueError, AttributeError): q = []
        day0 = dt.datetime.combine(day, dt.time(0), LIS).timestamp()
        n = sum(1 for e in q if e.get("sent") and not e.get("skipped") and e.get("sent_ts", 0) >= day0)
    return n


def _has_official(st, i):
    """Há Reel com o vídeo oficial (RBCP) deste torneio de padel?"""
    try:
        from padel import rbcp
        return any(x.get("kind") == "rbcp" and rbcp.same_event({"event": x.get("tournament")}, i.get("tournament")) for x in st["items"])
    except Exception:
        return False


def publish():
    """Publica no máximo 1 Reel por execução, à hora marcada, dentro do horário e do máximo de posts do dia (o Reel conta)."""
    import requests
    url = (os.environ.get("MAKE_WEBHOOK_REEL_URL") or "").strip()
    if not url:
        print("reels: sem MAKE_WEBHOOK_REEL_URL, ficam no admin para publicar à mão."); return
    st = load()
    try: manual = set(json.load(open("reel_posted_ids.json", encoding="utf-8")))
    except (OSError, ValueError): manual = set()
    try: approved = set(map(str, json.load(open("reel_approved_ids.json", encoding="utf-8"))))
    except (OSError, ValueError): approved = set()
    E = lambda k, d: (os.environ.get(k) or d).strip()
    cfg = {"tennis": dict(on=E("PUBLISH_AUTO", "0").lower() in ("1", "true", "yes", "on"), a=int(E("SEND_FROM", "8")), b=int(E("SEND_TO", "23")), cap=int(E("DAY_MAX_POSTS", "3"))),
           "padel": dict(on=E("PADEL_PUBLISH", "0") == "1", a=int(E("PADEL_SEND_FROM", "9")), b=int(E("PADEL_SEND_TO", "23")), cap=int(E("PADEL_MAX_POSTS_PER_DAY", "3")))}
    h = now().astimezone(LIS).hour
    changed = False
    order = lambda x: (x["kind"] not in ("rbcp", "rbcp_top3"), x["kind"] != "bracket", x["due"], x["gender"] != "men")   # vídeo oficial (RBCP) primeiro; depois o quadro antes do ponto; masculino primeiro
    for i in sorted(st["items"], key=order):
        if i.get("posted") or i.get("skipped") or i["id"] in manual: continue
        if i.get("approval") == "pending" and i["id"] not in approved:
            continue                                   # Top 3 points: só sai depois de aprovado no admin
        if i["sport"] == "padel" and i["kind"] == "point" and _has_official(st, i):
            i["skipped"] = "vídeo oficial"; changed = True; print(f"reels: {i['id']} não sai (há o vídeo oficial do torneio)"); continue
        due = dt.datetime.strptime(i["due"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        if due > now(): continue
        if (now() - due).total_seconds() > 30 * 3600:
            i["skipped"] = "caducou"; changed = True; print(f"reels: {i['id']} caducou sem sair"); continue
        if i.get("hq") in ("queued", "pending") and (now() - due).total_seconds() < 3 * 3600:
            print(f"reels: {i['id']} espera pela versão 3D"); continue
        c = cfg[i["sport"]]
        if not c["on"] or not (c["a"] <= h < c["b"]): continue
        if sent_today(i["sport"]) >= 1:
            continue                                   # no máximo 1 Reel por dia em cada conta
        used = _posts_today(i["sport"]) + sent_today(i["sport"])
        if used >= c["cap"]:
            print(f"reels: {i['id']} espera (já saíram {used} de {c['cap']} hoje)"); continue
        vid = f"https://beyond100tennis.com/reels/{i['file']}"
        try:
            if requests.head(vid, timeout=20).status_code != 200:
                print(f"reels: {i['id']} ainda não está no site"); continue
            _r = requests.post(url, json={"video_url": vid, "caption": i["caption"], "id": i["id"], "account": i["sport"], "kind": "reel"}, timeout=120)
            _r.raise_for_status()
            import ig_status
            ok, msg = ig_status.parse(_r)
            ig_status.record(i["sport"] + "-reels", i["id"], ok, msg)
            if ok is False:
                i["ig_tries"] = int(i.get("ig_tries") or 0) + 1; i["ig_error"] = msg; changed = True
                if i["ig_tries"] >= 3:
                    i["posted"], i["skipped"] = iso(now()), "instagram: " + msg[:80]
                print(f"reels: o Instagram recusou {i['id']} ({msg[:120]}), tentativa {i['ig_tries']}/3"); break
        except Exception as e:
            print(f"reels: envio de {i['id']} falhou ({type(e).__name__})"); break
        i["posted"] = iso(now()); changed = True
        print(f"reels: {i['id']} enviado para o Instagram ({used + 1}/{c['cap']} hoje)")
        break
    if changed:
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "site"
    st = load(); os.makedirs(DIR, exist_ok=True)
    if "--no-render" not in sys.argv:
        # vídeos feitos antes do som (v < 2) e ainda por publicar: refazem-se uma vez
        old = [i for i in st["items"] if i.get("v", 1) < VERSION and not i.get("posted") and not i.get("skipped")]
        if old:
            st["items"] = [i for i in st["items"] if i not in old]
            st["done"] = [x for x in st["done"] if x not in {i["id"] for i in old}]
            print(f"reels: {len(old)} vídeo(s) antigos voltam a ser feitos com som")
        finals = []
        for fn in (tennis_finals, padel_finals):
            try: finals += fn()
            except Exception as e: print(f"reels: {fn.__name__} falhou: {e}")
        jobs = plan(finals, st)
        if jobs and not ffmpeg_ok():
            print("reels: ffmpeg indisponível, fica para a próxima execução"); jobs = []
        for kind, f, rid, due in jobs[:MAX_RENDER]:
            path = os.path.join(DIR, rid + ".mp4")
            if kind == "point":                        # 18/11/2026: jogada ligada à final e sem repetir as últimas da conta
                try:
                    from reels import plays
                    recent = [i.get("play") for i in st["items"] if i.get("sport") == f["sport"] and i.get("play")][-3:]
                    f["venue"] = dict(f["venue"], gender=f["gender"],
                                      play=plays.choose(f["sport"], f["sets"], f["venue"].get("surface"), f["venue"].get("setting"), recent))
                except Exception as e:
                    print(f"reels: escolha da jogada falhou ({e})")
            try:
                extra = render(kind, f, path)
            except Exception as e:
                print(f"reels: {rid} não foi feito ({e})")
                st["done"].append(rid)                 # não insistir num quadro incompleto
                continue
            item = dict(id=rid, kind=kind, sport=f["sport"], gender=f["gender"], tournament=f["name"], champ=f["champ"],
                        file=os.path.basename(path), due=iso(due), made=iso(now()), caption=caption(kind, f, extra), posted=None, v=VERSION)
            if kind == "point":
                item["play"] = f["venue"].get("play")
                if hq_request(rid, f["venue"]): item["hq"] = "queued"
            st["items"].append(item)
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
    {"publish": publish, "hq": hq_dispatch}.get(sys.argv[1] if len(sys.argv) > 1 else "", main)()
