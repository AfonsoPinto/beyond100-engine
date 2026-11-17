"""Emblema Beyond100 (o mesmo do site: círculo verde, BEYOND100 em arco, 100 ao centro) desenhado em PIL, para os painéis
e decalques da cena 3D.  emblem(size, bottom) -> imagem RGBA."""
import math, os
from PIL import Image, ImageDraw, ImageFont

GREEN, CREAM, VOLT = (14, 58, 45), (247, 242, 230), (217, 242, 61)
_SERIF = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"]


def _font(sz):
    for p in _SERIF:
        if os.path.exists(p): return ImageFont.truetype(p, sz)
    return ImageFont.truetype(os.path.join(os.path.dirname(__file__), "..", "..", "fonts", "Inter-Black.otf"), sz)


def _arc_text(im, text, cx, cy, r, font, fill, top=True, spacing=0.0):
    d = ImageDraw.Draw(im)
    ws = [d.textlength(c, font=font) for c in text]
    total = sum(ws) + spacing * (len(text) - 1)
    ang = total / r                                   # ângulo ocupado
    a = -math.pi / 2 - ang / 2 if top else math.pi / 2 + ang / 2
    for c, w in zip(text, ws):
        mid = a + (w / 2) / r * (1 if top else -1)
        x, y = cx + r * math.cos(mid), cy + r * math.sin(mid)
        g = Image.new("RGBA", (int(w * 2 + 20), int(font.size * 2)), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((g.width / 2, g.height / 2), c, font=font, fill=fill, anchor="mm")
        rot = -math.degrees(mid + math.pi / 2) if top else -math.degrees(mid - math.pi / 2)
        g = g.rotate(rot, resample=Image.BICUBIC, expand=True)
        im.alpha_composite(g, (int(x - g.width / 2), int(y - g.height / 2)))
        a += ((w + spacing) / r) * (1 if top else -1)


def emblem(size=1024, bottom="TENNIS · CHALLENGER · ITF"):
    S = 4 * size // 4; k = S / 600
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = S / 2
    d.ellipse([c - 290 * k, c - 290 * k, c + 290 * k, c + 290 * k], fill=GREEN, outline=CREAM, width=int(8 * k))
    d.ellipse([c - 170 * k, c - 170 * k, c + 170 * k, c + 170 * k], outline=CREAM, width=max(1, int(2 * k)))
    _arc_text(im, "BEYOND100", c, c, 222 * k, _font(int(52 * k)), CREAM, True, spacing=10 * k)
    _arc_text(im, bottom, c, c, 240 * k, _font(int(30 * k)), CREAM, False, spacing=5 * k)
    for sx in (-1, 1):
        d.ellipse([c + sx * 236 * k - 10 * k, c - 10 * k, c + sx * 236 * k + 10 * k, c + 10 * k], fill=VOLT)
    d.text((c, c + 6 * k), "100", font=_font(int(150 * k)), fill=CREAM, anchor="mm")
    return im


if __name__ == "__main__":
    import sys
    emblem(1024, sys.argv[2] if len(sys.argv) > 2 else "TENNIS · CHALLENGER · ITF").save(sys.argv[1] if len(sys.argv) > 1 else "emblem.png")
