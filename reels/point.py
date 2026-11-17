"""Reel: o ponto de campeonato em 3D (rally ilustrado, figuras estilizadas e anónimas; o resultado é real).
Câmaras de transmissão com cortes, bola com física, rasto e câmara lenta no remate final."""
import json, math, os, subprocess, sys, random
from PIL import Image, ImageDraw, ImageFilter
from reels import common as C
F, seg, ease = C.F, C.seg, C.ease
BG, DEEP, ACC, CREAM, SOFT, RED, LINE, TURF, TURF2, GLASS = C.BG, C.DEEP, C.ACC, C.CREAM, C.SOFT, C.RED, C.LINE, C.TURF, C.TURF2, C.GLASS
W, H, FPS, S = 1080, 1920, 30, 2
G = 9.81
V = json.load(open(sys.argv[1]))          # recinto e textos, escritos por reels.make
VN = "x"
SPORT = V["sport"]
SURF = {"padel": ((24, 92, 160), (8, 34, 58), (235, 242, 250)),
        "hard": ((34, 92, 156), (24, 64, 112), (238, 242, 248)),
        "clay": ((190, 96, 58), (176, 86, 50), (246, 240, 228)),
        "grass": ((78, 150, 66), (64, 128, 56), (245, 245, 240))}[V["surface"]]

# ------------------------------------------------------------------ vetores e câmara
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): l = math.sqrt(dot(a, a)) or 1; return mul(a, 1 / l)
def lerp(a, b, u): return a + (b - a) * u
def vlerp(a, b, u): return tuple(lerp(a[i], b[i], u) for i in range(3))

class Cam:
    def __init__(s, pos, tgt, fov):
        s.p = pos; f = norm(sub(tgt, pos)); r = norm(cross(f, (0, 0, 1))); u = cross(r, f)
        s.f, s.r, s.u = f, r, u; s.foc = (H * S / 2) / math.tan(math.radians(fov) / 2)
    def cam(s, P):
        d = sub(P, s.p); return (dot(d, s.r), dot(d, s.u), dot(d, s.f))
    def scr(s, c):
        x, y, z = c; return (W * S / 2 + s.foc * x / z, H * S / 2 - s.foc * y / z)
    def proj(s, P):
        c = s.cam(P)
        if c[2] < 0.05: return None, None
        return s.scr(c), s.foc / c[2]           # ponto no ecrã, píxeis por metro
    def poly(s, pts):
        """projeta um polígono cortando-o no plano junto à câmara"""
        cs = [s.cam(p) for p in pts]; out = []; n = len(cs); NZ = 0.05
        for i in range(n):
            a, b = cs[i], cs[(i + 1) % n]
            if a[2] >= NZ: out.append(a)
            if (a[2] >= NZ) != (b[2] >= NZ):
                u = (NZ - a[2]) / (b[2] - a[2]); out.append(tuple(lerp(a[j], b[j], u) for j in range(3)))
        return [s.scr(c) for c in out] if len(out) >= 3 else None
    def depth(s, P): return dot(sub(P, s.p), s.f)

# ------------------------------------------------------------------ campo
if SPORT == "padel":
    HW, HL, NET = 5.0, 10.0, 0.88
else:
    HW, HL, NET = 5.485, 11.885, 0.914          # campo de pares; jogo de singulares
SW = 4.115                                   # linha lateral de singulares (ténis)

def court_items(cam):
    items = []                                # (profundidade, função de desenho)
    def P(pts, fill, outline=None, w=0, depth=None):
        pp = cam.poly(pts)
        if pp:
            dd = depth if depth is not None else sum(cam.depth(p) for p in pts) / len(pts)
            items.append((dd, lambda d, pp=pp: (d.polygon(pp, fill=fill), outline and d.line(pp + [pp[0]], fill=outline, width=w))))
    return items, P

def draw_floor(d, cam):
    # fora do campo
    ext = 13
    ex, ey = HW + 4.5, HL + 4.5
    pp = cam.poly([(-ex, -ey, 0), (ex, -ey, 0), (ex, ey, 0), (-ex, ey, 0)])
    if pp: d.polygon(pp, fill=SURF[1] if V["surface"] != "padel" else DEEP)
    if SPORT == "padel":
        pp = cam.poly([(-HW, -HL, 0), (HW, -HL, 0), (HW, HL, 0), (-HW, HL, 0)])
        if pp: d.polygon(pp, fill=SURF[0])
        L = [((-HW, -HL), (HW, -HL)), ((-HW, HL), (HW, HL)), ((-HW, -6.95), (HW, -6.95)), ((-HW, 6.95), (HW, 6.95)), ((0, -6.95), (0, 6.95))]
    else:
        pp = cam.poly([(-HW, -HL, 0), (HW, -HL, 0), (HW, HL, 0), (-HW, HL, 0)])
        if pp: d.polygon(pp, fill=SURF[0])
        L = [((-HW, -HL), (HW, -HL)), ((-HW, HL), (HW, HL)), ((-HW, -HL), (-HW, HL)), ((HW, -HL), (HW, HL)),
             ((-SW, -HL), (-SW, HL)), ((SW, -HL), (SW, HL)), ((-SW, -6.4), (SW, -6.4)), ((-SW, 6.4), (SW, 6.4)), ((0, -6.4), (0, 6.4)),
             ((0, -HL), (0, -HL + 0.2)), ((0, HL), (0, HL - 0.2))]
    for (a, b) in L:
        line3(d, cam, (a[0], a[1], 0.002), (b[0], b[1], 0.002), 0.05, SURF[2] + (235,))

