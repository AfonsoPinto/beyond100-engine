"""Versões em espanhol das páginas principais do padel (/padel/es/), 7/11/2026.

A maior parte das pesquisas de padel é em espanhol. Só as páginas principais são traduzidas (início, resultados e rankings);
as páginas de jogadores, pares, torneios e jogos ficam em inglês (nomes e resultados não mudam), como no ténis.

Funciona por cima do HTML já feito em inglês: troca só o texto visível (nunca nomes de jogadores, que não estão na lista),
o título, a descrição, o canonical e as ligações entre estas páginas, e liga as duas versões com hreflang.
"""
import os
import re

SITE_BASE = "https://beyond100tennis.com"

PAGES = {   # inglês -> espanhol
    "/padel/index.html": "/padel/es/index.html",
    "/padel/results.html": "/padel/es/results.html",
    "/padel/rankings-men.html": "/padel/es/rankings-men.html",
    "/padel/rankings-women.html": "/padel/es/rankings-women.html",
}
LINKS = dict(PAGES, **{"/padel/rankings.html": "/padel/es/rankings-men.html", "/padel/": "/padel/es/"})

META = {
    "/padel/index.html": ("Beyond Padel · Resultados, cuadros y ranking de Premier Padel y FIP Tour",
                          "Resultados, cuadros, orden de juego y ranking de Premier Padel y del CUPRA FIP Tour: cada jugador, cada cuadro."),
    "/padel/results.html": ("Resultados de pádel: Premier Padel y FIP Tour · Beyond Padel",
                            "Todos los resultados de Premier Padel y del CUPRA FIP Tour, los más recientes primero, con el marcador de cada set."),
    "/padel/rankings-men.html": ("Ranking de pádel masculino · Beyond Padel",
                                 "Ranking masculino de pádel actualizado: puesto, puntos y puestos ganados o perdidos esta semana."),
    "/padel/rankings-women.html": ("Ranking de pádel femenino · Beyond Padel",
                                   "Ranking femenino de pádel actualizado: puesto, puntos y puestos ganados o perdidos esta semana."),
}

# textos exatos (o nó de texto inteiro, sem espaços à volta)
EXACT = {
    "Home": "Inicio", "Results": "Resultados", "Tournaments": "Torneos", "Rankings": "Ranking", "Stats": "Estadísticas",
    "Today": "Hoy", "Videos": "Vídeos", "Highlights": "Resúmenes", "Live": "Directo", "● Live": "● Directo",
    "Men": "Masculino", "Women": "Femenino", "Later today": "Más tarde", "Order of play": "Orden de juego",
    "Latest highlights": "Últimos resúmenes", "All highlights": "Todos los resúmenes", "Latest champions": "Últimos campeones",
    "All tournaments": "Todos los torneos", "Coming up": "Próximos torneos", "Next week": "Próxima semana",
    "Every score, newest first": "Todos los resultados, los más recientes primero", "Today by court": "Hoy, pista por pista",
    "Titles, streaks, upsets": "Títulos, rachas y sorpresas", "Players": "Jugadores", "Full ranking →": "Ranking completo →",
    "EVERY PLAYER · EVERY DRAW": "CADA JUGADOR · CADA CUADRO", "Every player.": "Cada jugador.", "Every draw.": "Cada cuadro.",
    "Men's ranking": "Ranking masculino", "Women's ranking": "Ranking femenino", "By country ›": "Por país ›",
    "All countries": "Todos los países", "Player": "Jugador", "Points": "Puntos", "Match ›": "Partido ›", "▶ Video ›": "▶ Vídeo ›",
    "▶ Highlights ›": "▶ Resumen ›", "RETIRED": "ABANDONO", "Data:": "Datos:", "Photo credits": "Créditos de las fotos",
    "About": "Sobre nosotros", "Beyond100 Tennis": "Beyond100 Tenis", "Tennis": "Tenis", "Padel": "Pádel", "Champion": "Campeones",
    "Champions": "Campeones", "Final": "Final", "Finals": "Final", "Winner": "Ganadores", "Runners-up": "Finalistas",
    "Premier Padel and the CUPRA FIP Tour: results, draws and rankings.": "Premier Padel y CUPRA FIP Tour: resultados, cuadros y ranking.",
    "Premier Padel and the FIP Tour, newest first. Final and semi-finals first; open a tournament to see every match.":
        "Premier Padel y FIP Tour, los más recientes primero. Primero finales y semifinales; abre un torneo para ver todos los partidos.",
    "Order of play today ›": "Orden de juego de hoy ›", "All tournaments ›": "Todos los torneos ›", "All": "Todos",
    "All events": "Todos los torneos", "Show older results": "Ver resultados anteriores",
    "· Premier Padel and CUPRA FIP Tour (Platinum, Gold, Silver). Scores are for information only and may contain delays or errors. ·":
        "· Premier Padel y CUPRA FIP Tour (Platinum, Gold, Silver). Los resultados son solo informativos y pueden tener retrasos o errores. ·",
}
# palavras e expressões dentro de um texto maior ("Malé · Quarter · Men"); a ordem conta (as mais compridas primeiro)
PARTS = [
    ("Round of 128", "Ronda de 128"), ("Round of 64", "Ronda de 64"), ("Round of 32", "Dieciseisavos"), ("Round of 16", "Octavos"),
    ("Quarterfinals", "Cuartos"), ("Quarter-finals", "Cuartos"), ("Quarter", "Cuartos"), ("Semifinals", "Semifinales"), ("Semi-finals", "Semifinales"),
    ("Finals", "Final"), ("Qualifying", "Previa"), ("Men", "Masculino"), ("Women", "Femenino"),
    ("Today · first match at", "Hoy · primer partido a las"), ("local time", "hora local"),
    ("Official ranking of", "Ranking oficial del"), ("places moved this week.", "puestos ganados o perdidos esta semana."),
    ("Search", "Busca entre"), ("players", "jugadores"), ("matches", "partidos"), ("match", "partido"),
]
MONTHS = {"Jan": "ene", "Feb": "feb", "Mar": "mar", "Apr": "abr", "May": "may", "Jun": "jun", "Jul": "jul", "Aug": "ago",
          "Sep": "sept", "Oct": "oct", "Nov": "nov", "Dec": "dic"}
