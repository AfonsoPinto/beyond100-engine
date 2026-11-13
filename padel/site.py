"""Beyond Padel: gera a secção /padel do site a partir de padel/data/ (sem pedidos à API).
Páginas: início, torneios, torneio (info, ordem de jogo, quadro, resultados, campeões anteriores, notícias),
resultados, ordem de jogo, rankings (homens/mulheres), jogadores, pares e países.
Uso: python -m padel.site site   (escreve em site/padel/)"""
import datetime as dt
import html
import json
import os
import re
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sport_switch  # noqa: E402
import yt_player  # noqa: E402
import site_nav  # noqa: E402
import site_ui  # noqa: E402
import site_more  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "data")
SITE_BASE = os.environ.get("SITE_URL") or "https://beyond100tennis.com"
IG = "https://www.instagram.com/beyond100.padel/"
esc = html.escape

LEVEL = {"major": "Premier Padel Major", "p1": "Premier Padel P1", "p2": "Premier Padel P2", "finals": "Premier Padel Finals",
         "fip_platinum": "FIP Platinum", "fip_gold": "FIP Gold", "fip_silver": "FIP Silver", "fip_bronze": "FIP Bronze",
         "fip_other": "FIP"}
LEVEL_SHORT = {"major": "MAJOR", "p1": "P1", "p2": "P2", "finals": "FINALS", "fip_platinum": "FIP PLATINUM",
               "fip_gold": "FIP GOLD", "fip_silver": "FIP SILVER", "fip_bronze": "FIP BRONZE", "fip_other": "FIP"}
LEVEL_ORDER = {"finals": 0, "major": 1, "p1": 2, "p2": 3, "fip_platinum": 4, "fip_gold": 5, "fip_silver": 6, "fip_bronze": 7, "fip_other": 8}
CAT = {"men": "Men", "women": "Women"}
OG_MAP = {}
CSS_VER = "1"                                                     # muda quando o CSS muda (o telemóvel guardava o CSS antigo)                                                       # página -> imagem de partilha (preenchido no build)

CSS = """
:root{--g:#0c2e4a;--deep:#08223a;--c:#f7f2e6;--v:#d9f23d;--s:#a9c0d6;--e:#24507a}
body{background:var(--g)}
.pd-hero{text-align:center;padding:10px 0 26px}.pd-hero svg{width:min(220px,58vw);height:auto}
.pd-hero h1{margin:14px 0 6px}.pd-hero p{color:var(--s);max-width:40ch;margin:0 auto}
.pd-tabs{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 18px}
.pd-tabs a{border:1px solid var(--e);border-radius:999px;padding:7px 14px;text-decoration:none;color:var(--s);font:600 .88rem system-ui}
.pd-tabs a.on,.pd-tabs a:hover{background:var(--v);color:var(--g);border-color:var(--v)}
.pd-card{background:var(--deep);border:1px solid var(--e);border-radius:18px;padding:14px 16px;margin:0 0 12px}
.pd-card h3{margin:0 0 4px;font:700 1.15rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}.pd-card h3 a{text-decoration:none}
.pd-meta{color:var(--s);font-size:.86rem;display:flex;flex-wrap:wrap;gap:4px 10px;align-items:center}
.pd-tag{display:inline-block;background:var(--v);color:var(--g);font:800 .68rem system-ui;letter-spacing:.1em;padding:3px 8px;border-radius:6px}
.pd-tag.g{background:none;border:1px solid var(--e);color:var(--s)}
.pd-m{border-top:1px solid var(--e);padding:9px 0;display:grid;grid-template-columns:1fr auto;gap:2px 12px;align-items:center}
.pd-m:first-of-type{border-top:0}
.pd-m .r{grid-column:1/-1;font-size:.74rem;color:var(--s);letter-spacing:.04em;text-transform:uppercase}
.pd-t{display:flex;flex-direction:column;gap:1px;min-width:0}.pd-pl{display:block}
.pd-pair{font:600 .7rem system-ui;color:var(--s);text-decoration:none;margin-left:6px}
.pt td:nth-child(4){white-space:nowrap}
.pd-t a{text-decoration:none}.pd-t a:hover{text-decoration:underline}
.pd-t.w{font-weight:700}.pd-t.l{color:var(--s)}
.pd-t small{color:var(--s);font-weight:400}
.pd-sc{display:flex;gap:4px;justify-content:flex-end}
.pd-sc b{min-width:30px;height:30px;border-radius:8px;border:1px solid var(--e);display:grid;place-items:center;font:700 .95rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--s)}
.pd-sc b.on{background:var(--v);border-color:var(--v);color:var(--g)}
.pd-sc i{font-style:normal;font-size:.62rem;vertical-align:super}
.pd-when{color:var(--v);font:700 .85rem system-ui;white-space:nowrap}
.pd-live{color:#ff6b6b!important;animation:pdblink 1.6s ease-in-out infinite}.pd-since{color:var(--s);font-weight:600;animation:none}.tm .pd-since{display:block;text-align:right;font-size:.72rem}@keyframes pdblink{50%{opacity:.45}}
@media (prefers-reduced-motion:reduce){.pd-live{animation:none}}
.pd-rchips{display:flex;flex-wrap:nowrap;overflow-x:auto;max-width:100%;scrollbar-width:none;margin:0 0 12px}.pd-rchips::-webkit-scrollbar{display:none}
.pd-rchips button{flex:0 0 auto}
.pd-bk .rd{display:none}.pd-bk .rd.on{display:block}
.pd-bk h4{margin:0 0 8px;font:700 .72rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--v)}
.pd-bk .col{display:flex;flex-direction:column;justify-content:space-around;gap:8px}
.pd-bm{background:var(--deep);border:1px solid var(--e);border-radius:14px;padding:4px 12px;font:500 .95rem system-ui}
.pd-bm .pl{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:8px 0}
.pd-bm .pl+.pl{border-top:1px solid var(--e)}
.pd-bm .nm{min-width:0}.pd-bm a{text-decoration:none;color:inherit}
.pd-bm .pl.w{font-weight:700}.pd-bm .pl.l{color:var(--s)}
.pd-bm .s{display:flex;gap:4px;flex:0 0 auto}
.pd-bm .s b{min-width:24px;height:24px;border-radius:7px;border:1px solid var(--e);display:grid;place-items:center;font:700 .8rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--s)}
.pd-bm .s b.on{background:var(--v);border-color:var(--v);color:var(--g)}
.pd-bm .when{font:700 .75rem system-ui;color:var(--v);padding:0 0 8px}
@media(min-width:900px){.pd-bkw .pd-rchips{display:inline-flex}.pd-bk{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(250px,1fr);gap:14px;overflow-x:auto;padding:4px 2px 14px}
.pd-bk .rd{display:block}.pd-bm{font-size:.86rem}}
.pd-seed{display:inline-block;font:700 .62rem system-ui;color:var(--g);background:var(--s);border-radius:4px;padding:1px 4px;margin-left:6px;vertical-align:1px}
.pd-rk td{padding:8px 6px}.pd-rk .up{color:var(--v)}.pd-rk .dn{color:#ff9a8a}
.pd-news a{display:block;padding:8px 0;border-top:1px solid var(--e);text-decoration:none}.pd-news a:first-child{border:0}
.pd-news small{color:var(--s);display:block}
.pd-court{margin:10px 0 4px;font:700 .78rem system-ui;letter-spacing:.1em;text-transform:uppercase;color:var(--s)}
.pd-grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.pd-xrs{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.pd-xr{background:var(--deep);border:1px solid var(--e);border-radius:999px;padding:6px 12px;color:var(--s);font-size:.85rem}.pd-xr b{color:var(--v)}
.pd-count{margin:10px 0 4px;color:var(--s);font-weight:600}.pd-count span{color:var(--v);font-weight:800}
.pd-note{color:var(--s);font-size:.8rem}
.pd-av{width:34px;height:34px;border-radius:50%;object-fit:cover;flex:0 0 auto;border:2px solid var(--e);background:var(--deep)}
.pd-av.ini{display:inline-grid;place-items:center;font:700 .7rem system-ui;color:var(--s);box-sizing:border-box;background:var(--g);border-color:var(--e)!important}
.pd-avs{display:flex;margin-bottom:6px}.pd-avs .pd-av{width:38px;height:38px;margin-right:-8px;border-color:var(--deep)}
.pd-phead{display:flex;gap:16px;align-items:flex-end}.pd-ph{margin:0;flex:0 0 132px}
.pd-ph img{width:132px;height:165px;object-fit:cover;border-radius:16px;border:1px solid var(--e);display:block}
.pd-ph figcaption{font-size:.62rem;color:var(--s);margin-top:4px;line-height:1.25}
@media(min-width:760px){.pd-ph{flex-basis:200px}.pd-ph img{width:200px;height:250px}}
.pd-flts{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 14px}.pd-flt{margin:0}
.pd-seg a{color:var(--s);font:600 .85rem system-ui;padding:6px 14px;border-radius:999px;text-decoration:none}.pd-seg a.on{background:var(--v);color:var(--g)}
.pd-gh{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 4px}.pd-gh a{text-decoration:none}.pd-gh b{font:700 1.1rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}.pd-gh .pd-note{margin-left:auto}
.pd-more2{margin:6px 0 0}.pd-more2 summary{cursor:pointer;color:var(--v);font:600 .85rem system-ui;padding:8px 0;list-style:none}.pd-more2 summary::-webkit-details-marker{display:none}
.pd-more2 summary::after{content:" ▾"}.pd-more2[open] summary::after{content:" ▴"}
.pd-btn{display:block;width:100%;margin:10px 0 18px;padding:12px;border-radius:12px;border:1px solid var(--e);background:var(--deep);color:var(--v);font:600 .9rem system-ui;cursor:pointer}
.pd-tabs2{display:flex;gap:4px;border-bottom:1px solid var(--e);margin:14px 0 14px;overflow-x:auto;scrollbar-width:none}.pd-tabs2::-webkit-scrollbar{display:none}
.pd-tabs2 button{flex:0 0 auto;border:0;background:none;color:var(--s);font:600 .92rem system-ui;padding:10px 12px;border-bottom:3px solid transparent;cursor:pointer}
.pd-tabs2 button.on{color:var(--c);border-bottom-color:var(--v)}
.pd-chs{background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:12px 14px;margin:6px 0 10px}
.pd-chs-h{font:700 .72rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--v);margin-bottom:4px}
.pd-chr{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--e)}.pd-chr:first-of-type{border-top:0}
.pd-chr small{flex:0 0 52px;font:700 .68rem system-ui;letter-spacing:.1em;text-transform:uppercase;color:var(--s)}
.pd-chr .nm{flex:1;min-width:0;font:700 .95rem system-ui}.pd-chr a,.pd-bm a,.pd-bm .nm{font-family:system-ui,-apple-system,sans-serif!important}.pd-chr .nm a{text-decoration:none;color:inherit}
.pd-chr .pd-avs{margin:0}.pd-chr .pd-av{width:30px;height:30px;margin-right:-6px}.pd-pairl{color:var(--v);text-decoration:none;font-size:1.3rem;padding:0 2px}
.pd-av.lg{width:48px;height:48px}.pd-avs .pd-av.lg{width:48px;height:48px}
.pd-chart svg{width:100%;height:90px;display:block;margin:6px 0}
.pd-form{display:flex;gap:4px;margin:6px 0 0}.pd-form i,.form i{font:700 .7rem system-ui;font-style:normal;width:22px;height:22px;border-radius:6px;display:inline-grid;place-items:center}
.pd-form i.fw{background:var(--v);color:var(--g)}.pd-form i.fl{border:1px solid var(--e);color:var(--s)}
.pd-win{font-size:.88rem;margin-top:3px}.pd-win b{color:var(--v);font:700 .7rem system-ui;letter-spacing:.1em;text-transform:uppercase;margin-right:4px}
.pd-trow{display:flex;gap:10px;align-items:flex-start;padding:12px 2px;border-top:1px solid var(--e);text-decoration:none;color:inherit}.pd-trow b{font:700 1.02rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.pd-trow .pd-tag{flex:0 0 auto;margin-top:2px}
.pd-rkf{display:flex;gap:8px;margin:10px 0}.pd-rkf .srch{flex:1;margin:0}.pd-rkf select{background:var(--deep);color:var(--c);border:1px solid var(--e);border-radius:10px;padding:0 8px;max-width:40%}
.pd-pl{display:block}.pd-pl a{color:inherit}
td .on{color:var(--v)}
.pd-mlink.hl{background:var(--v);color:var(--g)!important;padding:3px 10px;border-radius:999px;letter-spacing:0}
.pd-mlink.vd{border:1px solid var(--v);padding:2px 9px;border-radius:999px}.pd-mlink.pl{color:var(--s)!important;font-weight:600}
.pd-bmv{display:block;text-align:right;font:700 .72rem system-ui;color:var(--v)!important;padding:0 0 8px;text-decoration:none}.pd-bmv.hl{color:var(--g)!important}
.pd-bmv.hl{display:inline-block;float:right;background:var(--v);border-radius:999px;padding:3px 10px;margin:0 0 8px}
.pd-hlh{color:var(--v)}
.pd-mlink{float:right;color:var(--v);text-decoration:none;font:700 .72rem system-ui;letter-spacing:.04em;text-transform:none}.pd-play{font-size:.7rem}
.pd-match{background:var(--deep);border:1px solid var(--e);border-radius:18px;padding:6px 16px;margin:6px 0 14px}
.pd-mside{display:grid;grid-template-columns:auto 1fr auto;gap:4px 12px;align-items:center;padding:12px 0}
.pd-mside+.pd-mside{border-top:1px solid var(--e)}
.pd-mside .pd-avs{grid-row:1/3}.pd-mside .nm a{display:block;text-decoration:none;color:inherit;font:600 1rem system-ui}.pd-mside .nm small{color:var(--s);font-weight:400}
.pd-mside.w .nm a{font-weight:800}.pd-mside.l{opacity:.75}.pd-mside .sc{display:flex;gap:4px;grid-column:3;grid-row:1/3}
.pd-mside .sc b{min-width:34px;height:38px;border-radius:9px;border:1px solid var(--e);display:grid;place-items:center;font:700 1.1rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--s)}
.pd-mside .sc b.on{background:var(--v);border-color:var(--v);color:var(--g)}.pd-mside .pd-seed{grid-column:2;justify-self:start}
.st-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;margin:6px 0 10px}
.st-card{background:var(--deep);border:1px solid var(--e);border-radius:20px;padding:16px 16px 8px;min-width:0}
.st-card h3{margin:0 0 12px;font:700 .72rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--s);display:flex;justify-content:space-between;gap:8px}
.st-card h3 small{font:600 .7rem system-ui;letter-spacing:0;text-transform:none;opacity:.8}
.st-lead{display:flex;align-items:center;gap:12px;background:var(--v);color:var(--g)!important;border-radius:14px;padding:12px;text-decoration:none;margin-bottom:6px}
.st-avs{display:flex;flex:none}.st-av{width:46px;height:46px;border-radius:50%;object-fit:cover;border:2px solid var(--v);background:var(--g)}
.st-avs .st-av+.st-av{margin-left:-14px}.st-av.ini{display:inline-flex;align-items:center;justify-content:center;color:var(--v);font:800 .85rem system-ui}
.st-who{flex:1;min-width:0}.st-who b{display:block;font:700 1.02rem/1.2 system-ui;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.st-who span{font:600 .74rem system-ui;opacity:.75}.st-val{text-align:right;flex:none}.st-val em{display:block;font:800 1.9rem/1 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;font-style:normal}
.st-val small{font:600 .7rem system-ui;opacity:.75;white-space:nowrap}
.st-rows{list-style:none;margin:0;padding:0}.st-rows a{display:flex;align-items:center;gap:10px;padding:8px 2px;border-top:1px solid var(--e);text-decoration:none;color:inherit}
.st-rows li:first-child a{border-top:0}.st-rows .n{width:18px;color:var(--s);font:700 .85rem system-ui}
.st-rows .nm{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font:600 .95rem system-ui,sans-serif}
.st-rows .v{flex:none;font:700 .95rem system-ui;font-variant-numeric:tabular-nums;white-space:nowrap}.st-rows .v small{color:var(--s);font-weight:500;font-size:.72rem}
.st-bars div{display:grid;grid-template-columns:minmax(0,150px) 1fr 34px;gap:10px;align-items:center;padding:6px 0}
.st-bars .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600}.st-bars .bar{height:10px;background:var(--e);border-radius:5px;overflow:hidden}
.st-bars .bar i{display:block;height:100%;background:var(--v);border-radius:5px}.st-bars b{text-align:right;font-variant-numeric:tabular-nums}
.pd-lchips{margin:10px 0 18px}.pd-lm{display:grid;grid-template-columns:1fr auto;gap:2px 12px;align-items:center;padding:9px 0;border-top:1px solid var(--e);text-decoration:none;color:inherit}
.pd-lm .r{grid-column:1/-1;font-size:.72rem;color:var(--s);text-transform:uppercase;letter-spacing:.05em}.pd-lm .pd-t.w{font-weight:800}.pd-lm .pd-t.l{color:var(--s)}
.pd-livetag{background:#e5484d;color:#fff;font:800 .62rem system-ui;padding:2px 6px;border-radius:4px;margin-right:4px}
.pd-tabs a[href$="live.html"]{color:#ff7a7f}.pd-tabs a.on[href$="live.html"]{color:var(--g)}
.pd-sub{margin:6px 0 0}.pd-sub a{color:var(--v);font:600 .9rem system-ui;text-decoration:none}
.pd-hls{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin:0 0 10px}
.pd-hl{display:flex;flex-direction:column;background:var(--deep);border:1px solid var(--e);border-radius:16px;overflow:hidden;text-decoration:none;color:inherit}
.pd-hls.row{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(240px,78%);grid-template-columns:none;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none}.pd-hls.row::-webkit-scrollbar{display:none}.pd-hls.row .pd-hl{scroll-snap-align:start}
@media(min-width:760px){.pd-hls.row{grid-auto-columns:calc(25% - 9px)}}
.pd-hl[hidden]{display:none}.pd-hl .th{position:relative}.pd-hl img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;background:#000}
.pd-hl i{position:absolute;left:12px;bottom:12px;width:40px;height:40px;border-radius:50%;background:var(--v);color:var(--g);display:grid;place-items:center;font-style:normal;font-size:1rem}
.pd-hl .tx{padding:10px 14px 12px;display:flex;flex-direction:column;gap:3px}.pd-hl small{font:700 .66rem system-ui;letter-spacing:.08em;text-transform:uppercase;color:var(--v)}
.pd-hl b{font:700 1rem system-ui}.pd-hl b span{color:var(--s);font-weight:500}
.pd-vgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.pd-vgrid a{display:flex;flex-direction:column;gap:4px;text-decoration:none;color:inherit;background:var(--deep);border:1px solid var(--e);border-radius:12px;overflow:hidden;padding-bottom:8px}
.pd-vgrid img{width:100%;height:auto;aspect-ratio:16/9;object-fit:cover;display:block}.pd-vgrid b{font:600 .82rem system-ui;padding:0 8px}.pd-vgrid .pd-note{padding:0 8px}
.pd-elo{margin:10px 0 4px}.pd-elo-bar{height:8px;border-radius:99px;background:var(--e);overflow:hidden}.pd-elo-bar i{display:block;height:100%;background:var(--v);border-radius:99px}
.pd-vlink{display:block;position:relative;border-radius:16px;overflow:hidden;border:1px solid var(--e);background:var(--deep);text-decoration:none}
.pd-vlink img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;opacity:.85}.pd-vlink span{position:absolute;left:14px;bottom:14px;background:var(--v);color:var(--g);font:800 .95rem system-ui;padding:10px 16px;border-radius:999px}
.pd-video{position:relative;padding-top:56.25%;border-radius:16px;overflow:hidden;border:1px solid var(--e);background:#000}
.pd-video iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.pd-old{display:none!important}.show-old .pd-old:not([hidden]){display:flex!important}.show-old h3.pd-old{display:block!important}.pd-trow[hidden]{display:none!important}
.pd-ctry details{border-top:1px solid var(--e)}.pd-ctry summary{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:11px 2px;cursor:pointer;list-style:none}
.pd-ctry summary::-webkit-details-marker{display:none}.pd-ctry summary .pd-note{margin-left:auto}.pd-ctry details a{display:block;padding:6px 10px;text-decoration:none}
.pd-anim{max-width:520px;margin:0 auto 4px}.pd-anim svg{width:100%;height:auto;display:block}
.pd-hero2{display:flex;gap:16px;align-items:center;padding:6px 0 18px}.pd-em svg{width:84px;height:84px;display:block}
.pd-hero2 h1{margin:0 0 4px;font-size:1.7rem;line-height:1.15}.pd-hero2 p{margin:0;color:var(--s);font-size:.92rem}
.pd-now{display:block;text-decoration:none;color:inherit;background:var(--deep);border:1px solid var(--e);border-radius:18px;padding:14px 16px;margin:0 0 12px}
.pd-now-h{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.pd-now-h b{font:700 1.2rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.pd-now-sub{margin:10px 0 2px;font:700 .72rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--v)}
.pd-more{display:block;margin-top:8px;color:var(--v);font:600 .85rem system-ui;text-decoration:none}
.mm{grid-template-columns:1fr auto}.mm-r{grid-column:1/-1;font-size:.72rem;color:var(--s);text-transform:uppercase;letter-spacing:.06em}
.mm .pd-t{font-size:1rem}.mm .pd-sc b{min-width:26px;height:26px;font-size:.85rem}
.pd-champs{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(210px,72%);gap:10px;overflow-x:auto;padding:2px 0 10px;scroll-snap-type:x mandatory;scrollbar-width:none}
.pd-champs::-webkit-scrollbar{display:none}
.pd-champ{scroll-snap-align:start;display:flex;flex-direction:column;gap:4px;text-decoration:none;color:inherit;background:var(--deep);border:1px solid var(--e);border-radius:16px;padding:14px}
.pd-champ .pd-tag{align-self:flex-start}.pd-champ b{font:700 1.1rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}.pd-champ div{font-weight:700;margin-top:4px}
.pd-champ small{display:block;font:700 .66rem system-ui;letter-spacing:.12em;text-transform:uppercase;color:var(--v)}
.pd-list a{display:flex;gap:10px;align-items:center;padding:11px 2px;border-top:1px solid var(--e);text-decoration:none;color:inherit}
.pd-list a:first-child{border-top:0}.pd-list b{flex:1;font-weight:700}
.pd-seg{display:inline-flex;border:1px solid var(--e);border-radius:999px;padding:3px;margin:0 0 8px}
.pd-seg button{border:0;background:none;color:var(--s);font:600 .85rem system-ui;padding:6px 14px;border-radius:999px;cursor:pointer}
.pd-seg button.on{background:var(--v);color:var(--g)}
.pd-rk5 a{display:flex;gap:10px;align-items:center;padding:9px 2px;border-top:1px solid var(--e);text-decoration:none;color:inherit}
.pd-rk5 a:first-child{border-top:0}.pd-rk5 .n{width:24px;font:700 1rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--v)}.pd-rk5 .nm{flex:1;font-weight:600}
.pd-rk5 a.pd-more{border:0;color:var(--v)}
.pd-quick{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:22px 0 6px}
.pd-quick a{background:var(--deep);border:1px solid var(--e);border-radius:14px;padding:12px;text-decoration:none;color:inherit}
.pd-quick b{display:block;font:700 1rem system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}.pd-quick span{color:var(--s);font-size:.8rem}
@media(min-width:760px){.pd-champs{grid-auto-columns:calc(33.3% - 7px)}.pd-quick{grid-template-columns:repeat(4,1fr)}}

@media(max-width:640px){
.pd-tabs{flex-wrap:nowrap;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;margin:4px -16px 16px;padding:0 16px 4px}
.pd-tabs::-webkit-scrollbar{display:none}.pd-tabs a{flex:0 0 auto}
.numgrid{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important}
.numgrid .nbox{min-width:0;padding:12px 8px!important}.numgrid .nbox b{font-size:1.5rem!important;overflow-wrap:anywhere}
.numgrid .nbox b.form{font-size:.8rem!important;display:flex;flex-wrap:wrap;gap:3px;justify-content:center}
.pd-grid2{grid-template-columns:minmax(0,1fr)}
.pt td,.pt th{padding-left:5px;padding-right:5px}
.pd-hero h1{font-size:1.8rem}
}
"""

