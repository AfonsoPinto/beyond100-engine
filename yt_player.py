"""Vídeos do YouTube com plano B por visitante: alguns vídeos oficiais estão bloqueados em certos países
(ex.: os resumos do beIN SPORTS USA só passam nos EUA). O site não sabe de onde vem cada visitante, por isso usa a
API do leitor do YouTube: se o vídeo der erro (bloqueado no país, removido, sem autorização para embeber), passa ao
seguinte da lista; se nenhum der, mostra a ligação para o YouTube."""
import html
import json
import os
import time

EMBED_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "padel", "data", "yt_embed.json")
EMBED_PER_RUN = int(os.environ.get("YT_EMBED_PER_RUN") or "150")
_emb, _n = None, [0]


def _emb_load():
    global _emb
    if _emb is None:
        try:
            with open(EMBED_FILE, encoding="utf-8") as f:
                _emb = json.load(f)
        except (OSError, ValueError):
            _emb = {}
    return _emb


def save():
    if _emb is not None and _n[0]:
        with open(EMBED_FILE, "w", encoding="utf-8") as f:
            json.dump(_emb, f, separators=(",", ":"))


def embeddable(vid):
    """True/False/None. Pergunta ao oEmbed público do YouTube (grátis, sem chave): 200 = pode ser incorporado;
    401/403 = o dono desligou a incorporação; 404 = removido ou privado; 451 (nosso) = bloqueado em muitos países (só com YT_API_KEY).
    Cache: bons 7 dias, maus 2 dias (podem mudar).
    None = não se sabe (sem rede / limite por execução): nesse caso o vídeo continua a aparecer, como antes."""
    if not vid or os.environ.get("YT_EMBED_CHECK", "1") == "0":
        return None
    c = _emb_load()
    hit = c.get(vid)
    fresh = hit and time.time() - hit[1] < (7 if hit[0] == 200 else 2) * 86400
    if fresh and not (hit[0] == 200 and os.environ.get("YT_API_KEY") and len(hit) < 3):   # com chave nova: verifica também os países
        return hit[0] == 200
    if _n[0] >= EMBED_PER_RUN:
        return None if not hit else hit[0] == 200
    _n[0] += 1
    try:
        import requests
        r = requests.get("https://www.youtube.com/oembed", params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        code = r.status_code
    except Exception:
        return None if not hit else hit[0] == 200
    if code not in (200, 401, 403, 404):
        return None
    if code == 200 and _region_locked(vid):                          # passa no oEmbed mas está bloqueado em muitos países
        code = 451
    c[vid] = [code, time.time()] + ([1] if os.environ.get("YT_API_KEY") else [])
    save()
    return code == 200


KEY_COUNTRIES = {"PT", "ES", "GB", "US", "FR", "IT", "DE", "AR", "BR", "MX", "AU"}


def _region_locked(vid):
    """Com YT_API_KEY (YouTube Data API, grátis, 1 unidade por vídeo): True se o vídeo só passa numa lista curta de países
    ou está bloqueado num dos países de onde vêm mais visitas. Sem chave: False (não se sabe)."""
    key = os.environ.get("YT_API_KEY")
    if not key:
        return False
    try:
        import requests
        r = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "contentDetails", "id": vid, "key": key}, timeout=15)
        it = (r.json().get("items") or [{}])[0] if r.status_code == 200 else {}
    except Exception:
        return False
    rr = (it.get("contentDetails") or {}).get("regionRestriction") or {}
    allowed, blocked = set(rr.get("allowed") or []), set(rr.get("blocked") or [])
    return bool((allowed and len(allowed) < 100) or (blocked & KEY_COUNTRIES))