_PARTS_RE = [(re.compile(r"(?<![\w'])" + re.escape(a) + r"(?![\w'])"), b) for a, b in PARTS]
_MON_RE = re.compile(r"(?<=\d )(" + "|".join(MONTHS) + r")\b|\b(" + "|".join(MONTHS) + r")(?= \d{4})")


def _text(t):
    s = t.strip()
    if not s or not re.search(r"[A-Za-z]{2}", s):
        return t
    lead, trail = t[: len(t) - len(t.lstrip())], t[len(t.rstrip()):]
    if s in EXACT:
        return lead + EXACT[s] + trail
    # só mexe em textos que tenham pelo menos uma das expressões conhecidas (nomes de jogadores ficam como estão)
    s = re.sub(r"^Show all (\d+)$", r"Ver los \1", s)
    out = re.sub(r"^All ([\d\s,.+\u00a0\u202f]+) ", r"Los \1 ", s)          # "All 3 matches" -> "Los 3 partidos"
    for rx, b in _PARTS_RE:
        out = rx.sub(b, out)
    out = _MON_RE.sub(lambda m: MONTHS[m.group(1) or m.group(2)], out)
    return lead + out + trail


def _alts(en_path):
    es_path = PAGES[en_path]
    c = lambda u: SITE_BASE + (u[: -len("index.html")] if u.endswith("index.html") else u[:-5])
    return (f'<link rel="alternate" hreflang="en" href="{c(en_path)}"><link rel="alternate" hreflang="es" href="{c(es_path)}">'
            f'<link rel="alternate" hreflang="x-default" href="{c(en_path)}">')


def translate(page, en_path):
    """HTML da página inglesa -> HTML da versão espanhola."""
    es_path = PAGES[en_path]
    c = lambda u: SITE_BASE + (u[: -len("index.html")] if u.endswith("index.html") else u[:-5])
    title, desc = META[en_path]
    s = page.replace('<html lang="en">', '<html lang="es">', 1)
    s = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", s, count=1, flags=re.S)
    s = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*', lambda m: m.group(1) + desc, s)
    s = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + title, s)
    s = s.replace(f'<link rel="canonical" href="{c(en_path)}">', f'<link rel="canonical" href="{c(es_path)}">', 1)
    s = s.replace(f'<meta property="og:url" content="{c(en_path)}">', f'<meta property="og:url" content="{c(es_path)}">', 1)
    s = s.replace("</head>", _alts(en_path) + "</head>", 1)
    for a, b in LINKS.items():                        # ligações entre as páginas traduzidas ficam em espanhol
        s = s.replace(f'href="{a}"', f'href="{b}"')
    # texto visível: fora de <script>, <style> e dos atributos
    parts = re.split(r"(<script\b.*?</script>|<style\b.*?</style>|<[^>]+>)", s, flags=re.S)
    return "".join(p if (p.startswith("<") or not p) else _text(p) for p in parts)


def make(out):
    """Escreve as versões espanholas a partir das inglesas já feitas e junta o hreflang às inglesas. Devolve os caminhos novos."""
    done = []
    for en_path, es_path in PAGES.items():
        fp = os.path.join(out, en_path.lstrip("/"))
        if not os.path.exists(fp):
            continue
        with open(fp, encoding="utf-8") as f:
            page = f.read()
        c = lambda u: u[: -len("index.html")] if u.endswith("index.html") else u[:-5]
        es = translate(page, en_path).replace("</footer>", f' · <a href="{c(en_path)}" hreflang="en">English</a></footer>', 1)
        if "hreflang=" not in page:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(page.replace("</head>", _alts(en_path) + "</head>", 1)
                        .replace("</footer>", f' · <a href="{c(es_path)}" hreflang="es">Español</a></footer>', 1))
        ep = os.path.join(out, es_path.lstrip("/"))
        os.makedirs(os.path.dirname(ep), exist_ok=True)
        with open(ep, "w", encoding="utf-8") as f:
            f.write(es)
        done.append(ep)
    return done