LIVE_JS = """<script>(function(){
var rows=[].slice.call(document.querySelectorAll('.pd-m[data-mid]'));if(!rows.length)return;
function today(){var d=new Date();return d.toISOString().slice(0,10)}
function y(){var d=new Date(Date.now()-864e5);return d.toISOString().slice(0,10)}
function g(x){var m=/^(\\d+)/.exec(x||"");return m?+m[1]:-1}
function cells(sc,team){return sc.map(function(s){var a=s[team],b=s[team=="team_1"?"team_2":"team_1"];var tb=/\\((\\d+)\\)/.exec(a||"");
 return '<b class="'+(g(a)>g(b)?'on':'')+'">'+String(a||"").replace(/\\(.*\\)/,'')+(tb?'<i>'+tb[1]+'</i>':'')+'</b>'}).join('')}
function load(){var want={};rows.forEach(function(r){var d=r.dataset.day;if(d==today()||d==y())want[r.dataset.tid+'|'+d]=1});
 Object.keys(want).forEach(function(k){var p=k.split('|');fetch('/api/padel/matches/'+p[0]+'?date='+p[1]).then(function(x){return x.ok?x.json():null}).then(function(j){
  if(!j||!j.matches)return;j.matches.forEach(function(m){var r=document.querySelector('.pd-m[data-mid="'+m.id+'"]');if(!r)return;
   if(!m.score){if(m.status=='live'){var w=r.querySelector('.pd-when,.tm');if(w){w.className=(w.classList.contains('tm')?'tm':'pd-when')+' pd-live';var d=m.scheduled_at?new Date(m.scheduled_at):null;
     w.innerHTML='● LIVE'+(d&&!isNaN(d)?'<small class="pd-since"> · from '+d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',hour12:false})+'</small>':'')}}return}
   ['team_1','team_2'].forEach(function(t){var c=r.querySelector('.pd-sc[data-team="'+t+'"]');if(c)c.innerHTML=cells(m.score,t)});
   var ts=r.querySelectorAll('.pd-t');if(m.winner&&ts.length==2){ts[0].className='pd-t '+(m.winner=='team_1'?'w':'l');ts[1].className='pd-t '+(m.winner=='team_2'?'w':'l')}
  });var n=document.getElementById('pd-upd');if(n)n.textContent='Scores updated '+new Date(j.ts).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',hour12:false})}).catch(function(){})})}
load();setInterval(function(){if(!document.hidden)load()},120000)})();</script>"""

EMBLEM = """<svg viewBox="0 0 600 600" role="img" aria-label="Beyond Padel">
<circle cx="300" cy="300" r="290" fill="#0c2e4a" stroke="#f7f2e6" stroke-width="8"/>
<circle cx="300" cy="300" r="170" fill="none" stroke="#f7f2e6" stroke-width="2"/>
<defs><path id="pa1" d="M 100,300 A 200,200 0 0 1 500,300"/><path id="pa2" d="M 68,300 A 232,232 0 0 0 532,300"/></defs>
<text font-family="Georgia,serif" font-weight="700" font-size="44" letter-spacing="8" fill="#f7f2e6" text-anchor="middle"><textPath href="#pa1" startOffset="50%">BEYOND PADEL</textPath></text>
<text font-family="Georgia,serif" font-weight="700" font-size="28" letter-spacing="5" fill="#f7f2e6" text-anchor="middle"><textPath href="#pa2" startOffset="50%">EVERY PLAYER · EVERY DRAW</textPath></text>
<circle cx="64" cy="300" r="10" fill="#d9f23d"/><circle cx="536" cy="300" r="10" fill="#d9f23d"/>
<g transform="translate(300 300)" fill="none" stroke="#f7f2e6" stroke-width="7"><rect x="-70" y="-120" width="140" height="240" rx="6"/>
<line x1="-70" y1="0" x2="70" y2="0" stroke="#d9f23d" stroke-width="8"/><line x1="-70" y1="-70" x2="70" y2="-70" stroke-width="4"/>
<line x1="-70" y1="70" x2="70" y2="70" stroke-width="4"/><line x1="0" y1="-70" x2="0" y2="70" stroke-width="4"/>
<path d="M -70 -120 L -70 -80 M 70 -120 L 70 -80 M -70 120 L -70 80 M 70 120 L 70 80" stroke="#7fb3d5" stroke-width="12"/></g></svg>"""