def line3(d, cam, A, B, width_m, col):
    """linha no espaço com espessura em metros (cortada junto à câmara)"""
    ca, cb = cam.cam(A), cam.cam(B); NZ = 0.05
    if ca[2] < NZ and cb[2] < NZ: return
    if ca[2] < NZ: u = (NZ - ca[2]) / (cb[2] - ca[2]); ca = tuple(lerp(ca[j], cb[j], u) for j in range(3))
    if cb[2] < NZ: u = (NZ - cb[2]) / (ca[2] - cb[2]); cb = tuple(lerp(cb[j], ca[j], u) for j in range(3))
    pa, pb = cam.scr(ca), cam.scr(cb)
    w = max(1, int(width_m * cam.foc / ((ca[2] + cb[2]) / 2)))
    d.line([pa, pb], fill=col, width=min(w, 400))

NOW = [0.0]
def clay_marks(d, cam):
    if V["surface"] != "clay": return
    for (tk, x, y, z) in KP:
        if z == 0 and tk <= NOW[0] and abs(x) <= HW + 1 and abs(y) <= HL + 2:
            pp = cam.poly([(x - 0.09, y - 0.16, 0.003), (x + 0.09, y - 0.16, 0.003), (x + 0.09, y + 0.16, 0.003), (x - 0.09, y + 0.16, 0.003)])
            if pp:
                xs = [p[0] for p in pp]; ys = [p[1] for p in pp]
                d.ellipse([min(xs), min(ys), max(xs), max(ys)], fill=(140, 62, 36, 200))

def dust(d, cam, t):
    if V["surface"] != "clay": return
    rnd = random.Random(3)
    for (tk, x, y, z) in KP:
        if z == 0 and 0 <= t - tk < 0.6:
            u = (t - tk) / 0.6
            for q in range(14):
                an = rnd.uniform(0, 2 * math.pi); sp = rnd.uniform(0.3, 0.9)
                P_ = (x + math.cos(an) * sp * u, y + math.sin(an) * sp * u, 0.05 + 0.5 * u * rnd.uniform(0.3, 1))
                c, ppm = cam.proj(P_)
                if c:
                    r = max(2, (0.05 + 0.12 * u) * ppm); d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(214, 140, 96, int(120 * (1 - u))))
    for pl in PLAYERS:
        x, y, sp = pl.base(t)
        if sp > 2.2:
            for q in range(6):
                k = q / 6; P_ = (x + rnd.uniform(-0.3, 0.3), y - pl.face * (0.2 + 0.6 * k) * 0 + rnd.uniform(-0.3, 0.3), 0.05 + 0.3 * k)
                c, ppm = cam.proj(P_)
                if c:
                    r = max(2, 0.1 * ppm); d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(214, 140, 96, int(70 * min(1, sp / 5) * (1 - k))))

def _solve(A, B):
    n = len(B); M = [row[:] + [b] for row, b in zip(A, B)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r != c and M[c][c]:
                f = M[r][c] / M[c][c]; M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [M[i][n] / M[i][i] for i in range(n)]
def _homog(src, dst):
    A = []; B = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return _solve(A, B)
_BOARD = {}
def board_img():
    if "i" not in _BOARD:
        w, h = 1600, 90
        im = Image.new("RGBA", (w, h), (12, 22, 38, 255)); dd = ImageDraw.Draw(im)
        dd.rectangle([0, h - 8, w, h], fill=ACC + (255,))
        txt = V["board"]; f = F("k", 54); tw = dd.textlength(txt, font=f)
        x = 40
        while x < w: dd.text((x, h / 2 - 4), txt, font=f, fill=CREAM, anchor="lm"); x += tw + 120
        _BOARD["i"] = im
    return _BOARD["i"]
def boards(cam):
    items = []
    if SPORT == "padel": spots = [((-HW - 2, s_ * (HL + 1.6)), (HW + 2, s_ * (HL + 1.6))) for s_ in (-1, 1)]
    else: spots = [((-HW - 3, s_ * (HL + 4.2)), (HW + 3, s_ * (HL + 4.2))) for s_ in (-1, 1)] + \
                  [((s_ * (HW + 3.2), -HL - 2), (s_ * (HW + 3.2), HL + 2)) for s_ in (-1, 1)]
    for (a, b) in spots:
        q = [(a[0], a[1], 0.95), (b[0], b[1], 0.95), (b[0], b[1], 0.0), (a[0], a[1], 0.0)]
        if any(cam.cam(p)[2] < 0.3 for p in q): continue
        pts = [cam.proj(p)[0] for p in q]
        if pts[0][0] > pts[1][0]:
            q = [q[1], q[0], q[3], q[2]]; pts = [cam.proj(p)[0] for p in q]
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 0.5)
        def draw(d, pts=pts, im_=None):
            img = board_img(); w, h = img.size
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            x0, y0, x1, y1 = int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1
            if x1 - x0 < 4 or y1 - y0 < 2 or x1 - x0 > 9000: return
            co = _homog([(0, 0), (w, 0), (w, h), (0, h)], [(p[0] - x0, p[1] - y0) for p in pts])
            warped = img.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, co, Image.BILINEAR)
            d._image.paste(warped, (x0, y0), warped)
        items.append((cam.depth(mid), draw))
    return items

def _sky():
    g = Image.new("RGB", (W * S, H * S)); d = ImageDraw.Draw(g)
    if V["setting"] == "day":
        top, bot = (96, 160, 220), (206, 226, 240)
    else:
        top, bot = (6, 10, 18), (16, 26, 42)
    for y in range(0, H * S, 8):
        k = y / (H * S); d.rectangle([0, y, W * S, y + 8], fill=tuple(int(top[j] + (bot[j] - top[j]) * k) for j in range(3)))
    return g
