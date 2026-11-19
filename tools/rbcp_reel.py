"""Reel de exemplo com o vídeo oficial "Social Newscut Clean" do Red Bull Content Pool (19/11/2026, Afonso).
Corre no GitHub: descarrega o vídeo pelo link do pedido, põe por cima os nossos grafismos (Python/ffmpeg, sem IA)
e grava o resultado no repositório privado. O vídeo nunca passa por IA (regra "AI Prohibition" do RBCP).

  python tools/rbcp_reel.py <video.mp4|-> <saida.mp4>    (com "-" gera um vídeo de teste, só cores)
Crédito obrigatório dos vídeos (termos 4.6 a): "© Red Bull Media House"; no Instagram marcar @redbull."""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
NAVY, DEEP, CREAM, VOLT, SOFT = (12, 46, 74), (8, 26, 44), (247, 242, 230), (217, 242, 61), (169, 192, 214)
FD = "fonts"
CREDIT = "© Red Bull Media House"

FINALS = {"tournament": "DUBAI P1", "level": "P1", "date": "15 NOV 2026",
          "finals": [{"label": "MEN", "w": "AUGSBURGER / LEBRÓN", "l": "Libaak / Alfonso", "sets": ["7-6", "5-7", "6-3"]},
                     {"label": "WOMEN", "w": "FERNÁNDEZ / CALVO", "l": "Josemaría / González", "sets": ["7-5", "6-1"]}]}


def f(name, size):
    for n in (name, "Inter-Bold.otf"):
        p = os.path.join(FD, n)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.truetype("DejaVuSans-Bold.ttf", size)


def fit(d, text, name, size, max_w):
    while size > 20 and d.textlength(text, font=f(name, size)) > max_w:
        size -= 2
    return f(name, size)


def pill(d, x, y, text, fill, fg, size=30):
    ft = f("Inter-ExtraBold.otf", size)
    tw = d.textlength(text, font=ft)
    d.rounded_rectangle([x, y, x + tw + 40, y + size + 26], radius=(size + 26) // 2, fill=fill)
    d.text((x + 20 + tw / 2, y + (size + 26) / 2), text, font=ft, fill=fg, anchor="mm")
    return x + tw + 40


def shade(img, y0, y1, a0, a1):
    d = ImageDraw.Draw(img)
    for y in range(y0, y1):
        d.line([(0, y), (W, y)], fill=DEEP + (int(a0 + (a1 - a0) * (y - y0) / max(1, y1 - y0)),))


def brand_layer():
    """Sempre visível: marca em cima, crédito em baixo (termos 4.6 a: crédito junto ao conteúdo)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shade(im, 0, 260, 150, 0)
    shade(im, H - 170, H, 0, 150)
    d = ImageDraw.Draw(im)
    x = pill(d, 60, 92, "BEYOND PADEL", CREAM, NAVY, 30)
    pill(d, x + 14, 92, f"{FINALS['tournament']} · FINALS", (0, 0, 0, 0), CREAM, 30)
    d.rounded_rectangle([x + 14, 92, x + 14 + d.textlength(f"{FINALS['tournament']} · FINALS", font=f("Inter-ExtraBold.otf", 30)) + 40, 148],
                        radius=28, outline=CREAM, width=3)
    d.text((W - 60, H - 70), CREDIT, font=f("Inter-SemiBold.otf", 28), fill=SOFT, anchor="rm")
    d.text((60, H - 70), "@beyond100.padel", font=f("Inter-Bold.otf", 30), fill=CREAM, anchor="lm")
    return im


def result_layer():
    """Primeiros segundos: as duas finais, no estilo dos cartões de resultado."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    y0 = 1080
    shade(im, y0 - 220, y0, 0, 225)
    d = ImageDraw.Draw(im)
    d.rectangle([0, y0, W, H - 170], fill=DEEP + (225,))
    d.polygon([(0, y0 + 6), (W, y0 - 34), (W, y0 - 22), (0, y0 + 18)], fill=VOLT)
    y = y0 + 50
    pill(d, 60, y, "CHAMPIONS", VOLT, NAVY, 28)
    y += 90
    for fin in FINALS["finals"]:
        d.text((60, y), fin["label"], font=f("Inter-Bold.otf", 28), fill=SOFT)
        y += 40
        d.text((60, y), fin["w"], font=fit(d, fin["w"], "InterDisplay-Black.otf", 78, W - 120), fill=CREAM)
        y += 96
        x = 60
        for i, s in enumerate(fin["sets"]):
            ft = f("InterDisplay-Black.otf", 60)
            d.text((x, y), s, font=ft, fill=VOLT if i == len(fin["sets"]) - 1 or True else SOFT)
            x += d.textlength(s, font=ft) + 34
        d.text((x + 6, y + 18), f"def. {fin['l']}", font=f("Inter-SemiBold.otf", 32), fill=SOFT)
        y += 108
    return im


def end_layer():
    im = Image.new("RGBA", (W, H), DEEP + (235,))
    d = ImageDraw.Draw(im)
    d.text((W / 2, 820), "BEYOND PADEL", font=f("InterDisplay-Black.otf", 92), fill=CREAM, anchor="mm")
    d.text((W / 2, 930), "Every draw, not just the finals", font=f("Inter-SemiBold.otf", 40), fill=SOFT, anchor="mm")
    pill(d, W / 2 - 230, 1010, "Follow @beyond100.padel", VOLT, NAVY, 34)
    d.text((W / 2, 1220), CREDIT, font=f("Inter-SemiBold.otf", 30), fill=SOFT, anchor="mm")
    return im


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", p],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 30)


def main(src, dst):
    os.makedirs("_reel", exist_ok=True)
    if src == "-":
        src = "_reel/test.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=25:d=30",
                        "-f", "lavfi", "-i", "sine=f=220:d=30", "-shortest", "-pix_fmt", "yuv420p", src], check=True)
    brand_layer().save("_reel/brand.png")
    result_layer().save("_reel/result.png")
    end_layer().save("_reel/end.png")
    T = dur(src)
    e0 = max(0.0, T - 3.0)
    fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[v0];"
          f"[v0][1:v]overlay=0:0:enable='lt(t,{e0})'[v1];"
          f"[2:v]format=rgba,fade=t=out:st=3.2:d=0.5:alpha=1[r];[v1][r]overlay=0:0:enable='between(t,0.3,3.7)'[v2];"
          f"[3:v]format=rgba,fade=t=in:st={e0}:d=0.4:alpha=1[e];[v2][e]overlay=0:0:enable='gte(t,{e0})'[v]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                    "-loop", "1", "-t", str(T), "-i", "_reel/brand.png",
                    "-loop", "1", "-t", str(T), "-i", "_reel/result.png",
                    "-loop", "1", "-t", str(T), "-i", "_reel/end.png",
                    "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M",
                    "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "128k", "-af", "loudnorm=I=-15:TP=-1.5",
                    "-movflags", "+faststart", "-t", str(T), dst], check=True)
    print(f"Reel: {dst} ({os.path.getsize(dst) / 1e6:.1f} MB, {T:.1f}s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