# ------------------------------------------------------------------ dados
def load(name, default):
    try:
        with open(os.path.join(DATA, name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def slug(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def flag(code, h=13):
    try:
        import site_more
        return site_more.flag(code, h)
    except Exception:
        return ""


_ISO2_TO_IOC = {}


def country_name(code):
    """A Padel API usa códigos ISO de 2 letras; o site do ténis tem os nomes pelos códigos de 3 letras."""
    c = (code or "").upper()
    if len(c) == 2:
        if not _ISO2_TO_IOC:
            for ioc, iso in site_more.ISO2.items():
                _ISO2_TO_IOC.setdefault(iso.upper(), ioc)
        n = site_more.country_name(_ISO2_TO_IOC.get(c, c))
        return n if len(n) > 2 else (EXTRA_NAMES.get(c) or c)
    return site_more.country_name(c)


EXTRA_NAMES = {"ES": "Spain", "AR": "Argentina", "PT": "Portugal", "IT": "Italy", "FR": "France", "BE": "Belgium", "NL": "Netherlands",
               "SE": "Sweden", "UY": "Uruguay", "PY": "Paraguay", "CL": "Chile", "MX": "Mexico", "BR": "Brazil", "EG": "Egypt",
               "QA": "Qatar", "KW": "Kuwait", "AE": "United Arab Emirates", "SA": "Saudi Arabia", "GB": "Great Britain", "DE": "Germany",
               "AT": "Austria", "CH": "Switzerland", "FI": "Finland", "DK": "Denmark", "NO": "Norway", "US": "United States", "VE": "Venezuela",
               "EC": "Ecuador", "CO": "Colombia", "PE": "Peru", "MA": "Morocco", "TN": "Tunisia", "IE": "Ireland", "PL": "Poland",
               "CZ": "Czechia", "RO": "Romania", "LT": "Lithuania", "LV": "Latvia", "EE": "Estonia", "UA": "Ukraine", "JP": "Japan",
               "AU": "Australia", "ZA": "South Africa", "AD": "Andorra", "MC": "Monaco", "LU": "Luxembourg", "GR": "Greece", "TR": "Türkiye",
               "HU": "Hungary", "SI": "Slovenia", "HR": "Croatia", "BG": "Bulgaria", "PR": "Puerto Rico", "DO": "Dominican Republic",
               "CR": "Costa Rica", "PA": "Panama", "GT": "Guatemala", "BO": "Bolivia", "IN": "India", "CN": "China", "KR": "South Korea",
               "SG": "Singapore", "BH": "Bahrain", "OM": "Oman", "JO": "Jordan", "LB": "Lebanon", "IR": "Iran", "RS": "Serbia", "CY": "Cyprus",
               "MT": "Malta", "IS": "Iceland", "CA": "Canada", "NZ": "New Zealand", "RU": "Russia", "BY": "Belarus", "KZ": "Kazakhstan"}


class DB:
    def __init__(self):
        self.tours = load("tournaments.json", {})
        from padel.fetch import load_matches
        self.matches = [m for m in load_matches().values() if m.get("status") != "bye"]
        self.players = load("players.json", {})
        self.ranks = load("rankings.json", {})
        self.editions = load("editions.json", {})
        self.news = load("news.json", {})
        self.videos = load("videos.json", {})
        self.entries = load("entries.json", {})
        self.highlights = load("highlights.json", {})
        self.state = load("state.json", {})
        self.by_t, self.by_p, self.by_pair = {}, {}, {}
        self.short = {}                                   # id -> apelido oficial (short_name), tirado dos jogos
        for m in self.matches:
            self.by_t.setdefault(str(m.get("tid")), []).append(m)
            for team in ("team_1", "team_2"):
                ps = team_players(m, team)
                for p in ps:
                    self.by_p.setdefault(str(p.get("id")), []).append((m, team))
                    if p.get("short_name"):
                        self.short.setdefault(str(p.get("id")), p["short_name"])
                if len(ps) == 2:
                    self.by_pair.setdefault(pair_key(ps), []).append((m, team))
        self.rank_of = {}
        for cat, r in self.ranks.items():
            for row in (r or {}).get("rows", []):
                self.rank_of[str(row.get("id"))] = row
        # quem aparece (jogadores com página): em jogos ou no top 300 dos rankings
        self.pinfo = {}
        for m in self.matches:
            for team in ("team_1", "team_2"):
                for p in team_players(m, team):
                    self.pinfo.setdefault(str(p.get("id")), {}).update({k: v for k, v in p.items() if v is not None and k != "connections"})
        for pid, row in self.rank_of.items():
            if (row.get("ranking") or 999) <= 300:
                self.pinfo.setdefault(pid, {}).update({"id": row.get("id"), "name": row.get("name"), "nationality": row.get("nationality"),
                                                       "category": row.get("category")})
        for pid, p in self.players.items():
            if pid in self.pinfo:
                self.pinfo[pid].update({k: v for k, v in p.items() if v is not None and not k.startswith("_") and k != "connections"})

    def rank_hist(self, pid):
        """[(data, ranking)] semanal, das nossas próprias cópias do ranking (o histórico da API é pago)."""
        if not hasattr(self, "_rh"):
            self._rh = load("rank_hist.json", {})
        out = []
        for cat in ("men", "women"):
            for d in sorted((self._rh.get(cat) or {})):
                r = self._rh[cat][d].get(str(pid))
                if r:
                    out.append((d, r))
        return sorted(out)

    def tour(self, tid):
        return self.tours.get(str(tid)) or {}


def team_players(m, team):
    return ((m.get("players") or {}).get(team) or [])


def ppath(p):
    return f"/padel/p/{p.get('id')}-{slug(p.get('name'))}.html"


def tpath(t):
    return f"/padel/t/{t.get('id')}-{slug(t.get('name'))}.html"


def pair_key(team):
    ids = sorted(str(p.get("id")) for p in team)
    return "-".join(ids)


def pair_path(team):
    return f"/padel/pair/{pair_key(team)}.html"


def plink(p, short=False):
    nm = p.get("short_name") if short and p.get("short_name") else p.get("name")
    return f'{flag(p.get("nationality"), 11)}<a href="{ppath(p)}">{esc(nm or "?")}</a>'


def rank_str(pid, db):
    r = db.rank_of.get(str(pid))
    return f"#{r['ranking']}" if r and r.get("ranking") else ""


PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "photos")
_PHOTO_IDS = None


def has_photo(pid):
    global _PHOTO_IDS
    if _PHOTO_IDS is None:
        try:
            _PHOTO_IDS = {f[:-4] for f in os.listdir(PHOTOS_DIR) if f.endswith(".jpg")}
        except OSError:
            _PHOTO_IDS = set()
    return str(pid) in _PHOTO_IDS


def avatar(p, cls="pd-av"):
    """Foto livre do jogador (miniatura) ou as iniciais num círculo."""
    pid, nm = str(p.get("id")), p.get("name") or "?"
    if has_photo(pid):
        return f'<img class="{cls}" src="/padel/img/{pid}-s.jpg" alt="{esc(nm)}" width="40" height="40" loading="lazy">'
    ini = "".join(w[0] for w in nm.split()[:2] if w).upper()
    return f'<span class="{cls} ini" aria-hidden="true">{esc(ini)}</span>'


def write_photos(out):
    """Miniaturas (160x160) e fotos de página (600x750) das fotos livres, a partir de padel/photos."""
    from PIL import Image, ImageOps
    od = os.path.join(out, "padel", "img")
    os.makedirs(od, exist_ok=True)
    for f in os.listdir(PHOTOS_DIR):
        if not f.endswith(".jpg"):
            continue
        pid = f[:-4]
        im = Image.open(os.path.join(PHOTOS_DIR, f)).convert("RGB")
        ImageOps.fit(im, (160, 160), centering=(0.5, 0.22)).save(os.path.join(od, f"{pid}-s.jpg"), quality=82, optimize=True)
        ImageOps.fit(im, (600, 750), centering=(0.5, 0.25)).save(os.path.join(od, f"{pid}.jpg"), quality=82, optimize=True)


def photo_credit(pid):
    try:
        c = json.load(open(os.path.join(PHOTOS_DIR, "credits.json"), encoding="utf-8")).get(str(pid)) or {}
    except (OSError, ValueError):
        c = {}
    return c


def disp(p):
    """Nome curto: inicial + apelido (o apelido que a API dá em short_name). Ex.: 'S. Pineda'."""
    nm = (p.get("name") or "").strip()
    sh = (p.get("short_name") or "").strip()
    if not nm:
        return sh or "?"
    first = nm.split()[0]
    last = sh or nm.split()[-1]
    return last if first == last or len(nm.split()) == 1 else f"{first[0]}. {last}"


def team_html(m, team, db, short=False):
    ps = team_players(m, team)
    if not ps:
        return '<span class="pd-note">To be decided</span>'
    seed = ((m.get("seeds") or {}).get(team))
    names = " / ".join(f'<a href="{ppath(p)}" title="{esc(p.get("name"))}{(" · " + rank_str(p.get("id"), db)) if rank_str(p.get("id"), db) else ""}">{esc(disp(p))}</a>' for p in ps)
    return f'<span class="pd-pl">{names}{f"<span class=pd-seed>{esc(str(seed))}</span>" if seed else ""}</span>'


def sets_of(m):
    sc = m.get("score")
    if not isinstance(sc, list):
        return []
    out = []
    for s in sc:
        a, b = str((s or {}).get("team_1") or ""), str((s or {}).get("team_2") or "")
        out.append((a, b))
    return out


def games(x):
    m = re.match(r"(\d+)", x or "")
    return int(m.group(1)) if m else -1


def score_cells(m, team):
    w = m.get("winner")
    cells = ""
    for a, b in sets_of(m):
        mine, oth = (a, b) if team == "team_1" else (b, a)
        tb = re.search(r"\((\d+)\)", mine)
        g = re.sub(r"\(.*\)", "", mine)
        on = games(mine) > games(oth)
        cells += f'<b class="{"on" if on else ""}">{esc(g)}{f"<i>{tb.group(1)}</i>" if tb else ""}</b>'
    return cells


def score_text(m, team="team_1"):
    out = []
    for a, b in sets_of(m):
        mine, oth = (a, b) if team == "team_1" else (b, a)
        out.append(f"{mine}-{oth}")
    return " ".join(out)


def when_local(m):
    t = m.get("scheduled_at_local") or m.get("scheduled_at") or ""
    return t[11:16] if len(t) >= 16 else ""


def match_html(m, db, show_round=True, show_tour=False):
    w = m.get("winner") if m.get("winner") in ("team_1", "team_2") else None
    t = db.tour(m.get("tid"))
    head = []
    if show_tour and t:
        head.append(f'<a href="{tpath(t)}">{esc(t.get("location") or t.get("name") or "")}</a>')
    if show_round:
        head.append(esc(m.get("round_name") or ""))
    head.append(CAT.get(m.get("category"), ""))
    if m.get("court") and m.get("status") != "finished":
        head.append(esc(m["court"]))
    st = m.get("status")
    right1 = right2 = ""
    if sets_of(m):
        right1, right2 = score_cells(m, "team_1"), score_cells(m, "team_2")
    elif st == "live":                                         # 12/11/2026: a Padel API só dá o resultado no fim; durante o jogo, LIVE
        right1 = f'<span class="pd-when pd-live">{live_label(m)}</span>'
    elif st in ("scheduled", "pending", None):
        right1 = f'<span class="pd-when">{esc(m.get("schedule_label") or when_local(m))}</span>'
    cls = lambda team: ("w" if w == team else "l") if w else ""
    extra = "" if st in ("finished", "scheduled", "pending", None) else f' · <span class="pd-tag g">{esc(st.upper())}</span>'
    _h = highlight_for(db, m) if team_players(m, "team_1") else None
    _v = None if _h else video_for(db, m)
    lbl = "▶ Highlights" if _h and _h["kind"] == "match" else ("▶ Video" if (_h or _v) else "Match")
    _c = " hl" if _h and _h["kind"] == "match" else (" vd" if (_h or _v) else " pl")
    more = (f' <a class="pd-mlink{_c}" href="{mpath(m)}">{lbl} ›</a>'
            if team_players(m, "team_1") and team_players(m, "team_2") else "")
    return (f'<div class="pd-m" data-mid="{m.get("id")}" data-tid="{m.get("tid")}" data-day="{esc(m.get("played_at") or "")}"><div class="r">{" · ".join(x for x in head if x)}{extra}{more}</div>'
            f'<div class="pd-t {cls("team_1")}">{team_html(m, "team_1", db)}</div><div class="pd-sc" data-team="team_1">{right1}</div>'
            f'<div class="pd-t {cls("team_2")}">{team_html(m, "team_2", db)}</div><div class="pd-sc" data-team="team_2">{right2}</div></div>')


def tour_meta(t):
    bits = [f'<span class="pd-tag">{esc(LEVEL_SHORT.get(t.get("level"), (t.get("level") or "").upper()))}</span>']
    loc = ", ".join(x for x in [t.get("location"), country_name(t.get("country"))] if x)
    bits.append(f'{flag(t.get("country"), 12)}{esc(loc)}')
    bits.append(esc(date_range(t)))
    if t.get("court_type"):
        bits.append(esc(str(t["court_type"]).title()))
    pr = t.get("prize") or {}
    if pr.get("amount"):
        bits.append(f'{pr["amount"]:,} {esc(pr.get("currency") or "")} prize money'.replace(",", " "))
    return '<div class="pd-meta">' + bits[0] + " " + " · ".join(bits[1:]) + "</div>"


def date_range(t):
    try:
        a = dt.date.fromisoformat(t.get("start_date"))
        b = dt.date.fromisoformat(t.get("end_date"))
        return f"{a.day} {a:%b}–{b.day} {b:%b %Y}" if a.month != b.month else f"{a.day}–{b.day} {b:%b %Y}"
    except (TypeError, ValueError):
        return ""


def winners_html(t, db):
    w = t.get("winners")
    if not isinstance(w, dict) or not w:
        return ""
    out = []
    for cat, v in w.items():
        ps = v if isinstance(v, list) else (v or {}).get("players") if isinstance(v, dict) else None
        if isinstance(v, dict) and not ps:
            ps = v.get("team") or v.get("pair") or []
        names = " / ".join(f'<a href="{ppath(p)}">{esc(p.get("name"))}</a>' for p in (ps or []) if isinstance(p, dict))
        if names:
            out.append(f'<div class="pd-win">🏆 <b>{esc(CAT.get(cat, cat))}</b> <span>{names}</span></div>')
    return "".join(out)


# ------------------------------------------------------------------ página
def _nl_inline(title):
    try:
        import nl_cta
        return nl_cta.inline(title, sport="padel")
    except Exception:
        return ""


def _nl_slide():
    try:
        import nl_cta
        return nl_cta.slide("padel")
    except Exception:
        return ""


def shell(title, body, path, desc=None, tab="", noindex=False, ld=None):
    try:
        import result_card as rc
        beacon = rc._beacon()
    except Exception:
        beacon = ""
    desc = desc or "Results, draws, order of play and rankings of Premier Padel and the CUPRA FIP Tour: every player, every draw."
    tabs = [("index", "Home"), ("live", "● Live"), ("results", "Results"), ("highlights", "Highlights"), ("tournaments", "Tournaments"),
            ("rankings", "Rankings"), ("stats", "Stats")]
    tab0 = {"next-week": "tournaments", "countries": "rankings", "players": "rankings"}.get(tab, tab)
    tab = {"order-of-play": "results"}.get(tab0, tab0)
    nav = "".join(f'<a class="{"on" if tab == k else ""}" href="/padel/{k}.html">{v}</a>' for k, v in tabs if k != "live" or LIVE_ON or tab == "live")
    _act = {"index": "home", "results": "results", "tournaments": "results", "order-of-play": "today", "highlights": "videos",
            "rankings": "players", "stats": "stats"}.get(tab0, "")
    bar = site_nav.bar("padel", _act)
    topnav = "".join(f'<a class="ntop{" on" if tab == k else ""}" href="/padel/{k}.html">{v}</a>'
                     for k, v in (("results", "Results"), ("tournaments", "Tournaments"), ("rankings", "Rankings"), ("stats", "Stats")))
    live_pill = site_nav.live_pill("/padel/live.html", tab == "live", show=LIVE_ON, sport="padel", tids=LIVE_TIDS)
    ldh = "".join('<script type="application/ld+json">' + json.dumps(b, ensure_ascii=False).replace("</", "<\\/") + "</script>" for b in (ld or []))
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            f'<title>{esc(title)}</title><meta name="description" content="{esc(desc)}">'
            f'<link rel="canonical" href="{SITE_BASE}{_clean(path)}"><meta property="og:type" content="website"><meta property="og:site_name" content="Beyond Padel">'
            f'<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{SITE_BASE}{_clean(path)}">'
            f'<meta property="og:image" content="{SITE_BASE}{OG_MAP.get(path, "/padel/og.png")}"><meta name="twitter:card" content="summary_large_image">'
            f'<meta name="theme-color" content="#0c2e4a">{"<meta name=robots content=noindex,follow>" if noindex else ""}{beacon}{ldh}'
            f'<link rel="icon" href="/padel/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/padel/style.css?v={CSS_VER}"></head><body><div class="wrap">'
            # menu de cima igual ao do ténis (5/11/2026): marca, LIVE quando há jogos em court, links, Instagram e pesquisa
            f'<nav><a class="brand" href="/padel/index.html">BEYOND PADEL</a><div>{live_pill}{topnav}<a href="{IG}">Instagram</a>{site_more.SEARCH_BTN}</div></nav>{sport_switch.switch("padel")}'
            f'{site_more.SEARCH_HTML}{body}{LIVE_JS}'
            + site_nav.footer("BEYOND PADEL", "Every player, every draw: Premier Padel and the CUPRA FIP Tour results, draws and rankings.",
                              [("Follow on Instagram", IG, True), ("Beyond100 Tennis", "/index.html", False)],
                              [("Explore", [("Results", "/padel/results.html"), ("Order of play", "/padel/order-of-play.html"), ("Tournaments", "/padel/tournaments.html"),
                                            ("Highlights", "/padel/highlights.html"), ("Players", "/padel/players.html")]),
                               ("Rankings & stats", [("Rankings", "/padel/rankings.html"), ("Power Ranking", "/padel/power.html"), ("Race to the Finals", "/padel/race.html"),
                                                     ("Stats", "/padel/stats.html"), ("Countries", "/padel/countries.html")]),
                               ("Beyond Padel", [("About", "/about.html"), ("Photo credits", "/padel/credits.html")])],
                              'Data: <a href="https://padelapi.org">Padel API</a> · Premier Padel and CUPRA FIP Tour (Platinum, Gold, Silver). Scores are for information only and may contain delays or errors.')
            + f'</div>{bar}' + site_ui.LOCALTIME_JS + site_ui.DEAD_YT_JS + _nl_slide() + '</body></html>')


def write(out, path, htmltext):
    fp = os.path.join(out, path.lstrip("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(htmltext)
    return fp


# ------------------------------------------------------------------ páginas
def live_label(m):
    """'● LIVE' e a hora marcada do jogo (a Padel API não dá o resultado durante o jogo nem a hora real de início). 12/11/2026"""
    t = m.get("scheduled_at")
    return "● LIVE" + (f'<small class="pd-since"> · from {site_ui.ltime(t, when_local(m))}</small>' if t else "")


def _short_team(m, team):
    ps = team_players(m, team)
    return " / ".join(esc(p.get("short_name") or (p.get("name") or "?").split()[-1]) for p in ps) or "TBD"


def live_tile(m, db):
    """Cartão de jogo do 'Playing now' (o mesmo molde do ténis): torneio e ronda em cima, os dois pares com fotos, país e ranking,
    resultado à direita (ou a hora de início). data-mid: o resultado atualiza no browser a cada 2 min."""
    t = db.tour(m.get("tid")) or {}

    def row(team):
        ps = team_players(m, team)
        avs = "".join(avatar(p, "pd-av sm") for p in ps if has_photo(p.get("id")))
        sub = " ".join(f'{flag(p.get("nationality"), 11)}{esc(rank_str(p.get("id"), db))}' for p in ps)
        o = "team_2" if team == "team_1" else "team_1"
        if sets_of(m):
            sc = "".join(f'<b class="{"on" if games(a if team == "team_1" else b) > games(b if team == "team_1" else a) else ""}">'
                         f'{esc(re.sub(r"\(.*\)", "", a if team == "team_1" else b))}</b>' for a, b in sets_of(m))
        elif m.get("status") == "live":                        # 12/11/2026: a decorrer (a Padel API só dá o resultado no fim)
            sc = f'<span class="tm pd-live">{live_label(m)}</span>' if team == "team_1" else ""
        else:
            sc = (f'<span class="tm">{site_ui.ltime(m.get("scheduled_at"), when_local(m) + " local") if m.get("scheduled_at") else "Later today"}</span>') if team == "team_1" else ""
        return (f'<div class="pl"><div class="who">{f"<div class=pd-avs>{avs}</div>" if avs else ""}<div><span class="nm"><span class="pd-t">{_short_team(m, team)}</span></span>'
                f'<small>{sub}</small></div></div><div class="sc pd-sc" data-team="{team}">{sc}</div></div>')
    head = " · ".join(x for x in [esc(t.get("location") or t.get("name") or ""), esc(m.get("round_name") or ""), CAT.get(m.get("category"), "")] if x)
    return (f'<a class="lv pd-m" href="{mpath(m)}" data-mid="{m.get("id")}" data-tid="{m.get("tid")}" data-day="{esc(m.get("played_at") or "")}">'
            f'<div class="lh"><span class="pd-tag">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</span> {head}<span class="lgo">›</span></div>'
            f'{row("team_1")}{row("team_2")}</a>')


def mini_match(m, db, label=True):
    """Linha compacta para a página inicial: só apelidos e resultado (o detalhe fica nas páginas do torneio)."""
    w = m.get("winner") if m.get("winner") in ("team_1", "team_2") else None
    sc = lambda team: "".join(f'<b class="{"on" if games(a if team == "team_1" else b) > games(b if team == "team_1" else a) else ""}">'
                              f'{esc(re.sub(r"\(.*\)", "", a if team == "team_1" else b))}</b>' for a, b in sets_of(m))
    right = (sc("team_1"), sc("team_2")) if sets_of(m) else (
        (f'<span class="pd-when pd-live">{live_label(m)}</span>' if m.get("status") == "live" else f'<span class="pd-when">{esc(m.get("schedule_label") or when_local(m))}</span>'), "")
    cls = lambda team: ("w" if w == team else "l") if w else ""
    head = (f'<div class="mm-r">{esc(m.get("round_name") or "")} · {CAT.get(m.get("category"), "")}</div>' if label
            else f'<div class="mm-r">{CAT.get(m.get("category"), "")}</div>')
    return (f'<div class="mm pd-m" data-mid="{m.get("id")}" data-tid="{m.get("tid")}" data-day="{esc(m.get("played_at") or "")}">{head}'
            f'<div class="pd-t {cls("team_1")}">{_short_team(m, "team_1")}</div><div class="pd-sc" data-team="team_1">{right[0]}</div>'
            f'<div class="pd-t {cls("team_2")}">{_short_team(m, "team_2")}</div><div class="pd-sc" data-team="team_2">{right[1]}</div></div>')


LIVE_ON = False
LIVE_TIDS = []                        # torneios a decorrer (o botão LIVE confirma no browser se há jogos em court)


def live_now(db):
    """Há padel a decorrer agora? Jogos de hoje (quadro principal) ainda por acabar e o primeiro já começou ou começa na próxima hora."""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    day = [m for m in db.matches if (m.get("played_at") or "") == today and team_players(m, "team_1") and team_players(m, "team_2")]
    left = [m for m in day if m.get("winner") not in ("team_1", "team_2") and m.get("status") not in ("finished", "bye", "walkover", "retired", "cancelled")]
    if not left:
        return False
    if any(sets_of(m) for m in left):                     # um jogo em court agora (resultado a meio); jogos já acabados não contam (5/11/2026)
        return True
    ts = []
    for m in left:
        try:
            ts.append(dt.datetime.fromisoformat((m.get("scheduled_at") or "").replace("Z", "+00:00")).timestamp())
        except ValueError:
            pass
    return bool(ts) and -3 * 3600 < min(ts) - time.time() < 30 * 60    # o primeiro jogo começa daqui a 30 min ou já devia ter começado


def _key_matches(ms, today):
    """Os jogos que interessam hoje num torneio: a ronda mais avançada do dia (finais > meias > ...), máx. 2."""
    day = [m for m in ms if (m.get("played_at") or "") == today and (m.get("draw") or "main") == "main" and team_players(m, "team_1")]
    if not day:
        return [], ""
    top = min(m.get("round") or 99 for m in day)
    sel = sorted([m for m in day if (m.get("round") or 99) == top], key=lambda m: (m.get("category") != "men", m.get("index") or 0))
    return sel[:2], (sel[0].get("round_name") or "")


# Animação do topo (par da bola do ténis): a bola passa a rede, bate no chão, sobe ao vidro do fundo (que acende) e volta.
HERO_ANIM = """<div class="pd-anim" aria-hidden="true"><svg id="pdanim" viewBox="0 0 500 130">
<line x1="0" y1="112" x2="500" y2="112" stroke="#24507a" stroke-width="3"/>
<line x1="250" y1="112" x2="250" y2="70" stroke="#a9c0d6" stroke-width="4" opacity=".6"/>
<rect x="8" y="22" width="12" height="90" rx="3" fill="rgba(127,179,213,.12)" stroke="#7fb3d5" stroke-width="2.5"/>
<rect x="480" y="22" width="12" height="90" rx="3" fill="rgba(127,179,213,.12)" stroke="#7fb3d5" stroke-width="2.5">
<animate attributeName="fill" values="rgba(127,179,213,.12);rgba(127,179,213,.12);rgba(217,242,61,.6);rgba(127,179,213,.12);rgba(127,179,213,.12)" keyTimes="0;0.4;0.46;0.53;1" dur="3.2s" repeatCount="indefinite"/></rect>
<ellipse rx="10" ry="3" fill="#000" opacity=".3"><animateMotion dur="3.2s" repeatCount="indefinite" path="M 40 114 L 330 114 L 470 114 L 330 114 L 40 114" keyTimes="0;0.33;0.46;0.66;1" calcMode="linear"/></ellipse>
<circle r="10" fill="#d9f23d" style="filter:drop-shadow(0 0 6px rgba(217,242,61,.6))">
<animateMotion dur="3.2s" repeatCount="indefinite" path="M 40 100 Q 180 -10 330 101 Q 400 35 468 50 Q 420 20 330 101 Q 180 -20 40 100"/></circle>
</svg></div><script>try{if(matchMedia("(prefers-reduced-motion: reduce)").matches)document.getElementById("pdanim").pauseAnimations()}catch(e){}</script>"""


def page_index(db):
    """Página inicial do padel. Desde 13/11/2026 usa o desenho novo comum ao ténis (home_ui); HOME_V2=0 volta à antiga."""
    if os.environ.get("HOME_V2", "1") != "0":
        try:
            return page_index_v2(db)
        except Exception as ex:
            print("Padel: página inicial v2 falhou:", type(ex).__name__, ex)
    return page_index_v1(db)


def page_index_v1(db):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    live = sorted([t for t in db.tours.values() if t.get("status") == "live"], key=lambda t: LEVEL_ORDER.get(t.get("level"), 9))
    body = (HERO_ANIM + '<section class="pd-hero2"><div class="pd-em">' + EMBLEM + '</div><div><h1>Every player. <em>Every draw.</em></h1>'
            '<p>Premier Padel and the CUPRA FIP Tour: results, draws and rankings.</p></div></section>')
    # 1) agora: o mesmo molde do ténis ("Playing now", cartões por jogo). Só diz "a jogar" quando há jogos mesmo a decorrer;
    #    antes disso é "Today" com a hora de início (5/11/2026: "Now playing" com jogos por começar confundia)
    tday = [m for t in live for m in db.by_t.get(str(t["id"]), []) if m.get("played_at") == today and (m.get("draw") or "main") == "main"
            and team_players(m, "team_1") and team_players(m, "team_2") and m.get("winner") not in ("team_1", "team_2")]
    on = [m for m in tday if sets_of(m) or m.get("status") == "live"]
    nx = sorted([m for m in tday if not (sets_of(m) or m.get("status") == "live")], key=lambda m: (m.get("scheduled_at") or "9", -(m.get("round") or 0)))
    on.sort(key=lambda m: (LEVEL_ORDER.get((db.tour(m.get("tid")) or {}).get("level"), 9), m.get("round") or 99))
    tiles = (on + nx)[:6]
    if tiles:
        h = ('<span><span class="dot" style="display:inline-block;margin-right:8px"></span>Playing now</span>' if on
             else f'<span>Today{(" · first match at " + site_ui.ltime(nx[0].get("scheduled_at"), when_local(nx[0]) + " local time")) if nx and nx[0].get("scheduled_at") else ""}</span>')
        body += f'<h2 class="sec">{h}<a href="/padel/order-of-play.html">Order of play</a></h2><div class="lvg">' + "".join(live_tile(m, db) for m in tiles) + "</div>"
        rest = [t for t in live if str(t["id"]) not in {str(m.get("tid")) for m in tiles}]
        if rest:
            body += '<p class="pd-note">Also today: ' + " · ".join(f'<a href="{tpath(t)}">{esc(t.get("location") or t.get("name"))}</a>' for t in rest) + "</p>"
    try:                                                               # 12/11/2026: igual ao ténis (jogadores perto da 1.ª página do Google)
        body += spotlight_block(db)
    except Exception as e:
        print("Padel: spotlight falhou", type(e).__name__, e)
    hl = highlight_cards(db, 4)
    if hl:
        body += '<h2 class="sec">Latest highlights<a href="/padel/highlights.html">All highlights</a></h2><div class="pd-hls row">' + "".join(hl_card(db, m, h) for m, h in hl) + "</div>"
    # 2) últimos campeões (o mais interessante para quem chega)
    # 6/11/2026: como no ténis, os campeões recentes (últimas 2 semanas) por ordem de importância (Major, P1, P2, FIP Platinum, Gold, Silver)
    _fin = sorted([t for t in db.tours.values() if t.get("status") == "finished" and t.get("winners")],
                  key=lambda t: t.get("end_date") or "", reverse=True)
    _cut = (dt.date.today() - dt.timedelta(days=14)).isoformat()
    _rec = [t for t in _fin if (t.get("end_date") or "") >= _cut] or _fin[:6]
    champs = sorted(_rec, key=lambda t: (LEVEL_ORDER.get(t.get("level"), 9), "".join(chr(255 - ord(c)) for c in (t.get("end_date") or ""))))[:6]
    if champs:
        body += '<h2 class="sec">Latest champions<a href="/padel/tournaments.html">All tournaments</a></h2><div class="pd-champs">'
        for t in champs:
            rows = ""
            for cat in ("men", "women"):
                ps = (t.get("winners") or {}).get(cat) or []
                if isinstance(ps, list) and ps:
                    rows += f'<div><small>{CAT[cat]}</small>{" / ".join(esc(p.get("short_name") or p.get("name") or "") for p in ps if isinstance(p, dict))}</div>'
            wps = [p for cat in ("men", "women") for p in ((t.get("winners") or {}).get(cat) or []) if isinstance(p, dict)]
            avs = "".join(avatar(p, "pd-av sm") for p in wps if has_photo(p.get("id")))
            body += (f'<a class="pd-champ" href="{tpath(t)}">{f"<div class=pd-avs>{avs}</div>" if avs else ""}<span class="pd-tag">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</span>'
                     f'<b>{esc(t.get("location") or t.get("name"))}</b><span class="pd-note">{esc(date_range(t))}</span>{rows}</a>')
        body += "</div>"
    # 3) a seguir: 3 linhas
    nxt = sorted([t for t in db.tours.values() if t.get("status") == "pending" and (t.get("start_date") or "") >= today],
                 key=lambda t: (t.get("start_date") or "", LEVEL_ORDER.get(t.get("level"), 9)))[:4]
    if nxt:
        body += '<h2 class="sec">Coming up<a href="/padel/next-week.html">Next week</a></h2><div class="pd-list">' + "".join(
            f'<a href="{tpath(t)}"><span class="pd-tag g">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</span><b>{esc(t.get("location") or t.get("name"))}</b>'
            f'<span class="pd-note">{esc(date_range(t))}</span></a>' for t in nxt) + "</div>"
    # 4) rankings: top 5, homens/mulheres em separadores
    tabs, panes = "", ""
    for i, cat in enumerate(("men", "women")):
        rows = ((db.ranks.get(cat) or {}).get("rows") or [])[:5]
        if not rows:
            continue
        tabs += f'<button class="{"on" if i == 0 else ""}" data-c="{cat}">{CAT[cat]}</button>'
        panes += (f'<div class="pd-rk5" data-c="{cat}"{"" if i == 0 else " hidden"}>' + "".join(
            f'<a href="{ppath({"id": r.get("id"), "name": r.get("name")})}"><span class="n">{r.get("ranking")}</span>{avatar(r)}{flag(r.get("nationality"), 11)}'
            f'<span class="nm">{esc(r.get("name"))}</span><span class="pd-note">{(r.get("points") or 0):,}</span></a>'.replace(",", " ") for r in rows)
                  + f'<a class="pd-more" href="/padel/rankings-{cat}.html">Full ranking →</a></div>')
    if panes:
        body += (f'<h2 class="sec">Rankings</h2><div class="pd-seg">{tabs}</div>{panes}'
                 '<script>document.querySelector(".pd-seg").onclick=function(e){var b=e.target.closest("button");if(!b)return;'
                 '[].forEach.call(document.querySelectorAll(".pd-seg button"),function(x){x.className=x===b?"on":""});'
                 '[].forEach.call(document.querySelectorAll(".pd-rk5"),function(p){p.hidden=p.dataset.c!==b.dataset.c})}</script>')
    # 5) atalhos
    links = [("results", "Results", "Every score, newest first"), ("order-of-play", "Order of play", "Today by court"),
             ("stats", "Stats", "Titles, streaks, upsets"), ("players", "Players", "Search 1,900+ players")]
    body += '<div class="pd-quick">' + "".join(f'<a href="/padel/{k}.html"><b>{v}</b><span>{d}</span></a>' for k, v, d in links) + "</div>"
    return shell("Beyond Padel · Premier Padel and FIP Tour results, draws and rankings", body, "/padel/index.html", tab="index")





ROUNDS = {1: "Final", 2: "Semi-finals", 4: "Quarter-finals", 8: "Round of 16", 16: "Round of 32", 32: "Round of 64", 64: "Round of 128"}


ROUND_SHORT = {1: "Final", 2: "Semis", 4: "Quarters", 8: "R16", 16: "R32", 32: "R64", 64: "R128"}


def bracket(ms, db):
    """Quadro: no telemóvel uma ronda de cada vez (botões por ronda); no computador as rondas lado a lado.
    Abre na ronda mais recente já jogada (ou na primeira, se ainda não começou)."""
    rounds = sorted({m.get("round") for m in ms if isinstance(m.get("round"), int)}, reverse=True)
    if not rounds:
        return ""
    played = [r for r in rounds if any(sets_of(m) for m in ms if m.get("round") == r)]
    cur = played[-1] if played else rounds[0]
    uid = f"bk{abs(hash(tuple(sorted(str(m.get('id')) for m in ms)))) % 10**8}"
    chips = "".join(f'<button class="{"on" if r == cur else ""}" data-r="{r}">{esc(ROUND_SHORT.get(r, f"R{r * 2}"))}</button>' for r in rounds)
    cols = ""
    for r in rounds:
        cells = ""
        for m in sorted([m for m in ms if m.get("round") == r], key=lambda m: m.get("index") or 0):
            w = m.get("winner") if m.get("winner") in ("team_1", "team_2") else None
            rows = ""
            for team in ("team_1", "team_2"):
                ps = team_players(m, team)
                nm = " / ".join(f'<a href="{ppath(p)}">{esc(disp(p))}</a>' for p in ps) or '<span class="pd-note">TBD</span>'
                seed = (m.get("seeds") or {}).get(team)
                sc = "".join(f'<b class="{"on" if games(a if team == "team_1" else b) > games(b if team == "team_1" else a) else ""}">'
                             f'{esc(re.sub(r"[(].*[)]", "", a if team == "team_1" else b))}</b>' for a, b in sets_of(m))
                rows += (f'<div class="pl {("w" if w == team else "l") if w else ""}"><span class="nm">{nm}{f"<span class=pd-seed>{esc(str(seed))}</span>" if seed else ""}</span>'
                         f'<span class="s">{sc}</span></div>')
            if not sets_of(m) and m.get("status") not in ("finished", "bye") and (m.get("schedule_label") or when_local(m)):
                rows += f'<div class="when">{esc(m.get("schedule_label") or when_local(m))}</div>'
            vbadge = ""
            if team_players(m, "team_1") and team_players(m, "team_2"):
                hv = highlight_for(db, m)
                vbadge = (f'<a class="pd-bmv{" hl" if hv and hv["kind"] == "match" else ""}" href="{mpath(m)}">'
                          f'{"▶ Highlights" if hv and hv["kind"] == "match" else ("▶ Video" if (hv or video_for(db, m)) else "Match")} ›</a>')
            cells += f'<div class="pd-bm">{rows}{vbadge}</div>'
        cols += (f'<div class="rd{" on" if r == cur else ""}" data-r="{r}"><h4>{esc(ROUNDS.get(r, f"Round of {r * 2}"))}</h4>'
                 f'<div class="col">{cells}</div></div>')
    return (f'<div class="pd-bkw" id="{uid}"><div class="pd-seg pd-rchips">{chips}</div><div class="pd-bk">{cols}</div></div>'
            f'<script>(function(){{var w=document.getElementById("{uid}"),cb=w.querySelector(".pd-rchips"),on=cb.querySelector("button.on");if(on)cb.scrollLeft=on.offsetLeft-cb.clientWidth/2+on.offsetWidth/2;w.querySelector(".pd-rchips").onclick=function(e){{var b=e.target.closest("button");if(!b)return;'
            'w.querySelectorAll(".pd-rchips button").forEach(function(x){x.className=x===b?"on":""});'
            'w.querySelectorAll(".rd").forEach(function(c){c.classList.toggle("on",c.dataset.r===b.dataset.r)});'
            'if(window.innerWidth>=900){var col=w.querySelector(\'.rd[data-r="\'+b.dataset.r+\'"]\'),bk=w.querySelector(".pd-bk");if(col&&bk)bk.scrollTo({left:col.offsetLeft-bk.offsetLeft,behavior:"smooth"})}}})();</script>')


def order_of_play(ms, db, show_tour=False):
    days = {}
    for m in ms:
        if not m.get("played_at"):
            continue
        days.setdefault(m["played_at"], {}).setdefault(m.get("court") or "Court TBC", []).append(m)
    out = ""
    for d in sorted(days):
        try:
            label = dt.date.fromisoformat(d).strftime("%A %d %B")
        except ValueError:
            label = d
        out += f'<h3 class="dh" style="font-size:1.05rem">{esc(label)}</h3><div class="pd-card">'
        for court, cm in sorted(days[d].items()):
            out += f'<div class="pd-court">{esc(court)}</div>'
            for m in sorted(cm, key=lambda m: (m.get("court_order") or 99, m.get("scheduled_at") or "")):
                out += match_html(m, db, show_tour=show_tour)
        out += "</div>"
    return out








FILTER_JS = """<script>(function(){var bar=document.querySelectorAll('.pd-flt');if(!bar.length)return;var st={};
function apply(){document.querySelectorAll('[data-f]').forEach(function(el){var ok=true;el.dataset.f.split(' ').forEach(function(kv){var p=kv.split(':');if(st[p[0]]&&st[p[0]]!==p[1])ok=false});el.hidden=!ok});
document.querySelectorAll('.pd-grp').forEach(function(g){var own=g.dataset.f?g.hidden:false;g.hidden=own||!g.querySelector('[data-f]:not([hidden])')})}
bar.forEach(function(b){b.addEventListener('click',function(e){var x=e.target.closest('button');if(!x)return;var k=x.dataset.k,v=x.dataset.v;st[k]=v;
b.querySelectorAll('button').forEach(function(y){y.className=y===x?'on':''});apply()})})})();</script>"""


def filters(groups):
    """groups: [(chave, [(valor, rótulo)])]. Botões que escondem os elementos com data-f que não batem certo."""
    out = ""
    for k, opts in groups:
        out += '<div class="pd-seg pd-flt">' + "".join(
            f'<button class="{"on" if i == 0 else ""}" data-k="{k}" data-v="{v}">{esc(l)}</button>' for i, (v, l) in enumerate(opts)) + "</div> "
    return f'<div class="pd-flts">{out}</div>'


def tier(t):
    return "premier" if (t.get("level") or "") in ("major", "p1", "p2", "finals") else "fip"


def page_results(db):
    days = {}
    for m in db.matches:
        if m.get("status") in ("finished", "retired", "walkover") and sets_of(m) and m.get("played_at"):
            days.setdefault(m["played_at"], []).append(m)
    body = ('<section class="page-h"><h1>Results</h1><p>Premier Padel and the FIP Tour, newest first. Finals and semi-finals first; '
            'open a tournament to see every match.</p><p class="pd-sub"><a href="/padel/order-of-play.html">Order of play today ›</a> &nbsp;·&nbsp; <a href="/padel/tournaments.html">All tournaments ›</a></p></section>'
            + filters([("c", [("", "All"), ("men", "Men"), ("women", "Women")]), ("t", [("", "All events"), ("premier", "Premier Padel"), ("fip", "FIP Tour")])]))
    for i, d in enumerate(sorted(days, reverse=True)[:10]):
        try:
            label = dt.date.fromisoformat(d).strftime("%A %d %B")
        except ValueError:
            label = d
        by_t = {}
        for m in days[d]:
            by_t.setdefault(str(m.get("tid")), []).append(m)
        tids = sorted(by_t, key=lambda k: (LEVEL_ORDER.get(db.tour(k).get("level"), 9), k))
        sec = ""
        for tid in tids:
            t = db.tour(tid)
            ms = sorted(by_t[tid], key=lambda m: (m.get("round") or 99, m.get("category") != "men", m.get("index") or 0))
            top = [m for m in ms if (m.get("round") or 99) <= 2 and (m.get("draw") or "main") == "main"] or ms[:2]
            rest = [m for m in ms if m not in top]
            row = lambda m: f'<div data-f="c:{m.get("category")}">{match_html(m, db)}</div>'
            sec += (f'<div class="pd-card pd-grp" data-f="t:{tier(t)}"><div class="pd-gh"><span class="pd-tag">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</span>'
                    f'<a href="{tpath(t)}"><b>{esc(t.get("location") or t.get("name") or "")}</b></a><span class="pd-note">{len(ms)} matches</span></div>'
                    + "".join(row(m) for m in top)
                    + (f'<details class="pd-more2"><summary>All {len(ms)} matches</summary>' + "".join(row(m) for m in rest) + "</details>" if rest else "")
                    + "</div>")
        hid = " hidden" if i >= 3 else ""
        body += f'<section class="pd-day"{hid}><h2 class="dh">{esc(label)}</h2>{sec}</section>'
    if len(days) > 3:
        body += ('<button class="pd-btn" onclick="document.querySelectorAll(\'.pd-day[hidden]\').forEach(function(x){x.hidden=false});this.remove()">'
                 'Show older results</button>')
    return shell("Padel results · Beyond Padel", body + FILTER_JS, "/padel/results.html", tab="results")


def _tabs(items, default):
    """Separadores simples: [(id, rótulo, html)]."""
    btn = "".join(f'<button class="{"on" if k == default else ""}" data-tab="{k}">{esc(l)}</button>' for k, l, h in items if h)
    panes = "".join(f'<div class="pd-pane" data-pane="{k}"{"" if k == default else " hidden"}>{h}</div>' for k, l, h in items if h)
    return (f'<div class="pd-tabs2">{btn}</div>{panes}'
            '<script>(function(){var b=document.querySelector(".pd-tabs2");if(!b)return;b.onclick=function(e){var x=e.target.closest("button");if(!x)return;'
            'b.querySelectorAll("button").forEach(function(y){y.className=y===x?"on":""});'
            'document.querySelectorAll(".pd-pane").forEach(function(p){p.hidden=p.dataset.pane!==x.dataset.tab});'
            'document.querySelectorAll(".pd-pane:not([hidden]) .pd-rchips").forEach(function(c){var o=c.querySelector("button.on");if(o)c.scrollLeft=o.offsetLeft-c.offsetLeft-c.clientWidth/2+o.offsetWidth/2})}})();</script>')


def champions_head(t, db):
    """Campeões do torneio. Desde 13/11/2026 em cartões grandes com foto (igual ao ténis); se falhar, o cartão antigo."""
    try:
        import home_ui
        import rank_ui
        cards = []
        for cat in ("men", "women"):
            fin = next((m for m in db.by_t.get(str(t["id"]), []) if m.get("round") == 1 and m.get("category") == cat
                        and (m.get("draw") or "main") == "main" and m.get("winner") in ("team_1", "team_2")), None)
            if not fin:
                continue
            w = fin["winner"]
            WP, LP = team_players(fin, w), team_players(fin, "team_2" if w == "team_1" else "team_1")
            ph = next((f"/padel/img/{p.get('id')}.jpg" for p in WP if has_photo(p.get("id"))), "")
            sc = " ".join(f"{games(a if w == 'team_1' else b)}-{games(b if w == 'team_1' else a)}" for a, b in sets_of(fin))
            c = photo_credit(next((p.get("id") for p in WP if has_photo(p.get("id"))), "")) or {}
            cards.append(home_ui.lead(mpath(fin), ph, "".join((disp(p).split()[-1] or "?")[0] for p in WP).upper(),
                                      [LEVEL_SHORT.get(t.get("level"), ""), f"{CAT[cat]} champions"], " / ".join(disp(p) for p in WP),
                                      f"Beat {' / '.join(disp(p) for p in LP)} {sc} in the final", c.get("credit") or ""))
        if cards:
            return rank_ui.champions(cards)
    except Exception as e:
        print("Padel: campeões com foto falharam", t.get("id"), type(e).__name__, e)
    return champions_head_v1(t, db)


def champions_head_v1(t, db):
    """Um só cartão 'Champions' com uma linha por categoria; fotos só de quem as tem."""
    w = t.get("winners") or {}
    rows = ""
    for cat in ("men", "women"):
        ps = [p for p in (w.get(cat) or []) if isinstance(p, dict)] if isinstance(w.get(cat), list) else []
        if not ps:
            continue
        avs = "".join(avatar(p, "pd-av") for p in ps if has_photo(p.get("id")))
        names = " / ".join(f'{flag(p.get("nationality"), 11)}<a href="{ppath(p)}">{esc(disp(p))}</a>' for p in ps)
        rows += (f'<div class="pd-chr"><small>{CAT[cat]}</small><span class="nm">{names}</span>'
                 f'{f"<span class=pd-avs>{avs}</span>" if avs else ""}<a class="pd-pairl" href="{pair_path(ps)}" aria-label="Pair">›</a></div>')
    return f'<div class="pd-chs"><div class="pd-chs-h">🏆 Champions</div>{rows}</div>' if rows else ""


def preview_html(db, t):
    """Antes do quadro sair: contagem decrescente, campeões em título (edição anterior) e pares cabeças de série (lista de inscritos)."""
    out = ""
    try:
        d0 = dt.date.fromisoformat(t.get("start_date"))
        n = (d0 - dt.date.today()).days
        when = "Starts today" if n == 0 else "Starts tomorrow" if n == 1 else f"Starts in {n} days" if n > 1 else ""
    except (TypeError, ValueError):
        when = ""
    if when:
        out += f'<p class="pd-count"><span>{esc(when)}</span> · the draw usually comes out a day or two before</p>'
    eds = sorted([e for e in (db.editions.get(str(t["id"])) or []) if str(e.get("id")) != str(t["id"]) and isinstance(e.get("winners"), dict)],
                 key=lambda e: e.get("start_date") or "", reverse=True)
    if eds:
        last = eds[0]
        for cat in ("men", "women"):
            ps = [p for p in (last["winners"].get(cat) or []) if isinstance(p, dict)]
            if ps:
                out += site_ui.defending(" / ".join(f'<a href="{ppath(p)}">{esc(disp(p))}</a>' for p in ps),
                                         (last.get("start_date") or "")[:4], True, label=f"Defending champions · {CAT[cat]}")
    rows = [r for r in ((db.entries.get(str(t["id"])) or {}).get("rows") or []) if r.get("draw") == "main" and r.get("pair")]
    pairs = {}
    for r in rows:
        cat = (db.rank_of.get(str(r["id"])) or {}).get("category") or (db.players.get(str(r["id"])) or {}).get("category") or "men"
        pairs.setdefault((cat, r["pair"]), []).append(r)
    for cat in ("men", "women"):
        ps = sorted([v for (c, _), v in pairs.items() if c == cat and len(v) == 2], key=lambda v: (min(x.get("position") or 999 for x in v)))
        if not ps:
            continue
        body = ""
        for v in ps[:8]:
            seed = min(x.get("position") or 0 for x in v) or ""
            av = '<span class="ui-stk">' + "".join(avatar(x, "av") for x in v) + "</span>"
            names = '<span class="nm">' + " / ".join(f'<a href="{ppath(x)}">{esc(disp(dict(x, short_name=db.short.get(str(x.get("id"))) or x.get("short_name"))))}</a>' for x in v) + "</span>"
            sub = " · ".join(f'{flag(x.get("nationality"), 11)}#{x.get("ranking")}' for x in v if x.get("ranking"))
            pts = sum(int(x.get("points") or 0) for x in v)
            body += site_ui.rank_row(seed, av, names, sub, f"{pts:,}" if pts else "", False, "pts")
        out += (site_ui.sec(f"Top seeds · {CAT[cat]}") + f'<div class="ui-rk">{body}</div>'
                + f'<p class="pd-note">{len(ps)} pairs in the main draw</p>')
    if not out:
        return ""
    return out + '<p class="pd-note">Entry list and past champions: Padel API. Seeds as listed before the draw.</p>'


def page_tournament(db, t):
    ms = db.by_t.get(str(t["id"]), [])
    main = [m for m in ms if (m.get("draw") or "main") == "main"]
    v = t.get("venue") or {}
    head = (f'<section class="page-h"><p><a href="/padel/tournaments.html">← Tournaments</a></p><h1>{esc(t.get("name"))}</h1>'
            f'{tour_meta(t)}</section>' + champions_head(t, db))
    cats = [c for c in ("men", "women") if any(m.get("category") == c for m in main)]
    seg = filters([("c", [(c, CAT[c]) for c in cats])]) if len(cats) > 1 else ""
    first_cat = cats[0] if cats else "men"
    draw = ""
    res = ""
    for cat in cats:
        cm = [m for m in main if m.get("category") == cat]
        hid = "" if cat == first_cat else " hidden"
        draw += f'<div data-f="c:{cat}"{hid}>{bracket(cm, db)}</div>'
        done = sorted([m for m in cm if sets_of(m)], key=lambda m: (m.get("round") or 99, m.get("index") or 0))
        if done:
            res += f'<div class="pd-card" data-f="c:{cat}"{hid}>' + "".join(match_html(m, db) for m in done) + "</div>"
    qual = [m for m in ms if m.get("draw") == "qualy" and sets_of(m)]
    if qual:
        res += '<details class="pd-more2"><summary>Qualifying · ' + str(len(qual)) + ' matches</summary><div class="pd-card">' + "".join(match_html(m, db) for m in qual) + "</div></details>"
    today = time.strftime("%Y-%m-%d", time.gmtime())
    upcoming = [m for m in ms if m.get("status") not in ("finished", "retired", "walkover", "bye") and (m.get("played_at") or "") >= today]
    oop = ('<p class="pd-note" id="pd-upd"></p>' + order_of_play(upcoming, db)) if upcoming else ""
    info = ""
    if v.get("name"):
        info += f'<div class="pd-card"><b>{esc(v.get("name"))}</b><p class="pd-note">{esc(v.get("address") or "")}</p></div>'
    eds = [e for e in (db.editions.get(str(t["id"])) or []) if str(e.get("id")) != str(t["id"]) and e.get("winners")]
    if eds:
        info += '<h3 class="pd-court">Past editions</h3>' + "".join(
            f'<div class="pd-card"><b>{esc(e.get("name"))}</b><div class="pd-note">{esc(date_range(e))}</div>{winners_html(e, db)}</div>' for e in eds[:8])
    nw = (db.news.get(str(t["id"])) or {}).get("rows") or []
    if nw:
        info += '<h3 class="pd-court">News</h3><div class="pd-card pd-news">' + "".join(
            f'<a href="{esc(n.get("url") or "#")}" rel="noopener nofollow" target="_blank">{esc(n.get("title") or "")}'
            f'<small>{esc(n.get("source") or n.get("publisher") or "")} {esc((n.get("published_at") or n.get("date") or "")[:10])}</small></a>'
            for n in nw[:10]) + "</div>"
    vids = sorted([v for v in ((db.videos.get(str(t["id"])) or {}).get("rows") or []) if (v.get("url") or "").startswith("https://")
                   and (v.get("started_at") or "")[:10] <= (t.get("end_date") or "9999")],
                  key=lambda v: v.get("started_at") or "", reverse=True)
    vhtml = ""
    place = _place_words(t)
    hls = sorted([(k, h) for k, h in db.highlights.items() if h.get("kind") in ("match", "day") and _in_window(t, h.get("published"))
                  and _place_ok(h.get("title"), place)], key=lambda kh: kh[1].get("published") or "", reverse=True)
    if hls:
        vhtml += '<h3 class="pd-court">Highlights</h3><div class="pd-vgrid">' + "".join(
            f'<a href="https://www.youtube.com/watch?v={k}" target="_blank" rel="noopener"><img src="https://i.ytimg.com/vi/{k}/mqdefault.jpg" alt="" loading="lazy" width="320" height="180">'
            f'<b>{esc((h.get("title") or "").split("|")[0].strip())}</b><span class="pd-note">{esc(h.get("channel") or "")} · {esc((h.get("published") or "")[:10])}</span></a>'
            for k, h in hls[:24]) + "</div>"
    if vids:
        vhtml += ('<h3 class="pd-court">Full streams</h3>' if hls else "") + '<div class="pd-vgrid">' + "".join(
            f'<a href="{esc(v["url"])}" target="_blank" rel="noopener"><img src="{esc(("https://i.ytimg.com/vi/" + _yt_id(v["url"]) + "/mqdefault.jpg") if _yt_id(v["url"]) else (v.get("photo_url") or ""))}" alt="" loading="lazy" width="320" height="180">'
            f'<b>{esc(re.sub(r"^[^:]*:\s*", "", v.get("name") or "") or v.get("name") or "")}</b><span class="pd-note">{esc((v.get("started_at") or "")[:10])}</span></a>'
            for v in vids[:30]) + '</div><p class="pd-note">Official broadcasts (YouTube and Red Bull TV). Each match page links to the stream of its court and day.</p>'
    # transmissões de hoje (YouTube oficial): em direto quando o torneio está a decorrer
    today_str = time.strftime("%Y-%m-%d", time.gmtime())
    live_now = [v for v in ((db.videos.get(str(t["id"])) or {}).get("rows") or []) if (v.get("started_at") or "")[:10] == today_str and _yt_id(v.get("url"))]
    live_now.sort(key=lambda v: ("🇬🇧" not in (v.get("name") or "") and not re.search(r"cent", v.get("name") or "", re.I), v.get("name") or ""))
    watch = ""
    if t.get("status") == "live" and live_now and not [v for v in live_now if yt_player.embeddable(_yt_id(v.get("url"))) is not False]:
        watch_card = yt_player.link_card(_yt_id(live_now[0]["url"]), "Watch live on YouTube")
    else:
        watch_card = ""
    live_now = [v for v in live_now if yt_player.embeddable(_yt_id(v.get("url"))) is not False]
    if t.get("status") == "live" and live_now:
        first = live_now[0]
        watch = (f'<h2 class="dh pd-hlh"><span class="dot" style="display:inline-block;margin-right:8px"></span>Watch live</h2>'
                 f'<div class="pd-video"><iframe src="https://www.youtube-nocookie.com/embed/{_yt_id(first["url"])}?rel=0" title="{esc(first.get("name") or "")}" loading="lazy" '
                 f'allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen" allowfullscreen></iframe></div>'
                 + ('<p class="pd-sub">Other courts: ' + " · ".join(f'<a href="{esc(v["url"])}" target="_blank" rel="noopener">{esc(re.sub(r"^.*?:\s*", "", v.get("name") or ""))} ↗</a>' for v in live_now[1:6]) + "</p>" if len(live_now) > 1 else "")
                 + '<p class="pd-note">Official live stream on YouTube.</p>')
    if watch_card and not watch:
        watch = '<h2 class="dh pd-hlh"><span class="dot" style="display:inline-block;margin-right:8px"></span>Watch live</h2>' + watch_card
    default = "oop" if oop else ("results" if res else "draw")
    # os jogos com resumo em vídeo, à vista logo no topo (miniaturas que levam à página do jogo)
    hlm = []
    for x in db.by_t.get(str(t["id"]), []):
        if team_players(x, "team_1") and (x.get("draw") or "main") == "main":
            h = highlight_for(db, x)
            if h and h["kind"] == "match":
                hlm.append((x, h))
    hlm.sort(key=lambda mh: (mh[0].get("round") or 99, mh[0].get("category") != "men"))
    hlrow = (f'<h2 class="sec">▶ Match highlights <small class="pd-note" style="font-weight:600">{len(hlm)} match{"es" if len(hlm) != 1 else ""} with video</small></h2>'
             '<div class="pd-hls row">' + "".join(hl_card(db, x, h) for x, h in hlm) + "</div>") if hlm else ""
    vlab = f"▶ Videos ({len(hls) + len(vids)})" if (hls or vids) else "Videos"
    pre = preview_html(db, t) if not any(sets_of(m) for m in main) else ""
    body = head + pre + watch + hlrow + seg + _tabs([("oop", "Order of play", oop), ("results", "Results", res), ("draw", "Draw", draw), ("videos", vlab, vhtml), ("info", "Info", info)], default) + FILTER_JS
    ld = [{"@context": "https://schema.org", "@type": "SportsEvent", "name": t.get("name"), "sport": "Padel",
           "startDate": t.get("start_date"), "endDate": t.get("end_date"), "url": SITE_BASE + _clean(tpath(t)),
           "location": {"@type": "Place", "name": (v.get("name") or t.get("location") or ""), "address": ", ".join(x for x in [t.get("location"), t.get("country")] if x)}},
          _crumbs([("Beyond Padel", "/padel/index.html"), ("Tournaments", "/padel/tournaments.html"), (t.get("name") or "", tpath(t))])]
    return shell(f"{t.get('name')}: results, draw and order of play · Beyond Padel", body, tpath(t),
                 desc=f"{t.get('name')} ({LEVEL.get(t.get('level'), '')}), {t.get('location')}: results, draw and order of play.", tab="tournaments", ld=ld)


def player_matches(db, pid):
    out = list(db.by_p.get(str(pid), []))
    out.sort(key=lambda x: (x[0].get("played_at") or "", -(x[0].get("round") or 99)), reverse=True)
    return out


def rank_chart(hist):
    """Linha do ranking ao longo das semanas (SVG). hist = [(data, ranking)], mais antigo primeiro."""
    pts = [(d, r) for d, r in hist if r]
    if len(pts) < 2:
        return ""
    W_, H_, pad = 320, 90, 10
    lo, hi = min(r for _, r in pts), max(r for _, r in pts)
    span = max(1, hi - lo)
    xy = [(pad + i * (W_ - 2 * pad) / (len(pts) - 1), pad + (r - lo) * (H_ - 2 * pad) / span) for i, (_, r) in enumerate(pts)]
    path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(xy))
    best = min(r for _, r in pts)
    return (f'<div class="pd-card pd-chart"><div class="pd-meta"><b>Ranking, last {len(pts)} weeks</b> · best #{best}</div>'
            f'<svg viewBox="0 0 {W_} {H_}" preserveAspectRatio="none" role="img" aria-label="Ranking evolution">'
            f'<path d="{path}" fill="none" stroke="#d9f23d" stroke-width="3" stroke-linejoin="round"/>'
            f'<circle cx="{xy[-1][0]:.1f}" cy="{xy[-1][1]:.1f}" r="5" fill="#d9f23d"/></svg>'
            f'<div class="pd-meta"><span>{esc(pts[0][0])} · #{pts[0][1]}</span><span style="margin-left:auto">{esc(pts[-1][0])} · #{pts[-1][1]}</span></div></div>')


def tournament_runs(db, pid, ms):
    """Melhor ronda em cada torneio jogado."""
    by = {}
    for m, tm in ms:
        if (m.get("draw") or "main") != "main":
            continue
        e = by.setdefault(str(m.get("tid")), {"best": 99, "won_final": False, "date": m.get("played_at") or "", "pair": team_players(m, tm)})
        r = m.get("round") or 99
        e["best"] = min(e["best"], r)
        if r == 1 and m.get("winner") == tm:
            e["won_final"] = True
    rows = ""
    for tid, e in sorted(by.items(), key=lambda kv: kv[1]["date"], reverse=True)[:12]:
        t = db.tour(tid)
        res = "Champion" if e["won_final"] else ("Final" if e["best"] == 1 else ROUNDS.get(e["best"], f"Round of {e['best'] * 2}"))
        partner = " / ".join(esc(disp(p)) for p in e["pair"] if str(p.get("id")) != str(pid))
        rows += (f'<tr><td class="pn"><a href="{tpath(t)}">{esc(t.get("location") or t.get("name") or "")}</a> <small class="pd-note">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</small></td>'
                 f'<td>{"<b class=on>🏆 Champion</b>" if e["won_final"] else esc(res)}</td><td class="pd-note">{partner}</td></tr>')
    return f'<table class="pt"><thead><tr><th>Tournament</th><th>Result</th><th>Partner</th></tr></thead><tbody>{rows}</tbody></table>' if rows else ""


def _hero_table(r, p, rk, d, w, done, titles, finals, pct, partner=""):
    """Tabela do topo da página de jogador (igual à do ténis): agora (ranking, subida, pontos, race) e o nosso registo."""
    now = []
    if rk:
        now.append((f"No. {rk}", "rank", ""))
    if d:
        now.append((f'{"▲" if d > 0 else "▼"}{abs(d)}', "this week", "up" if d > 0 else "dn"))
    pts = r.get("points") or p.get("points")
    if pts:
        now.append((f"{pts:,}" if isinstance(pts, int) else esc(str(pts)), "points", ""))
    race = p.get("race") if isinstance(p.get("race"), dict) else {}
    if race.get("ranking"):
        now.append((f'No. {race["ranking"]}', "race", ""))
    elo = p.get("elo")
    if isinstance(elo, dict) and elo.get("ranking"):
        now.append((f'No. {elo["ranking"]}', "Elo rank", ""))
    elif isinstance(elo, (int, float)) and elo:
        now.append((f"{round(elo):,}", "Elo rating", ""))
    if partner:
        now.append((esc(partner.split()[-1]), "partner", ""))
    rec = []
    if done:
        rec += [(f"{w}-{len(done) - w}", "won-lost", ""), (pct, "win rate", ""), (str(titles), "titles", ""), (str(finals), "finals", "")]
    rows = ([("Now", now)] if now else []) + ([("Tracked", rec)] if rec else [])
    return rows or None


def _player_shell(db, pid, p, r, ms, body):
    """Título, descrição, dados estruturados e moldura da ficha (comum às versões 1 e 2)."""
    _rk = r.get("ranking") if isinstance(r, dict) else None                 # mesmo formato do ténis: "<nome> ranking: No. X"
    _person = {"@context": "https://schema.org", "@type": "Person", "name": p.get("name"), "url": SITE_BASE + _clean(ppath(p)),
               "jobTitle": "Professional padel player"}
    if p.get("nationality"):
        _person["nationality"] = {"@type": "Country", "name": country_name(p.get("nationality"))}
    if (p.get("birthdate") or "")[:10]:
        _person["birthDate"] = p["birthdate"][:10]
    if p.get("height"):
        _person["height"] = {"@type": "QuantitativeValue", "value": p["height"], "unitCode": "CMT"}
    if p.get("birthplace"):
        _person["birthPlace"] = {"@type": "Place", "name": p["birthplace"]}
    if has_photo(pid):
        _person["image"] = f"{SITE_BASE}/padel/img/{pid}.jpg"
    _ld = [_person, _crumbs([("Beyond Padel", "/padel/index.html"), ("Rankings", "/padel/rankings.html"), (p.get("name") or "", ppath(p))])]
    _title = (f"{p.get('name')} padel ranking: No. {_rk}" if _rk else f"{p.get('name')} padel ranking") + " · results and partners | Beyond Padel"
    _desc = (f"{p.get('name')} is ranked No. {_rk} in padel" if _rk else f"{p.get('name')}") + f" ({country_name(p.get('nationality'))}): ranking, points, partners and match results."
    if _rk and _title_test(ppath(p)):                          # 12/11/2026: teste de título (páginas "Ninguém clica" do padel)
        _d = r.get("ranking_diff") or 0 if isinstance(r, dict) else 0
        _mv = f" (▲{_d} this week)" if _d > 0 else f" (▼{-_d} this week)" if _d < 0 else ""
        _day = time.strftime("%-d %b %Y")
        _title = f"{p.get('name')} padel ranking: No. {_rk}{_mv} · updated {_day}"
        _desc = f"{p.get('name')} is No. {_rk} in the padel ranking{_mv}, updated {_day}. " + _desc
    return shell(_title, body, ppath(p), desc=_desc, tab="players", noindex=_thin(p, ms, _rk), ld=_ld)


_SEEN_GSC = None


def _thin(p, ms, rk):
    """Ficha muito pobre fica fora do Google (noindex,follow), com a mesma regra do sitemap: menos de 3 jogos e fora do top 200.
    Exceção: fichas que já aparecem nas pesquisas do Google (gsc.json). (7/11/2026)"""
    global _SEEN_GSC
    if _SEEN_GSC is None:
        try:
            _SEEN_GSC = {re.sub(r"\.html$", "", (x.get("page") or "").split("beyond100tennis.com")[-1])
                         for x in json.load(open("gsc.json", encoding="utf-8")).get("pages") or []}
        except (OSError, ValueError):
            _SEEN_GSC = set()
    if not ms:
        return True
    if len(ms) >= 3 or (isinstance(rk, int) and rk <= 200):
        return False
    return _clean(ppath(p)) not in _SEEN_GSC


def spotlight_players(db, n=8, lo=7.5, hi=25):
    """Fichas de padel que o Google já mostra perto da 1.ª página (gsc.json -> by_sport.padel, posição lo-hi), por aparições."""
    try:
        qs = ((json.load(open("gsc.json", encoding="utf-8")).get("by_sport") or {}).get("padel") or {}).get("queries") or []
    except (OSError, ValueError):
        qs = []
    plain = lambda t: " ".join(unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower().split())
    names = {}
    for pid, p in (db.players or {}).items():
        if isinstance(p, dict) and p.get("name"):
            names[plain(p["name"])] = p
    agg = {}
    for q in qs:
        pos, imp = q.get("position") or 99, q.get("impressions") or 0
        if not (lo <= pos <= hi):
            continue
        t = [x for x in plain(q.get("q")).split() if x not in ("padel", "ranking", "rankings", "2026", "live", "results")]
        p = names.get(" ".join(t))
        if not p and t:
            hits = [v for k, v in names.items() if set(t) <= set(k.split())] if len(t) >= 2 else [v for k, v in names.items() if k.split()[-1] == t[0]]
            p = hits[0] if len(hits) == 1 else None
        if p:
            x = agg.setdefault(str(p.get("id")), [p, 0])
            x[1] += imp
    return [v[0] for v in sorted(agg.values(), key=lambda v: -v[1])][:n]


def spotlight_block(db):
    rows = spotlight_players(db)
    if len(rows) < 3:
        return ""
    import extras
    cards = ""
    for p in rows:
        pid, nm = str(p.get("id")), p.get("name") or ""
        rk = ((db.rank_of.get(pid) or {}).get("ranking"))
        img = (f'<img src="/padel/img/{pid}.jpg" alt="{esc(nm)}" loading="lazy" width="150" height="188">' if has_photo(pid)
               else f'<span class="ini">{esc("".join(w[0] for w in nm.split()[:2]).upper())}</span>')
        cards += (f'<a href="{ppath(p)}">{img}{f"<span class=rk>No. {rk}</span>" if rk else ""}'
                  f'<span class="ov"><b>{esc(nm)}</b><small>{esc(country_name(p.get("nationality"))) or "Ranking &amp; results"}</small></span></a>')
    return (f'<style>{extras.SPOT_CSS}.ui-spot .ini{{color:rgba(127,179,224,.28)}}</style><h2 class="sec">Players in the spotlight<a href="/padel/players.html">All players</a></h2>'
            f'<div class="ui-spot">{cards}</div>')


_TT = None


def _title_test(path):
    """Teste de título em curso (ou ganho) para esta ficha? gsc.json -> title_tests, chave = caminho sem .html."""
    global _TT
    if _TT is None:
        try:
            _TT = json.load(open("gsc.json", encoding="utf-8")).get("title_tests") or {}
        except (OSError, ValueError):
            _TT = {}
    t = _TT.get(path[:-5] if path.endswith(".html") else path)
    return bool(t and t.get("status") in ("running", "won"))


def page_player(db, pid, p):
    """Ficha do jogador. Desde 13/11/2026 usa o novo desenho comum ao ténis (player_ui); PLAYER_V2=0 volta ao antigo."""
    if os.environ.get("PLAYER_V2", "1") != "0":
        try:
            return page_player_v2(db, pid, p)
        except Exception as ex:
            print("Ficha padel v2 falhou:", pid, type(ex).__name__, ex)
    return page_player_v1(db, pid, p)


def page_player_v1(db, pid, p):
    ms = player_matches(db, pid)
    done = [(m, tm) for m, tm in ms if m.get("winner") in ("team_1", "team_2")]
    w = sum(1 for m, tm in done if m["winner"] == tm)
    r = db.rank_of.get(str(pid)) or {}
    titles = sum(1 for m, tm in done if m.get("round") == 1 and m["winner"] == tm)
    finals = sum(1 for m, tm in ms if m.get("round") == 1)
    partners = {}
    for m, tm in ms:
        for q in team_players(m, tm):
            if str(q.get("id")) != str(pid):
                e = partners.setdefault(str(q.get("id")), {"p": q, "n": 0, "w": 0, "team": team_players(m, tm)})
                e["n"] += 1
                e["w"] += 1 if m.get("winner") == tm else 0
    side = {"drive": "Drive (right side)", "backhand": "Backhand (left side)"}.get(p.get("side") or "", "")
    facts = [x for x in [country_name(p.get("nationality")), f"Age {p['age']}" if p.get("age") else "",
                         f"{p['height']} cm" if p.get("height") else "", side,
                         {"right": "Right-handed", "left": "Left-handed"}.get(str(p.get("hand") or "").lower(), "")] if x]
    form = "".join(f'<i class="{"fw" if m["winner"] == tm else "fl"}">{"W" if m["winner"] == tm else "L"}</i>' for m, tm in done[:6])
    rk = r.get("ranking") or p.get("ranking")
    d = r.get("ranking_diff") or 0
    c = photo_credit(pid) if has_photo(pid) else {}
    pct = f"{round(100 * w / len(done))}%" if done else "–"
    _partner = next((q.get("name") or "" for m, tm in ms[:1] for q in team_players(m, tm) if str(q.get("id")) != str(pid)), "")
    body = site_ui.player_hero("/padel/rankings.html", "Rankings", f"/padel/img/{pid}.jpg" if has_photo(pid) else "", p.get("name") or "",
                               flag(p.get("nationality"), 14) + esc(" · ".join(facts)), rk, "",
                               [m["winner"] == tm for m, tm in done[:8]],
                               [(r.get("points") or p.get("points") or "–", "points"), (f"{w}-{len(done) - w}", "won-lost"), (pct, "win rate"), (f"{titles}/{finals}", "titles/finals")],
                               esc(c.get("credit") or ""), table=_hero_table(r, p, rk, d, w, done, titles, finals, pct, _partner))
    hv = [(m, h) for m, tm in ms for h in [highlight_for(db, m)] if h and h["kind"] == "match"][:8]
    if hv:
        body += '<h2 class="sec">▶ Highlights</h2><div class="pd-hls row">' + "".join(hl_card(db, m, h) for m, h in hv) + "</div>"
    xr = [f'<span class="pd-xr"><b>#{p[k]["ranking"]}</b> {lab}</span>' for k, lab in (("elo", "Elo rating"),)              # a race já está na tabela do topo
          if isinstance(p.get(k), dict) and p[k].get("ranking")]
    if xr:
        body += '<p class="pd-xrs">' + "".join(xr) + "</p>"
    body += rank_chart(db.rank_hist(pid))
    runs = tournament_runs(db, pid, ms)
    if runs:
        body += '<h2 class="dh">Tournaments</h2>' + runs
    ph = [x for x in p.get("pairs_hist") or [] if len(x.get("players") or []) == 2]
    if ph:                                            # parceiros ao longo da carreira (Padel API), com datas e o nosso registo de jogos
        def _mon(d):
            try:
                return dt.date.fromisoformat(d[:10]).strftime("%b %Y")
            except (TypeError, ValueError):
                return ""
        rows_ = ""
        for x in sorted(ph, key=lambda x: (x.get("status") == "current", x.get("last") or ""), reverse=True)[:10]:
            q = next((y for y in x["players"] if str(y.get("id")) != str(pid)), None)
            if not q:
                continue
            e = partners.get(str(q.get("id")))
            span = f'{_mon(x.get("first"))} – {"now" if x.get("status") == "current" else _mon(x.get("last"))}'
            sub = span + (f' · {e["w"]}-{e["n"] - e["w"]} in our data' if e else "")
            rows_ += site_ui.rank_row("", avatar(q, "av"), f'<a href="{pair_path(x["players"])}">{esc(q.get("name"))}</a>', esc(sub),
                                      "Current" if x.get("status") == "current" else "", False, "")
        body += site_ui.sec("Partners") + f'<div class="ui-rk">{rows_}</div>'
    elif partners:
        body += '<h2 class="dh">Partners</h2><table class="pt"><thead><tr><th>Partner</th><th>Matches</th><th>W-L</th></tr></thead><tbody>' + "".join(
            f'<tr><td class="pn"><a href="{pair_path(e["team"])}">{esc(e["p"].get("name"))}</a></td><td>{e["n"]}</td><td>{e["w"]}-{e["n"] - e["w"]}</td></tr>'
            for e in sorted(partners.values(), key=lambda e: -e["n"])[:6]) + "</tbody></table>"
    if ms:
        body += _nl_inline(f"Following {p.get('name') or 'this player'}? Get the padel week in one email")
        body += '<h2 class="dh">Last matches</h2><div class="pd-card">' + "".join(match_html(m, db, show_tour=True) for m, _ in ms[:10]) + "</div>"
        if len(ms) > 10:
            body += (f'<details class="pd-more2"><summary>All {len(ms)} matches</summary><div class="pd-card">'
                     + "".join(match_html(m, db, show_tour=True) for m, _ in ms[10:60]) + "</div></details>")
    # ligações a páginas relacionadas (SEO e navegação, como no ténis): adversários frequentes e jogadores do mesmo país
    opp = {}
    for m, tm in done:
        ot = "team_2" if tm == "team_1" else "team_1"
        for q in team_players(m, ot):
            e_ = opp.setdefault(str(q.get("id")), [q, 0, 0])
            e_[1 if m["winner"] == tm else 2] += 1
    freq = sorted([v for v in opp.values() if v[1] + v[2] >= 2], key=lambda v: -(v[1] + v[2]))[:6]
    if freq:
        body += ('<h2 class="dh">Frequent opponents</h2><div class="sfs">'
                 + "".join(f'<span>{plink(q)} <b>{a}-{b}</b></span>' for q, a, b in freq) + "</div>")
    nat, my_rk = p.get("nationality"), (r.get("ranking") if isinstance(r, dict) else None) or 500
    if nat:
        mates = [((db.rank_of.get(k) or {}).get("ranking") or 9999, q) for k, q in db.pinfo.items()
                 if k != str(pid) and q.get("nationality") == nat and q.get("category") == p.get("category") and (db.rank_of.get(k) or {}).get("ranking")]
        if mates:
            mates.sort(key=lambda x: (abs(x[0] - my_rk), x[0]))
            body += (f'<h2 class="dh">More players from {esc(country_name(nat))}</h2><div class="sfs">'
                     + "".join(f'<span>{plink(q)} <b>#{rk}</b></span>' for rk, q in sorted(mates[:6], key=lambda x: x[0]))
                     + '<span><a href="/padel/countries.html">All countries →</a></span></div>')
    body += '<p class="pd-note">Won-lost, titles and tournaments count the matches in our database (Premier Padel and FIP Platinum, Gold and Silver, last months).</p>'
    return _player_shell(db, pid, p, r, ms, body)


def page_pair(db, key, team):
    ms = list(db.by_pair.get(key, []))
    ms.sort(key=lambda x: (x[0].get("played_at") or "", -(x[0].get("round") or 99)), reverse=True)
    done = [(m, tm) for m, tm in ms if m.get("winner") in ("team_1", "team_2")]
    w = sum(1 for m, tm in done if m["winner"] == tm)
    name = " / ".join(p.get("name") for p in team)
    h2h = {}
    for m, tm in done:
        opp = team_players(m, "team_2" if tm == "team_1" else "team_1")
        if len(opp) != 2:
            continue
        k = pair_key(opp)
        e = h2h.setdefault(k, {"team": opp, "w": 0, "l": 0})
        e["w" if m["winner"] == tm else "l"] += 1
    avs = "".join(avatar(p, "pd-av lg") for p in team)
    body = (f'<section class="page-h"><div class="pd-avs">{avs}</div><h1>{esc(name)}</h1><p>' + " · ".join(
            f'<a href="{ppath(p)}">{esc(p.get("name"))}</a>' + (f" <small>{rank_str(p.get('id'), db)}</small>" if rank_str(p.get('id'), db) else "") for p in team) +
            f'</p></section><div class="numgrid"><div class="nbox"><b>{w}-{len(done) - w}</b><span>together</span></div>'
            f'<div class="nbox"><b>{sum(1 for m, tm in done if m.get("round") == 1 and m["winner"] == tm)}</b><span>titles</span></div>'
            f'<div class="nbox"><b>{len({m.get("tid") for m, _ in ms})}</b><span>tournaments</span></div></div>')
    rows = sorted(h2h.values(), key=lambda e: -(e["w"] + e["l"]))
    if rows:
        body += ('<h2 class="dh">Head-to-head</h2><table class="pt"><thead><tr><th>Against</th><th>W-L</th></tr></thead><tbody>' + "".join(
            f'<tr><td class="pn"><a href="{pair_path(e["team"])}">{" / ".join(esc(disp(p)) for p in e["team"])}</a></td><td>{e["w"]}-{e["l"]}</td></tr>'
            for e in rows[:15]) + "</tbody></table>")
    body += '<h2 class="dh">Matches</h2><div class="pd-card">' + "".join(match_html(m, db, show_tour=True) for m, _ in ms[:30]) + "</div>"
    return shell(f"{name}: padel pair results · Beyond Padel", body, pair_path(team), tab="players", noindex=len(ms) < 2)


def rank_table(rows, db, more_after=None):
    tr = ""
    for i, r in enumerate(rows):
        d = r.get("ranking_diff") or 0
        mv = f'<span class="up">▲{d}</span>' if d > 0 else f'<span class="dn">▼{-d}</span>' if d < 0 else ""
        p = {"id": r.get("id"), "name": r.get("name"), "nationality": r.get("nationality")}
        hid = " hidden" if more_after and i >= more_after else ""
        tr += (f'<tr class="rk" data-n="{esc((r.get("name") or "").lower())}" data-c="{esc(r.get("nationality") or "")}"{hid}><td>{r.get("ranking")}</td><td>{mv}</td>'
               f'<td class="pn">{plink(p)}</td><td>{(r.get("points") or 0):,}</td></tr>').replace(",", " ")
    return f'<table class="pt pd-rk"><thead><tr><th>#</th><th></th><th>Player</th><th>Points</th></tr></thead><tbody>{tr}</tbody></table>'


def _rank_v2(rows, db):
    """Ranking com o mesmo desenho do ténis (13/11/2026): pódio com foto, subidas da semana com foto e linhas com foto, país, pontos e ▲▼."""
    import rank_ui
    pic = lambda r: [f"/padel/img/{r.get('id')}.jpg"] if has_photo(r.get("id")) else []
    ini = lambda r: "".join(w[0] for w in (r.get("name") or "?").split()[:2]).upper()
    pp = lambda r: ppath({"id": r.get("id"), "name": r.get("name")})
    pts = lambda r: f'{(r.get("points") or 0):,}'.replace(",", " ")
    out = f"<style>{rank_ui.CSS}</style>" + rank_ui.podium([(r.get("ranking"), pic(r), ini(r), r.get("name") or "", f'{esc(country_name(r.get("nationality")))} · {pts(r)} pts', pp(r))
                                                          for r in rows[:3]])
    cl = sorted([r for r in rows[:300] if (r.get("ranking_diff") or 0) > 0], key=lambda r: (-(r.get("ranking_diff") or 0), r.get("ranking") or 9999))[:6]
    if cl:
        out += site_ui.sec("Climbers this week") + rank_ui.climbers([(r["ranking_diff"], pic(r), ini(r), r.get("name") or "",
                                                                        f'No. {r["ranking"] + r["ranking_diff"]} → No. {r["ranking"]} · {pts(r)} pts', pp(r)) for r in cl])
    items = ""
    for i, r in enumerate(rows):
        p = {"id": r.get("id"), "name": r.get("name"), "nationality": r.get("nationality")}
        row = site_ui.rank_row(r.get("ranking"), avatar(p, "av"), f'<a href="{pp(r)}">{esc(r.get("name") or "")}</a>',
                               f'{flag(r.get("nationality"), 11)}{esc(country_name(r.get("nationality")))}', pts(r), r.get("ranking_diff") or None)
        row = row.replace('<div class="r', f'<div data-n="{esc((r.get("name") or "").lower())}" data-c="{esc(r.get("nationality") or "")}"{" hidden" if i >= 100 else ""} class="r', 1)
        items += row
    return out + site_ui.sec(f"Top {len(rows)}") + f'<div class="ui-rk rk-v2">{items}</div>'


def page_rankings(db, cat):
    r = db.ranks.get(cat) or {}
    rows = sorted(r.get("rows") or [], key=lambda x: x.get("ranking") or 9999)
    cs = sorted({x.get("nationality") for x in rows if x.get("nationality")}, key=lambda c: country_name(c))
    other = "women" if cat == "men" else "men"
    body = (f'<section class="page-h"><h1>{CAT[cat]}\'s ranking</h1><p>Official ranking{(" of " + esc(r.get("date"))) if r.get("date") else ""} · '
            f'▲▼ places moved this week.</p><p class="pd-sub"><a href="/padel/players.html">All 1 900+ players ›</a> &nbsp; <a href="/padel/countries.html">By country ›</a></p></section>'
            f'<div class="pd-seg"><a class="on" href="/padel/rankings-{cat}.html">{CAT[cat]}</a><a href="/padel/rankings-{other}.html">{CAT[other]}</a></div>'
            '<div class="pd-rkf"><input class="srch" id="rq" placeholder="Search player" autocomplete="off">'
            '<select id="rc"><option value="">All countries</option>' + "".join(f'<option value="{esc(c)}">{esc(country_name(c))}</option>' for c in cs) + '</select></div>'
            + _rank_v2(rows, db)
            + (f'<button class="pd-btn" id="rmore">Show all {len(rows)}</button>' if len(rows) > 100 else "")
            + '<script>(function(){var q=document.getElementById("rq"),c=document.getElementById("rc"),m=document.getElementById("rmore"),all=false,rs=[].slice.call(document.querySelectorAll(".rk-v2 .r"));'
              'function f(){var v=q.value.toLowerCase().trim(),cc=c.value;rs.forEach(function(r,i){var ok=(!v||r.dataset.n.indexOf(v)>=0)&&(!cc||r.dataset.c===cc);r.hidden=!ok||(!v&&!cc&&!all&&i>=100)});if(m)m.hidden=!!(v||cc||all)}'
              'q.oninput=f;c.onchange=f;if(m)m.onclick=function(){all=true;f()}})();</script>')
    return shell(f"Padel {CAT[cat].lower()}'s ranking · Beyond Padel", body, f"/padel/rankings-{cat}.html", tab="rankings")


def page_tournaments(db):
    groups = [("live", "This week"), ("pending", "Coming up"), ("finished", "Finished")]
    body = ('<section class="page-h"><h1>Tournaments</h1><p>Premier Padel and the CUPRA FIP Tour (Platinum, Gold, Silver).</p>'
            '<p class="pd-sub"><a href="/padel/next-week.html">Next week ›</a></p></section>'
            + filters([("t", [("", "All"), ("premier", "Premier Padel"), ("fip", "FIP Tour")])]))
    for st, title in groups:
        ts = [t for t in db.tours.values() if t.get("status") == st]
        ts.sort(key=lambda t: (t.get("start_date") or ""), reverse=(st == "finished"))
        if not ts:
            continue
        body += f'<section class="pd-grp"><h2 class="dh">{title}</h2>'
        month = None
        for i, t in enumerate(ts[:80]):
            old = " pd-old" if st == "finished" and i >= 15 else ""
            mo = (t.get("start_date") or "")[:7]
            if st != "live" and mo != month:
                month = mo
                try:
                    body += f'<h3 class="pd-court{old}">{dt.date.fromisoformat(mo + "-01").strftime("%B %Y")}</h3>'
                except ValueError:
                    pass
            win = ""
            for cat in ("men", "women"):
                ps = (t.get("winners") or {}).get(cat)
                if isinstance(ps, list) and ps:
                    win += f'<div class="pd-win">🏆 <b>{CAT[cat]}</b> <span>{" / ".join(esc(disp(p)) for p in ps if isinstance(p, dict))}</span></div>'
            body += (f'<a class="pd-trow{old}" data-f="t:{tier(t)}" href="{tpath(t)}">'
                     f'<div><span class="pd-tag">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</span><b style="display:block;margin-top:4px">{esc(t.get("name"))}</b><div class="pd-note">{flag(t.get("country"), 11)}{esc(t.get("location") or "")} · {esc(date_range(t))}</div>{win}</div></a>')
        if st == "finished" and len(ts) > 15:
            body += '<button class="pd-btn" onclick="this.parentNode.classList.add(\'show-old\');this.remove()">Show older tournaments</button>'
        body += "</section>"
    return shell("Padel tournaments · Beyond Padel", body + FILTER_JS, "/padel/tournaments.html", tab="tournaments")


def page_oop(db):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    ms = [m for m in db.matches if (m.get("played_at") or "") >= today and m.get("status") not in ("finished", "retired", "walkover", "bye")]
    body = '<section class="page-h"><h1>Order of play</h1><p>Today\'s and upcoming matches by court, in the tournament\'s local time.</p></section>'
    if ms:
        body += order_of_play(ms, db, show_tour=True)
    else:
        nxt = sorted([t for t in db.tours.values() if t.get("status") in ("pending", "live") and (t.get("start_date") or "") >= today],
                     key=lambda t: (t.get("start_date") or "", LEVEL_ORDER.get(t.get("level"), 9)))[:4]
        body += '<div class="pd-card"><b>No matches scheduled right now.</b><p class="pd-note">The order of play is published the day before each round.</p></div>'
        if nxt:
            body += '<h2 class="dh">Next tournaments</h2><div class="pd-list">' + "".join(
                f'<a href="{tpath(t)}"><span class="pd-tag g">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</span><b>{esc(t.get("location") or t.get("name"))}</b>'
                f'<span class="pd-note">starts {esc(dt.date.fromisoformat(t["start_date"]).strftime("%a %d %b"))}</span></a>' for t in nxt if t.get("start_date")) + "</div>"
    return shell("Padel order of play today · Beyond Padel", body, "/padel/order-of-play.html", tab="order-of-play")



# ------------------------------------------------------------------ vídeos e página de cada jogo
def _court_key(s):
    t = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    if re.search(r"cent(re|er|ral)|central|pista central", t):
        return "centre"
    m = re.search(r"court\s*(\d+)|pista\s*(\d+)", t)
    if m:
        return "c" + (m.group(1) or m.group(2))
    if "secondary" in t:
        return "c1"
    return ""


def _yt_id(url):
    m = re.search(r"(?:v=|youtu\.be/|/embed/|/live/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None


def _iso(s):
    try:
        return dt.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None


STREAM_ALT_JS = r"""<script>(function(){var el=document.getElementById('pd-alt');if(!el)return;var vid=el.dataset.vid;
el.addEventListener('click',function(e){var a=e.target.closest('a[data-v]');if(!a)return;e.preventDefault();   // 11/11/2026: toca aqui no site
 var box=document.querySelector('.pd-video');if(!box){box=document.createElement('div');box.className='pd-video';el.parentNode.insertBefore(box,el)}
 box.innerHTML='<iframe src="https://www.youtube-nocookie.com/embed/'+a.dataset.v+'?autoplay=1&mute=1&rel=0" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen title="'+a.textContent.replace(/[<>"]/g,'')+'"></iframe>';
 [].forEach.call(el.querySelectorAll('a[data-v]'),function(b){b.style.background=b===a?'var(--v)':'';b.style.color=b===a?'#08223a':''});box.scrollIntoView({behavior:'smooth',block:'center'})});
function bad(r,c){return !!(r&&c&&((r.b||[]).indexOf(c)>=0||((r.a||[]).length&&(r.a||[]).indexOf(c)<0)))}
Promise.all([fetch('/api/geo').then(function(r){return r.json()}).catch(function(){return{}}),fetch('/padel/yt-regions.json').then(function(r){return r.json()}).catch(function(){return{}})]).then(function(x){
 var c=x[0].c,R=x[1]||{};if(!c||!R[vid])return;
 if(bad(R[vid],c)){el.hidden=false;var t=el.querySelector('[data-t]');if(t)t.textContent="This court's stream isn't available in your country. Watch live on the other courts:";
  [].forEach.call(el.querySelectorAll('a[data-v]'),function(a){if(bad(R[a.dataset.v],c))a.remove()})}else{el.hidden=true}})})();</script>"""


def _stream_alts(db, m, v):
    """Se a transmissão do court deste jogo está bloqueada em vários países (código 451), mostra os outros courts do mesmo dia
    que passam em todo o lado. O script confirma pelo país do visitante (/api/geo + /padel/yt-regions.json) e esconde se não for preciso."""
    if not v or not v.get("id") or not m.get("played_at"):
        return ""
    emb = yt_player._emb_load()
    if (emb.get(v["id"]) or [0])[0] != 451:
        return ""
    rows = (db.videos.get(str(m.get("tid"))) or {}).get("rows") or []
    alts = []
    for x in rows:
        xid = _yt_id(x.get("url") or "")
        if xid and xid != v["id"] and (x.get("started_at") or "")[:10] == m["played_at"] and (emb.get(xid) or [0])[0] == 200:
            alts.append((xid, re.sub(r"^.*?:\s*", "", x.get("name") or "").strip() or "Other court"))
    chips = "".join(f'<a class="pd-btn" data-v="{esc(i)}" style="display:inline-block;width:auto;padding:8px 14px;margin:4px 6px 0 0" href="https://www.youtube.com/watch?v={esc(i)}" target="_blank" rel="noopener">▶ {esc(n)}</a>' for i, n in alts[:4])
    chips += '<a class="pd-btn" style="display:inline-block;width:auto;padding:8px 14px;margin:4px 6px 0 0" href="/padel/live.html">Live page</a>'
    return (f'<div class="pd-card" id="pd-alt" data-vid="{esc(v["id"])}" style="margin:10px 0 14px"><p class="pd-note" data-t>'
            f'This court\'s stream is blocked in some countries. If YouTube says it is unavailable, watch live on the other courts:</p>{chips}</div>' + STREAM_ALT_JS)


def video_for(db, m):
    """A transmissão (YouTube oficial) onde o jogo foi mostrado: mesmo dia e mesmo court (ou o vídeo único das meias/final),
    com o ponto de partida aproximado (hora marcada do jogo menos o início da transmissão). Devolve dict ou None."""
    rows = (db.videos.get(str(m.get("tid"))) or {}).get("rows") or []
    if not rows or not m.get("played_at"):
        return None
    day_rows = [v for v in rows if (v.get("url") or "").startswith("https://") and (v.get("started_at") or "")[:10] == m["played_at"]]
    if not day_rows:
        return None
    ck = _court_key(m.get("court"))
    rn = m.get("round")
    pick = None
    if rn in (1, 2):
        pick = next((v for v in day_rows if re.search(r"final|semi", v.get("name") or "", re.I)), None)
    if not pick and ck:
        cands = [v for v in day_rows if _court_key(re.sub(r"^.*?:", "", v.get("name") or "")) == ck or _court_key(v.get("name")) == ck]
        cands.sort(key=lambda v: ("🇬🇧" not in (v.get("name") or ""), "🇪🇸" in (v.get("name") or "")))   # inglês primeiro
        pick = cands[0] if cands else None
    if not pick and len(day_rows) == 1:
        pick = day_rows[0]
    if not pick:
        return None
    start = 0
    a, b = _iso(m.get("scheduled_at")), _iso(pick.get("started_at"))
    if a and b and (m.get("court_order") or 1) > 1:
        start = max(0, int((a - b).total_seconds()) - 300)
    yid = _yt_id(pick["url"])
    host = "YouTube" if yid else ("Red Bull TV" if "redbull" in pick["url"] else re.sub(r"^https://(www\.)?([^/]+).*$", r"\2", pick["url"]))
    return {"id": yid, "url": pick["url"], "start": start if yid else 0, "name": pick.get("name") or "", "host": host, "img": pick.get("photo_url")}


def _toks(s):
    return set(re.findall(r"[a-z]{3,}", unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()))


GENERIC = {"premier", "padel", "major", "fip", "tour", "cupra", "open", "cup", "the", "and", "platinum", "gold", "silver", "finals", "city"}


def _place_words(t):
    return (_toks(t.get("location")) | _toks(t.get("name"))) - GENERIC


def _place_ok(title, place):
    """O torneio tem de estar no título (aceita pequenas gralhas, ex.: 'Mellila' por 'Melilla')."""
    import difflib
    tt = _toks(title)
    return bool(tt & place) or any(difflib.SequenceMatcher(None, a, b).ratio() >= 0.85 for a in tt for b in place if len(a) >= 5 and len(b) >= 5)


def _in_window(t, pub, extra=3):
    try:
        d = dt.date.fromisoformat((pub or "")[:10])
        return dt.date.fromisoformat(t["start_date"]) <= d <= dt.date.fromisoformat(t["end_date"]) + dt.timedelta(days=extra)
    except (KeyError, TypeError, ValueError):
        return False


# canais com os vídeos bloqueados fora de um país (beIN SPORTS USA: só EUA). Ficam só como último recurso na página do jogo,
# onde o leitor salta para o seguinte se não der; nunca nas miniaturas nem nas etiquetas "▶ Highlights" (5/11/2026)
GEO_LOCKED = {"beIN SPORTS USA"}


def highlight_for(db, m, all_=False):
    """Resumo oficial do jogo (título 'A/B vs C/D | HIGHLIGHTS ... <torneio>') ou, se não houver, o resumo do dia
    ('Day N - Men's Highlights') do torneio. Devolve dict ou None."""
    t = db.tour(m.get("tid"))
    if not t or not db.highlights:
        return [] if all_ else None
    place = _place_words(t)
    A, Bt = team_players(m, "team_1"), team_players(m, "team_2")
    if len(A) < 2 or len(Bt) < 2:
        return [] if all_ else None
    sa = [(_toks(p.get("short_name")) | _toks(p.get("name"))) for p in A]       # apelido ou nome (ex.: 'Jairo' = Jairo Bautista)
    sb = [(_toks(p.get("short_name")) | _toks(p.get("name"))) for p in Bt]
    # ordem: Premier Padel (oficial) > canais de fãs > beIN SPORTS USA (oficial, mas só passa nos EUA: a maioria dos visitantes não o consegue ver)
    def _rank(kv):
        ch = kv[1].get("channel") or ""
        return (0 if ch == "Premier Padel" else 2 if ch == "beIN SPORTS USA" else 1, kv[1].get("published") or "")
    hl = sorted(db.highlights.items(), key=_rank)
    found = []
    for vid, h in hl:
        if h.get("kind") != "match" or not _in_window(t, h.get("published")) or not _place_ok(h.get("title"), place):
            continue
        if yt_player.embeddable(vid) is False:                         # removido ou sem autorização para ver fora do YouTube
            continue
        if not all_ and (h.get("channel") or "") in GEO_LOCKED:        # miniaturas e etiquetas "▶ Highlights": só vídeos que passam em todo o lado
            continue
        head = next((seg for seg in (h.get("title") or "").split("|") if re.search(r"\bvs\.?\b", seg, re.I)), "")
        if not head:
            continue
        pa, pb = [x.strip() for x in re.split(r"\bvs\.?\b", head, 1, flags=re.I)]
        ta, tb = [_toks(x) for x in re.split(r"[/&]", pa)], [_toks(x) for x in re.split(r"[/&]", pb)]
        def same(pair_t, pair_p):
            return len(pair_t) == 2 and all(any(x & y for y in pair_p) for x in pair_t)
        if (same(ta, sa) and same(tb, sb)) or (same(ta, sb) and same(tb, sa)):
            found.append({"id": vid, "kind": "match", "title": h["title"], "channel": h.get("channel"),
                          "official": h.get("official", h.get("channel") in ("Premier Padel", "beIN SPORTS USA"))})
            if not all_:
                return found[0]
    # resumo do dia
    main = sorted({x.get("played_at") for x in db.by_t.get(str(m.get("tid")), []) if (x.get("draw") or "main") == "main" and x.get("played_at")})
    if not main or not m.get("played_at"):
        return found if all_ else None
    try:
        n = (dt.date.fromisoformat(m["played_at"]) - dt.date.fromisoformat(main[0])).days + 1
    except ValueError:
        return found if all_ else None
    cat = "women" if m.get("category") == "women" else "men"
    for vid, h in db.highlights.items():
        ti = h.get("title") or ""
        if h.get("kind") != "day" or not _in_window(t, h.get("published")) or not _place_ok(ti, place) or yt_player.embeddable(vid) is False:
            continue
        mm = re.search(r"day\s*(\d+)", ti, re.I)
        isw = bool(re.search(r"women", ti, re.I))
        if mm and int(mm.group(1)) == n and (isw == (cat == "women")):
            d = {"id": vid, "kind": "day", "title": ti, "channel": h.get("channel"), "day": n}
            if not all_:
                return d
            found.append(d)
            break
    return found if all_ else None


def _clean(u):
    """Versão final do endereço na Cloudflare (sem .html; /index.html -> /): canonical e sitemap (5/11/2026)."""
    u = u or ""
    if u.endswith("index.html"):
        return u[: -len("index.html")]
    return u[:-5] if u.endswith(".html") else u


def _crumbs(items):
    """BreadcrumbList (caminho da página) para o Google: [(nome, caminho)]."""
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE_BASE + _clean(u)} for i, (n, u) in enumerate(items)]}


