"""Seletor Ténis / Padel (topo de todas as páginas das duas secções) e cartão de anúncio do padel na página inicial do ténis."""

ICON_TENNIS = ('<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="19" fill="#0e3a2d" stroke="#f7f2e6" stroke-width="1.6"/>'
               '<circle cx="20" cy="20" r="12" fill="none" stroke="#f7f2e6" stroke-width=".8"/>'
               '<text x="20" y="24.5" text-anchor="middle" font-family="Georgia,serif" font-weight="700" font-size="11" fill="#f7f2e6">100</text>'
               '<circle cx="4.5" cy="20" r="1.6" fill="#d9f23d"/><circle cx="35.5" cy="20" r="1.6" fill="#d9f23d"/></svg>')
ICON_PADEL = ('<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="19" fill="#0c2e4a" stroke="#f7f2e6" stroke-width="1.6"/>'
              '<g fill="none" stroke="#f7f2e6" stroke-width="1.4"><rect x="14" y="9" width="12" height="22" rx="1"/>'
              '<line x1="14" y1="15" x2="26" y2="15" stroke-width=".8"/><line x1="14" y1="25" x2="26" y2="25" stroke-width=".8"/>'
              '<line x1="20" y1="15" x2="20" y2="25" stroke-width=".8"/></g><line x1="14" y1="20" x2="26" y2="20" stroke="#d9f23d" stroke-width="1.8"/></svg>')

CSS = """
.sport{display:flex;justify-content:center;margin:0 0 14px}
.sport div{display:inline-flex;border:1px solid var(--e);border-radius:999px;padding:4px;gap:4px;background:rgba(0,0,0,.18)}
.sport a{display:inline-flex;align-items:center;gap:8px;padding:6px 16px 6px 6px;border-radius:999px;text-decoration:none;
 font:700 .92rem system-ui;color:var(--s);transition:background .15s,color .15s}
.sport a svg{width:28px;height:28px;flex:none}
.sport a:hover{color:var(--c)}
.sport a.on.t{background:#f7f2e6;color:#0e3a2d}.sport a.on.p{background:#f7f2e6;color:#0c2e4a}
.padel-promo{display:flex;align-items:center;gap:14px;background:#0c2e4a;border:1px solid #24507a;border-radius:18px;padding:14px 16px;
 margin:0 0 22px;text-decoration:none;color:#f7f2e6}
.padel-promo svg{width:54px;height:54px;flex:none}.padel-promo b{display:block;font:700 1.15rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.padel-promo span{color:#a9c0d6;font-size:.9rem}.padel-promo i{margin-left:auto;font-style:normal;color:#d9f23d;font-size:1.6rem}
"""


def switch(active):
    t_on, p_on = ("on", "") if active == "tennis" else ("", "on")
    return (f'<div class="sport"><div><a class="t {t_on}" href="/index.html">{ICON_TENNIS}Tennis</a>'
            f'<a class="p {p_on}" href="/padel/index.html">{ICON_PADEL}Padel</a></div></div>')


def promo():
    return (f'<a class="padel-promo" href="/padel/index.html">{ICON_PADEL}<div><b>New: Beyond Padel</b>'
            f'<span>Every player, every draw: Premier Padel and the FIP Tour.</span></div><i>›</i></a>')