SKY = _sky()
def roof(d, cam):
    if V["setting"] != "indoor": 
        if V["setting"] == "day":
            q, ppm = cam.proj((-60, 80, 70))
            if q:
                for r, a in ((260, 30), (140, 70), (60, 255)): d.ellipse([q[0] - r * S / 2, q[1] - r * S / 2, q[0] + r * S / 2, q[1] + r * S / 2], fill=(255, 248, 220, a))
        return
    Z = 16
    for i in range(-3, 4):                       # treliças do teto
        line3(d, cam, (i * 6, -34, Z), (i * 6, 34, Z), 0.25, (40, 54, 74, 255))
    for j in range(-5, 6):
        line3(d, cam, (-24, j * 6, Z), (24, j * 6, Z), 0.18, (34, 46, 64, 255))
    for (lx, ly) in ((-6, -9), (6, -9), (-6, 9), (6, 9), (0, 0)):
        top = (lx * 1.6, ly * 1.6, Z - 0.5)
        pp = cam.poly([top, (lx - 3, ly - 3, 0.01), (lx + 3, ly + 3, 0.01)])
        if pp: d.polygon(pp, fill=(255, 248, 225, 10))

def structure(cam):
    """rede e paredes, como peças com profundidade para ordenar"""
    items, P = court_items(cam)
    # rede
    net = [(-HW - (0 if SPORT == "padel" else 0.9), 0, 0), (HW + (0 if SPORT == "padel" else 0.9), 0, 0)]
    nx = HW + (0 if SPORT == "padel" else 0.9)
    for i in range(10):
        x0, x1 = -nx + 2 * nx * i / 10, -nx + 2 * nx * (i + 1) / 10
        P([(x0, 0, 0), (x1, 0, 0), (x1, 0, NET), (x0, 0, NET)], (14, 22, 34, 150))
    pp = cam.poly([(-nx, 0, NET - 0.06), (nx, 0, NET - 0.06), (nx, 0, NET), (-nx, 0, NET)])
    if pp: items.append((cam.depth((0, 0, NET)) - 0.01, lambda d, pp=pp: d.polygon(pp, fill=CREAM)))
    if SPORT == "padel":
        # vidros do fundo (3 m) com rede metálica por cima (até 4 m), vidros laterais junto ao fundo
        for sgn in (-1, 1):
            y = sgn * HL
            for i in range(5):
                x0, x1 = -HW + 2 * i, -HW + 2 * (i + 1)
                P([(x0, y, 0), (x1, y, 0), (x1, y, 3), (x0, y, 3)], GLASS + (46,), GLASS + (150,), 2 * S)
                P([(x0, y, 3), (x1, y, 3), (x1, y, 4), (x0, y, 4)], (40, 60, 80, 70), (90, 110, 130, 140), S)
            for sx in (-HW, HW):
                for (ya, yb, h) in ((HL, HL - 2, 3), (HL - 2, HL - 4, 2)):
                    P([(sx, sgn * ya, 0), (sx, sgn * yb, 0), (sx, sgn * yb, h), (sx, sgn * ya, h)], GLASS + (40,), GLASS + (140,), 2 * S)
                for (ya, yb) in ((HL - 4, 0.0),):
                    P([(sx, sgn * ya, 0), (sx, sgn * yb, 0), (sx, sgn * yb, 3), (sx, sgn * ya, 3)], (40, 60, 80, 40), (90, 110, 130, 90), S)
    return items

# ------------------------------------------------------------------ bola: troços balísticos entre pontos (t, x, y, z)
def ball_at(KP, t):
    if t <= KP[0][0]: return KP[0][1:]
    for (t0, *a), (t1, *b) in zip(KP, KP[1:]):
        if t0 <= t <= t1:
            T = t1 - t0; u = t - t0
            vz = (b[2] - a[2] + 0.5 * G * T * T) / T
            return (lerp(a[0], b[0], u / T), lerp(a[1], b[1], u / T), a[2] + vz * u - 0.5 * G * u * u)
    (t0, *a), (t1, *b) = KP[-2], KP[-1]
    T = t1 - t0; vz = (b[2] - a[2] + 0.5 * G * T * T) / T; u = t - t0
    return (a[0] + (b[0] - a[0]) / T * u, a[1] + (b[1] - a[1]) / T * u, a[2] + vz * u - 0.5 * G * u * u)

