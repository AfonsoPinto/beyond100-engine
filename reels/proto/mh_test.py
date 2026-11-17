"""Teste do MakeHuman (MPFB2) no Blender sem ecrã: instala os recursos, mostra a API e cria uma pessoa de exemplo."""
import bpy, sys, os, inspect, traceback, zipfile, glob, importlib
out = sys.argv[sys.argv.index("--") + 1]
os.makedirs(out, exist_ok=True)
mods = [m for m in sys.modules if m.endswith(".mpfb") or m == "mpfb"]
print("módulos mpfb:", mods)
base = None
for cand in ("bl_ext.user_default.mpfb", "mpfb"):
    try:
        importlib.import_module(cand); base = cand; break
    except Exception as e:
        print("import falhou", cand, e)
print("base:", base)
HS = importlib.import_module(base + ".services.humanservice").HumanService
LS = importlib.import_module(base + ".services.locationservice").LocationService
for n, f in inspect.getmembers(HS, predicate=inspect.isfunction):
    try: print("HumanService.%s%s" % (n, inspect.signature(f)))
    except Exception: print("HumanService." + n)
for n in ("get_user_data", "get_mpfb_data", "get_user_home"):
    if hasattr(LS, n):
        try: print("LocationService.%s ->" % n, getattr(LS, n)())
        except Exception as e: print(n, e)
ud = LS.get_user_data()
for z in glob.glob(os.path.join(os.getcwd(), "mh_assets", "*.zip")):
    print("a instalar", z)
    with zipfile.ZipFile(z) as zz: zz.extractall(ud)
for d in sorted(os.listdir(ud)): print("user data:", d, len(os.listdir(os.path.join(ud, d))) if os.path.isdir(os.path.join(ud, d)) else "")
for kind in ("clothes", "skins", "hair", "eyes", "eyebrows"):
    p = os.path.join(ud, kind)
    if os.path.isdir(p): print(kind, ":", sorted(os.listdir(p))[:60])
bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    bm = HS.create_human()
    print("criada:", bm, bm.name if bm else None)
except Exception:
    traceback.print_exc()
