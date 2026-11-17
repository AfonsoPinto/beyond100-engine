"""Troca o som de um vídeo já feito (mesma jogada): python -m reels.proto.resound <config.json> <entrada.mp4> <saída.mp4>"""
import os, subprocess, sys
cfg, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
sys.argv = ["point", cfg]
from reels import point as P
mute = dst[:-4] + ".mute.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-an", "-c:v", "copy", mute], check=True)
print("ok" if P.soundtrack(mute, dst) else "falhou")
