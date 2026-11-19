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
        age = re.search(r"\(\s*(\d+)\s*years", _txt(li))
        ctry = re.search(r'<img alt="([^"]+)"', li) or re.search(r'flagicon[^>]*>.*?title="([^"]+)"', li, re.S)
        txt = _txt(li)
        city = re.search(r"\)\s*[–-]\s*([^()]+?)\s*\(", txt)
        if a:
            out.append((html.unescape(a.group(1)), html.unescape(ctry.group(1)) if ctry else "", int(age.group(1)) if age else None,
                        city.group(1).strip() if city else ""))
    return out


def nations(lg):
    """[(país, títulos de singulares)] da tabela "Titles won by nation". A coluna certa é a que soma o total de títulos
    de singulares da tabela dos jogadores (assim não dependemos da ordem das colunas)."""
    t = page(lg)
    k = t.find('id="Titles_won_by_nation"')
    if k < 0:
        return []
    tb = re.search(r"<table[^>]*>(.*?)</table>", t[k:], re.S).group(1)
    rows = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", tb, re.S):
        if "<td" not in r:
            continue
        nat = re.search(r'<a [^>]*href="/wiki/[^"]+"[^>]*>([^<●]{3,})</a>', re.sub(r'<span class="flagicon">.*?</span>', "", r, flags=re.S))
        cells = [_txt(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        nums = [int(c) for c in cells if c.isdigit()]
        if nat and nums:
            rows.append((html.unescape(nat.group(1)), nums))
    total = sum(x[2] for x in titles(lg))
    for back in (2, 3, 1, 4):
        col = [(n, nums[-back]) for n, nums in rows if len(nums) >= back]
        if col and sum(v for _, v in col) == total:
            return sorted([x for x in col if x[1] > 0], key=lambda x: -x[1])
    print(f"Nações {lg}: nenhuma coluna soma {total} títulos; não uso.")
    return []


def _rank_table(t, title_start):
    """Linhas (posição, nome, células) da primeira tabela cujo cabeçalho começa por title_start
    (ou, com title_start=None, a primeira tabela de ranking de singulares que não seja a Race)."""
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", t, re.S):
        body = m.group(1)
        head = _txt(body[:600]).lower()
        if title_start and not head.startswith(title_start.lower()):
            continue
        if not title_start and not ("ranking" in head and "singles" in head and "race" not in head and "double" not in head.split("player")[0]):
            continue
        rows = []
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
            cells = [_txt(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            a = [x for x in re.findall(r'<a [^>]*href="/wiki/[^"]+"[^>]*title="([^"]+)"[^>]*>[^<]+</a>', re.sub(r'<span class="flagicon">.*?</span>', "", r, flags=re.S))
                 if not x.startswith("List of") and not x.startswith("Help:")]
            if cells and cells[0].isdigit() and a:
                rows.append((int(cells[0]), html.unescape(a[0]), cells))
        if rows:
            return rows
    return []


def top20(lg, year=2026):
    t = page(lg) if year == 2026 else _get(f"{year}_{lg.upper()}_Tour")
    for title in ("WTA Singles Year-End Rankings", "ATP rankings (singles)", "ATP Singles Year-End", "WTA rankings (singles)", None):
        rows = _rank_table(t, title)
        if rows:
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


def _head(img, l1, l2, sub, top=64):
    d = ImageDraw.Draw(img)
    x = _pill(d, 64, top, "BEYOND100", CREAM, BG)
    _pill(d, x + 12, top, "2026 IN REVIEW", ACC, BG)
    mc._paste_sq(img, l1, "black", 170, CREAM, 60, top + 76, 950, sx=0.74)
    mc._paste_sq(img, l2, "black", 170, ACC, 60, top + 222, 950, sx=0.74)
    d = ImageDraw.Draw(img)
    d.text((66, top + 392), sub, font=mc._fit(d, sub, "semi", 30, W - 130), fill=SOFT)
    return top + 450


def _foot(img, credits):
    d = ImageDraw.Draw(img)
    d.text((64, H - 92), "@beyond100.tennis", font=mc.F("bold", 30), fill=CREAM, anchor="lm")
    d.text((64, H - 52), SRC.replace(" (tour-level singles)", ""), font=mc.F("med", 18), fill=SOFT, anchor="lm")
    if credits:
        cr = "Photos: " + " · ".join(dict.fromkeys(" ".join(str(c).split()) for c in credits if c))
        d.text((W - 64, H - 92), cr, font=mc._fit(d, cr, "med", 16, 560, 10), fill=SOFT, anchor="rm")


def _glass(img, box, a=26, r=28, fill=None):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(box, radius=r, fill=fill or (247, 242, 230, a))
    img.alpha_composite(ov)


def first_card(out):
    D = data()["first"]
    img = _canvas()
    n_all = sum(len(v) for v in D.values())
    y = _head(img, "FIRST", "TITLES", f"{n_all} players won their first tour-level title in 2026")
    credits = []
    allp = [(p, lg) for lg in ("atp", "wta") for p in D.get(lg) or [] if p[2]]
    young = min(allp, key=lambda x: x[0][2]) if allp else None
    colw = (W - 128 - 24) // 2
    for c, lg in enumerate(("atp", "wta")):
        x0 = 64 + c * (colw + 24)
        yy = y
        d = ImageDraw.Draw(img)
        d.text((x0, yy), lg.upper(), font=mc.F("black", 28), fill=ACC)
        yy += 46
        for (name, ctry, age, city) in (D.get(lg) or [])[:7]:
            hot = young and young[0][0] == name
            _glass(img, [x0, yy, x0 + colw, yy + 66], a=30, r=33, fill=(ACC + (255,)) if hot else None)
            av, cr = _avatar(name, 54)
            if cr:
                credits.append(cr)
            img.alpha_composite(av, (x0 + 6, yy + 6))
            d = ImageDraw.Draw(img)
            fg, sf = (BG, BG) if hot else (CREAM, SOFT)
            d.text((x0 + 72, yy + 20), name, font=mc._fit(d, name, "bold", 24, colw - 90, 14), fill=fg, anchor="lm")
            sub = (f"{age} · " if age else "") + city + ("  · YOUNGEST" if hot else "")
            d.text((x0 + 72, yy + 46), sub, font=mc._fit(d, sub, "semi", 19, colw - 90, 12), fill=sf, anchor="lm")
            yy += 74
    _foot(img, credits)
    img.convert("RGB").save(out, quality=92)
    return out


def newtop20_card(out):
    T, T0 = data()["top20"], data()["top20_2025"]
    img = _canvas()
    y = _head(img, "NEW IN", "THE TOP 20", "Inside the top 20 now, outside it at the end of 2025")
    credits = []
    colw = (W - 128 - 24) // 2
    for c, lg in enumerate(("atp", "wta")):
        before = {n for _, n in T0.get(lg) or []}
        new = [(r, n) for r, n in T.get(lg) or [] if n not in before][:6]
        x0 = 64 + c * (colw + 24)
        yy = y
        d = ImageDraw.Draw(img)
        d.text((x0, yy), lg.upper(), font=mc.F("black", 28), fill=ACC)
        yy += 46
        for i, (r, name) in enumerate(new):
            h = 100 if i == 0 else 78
            _glass(img, [x0, yy, x0 + colw, yy + h - 8], a=30, r=(h - 8) // 2, fill=(ACC + (255,)) if i == 0 else None)
            av, cr = _avatar(name, h - 20)
            if cr:
                credits.append(cr)
            img.alpha_composite(av, (x0 + 6, yy + 6))
            d = ImageDraw.Draw(img)
            fg = BG if i == 0 else CREAM
            d.text((x0 + h + 2, yy + (h - 8) / 2), name, font=mc._fit(d, name, "bold", 26 if i == 0 else 23, colw - h - 110, 13), fill=fg, anchor="lm")
            d.text((x0 + colw - 20, yy + (h - 8) / 2), f"#{r}", font=mc.F("black", 48 if i == 0 else 38), fill=BG if i == 0 else ACC, anchor="rm")
            yy += h + 4
    _foot(img, credits)
    img.convert("RGB").save(out, quality=92)
    return out


def nations_card(out):
    T = data()["titles"]
    tally = {}
    for lg in ("atp", "wta"):
        for name, ctry, n, evs in T.get(lg) or []:
            if ctry:
                a = tally.setdefault(ctry, [0, 0]); a[0 if lg == "atp" else 1] += n
    rows = sorted(tally.items(), key=lambda x: -(x[1][0] + x[1][1]))[:8]
    img = _canvas()
    y = _head(img, "NATIONS", "OF THE YEAR", "Tour-level singles titles by country, men and women")
    d = ImageDraw.Draw(img)
    top = sum(rows[0][1]) if rows else 1
    for i, (c, (m, w)) in enumerate(rows):
        h = 66
        bx, maxw = 64 + 96, W - 64 - 110 - 160
        wm, ww = int(maxw * m / top), int(maxw * w / top)
        _glass(img, [64, y, 64 + 80, y + h - 10], r=(h - 10) // 2, fill=(ACC + (255,)) if i == 0 else (247, 242, 230, 30))
        if wm:
            _glass(img, [bx, y, bx + wm, y + h - 10], r=12, fill=ACC + (255,))
        if ww:
            _glass(img, [bx + wm + (4 if wm else 0), y, bx + wm + 4 + ww, y + h - 10], r=12, fill=(247, 242, 230, 200))
        d = ImageDraw.Draw(img)
        d.text((104, y + (h - 10) / 2), c, font=mc.F("black", 24), fill=BG if i == 0 else CREAM, anchor="mm")
        d.text((W - 64, y + (h - 10) / 2), str(m + w), font=mc.F("black", 52 if i == 0 else 40), fill=CREAM if i == 0 else ACC, anchor="rm")
        y += h
    d.rounded_rectangle([64, y + 14, 88, y + 38], radius=6, fill=ACC)
    d.text((98, y + 26), "ATP", font=mc.F("bold", 22), fill=SOFT, anchor="lm")
    d.rounded_rectangle([170, y + 14, 194, y + 38], radius=6, fill=(247, 242, 230))
    d.text((204, y + 26), "WTA", font=mc.F("bold", 22), fill=SOFT, anchor="lm")
    _foot(img, [])
    img.convert("RGB").save(out, quality=92)
    return out


def numbers_card(out):
    D = data()
    T, F, P, R = D["titles"], D["first"], D["prize"], D["top20"]
    allf = [(p, lg) for lg in ("atp", "wta") for p in F.get(lg) or [] if p[2]]
    young = min(allf, key=lambda x: x[0][2])[0] if allf else None
    tiles = []
    for lg in ("atp", "wta"):
        rows = T.get(lg) or []
        if rows:
            lead = [r for r in rows if r[2] == rows[0][2]]
            tiles.append((str(rows[0][2]), f"most {lg.upper()} titles", " & ".join(r[0].split()[-1] for r in lead[:2])))
    tiles.append((str(sum(len(v) for v in F.values())), "first-time champions", "men and women"))
    if young:
        tiles.append((str(young[2]), "youngest first-time champion", f"{young[0]} · {young[3]}"))
    for lg in ("atp", "wta"):
        if P.get(lg):
            name, money = P[lg][0]
            v = int(re.sub(r"\D", "", money) or 0)
            tiles.append((f"${v / 1e6:.1f}M", f"{lg.upper()} prize money leader", name))
    for lg in ("atp", "wta"):
        if R.get(lg):
            tiles.append(("No.1", f"{lg.upper()} ranking leader", R[lg][0][1]))
    img = _canvas()
    y = _head(img, "2026 IN", "NUMBERS", "The season at a glance")
    gw = (W - 128 - 24) // 2
    for i, (big, lab, who) in enumerate(tiles[:8]):
        c, r = i % 2, i // 2
        x0, y0 = 64 + c * (gw + 24), y + r * 168
        hot = i == 0
        _glass(img, [x0, y0, x0 + gw, y0 + 152], a=28, r=28, fill=(ACC + (255,)) if hot else None)
        d = ImageDraw.Draw(img)
        fg, sf = (BG, BG) if hot else (CREAM, SOFT)
        mc._paste_sq(img, big, "black", 70, ACC if not hot else BG, x0 + 26, y0 + 18, gw - 52, sx=0.8)
        d = ImageDraw.Draw(img)
        d.text((x0 + 28, y0 + 104), lab.upper(), font=mc._fit(d, lab.upper(), "xb", 19, gw - 56, 12), fill=sf, anchor="lm")
        d.text((x0 + 28, y0 + 130), who, font=mc._fit(d, who, "bold", 22, gw - 56, 12), fill=fg, anchor="lm")
    _foot(img, [])
    img.convert("RGB").save(out, quality=92)
    return out


if __name__ == "__main__":
    if sys.argv[1] == "data":
        for k, v in data().items():
            for lg, rows in v.items():
                print(k, lg, len(rows), rows[:6])
    else:
        {"titles": titles_card, "first": first_card, "top20": newtop20_card, "nations": nations_card, "numbers": numbers_card}[sys.argv[1]](sys.argv[2])
