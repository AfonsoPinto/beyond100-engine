"""Esqueleto dos jogadores para o protótipo realista (Python puro): postura de atleta, passadas com os pés a levantar,
split-step antes do batimento do adversário, rotação do tronco na preparação, braços e pernas com cinemática inversa,
pose de smash (braço livre a apontar à bola). Recebe a jogada do motor atual (point.py) e devolve as articulações."""
import math

def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))
def norm(a):
    l = length(a); return mul(a, 1 / l) if l > 1e-9 else (0.0, 0.0, 1.0)
def lerp(a, b, u): return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))
def clamp(x, a, b): return max(a, min(b, x))
def smooth(u): u = clamp(u, 0, 1); return u * u * (3 - 2 * u)
def ease_in(u): u = clamp(u, 0, 1); return u * u * u
def ease_out(u): u = clamp(u, 0, 1); return 1 - (1 - u) ** 3
def rotz(v, a):
    c, s = math.cos(a), math.sin(a); return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])
Z = (0.0, 0.0, 1.0)

UPPER, FORE = 0.30, 0.29          # braço

# movimento real: ciclo de corrida da CMU Graphics Lab Motion Capture Database (mocap.cs.cmu.edu, NSF EIA-0196217)
import json as _json, os as _os
try:
    _MC = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "mocap_cycles.json")))["clips"]
except (OSError, ValueError, KeyError):
    _MC = {}

def mocap_pose(name, phase):
    """articulações do ciclo (referencial do movimento: x = lado, y = frente, z = altura), interpoladas na fase 0-1"""
    c = _MC.get(name)
    if not c: return None
    fr = c["frames"]; n = len(fr); u = (phase % 1.0) * n; i = int(u) % n; j = (i + 1) % n; w = u - int(u)
    return {k: tuple(fr[i][k][q] * (1 - w) + fr[j][k][q] * w for q in range(3)) for k in fr[i]}
THIGH, SHIN = 0.45, 0.44          # perna
R_OFF = 0.29                      # da mão ao centro da raquete


def ik(root, target, l1, l2, pole):
    """cinemática inversa de dois ossos: devolve (cotovelo/joelho, ponta)"""
    d = sub(target, root); L = length(d)
    L = clamp(L, abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3)
    dn = norm(d); tip = add(root, mul(dn, L))
    a = (l1 * l1 + L * L - l2 * l2) / (2 * L)           # distância ao longo de d até ao pé da perpendicular
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    pv = sub(pole, mul(dn, dot(pole, dn))); pv = norm(pv) if length(pv) > 1e-6 else norm(cross(dn, (1, 0, 0)))
    return add(add(root, mul(dn, a)), mul(pv, h)), tip


