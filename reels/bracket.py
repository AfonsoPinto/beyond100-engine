"""Reel: o quadro inteiro de um torneio como uma corrida de bolas (dados reais da Padel API).
Cada bola é um par; em cada jogo as duas chocam, a que perde é projetada para fora, a que ganha desce de ronda."""
import argparse, json, math, os, subprocess, sys, random
from PIL import Image, ImageDraw
from reels import common as C
F, seg, ease = C.F, C.seg, C.ease
BG, DEEP, ACC, CREAM, SOFT, RED, LINE = C.BG, C.DEEP, C.ACC, C.CREAM, C.SOFT, C.RED, C.LINE
W, H, FPS, S = 1080, 1920, 30, 2          # S: desenho a 2x para as bolas ficarem lisas
AP = argparse.ArgumentParser()
AP.add_argument("--sport", default="padel"); AP.add_argument("--tid"); AP.add_argument("--cat")
AP.add_argument("--name", default=""); AP.add_argument("--date", default=""); AP.add_argument("--out", default="")
AP.add_argument("--stills", default="")
ARGS = AP.parse_args()
DATA = "padel/data"
TID, CAT = ARGS.tid, ARGS.cat

# ------------------------------------------------------------------ dados
# formato comum: balls[k] = nome, seed (número na bola), tag; jogos g = {t1, t2, w, sets=[(a, b, tba, tbb)]}
SPORT = ARGS.sport
def seed_of(s): return int(s) if s and str(s).isdigit() else None
balls, levels = {}, []          # levels[k] = jogos da ronda k pela ordem do quadro
if SPORT == "padel":
    T = json.load(open(f"{DATA}/tournaments.json"))[TID]
    TNAME = ARGS.name or T["name"].replace(" 2026", "")
    MS = [m for m in json.load(open(f"{DATA}/matches/{TID}.json")) if m["category"] == CAT and m["draw"] == "main" and m["round"] <= 16]
    by = {}
    for m in MS: by.setdefault(m["round"], {})[m["index"]] = m
    if sorted(by, reverse=True) != [16, 8, 4, 2, 1] or len(by[16]) != 16: sys.exit("quadro incompleto (padel)")
    key = lambda team: frozenset(p["id"] for p in team)
    for i in range(16):
        m = by[16][i]
        for side in ("team_1", "team_2"):
            team = m["players"][side]
            balls[key(team)] = dict(name=[p["short_name"] for p in team], seed=seed_of(m["seeds"][side]), tag=m["seeds"][side] or "")
    def tb(x): return x.split("(")[1].rstrip(")") if "(" in x else ""
    for r in (16, 8, 4, 2, 1):
        L = []
        for i in range(len(by[r])):
            m = by[r][i]
            L.append(dict(t1=key(m["players"]["team_1"]), t2=key(m["players"]["team_2"]), w=key(m["players"][m["winner"]]),
                          sets=[(int(x["team_1"].split("(")[0]), int(x["team_2"].split("(")[0]), tb(x["team_1"]), tb(x["team_2"])) for x in m["score"] or []]))
        levels.append(L)
    UNIT, BRAND, HANDLE = "PAIRS", "BEYOND PADEL", "@beyond100.padel"
