"""Exporta para o Blender, frame a frame, a mesma jogada do motor atual (câmara, bola, articulações dos jogadores)."""
import json, math, sys
cfg, out = sys.argv[1], sys.argv[2]
sys.argv = ["point", cfg]
from reels import point as P

from reels.proto.rig import Rig
RIGS = [Rig(pl, P.KP, P.ball_at, [th for o in P.PLAYERS if o.face != pl.face for th, _k in o.hits]) for pl in P.PLAYERS]
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
json.dump(dict(frames=frames, cols=[list(pl.col) for pl in P.PLAYERS], HW=P.HW, HL=P.HL, NET=P.NET, sport=P.SPORT,
               board=P.V["board"], stills=[idx(x) for x in (1.45, 3.9, 5.3, 5.55, 5.75)]), open(out, "w"))
print(f"{len(frames)} frames exportados")
