"""Legendas de Instagram geradas com a Anthropic API (Haiku).

Regras de segurança:
- a IA só recebe dados públicos do cartão e é instruída a não inventar nada;
- todo o número da legenda tem de existir nos dados; se não, usa-se a legenda-modelo;
- sem chave ou com erro de rede, usa-se a legenda-modelo (o workflow nunca falha por causa disto).
"""
import json
import os
import re

import requests

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("CAPTION_MODEL") or "claude-sonnet-5-5"
FALLBACK_MODEL = "claude-haiku-5-5"
SYSTEM = (
    "You write Instagram captions for Beyond100, a tennis account about the players and tournaments beyond the top 100 "
    "(Challengers, ITF, WTA and the Tour). "
    "Voice: write like a real person who follows tennis closely and is telling a friend what just happened. Normal, complete sentences, "
    "plain everyday words, a little emotion only when the result deserves it (e.g. 'Big one for him'). It must not read like an ad, a press release or AI. "
    "Banned style: runs of short three-word sentences, slogan lines ('One trophy. Two names.'), 'No more scrolling', em dashes, rhetorical build-ups, "
    "and words like stunning, incredible, masterclass, epic, statement, 'what a'. "
    "Format: 2 or 3 lines in total (the first says what happened, in plain words; then the one or two most interesting details from the JSON, such as the ranking, "
    "the round, the comeback, the path through the draw). Ask a question only when it comes naturally (about one post in three), never a generic one. "
    "Then 3-4 specific hashtags (player surname, tournament, circuit; each a complete word; the brand tag is #Beyond100, never #Beyond; no generic ones like #TennisLife). "
    "0 or 1 emoji. English. Vary how you open.\n"
    "Every line must add information: no filler about opponents or matches (e.g. 'a tight result against a ... who didn't make it easy'). "
    "web_context (if present) holds verified background facts from the web: use at most one or two, paraphrase them lightly, never add details beyond them. "
    "Hard rules: use ONLY facts in the JSON. Never invent names, scores, rankings, quotes, dates, injuries, history or anything about a "
    "player's career or personal life that is not in the JSON. If a ranking looks surprising, just state it, do not explain why. "
    "When facts.score exists, write the score exactly as in facts.score (same sets, same order). "
    "Every number you write must appear literally in the JSON. Never compute anything (no differences, totals, ordinals like 'third in a row', "
    "percentages or counts). Use ranking_gap if given, otherwise do not mention gaps. "
    "Do not describe events that are not in the JSON: no match points, breaks, aces, serving, crowd or emotions. "
    "For kind=news: tell the story in your own words from facts.summary (do not add anything beyond it), keep a neutral and respectful tone "
    "(especially for health or retirement news, with no speculation), and on the last line before the hashtags write 'Source: ' followed by facts.source_names. "
    "For kind=rising_week: a carousel of the week's biggest ranking climbers; mention each player once with places_gained, keep it short, "
    "say the rankings are the ones we recorded in their matches (never call them official live rankings), ask who climbs next. "
    "For kind=history: a throwback to a past season (facts.year); tell it as 'this week in <year>' using only the facts, and if "
    "facts.career_best is given, say the player later reached that career-high ranking. End with 'Data: Tennis Abstract' on its own line before the hashtags. "
    "For kind=road: the weekly 'Road to the Top 100' list (players ranked just outside the top 100, men and women); name two or three of them "
    "with their ranking and, if given, points_to_top100 (points behind No. 100; 0 means level on points); these are the official rankings of the week; ask who gets in first. "
    "For kind=power: our weekly Power Ranking of the best form outside the top 100 (last 14 days); name the number 1 of each list with their "
    "record (won-lost) and titles if any; say it is our own ranking; ask readers who is missing from the list. "
    "For kind=climbers: the biggest jumps of the week in the OFFICIAL ATP and WTA rankings (top 150); name the top climber of each tour with "
    "previous_ranking, ranking and places_gained (and age if 21 or under), mention anyone who enters the top 100, ask who climbs next. "
    "For kind=qualwatch: this week's players (men and women, ATP and WTA) who came through qualifying and keep winning in the main draw; "
    "name the best two or three with their tournament and main_draw_wins and say who is still_in; celebrate the grind; ask who goes furthest. "
    "For kind=records: the month's records beyond the top 100 (facts.leaders, men and women); highlight two or three leaders with their numbers, "
    "say they come from the matches we tracked, and ask who will lead next month. "
    "For kind=preview: the match has NOT been played yet. Never say or hint who won or will win, never predict. Build anticipation from the "
    "facts (rankings, countries, the title at stake, the tournament level, and head_to_head if present, citing it as the official record), then ask readers to pick a winner in the comments. "
    "Output the caption text only."
)


