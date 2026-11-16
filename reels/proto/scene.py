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

# público: células de cor aleatória (pessoas), um pouco iluminadas
CROWD = bpy.data.materials.new("crowd"); CROWD.use_nodes = True; nt = CROWD.node_tree
b = nt.nodes.get("Principled BSDF"); tc = nt.nodes.new("ShaderNodeTexCoord"); vo = nt.nodes.new("ShaderNodeTexVoronoi")
hs = nt.nodes.new("ShaderNodeHueSaturation"); vo.inputs["Scale"].default_value = 2.4
hs.inputs["Saturation"].default_value = 0.55; hs.inputs["Value"].default_value = 0.7
nt.links.new(tc.outputs["Object"], vo.inputs["Vector"]); nt.links.new(vo.outputs["Color"], hs.inputs["Color"])
nt.links.new(hs.outputs["Color"], b.inputs["Base Color"])
if "Emission Color" in b.inputs:
    nt.links.new(hs.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 0.12
b.inputs["Roughness"].default_value = 0.9

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

# bancadas (em degraus) com público
def stand(cx, cy, w, d, rot, rows=12):
    for r in range(rows):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0)); s_ = bpy.context.active_object
        s_.scale = (w, 0.8, 0.55 * (r + 1)); s_.data.materials.append(CROWD)
        off = Vector((0, r * 0.8, 0.275 * (r + 1)))
        s_.location = Vector((cx, cy, 0)) + Matrix.Rotation(rot, 3, "Z") @ off
        s_.rotation_euler = (0, 0, rot)
stand(0, HL + 5.0, 34, 0, 0); stand(0, -HL - 5.0, 34, 0, math.pi)
stand(HW + 5.0, 0, 30, 0, -math.pi / 2); stand(-HW - 5.0, 0, 30, 0, math.pi / 2)

# painéis com o nome do torneio
font = None
fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "fonts", "Inter-Black.otf")
if os.path.exists(fp): font = bpy.data.fonts.load(fp)
def board(y, rot):
    box("board", (0, y, 0.45), (2 * HW + 6, 0.12, 0.9), BOARD)
    box("board_acc", (0, y - math.copysign(0.065, y), 0.06), (2 * HW + 6, 0.01, 0.08), ACCM)
    for xo in (-5.5, 5.5):
        bpy.ops.object.text_add(location=(xo, y - math.copysign(0.07, y), 0.47)); t = bpy.context.active_object
        t.data.body = D["board"]; t.data.size = 0.42; t.data.align_x = "CENTER"; t.data.align_y = "CENTER"
        if font: t.data.font = font
        t.rotation_euler = (math.pi / 2, 0, rot); t.data.materials.append(TXT)
board(HL + 1.6, 0.0)          # ao fundo, virado para o campo (-Y)
board(-HL - 1.6, math.pi)     # do lado da câmara, virado para +Y

# ------------------------------------------------------------------ luz
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes.get("Background"); bg.inputs[0].default_value = (0.003, 0.005, 0.009, 1); bg.inputs[1].default_value = 1.0
for x in (-4.5, 4.5):
    for y in (-9, 0, 9):
        bpy.ops.object.light_add(type="AREA", location=(x, y, 13)); L = bpy.context.active_object
        L.data.energy = float(os.environ.get("PROTO_LIGHT", "14000")); L.data.size = 3.5; L.data.color = (1.0, 0.97, 0.92)
for (x, y) in ((-16, 0), (16, 0), (0, -20), (0, 20)):              # luz nas bancadas
    bpy.ops.object.light_add(type="AREA", location=(x, y, 11)); L = bpy.context.active_object
    L.data.energy = 9000; L.data.size = 8; L.data.color = (0.85, 0.9, 1.0)
    L.rotation_euler = (0, 0, 0)

# ------------------------------------------------------------------ figuras (manequins anónimos)
def cyl(name, r, m):
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=1, depth=2); o = bpy.context.active_object
    o.name = name; o.data.materials.append(m); smooth(o); o["r"] = r; return o
def sph(name, r, m):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=1); o = bpy.context.active_object
    o.name = name; o.scale = (r, r, r); o.data.materials.append(m); smooth(o); return o
def place(o, a, b_, r):
    a, b_ = Vector(a), Vector(b_); d = b_ - a; L = max(d.length, 1e-3)
    o.location = (a + b_) / 2; o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized()); o.scale = (r, r, L / 2)

