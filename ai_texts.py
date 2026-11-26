"""Textos de fundo escritos pela IA (Gemini, nível gratuito), 25/11/2026. Corre no GitHub em cada atualização completa,
sem depender do Claude. Cada tarefa só usa a margem do dia (llm.remaining) e para quando a margem acaba.
- bios.json: um parágrafo "In 2026" por jogador, a partir dos nossos dados (sem inventar), para as páginas do site
- previews_ai.json: antevisão escrita de cada torneio no dia em que começa
- weekly_report.json: relatório semanal (segunda) em português para o painel de administração
Sem chave de IA, ou sem margem, não faz nada: o site usa os textos sem IA."""
import datetime as dt
import json
import os
import re
import sys
import time

import llm

BIOS, PREVIEWS, REPORT = "bios.json", "previews_ai.json", "weekly_report.json"
VERSION = 4                       # 26/11/2026: v2 sem contagem de vitórias/derrotas; textos de versões antigas são refeitos ou tirados
BIO_DAYS = 14                     # cada bio é refeita no máximo de 2 em 2 semanas (ou quando o ranking muda muito)
STYLE = ("Write in plain, neutral English, like a careful sports journalist. Use ONLY the facts in the JSON. "
         "Never invent results, injuries, coaches, quotes, personal details or adjectives about personality. "
         "No hype words (sensational, stunning, superstar, phenomenal, sizzling). No emojis, no hashtags, no markdown.")