# ------------------------------------------------------------------ jogadores estilizados
class Player:
    def __init__(s, way, col, face, hits, hand=1):
        s.way, s.col, s.face, s.hits, s.hand = way, col, face, hits, hand     # way: [(t, x, y)], hits: [(t, tipo)]
    def base(s, t):
        w = s.way
        if t <= w[0][0]: return w[0][1], w[0][2], 0
        for (t0, x0, y0), (t1, x1, y1) in zip(w, w[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / (t1 - t0); u = u * u * (3 - 2 * u)
                return lerp(x0, x1, u), lerp(y0, y1, u), math.hypot(x1 - x0, y1 - y0) / (t1 - t0)
        return w[-1][1], w[-1][2], 0
    def joints(s, t, KP):
        x, y, sp = s.base(t)
        f = (0, s.face, 0); sd = (s.face, 0, 0)                 # lado da mão da raquete
        ph = t * 9; run = min(1, sp / 3)
        jump = 0; sw = None
        for (th, kind) in s.hits:
            if kind == "smash" and -0.35 < t - th < 0.3: jump = 0.45 * math.sin(math.pi * (t - th + 0.35) / 0.65)
            if -0.3 < t - th < 0.3: sw = (t - th, kind, th)
        lean = 0.12 * run
        hip = (x, y + s.face * lean * 0.3, 0.95 + jump)
        sh = (x, y + s.face * lean, 1.45 + jump)
        head = (x, y + s.face * lean * 1.2, 1.7 + jump)
        fl = (x - 0.18 + 0.28 * run * math.sin(ph) * 0, y + 0.3 * run * math.sin(ph), 0.0 + jump * 0.8)
        fr = (x + 0.18, y - 0.3 * run * math.sin(ph), 0.0 + jump * 0.8)
        shR = add(sh, mul(sd, 0.2 * s.hand)); shL = add(sh, mul(sd, -0.2 * s.hand))
        rest = add(shR, (0.15 * s.face * s.hand, 0.25 * s.face, -0.45))
        hand = rest
        if sw:
            dt, kind, th = sw; bp = ball_at(KP, th)
            reach = add(bp, (-0.15 * s.face * s.hand, -0.25 * s.face, 0))
            if kind == "smash":
                back_ = add(shR, (0.1 * s.face, -0.35 * s.face, 0.35)); thru = add(shR, (-0.3 * s.face * s.hand, 0.5 * s.face, -0.6))
            else:
                back_ = add(shR, (0.55 * s.face * s.hand, -0.45 * s.face, 0.0)); thru = add(shL, (-0.2 * s.face * s.hand, 0.35 * s.face, 0.25))
            if dt < 0:
                u = ease((dt + 0.3) / 0.3); hand = vlerp(back_, reach, u ** 2)
            else:
                u = ease(dt / 0.3); hand = vlerp(reach, thru, u)
        # a mão não se afasta mais do que o braço deixa
        v = sub(hand, shR); l = math.sqrt(dot(v, v))
        if l > 0.95: hand = add(shR, mul(v, 0.95 / l))
        rd = norm(sub(hand, shR)); head_r = add(hand, mul(rd, 0.38))
        return dict(hip=hip, sh=sh, head=head, fl=fl, fr=fr, shR=shR, shL=shL, hand=hand, rk=head_r, x=x, y=y, jump=jump)

def draw_player(d, cam, J, col):
    # sombra
    pp = cam.poly([(J["x"] - 0.35, J["y"] - 0.25, 0.003), (J["x"] + 0.35, J["y"] - 0.25, 0.003), (J["x"] + 0.35, J["y"] + 0.25, 0.003), (J["x"] - 0.35, J["y"] + 0.25, 0.003)])
    if pp:
        xs = [p[0] for p in pp]; ys = [p[1] for p in pp]
        d.ellipse([min(xs), min(ys), max(xs), max(ys)], fill=(0, 0, 0, int(80 / (1 + J["jump"] * 3))))
    dark = tuple(int(c * 0.55) for c in col); skin = (214, 176, 146); shorts = (28, 36, 56)
    for ft in (J["fl"], J["fr"]):
        knee = vlerp(J["hip"], ft, 0.45)
        line3(d, cam, knee, ft, 0.1, skin); line3(d, cam, J["hip"], knee, 0.17, shorts)
        line3(d, cam, ft, add(ft, (0, 0.12, 0.03)), 0.12, (245, 245, 245))
    line3(d, cam, J["hip"], J["sh"], 0.38, col)
    line3(d, cam, J["shL"], add(J["shL"], (0, 0.15, -0.42)), 0.09, skin)
    line3(d, cam, J["shR"], J["hand"], 0.09, skin)
    line3(d, cam, J["shR"], vlerp(J["shR"], J["hand"], 0.3), 0.13, col)
    line3(d, cam, J["hand"], J["rk"], 0.035, (30, 30, 36))
    c, ppm = cam.proj(J["rk"])
    if c:
        r = 0.14 * ppm; d.ellipse([c[0] - r, c[1] - r * 1.2, c[0] + r, c[1] + r * 1.2], fill=(28, 28, 34), outline=CREAM, width=max(1, int(0.02 * ppm)))
    c, ppm = cam.proj(J["head"])
    if c:
        r = 0.12 * ppm; d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(222, 196, 170))
        d.chord([c[0] - r, c[1] - r, c[0] + r, c[1] + r], 180, 360, fill=dark)

# ------------------------------------------------------------------ guiões (rally ilustrado)
def padel_script():
    KP = [(0.0, -1.8, 7.6, 1.0), (0.78, 1.5, -6.2, 0.0), (1.18, 2.3, -10.0, 1.35), (1.55, 2.4, -8.5, 0.95),
          (3.15, -1.6, 7.9, 0.0), (3.5, -1.8, 10.0, 1.9), (3.95, -1.5, 8.8, 1.15),
          (5.55, -1.0, -3.4, 2.75),
          (5.82, 1.9, 6.6, 0.0), (6.25, 2.6, 10.0, 4.7), (6.9, 3.0, 14.0, 2.0)]
    A = (247, 242, 230); B = (255, 138, 120)
    P = [Player([(0, 2.6, -7.9), (1.2, 2.6, -8.0), (1.55, 2.5, -8.2), (2.6, 1.6, -5.5), (5, 1.8, -4.5)], A, 1, [(1.55, "fh")]),
         Player([(0, -2.4, -4.5), (1.5, -2.2, -4.0), (3.2, -1.6, -3.6), (5.55, -1.1, -3.65), (7, -1.4, -3.4)], A, 1, [(5.55, "smash")]),
         Player([(0, -2.0, 7.4), (0.6, -1.8, 7.0), (2.0, -1.5, 6.0), (3.4, -1.6, 7.8), (3.95, -1.35, 8.55), (5.2, -1.0, 7.5), (6.3, 1.0, 8.8)], B, -1, [(0.0, "fh"), (3.95, "fh")]),
         Player([(0, 2.3, 5.0), (3.0, 2.0, 5.6), (5.0, 2.1, 6.4), (6.2, 2.9, 8.9)], B, -1, [])]
    shots = [  # (início, fim, câmara)
        (0.0, 1.62, ("fixed", (0.0, -17.5, 7.6), (0.0, -1.5, 0.3), 52)),
        (1.62, 3.38, ("side", 7.6, 2.0, 60)),
        (3.38, 4.05, ("fixed", (-0.6, 13.6, 2.3), (-1.6, 8.6, 1.2), 62)),
        (4.05, 5.3, ("follow", (4.2, -8.0, 1.3), 58)),
        (5.3, 5.85, ("fixed", (-6.2, 1.2, 2.4), (-1.0, -3.3, 2.0), 46)),
        (5.85, 7.2, ("follow", (0.0, -4.5, 2.6), 62)),
    ]
    slow = [(5.25, 5.9, 0.22), (5.9, 6.6, 0.5)]
    return KP, P, shots, slow, 7.2, {1: "smash"}

def tennis_script():
    KP = [(0.0, -2.5, 11.4, 1.0), (0.8, 1.8, -8.5, 0.0), (1.25, 2.6, -12.2, 0.95),
          (2.25, -2.2, 6.0, 0.0), (2.65, -2.6, 11.0, 1.0),
          (3.55, -1.0, -7.8, 0.0), (3.9, -0.8, -11.4, 1.0),
          (4.55, 3.7, 8.3, 0.0), (5.3, 4.0, 15.0, 0.45)]
    A = (247, 242, 230); B = (255, 138, 120)
    P = [Player([(0, 0.4, -12.0), (1.25, 2.4, -12.4), (2.8, 0.2, -11.6), (3.9, -0.6, -11.8), (5.5, 0.2, -11.0)], A, 1, [(1.25, "fh"), (3.9, "fh")]),
         Player([(0, -2.2, 11.6), (1.3, 0.2, 11.0), (2.65, -2.2, 11.3), (3.4, 0.0, 11.4), (4.4, 3.0, 9.8), (5.4, 3.4, 10.4)], B, -1, [(0.0, "fh"), (2.65, "fh")])]
    shots = [
        (0.0, 1.45, ("fixed", (0.0, -21.0, 7.0), (0.0, -2.0, 0.3), 50)),
        (1.45, 2.8, ("side", 8.6, 2.0, 58)),
        (2.8, 3.62, ("fixed", (-1.2, 15.5, 2.0), (-1.0, 4.0, 1.0), 56)),
        (3.62, 4.15, ("fixed", (-3.4, -14.2, 1.6), (-0.8, -11.4, 1.0), 58)),
        (4.15, 5.6, ("follow", (5.2, -6.0, 1.2), 50)),
    ]
    slow = [(3.6, 4.2, 0.22), (4.2, 4.6, 0.5)]
    return KP, P, shots, slow, 5.6, {}

def build_play(sport, name):
    """Jogada da biblioteca (reels/plays.py): bola, jogadores que vão à bola, câmaras e câmara lenta no último batimento."""
    from reels.plays import LIB
    p = LIB[sport][name]; ev = p["ev"]
    KP = [(e[0], e[1], e[2], e[3]) for e in ev]
    A = (247, 242, 230); B = (255, 138, 120)
    n = len(p["homes"]); faces = [1, 1, -1, -1] if n == 4 else [1, -1]
    cols = [A, A, B, B] if n == 4 else [A, B]
    hits = [(e[0], e[4], e[5], (e[1], e[2], e[3])) for e in ev if e[4] is not None]
    players = []
    for i in range(n):
        f = faces[i]; hx, hy = p["homes"][i]; way = [(0.0, hx, hy)]; my = []
        for th, who, kind, c in hits:
            if who != i: continue
            off = 0.55 if kind == "fh" else -0.55 if kind == "bh" else 0.25
            bx, by = c[0] - f * off, c[1] - f * (0.35 if kind in ("smash", "serve") else 0.3)
            if th < 0.05: way = [(0.0, bx, by)]
            else: way.append((th - 0.05, bx, by))
            my.append((th, kind))
            nxt = [h for h in hits if h[1] == i and h[0] > th]
            if not nxt or nxt[0][0] - th > 1.4: way.append((th + 0.9, hx, hy))
        for (t_, x_, y_) in p.get("moves", {}).get(i, []): way.append((t_, x_, y_))
        way.sort(key=lambda w: w[0])
        clean = []
        for w in way:
            if clean and w[0] - clean[-1][0] < 0.12: clean[-1] = w
            else: clean.append(w)
        players.append(Player(clean, cols[i], f, my))
    tf, fw, fk, fc = hits[-1]; f = faces[fw]
    hb = players[fw].base(tf)
    end = ev[-1][0] + 0.6
    bc = ((0.0, -17.5, 7.6), (0.0, -1.5, 0.3), 52) if sport == "padel" else ((0.0, -21.0, 7.0), (0.0, -2.0, 0.3), 50)
    t1 = min(1.6, max(0.6, tf * 0.35))
    shots = [(0.0, t1, ("fixed",) + bc)]
    if tf - 0.55 - t1 > 0.8:
        shots.append((t1, tf - 0.55, ("side", 7.6 if sport == "padel" else 8.6, 2.0, 60 if sport == "padel" else 58)))
    up = 2.1 if fk in ("smash", "serve") else 1.5
    side = 1 if hb[0] <= 0 else -1                                   # câmara do lado de dentro do campo
    cpos = (hb[0] + side * 3.2, hb[1] + f * 3.4, up)
    shots.append((shots[-1][1], tf + 0.35, ("fixed", cpos, (hb[0], hb[1], fc[2] * 0.8 + 0.3), 50)))
    shots.append((tf + 0.35, end, ("follow", (hb[0] + side * 2.6, hb[1] - f * 5.5, 3.3), 60)))   # de lado e acima: o jogador não tapa a bola
    slow = [(tf - 0.3, tf + 0.3, 0.22), (tf + 0.3, tf + 0.9, 0.5)]
    fin = (tf + 0.45, end) + tuple(p["title"])
    return KP, players, shots, slow, end, fin

PLAY = V.get("play")
if PLAY:
    KP, PLAYERS, SHOTS, SLOW, SIM_END, _FIN = build_play(SPORT, PLAY)
else:
    KP, PLAYERS, SHOTS, SLOW, SIM_END, _ = padel_script() if SPORT == "padel" else tennis_script()
    _FIN = None

CTX = dict(V, foot="Animation · real result")

def camera(t):
    for (a, b, spec) in SHOTS:
        if a <= t < b or (spec is SHOTS[-1][2] and t >= a):
            bp = ball_at(KP, t)
            if spec[0] == "fixed":
                return Cam(spec[1], spec[2], spec[3]), (a, b)
            if spec[0] == "side":
                x, z, fov = spec[1:]; u = (t - a) / (b - a)
                pos = (x, lerp(-4, 4, u) if SPORT == "padel" else lerp(-6, 6, u), z)
                tgt = (bp[0] * 0.3, bp[1] * 0.85, max(0.8, bp[2] * 0.6))
                return Cam(pos, tgt, fov), (a, b)
            if spec[0] == "follow":
                pos, fov = spec[1], spec[2]
                tgt = (bp[0] * 0.7, bp[1] * 0.9, max(0.9, bp[2] * 0.85))
                return Cam(pos, tgt, fov), (a, b)

# tempo do vídeo -> tempo da simulação (câmara lenta)
def build_timemap():
    m, t, sim = [], 0.0, 0.0
    while sim < SIM_END:
        m.append(sim)
        rate = 1.0
        for (a, b, r) in SLOW:
            if a <= sim < b: rate = r
        sim += rate / FPS
    return m
TM = build_timemap()
FINISH = _FIN or ((6.05, SIM_END, "POR 3!", "Smash out over the back wall") if SPORT == "padel" else (4.6, SIM_END, "WINNER.", "Forehand down the line"))
INTRO = 0.0
OUT = 3.4                                     # cartão final
TOTAL = len(TM) / FPS + OUT

def draw_ball(d, cam, t):
    bp = ball_at(KP, t)
    # rasto
    for k in range(8, 0, -1):
        p = ball_at(KP, t - k * 0.012)
        c, ppm = cam.proj(p)
        if c:
            r = max(2 * S, 0.05 * ppm) * (1 - k / 9)
            d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=ACC + (int(160 * (1 - k / 9)),))
    # sombra no chão
    c, ppm = cam.proj((bp[0], bp[1], 0.004))
    if c and bp[2] < 6:
        r = max(2 * S, 0.06 * ppm); d.ellipse([c[0] - r, c[1] - r * 0.45, c[0] + r, c[1] + r * 0.45], fill=(0, 0, 0, int(110 * (1 - bp[2] / 6))))
    c, ppm = cam.proj(bp)
    if c:
        r = max(4 * S, 0.06 * ppm)
        d.ellipse([c[0] - r * 2.2, c[1] - r * 2.2, c[0] + r * 2.2, c[1] + r * 2.2], fill=ACC + (50,))
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=ACC)
    return bp