FIGS = []
for k, col in enumerate(D["cols"]):
    shirt = principled(f"shirt{k}", lin(col), rough=0.75, sheen=0.4)
    P_ = dict(torso=cyl("torso", 0.16, shirt), pelvis=sph("pelvis", 0.15, SHORTS), chest=sph("chest", 0.17, shirt),
              head=sph("head", 0.115, SKIN), hair=sph("hair", 0.118, SHORTS),
              thL=cyl("thL", 0.075, SHORTS), thR=cyl("thR", 0.075, SHORTS), shL=cyl("shinL", 0.055, SKIN), shR_=cyl("shinR", 0.055, SKIN),
              knL=sph("kneeL", 0.06, SKIN), knR=sph("kneeR", 0.06, SKIN), ftL=box("shoeL", (0, 0, 0), (0.11, 0.27, 0.09), SHOE), ftR=box("shoeR", (0, 0, 0), (0.11, 0.27, 0.09), SHOE),
              uaR=cyl("uaR", 0.05, shirt), faR=cyl("faR", 0.042, SKIN), uaL=cyl("uaL", 0.05, shirt), faL=cyl("faL", 0.042, SKIN),
              elR=sph("elR", 0.048, SKIN), elL=sph("elL", 0.048, SKIN), hdR=sph("handR", 0.05, SKIN),
              grip=cyl("grip", 0.016, PADDLE), pad=cyl("paddle", 1.0, PADDLE))
    FIGS.append(P_)
ball = sph("ball", 0.042, BALL)

def pose(P_, J):
    V = lambda k: Vector(J[k]); face = J["face"]; fw = Vector((0, face, 0))
    hip, sh, hd = V("hip"), V("sh"), V("head")
    hipL, hipR = hip + Vector((-0.1, 0, -0.04)), hip + Vector((0.1, 0, -0.04))
    fl, fr = V("fl") + Vector((0, 0, 0.09)), V("fr") + Vector((0, 0, 0.09))
    knL = (hipL + fl) / 2 + fw * 0.09; knR = (hipR + fr) / 2 + fw * 0.09
    place(P_["torso"], hip + Vector((0, 0, 0.1)), sh - Vector((0, 0, 0.05)), 0.15)
    P_["pelvis"].location = hip; P_["pelvis"].scale = (0.17, 0.12, 0.13)
    P_["chest"].location = sh - Vector((0, 0, 0.1)); P_["chest"].scale = (0.21, 0.13, 0.17)
    P_["head"].location = hd; P_["hair"].location = hd + Vector((0, -0.01 * face, 0.03)); P_["hair"].scale = (0.118, 0.118, 0.095)
    place(P_["thL"], hipL, knL, 0.075); place(P_["thR"], hipR, knR, 0.075)
    place(P_["shL"], knL, fl, 0.055); place(P_["shR_"], knR, fr, 0.055)
    P_["knL"].location = knL; P_["knR"].location = knR
    P_["ftL"].location = V("fl") + Vector((0, 0.05 * face, 0.045)); P_["ftR"].location = V("fr") + Vector((0, 0.05 * face, 0.045))
    shR, shL, hand, rk = V("shR"), V("shL"), V("hand"), V("rk")
    elR = (shR + hand) / 2 + Vector((0.06 * face, -0.05 * face, -0.08))
    place(P_["uaR"], shR, elR, 0.05); place(P_["faR"], elR, hand, 0.042); P_["elR"].location = elR; P_["hdR"].location = hand
    handL = shL + Vector((0, 0.15, -0.42)); elL = (shL + handL) / 2 + Vector((-0.04 * face, 0.04 * face, 0))
    place(P_["uaL"], shL, elL, 0.05); place(P_["faL"], elL, handL, 0.042); P_["elL"].location = elL
    rd = (rk - hand); rd = rd.normalized() if rd.length > 1e-4 else Vector((0, 0, 1))
    place(P_["grip"], hand, hand + rd * 0.16, 0.016)
    n = rd.cross(Vector((0, 0, 1))); n = n.normalized() if n.length > 1e-3 else Vector((1, 0, 0))
    M = Matrix((rd.cross(n), rd, n)).transposed()                    # colunas: X, Y (cabo), Z (normal da pá)
    pad = P_["pad"]; pad.rotation_mode = "QUATERNION"; pad.rotation_quaternion = M.to_quaternion()
    pad.location = hand + rd * 0.33; pad.scale = (0.13, 0.15, 0.018)

# ------------------------------------------------------------------ câmara
bpy.ops.object.camera_add(); cam = bpy.context.active_object; sc.camera = cam
cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = 24.0
cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = float(os.environ.get("PROTO_FSTOP", "2.4"))

animated = [ball, cam] + [o for P_ in FIGS for o in P_.values()]
for f in keys:
    fr = FR[f]; n = f + 1
    pos, tgt = Vector(fr["cam"]), Vector(fr["tgt"])
    cam.location = pos; cam.rotation_mode = "QUATERNION"; cam.rotation_quaternion = (tgt - pos).normalized().to_track_quat("-Z", "Y")
    cam.data.lens = 12.0 / math.tan(math.radians(fr["fov"]) / 2); cam.data.dof.focus_distance = fr["focus"]
    cam.keyframe_insert("location", frame=n); cam.keyframe_insert("rotation_quaternion", frame=n)
    cam.data.keyframe_insert("lens", frame=n); cam.data.dof.keyframe_insert("focus_distance", frame=n)
    ball.location = Vector(fr["ball"]); ball.keyframe_insert("location", frame=n)
    for P_, J in zip(FIGS, fr["players"]):
        pose(P_, J)
        for o in P_.values():
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
sc.cycles.samples = int(os.environ.get("PROTO_SAMPLES", "32")); sc.cycles.use_adaptive_sampling = True
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
