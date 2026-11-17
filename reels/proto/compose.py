"""Junta os frames do Blender com os textos (HUD), o cartão final e o som do motor atual."""
import os, sys
cfg, fdir, out, mode = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
sys.argv = ["point", cfg]
from PIL import Image, ImageDraw
from reels import point as P, common as C

N = len(P.TM)
def deco(i):
    im = Image.open(os.path.join(fdir, f"f_{i:04d}.jpg")).convert("RGB")
    t = P.TM[i]; slow = any(a <= t < b and r < 0.4 for a, b, r in P.SLOW)
    P.hud(ImageDraw.Draw(im, "RGBA"), t, max(1, i / P.FPS), slow)
    return im
if mode == "stills":
    os.makedirs(out, exist_ok=True)
    import shutil
    for fn in sorted(os.listdir(fdir)):
        if fn.startswith("f_"):
            i = int(fn[2:6]); deco(i).save(os.path.join(out, f"still_{i:04d}.jpg"), quality=90)
        else:
            shutil.copy(os.path.join(fdir, fn), os.path.join(out, "close_" + fn))
    sys.exit(0)
tmp = out[:-4] + ".part.mp4"; p = C.encoder(tmp, P.W, P.H, P.FPS)
last = None
for i in range(int(P.TOTAL * P.FPS)):
    if i < N:
        last = Image.open(os.path.join(fdir, f"f_{i:04d}.jpg")).convert("RGB"); im = deco(i)
    else:
        im = P.outro(last, (i - N) / P.FPS / P.OUT)
    k = P.seg(i / P.FPS, P.TOTAL - 0.35, P.TOTAL)
    if k > 0: im = Image.blend(im, Image.new("RGB", (P.W, P.H), P.BG), k)
    p.stdin.write(im.tobytes())
p.stdin.close(); p.wait()
if not P.soundtrack(tmp, out): os.replace(tmp, out)
print("vídeo:", out)
