"""Season in review 2026 (série de dezembro, aprovada pelo Afonso a 19/11/2026). Sem IA.

Dados: páginas "2026 ATP Tour" e "2026 WTA Tour" da Wikipedia (tabelas "Titles won by player", "Titles information",
rankings de fim de ano) — factos, com a fonte no cartão. O ESPN foi posto de parte: misturava WTA 125 e faltavam torneios.

  python season_review.py titles out.png      cartão "Most titles" (ATP e WTA)
  python season_review.py data                imprime o resumo dos dados (para conferir)"""
import html
import json
import os
import re
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFilter

import modern_cards as mc

W, H = 1080, 1350
PAGES = {"atp": "2026_ATP_Tour", "wta": "2026_WTA_Tour"}
CACHE = "season_2026_wiki.json"
SRC = "Data: Wikipedia, 2026 ATP Tour & 2026 WTA Tour (tour-level singles)"


def _get(page):
    u = f"https://en.wikipedia.org/w/api.php?action=parse&page={page}&prop=text&format=json&formatversion=2"
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Beyond100Bot/1.0 (beyond100tennis.com)"}), timeout=40) as r:
        return json.load(r)["parse"]["text"]


def _txt(c):
    c = re.sub(r"<sup.*?</sup>", "", c, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", c))).strip()


def _tables(t):
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", t, re.S):
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S)
        hdr = [_txt(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", rows[0] if rows else "", re.S)]
        yield hdr, rows


def titles(lg):
    """[(jogador, país, n.º de títulos de singulares, [torneios])] da tabela "Titles won by player":
    cada título é uma ligação "2026 <torneio> – (Men's/Women's) singles"; contam-se essas ligações."""
    t = page(lg)
    k = t.find('id="Titles_won_by_player"')
    if k < 0:
        return []
    tb = re.search(r"<table[^>]*>(.*?)</table>", t[k:], re.S).group(1)
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S):
        if "<td" not in r:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
        name = None
        for c in cells[:3]:
            a = re.findall(r'<a [^>]*href="/wiki/[^"]+"[^>]*title="([^"]+)"[^>]*>[^<●]+</a>', c)
            if a:
                name = html.unescape(a[0]); break
        if not name:
            continue
        ctry = re.search(r'<abbr title="([^"]+)">([A-Z]{3})</abbr>', r)
        evs = [html.unescape(x) for x in re.findall(r'title="(2026 [^"]+?) – (?:Men&#39;s |Women&#39;s )?[Ss]ingles"', r)]
        evs = [re.sub(r"^2026 ", "", e) for e in evs]
        if evs:
            out.append((name, ctry.group(2) if ctry else "", len(evs), evs))
    return sorted(out, key=lambda x: -x[2])


_PAGE = {}


def page(lg):
    if lg not in _PAGE:
        _PAGE[lg] = _get(PAGES[lg])
    return _PAGE[lg]


def _anchor_seg(t, anchor, stop=None, n=60000):
    k = t.find(f'id="{anchor}"')
    if k < 0:
        return ""
    seg = t[k:k + n]
    if stop:
        e = seg.find(stop, 50)
        if e > 0:
            seg = seg[:e]
    return seg


def first_titles(lg):
    """Primeiros títulos da carreira em singulares em 2026: [(nome, país, idade, torneio)] (secção "Titles information")."""
    seg = _anchor_seg(page(lg), "Titles_information", stop="Doubles")
    out = []
    for li in re.findall(r"<li>(.*?)</li>", seg, re.S):
        a = re.search(r'<a [^>]*title="([^"]+)"[^>]*>[^<]+</a>', re.sub(r'<span class="flagicon">.*?</span>', "", li, flags=re.S))
        age = re.search(r"\((?:\s|&#160;)*(\d+)(?:&#160;|\s)years", li)
        ctry = re.search(r'<img alt="([^"]+)"', li) or re.search(r'flagicon[^>]*>.*?title="([^"]+)"', li, re.S)
        txt = _txt(li)
        city = re.search(r"\)\s*[–-]\s*([^()]+?)\s*\(", txt)
        if a:
            out.append((html.unescape(a.group(1)), html.unescape(ctry.group(1)) if ctry else "", int(age.group(1)) if age else None,
                        city.group(1).strip() if city else ""))
    return out


def nations(lg):
    """[(país, títulos de singulares)] da tabela "Titles won by nation"."""
    t = page(lg)
    k = t.find('id="Titles_won_by_nation"')
    if k < 0:
        return []
    tb = re.search(r"<table[^>]*>(.*?)</table>", t[k:], re.S).group(1)
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S):
        if "<td" not in r:
            continue
        nat = re.search(r'<a [^>]*href="/wiki/[^"]+"[^>]*>([^<●]{3,})</a>', re.sub(r'<span class="flagicon">.*?</span>', "", r, flags=re.S))
        n = len(re.findall(r'title="2026 [^"]+? – (?:Men&#39;s |Women&#39;s )?[Ss]ingles"', r))
        if nat and n:
            out.append((html.unescape(nat.group(1)), n))
    return sorted(out, key=lambda x: -x[1])


