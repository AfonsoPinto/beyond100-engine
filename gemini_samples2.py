"""Teste 2 (26/11/2026): o resto dos usos da IA com o Gemini. Só grava gemini_samples2.json (repositório privado)."""
import json, os, time, traceback
try:
    os.remove("llm_usage.json")
except OSError:
    pass
import llm, ai_texts, captions, news_scan
import result_card as rc
out = {"ts": time.time()}
def run(k, fn):
    try:
        out[k] = fn()
    except Exception as e:
        out[k] = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-600:]}
R = rc.load_results()
fin = next((r for r in R if (r.get("round") or "").split(" - ")[-1].lower() in ("final", "semi-finals") and " / " not in r["p1"]["name"]), R[0])
facts = {"tournament": fin.get("tournament"), "round": fin.get("round"), "date": fin.get("date"), "surface": fin.get("surface"), "level": fin.get("tour"),
         "p1": fin["p1"], "p2": fin["p2"], "games": fin["games"], "winner": fin["winner"], "_interest": 11}
run("final_caption", lambda: {"facts": {k: v for k, v in facts.items() if k != "_interest"}, "text": captions.make_caption("final", facts)})
run("web_research", lambda: captions._research(llm.key(), {k: v for k, v in facts.items() if k != "_interest"}))
run("card_headline", lambda: captions.card_headline(facts))
run("head_to_head", lambda: captions.head_to_head(fin["p1"]["name"], fin["p2"]["name"], fin.get("gender")))
run("news", lambda: news_scan.ask("Find one verified tennis news item from the last 48 hours about a player ranked 100-300. Reply JSON only: {\"items\":[{\"title\":\"...\",\"source\":\"https://...\"}]}", "Go.", 2, 800, feature="news-test"))
def padel():
    import padel.posts as pp
    q = pp.qload() if hasattr(pp, "qload") else json.load(open("padel/data/posts.json"))
    e = next(x for x in reversed(q["queue"]) if x.get("kind") == "result")
    return {"id": e["id"], "text": pp.caption(dict(e))}
run("padel_caption", padel)
run("previews_n", lambda: (ai_texts.previews(), ai_texts._load(ai_texts.PREVIEWS, {}))[1])
def bios_render():
    ai_texts.bios(R)
    b = ai_texts._load(ai_texts.BIOS, {})
    import extras, webapp
    sl = next(iter(b), None)
    if not sl:
        return "sem bios"
    name = next(r[k]["name"] for r in R for k in ("p1", "p2") if webapp.slugify(r[k]["name"]) == sl)
    html = extras.profile_block({"name": name, "country": ""}, [], None, False)
    return {"player": name, "bio": b[sl]["text"], "in_html": b[sl]["text"][:40] in html.replace("&#x27;", "'")}
run("bios_render", bios_render)
out["usage"] = ai_texts._load(llm.USAGE_FILE, {})
json.dump(out, open("gemini_samples2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("Teste 2 feito | pedidos:", out["usage"].get("calls"), "| erros:", [k for k, v in out.items() if isinstance(v, dict) and v.get("error")])
