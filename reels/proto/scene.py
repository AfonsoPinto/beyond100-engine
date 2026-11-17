"""Cena do Blender (Cycles) para o protótipo realista: pavilhão, campo de padel com vidros, bancadas com público,
painéis com o nome do torneio, quatro figuras anónimas (manequins) e a bola. Corre com:
  blender -b -P reels/proto/scene.py -- frames.json <parte> <nº de partes> <pasta> <full|stills>
A jogada, as câmaras e os tempos vêm do motor atual (export.py), por isso o resultado é o mesmo ponto, só que renderizado."""
import bpy, json, math, os, sys
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
D = json.load(open(argv[0])); part, parts, outdir, mode = int(argv[1]), int(argv[2]), argv[3], argv[4]
FR = D["frames"]; N = len(FR); HW, HL, NET = D["HW"], D["HL"], D["NET"]
if mode == "stills":
    todo = D["stills"] if part == 0 else []
else:
    per = math.ceil(N / parts); todo = list(range(part * per, min(N, (part + 1) * per)))
os.makedirs(outdir, exist_ok=True)
if not todo:
    print("nada para esta parte"); sys.exit(0)
keys = sorted({k for f in todo for k in (f - 1, f, f + 1) if 0 <= k < N})

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

def lin(c): return tuple((x / 255.0) ** 2.2 for x in c[:3])