def _rank_table(t, title_start):
    """Linhas (posição, nome, pontos) da primeira tabela cujo cabeçalho começa por title_start."""
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", t, re.S):
        body = m.group(1)
        if not _txt(body[:600]).startswith(title_start):
            continue
        rows = []
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
            cells = [_txt(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            a = re.findall(r'<a [^>]*href="/wiki/[^"]+"[^>]*title="([^"]+)"[^>]*>[^<]+</a>', re.sub(r'<span class="flagicon">.*?</span>', "", r, flags=re.S))
            if cells and cells[0].isdigit() and a:
                rows.append((int(cells[0]), html.unescape(a[0]), cells))
        if rows:
            return rows
    return []


def top20(lg, year=2026):
    t = page(lg) if year == 2026 else _get(f"{year}_{lg.upper()}_Tour")
    for title in ("WTA Singles Year-End Rankings", "ATP rankings (singles)", "ATP Singles Year-End", "WTA rankings (singles)", "Final Singles Race"):
        rows = _rank_table(t, title)
        if rows and not title.startswith("Final"):
            return [(n, name) for n, name, _ in rows][:20]
    return []


def prize(lg):
    rows = _rank_table(page(lg), "Prize money")
    out = []
    for n, name, cells in rows[:3]:
        money = next((c for c in reversed(cells) if c.startswith("$") or re.fullmatch(r"[\d,]{6,}", c.replace("$", ""))), "")
        out.append((name, money))
    return out


def data():
    if os.path.exists(CACHE):
        return json.load(open(CACHE, encoding="utf-8"))
    d = {"titles": {lg: titles(lg) for lg in PAGES}, "first": {lg: first_titles(lg) for lg in PAGES},
         "nations": {lg: nations(lg) for lg in PAGES}, "top20": {lg: top20(lg) for lg in PAGES},
         "top20_2025": {lg: top20(lg, 2025) for lg in PAGES}, "prize": {lg: prize(lg) for lg in PAGES}}
    json.dump(d, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return d


NICK = {"French Open": "Roland Garros", "Wimbledon Championships": "Wimbledon", "Australian Open": "Australian Open", "US Open": "US Open",
        "BNP Paribas Open": "Indian Wells", "Mutua Madrid Open": "Madrid", "Italian Open": "Rome", "Monte-Carlo Masters": "Monte-Carlo",
        "Rolex Paris Masters": "Paris", "Rolex Shanghai Masters": "Shanghai", "National Bank Open": "Canada", "Cincinnati Open": "Cincinnati",
        "Miami Open": "Miami", "Qatar TotalEnergies Open": "Doha", "Qatar ExxonMobil Open": "Doha", "Dubai Tennis Championships": "Dubai",
        "Porsche Tennis Grand Prix": "Stuttgart", "Upper Austria Ladies Linz": "Linz", "Erste Bank Open": "Vienna", "Japan Open Tennis Championships": "Tokyo"}


def short_event(e):
    """Nome curto do torneio, sem patrocinadores ("BNP Paribas Open" -> "Indian Wells")."""
    return NICK.get(e) or re.sub(r"\s+(International|Championships|Open|Tennis|Grand Prix|Ladies)\b.*$", "", e).strip() or e


# ------------------------------------------------------------------ desenho "Wrapped" (moderno)
BG, MID, ACC, CREAM, SOFT = (6, 24, 19), (14, 58, 45), (217, 242, 61), (247, 242, 230), (150, 178, 165)


def _canvas():
    img = Image.new("RGBA", (W, H), BG + (255,))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse([-300, -420, 820, 520], fill=(40, 120, 80, 150))
    g.ellipse([520, 760, 1500, 1700], fill=(217, 242, 61, 60))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(140)))
    big = mc._squeeze("2026", "black", 560, (247, 242, 230, 16), sx=0.8)          # "2026" gigante em fundo
    img.alpha_composite(big, (W - big.width + 60, 250))
    import random
    rnd = random.Random(7)
    noise = Image.new("RGBA", (W, H), (0, 0, 0, 0))                                  # grão subtil
    nd = noise.load()
    for _ in range(26000):
        x, y = rnd.randrange(W), rnd.randrange(H)
        nd[x, y] = (255, 255, 255, rnd.randrange(6, 20))
    img.alpha_composite(noise)
    return img


def _pill(d, x, y, text, fill, fg, size=26):
    f = mc.F("xb", size)
    w = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + w + 36, y + size + 22], radius=(size + 22) // 2, fill=fill)
    d.text((x + 18, y + (size + 22) / 2), text, font=f, fill=fg, anchor="lm")
    return x + w + 36