def impacts(d, cam, t):
    for (tk, x, y, z) in KP[1:-1]:
        if z > 3.2 or abs(y) > HL + 0.5: continue
        dt = t - tk
        if 0 <= dt < 0.22:
            c, ppm = cam.proj((x, y, z))
            if not c: continue
            v = dt / 0.22; r = (0.15 + 0.9 * v) * ppm
            if z < 0.01:
                d.ellipse([c[0] - r, c[1] - r * 0.35, c[0] + r, c[1] + r * 0.35], outline=CREAM + (int(230 * (1 - v)),), width=max(2, int(0.04 * ppm)))
            else:
                d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=CREAM + (int(230 * (1 - v)),), width=max(2, int(0.04 * ppm)))
                rnd = random.Random(int(tk * 100))
                for q in range(9):
                    an = rnd.uniform(0, 2 * math.pi); a0, a1 = r * 0.8, r * 0.8 + 0.4 * ppm
                    d.line([(c[0] + a0 * math.cos(an), c[1] + a0 * math.sin(an)), (c[0] + a1 * math.cos(an), c[1] + a1 * math.sin(an))], fill=ACC + (int(255 * (1 - v)),), width=max(2, int(0.03 * ppm)))

# bancadas com público (pontos), geradas uma vez
_rnd = random.Random(7); CROWD = []; STANDS = []
_cols = [(200, 190, 180), (230, 120, 110), (120, 150, 200), (240, 230, 210), (90, 100, 120), (210, 200, 90), (60, 70, 90)]
for sgn in (-1, 1):
    y0 = sgn * (HL + 4.5); x0 = HW + 4.5
    D_ = V['rows'] * 0.68; Z_ = V['rows'] * 0.57 + 0.6
    STANDS.append([(-x0 - 4, y0, 0), (x0 + 4, y0, 0), (x0 + 4, y0 + sgn * D_, Z_), (-x0 - 4, y0 + sgn * D_, Z_)])
    STANDS.append([(sgn * x0, -HL - 6, 0), (sgn * x0, HL + 6, 0), (sgn * (x0 + D_), HL + 6, Z_), (sgn * (x0 + D_), -HL - 6, Z_)])
    for r in range(V['rows']):
        for _ in range(70):
            c = _cols[_rnd.randrange(len(_cols))]
            CROWD.append(((_rnd.uniform(-x0 - 3, x0 + 3), y0 + sgn * (0.35 + r * 0.68), 0.55 + r * 0.57), c))
            CROWD.append(((sgn * (x0 + 0.35 + r * 0.68), _rnd.uniform(-HL - 5, HL + 5), 0.55 + r * 0.57), c))