else:
    d0 = ARGS.date or "9999"
    def _plus(d, n):
        import datetime as _dt
        return (_dt.date.fromisoformat(d) + _dt.timedelta(days=n)).isoformat()
    RS = [r for r in json.load(open("results.json"))
          if r.get("tour") == CAT and not r.get("q") and r["tournament"].split(",")[0].strip() == TID
          and (not ARGS.date or _plus(d0, -16) <= r["date"] <= d0)]
    LV = {"1/16-finals": 0, "Round of 32": 0, "1/8-finals": 1, "Round of 16": 1, "Quarter-finals": 2, "Semi-finals": 3, "Final": 4}
    ms = {}
    for r in RS:
        if r["round"] not in LV: continue
        k = LV[r["round"]]
        sets = []
        for i in range(len(r["games"][0])):
            tbs = r.get("tb") or [[None] * 9, [None] * 9]
            ta, tbb = tbs[0][i] if i < len(tbs[0]) else None, tbs[1][i] if i < len(tbs[1]) else None
            sets.append((r["games"][0][i], r["games"][1][i], "" if ta is None else str(ta), "" if tbb is None else str(tbb)))
        a, b = r["p1"]["name"], r["p2"]["name"]
        for pl in (r["p1"], r["p2"]):
            balls.setdefault(pl["name"], dict(name=[pl["name"].split(" ", 1)[-1]], seed=pl.get("rank"), tag=""))
        ms[(k, (a, b)[r["winner"] - 1])] = dict(t1=a, t2=b, w=(a, b)[r["winner"] - 1], sets=sets)
    # ronda em falta: deduz pelo quadro (quem ganhou a ronda anterior e não aparece)
    for k in range(1, 5):
        prev_w = {g["w"] for (kk, _), g in ms.items() if kk == k - 1}
        here = {p for (kk, _), g in ms.items() if kk == k for p in (g["t1"], g["t2"])}
        need = {g["t1"] for (kk, _), g in ms.items() if kk == k + 1} | {g["t2"] for (kk, _), g in ms.items() if kk == k + 1}
        miss_w = [p for p in need if (k, p) not in ms]; left = sorted(prev_w - here)
        if len(miss_w) == 1 and len(left) == 2 and miss_w[0] in left:
            o = [x for x in left if x != miss_w[0]][0]
            ms[(k, miss_w[0])] = dict(t1=miss_w[0], t2=o, w=miss_w[0], sets=[])
            print("jogo deduzido:", k, miss_w[0], "v", o)
    fins = [g for (kk, _), g in ms.items() if kk == 4]
    if len(fins) != 1: sys.exit("quadro incompleto: final em falta")
    fin = fins[0]
    def tree(g, k):
        if k == 0: return [g]
        return tree(ms[(k - 1, g["t1"])], k - 1) + tree(ms[(k - 1, g["t2"])], k - 1)
    levels = [[] for _ in range(5)]
    def walk(g, k):
        if k > 0:
            for p_ in (g["t1"], g["t2"]):
                if (k - 1, p_) not in ms: sys.exit(f"quadro incompleto: falta o jogo de {p_} na ronda {k - 1}")
                walk(ms[(k - 1, p_)], k - 1)
        levels[k].append(g)
    walk(fin, 4)
    TNAME = ARGS.name or TID
    UNIT, BRAND, HANDLE = "PLAYERS", "BEYOND 100", "@beyond100.tennis"
    for k in balls:
        if balls[k]["seed"] and balls[k]["seed"] > 99: balls[k]["seed"] = None

def score_txt(g):
    out = []
    for a, b, ta, tb_ in g["sets"]:
        if g["w"] == g["t2"]: a, b, ta, tb_ = b, a, tb_, ta
        lo = ta if a < b else tb_
        out.append(f"{a}-{b}" + (f"({lo})" if lo and min(a, b) == 6 and max(a, b) == 7 else ""))
    return "  ".join(out)

slots = []
for g in levels[0]: slots += [g["t1"], g["t2"]]
if len(slots) != 32: sys.exit("quadro incompleto: não há 32 na ronda de 32")
ROWS, steps = [list(slots)], []
for k in range(5):
    games, nxt = [], []
    for i, g in enumerate(levels[k]):
        a, b = ROWS[-1][2 * i], ROWS[-1][2 * i + 1]
        assert g["w"] in (a, b), (k, i, g, a, b)
        games.append((2 * i, 2 * i + 1, g["w"], b if g["w"] == a else a, g)); nxt.append(g["w"])
    steps.append(games); ROWS.append(nxt)