def mpath(m):
    return f"/padel/m/{m.get('id')}.html"


def _match_video(db, m):
    """Vídeo do jogo (resumo, transmissão do court e alternativas). Devolve (html, v). Comum às versões 1 e 2 da página do jogo."""
    body = ""
    hls = highlight_for(db, m, all_=True)
    v = video_for(db, m)
    vurl = (v["url"] + (("&t=" + str(v["start"]) + "s") if v.get("id") and v.get("start") else "")) if v else ""
    items = []
    for h in hls:
        lab = "▶ Match highlights" if h["kind"] == "match" else f"▶ Day {h['day']} highlights · {CAT.get(m.get('category'), '')}"
        cap = (f'{esc(h.get("channel") or "")} · {"official YouTube" if h.get("official", True) else "YouTube (fan channel)"}'
               + (" · the day's best moments, this match may or may not be in it" if h["kind"] == "day" else ""))
        items.append({"id": h["id"], "h": lab, "c": cap})
    if v and v.get("id"):                                              # último recurso (ou único): a transmissão do court
        items.append({"id": v["id"], "s": v.get("start") or 0, "h": "Watch",
                      "c": f'Official court stream on YouTube{" · starts around the scheduled time of this match" if v.get("start") else ""}. '
                           f'<a href="{esc(vurl)}" target="_blank" rel="noopener">Open on YouTube ↗</a>'})
    items = [x for x in items if yt_player.embeddable(x["id"]) is not False] or items[:1]   # só os que o YouTube deixa incorporar
    if items:
        body += (f'<h2 class="dh pd-hlh" id="pd-vh">{esc(items[0]["h"])}</h2>' + yt_player.box(items, "pd-video", "pd-vh", "pd-vc")
                 + f'<p class="pd-note" id="pd-vc">{items[0]["c"]}</p>')
        if hls and v:
            body += f'<p><a class="pd-btn" style="display:inline-block;width:auto;padding:10px 16px" href="{esc(vurl)}" target="_blank" rel="noopener">▶ Full court stream on {esc(v["host"])} ↗</a></p>'
        body += yt_player.JS
    elif v:
        body += (f'<h2 class="dh">Watch</h2><a class="pd-vlink" href="{esc(v["url"])}" target="_blank" rel="noopener">'
                 + (f'<img src="{esc(v["img"])}" alt="" loading="lazy">' if v.get("img") else "")
                 + f'<span>▶ Watch on {esc(v["host"])} ↗</span></a><p class="pd-note">Official broadcast of this round ({esc(v["name"])}). Availability may depend on your country.</p>')
    body += _stream_alts(db, m, v)                                      # 11/11/2026: transmissão bloqueada no país -> outros courts
    return body, v