SPEND_FILE = "spend.json"
# preços estimados em USD por milhão de tokens (entrada, saída); a pesquisa web custa ~0,01 USD cada. É uma ESTIMATIVA: o valor real está na Console.
PRICES = {"haiku": (1.0, 5.0), "sonnet": (3.0, 15.0), "opus": (5.0, 25.0)}
SEARCH_USD = 0.01


def _spend_load():
    try:
        with open(SPEND_FILE, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _spend_save(d):
    try:
        d["days"] = dict(sorted((d.get("days") or {}).items())[-120:])
        with open(SPEND_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
    except OSError:
        pass


FEATURE = "other"         # funcionalidade que está a gastar agora (para o gasto por funcionalidade no admin)


def _record(model, usage, feature=None):
    """Soma ao gasto estimado do dia (spend.json) os tokens e pesquisas desta chamada, também por funcionalidade."""
    try:
        import time
        ip, op = next((v for k, v in PRICES.items() if k in (model or "")), PRICES["sonnet"])
        u = usage or {}
        searches = int(((u.get("server_tool_use") or {}).get("web_search_requests")) or 0)
        usd = (u.get("input_tokens", 0) * ip + u.get("output_tokens", 0) * op) / 1e6 + searches * SEARCH_USD
        d = _spend_load()
        day = d.setdefault("days", {}).setdefault(time.strftime("%Y-%m-%d", time.gmtime()), {"usd": 0.0, "calls": 0, "searches": 0})
        day["usd"] = round(day["usd"] + usd, 5)
        day["calls"] += 1
        day["searches"] += searches
        by = day.setdefault("by", {})
        f = feature or FEATURE
        by[f] = round(by.get(f, 0) + usd, 5)
        _spend_save(d)
    except Exception:
        pass


def _credit_check(r):
    """Se a Anthropic recusar por falta de saldo, guarda o alerta (aparece no admin e dispara o aviso por email)."""
    try:
        if r.status_code in (400, 402, 403) and "credit balance" in (r.text or "").lower():
            import time
            d = _spend_load()
            d["credit_error"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _spend_save(d)
            print("ALERTA: sem saldo na Anthropic (credit balance too low). Carrega fundos na Console.")
    except Exception:
        pass


def _name(p):
    return (p or {}).get("name", "")


def fallback(kind, facts):
    tag = "#tennis #challengertennis #beyond100"
    if kind == "final":
        w = facts.get("winner")
        if w in (1, 2):
            win, los = facts["p%d" % w], facts["p%d" % (3 - w)]
            score = "  ".join(f"{a}-{b}" for a, b in zip(facts["games"][w - 1], facts["games"][2 - w]))
            why = facts.get("reasons") or []
            extra = ("Upset alert. " if "upset" in why else "") + ("A comeback win. " if "comeback" in why else "")
            stage = {"final": "in the final", "semifinal": "in the semifinals", "quarterfinal": "in the quarterfinals"}
            where = next((stage[r] for r in why if r in stage), "")
            return (f"{extra}{_name(win)} beats {_name(los)} {score} {where}.\n{facts.get('tournament', '')}\n"
                    f"Who impressed you most today?\n{tag}").replace("  ", " ").replace(" .", ".").strip()
    if kind == "upset":
        return (f"{facts.get('headline', 'Upset alert.')}\n{facts.get('context', '')}\n"
                f"Did you see this coming?\n{tag} #upset").strip()
    if kind == "weekly":
        fin = facts.get("finals") or []
        lines = [f"{f['winner']} won {f['tournament']}." for f in fin[:2]]
        return ("The week beyond the top 100.\n" + " ".join(lines) + f"\n{facts.get('matches', 0)} matches tracked. "
                f"Which result surprised you most?\n{tag} #weeklyrecap").strip()
    if kind == "news":
        src = ", ".join(facts.get("source_names") or [])
        return (f"{facts.get('headline', '')}\n{facts.get('summary', '')}\n" + (f"Source: {src}\n" if src else "") +
                f"What do you make of it?\n#tennis #beyond100 #tennisnews").strip()
    if kind == "records":
        L = facts.get("leaders") or {}
        bits = [f"{v['name']} ({v['value']} {k})" for g in ("men", "women") for k, v in list((L.get(g) or {}).items())[:1]]
        return (f"The month in records: {facts.get('month', '')}.\n" + " · ".join(bits) +
                "\nFrom the matches we tracked.\nWho leads next month?\n" + tag + " #records").strip()
    if kind == "climbers":
        bits = [f"{x['name']} (#{x['previous_ranking']} to #{x['ranking']}, +{x['places_gained']})" for lg in ("atp", "wta") for x in (facts.get(lg) or [])[:1]]
        return ("Climbers of the week in the official rankings.\n" + " · ".join(bits) + "\nWho climbs next?\n" + tag + " #rankings").strip()
    if kind == "qualwatch":
        ps = facts.get("players") or []
        return ("Qualifier watch: through qualifying and still winning.\n" + " · ".join(f"{p['name']} ({p['tournament']}, {p['main_draw_wins']} win{'s' if p['main_draw_wins'] > 1 else ''})" for p in ps[:4])
                + "\nWho goes furthest?\n" + tag + " #qualifiers").strip()
    if kind in ("road", "power"):
        first = [(g, (facts.get(g) or [{}])[0]) for g in ("men", "women") if facts.get(g)]
        bits = [f"{x.get('name', '')} (#{x.get('ranking', '')})" for _, x in first]
        title = "Road to the Top 100: knocking on the door." if kind == "road" else "Power Ranking: the best form outside the top 100."
        q = "Who gets in first?" if kind == "road" else "Who is missing from the list?"
        return (title + "\n" + " · ".join(bits) + f"\n{q}\n{tag} #" + ("roadtotop100" if kind == "road" else "powerranking")).strip()
    if kind == "rising_week":
        rs = facts.get("risers") or []
        lines = [f"{x['name']}: +{x['places_gained']} (#{x['rank_before']} to #{x['rank_now']})" for x in rs]
        return ("Rising this week.\n" + "\n".join(lines) + "\nRankings as recorded in their matches.\nWho climbs next?\n" + tag + " #rising").strip()
    if kind == "history":
        cb = facts.get("career_best")
        return (f"This week in {facts.get('year', '')}: {facts.get('winner', '')} won {facts.get('tournament', '')}, beating "
                f"{facts.get('runner_up', '')} {facts.get('score', '')}." + (f"\nCareer-high since then: #{cb}." if cb else "") +
                f"\nDid you remember this one?\nData: Tennis Abstract\n{tag} #throwback").strip()
    if kind == "preview":
        a, b = facts.get("player_1") or {}, facts.get("player_2") or {}
        return (f"Final day at {facts.get('tournament', '')}.\n{a.get('name', '')} vs {b.get('name', '')} for the title.\n"
                f"Who lifts the trophy? Drop your pick below.\n{tag} #final").strip()
    if kind == "rising":
        return f"A new name inside the top 100.\nWho's next?\n{tag} #rising"
    return f"{tag}"


BANNED = re.compile(r"match[- ]?points?|break[- ]?points?|\baces?\b|injur|retire|cramp|crowd|tears|emotional|"
                    r"career[- ]high|first[- ]ever|record|streak|unbeaten|saved|saves\b|serv(e|ing|ed)\b", re.I)


def _numbers(text):
    return set(re.findall(r"\d+", text))


LINK_LINE = "Full match, draw and highlights: link in bio 🔗"
FOLLOW_LINE = "Follow @beyond100.tennis for the stories beyond the top 100."


def _finish(text, kind=""):
    """Acrescenta 'Full results: link in bio' antes das hashtags (uma só vez)."""
    link_line = {"news": "More tennis beyond the top 100: link in bio 🔗", "preview": "Live score and result: link in bio 🔗"}.get(kind, LINK_LINE)
    text = (text or "").strip()
    if "link in bio" in text.lower():
        return text
    follow = FOLLOW_LINE if "follow @beyond100" not in text.lower() else ""
    add = link_line + ("\n" + follow if follow else "")
    lines = text.split("\n")
    if lines and lines[-1].lstrip().startswith("#"):
        return "\n".join(lines[:-1]).rstrip() + "\n" + add + "\n\n" + lines[-1]
    return text + "\n" + add


def make_caption(kind, facts):
    global FEATURE
    FEATURE = f"caption-{kind}"
    return _finish(_make_caption(kind, facts), kind)


def _ask(key, payload, extra="", model=None):
    model = model or MODEL
    def call(model):
        return requests.post(
            API_URL,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model, "max_tokens": 1500, "system": SYSTEM + extra,
                  "messages": [{"role": "user", "content": payload}]},
            timeout=40,
        )
    r = call(model)
    if r.status_code in (400, 404) and model != FALLBACK_MODEL:       # modelo indisponível: tenta o modelo mais simples
        print(f"Legenda: modelo {model} indisponível ({r.status_code}), a usar {FALLBACK_MODEL}.")
        r = call(FALLBACK_MODEL)
    _credit_check(r)
    r.raise_for_status()
    data = r.json()
    _record(data.get("model") or model, data.get("usage"))
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
    if not text:        # diagnóstico: resposta sem texto (ex.: tokens gastos a "pensar")
        print("Legenda: resposta vazia | stop_reason:", data.get("stop_reason"),
              "| blocos:", [b.get("type") for b in data.get("content", [])], "| uso:", data.get("usage"))
    return text


WEB_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 2}
RESEARCH_SYSTEM = (
    "You are a fact-checking tennis researcher. Given a match, use web search (at most 2 searches) to find up to 3 verified, newsworthy facts that give the match "
    "context (for example: a return after a long absence, a notable ranking move, a title or milestone, a rivalry). "
    "Rules: first make sure you have the RIGHT players (check country and age against the JSON; many players share names). "
    "Only use facts stated in the search results, preferably from official (ATP, WTA, ITF, tournament) or major news sources, and recent. "
    "No rumours, opinions, predictions or personal-life details. Each fact must be one plain sentence of at most 22 words, in English, "
    "paraphrased (never copy sentences). Prefer facts that explain WHY this result matters. "
    "If nothing solid and relevant is found, return an empty list. "
    'Reply with JSON only: {"facts":[{"text":"...","source":"https://..."}]}'
)


def _research(key, facts):
    """Pesquisa na web (ferramenta web_search da Anthropic) de contexto verificável para o jogo. Qualquer falha -> sem contexto."""
    if os.environ.get("CAPTION_WEB_CONTEXT", "1").strip() in ("0", "no", "false", "off"):
        return []
    brief = {k: facts.get(k) for k in ("tournament", "round", "date", "surface", "p1", "p2", "games", "winner", "level", "tag") if facts.get(k) is not None}
    try:
        r = requests.post(
            API_URL,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": MODEL, "max_tokens": 1500, "system": RESEARCH_SYSTEM, "tools": [WEB_TOOL],
                  "messages": [{"role": "user", "content": json.dumps(brief, ensure_ascii=False)}]},
            timeout=90,
        )
        _credit_check(r)
        if r.status_code >= 400:
            print("Pesquisa web indisponível:", r.status_code, r.text[:160].replace("\n", " "))
            return []
        _record(MODEL, r.json().get("usage"), "web-context")
        text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
        m = re.search(r"\{.*\}", text, re.S)
        items = (json.loads(m.group(0)).get("facts") if m else []) or []
    except Exception as e:
        print("Pesquisa web falhou:", type(e).__name__, str(e)[:120])
        return []
    out = []
    for it in items[:3]:
        t, src = (it.get("text") or "").strip(), (it.get("source") or "").strip()
        if t and src.startswith("http") and len(t.split()) <= 30:
            out.append({"text": t, "source": src})
            print("Contexto web:", t, "|", src)
    return out


