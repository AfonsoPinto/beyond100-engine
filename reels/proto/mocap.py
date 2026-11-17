"""Movimento real (CMU Graphics Lab Motion Capture Database, mocap.cs.cmu.edu; dados de uso livre, também comercial,
com pedido de crédito; criada com financiamento NSF EIA-0196217).
Lê ASF/AMC, calcula as articulações (cinemática direta) e extrai ciclos de passada para o esqueleto dos Reels:
corrida, passos laterais para cada lado. Saída: mocap_cycles.json (coordenadas no referencial do corpo, já à escala do esqueleto).
  python -m reels.proto.mocap <pasta com .asf/.amc> <saída.json> [<preview.png>]"""
import json, math, os, sys

# ---------------------------------------------------------------- matrizes 3x3
def mm(A, B): return [[sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
def mv(A, v): return [sum(A[i][k] * v[k] for k in range(3)) for i in range(3)]
def tr(A): return [[A[j][i] for j in range(3)] for i in range(3)]
def rx(a): c, s = math.cos(a), math.sin(a); return [[1, 0, 0], [0, c, -s], [0, s, c]]
def ry(a): c, s = math.cos(a), math.sin(a); return [[c, 0, s], [0, 1, 0], [-s, 0, c]]
def rz(a): c, s = math.cos(a), math.sin(a); return [[c, -s, 0], [s, c, 0], [0, 0, 1]]
def euler_sxyz(x, y, z):
    """eixos fixos x, depois y, depois z (como o transforms3d 'sxyz', usado nos leitores habituais de ASF/AMC)"""
    return mm(rz(z), mm(ry(y), rx(x)))

# ---------------------------------------------------------------- ASF / AMC
def parse_asf(path):
    bones, hier, sec, cur = {}, {}, None, None
    root = dict(order=["TX", "TY", "TZ", "RX", "RY", "RZ"], axis=[0, 0, 0])
    for raw in open(path, encoding="latin-1"):
        line = raw.strip()
        if not line or line.startswith("#"): continue
        if line.startswith(":"):
            sec = line.split()[0][1:]; continue
        w = line.split()
        if sec == "root":
            if w[0] == "order": root["order"] = [x.upper() for x in w[1:]]
            if w[0] == "orientation": root["axis"] = [float(x) for x in w[1:4]]
        elif sec == "bonedata":
            if w[0] == "begin": cur = dict(dof=[], axis=[0, 0, 0], direction=[0, 0, 0], length=0.0)
            elif w[0] == "end": bones[cur["name"]] = cur; cur = None
            elif w[0] == "name": cur["name"] = w[1]
            elif w[0] == "direction": cur["direction"] = [float(x) for x in w[1:4]]
            elif w[0] == "length": cur["length"] = float(w[1])
            elif w[0] == "axis": cur["axis"] = [float(x) for x in w[1:4]]
            elif w[0] == "dof": cur["dof"] = [x.lower() for x in w[1:]]
        elif sec == "hierarchy":
            if w[0] in ("begin", "end"): continue
            hier[w[0]] = w[1:]
    for b in bones.values():
        a = [math.radians(x) for x in b["axis"]]
        b["C"] = euler_sxyz(*a); b["Ci"] = tr(b["C"])
    ra = [math.radians(x) for x in root["axis"]]
    root["C"] = euler_sxyz(*ra); root["Ci"] = tr(root["C"])
    return bones, hier, root

def parse_amc(path):
    frames, cur = [], None
    for raw in open(path, encoding="latin-1"):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(":"): continue
        w = line.split()
        if len(w) == 1 and w[0].isdigit():
            cur = {}; frames.append(cur); continue
        if cur is not None: cur[w[0]] = [float(x) for x in w[1:]]
    return frames

def fk(bones, hier, root, fr):
    """posições do fim de cada osso (e 'root') num frame, em unidades do ficheiro, eixo Y para cima"""
    vals = dict(zip(root["order"], fr["root"]))
    rot = euler_sxyz(*(math.radians(vals.get(k, 0.0)) for k in ("RX", "RY", "RZ")))
    M = mm(root["C"], mm(rot, root["Ci"]))
    pos = {"root": [vals.get("TX", 0.0), vals.get("TY", 0.0), vals.get("TZ", 0.0)]}
    mats = {"root": M}
    stack = ["root"]
    while stack:
        p = stack.pop()
        for c in hier.get(p, []):
            b = bones[c]; ang = {"rx": 0.0, "ry": 0.0, "rz": 0.0}
            for k, v in zip(b["dof"], fr.get(c, [])): ang[k] = math.radians(v)
            R = euler_sxyz(ang["rx"], ang["ry"], ang["rz"])
            Mc = mm(mats[p], mm(b["C"], mm(R, b["Ci"])))
            d = mv(Mc, b["direction"])
            pos[c] = [pos[p][i] + b["length"] * d[i] for i in range(3)]
            mats[c] = Mc; stack.append(c)
    return pos

# ---------------------------------------------------------------- articulações do nosso esqueleto
MAP = dict(P="root", hipL="lhipjoint", hipR="rhipjoint", kneeL="lfemur", kneeR="rfemur", ankL="ltibia", ankR="rtibia",
           toeL="lfoot", toeR="rfoot", C="upperback", neck="lowerneck", head="head", shL="lclavicle", shR="rclavicle",
           elL="lhumerus", elR="rhumerus", handL="lradius", handR="rradius")

def to_z_up(p): return (p[0], -p[2], p[1])       # CMU: Y para cima → nosso Z para cima (rotação, sem espelhar)

def clip_joints(asf, amc):
    bones, hier, root = parse_asf(asf)
    out = []
    for fr in parse_amc(amc):
        pos = fk(bones, hier, root, fr)
        out.append({k: to_z_up(pos[v]) for k, v in MAP.items() if v in pos})
    return out

def local_frames(J, target_leg=0.89):
    """cada frame no referencial do corpo: s (lado direito), f (frente), z; origem no chão por baixo da anca; escala do esqueleto"""
    legs = [math.dist(j["hipL"], j["kneeL"]) + math.dist(j["kneeL"], j["ankL"]) for j in J]
    k = target_leg / (sum(legs) / len(legs))
    floor = min(min(j["toeL"][2], j["toeR"][2], j["ankL"][2], j["ankR"][2]) for j in J)
    heads = []
    for j in J:
        s = (j["hipR"][0] - j["hipL"][0], j["hipR"][1] - j["hipL"][1]); n = math.hypot(*s) or 1; s = (s[0] / n, s[1] / n)
        heads.append(s)
    out = []
    for i, j in enumerate(J):
        w = heads[max(0, i - 15): i + 16]                        # direção suavizada (evita tremer com o balanço da anca)
        sx, sy = sum(a for a, _ in w), sum(b for _, b in w); n = math.hypot(sx, sy) or 1; s = (sx / n, sy / n)
        f = (-s[1], s[0])
        o = j["P"]
        loc = {}
        for name, p in j.items():
            dx, dy = p[0] - o[0], p[1] - o[1]
            loc[name] = [round((dx * s[0] + dy * s[1]) * k, 4), round((dx * f[0] + dy * f[1]) * k, 4), round((p[2] - floor) * k, 4)]
        out.append(dict(loc=loc, root=(o[0] * k, o[1] * k), s=s, f=f))
    return out, k

def find_cycle(L, fps):
    """dois apoios consecutivos do pé esquerdo (mínimos da altura do tornozelo) no meio do clip"""
    h = [fr["loc"]["ankL"][2] for fr in L]
    n = len(h); mins = []
    for i in range(3, n - 3):
        if h[i] == min(h[i - 3: i + 4]) and (not mins or i - mins[-1] > fps * 0.25): mins.append(i)
    if len(mins) >= 3:
        mid = len(mins) // 2; return mins[mid - 1], mins[mid]
    return n // 3, n // 3 + int(fps * 0.7)

def cycle(L, a, b, fps, n=32):
    dx = L[b]["root"][0] - L[a]["root"][0]; dy = L[b]["root"][1] - L[a]["root"][1]
    s, f = L[a]["s"], L[a]["f"]
    d_loc = (dx * s[0] + dy * s[1], dx * f[0] + dy * f[1])           # deslocação no referencial do corpo
    frames = []
    for q in range(n):
        u = a + (b - a) * q / n; i = int(u); w = u - i; j = min(i + 1, b)
        frames.append({k: [round(L[i]["loc"][k][c] * (1 - w) + L[j]["loc"][k][c] * w, 4) for c in range(3)] for k in L[i]["loc"]})
    return dict(stride=round(math.hypot(*d_loc), 3), dir=[round(d_loc[0], 3), round(d_loc[1], 3)], dur=round((b - a) / fps, 3), frames=frames)

CLIPS = {                       # nome: (sujeito, ensaio, descrição na base CMU)
    "run": ("02", "03", "run/jog"),
    "side_left": ("127", "13", "Run Side Step Left"),
    "side_right": ("127", "14", "Run Side Step Right"),
}

def main():
    src, out = sys.argv[1], sys.argv[2]
    res = {"_fonte": "CMU Graphics Lab Motion Capture Database (mocap.cs.cmu.edu), NSF EIA-0196217", "clips": {}}
    for name, (sub, tri, desc) in CLIPS.items():
        asf = os.path.join(src, f"{sub}.asf"); amc = os.path.join(src, f"{sub}_{tri}.amc")
        if not (os.path.exists(asf) and os.path.exists(amc)):
            print("em falta:", asf, amc); continue
        J = clip_joints(asf, amc); L, k = local_frames(J)
        a, b = find_cycle(L, 120)
        c = cycle(L, a, b, 120); c["desc"] = desc; c["src"] = f"{sub}_{tri}"
        res["clips"][name] = c
        print(f"{name}: {len(J)} frames, ciclo {a}-{b} ({c['dur']} s), passada {c['stride']} m, direção {c['dir']}")
    json.dump(res, open(out, "w"))
    if len(sys.argv) > 3: preview(res, sys.argv[3])

def preview(res, path):
    from PIL import Image, ImageDraw
    clips = list(res["clips"].items()); W_, H_ = 220, 300
    im = Image.new("RGB", (W_ * 8, H_ * len(clips) * 2), (20, 28, 40)); d = ImageDraw.Draw(im)
    bones = [("hipL", "kneeL"), ("kneeL", "ankL"), ("ankL", "toeL"), ("hipR", "kneeR"), ("kneeR", "ankR"), ("ankR", "toeR"), ("P", "C"),
             ("C", "neck"), ("neck", "head"), ("shL", "elL"), ("elL", "handL"), ("shR", "elR"), ("elR", "handR"), ("shL", "shR"), ("hipL", "hipR")]
    for r, (name, c) in enumerate(clips):
        for q in range(8):
            fr = c["frames"][q * 4]
            for view in (0, 1):                       # 0: de lado (f, z), 1: de frente (s, z)
                ox, oy = q * W_ + W_ // 2, (r * 2 + view) * H_ + H_ - 20
                for a, b in bones:
                    if a in fr and b in fr:
                        pa, pb = fr[a], fr[b]; ia, ib = (1 if view == 0 else 0), (1 if view == 0 else 0)
                        col = (255, 120, 110) if a.endswith("R") or b.endswith("R") else (230, 230, 230)
                        d.line([(ox + pa[ia] * 120, oy - pa[2] * 120), (ox + pb[ib] * 120, oy - pb[2] * 120)], fill=col, width=3)
                d.text((q * W_ + 6, (r * 2 + view) * H_ + 6), f"{name} {'lado' if view == 0 else 'frente'} {q * 4}", fill=(200, 200, 200))
    im.save(path)

if __name__ == "__main__":
    main()