def _match_shell(db, m, t, A, Bt, w, v, body):
    """Partilha, dados estruturados, título e moldura da página do jogo (versões 1 e 2)."""
    title = f'{" / ".join(disp(p) for p in A)} vs {" / ".join(disp(p) for p in Bt)}'
    sc = score_text(m, "team_1")
    if team_players(m, "team_1") and team_players(m, "team_2"):
        if w:
            _sh = f'{" / ".join(disp(p) for p in team_players(m, w))} beat {" / ".join(disp(p) for p in team_players(m, "team_2" if w == "team_1" else "team_1"))} {score_text(m, w)} at {t.get("name")}'
        else:
            _sh = f"{title} at {t.get('name')}"
        body += site_more.share_html(SITE_BASE + mpath(m), _sh, "Share this result" if w else "Share this match", sport="padel")
    _ev = {"@context": "https://schema.org", "@type": "SportsEvent", "sport": "Padel", "name": f"{title} · {t.get('name')}" + (f" · {m.get('round_name')}" if m.get("round_name") else ""),
           "url": SITE_BASE + _clean(mpath(m)), "eventStatus": "https://schema.org/EventScheduled",
           "competitor": [{"@type": "SportsTeam", "name": " / ".join(disp(p) for p in ps),
                           "athlete": [{"@type": "Person", "name": p.get("name")} for p in ps]} for ps in (A, Bt) if ps],
           "location": {"@type": "Place", "name": t.get("location") or t.get("name") or "", "address": ", ".join(x for x in [t.get("location"), t.get("country")] if x)},
           "superEvent": {"@type": "SportsEvent", "name": t.get("name"), "url": SITE_BASE + _clean(tpath(t))}}
    if m.get("scheduled_at") or m.get("played_at"):
        _ev["startDate"] = m.get("scheduled_at") or m.get("played_at")
    if w and sc:
        _ev["description"] = f"{title}: {sc}"
    _ld = [_ev, _crumbs([("Beyond Padel", "/padel/index.html"), (t.get("name") or "", tpath(t)), (title, mpath(m))])]
    return shell(f"{title}{(' ' + sc) if sc else ''}: {t.get('name')} {m.get('round_name') or ''} · Beyond Padel", body, mpath(m),
                 desc=f"{title}, {m.get('round_name') or ''} at {t.get('name')}: result{', head-to-head and the official video' if v else ' and head-to-head'}.",
                 tab="results", noindex=not sets_of(m), ld=_ld)


