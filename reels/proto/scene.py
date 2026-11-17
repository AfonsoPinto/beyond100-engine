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
GLASS = mixmat("glass", {"Base Color": (0.8, 0.9, 1.0, 1), "Roughness": 0.03, "Metallic": 1.0}, 0.16)
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
# ------------------------------------------------------------------ pavilhão e campo
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.01)); o = bpy.context.active_object; o.scale = (60, 70, 1); o.data.materials.append(OUTF)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); o = bpy.context.active_object; o.scale = (2 * HW, 2 * HL, 1); o.data.materials.append(TURF)
W_ = 0.05
for (x0, y0, x1, y1) in ((-HW, -HL, HW, -HL), (-HW, HL, HW, HL), (-HW, -6.95, HW, -6.95), (-HW, 6.95, HW, 6.95), (0, -6.95, 0, 6.95),
                         (-HW, -HL, -HW, HL), (HW, -HL, HW, HL)):
    box("line", ((x0 + x1) / 2, (y0 + y1) / 2, 0.002), (max(W_, abs(x1 - x0)), max(W_, abs(y1 - y0)), 0.004), LINE)
# rede
box("net", (0, 0, NET / 2), (2 * HW, 0.02, NET), NETM)
box("netband", (0, 0, NET - 0.03), (2 * HW, 0.03, 0.06), WHITE)
for sx in (-HW - 0.05, HW + 0.05): box("post", (sx, 0, 0.5), (0.08, 0.08, 1.0), METAL)
# vidros e estrutura metálica
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

# bancadas em degraus, com pessoas sentadas (2 700 aprox.)
import bmesh, random
RND = random.Random(5)
SHIRTS = [(200, 196, 190), (232, 230, 226), (40, 44, 52), (196, 64, 60), (60, 92, 160), (230, 200, 70), (90, 120, 90), (150, 150, 160),
          (20, 22, 28), (210, 120, 70), (120, 70, 140), (240, 240, 240)]
SKINS = [(222, 184, 150), (196, 150, 112), (150, 104, 70), (100, 70, 50), (236, 200, 170)]
cbm = bmesh.new(); col_layer = cbm.loops.layers.color.new("col")
def person(pos, rot):
    c = lin(RND.choice(SHIRTS)); k = lin(RND.choice(SKINS)); hcol = lin(RND.choice([(30, 24, 20), (60, 44, 30), (120, 90, 60), (20, 20, 20), (200, 180, 140)]))
    lean = RND.uniform(-0.06, 0.06)
    M = Matrix.Translation(pos) @ Matrix.Rotation(rot, 4, "Z")
    parts = [("body", Matrix.Translation((lean, 0, 0.32)) @ Matrix.Diagonal((0.21, 0.13, 0.3, 1)), c),
             ("ico", Matrix.Translation((lean * 1.4, 0.02, 0.72)), k), ("ico2", Matrix.Translation((lean * 1.4, 0.05, 0.77)), hcol)]
    for kind, Lm, colr in parts:
        if kind == "body": r_ = bmesh.ops.create_icosphere(cbm, subdivisions=2, radius=1.0, matrix=M @ Lm)
        else: r_ = bmesh.ops.create_icosphere(cbm, subdivisions=1, radius=0.105 if kind == "ico" else 0.095, matrix=M @ Lm)
        fs = {f_ for v_ in r_["verts"] for f_ in v_.link_faces}
        for f_ in fs:
            for lp in f_.loops: lp[col_layer] = (*colr, 1.0)
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
            person(Vector((cx, cy, 0)) + R @ off, rot + math.pi)
stand(0, HL + 5.0, 34, 0); stand(0, -HL - 5.0, 34, math.pi)
stand(HW + 5.0, 0, 30, -math.pi / 2); stand(-HW - 5.0, 0, 30, math.pi / 2)
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
def board(y, rot):
    box("board", (0, y, 0.45), (2 * HW + 6, 0.12, 0.9), BOARD)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, y - math.copysign(0.065, y), 0.45)); pl = bpy.context.active_object
    pl.scale = (2 * HW + 6, 0.86, 1); pl.rotation_euler = (math.pi / 2, 0, rot); pl.data.materials.append(BM)
# ------------------------------------------------------------------ luz
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (0.003, 0.005, 0.009, 1); bg.inputs[1].default_value = 1.0
for x in (-4.5, 4.5):
    for y in (-9, 0, 9):
        bpy.ops.object.light_add(type="AREA", location=(x, y, 13)); L = bpy.context.active_object
        L.data.energy = float(os.environ.get("PROTO_LIGHT", "1300")); L.data.size = 3.5; L.data.color = (1.0, 0.97, 0.92)
for (x, y) in ((-16, 0), (16, 0), (0, -20), (0, 20)):              # luz nas bancadas
    bpy.ops.object.light_add(type="AREA", location=(x, y, 11)); L = bpy.context.active_object
    L.data.energy = 700; L.data.size = 8; L.data.color = (0.85, 0.9, 1.0)
    L.rotation_euler = (0, 0, 0)

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
    RACKETS.append(make_racket(k, [(230, 60, 50), (240, 240, 240), (40, 120, 230), (250, 200, 40)][k % 4]))
ball = sph("ball", 0.042, BALL)

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

# ------------------------------------------------------------------ câmara
bpy.ops.object.camera_add(); cam = bpy.context.active_object; sc.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24.0
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = float(os.environ.get("PROTO_FSTOP", "2.4"))

animated = [ball, cam] + [o for P_ in FIGS for o in P_.values()] + RACKETS
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
