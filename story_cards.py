"""Story diária "Today on court" (1080x1920), no estilo dos cartões novos (9/11/2026).
Fica no site em /story/today-tennis.jpg para o Afonso publicar à mão (com o autocolante de link para o site),
porque a API do Instagram não deixa pôr links em stories e o Make não publica stories.

  python story_cards.py out      -> out/story/today-tennis.jpg (sem pedidos à API: usa upcoming.json e fixtures.json)
"""
import datetime
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

import modern_cards as mc

SW, SH = 1080, 1920
LEVEL_ORDER = {"wta": 0, "atp": 0, "challenger": 1, "itf": 2}


def _load(p, d):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def pick_today(n=5, now=None):
    """Os jogos de hoje (UTC) mais interessantes: circuito principal primeiro, depois quem tem melhor ranking. Sem repetidos."""
    import result_card as rc
    now = now or datetime.datetime.now(datetime.timezone.utc)
    today = now.strftime("%Y-%m-%d")
    idx = rc._full_names()
    er = _load("espn_rank.json", {})                              # ranking oficial: completa nomes abreviados ("A. Sabalenka") e rankings em falta
    off = {}
    import webapp
    for lg in ("atp", "wta"):
        for x in er.get(lg) or []:
            nm = x.get("n") or ""
            ps = nm.split()
            if len(ps) >= 2:
                off.setdefault((ps[0][0].lower(), webapp.slugify(" ".join(ps[1:]))), (nm, x.get("r")))
                off.setdefault(("*", webapp.slugify(nm)), (nm, x.get("r")))

    def full(p):
        nm = p.get("name") or ""
        rk = p.get("rank") if isinstance(p.get("rank"), int) else None
        hit = off.get(("*", webapp.slugify(nm)))
        if not hit:
            import re as _re
            m_ = _re.match(r"^([A-Za-zÀ-ÿ])[a-zà-ÿ]*\.?\s+(.+)$", nm.strip())
            hit = off.get((m_.group(1).lower(), webapp.slugify(m_.group(2)))) if m_ else None
        if hit:
            return hit[0], rk or hit[1] or 999
        return rc._expand(nm, idx), rk or 999
    seen, rows = set(), []
    for src in ("upcoming.json", "fixtures.json"):
        for m in _load(src, {}).get("matches", []):
            t = m.get("t") or ""
            if not t.startswith(today) or m.get("status") in ("finished", "cancelled") or str(m.get("id")) in seen:
                continue
            if t[:16] < now.strftime("%Y-%m-%dT%H:%M"):          # já começou: não vai para a story da manhã
                continue
            seen.add(str(m.get("id")))
            a, b = m.get("p1") or {}, m.get("p2") or {}
            if not a.get("name") or not b.get("name") or "/" in a["name"]:
                continue
            (na, ra), (nb, rb) = full(a), full(b)
            rows.append({"t": t[11:16], "tp": (m.get("tp") or "").replace("Finals - ", "WTA Finals · "), "tour": m.get("tour") or "",
                         "a": na, "b": nb, "ra": ra, "rb": rb,
                         "key": (LEVEL_ORDER.get(m.get("tour"), 3), min(ra, rb) + max(ra, rb) / 10)})
    rows.sort(key=lambda r: r["key"])
    return sorted(rows[:n], key=lambda r: r["t"])


def render_today(rows, out, sport="tennis", date_label=None, photo=None, credit=None):
    P = mc.PALETTE[sport]
    img = Image.new("RGBA", (SW, SH), P["bg"] + (255,))
    if photo:
        bg = mc._photo(photo, (SW, SH)).filter(ImageFilter.GaussianBlur(4))
        img.alpha_composite(bg)
        img = mc._grad(img, 0, SH, P["bg"], 120, 235)
    img = img.convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    d.text((70, 300), P["brand"], font=mc.F("black", 34), fill=P["cream"], anchor="ls")
    mc._paste_sq(img, "TODAY", "black", 190, P["cream"] + (255,), 64, 500, SW - 140, anchor="lb")
    mc._paste_sq(img, "ON COURT", "black", 190, P["acc"] + (255,), 64, 664, SW - 140, anchor="lb")
    d = ImageDraw.Draw(img, "RGBA")
    d.text((70, 726), (date_label or "").upper() + "  ·  TIMES IN UTC", font=mc.F("semi", 30), fill=P["soft"], anchor="ls")
    y = 760
    for r in rows[:5]:
        box = (60, y, SW - 60, y + 140)
        d.rounded_rectangle(box, radius=30, fill=(0, 0, 0, 110), outline=(255, 255, 255, 50), width=2)
        d.text((100, y + 66), r["t"], font=mc.F("black", 44), fill=P["acc"], anchor="ls")
        tp = r["tp"].upper()
        d.text((100, y + 112), tp, font=mc._fit(d, tp, "bold", 22, 170, 14), fill=P["soft"], anchor="ls")
        tag = lambda rk: f"  #{rk}" if rk < 999 else ""
        x = 300
        d.text((x, y + 62), r["a"], font=mc._fit(d, r["a"], "xb", 38, 560), fill=P["cream"], anchor="ls")
        d.text((x + d.textlength(r["a"], font=mc._fit(d, r["a"], "xb", 38, 560)), y + 62), tag(r["ra"]), font=mc.F("semi", 26), fill=P["soft"], anchor="ls")
        d.text((x, y + 118), r["b"], font=mc._fit(d, r["b"], "xb", 38, 560), fill=P["cream"], anchor="ls")
        d.text((x + d.textlength(r["b"], font=mc._fit(d, r["b"], "xb", 38, 560)), y + 118), tag(r["rb"]), font=mc.F("semi", 26), fill=P["soft"], anchor="ls")
        y += 156
    d.text((SW / 2, y + 60), "Live scores · link below", font=mc.F("bold", 34), fill=P["cream"], anchor="ms")
    if photo and credit:
        d.text((SW - 60, y + 104), credit, font=mc._fit(d, credit, "med", 20, 700, 12), fill=P["soft"], anchor="rs")
    img.save(out, quality=92)
    return out


def make(out_dir="out"):
    import result_card as rc
    rows = pick_today()
    if len(rows) < 3:
        print(f"Story Today on court: só {len(rows)} jogos por começar hoje, não faz.")
        return None
    os.makedirs(os.path.join(out_dir, "story"), exist_ok=True)
    fp, cr = None, None
    for r in rows:                                               # fundo: foto boa de um dos jogadores (por ordem de interesse)
        for n in (r["a"], r["b"]):
            try:
                fp, cr = rc.find_post_photo({"name": n}, dry=True)[:2]
            except Exception:
                fp = None
            if fp:
                break
        if fp:
            break
    out = os.path.join(out_dir, "story", "today-tennis.jpg")
    render_today(rows, out, "tennis", datetime.date.today().strftime("%-d %b %Y"), fp, cr)
    print(f"Story Today on court: {len(rows)} jogos -> {out}")
    return out


if __name__ == "__main__":
    make(sys.argv[1] if len(sys.argv) > 1 else "out")
