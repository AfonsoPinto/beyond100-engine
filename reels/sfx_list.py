"""Lista candidatos CC0 no Freesound (nome, etiquetas, duração, descargas, nota) para escolher à mão."""
import json, os, urllib.parse, urllib.request
KEY = os.environ["FREESOUND_API_KEY"]
Q = {
    "hit": ["tennis ball racket hit", "tennis forehand", "tennis serve hit", "padel", "racquet ball hit"],
    "bounce": ["tennis ball bounce", "tennis ball bouncing court"],
    "glass": ["padel glass", "squash ball wall", "ball hit plexiglass", "ball hits glass"],
    "squeak": ["sneaker squeak", "shoes squeak gym floor", "tennis court shoes"],
    "crowd": ["tennis match crowd", "tennis tournament ambience", "stadium crowd ambience", "sports arena crowd"],
    "applause": ["tennis applause", "sports crowd applause cheer", "stadium applause"],
    "ooh": ["crowd ooh", "crowd gasp sport"],
}
for cat, qs in Q.items():
    for q in qs:
        url = "https://freesound.org/apiv2/search/text/?" + urllib.parse.urlencode(dict(
            query=q, filter='license:"Creative Commons 0"', page_size=15, sort="score",
            fields="id,name,tags,duration,num_downloads,avg_rating,num_ratings,username", token=KEY))
        try:
            res = json.load(urllib.request.urlopen(url, timeout=40)).get("results") or []
        except Exception as e:
            print("ERRO", cat, q, e); continue
        print(f"\n## {cat} | {q}")
        for s in res:
            print(f"{s['id']}\t{s['duration']:.2f}s\t{s['num_downloads']}dl\t{s.get('avg_rating',0):.1f}({s.get('num_ratings',0)})\t{s['name'][:60]}\t{','.join(s['tags'][:8])}")