def arena(d, cam):
    for st in STANDS:
        pp = cam.poly(st)
        if pp: d.polygon(pp, fill=(16, 28, 44) if V['setting'] != 'day' else (120, 128, 140))
    for (P_, c) in CROWD:
        q, ppm = cam.proj(P_)
        if not q or not (-50 < q[0] < W * S + 50 and -50 < q[1] < H * S + 50): continue
        r = max(1.2 * S, 0.2 * ppm)
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=tuple(int(v * (0.55 if V['setting'] != 'day' else 0.95)) for v in c))
    # luzes do pavilhão
    if V['setting'] == 'day': return
    for lx in (-8, 0, 8):
        for ly in (-14, 14):
            q, ppm = cam.proj((lx, ly, 15.5))
            if q:
                for k, a in ((6, 25), (3, 60), (1.2, 230)):
                    r = min(36 * S, max(3 * S, k * ppm * 0.4)); d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=(255, 250, 230, a))

def scene(t):
    im = SKY.copy(); NOW[0] = t
    d = ImageDraw.Draw(im, "RGBA")
    cam, (sa, sb) = camera(t)
    roof(d, cam)
    arena(d, cam)
    draw_floor(d, cam)
    items = structure(cam) + boards(cam)
    for i, pl in enumerate(PLAYERS):
        J = pl.joints(t, KP)
        items.append((cam.depth(J["sh"]), lambda d, J=J, pl=pl: draw_player(d, cam, J, pl.col)))
    bp = ball_at(KP, t)
    items.append((cam.depth(bp) - 0.05, lambda d: draw_ball(d, cam, t)))
    for _, fn in sorted(items, key=lambda z: -z[0]): fn(d)
    impacts(d, cam, t)
    dust(d, cam, t)
    out = im.resize((W, H), Image.LANCZOS)
    # entrada de cada plano: um flash curto
    k = t - sa
    if 0 <= k < 0.06 and sa > 0:
        out = Image.blend(out, Image.new("RGB", (W, H), (255, 255, 255)), 0.25 * (1 - k / 0.06))
    return out, bp

