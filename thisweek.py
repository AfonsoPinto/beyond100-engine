"""Post semanal "This week in <ano>": uma final de Tour/Challenger desta mesma semana num ano anterior,
de preferência de alguém que depois chegou bem alto ("antes de ser famoso"). Dados: Tennis Abstract (history.json).

  python thisweek.py out          -> só no dia/hora (THROWBACK_DAY, 3 = quinta; THROWBACK_HOUR, 12 UTC), 1 por semana
  python thisweek.py out --force  -> gera já (teste)

Precisa de foto licenciada do vencedor (como todos os posts). Desligado por omissão desde 5/11/2026 (pedido do Afonso); liga-se com THROWBACK_ENABLED=1.
O post não conta para o limite diário de resultados (id começa por "news-").
"""
import datetime
import json
import os
import sys
import time

import captions
import news_card
import result_card as rc
import webapp

DAY = int(os.environ.get("THROWBACK_DAY") or "3")
HOUR = int(os.environ.get("THROWBACK_HOUR") or "12")


def pick(hist, today):
    wk = today.isocalendar()[1]
    P = hist.get("p") or {}
    used = set()
    for v in rc._load_json(rc.POSTS_FILE, {}).values():
        for e in v:
            used.add(str(e.get("id")))
    cands = []
    for f in hist.get("finals") or []:
        try:
            d = datetime.date.fromisoformat(f["d"])
        except (KeyError, ValueError):
            continue
        if d.year >= today.year or abs(d.isocalendar()[1] - wk) > 0:
            continue
        br = (P.get(webapp.slugify(f.get("w", ""))) or {}).get("br")
        wr = f.get("wr")
        # interesse: chegou muito acima do ranking que tinha na altura; títulos de Challenger primeiro
        jump = (wr - br) if isinstance(wr, int) and isinstance(br, int) and wr > br else 0
        score = jump + (200 if isinstance(br, int) and br <= 20 else 80 if isinstance(br, int) and br <= 50 else 0) + (50 if f.get("lv") == "Challenger" else 0)
        cands.append((score, d, f, br))
    cands.sort(key=lambda c: -c[0])
    return cands


def run(out_dir="out", force=False):
    if os.environ.get("THROWBACK_ENABLED", "0").strip() in ("0", "no", "off", "false") or os.environ.get("HISTORY") == "0":
        print("This week in: desligado.")
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    if not force and not (now.weekday() == DAY and now.hour >= HOUR):
        print("This week in: ainda não é a hora.")
        return None
    pid = f"news-hist-{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    posts = rc._load_json(rc.POSTS_FILE, {})
    if not force and any(str(e.get("id")) == pid for v in posts.values() for e in v):
        print("This week in: já saiu esta semana.")
        return None
    hist = rc._load_json("history.json", {})
    for score, d, f, br in pick(hist, now.date())[:15]:
        fp, credit = rc.find_photo({"name": f["w"]})
        if not fp or not credit:
            continue
        year, tn, lv = d.year, f.get("t", ""), f.get("lv", "")
        wr = f.get("wr")
        head = f"{f['w']} wins {tn}" + (f" as world No. {wr}" if isinstance(wr, int) else "")
        summ = (f"{f['w']} beat {f['l']} {f.get('sc', '')} in the {tn} final ({lv}, {year})." +
                (f" Career-high ranking since then: No. {br}." if isinstance(br, int) and (not isinstance(wr, int) or br < wr) else ""))
        os.makedirs(os.path.join(out_dir, "post"), exist_ok=True)
        png = os.path.join(out_dir, "post", pid + ".png")
        news_card.render_news({"badge": f"THIS WEEK IN {year}", "headline": head, "summary": summ, "source": "Tennis Abstract",
                               "photo": fp, "photo_credit": credit}, png)
        facts = {"year": year, "tournament": tn, "level": lv, "winner": f["w"], "runner_up": f["l"], "score": f.get("sc", ""),
                 "winner_ranking_then": wr, "career_best": br if isinstance(br, int) and (not isinstance(wr, int) or br < wr) else None}
        captions.save_caption(png, "history", {k: v for k, v in facts.items() if v is not None})
        today = time.strftime("%Y-%m-%d", time.gmtime())
        posts.setdefault(today, []).append({"id": pid, "score": 0, "reasons": ["history"], "file": pid + ".png"})
        with open(rc.POSTS_FILE, "w", encoding="utf-8") as fh:
            json.dump(posts, fh, ensure_ascii=False, indent=2)
        print(f"This week in {year}: {head} ({png})")
        return png
    print("This week in: nenhuma final desta semana com foto licenciada do vencedor.")
    return None


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "out", "--force" in sys.argv)
