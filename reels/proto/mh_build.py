"""Cria as personagens MakeHuman (MPFB2) para os Reels e grava-as num .blend (texturas incluídas).
Pessoas geradas (não são jogadores reais). Recursos: CC0 (MakeHuman) e CC BY (calções e sapatilhas, ver CREDITOS.md).
  blender -b -P reels/proto/mh_build.py -- humans.blend"""
import bpy, sys, os, glob, zipfile, importlib, json
out = sys.argv[sys.argv.index("--") + 1]
base = "bl_ext.user_default.mpfb"
HS = importlib.import_module(base + ".services.humanservice").HumanService
LS = importlib.import_module(base + ".services.locationservice").LocationService
ud = LS.get_user_data()
for z in glob.glob(os.path.join(os.getcwd(), "mh_assets", "*.zip")):
    with zipfile.ZipFile(z) as zz: zz.extractall(ud)
def p(kind, name, ext="mhclo"):
    c = glob.glob(os.path.join(ud, kind, name, "*." + ext)); return c[0] if c else None
rigdir = os.path.join(LS.get_mpfb_data(), "rigs", "standard"); rigs = sorted(os.listdir(rigdir)); print("rigs:", rigs)
names = [r[4:-5] for r in rigs if r.startswith("rig.") and r.endswith(".json")]
RIG = "game_engine" if "game_engine" in names else ("default" if "default" in names else names[0]); print("rig escolhido:", RIG)
bpy.ops.wm.read_factory_settings(use_empty=True)
MD = HS._create_default_human_info_dict()["phenotype"]
LOOKS = {
    "m": [("young_caucasian_male", "short02", "namuhekam_male_polo_shirt", "elvs_male_trouser_short_1"),
          ("young_african_male", "short04", "toigo_basic_tucked_t-shirt", "elvs_male_trouser_short_2"),
          ("young_asian_male", "short01", "elvs_crude_t-shirt_male", "elvs_male_trouser_short_1"),
          ("young_caucasian_male2", "short03", "toigo_basic_tucked_t-shirt", "elvs_male_trouser_short_2")],
    "f": [("young_caucasian_female", "ponytail01", "joepal_crude_t-shirt_female", "elvs_male_trouser_short_2"),
          ("young_african_female", "braid01", "joepal_crude_t-shirt_female", "elvs_male_trouser_short_2"),
          ("young_asian_female", "ponytail01", "joepal_crude_t-shirt_female", "elvs_male_trouser_short_2"),
          ("young_caucasian_female2", "long01", "joepal_crude_t-shirt_female", "elvs_male_trouser_short_2")],
}
info = {}
for g, looks in LOOKS.items():
    for i, (skin, hair, top, shorts) in enumerate(looks):
        nm = f"H_{g}{i}"
        md = json.loads(json.dumps(MD)); md.update(gender=1.0 if g == "m" else 0.0, muscle=0.75, weight=0.42, age=0.42, height=0.62 if g == "m" else 0.55)
        try: bm = HS.create_human(macro_detail_dict=md)
        except Exception as e: print("macro falhou", e); bm = HS.create_human()
        arm = HS.add_builtin_rig(bm, RIG)
        HS.set_character_skin(p("skins", skin, "mhmat"), bm)
        bm["b100_role"] = "body"
        for kind, a, t in (("eyes", "high-poly", "Eyes"), ("eyebrows", "eyebrow001", "Eyebrows"), ("eyelashes", "eyelashes01", "Eyelashes"), ("hair", hair, "Hair"),
                           ("clothes", top, "Clothes"), ("clothes", shorts, "Clothes"), ("clothes", "culturalibre_sneakers", "Clothes")):
            f = p(kind, a)
            if f:
                try:
                    ob = HS.add_mhclo_asset(f, bm, asset_type=t)
                    ob["b100_role"] = "top" if a == top else ("shorts" if a == shorts else ("shoes" if "sneakers" in a else kind))
                except Exception as e: print("falhou", a, e)
            else: print("sem", kind, a)
        col = bpy.data.collections.new(nm); bpy.context.scene.collection.children.link(col)
        objs = [arm] + list(arm.children_recursive)
        for o in objs:
            for c in list(o.users_collection): c.objects.unlink(o)
            col.objects.link(o)
        arm.name = nm
        bones = [b.name for b in arm.data.bones]
        info[nm] = dict(bones=bones, parents={b.name: (b.parent.name if b.parent else None) for b in arm.data.bones})
        print(nm, len(objs), "objetos;", len(bones), "ossos")
print("ossos", RIG, json.dumps(info["H_m0"]["parents"])[:4000])
try: bpy.ops.file.pack_all()
except Exception as e: print("pack", e)
bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out), compress=True)
print("gravado", out, os.path.getsize(out) // 1048576, "MB")