def hud(d, t, vt, slow):
    for i in range(240): d.line([(0, i), (W, i)], fill=(6, 14, 26, int(200 * (1 - i / 240))))
    d.text((80, 120), CTX["brand"], font=F("k", 32), fill=CREAM)
    d.text((W - 160, 120), CTX["handle"], font=F("b", 28), fill=SOFT, anchor="ra")
    d.text((80, 180), CTX["kick"], font=F("x", 32), fill=ACC)
    # 17/11/2026 (Afonso): a animação é só entretenimento; nenhum texto sugere que foi o ponto real.
    # Gancho "WHO WON …?" grande nos primeiros 3 s, depois encolhe; a resposta (resultado real) vem no cartão final.
    hook = CTX.get("hook") or ("WHO WON " + CTX["board"].split("·")[0].strip() + "?")
    w1, w2 = "WHO WON", hook[len("WHO WON"):].strip() if hook.startswith("WHO WON") else hook
    k = seg(vt, 3.0, 3.5); a = int(255 * min(1, vt / 0.15) * (1 - seg(vt, 3.0, 3.22)))
    if a > 0:
        size = 92
        while size > 60 and d.textlength(w2, font=F("d", size)) > 920: size -= 4
        d.text((80, 228), w1, font=F("d", 92), fill=CREAM + (a,))
        d.text((80, 318), w2, font=F("d", size), fill=ACC + (a,))
    k2 = seg(vt, 3.22, 3.5)
    if k2 > 0:
        d.text((80, 232), hook, font=F("d", 46), fill=CREAM + (int(255 * k2),))
    cy = int(430 - 130 * k)
    txt = CTX["chip"]; w_ = d.textlength(txt, font=F("x", 26)) + 40
    d.rounded_rectangle([80, cy, 80 + w_, cy + 48], radius=24, fill=(6, 14, 26, 190)); d.text((100, cy + 24), txt, font=F("x", 26), fill=CREAM, anchor="lm")
    if slow:
        d.text((W - 88, 530), "SLOW-MO", font=F("x", 26), fill=ACC, anchor="rm")
    d.text((80, 1488), CTX["foot"], font=F("m", 24), fill=SOFT + (220,), anchor="ls")

def outro(last, u):
    im = last.filter(ImageFilter.GaussianBlur(int(4 + 14 * ease(min(1, u * 3)))))
    im = Image.blend(im, Image.new("RGB", (W, H), BG), 0.55 * ease(min(1, u * 3)))
    d = ImageDraw.Draw(im, "RGBA")
    a = int(255 * seg(u, 0.05, 0.25)); b_ = int(255 * seg(u, 0.18, 0.4)); c_ = int(255 * seg(u, 0.3, 0.5))
    d.text((80, 120), CTX["brand"], font=F("k", 32), fill=CREAM)
    d.text((W - 160, 120), CTX["handle"], font=F("b", 28), fill=SOFT, anchor="ra")
    d.text((80, 180), CTX["kick"], font=F("x", 32), fill=ACC)
    d.text((80, 560), CTX["title"], font=F("d", 120), fill=ACC + (a,))
    d.text((80, 700), CTX["champ"], font=F("d", 76), fill=CREAM + (b_,))
    d.text((80, 830), CTX["score"], font=F("k", 64), fill=CREAM + (c_,))
    d.text((80, 940), "Every result · beyond100tennis.com", font=F("b", 32), fill=SOFT + (c_,))
    d.text((80, 1488), CTX["foot"], font=F("m", 24), fill=SOFT + (220,), anchor="ls")
    return im

