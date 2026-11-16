"""Cores, letra e utilitários partilhados pelos Reels."""
import os
from PIL import ImageFont
FD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts") + os.sep
_F = {}
def F(w, s):
    k = (w, s)
    if k not in _F:
        _F[k] = ImageFont.truetype(FD + {"b": "Inter-Bold.otf", "x": "Inter-ExtraBold.otf", "k": "Inter-Black.otf", "m": "Inter-Medium.otf", "d": "InterDisplay-Black.otf"}[w], s)
    return _F[k]
BG, DEEP, TURF, TURF2, LINE, GLASS, ACC, CREAM, SOFT, RED = (12, 46, 74), (8, 34, 58), (24, 92, 160), (20, 80, 142), (235, 242, 250), (150, 200, 240), (217, 242, 61), (247, 242, 230), (169, 192, 214), (255, 154, 138)
def ease(t): t = max(0, min(1, t)); return 1 - (1 - t) ** 3
def seg(t, a, b): return ease((t - a) / (b - a))
def encoder(path, W, H, FPS):
    import subprocess
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-use_editlist", "0", "-movflags", "+faststart", path], stdin=subprocess.PIPE)