H2H_SOURCES = {"atptour.com": "ATP Tour", "wtatennis.com": "WTA", "itftennis.com": "ITF"}
H2H_SYSTEM = (
    "You look up the official head-to-head record between two professional tennis players. Use web search (at most 2 searches) and ONLY "
    "accept the head-to-head page or player page of atptour.com (men) or wtatennis.com (women) or itftennis.com. First make sure both players "
    "are the right people (country and gender given in the JSON). Count only main-tour/Challenger/ITF singles matches as the official site does. "
    'Reply with JSON only: {"found":true,"p1_wins":0,"p2_wins":0,"source":"https://..."} or {"found":false}. '
    "If the official page is not in the results, or you are not sure, reply {\"found\":false}. Never guess."
)


def head_to_head(p1, p2, gender=None):
    """Confronto direto OFICIAL (ATP/WTA/ITF) por pesquisa web. Devolve {p1_wins, p2_wins, source, source_name} ou None.
    O código confirma que a fonte é um site oficial; sem certeza, não há H2H."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or os.environ.get("PREVIEW_H2H", "1").strip() in ("0", "no", "false", "off"):
        return None
    brief = {"player_1": p1, "player_2": p2, "gender": gender}
    try:
        r = requests.post(API_URL, headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": MODEL, "max_tokens": 800, "system": H2H_SYSTEM, "tools": [WEB_TOOL],
                                "messages": [{"role": "user", "content": json.dumps(brief, ensure_ascii=False)}]}, timeout=90)
        _credit_check(r)
        if r.status_code >= 400:
            print("H2H indisponível:", r.status_code)
            return None
        _record(MODEL, r.json().get("usage"), "h2h")
        text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
        m = re.search(r"\{.*\}", text, re.S)
        d = json.loads(m.group(0)) if m else {}
    except Exception as e:
        print("H2H falhou:", type(e).__name__)
        return None
    if not d.get("found"):
        print("H2H: sem página oficial encontrada.")
        return None
    src = str(d.get("source") or "")
    host = re.sub(r"^www\.", "", (re.match(r"https?://([^/]+)", src) or [None, ""])[1].lower())
    name = next((v for k, v in H2H_SOURCES.items() if host == k or host.endswith("." + k)), None)
    a, b = d.get("p1_wins"), d.get("p2_wins")
    if not name or not isinstance(a, int) or not isinstance(b, int) or a < 0 or b < 0 or a + b > 60:
        print("H2H recusado (fonte não oficial ou valores inválidos):", src[:80])
        return None
    print(f"H2H oficial: {a}-{b} | {src}")
    return {"p1_wins": a, "p2_wins": b, "source": src, "source_name": name}


HEAD_SYSTEM = (
    "You write ONE short line for a tennis result card, the way a tennis fan or a good beat writer would say it out loud. "
    "2 to 6 words, English, no player names, no emoji, no hashtags, no quotes, no final period. "
    "Say something specific from the JSON (the ranking gap, the comeback, the round, the age, who they beat), in plain words. "
    "Use only facts from the JSON; no numbers unless that exact number is in the JSON. Never invent events (no match points, injuries, records, streaks). "
    "Do NOT write tabloid headlinese: never use crown, crowned, seize, claim, storm, cruise, outsider, clinch, triumph, glory, reign, "
    "masterclass, dominant, statement, stuns, shock, heads to, dream run, fairytale, sends a message. "
    "Do NOT use the pattern '<something> in <city>'. "
    "Good: 'Down a set, still won it', 'Beat the No. 17 in the final', 'Two tie-breaks, one trophy', 'Nobody saw that coming', "
    "'From qualifying to the title', 'Not bad for a qualifier'. "
    "Output the line only."
)
HEAD_BANNED = re.compile(r"crown|seiz|claim|storm|cruis|outsider|clinch|triumph|glory|reign|masterclass|dominan|statement|stun|shock|"
                         r"heads? to|dream run|fairytale|sends? a message|\bin [A-Z][a-z]+$", re.I)


def card_headline(facts):
    """Título editorial curto para o cartão (CARD_STYLE=2). Devolve None se a IA falhar ou quebrar as regras (usa-se a frase fixa)."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    f = {k: v for k, v in dict(facts).items() if not str(k).startswith("_")}
    payload = json.dumps(f, ensure_ascii=False)
    try:
        r = requests.post(API_URL, headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": FALLBACK_MODEL, "max_tokens": 400, "system": HEAD_SYSTEM,
                                "messages": [{"role": "user", "content": payload}]}, timeout=30)
        _credit_check(r)
        if r.status_code >= 400:
            return None
        data = r.json()
        _record(data.get("model") or FALLBACK_MODEL, data.get("usage"), "headline")
        t = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip().strip('"\'').rstrip(".")
    except Exception:
        return None
    names = " ".join(str((f.get(k) or {}).get("name", "")) for k in ("p1", "p2") if isinstance(f.get(k), dict)).lower().split()
    bad = (not t or len(t.split()) > 6 or len(t) > 40 or "\n" in t or "#" in t or (_numbers(t) - _numbers(payload))
           or BANNED.search(t) or HEAD_BANNED.search(t) or any(len(n) > 3 and n in t.lower().split() for n in names))
    if bad:
        print("Título do cartão recusado:", t[:60])
        return None
    print("Título do cartão:", t)
    return t