def _load(p, d):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def _save(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def _ask(system, data, feature, max_tokens=500, priority="low"):
    llm.PRIORITY = priority
    r = llm.post("", json={"model": "haiku" if priority == "low" else "gemini", "max_tokens": max_tokens, "system": system, "_feature": feature,
                           "messages": [{"role": "user", "content": json.dumps(data, ensure_ascii=False)}]}, timeout=90)
    if r.status_code >= 400:
        print(f"IA ({feature}): indisponível ({r.status_code}).")
        return None
    t = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text").strip()
    return t or None


BANNED = re.compile(r"\b(sensational|stunning|superstar|phenomenal|sizzling|legend|unstoppable|dominant force)\b", re.I)


ORD = {"first": 1, "second": 2, "third": 3}


def _clean(t, max_words=110, facts=None):
    """Rejeita textos com palavras proibidas, demasiado longos ou com NÚMEROS que não estão nos dados (rede de segurança contra invenções)."""
    t = re.sub(r"[*_#`]+", "", t or "").strip()
    if not t or BANNED.search(t) or len(t.split()) > max_words:
        return None
    if facts is not None:
        allowed = set(re.findall(r"\d+", json.dumps(facts, ensure_ascii=False))) | {"1", "2", "3", time.strftime("%Y")}
        bad = [n for n in re.findall(r"\d+", t) if n not in allowed]
        if bad:
            print(f"IA: texto rejeitado (números que não estão nos dados: {bad[:5]}).")
            return None
        # vitórias e derrotas têm de bater certo com os jogos (26/11: a IA escreveu que o Shelton ganhou ao Zverev, mas perdeu)
        for m in facts.get("recent_matches") or []:
            sur = re.escape((m.get("opponent") or "").split()[-1]) if m.get("opponent") else None
            if not sur:
                continue
            win_words = r"(beat|beating|defeat\w*|victory over|win over|wins over|won over|won against|upset\w*|ousted|knocked out|eliminat\w*)"
            lose_words = r"(lost to|losing to|fell to|falling to|defeated by|beaten by|loss to|lose to)"
            if not m.get("won") and re.search(win_words + r"\W+(?:[\w-]+\W+){0,5}" + sur + r"\b", t, re.I):
                print(f"IA: texto rejeitado (diz que ganhou a {m.get('opponent')}, mas perdeu).")
                return None
            if m.get("won") and re.search(lose_words + r"\W+(?:[\w-]+\W+){0,5}" + sur + r"\b", t, re.I):
                print(f"IA: texto rejeitado (diz que perdeu com {m.get('opponent')}, mas ganhou).")
                return None
        if re.search(r"\b(record|unbeaten|undefeated|won all)\b", t, re.I):
            print("IA: texto rejeitado (fala de registo de vitórias, que não temos completo).")
            return None
    return t


# ------------------------------------------------------------------ bios
def _player_facts(name, results, er):
    from webapp import slugify
    sl = slugify(name)
    ms = sorted([r for r in results if r.get("winner") in (1, 2) and name in (r["p1"]["name"], r["p2"]["name"]) and " / " not in r["p1"]["name"]],
                key=lambda r: r.get("date", ""))
    if len(ms) < 3:
        return None
    yr = time.strftime("%Y")
    w = sum(1 for r in ms if r["p%d" % r["winner"]]["name"] == name and r.get("date", "").startswith(yr))
    l = sum(1 for r in ms if r["p%d" % (3 - r["winner"])]["name"] == name and r.get("date", "").startswith(yr))
    rank = next((x for lg in ("atp", "wta") for x in (er.get(lg) or []) if slugify(x.get("n") or "") == sl), None)
    me = lambda r: 1 if r["p1"]["name"] == name else 2
    last = []
    for r in ms[-6:]:
        i = me(r)
        o = r["p%d" % (3 - i)]
        import tournament_story
        last.append({"date": r.get("date"), "tournament": r.get("tournament"), "round": tournament_story._rd(r),
                     "opponent": o["name"], "opponent_rank": o.get("rank"), "won": r["winner"] == i,
                     "score": ", ".join(f"{a}-{b}" for a, b in zip(r["games"][i - 1], r["games"][2 - i]))})
    titles = [r.get("tournament") for r in ms if (r.get("round") or "").split(" - ")[-1].lower() == "final"
              and r["p%d" % r["winner"]]["name"] == name and r.get("date", "").startswith(yr)]
    p = ms[-1]["p%d" % me(ms[-1])]
    # atenção: só temos os jogos que acompanhámos (não a época inteira): o registo é "desde <data>", nunca "this season"
    # 26/11/2026: sem contagem de vitórias/derrotas: não temos todos os jogos de todos os jogadores, por isso o registo podia estar errado
    return {"name": name, "country": (p.get("country") or "").upper(), "ranking": (rank or {}).get("r") or p.get("rank"),
            "previous_week_ranking": (rank or {}).get("prev"), "since": ms[0].get("date"),
            "titles_since": titles, "recent_matches": last}


def bios(results):
    if llm.remaining("low") <= 0:
        return 0
    from webapp import slugify
    er = _load("espn_rank.json", {})
    pop = _load("popular.json", {}).get("tennis") or {}
    try:
        import reach
        searched = set(reach.searched_slugs())
    except Exception:
        searched = set()
    names = {}
    for r in results:
        for k in ("p1", "p2"):
            n = r[k]["name"]
            if " / " not in n:
                names[slugify(n)] = n
    # prioridade: quem as pessoas pesquisam no Google, depois os mais vistos no site, depois quem jogou mais recentemente
    order = sorted(names, key=lambda s: (s not in searched, -(pop.get(s) or 0)))
    store, n, now = _load(BIOS, {}), 0, time.time()
    sysmsg = ("You write the short 'In 2026' paragraph of a tennis player's profile page. " + STYLE +
              " 2 or 3 sentences, at most 70 words, natural and varied (do not always start with the ranking). The list of matches is NOT complete: "
              "never count wins or losses, never say 'record', 'unbeaten' or 'won all'. Do not mention missing things. The ranking is the player's ranking NOW: "
              "write it as 'is currently ranked No. X' (never tie it to a past month). Do not start with 'In 2026' or 'In November'. Mention the current ranking, "
              "any title in titles_since, and the most notable recent result (a win over a higher-ranked player, a final, or a deep run), "
              "using 'recently' or 'in November' style time words, never 'this season'. Reply with the paragraph only.")
    for sl in order:
        if llm.remaining("low") <= 0 or n >= int(os.environ.get("BIOS_PER_RUN") or "8"):
            break
        old = store.get(sl) or {}
        f = _player_facts(names[sl], results, er)
        if not f:
            continue
        sig = f"{f['ranking']}|{len(f['recent_matches'])}|{len(f['titles_since'])}|{f['recent_matches'][-1]['date'] if f['recent_matches'] else ''}"
        if old.get("v") == VERSION and (old.get("sig") == sig or (now - (old.get("ts") or 0) < BIO_DAYS * 86400 and old.get("sig", "").split("|")[0] == str(f["ranking"]))):
            continue
        t = _clean(_ask(sysmsg, f, "bio", 300), 80, f)
        n += 1
        if t:
            store[sl] = {"text": t, "ts": now, "sig": sig, "v": VERSION}
        elif old.get("v") != VERSION:
            store.pop(sl, None)                       # texto de uma versão antiga das regras: sai do site
    _save(BIOS, store)
    print(f"IA bios: {n} pedidos, {len(store)} bios guardadas.")
    return n


# ------------------------------------------------------------------ antevisões de torneios
def previews():
    if llm.remaining("high") <= 0:
        return 0
    up = _load("upcoming.json", {}).get("matches") or []
    store = _load(PREVIEWS, {})
    today = time.strftime("%Y-%m-%d", time.gmtime())
    by = {}
    for u in up:
        t = (u.get("tp") or u.get("tournament") or "").split(" - ")[0]         # upcoming.json usa "tp"
        if t and " / " not in u["p1"]["name"]:
            by.setdefault(t, []).append(u)
    n = 0
    sysmsg = ("You write a short preview of a tennis tournament for a website about players beyond the top 100. " + STYLE +
              " 3 to 4 sentences, at most 90 words: the level (use the given level exactly) and surface, the highest-ranked players in the draw, "
              "and one or two upcoming matches worth watching (close rankings), naming their round as given. Reply with the paragraph only.")
    for t, ms in sorted(by.items(), key=lambda kv: -len(kv[1])):
        if n >= 3 or llm.remaining("high") <= 0:
            break
        if (store.get(t) or {}).get("day", "")[:7] == today[:7] and (store.get(t) or {}).get("v") == VERSION:      # uma antevisão por torneio e mês
            continue
        players = sorted({(u[k]["name"], u[k].get("rank")) for u in ms for k in ("p1", "p2") if isinstance(u[k].get("rank"), int)}, key=lambda x: x[1])[:8]
        import tournament_story
        g0, tr0 = ms[0].get("gender"), (ms[0].get("tour") or "").lower()
        lvl = ("WTA 125" if g0 == "women" else "ATP Challenger") if tr0 == "challenger" else ("ITF" if tr0 == "itf" else (ms[0].get("tag") or tr0.upper()))
        data = {"tournament": t, "level": lvl, "gender": g0, "surface": ms[0].get("surface"),
                "top_players": [{"name": a, "ranking": b} for a, b in players],
                "matches": [{"p1": u["p1"]["name"], "r1": u["p1"].get("rank"), "p2": u["p2"]["name"], "r2": u["p2"].get("rank"),
                             "round": tournament_story._rd(u)} for u in ms[:12]]}
        if len(players) < 3:
            continue
        txt = _clean(_ask(sysmsg, data, "preview", 400, priority="high"), 100, data)
        n += 1
        if txt:
            store[t] = {"text": txt, "day": today, "v": VERSION}
    _save(PREVIEWS, dict(sorted(store.items(), key=lambda kv: kv[1].get("day", ""))[-120:]))
    print(f"IA antevisões: {n} pedidos.")
    return n


# ------------------------------------------------------------------ relatório semanal (segunda, para o admin)
def weekly_report(force=False):
    now = dt.datetime.now(dt.timezone.utc)
    week = now.strftime("%G-W%V")
    rep = _load(REPORT, {})
    if not force and (now.weekday() != 0 or now.hour < 9 or rep.get("week") == week):
        return 0
    g = _load("gsc.json", {})
    def wk(daily, a, b):
        xs = daily[a:b] if daily else []
        return {"impressions": sum(x.get("i", 0) for x in xs), "clicks": sum(x.get("c", 0) for x in xs)}
    gs = {s: {"last_7_days": wk((g.get("by_sport") or {}).get(s, {}).get("daily") or [], -7, None),
              "previous_7_days": wk((g.get("by_sport") or {}).get(s, {}).get("daily") or [], -14, -7)} for s in ("tennis", "padel")}
    posts = _load("posts.json", {})
    cut = (now - dt.timedelta(days=7)).strftime("%Y-%m-%d")
    sent = [{"id": str(e.get("id")), "reasons": e.get("reasons"), "score": e.get("score")} for d, es in posts.items() if d >= cut
            for e in es if e.get("sent") and not e.get("skipped")]
    pp = [{"kind": e.get("kind"), "id": e.get("id")} for e in (_load("padel/data/posts.json", {}).get("queue") or [])
          if e.get("sent_ts") and e["sent_ts"] > time.time() - 7 * 86400 and not e.get("skipped")]
    data = {"google_search": gs, "top_queries": [q for q in (g.get("queries") or [])[:15]],
            "tennis_posts_sent": sent, "padel_posts_sent": pp, "ai_usage": _load(llm.USAGE_FILE, {}).get("history")}
    sysmsg = ("És o analista do Beyond100 (site e Instagram de ténis e padel fora do top 100). Escreve em português de Portugal, "
              "direto e curto, para o dono do projeto. Usa só os números do JSON. Estrutura: 1) números da semana vs anterior (com ▲▼), "
              "2) o que correu bem, 3) o que correu mal, 4) até 3 sugestões concretas. Máximo 180 palavras, sem markdown além de quebras de linha.")
    txt = _ask(sysmsg, data, "weekly-report", 900, priority="high")
    if not txt:
        return 1
    rep = {"week": week, "ts": time.time(), "text": txt.strip()[:2500]}
    _save(REPORT, rep)
    print("IA: relatório semanal escrito.")
    return 1


def newsletter_intro(d):
    """Abertura do editor da newsletter (2-3 frases), só com os dados da semana. Fica guardada por semana em previews_ai.json
    (refeita se entretanto houver mais resultados). Sem IA ou sem margem devolve None e a newsletter sai sem ela."""
    if not llm.key() or llm.provider() != "gemini":
        return None
    store = _load(PREVIEWS, {})
    k = f"_nl_{d.get('date', '')[:4]}w{d.get('week')}"
    old = store.get(k) or {}
    if old.get("n") == d.get("n_results") and old.get("v") == VERSION and old.get("text"):
        return old["text"]
    if llm.remaining("low") < 1:
        return None
    facts = {"champions": [{"name": c["name"], "ranking": c.get("rank"), "tournament": c.get("t"), "beat_in_final": c.get("loser")}
                           for c in (d.get("champs") or [])[:8]],
             "champions_outside_top_100": [c["name"] for c in d.get("beyond") or []],
             "upsets": [{"winner": u["w"], "winner_ranking": u["wr"], "loser": u["l"], "loser_ranking": u["lr"], "tournament": u.get("t")}
                        for u in d.get("upsets") or []],
             "ranking_climbers": [{"name": x.get("n") or x.get("name"), "tour": lg.upper(), "ranking": x.get("r"), "previous": x.get("prev")}
                                  for lg, xs in (d.get("climb") or {}).items() for x in xs],
             "padel_champions": [{"pair": c.get("pair"), "tournament": c.get("t"), "category": c.get("cat")} for c in d.get("pchamps") or []]}
    if not facts["champions"] and not facts["padel_champions"]:
        return None
    sys_ = (STYLE + " You write the opening lines of Beyond100's weekly newsletter, which follows tennis players outside the top 100 "
            "(Challengers, ITF, WTA 125) and pro padel. Write 2 or 3 short sentences, at most 60 words, that tell the reader the week's "
            "main stories, starting with the most remarkable one (a champion ranked outside the top 100 beats everything else). "
            "Do not greet the reader, do not sign off, do not list every champion.")
    t = _clean(_ask(sys_, facts, "newsletter_intro", max_tokens=300) or "", max_words=70, facts=facts)
    if not t:
        return None
    store[k] = {"text": t, "n": d.get("n_results"), "v": VERSION, "at": time.strftime("%Y-%m-%d %H:%M")}
    _save(PREVIEWS, store)
    return t


def main():
    if not llm.key() or llm.provider() != "gemini":
        print("IA de fundo: sem GEMINI_API_KEY (os textos de fundo só usam o nível gratuito do Gemini).")
        return
    try:
        import result_card as rc
        results = rc.load_results()
    except Exception as e:
        print("IA de fundo: sem resultados:", type(e).__name__)
        results = []
    for fn in (weekly_report, previews, lambda: bios(results)):
        try:
            fn()
        except Exception as e:
            print("IA de fundo falhou:", getattr(fn, "__name__", "bios"), type(e).__name__, str(e)[:120])


if __name__ == "__main__":
    if "--report" in sys.argv:
        weekly_report(force=True)
    else:
        main()
