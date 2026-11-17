"""Descarrega sons reais CC0 do Freesound (pré-visualizações HQ, só com a chave da API) para reels/sfx/<categoria>_<n>.wav.
CC0 = domínio público: uso comercial livre, sem crédito obrigatório (a lista de origem fica em reels/sfx/FONTES.md na mesma).
Uso (no GitHub, com o secret FREESOUND_API_KEY):  python -m reels.sfx_fetch reels/sfx"""
import json, os, subprocess, sys, urllib.parse, urllib.request

KEY = os.environ["FREESOUND_API_KEY"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "reels/sfx"
# categoria: (pesquisas por ordem de preferência, duração mín-máx em s, quantos)
CATS = {
    "hit_tennis": (["tennis racket hit ball", "tennis ball hit", "tennis serve"], (0.08, 2.5), 5),
    "hit_padel": (["padel ball hit", "padel racket", "paddle ball hit", "tennis racket hit ball"], (0.08, 2.5), 5),
    "bounce": (["tennis ball bounce", "ball bounce hard court"], (0.05, 2.0), 4),
    "bounce_clay": (["tennis ball bounce clay", "ball bounce dirt", "tennis ball bounce"], (0.05, 2.0), 3),
    "glass": (["ball hit glass", "padel glass", "ball hits window"], (0.05, 2.5), 4),
    "squeak": (["sneaker squeak", "shoe squeak court", "basketball shoe squeak"], (0.1, 2.0), 5),
    "crowd": (["tennis crowd ambience", "stadium crowd murmur", "crowd ambience indoor arena"], (8, 180), 3),
    "applause": (["tennis applause", "crowd applause cheer stadium", "applause crowd"], (2, 20), 3),
    "ooh": (["crowd ooh", "crowd gasp", "crowd reaction ooh"], (0.5, 6), 2),
}
FIELDS = "id,name,username,license,duration,previews,avg_rating,num_ratings,num_downloads,url"
os.makedirs(OUT, exist_ok=True)
fontes = ["# Sons reais (Freesound, CC0 — domínio público)", "",
          "Uso comercial livre, sem crédito obrigatório. Lista para referência.", ""]

def search(q, dmin, dmax):
    flt = f'license:"Creative Commons 0" duration:[{dmin} TO {dmax}]'
    url = "https://freesound.org/apiv2/search/text/?" + urllib.parse.urlencode(
        dict(query=q, filter=flt, fields=FIELDS, sort="rating_desc", page_size=30, token=KEY))
    with urllib.request.urlopen(url, timeout=40) as r:
        return json.load(r).get("results") or []

for cat, (queries, (dmin, dmax), n) in CATS.items():
    got, seen = 0, set()
    for q in queries:
        if got >= n: break
        try: res = search(q, dmin, dmax)
        except Exception as e: print("pesquisa falhou", cat, q, e); continue
        # mais descarregados primeiro, com nota mínima quando há notas
        res.sort(key=lambda s: (-(s.get("num_downloads") or 0)))
        for s in res:
            if got >= n: break
            if s["id"] in seen or "Creative Commons 0" not in (s.get("license") or "") and "publicdomain/zero" not in (s.get("license") or ""):
                continue
            if (s.get("num_ratings") or 0) >= 3 and (s.get("avg_rating") or 0) < 3.0: continue
            seen.add(s["id"])
            mp3 = os.path.join(OUT, f"_tmp_{s['id']}.mp3"); wav = os.path.join(OUT, f"{cat}_{got}.wav")
            try:
                urllib.request.urlretrieve(s["previews"]["preview-hq-mp3"], mp3)
                af = "silenceremove=start_periods=1:start_threshold=-45dB,loudnorm=I=-16:TP=-1.5" if cat not in ("crowd",) else "loudnorm=I=-20:TP=-2"
                if cat not in ("crowd", "applause"): af += ",atrim=0:1.6,afade=t=out:st=1.3:d=0.3"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", "44100", "-af", af, wav], check=True)
                os.remove(mp3); got += 1
                fontes.append(f"- `{os.path.basename(wav)}` — \"{s['name']}\" por {s['username']} — {s['url']} (CC0)")
                print("ok", cat, s["name"], s["duration"])
            except Exception as e:
                print("falhou", s.get("name"), e)
                for f in (mp3,):
                    if os.path.exists(f): os.remove(f)
    print(cat, got, "sons")
open(os.path.join(OUT, "FONTES.md"), "w").write("\n".join(fontes) + "\n")
