"""Reel "Top 3 points" a partir do resumo oficial do torneio ("Newscut", Red Bull Content Pool) (19/11/2026, Afonso).

Escolha dos pontos SEM IA e sem ninguém ver o vídeo (regra "AI Prohibition" do RBCP): só medições de som e de cortes
de câmara, como um medidor de volume —
  1) cortes de câmara (ffmpeg, mudança de cena);
  2) pancadas na bola = picos curtos de energia nos agudos (2–6 kHz);
  3) reação do público = volume alto e prolongado logo a seguir.
  4) campo à vista = proporção da imagem com a cor do campo (a cor saturada mais comum do vídeo inteiro; nas
     entrevistas e nos planos fechados quase não aparece) — 19/11/2026: o 1.º exemplo apanhava entrevistas.
Um bom ponto = vários golpes seguidos dentro do MESMO plano, com o campo à vista, + grande reação no fim.
O corte nunca passa para o plano seguinte. Ficam os 3 melhores, de ~8 s cada.
Formato: vídeo horizontal ao centro, a mesma imagem desfocada em cima e em baixo; título, contador #3→#1, marca e
"© Red Bull Media House" dentro da zona segura do Instagram. Licença dos vídeos: "NEWS Use", 7 dias.

  python -m reels.rbcp_top3 <newscut.mp4> <saida.mp4> "<TORNEIO>"   (ex.: "DUBAI P1")"""
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

from reels import rbcp_video as rv

W, H = 1080, 1920
SR = 16000
HOP = 0.05                                                         # 50 ms por medição


