"""Beyond Padel: os 3 posts de apresentação (iguais aos primeiros do ténis, em azul) e as capas dos destaques.
python -m padel.intro  -> posts/padel-intro-1..3.jpg e padel/highlights/*.png"""
import os

from PIL import Image, ImageDraw

from padel.cards import BLUE, CREAM, VOLT, SOFT, BRAND, font, SERIF_B, SERIF_I, SANS_B
import photo_cards as pc

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def base():
    img = Image.new("RGB", (W, H), BLUE)
    d = ImageDraw.Draw(img)
    d.rectangle([36, 36, W - 37, H - 37], outline=SOFT, width=3)
    d.rectangle([52, 52, W - 53, H - 53], outline=(60, 98, 134), width=2)
    d.ellipse([W / 2 - 10, 1222, W / 2 + 10, 1242], fill=VOLT)
    d.text((W / 2, 1278), BRAND, font=font(SANS_B, 34), fill=CREAM, anchor="mm")
    return img, d


def post1():
    img, d = base()
    em = Image.open(os.path.join(HERE, "emblem.jpg")).convert("RGB").resize((560, 560), Image.LANCZOS)
    img.paste(em, ((W - 560) // 2, 120))
    d.text((W / 2, 850), "Padel beyond", font=font(SERIF_B, 92), fill=CREAM, anchor="mm")
    d.text((W / 2, 960), "the big names.", font=font(SERIF_I, 92), fill=VOLT, anchor="mm")
    pc.spaced(d, W / 2, 1105, "RESULTS · PREMIER PADEL · FIP TOUR", font(SANS_B, 28), CREAM, 5)
    return img


def post2():
    img, d = base()
    pc.spaced(d, W / 2, 190, "WHAT TO EXPECT", font(SANS_B, 30), VOLT, 7)
    d.text((W / 2, 300), "Every player. Every draw.", font=font(SERIF_I, 68), fill=CREAM, anchor="mm")
    items = [("Results & champions", "Clean cards from Premier Padel and the FIP Tour."),
             ("Upsets", "When the underdogs win, you see it here."),
             ("Players to watch", "Power Ranking and the biggest ranking climbers.")]
    y = 410
    d.line([(115, y), (W - 115, y)], fill=SOFT, width=2)
    for t, s in items:
        d.ellipse([125, y + 82, 151, y + 108], fill=VOLT)
        d.text((180, y + 95), t, font=font(SERIF_B, 62), fill=CREAM, anchor="lm")
        d.text((180, y + 170), s, font=pc.fit(d, s, SANS_B, 30, W - 300, 20), fill=SOFT, anchor="lm")
        y += 230
        d.line([(115, y), (W - 115, y)], fill=SOFT, width=2)
    return img


def post3():
    img, d = base()
    pc.spaced(d, W / 2, 230, "NEW HERE?", font(SANS_B, 30), VOLT, 7)
    d.text((W / 2, 520), "Follow along.", font=font(SERIF_B, 140), fill=CREAM, anchor="mm")
    d.text((W / 2, 700), "Results from every draw,", font=font(SERIF_I, 62), fill=CREAM, anchor="mm")
    d.text((W / 2, 785), "not just the finals.", font=font(SERIF_I, 62), fill=VOLT, anchor="mm")
    f = font(SANS_B, 34)
    t = "SAVE  ·  SHARE"
    tw = d.textlength(t, font=f)
    d.rounded_rectangle([W / 2 - tw / 2 - 80, 900, W / 2 + tw / 2 + 80, 990], radius=45, outline=CREAM, width=4)
    d.text((W / 2, 945), t, font=f, fill=CREAM, anchor="mm")
    return img


def highlight(label, draw_icon):
    S = 1080
    img = Image.new("RGB", (S, S), BLUE)
    d = ImageDraw.Draw(img)
    d.ellipse([60, 60, S - 60, S - 60], outline=CREAM, width=10)
    d.ellipse([100, 100, S - 100, S - 100], outline=SOFT, width=3)
    draw_icon(d, S)
    d.text((S / 2, 760), label, font=font(SANS_B, 84), fill=CREAM, anchor="mm")
    return img


def ic_results(d, S):
    x0, y0 = S / 2 - 220, 280
    d.rounded_rectangle([x0, y0, x0 + 440, y0 + 260], radius=30, outline=CREAM, width=8)
    d.line([(x0, y0 + 130), (x0 + 440, y0 + 130)], fill=CREAM, width=8)
    for (txt, c), (x, y) in zip([("6", VOLT), ("3", CREAM), ("4", CREAM), ("6", VOLT)], [(80, 65), (180, 65), (80, 195), (180, 195)]):
        d.text((x0 + x, y0 + y), txt, font=font(SERIF_B, 96), fill=c, anchor="mm")
    d.ellipse([x0 + 330, y0 + 45, x0 + 370, y0 + 85], fill=VOLT)


def ic_rank(d, S):
    for i, h in enumerate([150, 260, 200]):
        x = S / 2 - 200 + i * 140
        d.rectangle([x, 560 - h, x + 110, 560], fill=VOLT if i == 1 else CREAM)


def ic_live(d, S):
    cx, cy = S / 2, 400
    d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=VOLT)
    for r in (110, 190):
        d.arc([cx - r, cy - r, cx + r, cy + r], 210, 330, fill=VOLT, width=22)
        d.arc([cx - r, cy - r, cx + r, cy + r], 30, 150, fill=VOLT, width=22)


def ic_about(d, S):
    em = Image.open(os.path.join(HERE, "emblem.jpg")).convert("RGB").resize((420, 420), Image.LANCZOS)
    d._image.paste(em, (int(S / 2 - 210), 190))


def main(out_posts=os.path.join(ROOT, "posts"), out_hl=os.path.join(HERE, "highlights")):
    os.makedirs(out_posts, exist_ok=True)
    os.makedirs(out_hl, exist_ok=True)
    for i, f in enumerate((post1, post2, post3), 1):
        f().save(os.path.join(out_posts, f"padel-intro-{i}.jpg"), quality=95)
    for name, ic in (("live", ic_live), ("results", ic_results), ("rankings", ic_rank), ("about", ic_about)):
        highlight(name.upper(), ic).save(os.path.join(out_hl, f"{name}.png"))


if __name__ == "__main__":
    main()
