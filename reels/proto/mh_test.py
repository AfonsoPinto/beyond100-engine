"""Teste do MakeHuman (MPFB2): pessoas de exemplo com várias roupas, lado a lado, para escolher."""
import bpy, sys, os, traceback, zipfile, glob, importlib, json, math
out = sys.argv[sys.argv.index("--") + 1]; os.makedirs(out, exist_ok=True)
base = "bl_ext.user_default.mpfb"
HS = importlib.import_module(base + ".services.humanservice").HumanService
LS = importlib.import_module(base + ".services.locationservice").LocationService
ud = LS.get_user_data()
for z in glob.glob(os.path.join(os.getcwd(), "mh_assets", "*.zip")):
    with zipfile.ZipFile(z) as zz: zz.extractall(ud)
print("info por omissão:", json.dumps(HS._create_default_human_info_dict(), default=str)[:1500])
def p(kind, name, ext="mhclo"):
    c = glob.glob(os.path.join(ud, kind, name, "*." + ext)); return c[0] if c else None
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
LOOKS = [
    ("m", "young_caucasian_male", "short02", ["namuhekam_male_polo_shirt", "male_casualsuit03", "shoes02"]),
    ("m", "young_african_male", "short04", ["toigo_basic_tucked_t-shirt", "male_casualsuit05", "shoes05"]),
    ("m", "young_asian_male", "short01", ["elvs_crude_t-shirt_male", "male_casualsuit01", "shoes01"]),
    ("f", "young_caucasian_female", "ponytail01", ["female_sportsuit01", "shoes02"]),
    ("f", "young_african_female", "bob02", ["toigo_keyhole_tank_top", "female_casualsuit02", "shoes05"]),
    ("m", "young_caucasian_male2", "short03", ["male_casualsuit04", "shoes06"]),
]
for i, (g, skin, hair, clothes) in enumerate(LOOKS):
    try:
        md = None
        try:
            md = HS._create_default_human_info_dict().get("phenotype") or None
        except Exception: pass
        bm = HS.create_human()
        # fenótipo de atleta (se a chave existir)
        for k, v in (("gender", 1.0 if g == "m" else 0.0), ("muscle", 0.72), ("weight", 0.45), ("height", 0.62 if g == "m" else 0.55), ("age", 0.45)):
            try:
                ts = importlib.import_module(base + ".services.targetservice").TargetService
                ts.set_macro_value(bm, k, v) if hasattr(ts, "set_macro_value") else None
            except Exception as e: print("macro", k, e)
        try:
            ts = importlib.import_module(base + ".services.targetservice").TargetService
            if hasattr(ts, "reapply_macro_details"): ts.reapply_macro_details(bm)
        except Exception as e: print("reapply", e)
        HS.set_character_skin(p("skins", skin, "mhmat"), bm)
        for kind, nm, t in (("eyes", "high-poly", "Eyes"), ("eyebrows", "eyebrow001", "Eyebrows"), ("eyelashes", "eyelashes01", "Eyelashes"), ("hair", hair, "Hair")):
            f = p(kind, nm)
            if f: HS.add_mhclo_asset(f, bm, asset_type=t)
            else: print("sem", kind, nm, os.listdir(os.path.join(ud, kind))[:5])
        for c in clothes:
            f = p("clothes", c)
            if f: HS.add_mhclo_asset(f, bm, asset_type="Clothes")
            else: print("sem roupa", c)
        bm.location.x = (i - (len(LOOKS) - 1) / 2) * 0.9
        print("feito", i, skin, clothes)
    except Exception:
        traceback.print_exc()
# luz e câmara de estúdio
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.2, 0.22, 0.26, 1)
bpy.ops.object.light_add(type="AREA", location=(2, -4, 4)); L = bpy.context.active_object; L.data.energy = 900; L.data.size = 4
L.rotation_euler = (math.radians(50), 0, math.radians(25))
bpy.ops.object.light_add(type="AREA", location=(-3, -2, 3)); L = bpy.context.active_object; L.data.energy = 400; L.data.size = 3
L.rotation_euler = (math.radians(60), 0, math.radians(-40))
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
bpy.ops.object.camera_add(location=(0, -7.5, 1.1), rotation=(math.radians(88), 0, 0)); sc.camera = bpy.context.active_object
sc.camera.data.lens = 40
sc.render.engine = "CYCLES"; sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 1800, 900
sc.render.filepath = os.path.join(out, "lineup.jpg"); sc.render.image_settings.file_format = "JPEG"
bpy.ops.render.render(write_still=True)
# lista de roupa com pernas curtas (para escolher calções)
for c in sorted(os.listdir(os.path.join(ud, "clothes"))): print("roupa:", c)