def scene_cuts(src):
    out = subprocess.run(["ffmpeg", "-v", "info", "-i", src, "-an", "-vf", "scale=320:-2,select='gt(scene,0.32)',showinfo", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    ts = []
    for line in out.splitlines():
        if "pts_time:" in line:
            try:
                ts.append(float(line.split("pts_time:")[1].split()[0]))
            except ValueError:
                pass
    return [0.0] + ts


def court_track(src, fps=4):
    """Proporção de cada imagem (4 por segundo) com a cor do campo. Devolve (tempos, proporções)."""
    w, h = 160, 90
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-an", "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    if not n:
        return np.array([0.0]), np.array([1.0])
    a = np.frombuffer(raw[:n * w * h * 3], dtype=np.uint8).reshape(n, h, w, 3).astype(np.float32) / 255.0
    mx, mn = a.max(axis=3), a.min(axis=3)
    sat = (mx - mn) / (mx + 1e-6)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    hue = np.where(mx == r, ((g - b) / (mx - mn + 1e-6)) % 6, np.where(mx == g, (b - r) / (mx - mn + 1e-6) + 2, (r - g) / (mx - mn + 1e-6) + 4)) * 60
    strong = (sat > 0.35) & (mx > 0.25)
    bins = (hue // 10).astype(int) % 36
    hist = np.bincount(bins[strong].ravel(), minlength=36)
    c = int(hist.argmax())                                          # a cor do campo (azul, verde...) é a mais comum
    near = (np.abs(((bins - c + 18) % 36) - 18) <= 1) & (sat > 0.3) & (mx > 0.2)
    frac = near.reshape(n, -1).mean(axis=1)
    return np.arange(n) / fps, frac


def audio(src):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def features(x):
    n = int(SR * HOP)
    frames = len(x) // n
    x = x[:frames * n].reshape(frames, n)
    rms = np.sqrt((x ** 2).mean(axis=1) + 1e-12)
    spec = np.abs(np.fft.rfft(x * np.hanning(n), axis=1))
    freqs = np.fft.rfftfreq(n, 1 / SR)
    hi = spec[:, (freqs >= 2000) & (freqs <= 6000)].sum(axis=1)
    onset = np.maximum(0, np.diff(np.log(hi + 1e-6), prepend=np.log(hi[0] + 1e-6)))
    return rms, onset


def smooth(v, k):
    k = max(1, int(k))
    return np.convolve(v, np.ones(k) / k, mode="same")


def pick(src, n=3, clip=7.0, tail=1.6, min_court=0.22):
    """Os n melhores momentos (início, fim, nota), por ordem de nota crescente (#3 primeiro)."""
    cuts = scene_cuts(src)
    rms, onset = features(audio(src))
    ct, cf = court_track(src)
    dur = len(rms) * HOP
    loud = 20 * np.log10(smooth(rms, 1.5 / HOP) + 1e-9)            # volume em dB, janela de 1,5 s
    inst = 20 * np.log10(rms + 1e-9)
    med = np.median(onset)
    thr = max(np.percentile(onset, 90), med + 6 * np.median(np.abs(onset - med)))
    peak = (onset > thr) & (onset == np.maximum.reduce([np.roll(onset, k) for k in range(-3, 4)]))
    decay = inst - np.roll(inst, -2)                               # pancada = som curto (cai depressa); a voz não
    hits = np.where(peak & (decay > 4))[0] * HOP
    base = np.median(loud)

    def court(a, b):
        m = (ct >= a) & (ct <= b)
        return float(np.min(cf[m])) if m.any() else 0.0, float(np.median(cf[m])) if m.any() else 0.0

    cands = []
    for i in range(int(4 / HOP), len(loud) - int(1 / HOP)):
        if loud[i] < base + 4 or loud[i] != loud[max(0, i - int(1.5 / HOP)): i + int(1.5 / HOP)].max():
            continue
        t = i * HOP                                                # pico da reação do público
        before = [c for c in cuts if c <= t]
        after = [c for c in cuts if c > t]
        shot0 = before[-1] if before else 0.0
        shot1 = after[0] if after else dur
        start = max(shot0 + 0.1, t - clip)
        end = min(shot1 - 0.1, t + tail)                           # nunca entra no plano seguinte (entrevistas)
        if end - start < 4.5 or t - start < 3.0:
            continue
        lo, md = court(start, t)
        if md < min_court or lo < min_court * 0.6:                 # sem campo à vista: entrevista / plano fechado
            continue
        h = [x for x in hits if start <= x <= t]
        gaps = np.diff(h) if len(h) > 1 else np.array([])
        rally = int(((gaps > 0.45) & (gaps < 2.2)).sum())          # golpes com ritmo de troca de bolas
        if rally < 3:
            continue
        cands.append((float((loud[i] - base) * min(rally, 10) * (0.5 + md)), start, end))
    chosen = []
    for score, s, e in sorted(cands, reverse=True):
        if all(e < cs - 0.5 or s > ce + 0.5 for _, cs, ce in chosen):
            chosen.append((score, s, e))
        if len(chosen) == n:
            break
    print(f"Top 3: {len(cuts)} planos, {len(hits)} pancadas, {len(cands)} candidatos, cor do campo em {np.median(cf):.0%} das imagens (mediana).")
    return [(s, e, sc) for sc, s, e in sorted(chosen)]


def title_layer(tournament, rank):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    vt = (H - 608) // 2
    d.rounded_rectangle([40, vt - 190, W - 140, vt - 14], radius=26, fill=rv.DEEP + (215,))
    d.text((70, vt - 168), "TOP 3 POINTS", font=rv.f("InterDisplay-Black.otf", 80), fill=rv.CREAM)
    d.text((72, vt - 70), tournament, font=rv.f("Inter-ExtraBold.otf", 36), fill=rv.VOLT)
    d.text((W - 170, vt - 102), f"#{rank}", font=rv.f("InterDisplay-Black.otf", 150), fill=rv.VOLT, anchor="rm")
    return im


def segment(src, s, e, rank, tournament, out, kbps):
    title_layer(tournament, rank).save("_reel/t.png")
    rv.FINALS.clear(); rv.FINALS.update({"tournament": tournament, "tag": "TOP 3"})
    rv.brand_layer().save("_reel/brand.png")
    d = e - s
    fc = (f"[0:v]split[a][b];[a]scale=-2:{H},crop={W}:{H},boxblur=28:2,eq=brightness=-0.18[bg];"
          f"[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2[v0];[v0][1:v]overlay=0:0[v1];[v1][2:v]overlay=0:0,"
          f"fade=t=in:st=0:d=0.2,fade=t=out:st={d - 0.2:.2f}:d=0.2[v]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{s:.2f}", "-t", f"{d:.2f}", "-i", src,
                    "-loop", "1", "-t", f"{d:.2f}", "-i", "_reel/t.png", "-loop", "1", "-t", f"{d:.2f}", "-i", "_reel/brand.png",
                    "-filter_complex", fc, "-map", "[v]", "-map", "0:a",
                    "-af", f"afade=t=in:d=0.15,afade=t=out:st={d - 0.25:.2f}:d=0.25,aresample=48000",
                    "-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", "25",
                    "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.5)}k", "-bufsize", f"{kbps * 2}k",
                    "-c:a", "aac", "-b:a", "192k", "-ac", "2", out], check=True)


def end_clip(out, kbps, d=2.4):
    rv.end_layer().save("_reel/end.png")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", str(d), "-i", "_reel/end.png",
                    "-f", "lavfi", "-t", str(d), "-i", "anullsrc=r=48000:cl=stereo",
                    "-vf", "format=yuv420p,fade=t=in:st=0:d=0.3", "-c:v", "libx264", "-preset", "slow", "-profile:v", "high",
                    "-r", "25", "-b:v", f"{kbps}k", "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True)


def make(src, dst, tournament):
    os.makedirs("_reel", exist_ok=True)
    pts = pick(src)
    if len(pts) < 3:
        raise RuntimeError(f"só {len(pts)} momentos encontrados")
    total = sum(e - s for s, e, _ in pts) + 2.4
    kbps = int(min(6500, 22e6 * 8 / total / 1000 - 192))
    parts = []
    for k, (s, e, sc) in enumerate(pts):
        p = f"_reel/p{k}.mp4"
        segment(src, s, e, 3 - k, tournament, p, kbps)
        parts.append(p)
        print(f"#{3 - k}: {s:.1f}s–{e:.1f}s (nota {sc:.0f})")
    end_clip("_reel/end.mp4", kbps)
    parts.append("_reel/end.mp4")
    with open("_reel/list.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parts)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "_reel/list.txt", "-c:v", "copy",
                    "-af", "loudnorm=I=-15:TP=-1.5", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dst + ".part.mp4"], check=True)
    os.replace(dst + ".part.mp4", dst)
    print(f"Top 3: {dst} ({os.path.getsize(dst) / 1e6:.1f} MB, {total:.1f}s)")
    return pts


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "PREMIER PADEL")
