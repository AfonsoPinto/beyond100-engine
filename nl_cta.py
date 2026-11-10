"""Convites para a newsletter no site (ténis e padel, iguais), 10/11/2026.

1. inline(...): cartão a meio das páginas de jogador e de jogo, com texto da própria página ("Follow Watanuki...").
   Os estudos de formulários dizem que um convite ligado ao que se está a ler converte 2 a 3 vezes mais do que um genérico.
2. SLIDE: cartão pequeno que sobe do fundo nas outras páginas depois de ler 25% (menos de ~15% do ecrã no telemóvel,
   como pede o Google para não penalizar). Fecha-se e não volta durante 14 dias; quem se inscreveu nunca mais o vê.
   Nunca aparece em páginas que já têm o cartão inline, nem em /admin/ e /newsletter/.
3. Em ambos: "See last week's issue" (a newsletter da semana em /newsletter/latest.html) e a capa da semana como imagem.

Usa o mesmo formulário do Buttondown que já existe (NEWSLETTER_USER). Sem utilizador definido, não mostra nada.
Só guarda no browser (localStorage) se fechaste o cartão ou te inscreveste: nada de dados pessoais no site.
"""
import html
import os
import re

esc = html.escape


def form_url():
    url = (os.environ.get("NEWSLETTER_URL") or "").strip()
    user = re.sub(r"[^A-Za-z0-9_-]", "", os.environ.get("NEWSLETTER_USER") or "")
    if user and not url:
        url = f"https://buttondown.com/api/emails/embed-subscribe/{user}"
    return url if url.startswith("https://") else ""


SUB = "Every Sunday: the week's champions, upsets and biggest climbers beyond the top 100. One email, two minutes."
SUB_PADEL = "Every Sunday: padel champions, the Race to the Finals and the best of tennis beyond the top 100. One email, two minutes."


def inline(title, sub=None, sport="tennis"):
    """Cartão para o meio da página. title já vem com o contexto da página (ex.: "Follow Yosuke Watanuki's season")."""
    url = form_url()
    if not url:
        return ""
    sub = sub or (SUB_PADEL if sport == "padel" else SUB)
    return (f'<section class="nlc{" padel" if sport == "padel" else ""}" data-nl>'
            f'<a class="nlc-cov" href="/newsletter/latest.html" aria-label="See last week\'s issue"><img src="/newsletter/cover.jpg" alt="" width="150" height="172" loading="lazy" onerror="this.parentNode.remove()"></a>'
            f'<div class="nlc-b"><p class="nlc-k">Weekly · free</p><h2>{esc(title)}</h2><p class="nlc-s">{esc(sub)}</p>'
            f'<form action="{esc(url)}" method="post" target="_blank" data-nlf><input type="email" name="email" required placeholder="you@example.com" aria-label="Email">'
            f'<input type="hidden" name="embed" value="1"><button type="submit">Subscribe</button></form>'
            f'<p class="nlc-f"><a href="/newsletter/latest.html">See last week\'s issue →</a><span>No spam. Unsubscribe in one click.</span></p></div></section>')


