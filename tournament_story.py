"""Resumo escrito de cada torneio (25/11/2026): texto único por página, com os factos que as pessoas pesquisam
("who won the Montevideo Challenger 2026", "when is ..."). Sem IA: frases a partir dos resultados.
Devolve (html, perguntas_e_respostas) para a página e para os dados estruturados (FAQPage)."""
import html

ROUND_NAMES = {"final": "final", "finals": "final", "semi-finals": "semi-finals", "1/2-finals": "semi-finals",
               "quarter-finals": "quarter-finals", "1/4-finals": "quarter-finals"}
SURF = {"hard": "hard courts", "clay": "clay", "grass": "grass", "carpet": "carpet"}


def _d(s):
    import datetime as dt
    try:
        x = dt.date.fromisoformat(s)
        return f"{x.day} {x.strftime('%B %Y')}"
    except (TypeError, ValueError):
        return s or ""


def _rk(p):
    r = p.get("rank")
    return f" (No. {r})" if isinstance(r, int) else ""


def _score(r):
    w = r["winner"]
    return ", ".join(f"{a}-{b}" for a, b in zip(r["games"][w - 1], r["games"][2 - w]))


def _rd(r):
    x = (r.get("round") or "").strip().lower().split(" - ")[-1].strip()
    return {"final": "final", "finals": "final", "semi-finals": "semi-finals", "semifinals": "semi-finals", "1/2-finals": "semi-finals",
            "quarter-finals": "quarter-finals", "quarterfinals": "quarter-finals", "1/4-finals": "quarter-finals",
            "1/8-finals": "round of 16", "1/16-finals": "round of 32", "1/32-finals": "round of 64"}.get(x, x or "draw")


def story(full, singles, tag="", surface="", today=None):
    """full: nome oficial com ano; singles: jogos de singulares do torneio (dicts do results.json)."""
    esc = html.escape
    done = [r for r in singles if r.get("winner") in (1, 2) and r.get("games")]
    if not done:
        return "", []
    dates = sorted(r["date"] for r in done if r.get("date"))
    surf = SURF.get((surface or done[0].get("surface") or "").lower(), "")
    fin = next((r for r in done if _rd(r) == "final"), None)
    qa, s = [], []
    what = f"The {full}" + (f" ({tag})" if tag and tag.lower() not in full.lower() else "")
    s.append(f"{what} {'was' if fin else 'is being'} played on {surf}" if surf else what)
    if dates:
        s[-1] += f", with results from {_d(dates[0])}" + (f" to {_d(dates[-1])}" if dates[-1] != dates[0] else "") + "."
        qa.append((f"When is the {full}?", f"The {full} runs with matches from {_d(dates[0])}" +
                   (f" to {_d(dates[-1])}" if dates[-1] != dates[0] else "") + (f", on {surf}" if surf else "") + "."))
    else:
        s[-1] += "."
    if fin:
        w, l = fin["p%d" % fin["winner"]], fin["p%d" % (3 - fin["winner"])]
        line = f"{w['name']}{_rk(w)} won the title, beating {l['name']}{_rk(l)} {_score(fin)} in the final."
        s.append(line)
        qa.append((f"Who won the {full}?", line))
    else:
        alive = {}
        last = max(done, key=lambda r: r.get("date", ""))
        for r in done:
            alive[r["p%d" % r["winner"]]["name"]] = r
        losers = {r["p%d" % (3 - r["winner"])]["name"] for r in done}
        still = [n for n in alive if n not in losers]
        if 1 < len(still) <= 8:
            s.append(f"Still in the draw after the {_rd(last)}: " + ", ".join(still[:8]) + ".")
    ups = [r for r in done if isinstance(r["p%d" % r["winner"]].get("rank"), int) and isinstance(r["p%d" % (3 - r["winner"])].get("rank"), int)]
    ups = [r for r in ups if r["p%d" % r["winner"]]["rank"] > r["p%d" % (3 - r["winner"])]["rank"]]
    if ups:
        u = max(ups, key=lambda r: r["p%d" % r["winner"]]["rank"] - r["p%d" % (3 - r["winner"])]["rank"])
        w, l = u["p%d" % u["winner"]], u["p%d" % (3 - u["winner"])]
        if w["rank"] - l["rank"] >= 50 and u is not fin:
            s.append(f"Biggest upset: {w['name']}{_rk(w)} beat {l['name']}{_rk(l)} {_score(u)} in the {_rd(u)}.")
    three = sum(1 for r in done if len(r["games"][0]) >= 3)
    s.append(f"{len(done)} singles matches so far" + (f", {three} of them went to a deciding set." if three else ".")
             if not fin else f"{len(done)} singles matches played" + (f", {three} of them decided in a final set." if three else "."))
    body = f'<section class="tstory"><h2 class="dh">About the {esc(full)}</h2><p>{esc(" ".join(s))}</p></section>'
    return body, qa


def faq_ld(qa):
    if not qa:
        return None
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]}