def _avatar(name, size):
    try:
        import features
        fp, cr = features._hero_photo(name)
    except Exception:
        fp, cr = None, None
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse([0, 0, size - 1, size - 1], fill=255)
    if fp:
        ph = mc._photo(fp, (size, size))
    else:
        ph = Image.new("RGBA", (size, size), MID + (255,))
        ini = "".join(w[0] for w in name.split()[:2]).upper()
        ImageDraw.Draw(ph).text((size / 2, size / 2), ini, font=mc.F("black", int(size * 0.38)), fill=CREAM, anchor="mm")
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(ph, (0, 0), m)
    return out, cr


def titles_card(out):
    d0 = data()["titles"]
    img = _canvas()
    d = ImageDraw.Draw(img)
    x = _pill(d, 64, 64, "BEYOND100", CREAM, BG)
    _pill(d, x + 12, 64, "2026 IN REVIEW", ACC, BG)
    mc._paste_sq(img, "MOST", "black", 190, CREAM, 60, 140, 900, sx=0.74)
    mc._paste_sq(img, "TITLES", "black", 190, ACC, 60, 300, 900, sx=0.74)
    d = ImageDraw.Draw(img)
    d.text((66, 480), "Tour-level singles titles this season", font=mc.F("semi", 32), fill=SOFT)
    credits = []
    y = 548
    for lg in ("atp", "wta"):
        rows = d0.get(lg) or []
        if not rows:
            continue
        top = rows[0][2]
        d.text((64, y), lg.upper(), font=mc.F("black", 30), fill=ACC)
        d.line([(140, y + 18), (W - 64, y + 18)], fill=(70, 110, 92), width=2)
        y += 50
        for i, (name, ctry, n, evs) in enumerate(rows[:3]):
            lead = n == top
            h = 96 if i == 0 else 74
            av, cr = _avatar(name, h - 12)
            if cr:
                credits.append(cr)
            bx = 64 + h + 4
            maxw = W - 64 - 110 - bx
            bw = max(int(maxw * n / top), 300)
            ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(ov).rounded_rectangle([bx, y, bx + bw, y + h - 12], radius=(h - 12) // 2,
                                                 fill=(ACC + (255,)) if lead else (247, 242, 230, 30))
            img.alpha_composite(ov)
            img.alpha_composite(av, (64, y))
            d = ImageDraw.Draw(img)
            fg = BG if lead else CREAM
            nm = f"{name}  {ctry}" if ctry else name
            if i == 0 and evs:
                d.text((bx + 28, y + (h - 12) / 2 - 15), name, font=mc._fit(d, name, "xb", 38, bw - 50), fill=fg, anchor="lm")
                ev = " · ".join(short_event(e) for e in evs[:3])
                d.text((bx + 28, y + (h - 12) / 2 + 22), ev, font=mc._fit(d, ev, "semi", 22, bw - 50, 14), fill=(BG + (200,)) if lead else SOFT, anchor="lm")
            else:
                d.text((bx + 26, y + (h - 12) / 2), name, font=mc._fit(d, name, "bold", 30, bw - 46), fill=fg, anchor="lm")
            d.text((W - 64, y + (h - 12) / 2), str(n), font=mc.F("black", 76 if i == 0 else 56), fill=CREAM if lead else ACC, anchor="rm")
            y += h + 6
        y += 26
    d.text((64, H - 92), "@beyond100.tennis", font=mc.F("bold", 30), fill=CREAM, anchor="lm")
    d.text((64, H - 52), SRC, font=mc.F("med", 18), fill=SOFT, anchor="lm")
    if credits:
        cr = "Photos: " + " · ".join(dict.fromkeys(" ".join(str(c).split()) for c in credits if c))
        d.text((W - 64, H - 92), cr, font=mc._fit(d, cr, "med", 16, 560, 10), fill=SOFT, anchor="rm")
    img.convert("RGB").save(out, quality=92)
    return out


if __name__ == "__main__":
    if sys.argv[1] == "data":
        for k, v in data().items():
            for lg, rows in v.items():
                print(k, lg, len(rows), rows[:6])
    else:
        {"titles": titles_card}[sys.argv[1]](sys.argv[2])
