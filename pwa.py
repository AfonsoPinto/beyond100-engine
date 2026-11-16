"""Site instalável (PWA) e "Follow" de jogadores (16/11/2026). Comum ao ténis e ao padel.

- manifest.webmanifest (ténis, na raiz) e /padel/manifest.webmanifest (padel): o site pode ser adicionado ao ecrã inicial e abre
  em ecrã inteiro como uma app. Ícones desenhados aqui (sem imagens de fora).
- sw.js: service worker mínimo (deixa instalar; sem rede, mostra a última versão guardada da página ou um aviso simples).
- Botão "Follow" nas fichas de jogador: guarda a lista no próprio telemóvel (localStorage "b100_follow"), sem conta nem email.
- follow.json (ténis) e /padel/follow.json (padel): último resultado e próximo jogo de cada jogador, para o bloco "Your players"
  no topo da página inicial. Notificações ficam para uma 2.ª fase (precisam de chaves que o Afonso cria).
Não gasta pedidos à API de ténis: usa só os dados que o site já tem."""
import html
import json
import os

from PIL import Image, ImageDraw, ImageFont

esc = html.escape
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

APPS = {
    "tennis": {"name": "Beyond100 Tennis", "short": "Beyond100", "start": "/?source=pwa", "scope": "/", "bg": (14, 58, 45), "theme": "#0e3a2d",
               "dir": "", "desc": "Tennis beyond the top 100: Challenger, ITF and WTA scores, rankings and your players."},
    "padel": {"name": "Beyond Padel", "short": "Beyond Padel", "start": "/padel/?source=pwa", "scope": "/", "bg": (12, 46, 74), "theme": "#0c2e4a",
              "dir": "padel", "desc": "Premier Padel and FIP Tour results, draws, rankings and your players."},
}


def _font(size):
    try:
        return ImageFont.truetype(os.path.join(FONTS, "Inter-Black.otf"), size)
    except OSError:
        return ImageFont.load_default()


