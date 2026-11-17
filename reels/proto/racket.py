"""Raquetes com as medidas reais (sem marcas), para a cena do Blender.
Convenção: origem no centro da face, +Y para a ponta, Z = normal da face, cabo em -Y.
  tennis(k, cor) -> (raiz, GRIP)   68,5 cm, cabeça ~100 pol², aro com perfil, garganta aberta, cordas 16x19, cabo octogonal com fita
  padel(k, cor)  -> (raiz, GRIP)   45,5 cm, 38 mm de espessura, furos, aro de proteção, coração aberto, cabo com overgrip e cordão
GRIP = ponto (local) que fica no centro da palma."""
import math
import bpy, bmesh
from mathutils import Vector, Matrix


def _lin(c): return tuple((x / 255.0) ** 2.2 for x in c[:3])


def _mat(name, col, rough=0.4, metal=0.0, coat=0.0, sheen=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = coat
    if "Sheen Weight" in b.inputs: b.inputs["Sheen Weight"].default_value = sheen
    return m


def _carbon(name, col, accent):
    """carbono lacado: cor do modelo na metade de cima, preto em baixo, com tecido de carbono fino e verniz"""
    m = _mat(name, col, rough=0.28, coat=1.0); nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord"); sx = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sx.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = -0.05; mr.inputs["From Max"].default_value = 0.05
    nt.links.new(sx.outputs["Y"], mr.inputs["Value"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*_lin((18, 18, 22)), 1); mix.inputs["B"].default_value = (*col, 1)
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    # risca de cor de destaque a meio
    st = nt.nodes.new("ShaderNodeMapRange"); st.inputs["From Min"].default_value = -0.012; st.inputs["From Max"].default_value = 0.012
    st.inputs["To Min"].default_value = 1.0; st.inputs["To Max"].default_value = 0.0
    ab = nt.nodes.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"
    off = nt.nodes.new("ShaderNodeMath"); off.operation = "SUBTRACT"; off.inputs[1].default_value = -0.02
    nt.links.new(sx.outputs["Y"], off.inputs[0]); nt.links.new(off.outputs[0], ab.inputs[0]); nt.links.new(ab.outputs[0], st.inputs["Value"])
    mix2 = nt.nodes.new("ShaderNodeMix"); mix2.data_type = "RGBA"; mix2.inputs["B"].default_value = (*accent, 1)
    nt.links.new(st.outputs["Result"], mix2.inputs["Factor"]); nt.links.new(mix.outputs["Result"], mix2.inputs["A"])
    nt.links.new(mix2.outputs["Result"], b.inputs["Base Color"])
    ck = nt.nodes.new("ShaderNodeTexChecker"); ck.inputs["Scale"].default_value = 260.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.05
    nt.links.new(tc.outputs["Object"], ck.inputs["Vector"]); nt.links.new(ck.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def _grip_mat(name, col):
    """fita do cabo: borracha com espiral em relevo"""
    m = _mat(name, col, rough=0.75, sheen=0.2); nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord"); wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "DIAGONAL"
    wv.inputs["Scale"].default_value = 30.0
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"]); nt.links.new(wv.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def _obj(name, bm, mat, parent, smooth=True, subsurf=0):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); me.materials.append(mat); o.parent = parent
    if subsurf:
        md = o.modifiers.new("s", "SUBSURF"); md.levels = subsurf; md.render_levels = subsurf
    return o


def _profile(w, h, n=12, p=4.0):
    """secção arredondada (superelipse) com largura w (no plano) e altura h (em z)"""
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n; c, s = math.cos(a), math.sin(a)
        out.append((w / 2 * math.copysign(abs(c) ** (2 / p), c), h / 2 * math.copysign(abs(s) ** (2 / p), s)))
    return out


def _sweep(bm, path, prof, closed=False, ups=None):
    """varre a secção ao longo do caminho (pontos no plano XY; o eixo z da secção fica em Z)"""
    rings = []; n = len(path)
    for i, p in enumerate(path):
        a = path[(i - 1) % n] if (closed or i > 0) else path[i]; b = path[(i + 1) % n] if (closed or i < n - 1) else path[i]
        t = (Vector(b) - Vector(a)); t.z = 0; t.normalize()
        nrm = Vector((t.y, -t.x, 0))                          # normal no plano (para fora num caminho anti-horário)
        rings.append([bm.verts.new(Vector(p) + nrm * u + Vector((0, 0, v))) for (u, v) in prof])
    m = len(prof)
    for i in range(n if closed else n - 1):
        r0, r1 = rings[i], rings[(i + 1) % n]
        for j in range(m):
            bm.faces.new((r0[j], r0[(j + 1) % m], r1[(j + 1) % m], r1[j]))
    if not closed:
        bm.faces.new(list(reversed(rings[0]))); bm.faces.new(rings[-1])
    return rings


def _ellipse(a, b, n, y0=0.0, squash=0.0):
    """oval da cabeça (um pouco mais largo em cima, como as raquetes reais)"""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = a * math.cos(t) * (1 + squash * math.sin(t)); y = y0 + b * math.sin(t)
        pts.append((x, y, 0))
    return pts


def tennis(k, col, accent=(217, 242, 61), string_col=(236, 232, 214)):
    col, accent = _lin(col), _lin(accent)
    root = bpy.data.objects.new(f"racket{k}", None); bpy.context.collection.objects.link(root)
    frame_m = _carbon(f"tframe{k}", col, accent)
    # cabeça: oval exterior ~25,5 x 33 cm (≈100 pol² de cordas), aro 17 mm (plano) x 24 mm (espessura)
    A, B = 0.1195, 0.1555
    bm = bmesh.new(); _sweep(bm, _ellipse(A, B, 120, 0.0, 0.06), _profile(0.017, 0.024, 14, 3.0), closed=True)
    _obj("tframe", bm, frame_m, root)
    # proteção da ponta (borracha preta) no terço de cima
    bm = bmesh.new(); top = [p for p in _ellipse(A + 0.0035, B + 0.0035, 120, 0.0, 0.06) if p[1] > 0.10]
    top.sort(key=lambda p: math.atan2(p[1], p[0]))
    _sweep(bm, top, _profile(0.006, 0.02, 10, 3.0)); _obj("bumper", bm, _mat(f"bump{k}", _lin((22, 22, 24)), 0.6), root)
    # garganta aberta: dois braços da cabeça até ao veio, e a ponte (yoke) que fecha a face em baixo
    bm = bmesh.new()
    for sgn in (-1, 1):
        x0 = sgn * 0.085; y0 = -0.105
        path = [(x0 + sgn * 0.002 * (1 - t) - sgn * (0.085 - 0.012) * t ** 1.3, y0 - (0.165 - 0.0) * t, 0) for t in [i / 24 for i in range(25)]]
        _sweep(bm, path, _profile(0.016, 0.022, 12, 3.0))
    _sweep(bm, [(-0.06 + 0.12 * i / 16, -0.152 - 0.012 * math.sin(math.pi * i / 16), 0) for i in range(17)], _profile(0.012, 0.02, 12, 3.0))
    _obj("throat", bm, frame_m, root)
    # veio e cabo (octogonal, ~27 mm entre faces), tampa na ponta
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.0115, radius2=0.0125, depth=0.06,
                                             matrix=Matrix.Translation((0, -0.29, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    _obj("shaft", bm, frame_m, root)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.0145, radius2=0.0145, depth=0.20,
                                             matrix=Matrix.Translation((0, -0.42, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X") @ Matrix.Rotation(math.pi / 8, 4, "Z"))
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.1], offset=0.002, segments=2, affect="EDGES")
    _obj("grip", bm, _grip_mat(f"tgrip{k}", _lin((240, 240, 236) if k % 2 == 0 else (24, 24, 28))), root)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.0175, radius2=0.016, depth=0.012,
                                             matrix=Matrix.Translation((0, -0.524, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    _obj("buttcap", bm, frame_m, root)
    # cordas 16 x 19 (cordas verticais e horizontais entrelaçadas)
    smat = _mat(f"strings{k}", _lin(string_col), rough=0.45, sheen=0.3)
    bm = bmesh.new(); ai, bi = A - 0.009, B - 0.009
    def inside_x(y):   # meia-largura interior para um y
        if abs(y) >= bi: return 0
        return ai * math.sqrt(1 - (y / bi) ** 2) * (1 + 0.06 * (y / bi))
    for i in range(16):
        x = -ai * 0.94 + 2 * ai * 0.94 * i / 15
        if abs(x) >= ai: continue
        h = bi * math.sqrt(max(0, 1 - (x / ai) ** 2))
        pts = [(x, -h + 2 * h * j / 18, (0.0007 if (i + j) % 2 else -0.0007)) for j in range(19)]
        _sweep(bm, pts, _profile(0.0013, 0.0013, 6, 2.0))
    for j in range(19):
        y = -bi * 0.93 + 2 * bi * 0.93 * j / 18
        w = inside_x(y)
        if w < 0.01: continue
        pts = [(-w + 2 * w * i / 15, y, (0.0007 if (i + j + 1) % 2 else -0.0007)) for i in range(16)]
        _sweep(bm, pts, _profile(0.0013, 0.0013, 6, 2.0))
    _obj("strings", bm, smat, root, smooth=False)
    return root, Vector((0, -0.43, 0))


def padel(k, col, accent=(217, 242, 61)):
    col, accent = _lin(col), _lin(accent)
    root = bpy.data.objects.new(f"racket{k}", None); bpy.context.collection.objects.link(root)
    face_m = _carbon(f"pface{k}", col, accent)
    # face: forma redonda/lágrima 26 x 29 cm, 38 mm de espessura, arestas boleadas
    W2, H2 = 0.13, 0.145
    out = []
    for i in range(96):
        t = 2 * math.pi * i / 96; c, s = math.cos(t), math.sin(t)
        x = W2 * math.copysign(abs(c) ** 0.85, c) * (1 + 0.07 * s); y = H2 * math.copysign(abs(s) ** 0.9, s)
        out.append((x, y))
    bm = bmesh.new(); vs = [bm.verts.new((x, y, -0.019)) for x, y in out]; f = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[f]); top = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=top, vec=(0, 0, 0.038)); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-4], offset=0.007, segments=3, affect="EDGES")
    face = _obj("pface", bm, face_m, root)
    # furos (13 mm) em padrão hexagonal, cortados com booleana
    hb = bmesh.new(); n = 0
    for r in range(-9, 10):
        for c in range(-8, 9):
            x = c * 0.024 + (0.012 if r % 2 else 0); y = r * 0.0205 + 0.006
            ex = (abs(x) / (W2 - 0.034)) ** 2 + (abs(y - 0.005) / (H2 - 0.034)) ** 2
            if ex < 1.0 and not (abs(x) < 0.03 and y < -0.09):
                bmesh.ops.create_cone(hb, cap_ends=True, segments=14, radius1=0.0065, radius2=0.0065, depth=0.06, matrix=Matrix.Translation((x, y, 0))); n += 1
    hme = bpy.data.meshes.new("holes"); hb.to_mesh(hme); hb.free()
    holes = bpy.data.objects.new("holes", hme); bpy.context.collection.objects.link(holes); holes.parent = root
    holes.hide_render = True; holes.hide_viewport = True
    bo = face.modifiers.new("furos", "BOOLEAN"); bo.object = holes; bo.operation = "DIFFERENCE"; bo.solver = "EXACT"
    # aro de proteção (borracha) à volta da cabeça
    bm = bmesh.new(); guard = [(x * 1.02, y * 1.02, 0) for (x, y) in out if y > -0.06]
    guard.sort(key=lambda p: math.atan2(p[1], p[0]))
    _sweep(bm, guard, _profile(0.008, 0.042, 10, 3.0)); _obj("pguard", bm, _mat(f"pguard{k}", _lin((20, 20, 22)), 0.55), root)
    # coração aberto: dois braços da face ao cabo
    bm = bmesh.new()
    for sgn in (-1, 1):
        path = [(sgn * (0.07 - 0.052 * t ** 1.2), -0.125 - 0.085 * t, 0) for t in [i / 16 for i in range(17)]]
        _sweep(bm, path, _profile(0.022, 0.036, 12, 3.0))
    _obj("pheart", bm, face_m, root)
    # cabo com overgrip branco, tampa e cordão de pulso
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.0185, radius2=0.017, depth=0.115,
                                             matrix=Matrix.Translation((0, -0.262, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    _obj("pgrip", bm, _grip_mat(f"pgrip{k}", _lin((244, 244, 240))), root)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.021, radius2=0.02, depth=0.014,
                                             matrix=Matrix.Translation((0, -0.324, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    _obj("pcap", bm, face_m, root)
    bm = bmesh.new(); loop = [(0.004 * math.sin(2 * math.pi * i / 24), -0.33 - 0.06 * (1 - math.cos(2 * math.pi * i / 24)) / 2, 0.012 * math.sin(2 * math.pi * i / 24)) for i in range(24)]
    _sweep(bm, loop, _profile(0.004, 0.004, 6, 2.0), closed=True); _obj("pcord", bm, _mat(f"pcord{k}", _lin((30, 30, 34)), 0.7), root)
    return root, Vector((0, -0.255, 0))