def page_match(db, m):
    """Página do jogo. Desde 13/11/2026 usa o novo desenho comum ao ténis (player_ui); MATCH_V2=0 volta ao antigo."""
    if os.environ.get("MATCH_V2", "1") != "0":
        try:
            return page_match_v2(db, m)
        except Exception as ex:
            print("Jogo padel v2 falhou:", m.get("id"), type(ex).__name__, ex)
    return page_match_v1(db, m)


def page_match_v1(db, m):
    t = db.tour(m.get("tid"))
    w = m.get("winner") if m.get("winner") in ("team_1", "team_2") else None
    A, Bt = team_players(m, "team_1"), team_players(m, "team_2")
    seeds = m.get("seeds") or {}
    try:
        dlabel = dt.date.fromisoformat(m.get("played_at")).strftime("%a %d %b %Y")
    except (TypeError, ValueError):
        dlabel = ""
    head = " · ".join(x for x in [esc(m.get("round_name") or ""), CAT.get(m.get("category"), ""), esc(dlabel), esc(m.get("court") or "")] if x)

    def side(team, ps):
        cls = ("w" if w == team else "l") if w else ""
        avs = "".join(avatar(p, "pd-av lg") for p in ps)
        names = "".join(f'<a href="{ppath(p)}">{flag(p.get("nationality"), 12)}{esc(p.get("name"))}'
                        f'{(" <small>" + rank_str(p.get("id"), db) + "</small>") if rank_str(p.get("id"), db) else ""}</a>' for p in ps)
        seed = seeds.get(team)
        return (f'<div class="pd-mside {cls}"><div class="pd-avs">{avs}</div><div class="nm">{names}</div>'
                f'{f"<span class=pd-seed>{esc(str(seed))}</span>" if seed else ""}'
                f'<div class="sc">{score_cells(m, team) if sets_of(m) else ""}</div></div>')
    status = ""
    if not sets_of(m):
        status = f'<p class="pd-when" style="margin:8px 0">{esc(m.get("schedule_label") or when_local(m) or "Scheduled")}</p>'
    elif m.get("status") in ("retired", "walkover"):
        status = f'<p class="pd-note">{esc(m.get("status").title())}</p>'
    body = (f'<section class="page-h"><p><a href="{tpath(t)}">← {esc(t.get("name") or "Tournament")}</a></p>'
            f'<div class="pd-meta"><span class="pd-tag">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</span> {head}</div></section>')
    score_html = f'<div class="pd-match">{side("team_1", A)}{side("team_2", Bt)}</div>{status}'
    try:                                                               # favorito pelo Elo (estimativa nossa, a partir do Elo da Padel API)
        from padel import elo as _elo
        _c = _elo.chance(A, Bt)
        try:                                                           # o Elo é o de hoje: só faz sentido para jogos por jogar ou das últimas 3 semanas
            _recent = not m.get("played_at") or (dt.date.today() - dt.date.fromisoformat(m["played_at"][:10])).days <= 21
        except ValueError:
            _recent = False
        if _c is not None and _recent:
            _nm = lambda ps: " / ".join(esc(p.get("short_name") or p.get("name") or "") for p in ps)
            _pa = round(_c * 100)
            score_html += (f'<div class="pd-elo"><div class="pd-elo-bar"><i style="width:{_pa}%"></i></div>'
                           f'<p class="pd-note"><b>{_nm(A)} {_pa}%</b> · <b>{_nm(Bt)} {100 - _pa}%</b> · '
                           f'chance to win, our estimate from the players\' current Elo ratings (Padel API)</p></div>')
    except Exception as e:
        print("Elo:", type(e).__name__, e)
    _vh, v = _match_video(db, m)
    body += _vh
    body += score_html                                                  # o vídeo vem primeiro, logo a seguir o resultado
    body += _nl_inline("Enjoyed this match? Get the padel week in one email")
    # percurso de cada par no torneio até este jogo
    ms = [x for x in db.by_t.get(str(m.get("tid")), []) if (x.get("draw") or "main") == (m.get("draw") or "main") and x.get("category") == m.get("category")]
    roads = ""
    for team, ps in (("team_1", A), ("team_2", Bt)):
        k = pair_key(ps) if len(ps) == 2 else None
        if not k:
            continue
        prev = [x for x in ms if (x.get("round") or 0) > (m.get("round") or 0) and any(pair_key(team_players(x, tt)) == k for tt in ("team_1", "team_2") if len(team_players(x, tt)) == 2)]
        prev.sort(key=lambda x: -(x.get("round") or 0))
        if prev:
            roads += f'<h3 class="pd-court">{" / ".join(esc(disp(p)) for p in ps)}</h3><div class="pd-card">' + "".join(match_html(x, db) for x in prev) + "</div>"
    if roads:
        body += '<h2 class="dh">Road to this match</h2>' + roads
    # confronto direto entre os dois pares
    if len(A) == 2 and len(Bt) == 2:
        ka, kb = pair_key(A), pair_key(Bt)
        h2h = [x for x, _ in db.by_pair.get(ka, []) if x.get("id") != m.get("id") and kb in {pair_key(team_players(x, tt)) for tt in ("team_1", "team_2") if len(team_players(x, tt)) == 2}]
        h2h = sorted({x["id"]: x for x in h2h}.values(), key=lambda x: x.get("played_at") or "", reverse=True)
        if h2h:
            wa = sum(1 for x in h2h if x.get("winner") in ("team_1", "team_2") and pair_key(team_players(x, x["winner"])) == ka)
            wb = sum(1 for x in h2h if x.get("winner") in ("team_1", "team_2") and pair_key(team_players(x, x["winner"])) == kb)
            body += (f'<h2 class="dh">Head-to-head <small class="pd-note">{wa}-{wb} before this match</small></h2><div class="pd-card">'
                     + "".join(match_html(x, db, show_tour=True) for x in h2h[:6]) + "</div>")
    nxt = [x for x in ms if w and (x.get("round") or 0) < (m.get("round") or 0) and len(team_players(m, w)) == 2
           and pair_key(team_players(m, w)) in {pair_key(team_players(x, tt)) for tt in ("team_1", "team_2") if len(team_players(x, tt)) == 2}]
    if nxt:
        nx = max(nxt, key=lambda x: x.get("round") or 0)
        body += '<h2 class="dh">Next match</h2><div class="pd-card">' + match_html(nx, db) + "</div>"
    return _match_shell(db, m, t, A, Bt, w, v, body)


def highlight_cards(db, limit=None):
    """[(jogo, highlight)] dos resumos de jogo, mais recentes primeiro."""
    out = []
    for m in db.matches:
        if (m.get("round") or 99) > 16 or not team_players(m, "team_1"):
            continue
        h = highlight_for(db, m)
        if h and h["kind"] == "match":
            out.append((m, h))
    out.sort(key=lambda mh: (mh[0].get("played_at") or "", -(mh[0].get("round") or 99)), reverse=True)
    return out[:limit] if limit else out


def hl_card(db, m, h):
    t = db.tour(m.get("tid"))
    w = m.get("winner")
    ta, tb = (w, "team_2" if w == "team_1" else "team_1") if w in ("team_1", "team_2") else ("team_1", "team_2")
    names = f'{" / ".join(esc(disp(p)) for p in team_players(m, ta))} <span>vs</span> {" / ".join(esc(disp(p)) for p in team_players(m, tb))}'
    sc = score_text(m, ta)
    return (f'<a class="pd-hl" href="{mpath(m)}" data-f="c:{m.get("category")} t:{tier(t)}"><div class="th"><img src="https://i.ytimg.com/vi/{h["id"]}/mqdefault.jpg" alt="" loading="lazy" width="320" height="180"><i>▶</i></div>'
            f'<div class="tx"><small>{esc(LEVEL_SHORT.get(t.get("level"), ""))} · {esc(t.get("location") or "")} · {esc(m.get("round_name") or "")} · {CAT.get(m.get("category"), "")}</small>'
            f'<b>{names}</b><span class="pd-note">{esc(sc)}{" · " + esc(h.get("channel") or "") if h.get("channel") else ""}</span></div></a>')


DAYV_JS = r"""<script>document.addEventListener("click",function(e){var a=e.target.closest("[data-v]"),b=document.getElementById("pd-dayv");if(!a||!b)return;e.preventDefault();
b.innerHTML='<iframe src="https://www.youtube-nocookie.com/embed/'+a.dataset.v+'?rel=0&autoplay=1" title="Video" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>';
b.scrollIntoView({behavior:"smooth",block:"center"})});</script>"""


def page_highlights(db):
    cards = highlight_cards(db)
    day = sorted([(k, h) for k, h in db.highlights.items() if h.get("kind") == "day" and yt_player.embeddable(k) is not False],
                 key=lambda kh: kh[1].get("published") or "", reverse=True)[:6]
    body = ('<section class="page-h"><h1>Highlights</h1><p>The best moments of the latest matches, to watch right here. Only videos that can be played on this site are listed.</p></section>')
    if day:
        body += ('<h2 class="dh">Day highlights</h2>'                   # vê-se aqui: as miniaturas trocam o vídeo do leitor
                 + yt_player.box([{"id": day[0][0]}], "pd-video").replace('class="pd-video"', 'class="pd-video" id="pd-dayv"', 1)
                 + '<div class="pd-vgrid">') + "".join(
            f'<a href="https://www.youtube.com/watch?v={k}" data-v="{k}" target="_blank" rel="noopener"><img src="https://i.ytimg.com/vi/{k}/mqdefault.jpg" alt="" loading="lazy" width="320" height="180">'
            f'<b>{esc(re.sub(r"^.*?:\s*", "", h.get("title") or ""))}</b><span class="pd-note">{esc(re.sub(r"[^A-Za-z0-9 ]", "", (h.get("title") or "").split(":")[0]).strip())} · {esc((h.get("published") or "")[:10])}</span></a>'
            for k, h in day) + "</div>" + DAYV_JS + yt_player.JS
    body += '<h2 class="dh">Matches</h2>' + filters([("c", [("", "All"), ("men", "Men"), ("women", "Women")]), ("t", [("", "All events"), ("premier", "Premier Padel"), ("fip", "FIP Tour")])])
    body += ('<div class="pd-hls">' + "".join(hl_card(db, m, h) for m, h in cards[:60]) + "</div>") if cards else '<p class="empty">No match highlights yet.</p>'
    return shell("Padel highlights · Beyond Padel", body + FILTER_JS, "/padel/highlights.html", tab="highlights",
                 desc="Video highlights of the latest Premier Padel and FIP Tour matches.")


LIVE_PAGE_JS = r"""<script>(function(){
var T=JSON.parse(document.getElementById('pd-lt').textContent),box=document.getElementById('pd-live'),pl=document.getElementById('pd-player'),ch=document.getElementById('pd-chips');
var today=new Date().toISOString().slice(0,10),streams=[],cur=null;
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function yt(u){var m=/(?:v=|youtu\.be\/|\/embed\/|\/live\/)([A-Za-z0-9_-]{11})/.exec(u||'');return m?m[1]:null}
function sn(p){var n=(p.name||'').split(' ');return (n.length>1?n[0][0]+'. ':'')+(p.short_name||n[n.length-1])}
function pair(ps){return (ps||[]).map(sn).join(' / ')||'TBD'}
function g(x){var m=/^(\d+)/.exec(x||'');return m?+m[1]:-1}
function cells(sc,t){var o=t=='team_1'?'team_2':'team_1';return (sc||[]).map(function(s){return '<b class="'+(g(s[t])>g(s[o])?'on':'')+'">'+esc(String(s[t]||'').replace(/\(.*\)/,''))+'</b>'}).join('')}
function play(i){cur=i;var s=streams[i];if(!s)return;var id=yt(s.url);
 pl.innerHTML=id?'<div class="pd-video"><iframe src="https://www.youtube-nocookie.com/embed/'+id+'?autoplay=1&mute=1&rel=0" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen title="'+esc(s.name)+'"></iframe></div>'
  :'<a class="pd-vlink" href="'+esc(s.url)+'" target="_blank" rel="noopener">'+(s.photo_url?'<img src="'+esc(s.photo_url)+'" alt="">':'')+'<span>▶ Watch on Red Bull TV ↗</span></a>';
 [].forEach.call(ch.querySelectorAll('button'),function(b){b.className=+b.dataset.i===i?'on':''})}
function court(n){return String(n||'').replace(/^.*?:\s*/,'').replace(/\s*\(.*?\)\s*/g,' ').trim()||n}
var GEO=Promise.all([fetch('/api/geo').then(function(r){return r.json()}).catch(function(){return{}}),fetch('/padel/yt-regions.json').then(function(r){return r.json()}).catch(function(){return{}})]);
function blocked(v,g){var r=g[1][yt(v.url)],c=g[0].c;return !!(r&&c&&((r.b||[]).indexOf(c)>=0||((r.a||[]).length&&(r.a||[]).indexOf(c)<0)))}
GEO.then(function(g){return Promise.all(T.map(function(t){return fetch('/api/padel/videos/'+t.id).then(function(r){return r.ok?r.json():{videos:[]}}).catch(function(){return {videos:[]}})})).then(function(rs){return [rs,g]})}).then(function(x){var rs=x[0],g=x[1];
 rs.forEach(function(r,k){(r.videos||[]).forEach(function(v){if((v.started_at||'').slice(0,10)===today){v.t=T[k];v.bl=blocked(v,g);streams.push(v)}})});
 streams.sort(function(a,b){function sc(v){return (v.bl?10:0)+(yt(v.url)?0:2)+(/🇬🇧|cent/i.test(v.name)?0:1)+(v.t.premier?0:3)}return sc(a)-sc(b)});
 if(!streams.length){pl.innerHTML='<p class="pd-note">No live video for today\'s tournaments: the scores below update every 2 minutes.</p>';return}
 ch.innerHTML=streams.map(function(s,i){return '<button data-i="'+i+'">'+esc(s.t.loc)+' · '+esc(court(s.name))+(yt(s.url)?'':' ↗')+(s.bl?' · not in your country':'')+'</button>'}).join('');
 ch.onclick=function(e){var b=e.target.closest('button');if(b)play(+b.dataset.i)};play(0)});
function load(){Promise.all(T.map(function(t){return fetch('/api/padel/matches/'+t.id+'?date='+today).then(function(r){return r.ok?r.json():{matches:[]}}).catch(function(){return {matches:[]}})})).then(function(rs){
 var html='';rs.forEach(function(r,k){var t=T[k],ms=(r.matches||[]).filter(function(m){return m.players&&m.players.team_1&&m.players.team_1.length});if(!ms.length)return;
  var live=ms.filter(function(m){return m.score&&!m.winner&&m.status!=='finished'}),next=ms.filter(function(m){return !m.score&&m.status!=='finished'}),done=ms.filter(function(m){return m.winner});
  function row(m,tag){return '<a class="pd-lm" href="/padel/m/'+m.id+'.html"><div class="r">'+tag+esc(m.round_name||'')+' · '+(m.category=='women'?'Women':'Men')+(m.court?' · '+esc(m.court):'')+'</div>'
   +'<div class="pd-t '+(m.winner=='team_1'?'w':m.winner?'l':'')+'">'+esc(pair(m.players.team_1))+'</div><div class="pd-sc">'+(m.score?cells(m.score,'team_1'):'<span class="pd-when">'+esc(m.schedule_label||'')+'</span>')+'</div>'
   +'<div class="pd-t '+(m.winner=='team_2'?'w':m.winner?'l':'')+'">'+esc(pair(m.players.team_2))+'</div><div class="pd-sc">'+(m.score?cells(m.score,'team_2'):'')+'</div></a>'}
  html+='<div class="pd-card"><div class="pd-gh"><span class="pd-tag">'+esc(t.lvl)+'</span><a href="'+t.url+'"><b>'+esc(t.loc)+'</b></a><span class="pd-note">'+live.length+' live · '+next.length+' to play</span></div>'
   +live.map(function(m){return row(m,'<span class="pd-livetag">LIVE</span> ')}).join('')+next.slice(0,6).map(function(m){return row(m,'')}).join('')
   +(done.length?'<details class="pd-more2"><summary>'+done.length+' finished today</summary>'+done.map(function(m){return row(m,'')}).join('')+'</details>':'')+'</div>'});
 box.innerHTML=html||'<p class="empty">No matches on court right now.</p>';var u=document.getElementById('pd-lu');if(u)u.textContent='Updated '+new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})})}
load();setInterval(function(){if(!document.hidden)load()},60000)})();</script>"""


