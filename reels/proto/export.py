"""Exporta para o Blender, frame a frame, a mesma jogada do motor atual (câmara, bola, articulações dos jogadores)."""
import json, math, os, sys
cfg, out = sys.argv[1], sys.argv[2]
sys.argv = ["point", cfg]
from reels import point as P

from reels.proto.rig import Rig
ROFF = 0.29 if P.SPORT == "padel" else 0.40
RIGS = [Rig(pl, P.KP, P.ball_at, [th for o in P.PLAYERS if o.face != pl.face for th, _k in o.hits], ROFF) for pl in P.PLAYERS]
frames = []
for i, t in enumerate(P.TM):
    cam, _ = P.camera(t)
    fov = 2 * math.degrees(math.atan((P.H * P.S / 2) / cam.foc))
    bp = P.ball_at(P.KP, t)
    pls = []
    for pl, rg in zip(P.PLAYERS, RIGS):
        d = {k: list(v) for k, v in rg.joints(t).items()}
        d["face"] = pl.face
        pls.append(d)
    # foco: a bola, ou o jogador mais perto se a bola estiver longe do centro do plano
    fd = max(0.6, P.dot(P.sub(bp, cam.p), cam.f))
    frames.append(dict(t=t, cam=list(cam.p), tgt=list(P.add(cam.p, cam.f)), fov=fov, focus=fd, ball=list(bp), players=pls))
idx = lambda ts: next((i for i, x in enumerate(P.TM) if x >= ts), len(P.TM) - 1)
bounces = [(idx(tk) + 1, x, y) for (tk, x, y, z) in P.KP if z == 0 and abs(x) <= P.HW + 2 and abs(y) <= P.HL + 3]
json.dump(dict(frames=frames, cols=[list(pl.col) for pl in P.PLAYERS], HW=P.HW, HL=P.HL, NET=P.NET, sport=P.SPORT, SW=getattr(P, "SW", 4.115),
               surface=P.V.get("surface"), setting=P.V.get("setting"), rows=P.V.get("rows", 14), bounces=bounces,
               board=P.V["board"], stills=[idx(x) for x in ((1.45, 3.9, 5.3, 5.55, 5.75) if P.SPORT == 'padel' else (0.55, 1.25, 2.65, 3.88, 4.7))]), open(out, "w"))
# painel do torneio desenhado como imagem (a letra do Blender falhava letras)
from PIL import Image, ImageDraw
from reels import common as C
bw, bh = 4096, 240
im = Image.new("RGB", (bw, bh), (10, 18, 32)); d = ImageDraw.Draw(im)
d.rectangle([0, bh - 18, bw, bh], fill=C.ACC)
# alterna o nome do torneio com a nossa marca (publicidade própria; nunca logótipos de patrocinadores reais)
segs = [(P.V["board"].replace("·", "•"), C.CREAM), ("BEYOND 100  •  beyond100tennis.com", C.ACC)]
f = C.F("k", 112); x = 60; k = 0
while x < bw:
    txt, colr = segs[k % 2]; d.text((x, bh / 2 - 8), txt, font=f, fill=colr, anchor="lm"); x += d.textlength(txt, font=f) + 200; k += 1
im.save(os.path.join(os.path.dirname(out) or ".", "board.png"))
print(f"{len(frames)} frames exportados")
