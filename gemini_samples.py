"""Teste (25/11/2026): exemplos reais do Gemini para o Afonso ver antes de ativar. Só grava gemini_samples.json (repositório privado)."""
import json, time
import llm, ai_texts, captions
import result_card as rc, os
import json as _j
try:
    os.remove(llm.USAGE_FILE)
except OSError:
    pass
out = {"ts": time.time(), "provider": llm.provider()}
R = rc.load_results()
er = ai_texts._load("espn_rank.json", {})
names = []
for r in sorted(R, key=lambda r: r.get("date", ""), reverse=True):
    for k in ("p1", "p2"):
        n = r[k]["name"]
        if " / " not in n and n not in names:
            names.append(n)
bios = []
sysmsg = ("You write the short 'In 2026' paragraph of a tennis player's profile page. " + ai_texts.STYLE +
          " 2 or 3 sentences, at most 70 words. Do not mention missing things (no 'no titles'). Mention the record and titles SINCE the date in record_since (say 'since <month>' or 'in recent weeks', never 'this season'), the current ranking, and the most notable recent result. Reply with the paragraph only.")
for n in names[:15]:
    f = ai_texts._player_facts(n, R, er)
    if f:
        bios.append({"name": n, "facts": f, "text": ai_texts._ask(sysmsg, f, "bio-test", 300)})
    if len(bios) >= 3:
        break
out["bios"] = bios
fin = [r for r in R if r.get("winner") in (1, 2) and " / " not in r["p1"]["name"]][:1]
if fin:
    r = fin[0]
    facts = {"tournament": r.get("tournament"), "round": r.get("round"), "date": r.get("date"), "surface": r.get("surface"),
             "p1": r["p1"], "p2": r["p2"], "games": r["games"], "winner": r["winner"]}
    try:
        out["caption"] = {"facts": facts, "text": captions.make_caption("result", facts)}
    except Exception as e:
        out["caption"] = {"error": f"{type(e).__name__}: {e}"}
for k, fn in (("previews", ai_texts.previews), ("report", lambda: ai_texts.weekly_report(force=True))):
    try:
        fn()
    except Exception as e:
        out[k + "_error"] = str(e)
out["previews"] = ai_texts._load(ai_texts.PREVIEWS, {})
out["report"] = ai_texts._load(ai_texts.REPORT, {})
out["usage"] = ai_texts._load(llm.USAGE_FILE, {})
json.dump(out, open("gemini_samples.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Exemplos guardados:", len(bios), "bios | pedidos:", out["usage"].get("calls"), "| limitado:", out["usage"].get("limited"))
