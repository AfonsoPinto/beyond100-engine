"""Sons reais CC0 do Freesound, escolhidos à mão (ver reels/sfx/FONTES.md), cortados em peças para os Reels.
Pré-visualizações HQ (só com a chave da API). CC0 = domínio público: uso comercial livre, sem crédito obrigatório.
  python -m reels.sfx_fetch reels/sfx      (no GitHub, com o secret FREESOUND_API_KEY)"""
import array, json, math, os, subprocess, sys, urllib.parse, urllib.request, wave

KEY = os.environ["FREESOUND_API_KEY"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "reels/sfx"
SR = 44100
# (categoria, id Freesound, modo, n.º de peças): "hits" corta golpes isolados; "loop" tira um trecho de ambiente;
# "peak" tira o trecho mais forte (aplauso/ovação); "whole" usa o som inteiro (aparado)
SPEC = [
    ("hit_tennis", 662256, "hits", 3), ("hit_tennis", 662263, "hits", 3), ("hit_tennis", 338122, "hits", 4), ("hit_tennis", 710041, "hits", 1),
    ("serve", 662265, "hits", 2), ("serve", 662264, "hits", 2),
    ("hit_padel", 813413, "hits", 3), ("hit_padel", 816833, "hits", 3), ("hit_padel", 790875, "hits", 4),
    ("bounce", 533410, "hits", 3), ("bounce", 394355, "hits", 2), ("bounce", 788264, "hits", 2),
    ("bounce_clay", 662258, "hits", 4),
    ("squeak", 71224, "hits", 6), ("squeak", 88502, "hits", 3),
    ("crowd", 114052, "loop", 1), ("crowd_indoor", 381373, "loop", 1), ("crowd_indoor", 424297, "loop", 1),
    ("applause", 490341, "peak", 1), ("applause", 397434, "peak", 1), ("applause", 819358, "peak", 1),
    ("ooh", 324890, "peak", 1), ("ooh", 264499, "peak", 1),
]
LEN = {"hits": 0.45, "loop": 24.0, "peak": 6.0}
os.makedirs(OUT, exist_ok=True)


def info(i):
    u = f"https://freesound.org/apiv2/sounds/{i}/?" + urllib.parse.urlencode(dict(fields="id,name,username,license,url,previews", token=KEY))
    return json.load(urllib.request.urlopen(u, timeout=40))


def load(path):
    with wave.open(path) as w:
        a = array.array("h"); a.frombytes(w.readframes(w.getnframes()))
    return [v / 32768 for v in a]


def save(path, x):
    pk = max(1e-6, max(abs(v) for v in x)); g = 0.9 / pk
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(array.array("h", (int(max(-1, min(1, v * g)) * 32767) for v in x)).tobytes())


def env(x, hop=441):
    return [math.sqrt(sum(v * v for v in x[i:i + hop]) / hop) for i in range(0, len(x) - hop, hop)]


def hits(x, n):
    """golpes isolados: subida brusca de energia, separados >= 0,25 s; ficam os mais fortes"""
    e = env(x); out = []
    for k in range(3, len(e) - 1):
        base = max(1e-5, sorted(e[max(0, k - 30):k])[len(e[max(0, k - 30):k]) // 2])
        if e[k] > 6 * base and e[k] >= e[k - 1] and e[k] > 0.02:
            out.append((e[k], k))
    out.sort(reverse=True); sel = []
    for amp, k in out:
        if all(abs(k - j) > 25 for _, j in sel): sel.append((amp, k))
        if len(sel) >= n: break
    pieces = []
    for _, k in sel:
        i0 = max(0, k * 441 - 220); seg = x[i0:i0 + int(LEN["hits"] * SR)]
        L = len(seg); f = int(0.12 * SR)
        seg = [v * (min(1, (L - j) / f)) for j, v in enumerate(seg)]
        pieces.append(seg)
    return pieces


def window(x, secs, strongest):
    L = int(secs * SR)
    if len(x) <= L: return x
    if not strongest:
        i0 = min(len(x) - L, int(5 * SR)); return x[i0:i0 + L]
    e = env(x); w = int(secs * 100); best, bi = -1, 0; s = sum(e[:w])
    for k in range(len(e) - w):
        if s > best: best, bi = s, k
        s += e[k + w] - e[k]
    i0 = max(0, bi * 441 - int(0.3 * SR)); seg = x[i0:i0 + L]; f = int(0.6 * SR)
    return [v * min(1, j / (0.05 * SR), (len(seg) - j) / f) for j, v in enumerate(seg)]


fontes = ["# Sons reais (Freesound, CC0 — domínio público)", "", "Uso comercial livre, sem crédito obrigatório. Lista para referência.", ""]
count = {}
for cat, sid, mode, n in SPEC:
    try:
        s = info(sid)
        if "zero" not in (s.get("license") or "") and "Creative Commons 0" not in (s.get("license") or ""):
            print("não é CC0, ignorado:", sid, s.get("license")); continue
        mp3 = os.path.join(OUT, f"_{sid}.mp3"); wv = os.path.join(OUT, f"_{sid}.wav")
        urllib.request.urlretrieve(s["previews"]["preview-hq-mp3"], mp3)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", str(SR), "-af", "highpass=f=40", wv], check=True)
        x = load(wv); os.remove(mp3); os.remove(wv)
        pieces = hits(x, n) if mode == "hits" else [window(x, LEN[mode], mode == "peak")]
        for p in pieces:
            k = count.get(cat, 0); count[cat] = k + 1
            save(os.path.join(OUT, f"{cat}_{k}.wav"), p)
        fontes.append(f"- {cat}: \"{s['name']}\" por {s['username']} — {s['url']} (CC0) — {len(pieces)} peça(s)")
        print("ok", cat, sid, s["name"], len(pieces))
    except Exception as e:
        print("falhou", cat, sid, type(e).__name__, e)
print(count)
open(os.path.join(OUT, "FONTES.md"), "w").write("\n".join(fontes) + "\n")