def page_live(db):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    live = sorted([t for t in db.tours.values() if t.get("status") == "live" or (t.get("start_date", "") <= today <= t.get("end_date", ""))],
                  key=lambda t: LEVEL_ORDER.get(t.get("level"), 9))
    T = [{"id": t["id"], "loc": t.get("location") or t.get("name"), "lvl": LEVEL_SHORT.get(t.get("level"), ""), "url": tpath(t),
          "premier": (t.get("level") or "") in ("major", "p1", "p2", "finals")} for t in live]
    body = ('<section class="page-h"><h1><span class="dot" style="display:inline-block;margin-right:10px"></span>Live</h1>'
            '<p>Official live streams and the scores of today\'s matches, updated every 2 minutes.</p></section>'
            '<div id="pd-player"><div class="pd-card"><p class="pd-note">Loading streams…</p></div></div><div class="pd-seg pd-rchips pd-lchips" id="pd-chips"></div>'
            '<h2 class="dh">On court today <small class="pd-note" id="pd-lu"></small></h2><div id="pd-live"><p class="pd-note">Loading…</p></div>')
    if not live:
        nxt = sorted([t for t in db.tours.values() if t.get("status") == "pending" and (t.get("start_date") or "") >= today], key=lambda t: t.get("start_date") or "")[:3]
        body = ('<section class="page-h"><h1>Live</h1><p>No tournament is being played right now.</p></section>'
                + ('<div class="pd-list">' + "".join(f'<a href="{tpath(t)}"><span class="pd-tag g">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</span><b>{esc(t.get("location") or t.get("name"))}</b>'
                                                     f'<span class="pd-note">starts {esc(t.get("start_date"))}</span></a>' for t in nxt) + "</div>" if nxt else ""))
        return shell("Live padel: streams and scores · Beyond Padel", body, "/padel/live.html", tab="live")
    body += '<script type="application/json" id="pd-lt">' + json.dumps(T).replace("</", "<\\/") + "</script>" + LIVE_PAGE_JS
    return shell("Live padel: streams and scores · Beyond Padel", body, "/padel/live.html", tab="live",
                 desc="Watch Premier Padel live (official streams) and follow today's padel scores, updated every 2 minutes.")


def page_players(db):
    rows = []
    for pid, p in db.pinfo.items():
        r = db.rank_of.get(pid) or {}
        rows.append((r.get("ranking") or 9999, p))
    rows.sort(key=lambda x: (x[0], x[1].get("name") or ""))
    items = [{"n": p.get("name"), "u": ppath(p), "k": country_name(p.get("nationality")), "r": rk if rk < 9999 else None} for rk, p in rows]
    tr = "".join(f'<tr><td>{(str(rk) if rk < 9999 else "–")}</td><td class="pn">{plink(p)}</td><td class="lt">{esc(CAT.get(p.get("category"), ""))}</td></tr>'
                 for rk, p in rows[:100])
    body = (f'<section class="page-h"><h1>Players</h1><p>{len(rows):,} players in our padel database. The 100 best ranked are below; search to find anyone.</p><p class="pd-sub"><a href="/padel/countries.html">Players by country ›</a></p></section>'.replace(",", " ") +
            '<input class="srch" id="q" placeholder="Search player or country" autocomplete="off">'
            f'<table class="pt" id="tb"><thead><tr><th>#</th><th>Player</th><th>Cat.</th></tr></thead><tbody>{tr}</tbody></table>'
            '<script>const P=' + json.dumps(items, ensure_ascii=False) + ';const tb=document.querySelector("#tb tbody");'
            'document.getElementById("q").oninput=e=>{const q=e.target.value.toLowerCase().trim();if(!q)return;'
            'tb.innerHTML=P.filter(x=>(x.n+" "+x.k).toLowerCase().includes(q)).slice(0,200).map(x=>`<tr><td>${x.r||"–"}</td><td class="pn"><a href="${x.u}">${x.n}</a> <small>${x.k}</small></td><td></td></tr>`).join("")}</script>')
    return shell("Padel players · Beyond Padel", body, "/padel/players.html", tab="players")


def page_countries(db):
    by = {}
    for pid, p in db.pinfo.items():
        by.setdefault(p.get("nationality") or "?", []).append(p)
    body = ('<section class="page-h"><h1>Countries</h1><p>Players in our database by country. Open a country to see its best-ranked players.</p></section>'
            '<input class="srch" id="cq" placeholder="Search country" autocomplete="off"><div class="pd-ctry">')
    for c, ps in sorted(by.items(), key=lambda kv: -len(kv[1])):
        ps.sort(key=lambda p: (db.rank_of.get(str(p.get("id"))) or {}).get("ranking") or 9999)
        top = ps[0] if ps else {}
        body += (f'<details data-n="{esc(country_name(c).lower())}"><summary>{flag(c, 14)}<b>{esc(country_name(c))}</b>'
                 f'<span class="pd-note">{len(ps)} players{(" · best: " + esc(disp(top)) + " " + rank_str(top.get("id"), db)) if rank_str(top.get("id"), db) else ""}</span></summary>'
                 + "".join(f'<a href="{ppath(p)}">{esc(p.get("name"))} <small class="pd-note">{rank_str(p.get("id"), db)}</small></a>' for p in ps[:10]) + "</details>")
    body += ('</div><script>document.getElementById("cq").oninput=function(e){var v=e.target.value.toLowerCase();'
             'document.querySelectorAll(".pd-ctry details").forEach(function(d){d.hidden=v&&d.dataset.n.indexOf(v)<0})}</script>')
    return shell("Padel players by country · Beyond Padel", body, "/padel/countries.html", tab="countries")


def update_rank_hist(db):
    """Guarda uma cópia semanal do ranking (top 500) em padel/data/rank_hist.json. Na primeira vez reconstrói
    também a semana anterior a partir da variação (ranking_diff), para o gráfico começar com 2 pontos."""
    fp = os.path.join(DATA, "rank_hist.json")
    h = load("rank_hist.json", {})
    changed = False
    for cat in ("men", "women"):
        r = db.ranks.get(cat) or {}
        d = (r.get("date") or "")[:10]
        rows = r.get("rows") or []
        if not d or not rows:
            continue
        hc = h.setdefault(cat, {})
        if d not in hc:
            if not hc:
                try:
                    prev = (dt.date.fromisoformat(d) - dt.timedelta(days=7)).isoformat()
                    hc[prev] = {str(x["id"]): (x.get("ranking") or 0) + (x.get("ranking_diff") or 0) for x in rows
                                if x.get("ranking") and (x.get("ranking") or 0) + (x.get("ranking_diff") or 0) > 0}
                except (TypeError, ValueError, KeyError):
                    pass
            hc[d] = {str(x["id"]): x.get("ranking") for x in rows if x.get("ranking")}
            for old in sorted(hc)[:-60]:                               # guarda até ~60 semanas
                hc.pop(old)
            changed = True
    if changed:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(h, f, separators=(",", ":"))
    db._rh = h