CHAMP = ROWS[-1][0]

# ------------------------------------------------------------------ geometria (coordenadas 1x)
X0, X1 = 88, 992
Y = [470, 640, 810, 990, 1170, 1300]
R = [11, 14, 19, 27, 38, 58]
def sx(k, j): n = 32 >> k; sp = (X1 - X0) / n; return X0 + sp * (j + 0.5)
def gy(k): return Y[k] + (Y[k + 1] - Y[k]) * 0.52

ST = [1.5, 3.7, 6.0, 8.8, 11.7]
GAP = [0.045, 0.09, 0.2, 0.4, 0]
DUR = [1.0, 1.1, 1.35, 1.6, 0]
FIN = dict(meet=12.35, hits=[12.9, 13.75, 14.65], ko=14.65, land=15.5)
TEN = SPORT != 'padel'
GEN = 'WOMEN' if CAT in ('women', 'wta') else 'MEN'

END = 20.5

def lerp(a, b, u): return a + (b - a) * u
def poly(pts, u):
    """ponto à distância u (0-1) ao longo de uma linha quebrada"""
    L = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; tot = sum(L); d = u * tot
    for i, l in enumerate(L):
        if d <= l or i == len(L) - 1:
            v = 0 if l == 0 else min(1, d / l); return (lerp(pts[i][0], pts[i + 1][0], v), lerp(pts[i][1], pts[i + 1][1], v)), tot
        d -= l
def ease_in(u): u = max(0, min(1, u)); return u * u
def back(u):
    u = max(0, min(1, u)); c = 1.6; return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2

# para cada bola: em que ronda cai
fate = {}
for k, games in enumerate(steps):
    for gi, (ia, ib, wk, lk, m) in enumerate(games):
        fate[lk] = (k, gi)
slot_in_row = [{kk: j for j, kk in enumerate(row)} for row in ROWS]

def gate_t(k, gi): return ST[k] + GAP[k] * gi

def state(bk, t):
    """posição (x, y), raio, alfa, ângulo de rotação"""
    # entrada: as bolas caem do topo para a linha de partida
    j0 = slot_in_row[0][bk]
    t_in = 0.05 + 0.025 * j0
    if t < t_in + 0.8:
        u = (t - t_in) / 0.8
        if u < 0: return None
        y = lerp(330, Y[0], ease_in(min(1, u * 1.25))) if u < 0.8 else Y[0] - 26 * math.sin((u - 0.8) / 0.2 * math.pi)
        return (sx(0, j0), y), R[0], 1, y / R[0]
    for k in range(5):
        j = slot_in_row[k][bk]; gi = j // 2
        x, y = sx(k, j), Y[k]
        xm, yg, xn, yn = sx(k + 1, gi) if k < 4 else 540, gy(k), sx(k + 1, gi) if k < 4 else 540, Y[k + 1]
        side = -1 if j % 2 == 0 else 1
        won = slot_in_row[k + 1].get(bk) is not None
        r0, r1 = R[k], R[k + 1]
        if k == 4:
            return final_state(bk, t, x, y, side, won)
        ts = gate_t(k, gi); D = DUR[k]
        if t < ts: return (x, y), r0, 1, 0
        u = (t - ts) / D
        path = [(x, y), (x, yg), (xm + side * r0, yg)]
        if u < 0.5:
            (px, py), tot = poly(path, ease_in(u / 0.5)); return (px, py), r0, 1, tot * ease_in(u / 0.5) / r0 * side
        tot = poly(path, 1)[1]
        if won:
            if u >= 1: continue
            v = (u - 0.5) / 0.5
            px, py = lerp(xm + side * r0, xn, ease(v * 1.6)), lerp(yg, yn, back(v))
            return (px, py), lerp(r0, r1, ease(v)), 1, (tot + 60 * v) / r0 * side
        # perdeu: voo para fora com gravidade
        tt = (t - ts - 0.5 * D) * 1.0
        vx, vy, g = side * (300 + 40 * k), -360 - 40 * k, 1900
        px, py = xm + side * r0 + vx * tt, yg + vy * tt + 0.5 * g * tt * tt
        a = max(0, 1 - tt / 0.9)
        if a <= 0 or py > H + 60: return None
        return (px, py), r0, a, (tot + 900 * tt) / r0 * side