def principled(name, color, rough=0.5, metal=0.0, emit=None, es=0.0, sheen=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    def s(k, v):
        if k in b.inputs: b.inputs[k].default_value = v
    s("Base Color", (*color, 1)); s("Roughness", rough); s("Metallic", metal)
    if emit is not None: s("Emission Color", (*emit, 1)); s("Emission Strength", es)
    if sheen: s("Sheen Weight", sheen)
    if coat: s("Coat Weight", coat)
    return m

def mixmat(name, a_shader, fac):
    """mistura transparente + material (vidro barato e limpo, rede)"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes.get("Principled BSDF"); out = nt.nodes.get("Material Output")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mix = nt.nodes.new("ShaderNodeMixShader")
    for k, v in a_shader.items():
        if k in b.inputs: b.inputs[k].default_value = v
    mix.inputs["Fac"].default_value = fac
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(b.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m

def add_bump(m, scale, strength):
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = 6
    bu = nt.nodes.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = strength
    nt.links.new(nz.outputs["Fac"], bu.inputs["Height"]); nt.links.new(bu.outputs["Normal"], b.inputs["Normal"])

def box(name, loc, size, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.active_object
    o.name = name; o.scale = size; o.data.materials.append(m); return o

def smooth(o):
    for p in o.data.polygons: p.use_smooth = True

# ------------------------------------------------------------------ materiais
TURF = principled("turf", lin((28, 92, 168)), rough=0.9); add_bump(TURF, 900, 0.35)
OUTF = principled("outfloor", lin((14, 40, 78)), rough=0.85); add_bump(OUTF, 600, 0.2)
LINE = principled("line", lin((240, 244, 250)), rough=0.6, emit=lin((240, 244, 250)), es=0.15)
GLASS = mixmat("glass", {"Base Color": (0.8, 0.9, 1.0, 1), "Roughness": 0.06, "Metallic": 1.0}, 0.08)
METAL = principled("metal", lin((30, 34, 40)), rough=0.35, metal=0.9)
NETM = mixmat("net", {"Base Color": (0.02, 0.02, 0.03, 1), "Roughness": 0.8}, 0.6)
WHITE = principled("white", lin((245, 245, 245)), rough=0.5)
SKIN = principled("skin", lin((214, 176, 146)), rough=0.55, sheen=0.2)
SHORTS = principled("shorts", lin((26, 34, 54)), rough=0.8, sheen=0.3)
SHOE = principled("shoe", lin((245, 245, 245)), rough=0.5)
BALL = principled("ball", lin((217, 242, 61)), rough=0.9, emit=lin((217, 242, 61)), es=0.6, sheen=1.0)
PADDLE = principled("paddle", lin((24, 26, 32)), rough=0.3, coat=1.0)
BOARD = principled("board", lin((10, 18, 32)), rough=0.4)
ACCM = principled("acc", lin((217, 242, 61)), emit=lin((217, 242, 61)), es=4.0)
TXT = principled("txt", lin((247, 242, 230)), emit=lin((247, 242, 230)), es=3.0)

# público: pessoas em 3D (tronco + cabeça), cor por pessoa num atributo
CROWD = bpy.data.materials.new("crowd"); CROWD.use_nodes = True; nt = CROWD.node_tree
b = nt.nodes.get("Principled BSDF"); at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "col"
nt.links.new(at.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.85
if "Sheen Weight" in b.inputs: b.inputs["Sheen Weight"].default_value = 0.3
SEAT = principled("seat", lin((34, 38, 46)), rough=0.8)
# ------------------------------------------------------------------ pavilhão e campo (padel ou ténis)
SPORT, SURF, SETTING = D.get("sport", "padel"), D.get("surface", "padel"), D.get("setting", "indoor")
SW = D.get("SW", 4.115)
def beam(name, a, b_, r, m):
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=1, depth=2); o = bpy.context.active_object
    a, b_ = Vector(a), Vector(b_); d = b_ - a
    o.location = (a + b_) / 2; o.rotation_mode = "QUATERNION"; o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o.scale = (r, r, d.length / 2); o.data.materials.append(m); return o
if SPORT == "padel":
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.01)); o = bpy.context.active_object; o.scale = (60, 70, 1); o.data.materials.append(OUTF)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); o = bpy.context.active_object; o.scale = (2 * HW, 2 * HL, 1); o.data.materials.append(TURF)
    W_ = 0.05
    for (x0, y0, x1, y1) in ((-HW, -HL, HW, -HL), (-HW, HL, HW, HL), (-HW, -6.95, HW, -6.95), (-HW, 6.95, HW, 6.95), (0, -6.95, 0, 6.95),
                             (-HW, -HL, -HW, HL), (HW, -HL, HW, HL)):
        box("line", ((x0 + x1) / 2, (y0 + y1) / 2, 0.002), (max(W_, abs(x1 - x0)), max(W_, abs(y1 - y0)), 0.004), LINE)
    box("net", (0, 0, NET / 2), (2 * HW, 0.02, NET), NETM)
    box("netband", (0, 0, NET - 0.03), (2 * HW, 0.03, 0.06), WHITE)
    for sx in (-HW - 0.05, HW + 0.05): box("post", (sx, 0, 0.5), (0.08, 0.08, 1.0), METAL)
    for sgn in (-1, 1):
        y = sgn * HL
        box("glass_back", (0, y + sgn * 0.01, 1.5), (2 * HW, 0.012, 3.0), GLASS)
        for sx in (-HW, HW):
            box("glass_side", (sx + (0.01 if sx > 0 else -0.01), sgn * (HL - 1), 1.5), (0.012, 2.0, 3.0), GLASS)
            box("glass_side2", (sx + (0.01 if sx > 0 else -0.01), sgn * (HL - 3), 1.0), (0.012, 2.0, 2.0), GLASS)
        for i in range(6):
            box("post", (-HW + 2 * i, y + sgn * 0.06, 2.0), (0.06, 0.06, 4.0), METAL)
        box("rail", (0, y + sgn * 0.06, 4.0), (2 * HW + 0.1, 0.06, 0.06), METAL)
        for sx in (-HW, HW):
            for yy in (HL - 2, HL - 4):
                box("post", (sx + (0.06 if sx > 0 else -0.06), sgn * yy, 1.5), (0.06, 0.06, 3.0), METAL)
    for sx in (-HW, HW):
        box("rail_side", (sx + (0.06 if sx > 0 else -0.06), 0, 3.0), (0.05, 2 * HL - 8, 0.05), METAL)
    STAND = dict(y=HL + 5.0, x=HW + 5.0, wy=34, wx=30, rows=12)
    BOARDS = [(HL + 1.6, 0.0), (-HL - 1.6, math.pi)]
else:
    # cores do piso por superfície (dentro e fora das linhas)
    pal = {"hard": ((34, 92, 156), (28, 74, 120)), "clay": ((188, 94, 56), (178, 88, 52)), "grass": ((76, 140, 64), (70, 130, 58))}[SURF if SURF in ("hard", "clay", "grass") else "hard"]
    IN = principled("court_in", lin(pal[0]), rough=0.85 if SURF != "hard" else 0.6); add_bump(IN, 700 if SURF == "clay" else 500, 0.35 if SURF == "clay" else 0.15)
    OUT = principled("court_out", lin(pal[1]), rough=0.85 if SURF != "hard" else 0.6); add_bump(OUT, 700, 0.3 if SURF == "clay" else 0.12)
    if SURF == "grass":                                              # riscas do corte da relva
        for m_ in (IN, OUT):
            nt = m_.node_tree; b = nt.nodes.get("Principled BSDF")
            g = nt.nodes.new("ShaderNodeNewGeometry"); sx_ = nt.nodes.new("ShaderNodeSeparateXYZ"); mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = 1 / 2.4
            fr_ = nt.nodes.new("ShaderNodeMath"); fr_.operation = "FRACT"; lt = nt.nodes.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.5
            mx = nt.nodes.new("ShaderNodeMixRGB"); mx.inputs[1].default_value = (*lin(pal[0]), 1); mx.inputs[2].default_value = (*lin((96, 162, 78)), 1)
            nt.links.new(g.outputs["Position"], sx_.inputs[0]); nt.links.new(sx_.outputs["Y"], mu.inputs[0]); nt.links.new(mu.outputs[0], fr_.inputs[0])
            nt.links.new(fr_.outputs[0], lt.inputs[0]); nt.links.new(lt.outputs[0], mx.inputs["Fac"]); nt.links.new(mx.outputs[0], b.inputs["Base Color"])
    RX, RY = HW + 3.7, HL + 6.4                                     # zona à volta do campo
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.012)); o = bpy.context.active_object; o.scale = (80, 90, 1); o.data.materials.append(principled("concourse", lin((40, 44, 52)), rough=0.8))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.002)); o = bpy.context.active_object; o.scale = (2 * RX, 2 * RY, 1); o.data.materials.append(OUT)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); o = bpy.context.active_object; o.scale = (2 * HW, 2 * HL, 1); o.data.materials.append(IN)
    W_ = 0.05
    for (x0, y0, x1, y1) in ((-HW, -HL, HW, -HL), (-HW, HL, HW, HL), (-HW, -HL, -HW, HL), (HW, -HL, HW, HL), (-SW, -HL, -SW, HL), (SW, -HL, SW, HL),
                             (-SW, -6.4, SW, -6.4), (-SW, 6.4, SW, 6.4), (0, -6.4, 0, 6.4), (0, -HL, 0, -HL + 0.1), (0, HL, 0, HL - 0.1)):
        box("line", ((x0 + x1) / 2, (y0 + y1) / 2, 0.002), (max(W_, abs(x1 - x0)), max(W_, abs(y1 - y0)), 0.004), LINE)
    # rede com curva (1,07 m nos postes, 0,914 m ao centro), fita branca e cinta central
    import bmesh as _bm
    nx = HW + 0.914; bm_ = _bm.new(); vs = []
    for i in range(41):
        x = -nx + 2 * nx * i / 40; top = NET + (1.07 - NET) * (x / nx) ** 2
        vs.append((bm_.verts.new((x, 0, 0.0)), bm_.verts.new((x, 0, top))))
    for i in range(40): bm_.faces.new((vs[i][0], vs[i + 1][0], vs[i + 1][1], vs[i][1]))
    me_ = bpy.data.meshes.new("net"); bm_.to_mesh(me_); bm_.free(); on = bpy.data.objects.new("net", me_); bpy.context.collection.objects.link(on); me_.materials.append(NETM)
    for i in range(8):
        xa, xb = -nx + 2 * nx * i / 8, -nx + 2 * nx * (i + 1) / 8
        beam("tape", (xa, 0, NET + (1.07 - NET) * (xa / nx) ** 2 - 0.02), (xb, 0, NET + (1.07 - NET) * (xb / nx) ** 2 - 0.02), 0.03, WHITE)
    box("strap", (0, 0, NET / 2), (0.05, 0.025, NET), WHITE)
    for sx in (-nx - 0.05, nx + 0.05): beam("post", (sx, 0, 0), (sx, 0, 1.1), 0.05, METAL)
    cx = nx + 1.1                                                   # cadeira do árbitro
    for dx in (-0.25, 0.25):
        for dy in (-0.25, 0.25): beam("chair_leg", (cx + dx, dy, 0), (cx + dx * 0.6, dy * 0.6, 1.9), 0.025, METAL)
    box("chair_seat", (cx, 0, 1.95), (0.55, 0.5, 0.08), METAL); box("chair_back", (cx + 0.25, 0, 2.25), (0.06, 0.5, 0.6), METAL)
    STAND = dict(y=RY + 1.2, x=RX + 1.2, wy=40, wx=46, rows=min(14, int(D.get("rows", 14))))
    BOARDS = [(RY, 0.0), (-RY, math.pi)]

# bancadas em degraus, com pessoas sentadas (2 700 aprox.)
import bmesh, random
RND = random.Random(5)
SHIRTS = [(200, 196, 190), (232, 230, 226), (40, 44, 52), (196, 64, 60), (60, 92, 160), (230, 200, 70), (90, 120, 90), (150, 150, 160),
          (20, 22, 28), (210, 120, 70), (120, 70, 140), (240, 240, 240)]
SKINS = [(222, 184, 150), (196, 150, 112), (150, 104, 70), (100, 70, 50), (236, 200, 170)]
cbm = bmesh.new(); col_layer = cbm.loops.layers.color.new("col")
PANTS = [(40, 44, 56), (70, 80, 100), (30, 30, 34), (120, 110, 96), (180, 176, 168)]
def _ell(M, colr, sub=1):
    r_ = bmesh.ops.create_icosphere(cbm, subdivisions=sub, radius=1.0, matrix=M)
    for v_ in r_["verts"]:
        for f_ in v_.link_faces:
            f_.smooth = True
            for lp in f_.loops: lp[col_layer] = (*colr, 1.0)
def _seg(M, a, b_, r, colr):
    """elipsoide alongado entre dois pontos (membros do público)"""
    a, b_ = Vector(a), Vector(b_); d = b_ - a; L = d.length
    q = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    _ell(M @ Matrix.Translation((a + b_) / 2) @ q @ Matrix.Diagonal((r, r, L / 2 + r * 0.4, 1)), colr)
def person(pos, rot, detail=False):
    c = lin(RND.choice(SHIRTS)); k = lin(RND.choice(SKINS)); hcol = lin(RND.choice([(30, 24, 20), (60, 44, 30), (120, 90, 60), (20, 20, 20), (200, 180, 140)]))
    lean = RND.uniform(-0.06, 0.06)
    M = Matrix.Translation(pos) @ Matrix.Rotation(rot + math.pi, 4, "Z")    # frente = -y local, virada para o campo
    if not detail:
        _ell(M @ Matrix.Translation((lean, 0, 0.32)) @ Matrix.Diagonal((0.21, 0.13, 0.3, 1)), c)
        _ell(M @ Matrix.Translation((lean * 1.4, 0.02, 0.72)) @ Matrix.Diagonal((0.105,) * 3 + (1,)), k)
        _ell(M @ Matrix.Translation((lean * 1.4, 0.05, 0.77)) @ Matrix.Diagonal((0.095,) * 3 + (1,)), hcol)
        return
    # espectador sentado (frente = -y local): coxas para a frente, braços no colo, cabeça um pouco virada
    pc = lin(RND.choice(PANTS)); sleeve = c if RND.random() < 0.4 else k
    hx = lean * 1.3; turn = RND.uniform(-0.35, 0.35)
    _ell(M @ Matrix.Translation((lean * 0.6, 0.0, 0.33)) @ Matrix.Diagonal((0.19, 0.12, 0.25, 1)), c)          # tronco
    _ell(M @ Matrix.Translation((lean * 0.9, 0.0, 0.52)) @ Matrix.Diagonal((0.21, 0.11, 0.07, 1)), c)          # ombros
    _ell(M @ Matrix.Translation((0, -0.02, 0.1)) @ Matrix.Diagonal((0.18, 0.13, 0.08, 1)), pc)                 # anca
    for sx in (-1, 1):
        _seg(M, (sx * 0.09, -0.02, 0.08), (sx * 0.1, -0.42, 0.1), 0.068, pc)                                   # coxa
        _seg(M, (sx * 0.1, -0.44, 0.08), (sx * 0.11, -0.47, -0.36), 0.05, pc)                                  # perna
        sh = (lean * 0.9 + sx * 0.19, 0.0, 0.52); el = (lean * 0.5 + sx * 0.2, -0.06, 0.28)
        _seg(M, sh, el, 0.05, sleeve)                                                                          # braço
        _seg(M, el, (sx * 0.08, -0.3, 0.17), 0.04, k)                                                          # antebraço no colo
    _seg(M, (hx * 0.8, 0, 0.56), (hx, -0.01, 0.66), 0.045, k)                                                  # pescoço
    H = M @ Matrix.Translation((hx, -0.01, 0.75)) @ Matrix.Rotation(turn, 4, "Z")
    _ell(H @ Matrix.Diagonal((0.085, 0.095, 0.11, 1)), k, 2)                                                   # cabeça
    _ell(H @ Matrix.Translation((0, 0.022, 0.03)) @ Matrix.Diagonal((0.09, 0.095, 0.1, 1)), hcol, 2)          # cabelo
def stand(cx, cy, w, rot, rows=12):
    R = Matrix.Rotation(rot, 3, "Z")
    for r in range(rows):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0)); s_ = bpy.context.active_object
        s_.scale = (w, 0.85, 0.5 * (r + 1)); s_.data.materials.append(SEAT)
        s_.location = Vector((cx, cy, 0)) + R @ Vector((0, r * 0.85, 0.25 * (r + 1))); s_.rotation_euler = (0, 0, rot)
        n = int(w / 0.55)
        for j in range(n):
            if RND.random() < 0.12: continue                          # lugares vazios
            off = Vector((-w / 2 + 0.275 + j * 0.55 + RND.uniform(-0.05, 0.05), r * 0.85 - 0.1, 0.5 * (r + 1)))
            person(Vector((cx, cy, 0)) + R @ off, rot + math.pi, detail=r < 6)
R_ = STAND["rows"]
stand(0, STAND["y"], STAND["wy"], 0, R_); stand(0, -STAND["y"], STAND["wy"], math.pi, R_)
stand(STAND["x"], 0, STAND["wx"], -math.pi / 2, R_); stand(-STAND["x"], 0, STAND["wx"], math.pi / 2, R_)
cme = bpy.data.meshes.new("crowd"); cbm.to_mesh(cme); cbm.free()
cob = bpy.data.objects.new("crowd", cme); bpy.context.collection.objects.link(cob); cme.materials.append(CROWD)

# painéis com o nome do torneio
font = None
fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "fonts", "Inter-Black.otf")
# a letra Inter (OTF) falha no Blender: fica a letra de origem do Blender
BIMG = bpy.data.images.load(os.path.join(os.path.dirname(os.path.abspath(argv[0])), "board.png"))
BM = bpy.data.materials.new("boardimg"); BM.use_nodes = True; nt = BM.node_tree; bb = nt.nodes.get("Principled BSDF")
ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = BIMG
nt.links.new(ti.outputs["Color"], bb.inputs["Base Color"])
if "Emission Color" in bb.inputs:
    nt.links.new(ti.outputs["Color"], bb.inputs["Emission Color"]); bb.inputs["Emission Strength"].default_value = 1.6
bb.inputs["Roughness"].default_value = 0.4
BW = 2 * HW + (6 if SPORT == "padel" else 12)
def board(y, rot):
    box("board", (0, y, 0.45), (BW, 0.12, 0.9), BOARD)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, y - math.copysign(0.065, y), 0.45)); pl = bpy.context.active_object
    pl.scale = (BW, 0.86, 1); pl.rotation_euler = (math.pi / 2, 0, rot); pl.data.materials.append(BM)
for (y_, r_) in BOARDS: board(y_, r_)
# ------------------------------------------------------------------ luz (pavilhão, dia ou noite)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes.get("Background")
LK = float(os.environ.get("PROTO_LIGHT", "1300")) * (1.6 if SPORT == "tennis" else 1.0)
if SETTING == "day":
    bg.inputs[0].default_value = (0.32, 0.5, 0.85, 1); bg.inputs[1].default_value = float(os.environ.get("PROTO_SKY", "1.0"))
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 30)); L = bpy.context.active_object
    L.data.energy = float(os.environ.get("PROTO_SUN", "4.5")); L.data.angle = math.radians(1.5); L.data.color = (1.0, 0.96, 0.9)
    L.rotation_euler = (math.radians(50), math.radians(18), math.radians(35))
else:
    bg.inputs[0].default_value = (0.003, 0.005, 0.009, 1) if SETTING == "indoor" else (0.004, 0.008, 0.02, 1); bg.inputs[1].default_value = 1.0
    xs = (-4.5, 4.5) if SPORT == "padel" else (-5, 5)
    ys = (-9, 0, 9) if SPORT == "padel" else (-12, 0, 12)
    for x in xs:
        for y in ys:
            bpy.ops.object.light_add(type="AREA", location=(x, y, 13 if SPORT == "padel" else 17)); L = bpy.context.active_object
            L.data.energy = LK * (1.0 if SPORT == "padel" else 1.7); L.data.size = 3.5 if SPORT == "padel" else 6.0; L.data.color = (1.0, 0.97, 0.92)
    for (x, y) in ((-STAND["x"] - 8, 0), (STAND["x"] + 8, 0), (0, -STAND["y"] - 8), (0, STAND["y"] + 8)):   # luz nas bancadas
        bpy.ops.object.light_add(type="AREA", location=(x * 0.75, y * 0.75, 12)); L = bpy.context.active_object
        L.data.energy = 700 if SPORT == "padel" else 1100; L.data.size = 8; L.data.color = (0.85, 0.9, 1.0)

# ------------------------------------------------------------------ figuras (anónimas) e raquetes
SKIN.node_tree.nodes.get("Principled BSDF").inputs["Subsurface Weight"].default_value = 0.15 if "Subsurface Weight" in SKIN.node_tree.nodes.get("Principled BSDF").inputs else 0
SOCK = principled("sock", lin((240, 240, 240)), rough=0.9, sheen=0.5)
SOLE = principled("sole", lin((220, 220, 215)), rough=0.6)
HAIR = principled("hair", lin((40, 30, 24)), rough=0.6, sheen=0.4)

def cone(name, r1, r2, m):
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=1, radius2=r2 / r1, depth=2); o = bpy.context.active_object
    o.name = name; o.data.materials.append(m); smooth(o); o["r"] = r1; return o
def sph(name, r, m, seg=28):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1); o = bpy.context.active_object
    o.name = name; o.scale = (r, r, r); o.data.materials.append(m); smooth(o); return o
def limb(o, a, b_, r):
    """cone/cilindro de a para b (o raio da base vem do objeto)"""
    a, b_ = Vector(a), Vector(b_); d = b_ - a; L = max(d.length, 1e-3)
    o.location = (a + b_) / 2; o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized()); o.scale = (r, r, L / 2)
def oriented(o, loc, x, y, z, sc_):
    """objeto com eixos próprios (x, y, z) e escala"""
    o.location = Vector(loc); o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Matrix((Vector(x), Vector(y), Vector(z))).transposed().to_quaternion(); o.scale = sc_

def racket_mat(frame_col):
    face = bpy.data.materials.new("racket_face"); face.use_nodes = True; nt = face.node_tree
    b = nt.nodes.get("Principled BSDF"); out = nt.nodes.get("Material Output")
    b.inputs["Base Color"].default_value = (0.02, 0.02, 0.025, 1); b.inputs["Roughness"].default_value = 0.35
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = 0.8
    tc = nt.nodes.new("ShaderNodeTexCoord"); vo = nt.nodes.new("ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 6.5
    if "Randomness" in vo.inputs: vo.inputs["Randomness"].default_value = 0.0
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.16; mr.inputs["From Max"].default_value = 0.2
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"]); nt.links.new(vo.outputs["Distance"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mx.inputs["Fac"]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(b.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return face, principled("racket_frame", lin(frame_col), rough=0.3, coat=1.0)

def strings_mat():
    m = bpy.data.materials.new("strings"); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes.get("Principled BSDF"); out = nt.nodes.get("Material Output")
    b.inputs["Base Color"].default_value = (0.85, 0.85, 0.8, 1); b.inputs["Roughness"].default_value = 0.5
    tc = nt.nodes.new("ShaderNodeTexCoord"); sx = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sx.inputs[0])
    mxs = []
    for ax, n_ in (("X", 9.0), ("Y", 10.5)):
        mu = nt.nodes.new("ShaderNodeMath"); mu.operation = "MULTIPLY"; mu.inputs[1].default_value = n_
        fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "PINGPONG"; fr.inputs[1].default_value = 0.5
        lt = nt.nodes.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.06
        nt.links.new(sx.outputs[ax], mu.inputs[0]); nt.links.new(mu.outputs[0], fr.inputs[0]); nt.links.new(fr.outputs[0], lt.inputs[0]); mxs.append(lt)
    mxm = nt.nodes.new("ShaderNodeMath"); mxm.operation = "MAXIMUM"
    nt.links.new(mxs[0].outputs[0], mxm.inputs[0]); nt.links.new(mxs[1].outputs[0], mxm.inputs[1])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mxm.outputs[0], mx.inputs["Fac"]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(b.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs["Surface"])
    return m

def make_tennis_racket(k, frame_col):
    """raquete de ténis: aro oval, cordas, garganta aberta e cabo (68,5 cm)"""
    frame_m = principled(f"tframe{k}", lin(frame_col), rough=0.3, coat=1.0); grip_m = principled(f"tgrip{k}", lin((30, 30, 34)), rough=0.8)
    bpy.ops.object.empty_add(location=(0, 0, 0)); root = bpy.context.active_object; root.name = f"racket{k}"; parts = []
    bpy.ops.mesh.primitive_torus_add(major_radius=1, minor_radius=0.075, major_segments=64, minor_segments=10); t = bpy.context.active_object
    t.scale = (0.125, 0.155, 0.125); t.data.materials.append(frame_m); smooth(t); parts.append(t)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=2); c = bpy.context.active_object
    c.scale = (0.118, 0.148, 0.0015); c.data.materials.append(strings_mat()); parts.append(c)
    for sgn in (-1, 1):
        parts.append(beam("throat", (sgn * 0.06, -0.135, 0), (sgn * 0.012, -0.25, 0), 0.011, frame_m))
    g = beam("handle", (0, -0.25, 0), (0, -0.52, 0), 0.016, grip_m); parts.append(g)
    for o in parts: o.parent = root
    return root

def make_racket(k, frame_col):
    face_m, frame_m = racket_mat(frame_col)
    grip_m = principled(f"grip{k}", lin((240, 240, 240)), rough=0.8)
    bpy.ops.object.empty_add(location=(0, 0, 0)); root = bpy.context.active_object; root.name = f"racket{k}"
    parts = []
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=2); fr_ = bpy.context.active_object       # aro
    fr_.scale = (0.132, 0.152, 0.017); fr_.data.materials.append(frame_m); smooth(fr_); parts.append(fr_)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=2); fc = bpy.context.active_object        # face furada
    fc.scale = (0.122, 0.142, 0.0192); fc.data.materials.append(face_m); parts.append(fc)
    for sgn in (-1, 1):                                                                                      # coração
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=1, depth=2); h = bpy.context.active_object
        h.scale = (0.012, 0.012, 0.045); h.location = (sgn * 0.03, -0.175, 0); h.rotation_euler = (math.pi / 2, 0, sgn * -0.55)
        h.data.materials.append(frame_m); smooth(h); parts.append(h)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1, depth=2); g = bpy.context.active_object        # cabo
    g.scale = (0.019, 0.019, 0.07); g.location = (0, -0.27, 0); g.rotation_euler = (math.pi / 2, 0, 0); g.data.materials.append(grip_m); smooth(g); parts.append(g)
    for o in parts: o.parent = root
    return root

FIGS, RACKETS = [], []
for k, col in enumerate(D["cols"]):
    shirt = principled(f"shirt{k}", lin(col), rough=0.75, sheen=0.4)
    P_ = dict(pelvis=sph("pelvis", 1, SHORTS), torso=cone("torso", 0.17, 0.2, shirt), chest=sph("chest", 1, shirt), neck=cone("neck", 0.055, 0.05, SKIN),
              head=sph("head", 1, SKIN), hair=sph("hair", 1, HAIR),
              thL=cone("thL", 0.095, 0.075, SHORTS), thR=cone("thR", 0.095, 0.075, SHORTS), lgL=cone("legL", 0.062, 0.042, SKIN), lgR=cone("legR", 0.062, 0.042, SKIN),
              knL=sph("knL", 0.062, SKIN), knR=sph("knR", 0.062, SKIN), soL=cone("sockL", 0.046, 0.044, SOCK), soR=cone("sockR", 0.046, 0.044, SOCK),
              shoeL=sph("shoeL", 1, SOLE), shoeR=sph("shoeR", 1, SOLE),
              slR=cone("sleeveR", 0.07, 0.06, shirt), slL=cone("sleeveL", 0.07, 0.06, shirt),
              uaR=cone("uaR", 0.052, 0.042, SKIN), uaL=cone("uaL", 0.052, 0.042, SKIN), faR=cone("faR", 0.042, 0.032, SKIN), faL=cone("faL", 0.042, 0.032, SKIN),
              elR=sph("elR", 0.044, SKIN), elL=sph("elL", 0.044, SKIN), hdR=sph("hdR", 0.046, SKIN), hdL=sph("hdL", 0.046, SKIN),
              shoR=sph("shoR", 0.07, shirt), shoL=sph("shoL", 0.07, shirt))
    FIGS.append(P_)
    cols_ = [(230, 60, 50), (240, 240, 240), (40, 120, 230), (250, 200, 40)]
    RACKETS.append(make_racket(k, cols_[k % 4]) if SPORT == "padel" else make_tennis_racket(k, cols_[(k * 2) % 4]))
ball = sph("ball", 0.042, BALL)

# ------------------------------------------------------------------ pessoas realistas (MakeHuman), se existir humans.blend
# As articulações do nosso rig conduzem o esqueleto: cada osso aponta (Damped Track) para a articulação seguinte.
HUMANS = []
HB = os.environ.get("PROTO_HUMANS", "")
if HB and os.path.exists(HB):
    gender = D.get("gender", "m")
    with bpy.data.libraries.load(HB, link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c.startswith("H_" + gender)][:len(D["cols"])]
    J0 = FR[0]["players"]
    for k, colh in enumerate(dst.collections):
        sc.collection.children.link(colh)
        arm = next(o for o in colh.objects if o.type == "ARMATURE")
        bpy.ops.object.empty_add(location=(0, 0, 0)); root = bpy.context.active_object; root.name = f"hroot{k}"
        arm.parent = root
        EMP = {}
        def emp(nm_):
            if nm_ not in EMP:
                bpy.ops.object.empty_add(location=(0, 0, 0)); e_ = bpy.context.active_object; e_.name = f"j{k}_{nm_}"; EMP[nm_] = e_
            return EMP[nm_]
        def side(n_):
            l_ = n_.lower()
            if l_.endswith((".l", "_l", ".left")) or "_l_" in l_ or l_.endswith("l") and l_[-2:-1] in "._": return "L"
            if l_.endswith((".r", "_r", ".right")) or "_r_" in l_: return "R"
            return ""
        thighs = []
        for pb in arm.pose.bones:
            n_ = pb.name.lower(); sd = side(pb.name); tgt = None
            if "twist" in n_ or "finger" in n_ or "thumb" in n_ or "index" in n_ or "pinky" in n_ or "ring" in n_ or "middle" in n_: continue
            if ("upperarm" in n_ or "upper_arm" in n_) and sd: tgt = "el" + sd
            elif ("lowerarm" in n_ or "forearm" in n_) and sd: tgt = "hand" + sd
            elif ("upperleg" in n_ or "thigh" in n_) and sd: tgt = "knee" + sd; thighs.append(pb)
            elif ("lowerleg" in n_ or "calf" in n_ or "shin" in n_) and sd: tgt = "ank" + sd
            elif n_.startswith("foot") and sd: tgt = "toe" + sd
            elif n_.startswith("spine"): tgt = "neck"
            elif n_.startswith("neck"): tgt = "head"
            if tgt:
                c_ = pb.constraints.new("DAMPED_TRACK"); c_.target = emp(tgt); c_.track_axis = "TRACK_Y"
        # medidas em repouso: altura da anca do MakeHuman vs. a do nosso rig
        bpy.context.view_layer.update()
        hips = [arm.matrix_world @ pb.bone.head_local for pb in thighs] or [Vector((0, 0, 0.95))]
        mh_hip = sum(hips, Vector()) / len(hips)
        ours_z = max((fr_["players"][k]["hipL"][2] + fr_["players"][k]["hipR"][2]) / 2 for fr_ in FR)
        sk = max(0.85, min(1.15, ours_z / max(0.5, mh_hip.z)))
        # roupa lisa, com as cores do jogador/equipa (sem padrões nem estampados)
        team = lin(D["cols"][k]); dark = lin((24, 28, 36)) if sum(D["cols"][k]) > 380 else lin((236, 236, 232))
        for o in colh.objects:
            role = o.get("b100_role", "")
            if role not in ("top", "shorts") or o.type != "MESH": continue
            m_ = principled(f"{role}{k}", team if role == "top" else dark, rough=0.8, sheen=0.5)
            o.data.materials.clear(); o.data.materials.append(m_)
        # dedos da mão da raquete fechados no cabo
        for pb in arm.pose.bones:
            n_ = pb.name
            if n_.endswith("_r") and n_.split("_")[0] in ("index", "middle", "ring", "pinky"):
                pb.rotation_mode = "XYZ"; pb.rotation_euler = (0, 0, 1.25 if n_.split("_")[1] == "01" else 1.35)
            if n_ == "thumb_02_r" or n_ == "thumb_03_r":
                pb.rotation_mode = "XYZ"; pb.rotation_euler = (0, 0, 0.6)
        HUMANS.append(dict(root=root, arm=arm, emp=EMP, hip=mh_hip, sc=sk, hand=arm.pose.bones.get("hand_r")))
        print("pessoa", k, colh.name, "ossos com alvo:", len([1 for pb in arm.pose.bones if pb.constraints]), "escala", round(sk, 3))
    for P_ in FIGS[:len(HUMANS)]:
        for o in P_.values(): o.hide_render = True; o.hide_viewport = True

def pose_human(h, J):
    V = lambda k_: Vector(J[k_])
    for nm_, e_ in h["emp"].items(): e_.location = V(nm_)
    fh = V("fh"); yaw = math.atan2(fh.y, fh.x) + math.pi / 2
    R = Matrix.Rotation(yaw, 4, "Z")
    root = h["root"]; root.rotation_mode = "XYZ"; root.rotation_euler = (0, 0, yaw); root.scale = (h["sc"],) * 3
    hipmid = (V("hipL") + V("hipR")) / 2
    root.location = hipmid - (R @ (h["hip"] * h["sc"]))

def pose(P_, rk, J):
    V = lambda k_: Vector(J[k_]); f, s_, fh, shs = V("f"), V("s"), V("fh"), V("sh"); z = Vector((0, 0, 1))
    P, C = V("P"), V("C")
    oriented(P_["pelvis"], P + Vector((0, 0, 0.02)), shs, fh, z, (0.19, 0.13, 0.13))
    limb(P_["torso"], P + Vector((0, 0, 0.06)), C, 0.17); P_["torso"].scale = (0.17, 0.17, P_["torso"].scale[2])
    up = (C - P).normalized()
    oriented(P_["chest"], C - up * 0.06, s_, f, z, (0.21, 0.125, 0.17))
    limb(P_["neck"], V("neck") - Vector((0, 0, 0.04)), V("head") - Vector((0, 0, 0.09)), 0.055)
    oriented(P_["head"], V("head"), s_, f, z, (0.098, 0.11, 0.122))
    oriented(P_["hair"], V("head") + Vector((0, 0, 0.025)) - f * 0.012, s_, f, z, (0.103, 0.112, 0.105))
    for sd, hip, kn, an, toe in (("L", "hipL", "kneeL", "ankL", "toeL"), ("R", "hipR", "kneeR", "ankR", "toeR")):
        h_, k_, a_, t_ = V(hip), V(kn), V(an), V(toe)
        limb(P_["th" + sd], h_, k_, 0.095); limb(P_["lg" + sd], k_, a_ - (a_ - k_).normalized() * 0.08, 0.062)
        P_["kn" + sd].location = k_
        limb(P_["so" + sd], a_ - (a_ - k_).normalized() * 0.1, a_, 0.046)
        fwd = (t_ - a_); fwd.z = 0; fwd = fwd.normalized() if fwd.length > 1e-4 else fh
        side = fwd.cross(z)
        oriented(P_["shoe" + sd], (a_ + t_) / 2 + Vector((0, 0, -0.005)), side, fwd, z, (0.055, 0.15, 0.045))
    for sd in ("R", "L"):
        sh_, el, hd = V("sh" + sd), V("el" + sd), V("hand" + sd)
        limb(P_["ua" + sd], sh_, el, 0.052); limb(P_["sl" + sd], sh_, sh_ + (el - sh_) * 0.42, 0.07)
        limb(P_["fa" + sd], el, hd, 0.042); P_["el" + sd].location = el; P_["hd" + sd].location = hd; P_["sho" + sd].location = sh_
    rd, rn = V("rd"), V("rn"); xax = rd.cross(rn)
    oriented(rk, V("rc"), xax, rd, rn, (1, 1, 1))

# ------------------------------------------------------------------ terra batida: marcas da bola e pó
if SURF == "clay":
    MARK = principled("mark", lin((150, 70, 40)), rough=0.95)
    DUST = mixmat("dust", {"Base Color": (*lin((214, 150, 110)), 1), "Roughness": 1.0}, 0.18)
    import random as _r; rr = _r.Random(9)
    for (fb, x, y) in D.get("bounces", []):
        m_ = sph("mark", 1, MARK, 16); m_.location = (x, y, 0.0)
        m_.scale = (0, 0, 0); m_.keyframe_insert("scale", frame=fb)
        m_.scale = (0.05, 0.11, 0.004); m_.keyframe_insert("scale", frame=fb + 1)
        for q in range(14):
            pz = sph("dust", 1, DUST, 12); an = rr.uniform(0, 2 * math.pi); sp_ = rr.uniform(0.25, 0.7)
            pz.location = (x, y, 0.03); pz.scale = (0, 0, 0); pz.keyframe_insert("location", frame=fb); pz.keyframe_insert("scale", frame=fb)
            pz.scale = (0.05, 0.05, 0.05); pz.keyframe_insert("scale", frame=fb + 2)
            pz.location = (x + math.cos(an) * sp_, y + math.sin(an) * sp_, rr.uniform(0.15, 0.45)); pz.keyframe_insert("location", frame=fb + 16)
            pz.scale = (0.3, 0.3, 0.2); pz.keyframe_insert("scale", frame=fb + 12)
            pz.scale = (0, 0, 0); pz.keyframe_insert("scale", frame=fb + 26)

# ------------------------------------------------------------------ câmara
bpy.ops.object.camera_add(); cam = bpy.context.active_object; sc.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24.0
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = float(os.environ.get("PROTO_FSTOP", "2.4"))

animated = [ball, cam] + [o for P_ in FIGS for o in P_.values()] + RACKETS + [h["root"] for h in HUMANS] + [e_ for h in HUMANS for e_ in h["emp"].values()]
for f in keys:
    fr = FR[f]; n = f + 1
    pos, tgt = Vector(fr["cam"]), Vector(fr["tgt"])
    cam.location = pos; cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = (tgt - pos).normalized().to_track_quat("-Z", "Y")
    cam.data.lens = 12.0 / math.tan(math.radians(fr["fov"]) / 2); cam.data.dof.focus_distance = fr["focus"]
    cam.keyframe_insert("location", frame=n); cam.keyframe_insert("rotation_quaternion", frame=n)
    cam.data.keyframe_insert("lens", frame=n); cam.data.dof.keyframe_insert("focus_distance", frame=n)
    ball.location = Vector(fr["ball"]); ball.keyframe_insert("location", frame=n)
    for P_, rk, J in zip(FIGS, RACKETS, fr["players"]):
        pose(P_, rk, J)
        for o in list(P_.values()) + [rk]:
            o.rotation_mode = "QUATERNION"
            o.keyframe_insert("location", frame=n); o.keyframe_insert("rotation_quaternion", frame=n); o.keyframe_insert("scale", frame=n)
    for h, rk, J in zip(HUMANS, RACKETS, fr["players"]):
        pose_human(h, J)
        # raquete presa à mão do esqueleto (palma), com a mesma orientação do nosso rig
        bpy.context.view_layer.update()
        hb = h["hand"]
        if hb:
            Mw = h["arm"].matrix_world
            palm = Mw @ (hb.head + (hb.tail - hb.head) * 0.75)
            rk.location = rk.location + (palm - Vector(J["handR"]))
            rk.keyframe_insert("location", frame=n)
        for o in [h["root"]] + list(h["emp"].values()):
            o.keyframe_insert("location", frame=n)
        h["root"].keyframe_insert("rotation_euler", frame=n); h["root"].keyframe_insert("scale", frame=n)
# câmara: sem interpolação (há cortes entre planos); resto linear (desfoque de movimento correto)
for o in animated:
    for owner in (o, getattr(o, "data", None)):
        ad = getattr(owner, "animation_data", None)
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT" if o is cam else "LINEAR"
dad = cam.data.dof
for owner in (cam.data,):
    ad = owner.animation_data
    if ad and ad.action:
        for fc in ad.action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = "CONSTANT"

# ------------------------------------------------------------------ render
r = sc.render
r.engine = "CYCLES"; sc.cycles.device = "CPU"
sc.cycles.samples = int(os.environ.get("PROTO_SAMPLES", "20")); sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.04
sc.cycles.use_denoising = True
try: sc.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception: pass
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
sc.cycles.transmission_bounces = 2; sc.cycles.transparent_max_bounces = 16
r.use_motion_blur = True; r.motion_blur_shutter = 0.5
r.resolution_x, r.resolution_y, r.resolution_percentage = 1080, 1920, 100
r.fps = 30; r.use_persistent_data = True
r.image_settings.file_format = "JPEG"; r.image_settings.quality = 93
try: sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
except Exception:
    try: sc.view_settings.look = "None"
    except Exception: pass
sc.view_settings.exposure = float(os.environ.get("PROTO_EXPOSURE", "0"))
sc.frame_start, sc.frame_end = 1, N
for f in todo:
    sc.frame_set(f + 1)
    r.filepath = os.path.join(outdir, f"f_{f:04d}.jpg")
    bpy.ops.render.render(write_still=True)
    print("frame", f, "feito", flush=True)