def build(out_dir="site"):
    db = DB()
    out = out_dir
    paths = []
    from padel import site_extras as sx
    try:
        update_rank_hist(db)
    except Exception as e:
        print("Padel histórico de ranking falhou:", type(e).__name__, e)
    global CSS_VER
    import hashlib
    try:
        import webapp
        import extras
        _base = webapp.CSS + extras.EXTRA_CSS
    except Exception:
        _base = ""
    CSS_VER = hashlib.sha1((_base + CSS + site_ui.CSS + sport_switch.CSS + site_nav.CSS).encode()).hexdigest()[:8]
    try:
        write_photos(out)
    except Exception as e:
        print("Padel fotos falharam:", type(e).__name__, e)
    try:
        OG_MAP.update(sx.build_og(db, out))
    except Exception as e:
        print("Padel OG falhou:", type(e).__name__, e)
    global LIVE_ON
    try:
        LIVE_ON = live_now(db)
        LIVE_TIDS[:] = [t["id"] for t in db.tours.values() if t.get("status") == "live"]
    except Exception as e:
        print("Padel live_now falhou:", type(e).__name__, e)
    print("Padel: separador Live", "visível" if LIVE_ON else "escondido")
    _home = page_index(db)
    paths.append(write(out, "/padel/index.html", _home))
    write(out, "/padel/i/index.html", _home.replace("<head>", "<head><meta name=robots content=noindex,follow>", 1))   # bio do Instagram do padel
    paths.append(write(out, "/padel/results.html", page_results(db)))
    paths.append(write(out, "/padel/order-of-play.html", page_oop(db)))
    paths.append(write(out, "/padel/tournaments.html", page_tournaments(db)))
    for cat in ("men", "women"):
        paths.append(write(out, f"/padel/rankings-{cat}.html", page_rankings(db, cat)))
    paths.append(write(out, "/padel/rankings.html", page_rankings(db, "men")))
    paths.append(write(out, "/padel/players.html", page_players(db)))
    paths.append(write(out, "/padel/countries.html", page_countries(db)))
    paths.append(write(out, "/padel/highlights.html", page_highlights(db)))
    paths.append(write(out, "/padel/live.html", page_live(db)))
    try:                                                               # 11/11/2026: países de cada transmissão (dados do YouTube)
        with open(os.path.join(out, "padel", "yt-regions.json"), "w", encoding="utf-8") as f:
            json.dump({k: {"a": v.get("a") or [], "b": v.get("b") or []} for k, v in yt_player.regions().items()}, f, separators=(",", ":"))
    except Exception as e:
        print("Padel: yt-regions falhou", type(e).__name__, e)
    for fn, fnc in (("/padel/next-week.html", sx.page_next_week), ("/padel/stats.html", sx.page_stats), ("/padel/credits.html", sx.page_credits),
                    ("/padel/power.html", sx.page_power), ("/padel/race.html", sx.page_race)):
        try:
            paths.append(write(out, fn, fnc(db)))
        except Exception as e:
            print("Padel", fn, "falhou:", type(e).__name__, e)
    try:
        print("Pesquisa global:", sx.add_to_search(db, out), "entradas")
    except Exception as e:
        print("Padel pesquisa falhou:", type(e).__name__, e)
    for t in db.tours.values():
        paths.append(write(out, tpath(t), page_tournament(db, t)))
    for pid, p in db.pinfo.items():
        if p.get("name"):
            paths.append(write(out, ppath(p), page_player(db, pid, p)))
    nm = 0
    for m in db.matches:
        if team_players(m, "team_1") and team_players(m, "team_2"):
            write(out, mpath(m), page_match(db, m))
            nm += 1
    print(f"Padel: {nm} páginas de jogo.")
    pairs = {}
    for m in db.matches:
        for tm in ("team_1", "team_2"):
            team = team_players(m, tm)
            if len(team) == 2:
                pairs.setdefault(pair_key(team), team)
    for key, team in pairs.items():
        paths.append(write(out, pair_path(team), page_pair(db, key, team)))
    try:
        import webapp
        import extras
        base_css = webapp.CSS + extras.EXTRA_CSS
    except Exception:
        base_css = ""
    with open(os.path.join(out, "padel", "style.css"), "w", encoding="utf-8") as f:
        f.write(base_css + CSS + site_ui.CSS + sport_switch.CSS + site_nav.CSS)
    with open(os.path.join(out, "padel", "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(EMBLEM.replace('<svg viewBox', '<svg xmlns="http://www.w3.org/2000/svg" viewBox'))
    # sitemap próprio (o robots.txt do site aponta para ele)
    urls = ["/padel/index.html", "/padel/results.html", "/padel/tournaments.html", "/padel/order-of-play.html", "/padel/rankings-men.html",
            "/padel/rankings-women.html", "/padel/players.html", "/padel/countries.html", "/padel/next-week.html", "/padel/stats.html", "/padel/highlights.html", "/padel/live.html",
            "/padel/power.html", "/padel/race.html"]
    # Só as páginas com mais conteúdo (um site novo tem pouca "atenção" do Google: melhor 2000 páginas boas do que 5000 fracas).
    # As outras continuam no site e ligadas entre si; só não são pedidas ao Google no sitemap.
    lm = {u: "" for u in urls}
    for t in db.tours.values():
        lm[tpath(t)] = (t.get("end_date") or t.get("start_date") or "")[:10]
    _cut = (dt.date.today() - dt.timedelta(days=45)).isoformat()
    for pid, p in db.pinfo.items():
        ms_ = db.by_p.get(pid) or []
        rk_ = (db.rank_of.get(str(pid)) or {}).get("ranking")
        if p.get("name") and (len(ms_) >= 3 or (isinstance(rk_, int) and rk_ <= 200)):
            lm[ppath(p)] = max(((m.get("played_at") or "")[:10] for m, _ in ms_), default="")
    for m in db.matches:
        if not (sets_of(m) and (m.get("draw") or "main") == "main" and team_players(m, "team_1")):
            continue
        if (m.get("round") or 99) <= 8 or (m.get("played_at") or "") >= _cut:      # oitavos em diante, ou recentes
            lm[mpath(m)] = (m.get("played_at") or "")[:10]
    try:                                              # páginas principais em espanhol (7/11/2026)
        from padel import es as _es
        _esp = _es.make_all(out)                      # 12/11/2026: espanhol, italiano e francês
        paths += _esp
        for u in _es.EN_PAGES:
            for lg in _es.LANGS:
                lm[_es.lpath(u, lg)] = ""
        print(f"Padel: {len(_esp)} páginas traduzidas (es, it, fr).")
    except Exception as e:
        print("Padel espanhol falhou:", type(e).__name__, e)
    with open(os.path.join(out, "padel", "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                + "".join(f"<url><loc>{SITE_BASE}{esc(_clean(u))}</loc>" + (f"<lastmod>{d}</lastmod>" if d else "") + "</url>\n" for u, d in lm.items())
                + "</urlset>\n")
    print(f"Padel sitemap: {len(lm)} páginas (das mais completas).")
    print(f"Padel: {len(paths)} páginas em {out}/padel ({len(db.tours)} torneios, {len(db.matches)} jogos, {len(db.pinfo)} jogadores, {len(pairs)} pares).")
    return paths




# ---------------------------------------------------------------- ficha do jogador, versão 2 (13/11/2026, igual ao ténis)
RSHORT = {1: "F", 2: "SF", 4: "QF", 8: "R16", 16: "R32", 32: "R64", 64: "R128"}


def _p_rshort(m):
    r = m.get("round")
    q = (m.get("draw") or "main") != "main"
    if q:
        return "Q"
    return RSHORT.get(r, esc(str(m.get("round_name") or ""))[:4])


def _p_runs(ms):
    """[(tid, [(m, tm), ...])] por torneio, do mais recente para o mais antigo."""
    out, idx = [], {}
    for m, tm in ms:
        k = str(m.get("tid"))
        if k not in idx:
            idx[k] = len(out)
            out.append((k, []))
        out[idx[k]][1].append((m, tm))
    return out


def _p_outcome(run):
    """(etiqueta, é título?, frase da pílula) do melhor resultado no quadro principal."""
    main = [(m, tm) for m, tm in run if (m.get("draw") or "main") == "main" and m.get("winner") in ("team_1", "team_2")]
    if not main:
        return ("", False, "")
    best = min(main, key=lambda x: x[0].get("round") or 99)
    m, tm = best
    r = m.get("round") or 99
    won = m.get("winner") == tm
    if r == 1:
        return ("Title", True, "Champion") if won else ("Final", False, "Finalist")
    if won:
        return (f"Won {RSHORT.get(r, '')}".strip(), False, "")
    return {2: ("Semi-final", False, "Semi-finalist"), 4: ("Quarter-final", False, "Quarter-finalist")}.get(r, (f"Lost {RSHORT.get(r, '')}".strip(), False, ""))


def _p_score(m, tm):
    ot = "team_2" if tm == "team_1" else "team_1"
    out = ""
    for a, b in sets_of(m):
        mine, oth = (a, b) if tm == "team_1" else (b, a)
        tb = re.search(r"\((\d+)\)", mine) or re.search(r"\((\d+)\)", oth)
        out += f'<i>{games(mine)}-{games(oth)}{f"<sup>{tb.group(1)}</sup>" if tb else ""}</i>'
    return out


def _p_event(db, pid, tid, run):
    import player_ui as pu
    t = db.tour(tid) or {}
    label, is_title, _ = _p_outcome(run)
    m0 = run[0][0]
    sub = " · ".join(x for x in [LEVEL_SHORT.get(t.get("level"), ""), date_range(t), CAT.get(m0.get("category"), "")] if x)
    title = f'<a href="{tpath(t)}">{esc(t.get("location") or t.get("name") or "")}</a>' if t else esc(str(tid))
    rows = []
    for m, tm in run:
        rows.append(_p_row(db, m, tm, pid))
    return pu.event(title, sub, label, rows, is_title)


def _p_row(db, m, tm, pid=None, rd=None):
    """Uma linha de jogo (ronda, adversários, resultado) do ponto de vista da equipa tm."""
    ot = "team_2" if tm == "team_1" else "team_1"
    opp = team_players(m, ot)
    mate = [q for q in team_players(m, tm) if pid is not None and str(q.get("id")) != str(pid)]
    nm = " / ".join(f'<a href="{ppath(q)}">{esc(disp(q))}</a>' for q in opp) or "TBD"
    rk = [rank_str(q.get("id"), db) for q in opp]
    osub = " · ".join(x for x in [("with " + disp(mate[0])) if mate else "", " ".join(x for x in rk if x)] if x)
    st = m.get("status")
    if m.get("winner") in ("team_1", "team_2"):
        sc, won = _p_score(m, tm) or "–", m.get("winner") == tm
    elif st == "live":
        sc, won = '<span class="pd-live">● LIVE</span>', None
    else:
        sc, won = esc(m.get("schedule_label") or when_local(m) or ""), None
    href = mpath(m) if opp and team_players(m, tm) else ""
    return (rd or _p_rshort(m), nm, osub, sc, href, won)


def page_player_v2(db, pid, p):
    import player_ui as pu
    ms = player_matches(db, pid)
    done = [(m, tm) for m, tm in ms if m.get("winner") in ("team_1", "team_2")]
    w = sum(1 for m, tm in done if m["winner"] == tm)
    r = db.rank_of.get(str(pid)) or {}
    rk = r.get("ranking") or p.get("ranking")
    d = r.get("ranking_diff") or 0
    titles = sum(1 for m, tm in done if m.get("round") == 1 and m["winner"] == tm and (m.get("draw") or "main") == "main")
    finals = sum(1 for m, tm in done if m.get("round") == 1 and (m.get("draw") or "main") == "main")
    name = p.get("name") or ""
    runs = _p_runs(ms)

    # --- topo
    chips = []
    nat = p.get("nationality")
    if nat:
        chips.append(f'<span>{flag(nat, 14)}{esc(country_name(nat))}</span>')
    if p.get("age"):
        chips.append(f"Age {p['age']}")
    if isinstance(p.get("height"), (int, float)) and 150 <= p["height"] <= 215:
        chips.append(f"{p['height'] / 100:.2f} m")
    side = {"drive": "Right side (drive)", "backhand": "Left side (backhand)"}.get(p.get("side") or "", "")
    if side:
        chips.append(side)
    hand = {"right": "Right-handed", "left": "Left-handed"}.get(str(p.get("hand") or "").lower(), "")
    if hand:
        chips.append(hand)
    chips = [c if c.startswith("<") else esc(c) for c in chips]
    chips = [c[6:-7] if c.startswith("<span>") else c for c in chips]
    pill, pill_href = "", ""
    for tid, run in runs:
        _, _, phrase = _p_outcome(run)
        t = db.tour(tid) or {}
        try:
            dl = dt.date.fromisoformat((t.get("end_date") or run[0][0].get("played_at") or "")[:10])
        except ValueError:
            dl = None
        if any(m.get("winner") in ("team_1", "team_2") for m, _ in run):
            if phrase and dl and (dt.date.today() - dl).days <= 21:
                pill, pill_href = esc(f"{phrase} · {t.get('location') or t.get('name') or ''} · {dl.strftime('%-d %b')}"), "#results"
            break
    c = photo_credit(pid) if has_photo(pid) else {}
    top_left = pu.hero("/padel/rankings.html", "Rankings", f"/padel/img/{pid}.jpg" if has_photo(pid) else "", name, chips, pill,
                       esc(c.get("credit") or ""), pill_href)

    # --- cartão do ranking
    hist = [(dd, x) for dd, x in db.rank_hist(pid) if x]
    chart, axis = "", ()
    if len(hist) >= 2 and len({x for _, x in hist}) >= 2:
        lo, hi = min(x for _, x in hist), max(x for _, x in hist)
        n = len(hist) - 1
        chart = pu.sparkline([(i / n, (x - lo) / max(1, hi - lo)) for i, (_, x) in enumerate(hist)],
                             label=f"Ranking over the last {len(hist)} weeks, best No. {lo}")
        try:
            d0 = dt.date.fromisoformat(hist[0][0][:10]).strftime("%-d %b")
        except ValueError:
            d0 = hist[0][0]
        axis = (f"{d0} · No. {hist[0][1]}", f"Best No. {lo}", "Now")
    minis = []
    race = p.get("race") if isinstance(p.get("race"), dict) else {}
    if race.get("ranking"):
        minis.append((f'{race["ranking"]}', "Race to the Finals"))
    if done and finals:
        minis.append((f"{titles}/{finals}", "titles / finals"))
    if done:
        minis.append((f"{w}-{len(done) - w}", "won-lost"))
        minis.append((f"{round(100 * w / len(done))}%", "win rate"))
    pts = r.get("points") or p.get("points")
    pts = f"{pts:,}".replace(",", " ") if isinstance(pts, int) else (pts or "")
    lab = {"men": "Men's padel ranking", "women": "Women's padel ranking"}.get(p.get("category"), "Padel ranking")
    top_right = pu.rank_card(lab, rk or "", d if isinstance(d, int) else None, pts, "points", chart, axis, minis,
                             "Weekly ranking: our own copies of the official ranking" if chart else "")
    if not top_right:
        top_right = pu.rank_card("Matches we tracked", "", None, f"{w}-{len(done) - w}", "won-lost")

    # --- principal
    main = pu.h2("overview", "Form", f"<small>{w}-{len(done) - w} in the matches we tracked</small>" if done else "")
    main += pu.form([(m["winner"] == tm, _p_rshort(m)) for m, tm in done[:6]])
    if done:
        main += '<div class="pv-note">Round · newest first</div>'
    if runs:
        main += pu.h2("results", f"{esc(name)} results", f"<small>{len(done)} match{'es' if len(done) != 1 else ''} we tracked</small>")
        main += "".join(_p_event(db, pid, tid, run) for tid, run in runs[:4])
        if len(runs) > 4:
            older = sum(len(run) for _, run in runs[4:])
            main += pu.more(f"Older results ({older} matches)", "".join(_p_event(db, pid, tid, run) for tid, run in runs[4:]))
    hv = [(m, h) for m, tm in ms for h in [highlight_for(db, m)] if h and h["kind"] == "match"][:8]
    if hv:
        main += '<h2 class="pv-h">▶ Highlights</h2><div class="pd-hls row">' + "".join(hl_card(db, m, h) for m, h in hv) + "</div>"

    # --- lateral: números e parceiros
    sidebar = pu.h2("stats", "Season &amp; partners")
    cards = []
    if done:
        cards.append(pu.stat_card("Matches we tracked", f"{w}-{len(done) - w}", f"{round(100 * w / len(done))}% won"))
        cards.append(pu.stat_card("Titles", f"{titles}", f"from {finals} final{'s' if finals != 1 else ''}"))
    if cards:
        sidebar += f'<div class="pv-two">{"".join(cards)}</div>'
    lv = {}
    for m, tm in done:
        t = db.tour(m.get("tid")) or {}
        k = t.get("level") or ""
        x = lv.setdefault(k, [0, 0])
        x[0 if m["winner"] == tm else 1] += 1
    sidebar += pu.bars("By level · win %", [(LEVEL_SHORT.get(k, k.upper()).title().replace("Fip", "FIP").replace("P1", "P1"), f"{a}-{b}", round(100 * a / (a + b)))
                                         for k, (a, b) in sorted(lv.items(), key=lambda kv: LEVEL_ORDER.get(kv[0], 9)) if a + b])
    elo = p.get("elo")
    if isinstance(elo, dict) and elo.get("ranking"):
        sidebar += f'<div class="pv-sub">Elo rating rank: <b>No. {elo["ranking"]}</b></div>'
    partners = {}
    for m, tm in ms:
        for q in team_players(m, tm):
            if str(q.get("id")) != str(pid):
                e = partners.setdefault(str(q.get("id")), {"p": q, "n": 0, "w": 0, "team": team_players(m, tm)})
                e["n"] += 1
                e["w"] += 1 if m.get("winner") == tm else 0
    ph = [x for x in p.get("pairs_hist") or [] if len(x.get("players") or []) == 2]
    prow = ""
    if ph:
        def _mon(x):
            try:
                return dt.date.fromisoformat(x[:10]).strftime("%b %Y")
            except (TypeError, ValueError):
                return ""
        for x in sorted(ph, key=lambda x: (x.get("status") == "current", x.get("last") or ""), reverse=True)[:8]:
            q = next((y for y in x["players"] if str(y.get("id")) != str(pid)), None)
            if not q:
                continue
            e = partners.get(str(q.get("id")))
            sub = f'{_mon(x.get("first"))} – {"now" if x.get("status") == "current" else _mon(x.get("last"))}' + (f' · {e["w"]}-{e["n"] - e["w"]} in our data' if e else "")
            prow += site_ui.rank_row("", avatar(q, "av"), f'<a href="{pair_path(x["players"])}">{esc(q.get("name"))}</a>', esc(sub),
                                     "Current" if x.get("status") == "current" else "", False, "")
    elif partners:
        for e in sorted(partners.values(), key=lambda e: -e["n"])[:6]:
            prow += site_ui.rank_row("", avatar(e["p"], "av"), f'<a href="{pair_path(e["team"])}">{esc(e["p"].get("name"))}</a>',
                                     esc(f'{e["n"]} matches · {e["w"]}-{e["n"] - e["w"]}'), "", False, "")
    if prow:
        sidebar += '<div class="pv-card" style="padding:12px"><div class="pv-lab" style="margin:4px 4px 10px">Partners</div><div class="ui-rk">' + prow + "</div></div>"
    if ms:
        sidebar += _nl_inline(f"Following {name or 'this player'}? Get the padel week in one email")
    sidebar += pu.share()

    # --- sobre (texto factual escrito pelo código) e ligações
    he = "she" if p.get("category") == "women" else "he"
    his = "her" if he == "she" else "his"
    bits = [f"{esc(name)} is a " + (f"{p['age']}-year-old " if p.get("age") else "") + "padel player"
            + (f" from {esc(country_name(nat))}" if nat else "")
            + (f", ranked <b>No. {rk}</b> in the {'women' if he == 'she' else 'men'}'s padel ranking" if rk else "")
            + (f" with {pts} points" if pts else "") + "."]
    if side:
        bits.append(f"{he.capitalize()} plays on the {'right' if p.get('side') == 'drive' else 'left'} side of the court.")
    cur = next((x for x in ph if x.get("status") == "current"), None)
    if cur:
        q = next((y for y in cur["players"] if str(y.get("id")) != str(pid)), None)
        if q:
            bits.append(f"{his.capitalize()} current partner is <a href=\"{ppath(q)}\">{esc(q.get('name'))}</a>.")
    if done:
        bits.append(f"In the Premier Padel and FIP matches we tracked, {he} is {w}-{len(done) - w}" +
                    (f", with {titles} title{'s' if titles != 1 else ''} from {finals} final{'s' if finals != 1 else ''}" if finals else "") + ".")
    for tid, run in runs:
        lab_, _, _ = _p_outcome(run)
        t = db.tour(tid) or {}
        if lab_ and t:
            what = {"Title": "won the title", "Final": "reached the final", "Semi-final": "reached the semi-finals",
                    "Quarter-final": "reached the quarter-finals"}.get(lab_, "played")
            bits.append(f"Most recently, at <a href=\"{tpath(t)}\">{esc(t.get('location') or t.get('name') or '')}</a>, {he} {what}.")
            break
    about = pu.h2("about", f"About {esc(name)}") + "<p>" + " ".join(bits) + "</p>"
    opp = {}
    for m, tm in done:
        ot = "team_2" if tm == "team_1" else "team_1"
        for q in team_players(m, ot):
            e_ = opp.setdefault(str(q.get("id")), [q, 0, 0])
            e_[1 if m["winner"] == tm else 2] += 1
    freq = sorted([v for v in opp.values() if v[1] + v[2] >= 2], key=lambda v: -(v[1] + v[2]))[:6]
    if freq:
        about += (pu.h2("", "Frequent opponents") + '<div class="pv-links">'
                  + "".join(f'<a href="{ppath(q)}">{esc(q.get("name"))} <b>{a}-{b}</b></a>' for q, a, b in freq) + "</div>")
    my_rk = rk or 500
    if nat:
        mates = [((db.rank_of.get(k) or {}).get("ranking") or 9999, q) for k, q in db.pinfo.items()
                 if k != str(pid) and q.get("nationality") == nat and q.get("category") == p.get("category") and (db.rank_of.get(k) or {}).get("ranking")]
        if mates:
            mates.sort(key=lambda x: (abs(x[0] - my_rk), x[0]))
            about += (pu.h2("", f"More players from {esc(country_name(nat))}") + '<div class="pv-links">'
                      + "".join(f'<a href="{ppath(q)}">{esc(q.get("name"))} <b>#{x}</b></a>' for x, q in sorted(mates[:6], key=lambda x: x[0]))
                      + '<a href="/padel/countries.html">All countries →</a></div>')
    about += '<p class="pv-src">Won-lost, titles and tournaments count the matches in our database (Premier Padel and FIP Platinum, Gold and Silver, last months).</p>'
    body = pu.page(top_left, top_right, pu.tabs([("overview", "Overview"), ("results", "Results"), ("stats", "Stats"), ("about", "About")]),
                   main, sidebar, about)
    # o resto (título, descrição, dados estruturados) é o mesmo da versão 1
    return _player_shell(db, pid, p, r, ms, body)


# ---------------------------------------------------------------- página do jogo, versão 2 (13/11/2026, igual ao ténis)
def _team_of(x, k):
    for tt in ("team_1", "team_2"):
        ps = team_players(x, tt)
        if len(ps) == 2 and pair_key(ps) == k:
            return tt
    return None


def page_match_v2(db, m):
    import player_ui as pu
    t = db.tour(m.get("tid")) or {}
    w = m.get("winner") if m.get("winner") in ("team_1", "team_2") else None
    A, Bt = team_players(m, "team_1"), team_players(m, "team_2")
    try:
        day = dt.date.fromisoformat((m.get("played_at") or "")[:10])
    except ValueError:
        day = None
    st = m.get("status")
    tn = t.get("location") or t.get("name") or ""
    pills = [(esc((m.get("round_name") or "").upper()), "", True), (esc(tn), tpath(t) if t else "", False),
             (esc(LEVEL_SHORT.get(t.get("level"), "")), "", False),
             (" · ".join(x for x in [day.strftime("%-d %b %Y") if day else "", CAT.get(m.get("category"), "")] if x), "", False)]
    if st == "live":
        pills.insert(0, ('<span class="pd-live">● LIVE</span>', "", False))
    elif not sets_of(m):
        pills.insert(1, (esc(m.get("schedule_label") or when_local(m) or "Scheduled"), "", False))
    sides, rows = [], []
    for team, ps in (("team_1", A), ("team_2", Bt)):
        won = (w == team) if w else None
        ranks = " · ".join(x for x in (rank_str(p.get("id"), db) for p in ps) if x)
        sides.append({"photos": [f"/padel/img/{p.get('id')}.jpg" for p in ps if has_photo(p.get("id"))],
                      "ini": "".join((disp(p).split()[-1] or "?")[0] for p in ps).upper(),
                      "name": "<br>".join(esc(disp(p)) for p in ps) or "TBD", "sub": ranks,
                      "href": pair_path(ps) if len(ps) == 2 else "", "won": won})
        sets = []
        for a, b in sets_of(m):
            mine, oth = (a, b) if team == "team_1" else (b, a)
            tb = re.search(r"\((\d+)\)", mine)
            sets.append((games(mine), games(mine) > games(oth), f"<sup>{tb.group(1)}</sup>" if tb else ""))
        rows.append((" / ".join(f'<a href="{ppath(p)}">{esc(disp(p))}</a>' for p in ps) or "TBD", ranks, sets, w == team))
    hero = pu.vs_hero(pills, sides, rows)
    vid, v = _match_video(db, m)
    elo = ""
    try:
        from padel import elo as _elo
        _c = _elo.chance(A, Bt)
        try:
            _recent = not m.get("played_at") or (dt.date.today() - dt.date.fromisoformat(m["played_at"][:10])).days <= 21
        except ValueError:
            _recent = False
        if _c is not None and _recent:
            _nm = lambda ps: " / ".join(esc(p.get("short_name") or p.get("name") or "") for p in ps)
            _pa = round(_c * 100)
            elo = (f'<div class="pd-elo"><div class="pd-elo-bar"><i style="width:{_pa}%"></i></div>'
                   f'<p class="pd-note"><b>{_nm(A)} {_pa}%</b> · <b>{_nm(Bt)} {100 - _pa}%</b> · '
                   f'chance to win, our estimate from the players\' current Elo ratings (Padel API)</p></div>')
    except Exception as e:
        print("Elo:", type(e).__name__, e)

    # --- história (factos)
    nm = lambda ps: " / ".join(f'<a href="{ppath(p)}">{esc(p.get("name"))}</a>' for p in ps)
    story = ""
    ms = [x for x in db.by_t.get(str(m.get("tid")), []) if (x.get("draw") or "main") == (m.get("draw") or "main") and x.get("category") == m.get("category")]
    if w:
        L = "team_2" if w == "team_1" else "team_1"
        WP, LP = team_players(m, w), team_players(m, L)
        sc = " ".join(f"{games(a if w == 'team_1' else b)}-{games(b if w == 'team_1' else a)}" for a, b in sets_of(m))
        out = [f"{nm(WP)} beat {nm(LP)} {sc}" + (f" in the {esc((m.get('round_name') or '').lower())}" if m.get("round_name") else "")
               + (f" at {esc(t.get('name') or tn)}" if t else "") + (f" on {day.strftime('%-d %B %Y')}" if day else "") + "."]
        ss = sets_of(m)
        if len(ss) >= 2:
            a0, b0 = ss[0]
            first_lost = (games(a0) < games(b0)) if w == "team_1" else (games(b0) < games(a0))
            out.append("They came back from a set down." if first_lost else ("It was a straight-sets win." if len(ss) == 2 else ""))
        ntb = sum(1 for a, b in ss if {games(a), games(b)} == {6, 7})
        if ntb:
            out.append(f"The match had {ntb} tie-break{'s' if ntb > 1 else ''}.")
        if len(WP) == 2:
            k = pair_key(WP)
            before = [x for x in ms if (x.get("round") or 0) > (m.get("round") or 0) and _team_of(x, k) and x.get("winner") == _team_of(x, k)]
            if m.get("round") == 1:
                out.append(f"They won the title with {len(before) + 1} wins in a row.")
            elif before:
                out.append(f"It was their {_ordn(len(before) + 1)} win of the tournament.")
        story = pu.h2("", "The story") + f'<div class="mv-story"><p>{" ".join(x for x in out if x)}</p></div>'

    # --- principal
    main = vid + elo
    ss = sets_of(m)
    if w and ss:
        L = "team_2" if w == "team_1" else "team_1"
        main += pu.set_bars([(games(a if w == "team_1" else b), games(b if w == "team_1" else a)) for a, b in ss],
                            (" / ".join(disp(p).split()[-1] for p in team_players(m, w)), " / ".join(disp(p).split()[-1] for p in team_players(m, L))))
    roads = ""
    for team, ps in (("team_1", A), ("team_2", Bt)):
        if len(ps) != 2:
            continue
        k = pair_key(ps)
        prev = sorted([x for x in ms if (x.get("round") or 0) > (m.get("round") or 0) and _team_of(x, k)], key=lambda x: (x.get("round") or 0))
        if prev:
            nwin = sum(1 for x in prev if x.get("winner") == _team_of(x, k))
            roads += pu.event(f'<a href="{pair_path(ps)}">{" / ".join(esc(disp(p)) for p in ps)}</a>',
                              f"Road to the {(m.get('round_name') or 'match').lower()} · {nwin} win{'s' if nwin != 1 else ''}", "",
                              [_p_row(db, x, _team_of(x, k)) for x in prev])
    if roads:
        main += pu.h2("", "Road to this match") + f'<div class="mv-roads">{roads}</div>'
    if len(A) == 2 and len(Bt) == 2:
        ka, kb = pair_key(A), pair_key(Bt)
        h2h = [x for x, _ in db.by_pair.get(ka, []) if x.get("id") != m.get("id") and _team_of(x, kb)]
        h2h = sorted({x["id"]: x for x in h2h}.values(), key=lambda x: x.get("played_at") or "", reverse=True)
        if h2h:
            wa = sum(1 for x in h2h if x.get("winner") == _team_of(x, ka))
            wb = sum(1 for x in h2h if x.get("winner") == _team_of(x, kb))
            main += pu.h2("", "Head-to-head", f"<small>{wa}-{wb} before this match</small>")
            main += pu.event(" / ".join(esc(disp(p)) for p in A) + " vs " + " / ".join(esc(disp(p)) for p in Bt), "", "",
                             [_p_row(db, x, _team_of(x, ka), rd=(x.get("played_at") or "")[:4]) for x in h2h[:6]])
    if w and len(team_players(m, w)) == 2:
        kw = pair_key(team_players(m, w))
        nxt = [x for x in ms if (x.get("round") or 0) < (m.get("round") or 0) and _team_of(x, kw)]
        if nxt:
            nx = max(nxt, key=lambda x: x.get("round") or 0)
            main += pu.h2("", "Next match") + pu.event(" / ".join(esc(disp(p)) for p in team_players(m, w)), esc(nx.get("round_name") or ""), "",
                                                       [_p_row(db, nx, _team_of(nx, kw))])
    if t:
        main += f'<div class="pv-links"><a href="{tpath(t)}">All results from {esc(t.get("name") or tn)} →</a></div>'

    # --- lateral
    side = ""
    if ss:
        ga = [games(a) for a, _ in ss]
        gb = [games(b) for _, b in ss]
        sa = sum(1 for x, y in zip(ga, gb) if x > y)
        rows_ = [("Sets won", sa, len(ss) - sa, str(sa), str(len(ss) - sa), "sets"), ("Games won", sum(ga), sum(gb), str(sum(ga)), str(sum(gb)), "games")]
        tba = sum(1 for x, y in zip(ga, gb) if x == 7 and y == 6)
        tbb = sum(1 for x, y in zip(ga, gb) if y == 7 and x == 6)
        if tba + tbb:
            rows_.append(("Tie-breaks won", tba, tbb, str(tba), str(tbb), "tbs"))
        lab = lambda ps: " / ".join(esc(disp(p).split()[-1]) for p in ps)
        side += site_ui.sec("Match stats") + site_ui.compare((lab(A), lab(Bt)), rows_)
        tape = []
        for f_, lab_ in ((lambda p: rank_str(p.get("id"), db) or "–", "Ranking"),):
            tape.append((lab_, None, None, " · ".join(f_(p) for p in A), " · ".join(f_(p) for p in Bt), "rk"))
        side += site_ui.sec("Tale of the tape") + site_ui.compare((lab(A), lab(Bt)), tape)
    side += _nl_inline("Enjoyed this match? Get the padel week in one email")
    body = pu.match_page(hero, story, main, side)
    return _match_shell(db, m, t, A, Bt, w, v, body)


def _ordn(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ---------------------------------------------------------------- página inicial, versão 2 (13/11/2026, igual ao ténis)
def page_index_v2(db):
    import home_ui
    import player_ui as pu
    today = dt.date.today()
    tstr = today.isoformat()
    live = sorted([t for t in db.tours.values() if t.get("status") == "live"], key=lambda t: LEVEL_ORDER.get(t.get("level"), 9))
    names = lambda ps: " / ".join(disp(p) for p in ps)
    ini = lambda ps: "".join((disp(p).split()[-1] or "?")[0] for p in ps).upper()
    pic = lambda ps: next((f"/padel/img/{p.get('id')}.jpg" for p in ps if has_photo(p.get("id"))), "")

    # --- finais recentes (campeões) -> acontecimento do dia e cartões
    finals = []
    for t in db.tours.values():
        for m in db.by_t.get(str(t.get("id")), []):
            if m.get("round") == 1 and (m.get("draw") or "main") == "main" and m.get("winner") in ("team_1", "team_2"):
                try:
                    d = dt.date.fromisoformat((m.get("played_at") or t.get("end_date") or "")[:10])
                except ValueError:
                    continue
                if (today - d).days <= 14:
                    finals.append((t, m, d))
    finals.sort(key=lambda x: (LEVEL_ORDER.get(x[0].get("level"), 9), -x[2].toordinal(), x[1].get("category") != "men"))

    def sc(m, w):
        return " ".join(f"{games(a if w == 'team_1' else b)}-{games(b if w == 'team_1' else a)}" for a, b in sets_of(m))

    lead_c = sorted(finals, key=lambda x: (-(30 - 6 * LEVEL_ORDER.get(x[0].get("level"), 9) - 4 * (today - x[2]).days + (15 if pic(team_players(x[1], x[1]["winner"])) else 0))))
    lead = ""
    more_rows = ""
    if lead_c:
        t, m, d = lead_c[0]
        w = m["winner"]
        WP, LP = team_players(m, w), team_players(m, "team_2" if w == "team_1" else "team_1")
        c = photo_credit(next((p.get("id") for p in WP if has_photo(p.get("id"))), "")) or {}
        lead = home_ui.lead(mpath(m), pic(WP), ini(WP), [LEVEL_SHORT.get(t.get("level"), "") or "Final", f"{CAT.get(m.get('category'), '')} champions"],
                            f"{names(WP)} win {t.get('location') or t.get('name')}",
                            f"Beat {names(LP)} {sc(m, w)} in the final · {d.strftime('%-d %b')}", c.get("credit") or "")
        for t2, m2, d2 in lead_c[1:4]:
            w2 = m2["winner"]
            W2 = team_players(m2, w2)
            av = "".join(avatar(p, "av") for p in W2[:1])
            more_rows += (f'<a href="{mpath(m2)}">{av}<span><b>{esc(names(W2))} win {esc(t2.get("location") or t2.get("name") or "")}</b>'
                          f'<small>{esc(sc(m2, w2))} · {esc(LEVEL_SHORT.get(t2.get("level"), ""))} · {esc(CAT.get(m2.get("category"), ""))}</small></span></a>')
    week = [m for m in db.matches if (m.get("played_at") or "") >= (today - dt.timedelta(days=6)).isoformat() and m.get("winner") in ("team_1", "team_2")]
    side = (home_ui.search(placeholder="Search a padel player or tournament", pref="/padel/")
            + home_ui.intro("Every player.", "Every draw.", "Premier Padel and the CUPRA FIP Tour: results, draws and rankings.",
                            [("Follow @beyond100.padel", "https://www.instagram.com/beyond100.padel/", True), ("Rankings", "/padel/rankings.html", False)])
            + (f'<div class="hm-more"><div class="pv-lab">More champions</div>{more_rows}</div>' if more_rows else "")
            + home_ui.nums([(len(week), "matches in 7 days", "/padel/results.html"), (len(live), "tournaments live", "/padel/tournaments.html"),
                            (f"{len(db.pinfo):,}".replace(",", " "), "players", "/padel/players.html")]))
    if not lead:
        lead, side = side, ""

    # --- ao vivo / hoje (igual à versão anterior)
    rest = ""
    tday = [m for t in live for m in db.by_t.get(str(t["id"]), []) if m.get("played_at") == tstr and (m.get("draw") or "main") == "main"
            and team_players(m, "team_1") and team_players(m, "team_2") and m.get("winner") not in ("team_1", "team_2")]
    on = [m for m in tday if sets_of(m) or m.get("status") == "live"]
    nx = sorted([m for m in tday if not (sets_of(m) or m.get("status") == "live")], key=lambda m: (m.get("scheduled_at") or "9", -(m.get("round") or 0)))
    on.sort(key=lambda m: (LEVEL_ORDER.get((db.tour(m.get("tid")) or {}).get("level"), 9), m.get("round") or 99))
    tiles = (on + nx)[:4]
    if tiles:
        h = ('<span><span class="dot" style="display:inline-block;margin-right:8px"></span>Playing now</span>' if on
             else f'<span>Today{(" · first match at " + site_ui.ltime(nx[0].get("scheduled_at"), when_local(nx[0]) + " local time")) if nx and nx[0].get("scheduled_at") else ""}</span>')
        rest += f'<h2 class="sec">{h}<a href="/padel/order-of-play.html">Order of play</a></h2><div class="lvg">' + "".join(live_tile(m, db) for m in tiles) + "</div>"

    # --- campeões com foto (um cartão por categoria e torneio)
    cards = ""
    for t, m, d in finals[:8]:
        w = m["winner"]
        WP, LP = team_players(m, w), team_players(m, "team_2" if w == "team_1" else "team_1")
        cards += home_ui.champ(mpath(m), pic(WP), ini(WP), LEVEL_SHORT.get(t.get("level"), ""), CAT.get(m.get("category"), "Champions"),
                               names(WP), t.get("location") or t.get("name") or "", f"d. {names(LP)} {sc(m, w)} · {d.strftime('%d/%m')}")
    if cards:
        rest += site_ui.sec("Latest champions", "/padel/tournaments.html", "All tournaments") + f'<div class="hm-row">{cards}</div>'
    hl = highlight_cards(db, 4)
    if hl:
        rest += site_ui.sec("▶ Latest highlights", "/padel/highlights.html", "All highlights") + '<div class="pd-hls row">' + "".join(hl_card(db, m, h) for m, h in hl) + "</div>"

    # --- últimos resultados por torneio
    done = sorted([m for m in db.matches if m.get("winner") in ("team_1", "team_2") and team_players(m, "team_1") and (m.get("draw") or "main") == "main"],
                  key=lambda m: (m.get("played_at") or "", -(m.get("round") or 99)), reverse=True)
    groups, order = {}, []
    for m in done:
        k = (str(m.get("tid")), m.get("category"))
        if k not in groups:
            if len(order) >= 4:
                continue
            groups[k] = []
            order.append(k)
        if len(groups[k]) < 4:
            groups[k].append(m)
    evs = ""
    for k in order:
        t = db.tour(k[0]) or {}
        rows = []
        for m in groups[k]:
            w = m["winner"]
            WP, LP = team_players(m, w), team_players(m, "team_2" if w == "team_1" else "team_1")
            rows.append((RSHORT.get(m.get("round"), ""), " / ".join(f'<a href="{ppath(p)}">{esc(disp(p))}</a>' for p in WP),
                         "d. " + names(LP), _p_score(m, w), mpath(m), True))
        evs += pu.event(f'<a href="{tpath(t)}">{esc(t.get("location") or t.get("name") or "")}</a>',
                        " · ".join(x for x in [LEVEL_SHORT.get(t.get("level"), ""), CAT.get(k[1], ""), (groups[k][0].get("played_at") or "")[:10]] if x), "", rows)
    if evs:
        rest += site_ui.sec("Latest results", "/padel/results.html", "All results") + f'<div class="hm-res">{evs}</div>'
    try:
        rest += spotlight_block(db)
    except Exception as e:
        print("Padel: spotlight falhou", type(e).__name__, e)
    nxt = sorted([t for t in db.tours.values() if t.get("status") == "pending" and (t.get("start_date") or "") >= tstr],
                 key=lambda t: (t.get("start_date") or "", LEVEL_ORDER.get(t.get("level"), 9)))[:4]
    if nxt:
        rest += site_ui.sec("Coming up", "/padel/next-week.html", "Next week") + '<div class="pd-list">' + "".join(
            f'<a href="{tpath(t)}"><span class="pd-tag g">{esc(LEVEL_SHORT.get(t.get("level"), ""))}</span><b>{esc(t.get("location") or t.get("name"))}</b>'
            f'<span class="pd-note">{esc(date_range(t))}</span></a>' for t in nxt) + "</div>"
    tabs, panes = "", ""
    for i, cat in enumerate(("men", "women")):
        rows = ((db.ranks.get(cat) or {}).get("rows") or [])[:5]
        if not rows:
            continue
        tabs += f'<button class="{"on" if i == 0 else ""}" data-c="{cat}">{CAT[cat]}</button>'
        panes += (f'<div class="pd-rk5" data-c="{cat}"{"" if i == 0 else " hidden"}>' + "".join(
            f'<a href="{ppath({"id": r.get("id"), "name": r.get("name")})}"><span class="n">{r.get("ranking")}</span>{avatar(r)}{flag(r.get("nationality"), 11)}'
            f'<span class="nm">{esc(r.get("name"))}</span><span class="pd-note">{(r.get("points") or 0):,}</span></a>'.replace(",", " ") for r in rows)
                  + f'<a class="pd-more" href="/padel/rankings-{cat}.html">Full ranking →</a></div>')
    if panes:
        rest += (site_ui.sec("Rankings", "/padel/rankings.html", "All rankings") + f'<div class="pd-seg">{tabs}</div>{panes}'
                 '<script>document.querySelector(".pd-seg").onclick=function(e){var b=e.target.closest("button");if(!b)return;'
                 '[].forEach.call(document.querySelectorAll(".pd-seg button"),function(x){x.className=x===b?"on":""});'
                 '[].forEach.call(document.querySelectorAll(".pd-rk5"),function(p){p.hidden=p.dataset.c!==b.dataset.c})}</script>')
    links = [("results", "Results", "Every score, newest first"), ("order-of-play", "Order of play", "Today by court"),
             ("power", "Power Ranking", "Best form, last 30 days"), ("race", "Race to the Finals", "Who makes Barcelona")]
    rest += '<div class="pd-quick ui-quick">' + "".join(f'<a href="/padel/{k}.html"><b>{v}</b><span>{d}</span></a>' for k, v, d in links) + "</div>"
    rest += _nl_inline("Get the padel week in one email")
    body = f"<style>{pu.CSS}</style>" + home_ui.page(lead, side, rest)
    return shell("Beyond Padel · Premier Padel and FIP Tour results, draws and rankings", body, "/padel/index.html", tab="index")


# no fim do ficheiro: corrido como script (python padel/site.py), todas as funções têm de estar definidas antes (13/11/2026)
if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "site")