def final_state(bk, t, x, y, side, won):
    ts, meet = ST[4], FIN["meet"]
    r = R[4]; xm, yg = 540, gy(4)
    if t < ts: return (x, y), r, 1, 0
    contact = xm + side * r
    if t < meet:
        u = (t - ts) / (meet - ts)
        (px, py), tot = poly([(x, y), (x, yg), (contact, yg)], ease_in(u)); return (px, py), r, 1, tot * ease_in(u) / r * side
    # trocas de pancadas: afastam-se e voltam a chocar em cada set
    hits = FIN["hits"]
    for i, h in enumerate(hits[:-1]):
        nh = hits[i + 1]
        if t < nh:
            dt = (t - max(meet, h)) / (nh - max(meet, h)) if t >= h else 0
            # quem perde o set é empurrado mais para trás
            sw = set_winner(i)
            push = 150 if sw != bk else 70
            off = push * math.sin(math.pi * min(1, max(0, dt)))
            return (contact + side * off, yg - 0.35 * off), r, 1, off / r * side
    ko = FIN["ko"]
    if t < ko: return (contact, yg), r, 1, 0
    tt = t - ko
    if won:
        v = min(1, tt / (FIN["land"] - ko))
        return (lerp(contact, 540, ease(v)), lerp(yg, Y[5], back(v))), lerp(r, R[5], ease(v)), 1, 0
    vx, vy, g = side * 520, -900, 2100
    px, py = contact + vx * tt, yg + vy * tt + 0.5 * g * tt * tt
    a = max(0, 1 - tt / 1.3)
    if a <= 0: return None
    return (px, py), r, a, 900 * tt / r * side

FM = steps[4][0][4]
FIN['hits'] = [12.9, 13.75, 14.65][-len(FM['sets']):] if len(FM['sets']) <= 3 else [12.9 + i * 0.44 for i in range(len(FM['sets']))]
FIN['ko'] = FIN['hits'][-1]
HITS = FIN['hits']
def set_winner(i):
    a, b = FM["sets"][i][:2]
    return FM["t1"] if a > b else FM["t2"]

# ------------------------------------------------------------------ desenho
def ball(d, x, y, r, a, ang, seed, hi=None):
    X, Yy, Rr = x * S, y * S, r * S
    al = int(255 * a)
    d.ellipse([X - Rr, Yy - Rr * 0.35 + Rr * 1.05, X + Rr, Yy + Rr * 0.35 + Rr * 1.05], fill=(0, 0, 0, int(70 * a)))   # sombra
    col = ACC
    if hi: d.ellipse([X - Rr * 1.9, Yy - Rr * 1.9, X + Rr * 1.9, Yy + Rr * 1.9], fill=hi + (int(70 * a),))
    d.ellipse([X - Rr, Yy - Rr, X + Rr, Yy + Rr], fill=col + (al,))
    d.ellipse([X - Rr * 0.55, Yy - Rr * 0.75, X - Rr * 0.05, Yy - Rr * 0.3], fill=(255, 255, 230, int(90 * a)))       # brilho
    # costura da bola, a rodar
    for sgn in (-1, 1):
        cx = X + sgn * Rr * 1.15 * math.cos(ang); cy = Yy + sgn * Rr * 1.15 * math.sin(ang)
        bb = [cx - Rr * 0.85, cy - Rr * 0.85, cx + Rr * 0.85, cy + Rr * 0.85]
        st = math.degrees(ang) + (180 if sgn > 0 else 0)
        d.arc(bb, st - 52, st + 52, fill=(255, 255, 245, int(200 * a)), width=max(2, int(Rr * 0.11)))
    if seed and r >= 11:
        f = F("k", int(Rr * (0.95 if seed < 10 else 0.8)))
        d.text((X, Yy + Rr * 0.04), str(seed), font=f, fill=DEEP + (al,), anchor="mm")