CSS = """
.nlc{position:relative;display:flex;gap:22px;align-items:center;margin:34px 0;padding:22px;border-radius:26px;overflow:hidden;
  background:radial-gradient(120% 140% at 0% 0%,rgba(217,242,61,.16),transparent 55%),var(--deep);border:1px solid var(--e)}
.nlc::after{content:"";position:absolute;inset:0;border-radius:26px;padding:1px;pointer-events:none;
  background:linear-gradient(135deg,rgba(217,242,61,.7),transparent 40%,transparent 70%,rgba(217,242,61,.35));
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude}
.nlc-cov{flex:0 0 auto;display:block;transform:rotate(-4deg);transition:transform .25s}
.nlc-cov:hover{transform:rotate(0) scale(1.03)}
.nlc-cov img{display:block;width:150px;height:auto;border-radius:16px;box-shadow:0 14px 34px rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.12)}
.nlc-b{flex:1;min-width:0}
.nlc-k{margin:0 0 6px;font-size:.72rem;font-weight:800;letter-spacing:.16em;text-transform:uppercase;color:var(--v)}
.nlc h2{margin:0;font-size:1.55rem;line-height:1.08;letter-spacing:-.02em;color:var(--c);text-transform:none}
.nlc-s{margin:8px 0 14px;color:var(--s);font-size:.95rem;line-height:1.45}
.nlc form,.nls form{display:flex;gap:8px;margin:0}
.nlc input[type=email],.nls input[type=email]{flex:1;min-width:0;padding:12px 16px;border-radius:999px;border:1px solid var(--e);background:rgba(0,0,0,.25);color:var(--c);font:inherit;font-size:.95rem}
.nlc input[type=email]:focus,.nls input[type=email]:focus{outline:2px solid var(--v);outline-offset:1px;border-color:transparent}
.nlc button,.nls button[type=submit]{padding:12px 20px;border-radius:999px;border:0;background:var(--v);color:#0e3a2d;font:inherit;font-weight:800;cursor:pointer;white-space:nowrap}
.nlc button:hover,.nls button[type=submit]:hover{filter:brightness(1.08)}
.nlc-f{display:flex;flex-wrap:wrap;gap:6px 16px;margin:12px 0 0;font-size:.8rem;color:var(--s)}
.nlc-f a{color:var(--c);font-weight:700;text-decoration:none}.nlc-f a:hover{color:var(--v)}
.nlc.done form,.nls.done form{display:none}
.nl-ok{display:none;margin:0;padding:12px 16px;border-radius:16px;background:rgba(217,242,61,.12);color:var(--c);font-weight:700}
.done .nl-ok{display:block}
@media (max-width:600px){.nlc{flex-direction:column;align-items:flex-start;padding:20px 18px}.nlc-cov{display:none}.nlc h2{font-size:1.3rem}.nlc form{flex-direction:column}.nlc input[type=email],.nls input[type=email]{font-size:16px}.nlc button{width:100%}}
.nls{position:fixed;right:20px;bottom:20px;z-index:60;width:360px;max-width:calc(100vw - 24px);padding:16px 16px 14px;border-radius:22px;
  background:rgba(9,40,31,.92);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border:1px solid rgba(217,242,61,.35);
  box-shadow:0 20px 50px rgba(0,0,0,.5);transform:translateY(140%);opacity:0;transition:transform .45s cubic-bezier(.2,.8,.2,1),opacity .3s}
.nls.padel{background:rgba(8,34,58,.92)}
.nls.on{transform:none;opacity:1}
.nls-t{display:flex;align-items:center;gap:10px;margin:0 30px 10px 0}
.nls-t img{width:40px;height:46px;object-fit:cover;border-radius:8px;flex:0 0 auto}
.nls-t b{display:block;color:var(--c);font-size:.98rem;line-height:1.2}
.nls-t small{display:block;color:var(--s);font-size:.78rem;margin-top:2px}
.nls-t small a{color:var(--v);text-decoration:none;font-weight:700}
.nls .x{position:absolute;top:10px;right:10px;width:28px;height:28px;border-radius:50%;border:0;background:rgba(255,255,255,.08);color:var(--s);font-size:16px;line-height:28px;cursor:pointer;padding:0}
.nls input[type=email]{padding:10px 14px}.nls button[type=submit]{padding:10px 16px}
@media (max-width:720px){.nls{left:12px;right:12px;bottom:calc(72px + env(safe-area-inset-bottom));width:auto}}
@media (max-width:600px){.nls{left:12px;right:12px;width:auto;padding:12px 12px 10px;border-radius:18px}.nls-t{margin-bottom:8px}.nls-t img{display:none}.nls-t small{display:none}.nls-t b{font-size:.92rem}.nls input[type=email],.nls button[type=submit]{padding:9px 14px}}
@media (prefers-reduced-motion:reduce){.nls{transition:none}.nlc-cov{transform:none}}
"""