def link_card(vid, label="Watch on YouTube"):
    """Miniatura que abre o vídeo no YouTube (funciona sempre, mesmo quando o vídeo não pode ser incorporado)."""
    v = html.escape(vid)
    return (f'<a class="yt-card" href="https://www.youtube.com/watch?v={v}" target="_blank" rel="noopener" style="display:block;position:relative;'
            f'border-radius:16px;overflow:hidden;background:#000;text-decoration:none;margin:12px 0">'
            f'<img src="https://i.ytimg.com/vi/{v}/hqdefault.jpg" alt="" loading="lazy" style="width:100%;aspect-ratio:16/9;object-fit:cover;display:block;opacity:.85">'
            f'<span style="position:absolute;left:14px;bottom:14px;background:#d7f75b;color:#0b2b20;font:800 .95rem system-ui;padding:10px 16px;border-radius:999px">'
            f'▶ {html.escape(label)} ↗</span></a>')

JS = r"""<script>(function(){var E=document.querySelectorAll('[data-yt]');if(!E.length)return;
function go(){[].forEach.call(E,function(el){if(el._yt)return;el._yt=1;var L=JSON.parse(el.getAttribute('data-yt')),i=0,
h=el.dataset.h?document.getElementById(el.dataset.h):null,c=el.dataset.c?document.getElementById(el.dataset.c):null;
function show(v){if(h&&v.h)h.textContent=v.h;if(c)c.innerHTML=v.c||''}
function mk(){var v=L[i],d=document.createElement('div');el.innerHTML='';el.appendChild(d);show(v);
new YT.Player(d,{videoId:v.id,host:'https://www.youtube-nocookie.com',width:'100%',height:'100%',playerVars:{rel:0,playsinline:1,start:v.s||0},
events:{onError:function(){i++;if(i<L.length)mk();else{el.className='';el.innerHTML='<a href="https://www.youtube.com/watch?v='+L[0].id+'" target="_blank" rel="noopener" style="display:block;position:relative;border-radius:16px;overflow:hidden;background:#000;margin:12px 0"><img src="https://i.ytimg.com/vi/'+L[0].id+'/hqdefault.jpg" alt="" style="width:100%;aspect-ratio:16/9;object-fit:cover;display:block;opacity:.85"><span style="position:absolute;left:14px;bottom:14px;background:#d7f75b;color:#0b2b20;font:800 .95rem system-ui;padding:10px 16px;border-radius:999px">▶ Watch on YouTube ↗</span></a><p class="pd-note">Not playable here (often a country restriction).</p>'}}}})}
mk()})}
if(window.YT&&YT.Player)go();else{var p=window.onYouTubeIframeAPIReady;window.onYouTubeIframeAPIReady=function(){if(p)p();go()};
if(!document.getElementById('yt-api')){var s=document.createElement('script');s.id='yt-api';s.src='https://www.youtube.com/iframe_api';document.head.appendChild(s)}}})();</script>"""


def box(items, cls, hid="", cid=""):
    """items: [{'id','s'(início, s),'h'(título da secção),'c'(legenda em HTML)}], por ordem de preferência.
    O primeiro aparece logo como miniatura (sem JS também funciona); o leitor troca para o seguinte se der erro."""
    items = [x for x in items if x.get("id")]
    if not items:
        return ""
    ok = [x for x in items if embeddable(x["id"]) is not False]       # só os que o YouTube deixa incorporar
    if not ok:                                                          # nenhum: miniatura que abre no YouTube (em vez de um leitor partido)
        return link_card(items[0]["id"])
    items = ok
    v = items[0]
    first = (f'<iframe src="https://www.youtube-nocookie.com/embed/{html.escape(v["id"])}?rel=0{"&start=" + str(v["s"]) if v.get("s") else ""}" '
             f'title="Video" loading="lazy" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen" allowfullscreen></iframe>')
    data = html.escape(json.dumps(items, ensure_ascii=False), quote=True)
    return (f'<div class="{cls}" data-yt="{data}"{f" data-h={hid!r}" if hid else ""}{f" data-c={cid!r}" if cid else ""}>{first}</div>')