def _make_caption(kind, facts):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return fallback(kind, facts)
    want = None
    if kind == "final" and facts.get("winner") in (1, 2) and facts.get("games"):
        w = facts["winner"]
        want = "  ".join(f"{a}-{b}" for a, b in zip(facts["games"][w - 1], facts["games"][2 - w]))
        facts = dict(facts, score=want)          # resultado já pronto, na ordem dos sets e do ponto de vista do vencedor
    facts = dict(facts)
    interest = facts.pop("_interest", None)       # pontuação de interesse do jogo (não vai para a IA)
    try:
        web_min = float(os.environ.get("CAPTION_WEB_MIN_SCORE") or 10)
    except ValueError:
        web_min = 10.0
    if kind == "final" and (interest is None or interest >= web_min):
        web = _research(key, facts)
        if web:
            facts = dict(facts, web_context=[w["text"] for w in web])       # só o texto vai para a legenda; as fontes ficam no log
    try:
        lite_below = float(os.environ.get("CAPTION_LITE_BELOW") or 0)       # 0 = desligado: posts com interesse abaixo disto usam o modelo mais barato
    except ValueError:
        lite_below = 0.0
    model = FALLBACK_MODEL if (kind == "final" and interest is not None and lite_below and interest < lite_below) else MODEL
    payload = json.dumps({"kind": kind, "facts": facts}, ensure_ascii=False)
    allowed = _numbers(payload) | {"100"}          # "100" faz parte da marca (#beyond100, "beyond the top 100"), não é um facto
    extra = ""
    for attempt in (1, 2):                      # uma segunda tentativa, mais restrita, antes de usar o modelo simples
        try:
            text = _ask(key, payload, extra, model)
        except Exception as e:  # rede, quota, chave inválida...
            print("Legenda: IA indisponível, a usar modelo:", type(e).__name__)
            return fallback(kind, facts)
        if not text:
            print(f"Legenda (tentativa {attempt}): resposta vazia.")
            continue
        bad = sorted(_numbers(text) - allowed)
        banned = sorted({m.group(0).lower() for m in BANNED.finditer(text or "")} - set(BANNED.findall(payload.lower()) if False else []))
        banned = [w for w in banned if w not in payload.lower()]
        if want and re.sub(r"\s+", " ", want) not in re.sub(r"\s+", " ", text):
            bad = bad + [f"score must be exactly '{want}'"]          # o resultado da legenda tem de ser igual ao do cartão
        elif text and not bad and not banned:
            return text
        bad = bad + banned
        print(f"Legenda (tentativa {attempt}): números fora dos dados {bad}.")
        extra = (" IMPORTANT: your previous answer used numbers not in the JSON (" + ", ".join(bad) +
                 "). Rewrite without them; do not do any arithmetic. If a score is given in facts.score, copy it exactly, set by set, in the same order.")
    print("Legenda: a usar modelo simples.")
    return fallback(kind, facts)