def frame_at(i):
    n = len(TM)
    if i < n:
        t = TM[i]; im, bp = scene(t)
        slow = any(a <= t < b and r < 0.4 for a, b, r in SLOW)
        d = ImageDraw.Draw(im, "RGBA"); hud(d, t, i / FPS, slow)
        return im
    global LAST
    if "LAST" not in globals() or LAST is None:
        im, _ = scene(TM[-1]); LAST = im
    return outro(LAST, (i - n) / FPS / OUT)
LAST = None

def soundtrack(tmp, out):
    """Junta o som ao vídeo tmp e escreve out; True se correu bem.
    Com sons reais em reels/sfx (CC0): bola, ressaltos, vidro, sapatilhas e público, sem música.
    Sem eles: o som gerado por código de antes."""
    try:
        from reels import sound
        vt = lambda ts: next((i for i, x in enumerate(TM) if x >= ts), len(TM)) / FPS
        m = sound.Mix(TOTAL)
        end = len(TM) / FPS
        hits = {round(th, 3): kind for pl in PLAYERS for th, kind in pl.hits}
        if sound.SFX.get("crowd") and (sound.SFX.get("hit_tennis") or sound.SFX.get("hit_padel")):
            hit = "hit_padel" if SPORT == "padel" and sound.SFX.get("hit_padel") else "hit_tennis"
            bounce = "bounce_clay" if V.get("surface") == "clay" and sound.SFX.get("bounce_clay") else "bounce"
            indoor = str(V.get("setting", "")).startswith("indoor") or "INDOOR" in str(V.get("chip", "")).upper()
            m.sample(0.0, "crowd_indoor" if indoor and sound.SFX.get("crowd_indoor") else "crowd", 0.22, loop_to=TOTAL)
            last = None
            for (tk, x, y, z) in KP:
                t_ = vt(tk)
                if round(tk, 3) in hits:
                    big = hits[round(tk, 3)] == "smash" or tk == max(hits)
                    m.sample(t_, hit, 1.0 if big else 0.8)
                    if last is None or t_ - last > 0.9: m.sample(max(0, t_ - 0.35), "squeak", 0.35)   # apoio antes da pancada
                    last = t_
                elif z == 0 and abs(y) <= HL + 0.5: m.sample(t_, bounce, 0.55)
                elif SPORT == "padel" and abs(abs(y) - HL) < 0.05 and z < 3.2:
                    if not m.sample(t_, "glass", 0.7): m.glass(t_, 0.3); m.sample(t_, bounce, 0.4)
            if KP[0][0] == 0: m.sample(0.0, "serve" if sound.SFX.get("serve") and SPORT != "padel" else hit, 0.8)
            if FINISH and sound.SFX.get("ooh"): m.sample(max(0, vt(FINISH[0]) - 0.1), "ooh", 0.45)
            m.sample(end - 0.2, "applause", 0.85)
        else:
            slow0 = vt(SLOW[0][0])
            m.beat(0.0, TOTAL - 0.6, bpm=100, mute=[(slow0 - 0.1, end + 0.2)], vol=0.7)
            m.pad(0.0, TOTAL, vol=0.035)
            m.crowd(0.0, TOTAL, 0.07, swell=(vt(FINISH[0]) if FINISH else end, 0.7))
            m.whoosh(slow0 - 0.1, 0.6, 0.3)
            for (tk, x, y, z) in KP:
                t_ = vt(tk)
                if round(tk, 3) in hits:
                    big = hits[round(tk, 3)] == "smash" or tk == max(hits)
                    m.pop(t_, 1.0 if big else 0.6, 0.8 if big else 1.0)
                    if big: m.boom(t_, 0.6)
                elif z == 0 and abs(y) <= HL + 0.5: m.thock(t_, 0.4)
                elif SPORT == "padel" and abs(abs(y) - HL) < 0.05 and z < 3.2: m.glass(t_, 0.5)
            if KP[0][0] == 0: m.pop(0.0, 0.5)
            m.boom(end, 0.7)
        wav = tmp[:-4] + ".wav"; m.write(wav, TOTAL)
        ok = sound.mux(tmp, wav, out); os.remove(wav)
        if ok: os.remove(tmp); return True
    except Exception as e:
        print("som falhou:", type(e).__name__, e, file=sys.stderr)
    return False


def render(out):
    tmp = out[:-4] + ".part.mp4"
    p = C.encoder(tmp, W, H, FPS)
    N = int(TOTAL * FPS)
    for i in range(N):
        im = frame_at(i)
        k = seg(i / FPS, TOTAL - 0.35, TOTAL)
        if k > 0: im = Image.blend(im, Image.new("RGB", (W, H), BG), k)
        p.stdin.write(im.tobytes())
    p.stdin.close()
    if p.wait() != 0: sys.exit("ffmpeg falhou")
    if soundtrack(tmp, out): return
    os.replace(tmp, out)

if __name__ == "__main__":
    if V.get("stills"):
        for x in V["stills"].split(","):
            t = float(x); im, _ = scene(t); d = ImageDraw.Draw(im, "RGBA"); hud(d, t, 1, False)
            im.save(f"{V['out']}_{t:05.2f}.jpg", quality=88)
    else:
        render(V["out"])
