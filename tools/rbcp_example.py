"""Exemplo (só para o Afonso ver): cartão do resultado da final masculina do Dubai P1 com a foto do Red Bull Content Pool
e a legenda com crédito e marcações. Corre no GitHub; a imagem fica no repositório privado (não passa por IA)."""
import json, os, sys
sys.path.insert(0, os.getcwd())
from padel import cards, rbcp, posts
ms = json.load(open("padel/data/matches/750.json"))
m = next(x for x in ms if x.get("round") == 1 and x.get("draw") == "main" and (x.get("category") or "men") == "men" and x.get("winner"))
w = m["winner"]; l = "team_2" if w == "team_1" else "team_1"
W, L = m["players"][w], m["players"][l]
ph = posts.best_photo(W, "Premier Padel Dubai P1")
print("foto:", {k: v for k, v in (ph or {}).items() if k != "path"})
sets = [(s[w], s[l]) for s in m["score"]]
os.environ["PADEL_RESULT_STYLE"] = "C"
cards.result_card({"kicker": "Champions", "level": "P1", "round": "Final", "tournament": "Dubai P1", "city": "Dubai", "date": "15 NOV 2026",
                   "winners": W, "losers": L, "sets": sets, "photo": ph, "ranks": {}, "note": ""}, "rbcp/exemplo.jpg")
os.environ.pop("ANTHROPIC_API_KEY", None)
e = {"id": "x", "kind": "result", "rbcp": [ph["rbcp"]], "score": 0, "facts": {"tournament": "Premier Padel Dubai P1",
     "winners": [{"name": p["name"]} for p in W], "losers": [{"name": p["name"]} for p in L],
     "score": " ".join(f"{a}-{b}" for a, b in sets), "round": "Final"}}
print("legenda:\n" + posts.caption(e))
# v2