def _mention(text, handle, tournament=None):
    """Acrescenta a menção ao jogador (linha própria, antes das hashtags). Só se o perfil estiver na lista verificada."""
    parts = [x for x in [(f"🎾 {handle}" if handle else ""), (f"🏟 {tournament}" if tournament else "")] if x and x.split(" ", 1)[1].lower() not in (text or "").lower()]
    if not parts:
        return text
    lines = text.rstrip().split("\n")
    line = "  ".join(parts)
    if lines and lines[-1].lstrip().startswith("#"):
        return "\n".join(lines[:-1]).rstrip() + "\n" + line + "\n\n" + lines[-1]
    return text.rstrip() + "\n" + line


def save_pending(png_path, kind, facts, mention=None, tournament=None):
    """Guarda os factos para a legenda ser escrita só quando o post for mesmo publicado (poupa IA nos cartões que ficam na fila).
    O ficheiro .tag (perfis a marcar) é escrito já, como em save_caption."""
    base = os.path.splitext(png_path)[0]
    with open(base + ".facts.json", "w", encoding="utf-8") as f:
        json.dump({"kind": kind, "facts": facts, "mention": mention, "tournament": tournament}, f, ensure_ascii=False, default=str)
    if mention or tournament:
        with open(base + ".tag", "w", encoding="utf-8") as f:
            f.write(((mention or "").split() or [""])[0].lstrip("@").strip() + "\n" + (tournament or "").lstrip("@").strip())
    return base + ".facts.json"


def caption_from_pending(facts_path):
    """Escreve a legenda a partir dos factos guardados por save_pending. Devolve o texto (ou "" se não houver factos)."""
    try:
        with open(facts_path, encoding="utf-8") as f:
            p = json.load(f)
    except (OSError, ValueError):
        return ""
    return _mention(make_caption(p["kind"], p["facts"]), p.get("mention"), p.get("tournament"))


def save_caption(png_path, kind, facts, mention=None, tournament=None):
    path = os.path.splitext(png_path)[0] + ".txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_mention(make_caption(kind, facts), mention, tournament))
    if mention or tournament:     # perfis a marcar na fotografia (sem arroba): 1.ª linha jogador, 2.ª torneio; lido pelo publisher
        with open(os.path.splitext(png_path)[0] + ".tag", "w", encoding="utf-8") as f:
            f.write(((mention or "").split() or [""])[0].lstrip("@").strip() + "\n" + (tournament or "").lstrip("@").strip())
    return path