def lines(d, t, glow):
    for k, games in enumerate(steps):
        for gi, (ia, ib, wk, lk, m) in enumerate(games):
            xm = sx(k + 1, gi) if k < 4 else 540
            yg, yn = gy(k), Y[k + 1]
            for j in (ia, ib):
                x = sx(k, j)
                d.line([(x * S, Y[k] * S), (x * S, yg * S), (xm * S, yg * S)], fill=LINE + (34,), width=2 * S)
            d.line([(xm * S, yg * S), (xm * S, yn * S)], fill=LINE + (34,), width=2 * S)
    # o caminho do campeão, desenhado aos poucos no fim
    if glow > 0:
        pts = []
        for k in range(5):
            j = slot_in_row[k][CHAMP]; xm = sx(k + 1, j // 2) if k < 4 else 540
            pts += [(sx(k, j), Y[k]), (sx(k, j), gy(k)), (xm, gy(k))]
        pts.append((540, Y[5]))
        tot = poly(pts, 1)[1]; n = 160
        seq = [poly(pts, glow * i / n)[0] for i in range(n + 1)]
        d.line([(x * S, y * S) for x, y in seq], fill=ACC + (230,), width=5 * S, joint="curve")
    # lugares vazios na linha de partida
    for j in range(32):
        x = sx(0, j) * S; r = R[0] * S * 0.55
        d.ellipse([x - r, Y[0] * S - r, x + r, Y[0] * S + r], outline=LINE + (40,), width=S)

impacts = []
for k, games in enumerate(steps[:4]):
    for gi, g in enumerate(games):
        impacts.append((gate_t(k, gi) + 0.5 * DUR[k], sx(k + 1, gi), gy(k), R[k], g[3]))
for h in FIN["hits"]: impacts.append((h, 540, gy(4), R[4], None))

def upsets():
    out = []
    for k, games in enumerate(steps[:4]):
        best = None
        for gi, (ia, ib, wk, lk, m) in enumerate(games):
            ls, ws = balls[lk]["seed"], balls[wk]["seed"]
            if ls and (ws is None or ws - ls >= 4) and (not TEN or (ls <= 30 and (ws is None or ws >= ls + 15))):
                if best is None or ls < best[0]: best = (ls, gi, wk, lk)
        if best: out.append((gate_t(k, best[1]) + 0.5 * DUR[k], k, best))
    return out
UPS = upsets()
RNAME = ["ROUND OF 32", "ROUND OF 16", "QUARTER-FINALS", "SEMI-FINALS", "FINAL"]

def nm(k): return " / ".join(balls[k]["name"])
def who(k):
    b = balls[k]
    if b["seed"]: return f"world No. {b['seed']}" if TEN else f"#{b['seed']} seeds"
    return {"Q": "qualifiers", "WC": "wildcards", "LL": "lucky losers"}.get(b["tag"], "an unseeded pair")

CAMK = [(0, 1.0, 960), (1.4, 1.0, 960), (3.5, 1.08, 900), (5.8, 1.18, 960), (8.6, 1.2, 1040), (11.4, 1.45, 1190), (15.6, 1.45, 1190), (16.6, 1.0, 960), (END, 1.0, 960)]
def cam(t):
    for (a, za, ya), (b, zb, yb) in zip(CAMK, CAMK[1:]):
        if a <= t <= b:
            u = ease((t - a) / (b - a)) if b > a else 1
            return lerp(za, zb, u), lerp(ya, yb, u)
    return 1.0, 960
def _bg():
    g = Image.new("RGBA", (W * S, H * S), DEEP + (255,)); d = ImageDraw.Draw(g)
    for i in range(60):
        k = i / 60; r = (1 - k) * 1500 * S
        col = tuple(int(DEEP[j] + (BG[j] + 12 - DEEP[j]) * k) for j in range(3))
        d.ellipse([540 * S - r, 1000 * S - r * 1.2, 540 * S + r, 1000 * S + r * 1.2], fill=col + (255,))
    return g
BGIMG = _bg()
def frame(t):
    world = BGIMG.copy()
    d = ImageDraw.Draw(world, "RGBA")
    glow = seg(t, 16.6, 18.4) if t > 16.6 else 0
    lines(d, t, glow)
    # impactos: anel e faíscas
    for (ti, x, y, r, lk) in impacts:
        dt = t - ti
        if 0 <= dt < 0.35:
            v = dt / 0.35; rr = (r * 1.2 + 3.2 * r * v) * S
            d.ellipse([x * S - rr, y * S - rr, x * S + rr, y * S + rr], outline=CREAM + (int(230 * (1 - v)),), width=3 * S)
            rnd = random.Random(int(ti * 1000 + x))
            for q in range(10):
                an = rnd.uniform(0, 2 * math.pi); a0, a1 = (r * 1.3 + 2.6 * r * v) * S, (r * 1.3 + 2.6 * r * v + r * 1.1) * S
                d.line([(x * S + a0 * math.cos(an), y * S + a0 * math.sin(an)), (x * S + a1 * math.cos(an), y * S + a1 * math.sin(an))],
                       fill=ACC + (int(255 * (1 - v)),), width=3 * S)
    # bolas (as que caem por cima)
    up_keys = {u[2][3]: u[0] for u in UPS}
    drawn = []
    for bk in balls:
        s = state(bk, t)
        if s: drawn.append((s[2] < 1, bk, s))
    for _, bk, ((x, y), r, a, ang) in sorted(drawn, key=lambda z: z[0]):
        hi = RED if bk in up_keys and 0 <= t - up_keys[bk] < 1.2 else None
        ball(d, x, y, r, a, ang, balls[bk]["seed"], hi)
        # nomes a partir das meias-finais
        k_now = max(k for k in range(6) if bk in slot_in_row[k])
        if a == 1 and r >= R[3] - 0.5 and k_now == 3 and t < ST[4] + 0.4:
            f = F("x", int((20 if r < 34 else 24) * S))
            for li, n_ in enumerate(balls[bk]["name"]):
                d.text((x * S, (y + r + 14 + li * (r * 0.0 + 26)) * S), n_.upper(), font=f, fill=CREAM + (230,), anchor="ma")
    # resultado de cada jogo junto ao cruzamento (quartos e meias)
    for k in (2, 3):
        for gi, (ia, ib, wk, lk, m) in enumerate(steps[k]):
            ti = gate_t(k, gi) + 0.5 * DUR[k]; dt = t - ti
            if 0 < dt < 2.2 and t < ST[4]:
                a = int(255 * min(1, dt / 0.2) * min(1, (2.2 - dt) / 0.3))
                f = F("x", 21 * S); x = sx(k + 1, gi)
                txt = score_txt(m)
                if not txt: continue
                tw = d.textlength(txt, font=f)
                yy = gy(k) - R[k] - 46
                d.rounded_rectangle([x * S - tw / 2 - 14 * S, yy * S, x * S + tw / 2 + 14 * S, (yy + 34) * S], radius=17 * S, fill=DEEP + (a,))
                d.text((x * S, (yy + 17) * S), txt, font=f, fill=CREAM + (a,), anchor="mm")
    z, fy = cam(t)
    sh = 0
    for (ti, *_r) in UPS:
        if 0 <= t - ti < 0.3: sh = 9 * (1 - (t - ti) / 0.3)
    rnd = random.Random(int(t * 1000))
    ox, oy = rnd.uniform(-sh, sh) * S, rnd.uniform(-sh, sh) * S
    cw, ch = W * S / z, H * S / z
    cx0, cy0 = 540 * S - cw / 2 + ox, max(0, min(H * S - ch, fy * S - ch / 2)) + oy
    im = world.resize((W, H), Image.LANCZOS, box=(cx0, cy0, cx0 + cw, cy0 + ch)).convert("RGB")
    hud(ImageDraw.Draw(im, "RGBA"), t)
    return im

def hud(d, t):
    d.rectangle([0, 0, W, 400], fill=BG)
    for i in range(50): d.line([(0, 400 + i), (W, 400 + i)], fill=BG + (int(255 * (1 - i / 50)),))
    d.text((80, 120), BRAND, font=F("k", 32), fill=CREAM)
    d.text((W - 160, 120), HANDLE, font=F("b", 28), fill=SOFT, anchor="ra")
    kick = f"{TNAME.upper()} · {GEN}'S DRAW" if t < 18.6 else "FOLLOW FOR EVERY DRAW"
    d.text((80, 180), kick, font=F("x", 32), fill=ACC)
    # título: o gancho, depois os campeões
    if t < 15.4:
        d.text((80, 228), "LAST 32.", font=F("d", 96), fill=CREAM)
        d.text((80, 322), "1 TITLE.", font=F("d", 96), fill=ACC)
    else:
        a = int(255 * seg(t, 15.4, 15.8))
        d.text((80, 232), "CHAMPIONS", font=F("d", 104), fill=ACC + (a,))
    # ronda em curso e quantos sobram
    k = max([i for i in range(5) if t >= ST[i]] or [0])
    if 1.3 < t < 15.4:
        alive = sum(1 for bk in balls if not (bk in fate and t >= gate_t(*fate[bk]) + (0.5 * DUR[fate[bk][0]] if fate[bk][0] < 4 else FIN["ko"] - ST[4])))
        d.text((W - 88, 236), RNAME[k], font=F("x", 26), fill=SOFT, anchor="ra")
        d.text((W - 88, 268), str(alive), font=F("d", 96), fill=CREAM, anchor="ra")
        d.text((W - 88, 380), "LEFT", font=F("x", 26), fill=SOFT, anchor="ra")
    # surpresas
    for i, (ti, kk, (ls, gi, wk, lk)) in enumerate(UPS):
        nt = UPS[i + 1][0] if i + 1 < len(UPS) else ti + 2.3
        e = min(nt, ti + 2.3)
        if ti <= t < e:
            a = int(255 * min(1, (t - ti) / 0.2) * min(1, (e - t) / 0.25))
            card = [80, 1360, W - 160, 1478]
            d.rounded_rectangle(card, radius=24, fill=DEEP + (a,))
            d.rounded_rectangle([80, 1360, 92, 1478], radius=6, fill=RED + (a,))
            d.text((116, 1378), f"UPSET · {RNAME[kk]}", font=F("x", 24), fill=RED + (a,))
            d.text((116, 1414), (f"No. {ls} " if TEN else f"#{ls} ") + f"{nm(lk)} out", font=F("x", 34), fill=CREAM + (a,))
            d.text((W - 190, 1378), f"by {who(wk)}", font=F("b", 24), fill=SOFT + (a,), anchor="ra")
    # placar da final
    if ST[4] + 0.3 < t < 15.9:
        a = int(255 * seg(t, ST[4] + 0.3, ST[4] + 0.7) * (1 - seg(t, 15.5, 15.9)))
        x0, y0 = 88, 470
        d.rounded_rectangle([x0, y0, W - x0, y0 + 190], radius=26, fill=DEEP + (a,))
        tk = [FM["t1"], FM["t2"]]
        for row, kk in enumerate(tk):
            yy = y0 + 34 + row * 72
            sd = balls[kk]['seed']
            d.text((x0 + 34, yy), ((f'No.{sd}  ' if TEN else f'#{sd}  ') if sd else '') + nm(kk).upper(), font=F("x", 30), fill=CREAM + (a,))
            for i, st in enumerate(FM["sets"]):
                if t < HITS[i]: continue
                g, o = (st[0], st[1]) if row == 0 else (st[1], st[0])
                d.text((W - x0 - 80 * len(FM["sets"]) - 10 + i * 80, yy - 4), str(g), font=F("k", 44), fill=(ACC if g > o else SOFT) + (a,))
    # cartão dos campeões
    if t > 15.6:
        a = int(255 * seg(t, 15.6, 16.1))
        ch = CHAMP; b = balls[ch]
        wins = 5 - (1 if any(bk == ch for bk in []) else 0)
        played = [g[4] for k_ in range(5) for g in steps[k_] if g[2] == ch]
        lost_sets = 0
        for m in played:
            lost_sets += sum(1 for st in m["sets"] if (st[0] < st[1]) == (m["t1"] == ch))
        d.text((540, 1412), nm(ch).upper(), font=F("d", 64), fill=CREAM + (a,), anchor="mm")
        lab = (f"World No. {b['seed']} · " if TEN else f"#{b['seed']} seeds · ") if b['seed'] else ''
        sub = f"{lab}{len(played)} wins · {lost_sets} set{'s' if lost_sets != 1 else ''} dropped"
        d.text((540, 1474), sub, font=F("b", 28), fill=SOFT + (a,), anchor="mm")

def render(out, total):
    tmp = out[:-4] + ".part.mp4"
    p = C.encoder(tmp, W, H, FPS)
    for i in range(int(total * FPS)):
        im = frame(i / FPS)
        k = seg(i / FPS, total - 0.4, total)
        if k > 0: im = Image.blend(im, Image.new("RGB", (W, H), BG), k)
        p.stdin.write(im.tobytes())
    p.stdin.close()
    if p.wait() != 0: sys.exit("ffmpeg falhou")
    try:
        from reels import sound
        m = sound.Mix(total)
        m.beat(0.0, total - 0.6, bpm=104, mute=[(11.2, 15.45)])
        m.pad(0.0, total, vol=0.04)
        for k in range(4): m.whoosh(ST[k] - 0.25, 0.4, 0.22)
        for (ti, x, y, r, lk) in impacts:
            v = {R[0]: 0.16, R[1]: 0.22, R[2]: 0.32, R[3]: 0.45}.get(r, 0.95)
            m.pop(ti, v, 1.0 if r < R[4] else 0.8)
            if r >= R[4]: m.thock(ti + 0.02, 0.5)
        for (ti, *_r) in UPS: m.boom(ti, 0.55)
        m.heartbeat(11.3, FIN["land"] - 0.5, vol=0.6)
        m.riser(FIN["ko"] - 1.6, FIN["land"], 0.18)
        m.crowd(ST[4] - 0.3, total, 0.05, swell=(FIN["land"], 0.55))
        m.boom(FIN["land"], 0.9)
        wav = tmp[:-4] + ".wav"; m.write(wav, total)
        ok = sound.mux(tmp, wav, out); os.remove(wav)
        if ok: os.remove(tmp); return
    except Exception as e:
        print("som falhou:", type(e).__name__, e, file=sys.stderr)
    os.replace(tmp, out)

if __name__ == "__main__":
    if ARGS.stills:
        for t in [float(x) for x in ARGS.stills.split(",")]:
            frame(t).save(f"{ARGS.out}_{t:05.2f}.jpg", quality=88)
    else:
        render(ARGS.out, END)
        print(json.dumps({"champ": nm(CHAMP), "ups": [(RNAME[k], nm(lk), nm(wk)) for (_t, k, (ls, gi, wk, lk)) in UPS]}))