class Rig:
    def __init__(self, pl, KP, ball_at, others_hits, r_off=0.29):
        self.roff = r_off; self._mc = None
        self.pl, self.KP, self.ball_at = pl, KP, ball_at
        self.face = pl.face
        self.hits = [(th, kind, ball_at(KP, th)) for th, kind in pl.hits]
        self.opp = sorted(others_hits)
        # distância percorrida (para a fase da passada)
        self.tab = []; d = 0.0; prev = None; t = -0.5
        while t < 12:
            x, y, _ = pl.base(t)
            if prev: d += math.hypot(x - prev[0], y - prev[1])
            self.tab.append((t, d)); prev = (x, y); t += 1 / 120
        # correção de alcance: no batimento, o corpo aproxima-se da bola o necessário
        self.corr = []
        for th, kind, B in self.hits:
            x, y, _ = pl.base(th)
            sh_h = 1.42 + (0.45 if kind == "smash" else 0)
            s0 = (self.face, 0, 0)
            shR = (x + s0[0] * 0.2, y, sh_h)
            reach = 0.57 + r_off + (0.04 if kind == "smash" else 0)
            v = sub(B, shR); L = length(v)
            ex = (0, 0, 0) if L <= reach else mul(norm((v[0], v[1], 0)), L - reach)
            self.corr.append((th, ex))

    def dist(self, t):
        i = clamp(int((t + 0.5) * 120), 0, len(self.tab) - 1); return self.tab[i][1]

    def base(self, t):
        x, y, _ = self.pl.base(t)
        for th, ex in self.corr:
            k = smooth(1 - abs(t - th) / 0.55)
            x += ex[0] * k; y += ex[1] * k
        return x, y

    def vel(self, t):
        a, b = self.base(t - 0.04), self.base(t + 0.04)
        return ((b[0] - a[0]) / 0.08, (b[1] - a[1]) / 0.08, 0.0)

    def swing(self, t):
        """batimento ativo: (dt, tipo, ponto de contacto)"""
        best = None
        for th, kind, B in self.hits:
            dt = t - th
            win = (-0.9, 0.85) if kind in ("smash", "serve") else (-0.65, 0.8)
            if win[0] <= dt <= win[1] and (best is None or abs(dt) < abs(best[0])):
                best = (dt, kind, B)
        return best

    def joints(self, t):
        f0 = (0.0, float(self.face), 0.0); s0 = (float(self.face), 0.0, 0.0)
        x, y = self.base(t); v = self.vel(t); sp = math.hypot(v[0], v[1])
        sw = self.swing(t)
        # ------------------------------------------------ rotação do corpo (yaw)
        yaw = 0.0
        if sp > 0.8:                                             # vira-se um pouco para onde corre
            mv = norm(v); ang = math.atan2(mv[1], mv[0]) - math.atan2(f0[1], f0[0])
            ang = (ang + math.pi) % (2 * math.pi) - math.pi
            yaw = clamp(ang, -0.9, 0.9) * 0.55 * min(1, sp / 3)
        coil = 0.0
        if sw:
            dt, kind, B = sw
            if kind in ("smash", "serve"):
                coil = -0.9 * smooth((dt + 0.9) / 0.5) if dt < -0.12 else (-0.9 + 1.5 * ease_out((dt + 0.12) / 0.3) if dt < 0.35 else 0.6 * (1 - smooth((dt - 0.35) / 0.5)))
            else:
                coil = -1.25 * smooth((dt + 0.65) / 0.35) if dt < -0.12 else (-1.25 + 2.0 * ease_out((dt + 0.12) / 0.3) if dt < 0.3 else 0.75 * (1 - smooth((dt - 0.3) / 0.5)))
            if kind == "bh": coil = -coil                         # esquerda: roda para o outro lado
            yaw = yaw * 0.3
        f = norm(rotz(f0, yaw + coil * 0.75)); s = norm(rotz(s0, yaw + coil * 0.75))      # ombros
        fh = norm(rotz(f0, yaw + coil * 0.35)); shs = norm(rotz(s0, yaw + coil * 0.35))  # anca
        # ------------------------------------------------ altura e saltos
        ph = 2 * math.pi * self.dist(t) / 1.5
        run = min(1, sp / 1.8)
        hz = 0.88 - 0.03 * run + 0.025 * abs(math.sin(ph)) * run
        jump = 0.0
        if sw and sw[1] in ("smash", "serve"):
            dt = sw[0]; jump = (0.45 if sw[1] == "smash" else 0.12) * math.sin(math.pi * clamp((dt + 0.3) / 0.62, 0, 1))
        elif sw:
            hz -= 0.07 * smooth(1 - abs(sw[0]) / 0.35)            # baixa-se para bater
        for th in self.opp:                                      # split-step quando o adversário bate
            u = (t - (th - 0.12)) / 0.28
            if 0 <= u <= 1 and sp < 2.5: jump = max(jump, 0.07 * math.sin(math.pi * u))
        P = (x, y, hz + jump)
        lean = 0.05 + 0.1 * run + (0.08 if sw and sw[1] not in ("smash", "serve") and abs(sw[0]) < 0.3 else 0)
        C = add(P, add((0, 0, 0.5), mul(f, lean)))
        neck = add(C, (0, 0, 0.1)); head = add(neck, add((0, 0, 0.15), mul(f, 0.02)))
        shL, shR = add(C, mul(s, -0.2)), add(C, mul(s, 0.2))
        hipL, hipR = add(P, mul(shs, -0.1)), add(P, mul(shs, 0.1))
        # ------------------------------------------------ pés: passada com o pé a levantar
        mv = norm(v) if sp > 0.2 else fh
        A = min(0.34, 0.15 * sp)
        dl, dr = A * math.sin(ph), -A * math.sin(ph)
        lift = 0.13 * min(1, sp / 1.5)
        gl = (P[0], P[1], 0.0)
        aL = add(add(gl, mul(shs, -0.17)), add(mul(mv, dl), (0, 0, 0.08 + jump * 0.85 + lift * max(0, math.cos(ph)))))
        aR = add(add(gl, mul(shs, 0.17)), add(mul(mv, dr), (0, 0, 0.08 + jump * 0.85 + lift * max(0, -math.cos(ph)))))
        if sw and sw[1] not in ("smash", "serve"):                 # passo à frente com o pé contrário no batimento
            k = smooth(1 - abs(sw[0] + 0.05) / 0.4)
            aL = add(aL, add(mul(fh, 0.28 * k), mul(shs, 0.05 * k)))
            aR = add(aR, mul(fh, -0.12 * k))
        if jump > 0.05 and sw and sw[1] in ("smash", "serve"):                # no ar: pés juntos e uma perna dobrada
            aR = add(aR, add(mul(fh, -0.18), (0, 0, 0.12)))
        # ---- corrida real (CMU): pernas, anca e balanço quando se desloca; a parte de cima continua a ser do batimento
        wmc = smooth((sp - 0.7) / 1.3) * (0.35 if (sw and abs(sw[0]) < 0.25) else 1.0)
        mpose = mocap_pose("run", self.dist(t) / max(0.9, min(2.0, 0.72 * sp))) if wmc > 0 and _MC else None
        if mpose:
            fm = norm((v[0], v[1], 0.0)); sm = (fm[1], -fm[0], 0.0)
            W_ = lambda l: (x + sm[0] * l[0] + fm[0] * l[1], y + sm[1] * l[0] + fm[1] * l[1], l[2] + jump * 0.85)
            dz = (mpose["P"][2] + jump) - P[2]
            P = (P[0], P[1], P[2] + dz * wmc)
            hipL = lerp(hipL, W_(mpose["hipL"]), wmc); hipR = lerp(hipR, W_(mpose["hipR"]), wmc)
            aL = lerp(aL, W_(mpose["ankL"]), wmc); aR = lerp(aR, W_(mpose["ankR"]), wmc)
            C = add(C, (0, 0, dz * wmc)); neck = add(neck, (0, 0, dz * wmc)); head = add(head, (0, 0, dz * wmc))
            shL = add(shL, (0, 0, dz * wmc)); shR = add(shR, (0, 0, dz * wmc))
            pkL = sub(W_(mpose["kneeL"]), lerp(W_(mpose["hipL"]), W_(mpose["ankL"]), 0.5))
            pkR = sub(W_(mpose["kneeR"]), lerp(W_(mpose["hipR"]), W_(mpose["ankR"]), 0.5))
            polL = norm(lerp(add(mul(fh, 1.0), mul(shs, -0.2)), pkL, wmc)); polR = norm(lerp(add(mul(fh, 1.0), mul(shs, 0.2)), pkR, wmc))
            self._mc = (mpose, W_, wmc)
        else:
            polL, polR = add(mul(fh, 1.0), mul(shs, -0.2)), add(mul(fh, 1.0), mul(shs, 0.2)); self._mc = None
        kL, aL = ik(hipL, aL, THIGH, SHIN, polL)
        kR, aR = ik(hipR, aR, THIGH, SHIN, polR)
        toeL = add(aL, add(mul(norm(add(fh, mul(shs, -0.15))), 0.17), (0, 0, -0.06)))
        toeR = add(aR, add(mul(norm(add(fh, mul(shs, 0.15))), 0.17), (0, 0, -0.06)))
        if self._mc:
            mp, W_, wm = self._mc
            toeL = lerp(toeL, add(aL, sub(W_(mp["toeL"]), W_(mp["ankL"]))), wm); toeR = lerp(toeR, add(aR, sub(W_(mp["toeR"]), W_(mp["ankR"]))), wm)
        # ------------------------------------------------ raquete e braços
        ready_rc = add(C, add(mul(f, 0.42), add(mul(s, 0.08), (0, 0, -0.12))))
        ready_rd = norm(add(mul(f, 0.55), add((0, 0, 0.7), mul(s, 0.15))))
        rc, rd = ready_rc, ready_rd
        lh = None
        if sw:
            dt, kind, B = sw
            if kind in ("smash", "serve"):
                back_rc = add(shR, add((0, 0, 0.18), mul(f, -0.32))); back_rd = norm(add((0, 0, -0.9), mul(f, -0.35)))
                con_rd = norm(add((0, 0, 0.85), mul(f, 0.45)))
                fol_rc = add(P, add(mul(s, -0.3), add(mul(f, 0.35), (0, 0, 0.35)))); fol_rd = norm(add((0, 0, -0.75), add(mul(f, 0.5), mul(s, -0.3))))
                ks = [(-0.9, ready_rc, ready_rd), (-0.55, back_rc, back_rd), (-0.13, back_rc, back_rd), (0.0, B, con_rd),
                      (0.3, fol_rc, fol_rd), (0.85, ready_rc, ready_rd)]
                if dt < -0.05: lh = add(shL, add((0, 0, 0.55), mul(f, 0.22)))           # braço livre a apontar à bola
            elif kind == "bh":                                       # esquerda: prepara do lado esquerdo e termina por cima do ombro direito
                back_rc = add(shL, add(mul(s, -0.32), add(mul(f, -0.42), (0, 0, 0.08)))); back_rd = norm(add(mul(f, -0.7), add((0, 0, 0.5), mul(s, -0.25))))
                con_rd = norm(add(mul(s, -0.9), add(mul(f, 0.25), (0, 0, 0.15))))
                fol_rc = add(shR, add((0, 0, 0.28), mul(f, 0.2))); fol_rd = norm(add((0, 0, 0.8), add(mul(s, 0.45), mul(f, 0.1))))
                ks = [(-0.65, ready_rc, ready_rd), (-0.32, back_rc, back_rd), (0.0, B, con_rd), (0.32, fol_rc, fol_rd), (0.8, ready_rc, ready_rd)]
                lh = None                                                     # as duas mãos na raquete
            else:
                back_rc = add(shR, add(mul(s, 0.38), add(mul(f, -0.42), (0, 0, 0.05)))); back_rd = norm(add(mul(f, -0.7), add((0, 0, 0.5), mul(s, 0.25))))
                con_rd = norm(add(mul(s, 0.9), add(mul(f, 0.25), (0, 0, 0.15))))
                fol_rc = add(shL, add((0, 0, 0.25), mul(f, 0.22))); fol_rd = norm(add((0, 0, 0.8), add(mul(s, -0.45), mul(f, 0.1))))
                ks = [(-0.65, ready_rc, ready_rd), (-0.32, back_rc, back_rd), (0.0, B, con_rd), (0.32, fol_rc, fol_rd), (0.8, ready_rc, ready_rd)]
                if dt < -0.02: lh = add(shL, add(mul(f, 0.48), add(mul(s, 0.12), (0, 0, 0.02))))   # aponta à bola na preparação
                elif dt < 0.4: lh = add(C, add(mul(f, 0.22), add(mul(s, -0.12), (0, 0, -0.12))))
            for (ta, rca, rda), (tb, rcb, rdb) in zip(ks, ks[1:]):
                if ta <= dt <= tb:
                    u = (dt - ta) / (tb - ta)
                    u = ease_in(u) if tb == 0.0 else ease_out(u) if ta == 0.0 else smooth(u)
                    rc, rd = lerp(rca, rcb, u), norm(lerp(rda, rdb, u)); break
        handR = sub(rc, mul(rd, self.roff))
        eR, handR = ik(shR, handR, UPPER, FORE, add((0, 0, -0.7), add(mul(f, -0.3), mul(s, 0.35))))
        rc = add(handR, mul(rd, self.roff))
        if lh is None:
            lh = sub(rc, mul(rd, 0.17))                                   # em espera: a mão livre segura a raquete
            if self._mc and not sw:
                mp, W_, wm = self._mc
                lh = lerp(lh, add(shL, sub(W_(mp["handL"]), W_(mp["shL"]))), wm * 0.85)
        eL, handL = ik(shL, lh, UPPER, FORE, add((0, 0, -0.7), add(mul(f, -0.2), mul(s, -0.35))))
        rn = sub(f, mul(rd, dot(f, rd))); rn = norm(rn) if length(rn) > 1e-3 else Z
        return dict(P=P, C=C, neck=neck, head=head, shL=shL, shR=shR, elL=eL, elR=eR, handL=handL, handR=handR,
                    hipL=hipL, hipR=hipR, kneeL=kL, kneeR=kR, ankL=aL, ankR=aR, toeL=toeL, toeR=toeR,
                    rc=rc, rd=rd, rn=rn, f=f, s=s, fh=fh, sh=shs)