# textos do cartão que sobe, por língua da página (a newsletter é em inglês: nas outras línguas dizemos isso)
_TXT = {
    "en": ("The week beyond the top 100", "Every Sunday · free", "See an issue", "Subscribe", "Thanks! Check your inbox to confirm."),
    "es": ("La semana más allá del top 100", "Cada domingo · gratis · en inglés", "Ver un número", "Suscribirme", "¡Gracias! Revisa tu correo para confirmar."),
    "fr": ("La semaine au-delà du top 100", "Chaque dimanche · gratuit · en anglais", "Voir un numéro", "S'abonner", "Merci ! Confirmez dans votre boîte mail."),
    "de": ("Die Woche jenseits der Top 100", "Jeden Sonntag · kostenlos · auf Englisch", "Ausgabe ansehen", "Abonnieren", "Danke! Bitte bestätige in deinem Postfach."),
    "it": ("La settimana oltre la top 100", "Ogni domenica · gratis · in inglese", "Vedi un numero", "Iscriviti", "Grazie! Controlla la posta per confermare."),
}


def slide(sport="tennis"):
    """CSS + cartão que sobe + script (vai no fim de todas as páginas; ele próprio decide se aparece)."""
    url = form_url()
    if not url:
        return ""
    import json
    padel = sport == "padel"
    t_padel = dict(_TXT, en=("The padel week, in one email",) + _TXT["en"][1:],
                   es=("La semana del pádel, en un correo",) + _TXT["es"][1:])
    tx = json.dumps(t_padel if padel else _TXT, ensure_ascii=False)
    return (f'<style>{CSS}</style>'
            f'<aside class="nls{" padel" if padel else ""}" id="nls" aria-label="Newsletter" hidden>'
            f'<button class="x" type="button" aria-label="Close">×</button>'
            f'<div class="nls-t"><img src="/newsletter/cover.jpg" alt="" onerror="this.remove()"><div><b data-t="0"></b><small><span data-t="1"></span> · <a href="/newsletter/latest.html" data-t="2"></a></small></div></div>'
            f'<form action="{esc(url)}" method="post" target="_blank" data-nlf><input type="email" name="email" required placeholder="you@example.com" aria-label="Email">'
            f'<input type="hidden" name="embed" value="1"><button type="submit" data-t="3"></button></form><p class="nl-ok" data-t="4"></p></aside>'
            "<script>(function(){var T=" + tx + r""",L=(document.documentElement.lang||"en").slice(0,2),t=T[L]||T.en;
function g(k){try{return localStorage.getItem(k)}catch(e){return null}}function s(k,v){try{localStorage.setItem(k,v)}catch(e){}}
document.querySelectorAll("form[data-nlf]").forEach(function(f){f.addEventListener("submit",function(){s("b100_nl","1");var c=f.closest(".nlc,.nls");
  if(c){setTimeout(function(){c.classList.add("done");if(!c.querySelector(".nl-ok")){var p=document.createElement("p");p.className="nl-ok";p.textContent=t[4];f.after(p)}},300)}})});
var a=document.getElementById("nls");if(!a)return;
a.querySelectorAll("[data-t]").forEach(function(e){e.textContent=t[+e.dataset.t]});
var p=location.pathname;if(g("b100_nl")||/^\/(admin|newsletter)\//.test(p)||document.querySelector("[data-nl]"))return;
var x=+g("b100_nl_x")||0;if(Date.now()-x<14*864e5)return;
var shown=false;function chk(){if(shown)return;var h=document.documentElement,sc=(h.scrollTop||document.body.scrollTop)/Math.max(1,h.scrollHeight-h.clientHeight);
  if(sc>=.25){shown=true;a.hidden=false;requestAnimationFrame(function(){requestAnimationFrame(function(){a.classList.add("on")})});removeEventListener("scroll",chk)}}
addEventListener("scroll",chk,{passive:true});
a.querySelector(".x").onclick=function(){a.classList.remove("on");s("b100_nl_x",String(Date.now()));setTimeout(function(){a.hidden=true},500)};
})();</script>""")