def _icon(sport, size, maskable=False):
    a = APPS[sport]
    im = Image.new("RGB", (size, size), a["bg"])
    d = ImageDraw.Draw(im)
    pad = int(size * (0.2 if maskable else 0.08))                  # "maskable": o Android corta em círculo, deixamos margem
    lime, cream = (217, 242, 61), (247, 242, 230)
    d.ellipse([pad, pad, size - pad, size - pad], outline=cream, width=max(3, size // 48))
    if sport == "tennis":
        d.text((size / 2, size / 2 + size * 0.01), "100", font=_font(int((size - 2 * pad) * 0.36)), fill=lime, anchor="mm")
    else:                                                          # campo de padel visto de cima
        w, h = (size - 2 * pad) * 0.34, (size - 2 * pad) * 0.56
        x0, y0 = size / 2 - w / 2, size / 2 - h / 2
        lw = max(2, size // 64)
        d.rectangle([x0, y0, x0 + w, y0 + h], outline=cream, width=lw)
        d.line([(x0, size / 2), (x0 + w, size / 2)], fill=lime, width=lw * 2)
        for yy in (y0 + h * 0.18, y0 + h * 0.82):
            d.line([(x0, yy), (x0 + w, yy)], fill=cream, width=lw)
        d.line([(size / 2, y0 + h * 0.18), (size / 2, y0 + h * 0.82)], fill=cream, width=lw)
    return im


def write_app(out_dir, sport):
    """Manifesto e ícones de uma das vertentes."""
    a = APPS[sport]
    base = os.path.join(out_dir, a["dir"]) if a["dir"] else out_dir
    os.makedirs(base, exist_ok=True)
    pre = f"/{a['dir']}" if a["dir"] else ""
    for n in (192, 512):
        _icon(sport, n).save(os.path.join(base, f"app-{n}.png"))
        _icon(sport, n, maskable=True).save(os.path.join(base, f"app-{n}-m.png"))
    _icon(sport, 180).save(os.path.join(base, "apple-touch-icon.png"))
    man = {"name": a["name"], "short_name": a["short"], "description": a["desc"], "start_url": a["start"], "scope": a["scope"],
           "id": a["start"].split("?")[0], "display": "standalone", "background_color": a["theme"], "theme_color": a["theme"],
           "icons": [{"src": f"{pre}/app-{n}.png", "sizes": f"{n}x{n}", "type": "image/png", "purpose": "any"} for n in (192, 512)]
           + [{"src": f"{pre}/app-{n}-m.png", "sizes": f"{n}x{n}", "type": "image/png", "purpose": "maskable"} for n in (192, 512)]}
    with open(os.path.join(base, "manifest.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)


SW_JS = r"""// Beyond100: service worker mínimo (16/11/2026). Páginas: rede primeiro, a última cópia se não houver rede.
const C = "b100-v1";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const r = e.request;
  if (r.method !== "GET" || new URL(r.url).origin !== location.origin || r.url.includes("/api/") || r.url.includes("/admin")) return;
  if (r.mode === "navigate") {
    e.respondWith(fetch(r).then(res => { const c = res.clone(); caches.open(C).then(x => x.put(r, c)); return res; })
      .catch(() => caches.match(r).then(m => m || new Response("<meta name=viewport content='width=device-width'><body style='font:16px system-ui;background:#0e3a2d;color:#f7f2e6;padding:24px'><h2>You're offline</h2><p>Reconnect to see the latest scores.</p>", {headers: {"Content-Type": "text/html"}}))));
  }
});
"""


def write_sw(out_dir):
    with open(os.path.join(out_dir, "sw.js"), "w", encoding="utf-8") as f:
        f.write(SW_JS)
    with open(os.path.join(out_dir, "_headers"), "a", encoding="utf-8") as f:
        f.write("/sw.js\n  Cache-Control: no-cache\n  Service-Worker-Allowed: /\n")


def head(sport):
    """Etiquetas para o <head> de todas as páginas de uma vertente."""
    a = APPS[sport]
    pre = f"/{a['dir']}" if a["dir"] else ""
    return (f'<link rel="manifest" href="{pre}/manifest.webmanifest"><link rel="apple-touch-icon" href="{pre}/apple-touch-icon.png">'
            f'<meta name="apple-mobile-web-app-capable" content="yes"><meta name="mobile-web-app-capable" content="yes">'
            f'<meta name="apple-mobile-web-app-title" content="{esc(a["short"])}">')


# ------------------------------------------------------------------ Follow
CSS = """
.pv-follow{display:inline-flex;align-items:center;gap:8px;align-self:flex-start;border:1px solid rgba(255,255,255,.35);background:rgba(0,0,0,.25);color:#fff;
font:800 .9rem system-ui;border-radius:999px;padding:9px 16px;cursor:pointer;backdrop-filter:blur(6px)}
.pv-follow svg{width:16px;height:16px}.pv-follow.on{background:var(--v);border-color:var(--v);color:var(--g)}
.yp{margin:4px 0 20px}.yp[hidden]{display:none}
.yp-h{display:flex;justify-content:space-between;align-items:baseline;margin:0 0 10px}.yp-h b{font:850 1.2rem system-ui;color:var(--c)}.yp-h a{font:700 .84rem system-ui;color:var(--v);text-decoration:none}
.yp-row{display:flex;gap:10px;overflow-x:auto;scrollbar-width:none;padding-bottom:4px}.yp-row::-webkit-scrollbar{display:none}
.yp-c{flex:0 0 240px;display:flex;flex-direction:column;gap:6px;background:var(--deep);border:1px solid var(--e);border-radius:18px;padding:12px 14px;text-decoration:none;color:var(--c)}
.yp-c .t{display:flex;align-items:center;gap:10px}.yp-c img,.yp-c .i{width:40px;height:40px;border-radius:50%;object-fit:cover;flex:none;background:var(--g);display:grid;place-items:center;font:800 .8rem system-ui;color:var(--s)}
.yp-c b{font:800 .95rem/1.2 system-ui}.yp-c small{display:block;font:600 .74rem system-ui;color:var(--s)}
.yp-c .l{font:600 .82rem/1.35 system-ui}.yp-c .l.w{color:var(--v)}.yp-c .l.x{color:#ff9a8a}.yp-c .n{font:600 .78rem system-ui;color:var(--s)}
.inst{position:fixed;left:12px;right:12px;bottom:calc(96px + env(safe-area-inset-bottom));z-index:70;display:flex;gap:12px;align-items:center;background:var(--deep);
border:1px solid var(--e);border-radius:18px;padding:12px 14px;box-shadow:0 14px 34px rgba(0,0,0,.45);color:var(--c);font:500 .88rem/1.35 system-ui}
.inst[hidden]{display:none}.inst b{display:block;font-weight:800}.inst button{border:0;border-radius:12px;font:800 .84rem system-ui;padding:10px 12px;cursor:pointer}
.inst .go{background:var(--v);color:var(--g)}.inst .x{background:transparent;color:var(--s)}
@media(min-width:721px){.inst{left:auto;right:24px;bottom:24px;max-width:420px}}
"""

STAR = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 3.5l2.6 5.3 5.9.9-4.2 4.1 1 5.8L12 16.9l-5.3 2.7 1-5.8-4.2-4.1 5.9-.9z"/></svg>'


def follow_button(key, name):
    """key: "tennis:<slug>" ou "padel:<id>"."""
    return f'<button type="button" class="pv-follow" data-k="{esc(key)}" data-n="{esc(name)}" aria-pressed="false">{STAR}<span>Follow</span></button>'


def your_players(sport):
    """Bloco "Your players" da página inicial: aparece só a quem já segue alguém."""
    src = "/padel/follow.json" if sport == "padel" else "/follow.json"
    return f'<section class="yp" id="yp" data-src="{src}" data-sport="{sport}" hidden><div class="yp-h"><b>Your players</b><span class="mut2">Saved on this phone</span></div><div class="yp-row"></div></section>'


JS = r"""<script>(function(){
var K="b100_follow";function get(){try{return JSON.parse(localStorage.getItem(K)||"[]")}catch(e){return[]}}
function put(a){try{localStorage.setItem(K,JSON.stringify(a))}catch(e){}}
function sync(b){var on=get().some(function(x){return x.k===b.dataset.k});b.classList.toggle("on",on);b.setAttribute("aria-pressed",on);b.lastChild.textContent=on?"Following":"Follow"}
document.querySelectorAll(".pv-follow").forEach(function(b){sync(b);b.addEventListener("click",function(){var a=get(),i=a.findIndex(function(x){return x.k===b.dataset.k});
 if(i>=0)a.splice(i,1);else a.unshift({k:b.dataset.k,n:b.dataset.n,t:Date.now()});put(a.slice(0,40));sync(b);if(i<0)maybeInstall(true)})});
var yp=document.getElementById("yp");
if(yp){var mine=get().filter(function(x){return x.k.indexOf(yp.dataset.sport+":")===0});
 if(mine.length){fetch(yp.dataset.src).then(function(r){return r.json()}).then(function(d){var e=function(s){return String(s||"").replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})};
  var h=mine.map(function(f){var p=d[f.k.split(":")[1]];if(!p)return"";var ini=f.n.split(" ").slice(0,2).map(function(w){return w[0]}).join("");
   return '<a class="yp-c" href="'+e(p.u)+'"><span class="t">'+(p.i?'<img src="'+e(p.i)+'" alt="" loading="lazy">':'<span class="i">'+e(ini)+'</span>')+'<span><b>'+e(f.n)+'</b><small>'+(p.r?"No. "+p.r:"")+'</small></span></span>'
    +(p.l?'<span class="l '+(p.w?"w":"x")+'">'+e(p.l)+'</span>':"")+(p.x?'<span class="n">Next: '+e(p.x)+'</span>':"")+'</a>'}).join("");
  if(h){yp.querySelector(".yp-row").innerHTML=h;yp.hidden=false}}).catch(function(){})}}
// convite para instalar: só depois de seguir alguém ou à 3.ª visita, e nunca dentro da app instalada
var ev=null,st=window.matchMedia("(display-mode: standalone)").matches||navigator.standalone;
window.addEventListener("beforeinstallprompt",function(e){e.preventDefault();ev=e});
function maybeInstall(force){if(st)return;var n=0;try{n=+localStorage.getItem("b100_v")||0;localStorage.setItem("b100_v",n+1);if(Date.now()-(+localStorage.getItem("b100_ix")||0)<1209600000)return}catch(e){return}
 if(!force&&n<2)return;var ios=/iphone|ipad|ipod/i.test(navigator.userAgent);if(!ev&&!ios)return;
 var b=document.createElement("div");b.className="inst";b.innerHTML='<div style="flex:1"><b>Add Beyond100 to your home screen</b>'+(ios?'Tap <b style="display:inline">Share</b> then <b style="display:inline">Add to Home Screen</b>.':'Opens like an app, one tap away.')+'</div>'+(ios?"":'<button class="go">Add</button>')+'<button class="x" aria-label="Close">✕</button>';
 document.body.appendChild(b);b.querySelector(".x").onclick=function(){b.remove();try{localStorage.setItem("b100_ix",Date.now())}catch(e){}};
 var g=b.querySelector(".go");if(g)g.onclick=function(){ev.prompt();b.remove()}}
setTimeout(function(){maybeInstall(false)},4000);
if("serviceWorker" in navigator)navigator.serviceWorker.register("/sw.js").catch(function(){});
})();</script>"""


def follow_index_tennis(pidx, avatars, ranks, upcoming, base_tournament, rshort):
    """slug -> {u, r, i, l (último jogo), w (ganhou?), x (próximo jogo)} para todos os jogadores com página."""
    out = {}
    nxt = {}
    for u in (upcoming or {}).get("matches", []):
        for i in (1, 2):
            p, o = u.get("p%d" % i) or {}, u.get("p%d" % (3 - i)) or {}
            from webapp import slugify
            k = slugify(p.get("name") or "")
            if k and (k not in nxt or (u.get("t") or "") < nxt[k][0]):
                nxt[k] = (u.get("t") or "", f'vs {o.get("name", "?")} · {base_tournament(u.get("tp") or "")} · {(u.get("t") or "")[8:10]}/{(u.get("t") or "")[5:7]}')
    for sl, e in pidx.items():
        ms = sorted(e["matches"], key=lambda x: x[1].get("date", ""), reverse=True)
        row = {"u": f"/p/{sl}.html"}
        rk = (ranks.get(sl) or {}).get("rank") or e.get("rank")
        if isinstance(rk, int) and rk > 0:
            row["r"] = rk
        if sl in avatars:
            row["i"] = f"/img/{sl}.jpg"
        if ms:
            i, r = ms[0]
            if r.get("winner") in (1, 2):
                op = r["p%d" % (3 - i)]["name"]
                g = r.get("games") or [[], []]
                sc = " ".join(f"{a}-{b}" for a, b in zip(g[i - 1], g[2 - i]))
                won = r["winner"] == i
                row["l"] = f'{"Won" if won else "Lost"} {sc} vs {op} · {rshort(r.get("round"), r.get("q"))} {base_tournament(r.get("tournament", ""))}'
                row["w"] = 1 if won else 0
        if sl in nxt:
            row["x"] = nxt[sl][1]
        out[sl] = row
    return out
