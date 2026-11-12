"""Versões em espanhol das páginas principais do padel (/padel/es/), 7/11/2026.

A maior parte das pesquisas de padel é em espanhol. Só as páginas principais são traduzidas (início, resultados e rankings);
as páginas de jogadores, pares, torneios e jogos ficam em inglês (nomes e resultados não mudam), como no ténis.

Funciona por cima do HTML já feito em inglês: troca só o texto visível (nunca nomes de jogadores, que não estão na lista),
o título, a descrição, o canonical e as ligações entre estas páginas, e liga as duas versões com hreflang.
"""
import os
import re

SITE_BASE = "https://beyond100tennis.com"

PAGES = {   # inglês -> espanhol (12/11/2026: também italiano e francês, em LANGS)
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


# ------------------------------------------------------------------ 12/11/2026: italiano e francês (mesmo mecanismo do espanhol)
EN_PAGES = list(PAGES)
LANGS = {
    "es": {"name": "Español", "meta": META, "exact": EXACT, "parts": PARTS, "months": MONTHS},
    "it": {"name": "Italiano", "months": {"Jan": "gen", "Feb": "feb", "Mar": "mar", "Apr": "apr", "May": "mag", "Jun": "giu", "Jul": "lug", "Aug": "ago",
                                          "Sep": "set", "Oct": "ott", "Nov": "nov", "Dec": "dic"},
           "meta": {"/padel/index.html": ("Beyond Padel · Risultati, tabelloni e ranking di Premier Padel e FIP Tour",
                                          "Risultati, tabelloni, ordine di gioco e ranking di Premier Padel e del CUPRA FIP Tour: ogni giocatore, ogni tabellone."),
                    "/padel/results.html": ("Risultati padel: Premier Padel e FIP Tour · Beyond Padel",
                                            "Tutti i risultati di Premier Padel e del CUPRA FIP Tour, dai più recenti, con il punteggio di ogni set."),
                    "/padel/rankings-men.html": ("Ranking padel maschile · Beyond Padel", "Ranking maschile di padel aggiornato: posizione, punti e posizioni guadagnate o perse questa settimana."),
                    "/padel/rankings-women.html": ("Ranking padel femminile · Beyond Padel", "Ranking femminile di padel aggiornato: posizione, punti e posizioni guadagnate o perse questa settimana.")},
           "exact": {"Home": "Home", "Results": "Risultati", "Tournaments": "Tornei", "Rankings": "Ranking", "Stats": "Statistiche", "Today": "Oggi",
                     "Videos": "Video", "Highlights": "Highlights", "Live": "Live", "● Live": "● Live", "Men": "Maschile", "Women": "Femminile",
                     "Later today": "Più tardi", "Order of play": "Ordine di gioco", "Latest highlights": "Ultimi highlights", "All highlights": "Tutti gli highlights",
                     "Latest champions": "Ultimi campioni", "All tournaments": "Tutti i tornei", "Coming up": "Prossimi tornei", "Next week": "Prossima settimana",
                     "Every score, newest first": "Tutti i risultati, dai più recenti", "Today by court": "Oggi, campo per campo",
                     "Titles, streaks, upsets": "Titoli, serie e sorprese", "Players": "Giocatori", "Full ranking →": "Ranking completo →",
                     "EVERY PLAYER · EVERY DRAW": "OGNI GIOCATORE · OGNI TABELLONE", "Every player.": "Ogni giocatore.", "Every draw.": "Ogni tabellone.",
                     "Men's ranking": "Ranking maschile", "Women's ranking": "Ranking femminile", "By country ›": "Per paese ›", "All countries": "Tutti i paesi",
                     "Player": "Giocatore", "Points": "Punti", "Match ›": "Partita ›", "▶ Video ›": "▶ Video ›", "▶ Highlights ›": "▶ Highlights ›",
                     "RETIRED": "RITIRO", "Data:": "Dati:", "Photo credits": "Crediti foto", "About": "Chi siamo", "Beyond100 Tennis": "Beyond100 Tennis",
                     "Tennis": "Tennis", "Padel": "Padel", "Champion": "Campioni", "Champions": "Campioni", "Final": "Finale", "Finals": "Finale",
                     "Winner": "Vincitori", "Runners-up": "Finalisti", "Playing now": "In campo ora", "Players in the spotlight": "Giocatori in evidenza",
                     "Premier Padel and the CUPRA FIP Tour: results, draws and rankings.": "Premier Padel e CUPRA FIP Tour: risultati, tabelloni e ranking.",
                     "Order of play today ›": "Ordine di gioco di oggi ›", "All tournaments ›": "Tutti i tornei ›", "All": "Tutti", "All events": "Tutti i tornei",
                     "Show older results": "Mostra risultati precedenti", "All players": "Tutti i giocatori", "Power Ranking": "Power Ranking",
                     "Race to the Finals": "Race to the Finals"},
           "parts": [("Round of 128", "Primo turno"), ("Round of 64", "Trentaduesimi"), ("Round of 32", "Sedicesimi"), ("Round of 16", "Ottavi"),
                     ("Quarterfinals", "Quarti"), ("Quarter-finals", "Quarti"), ("Quarter", "Quarti"), ("Semifinals", "Semifinali"), ("Semi-finals", "Semifinali"),
                     ("Finals", "Finale"), ("Qualifying", "Qualificazioni"), ("Men", "Maschile"), ("Women", "Femminile"),
                     ("Today · first match at", "Oggi · prima partita alle"), ("local time", "ora locale"), ("Official ranking of", "Ranking ufficiale del"),
                     ("places moved this week.", "posizioni guadagnate o perse questa settimana."), ("Search", "Cerca tra"), ("players", "giocatori"),
                     ("matches", "partite"), ("match", "partita")]},
    "fr": {"name": "Français", "months": {"Jan": "janv.", "Feb": "févr.", "Mar": "mars", "Apr": "avr.", "May": "mai", "Jun": "juin", "Jul": "juil.", "Aug": "août",
                                          "Sep": "sept.", "Oct": "oct.", "Nov": "nov.", "Dec": "déc."},
           "meta": {"/padel/index.html": ("Beyond Padel · Résultats, tableaux et classement Premier Padel et FIP Tour",
                                          "Résultats, tableaux, programme et classement de Premier Padel et du CUPRA FIP Tour : chaque joueur, chaque tableau."),
                    "/padel/results.html": ("Résultats padel : Premier Padel et FIP Tour · Beyond Padel",
                                            "Tous les résultats de Premier Padel et du CUPRA FIP Tour, les plus récents d'abord, avec le score de chaque set."),
                    "/padel/rankings-men.html": ("Classement padel hommes · Beyond Padel", "Classement padel masculin à jour : place, points et places gagnées ou perdues cette semaine."),
                    "/padel/rankings-women.html": ("Classement padel femmes · Beyond Padel", "Classement padel féminin à jour : place, points et places gagnées ou perdues cette semaine.")},
           "exact": {"Home": "Accueil", "Results": "Résultats", "Tournaments": "Tournois", "Rankings": "Classement", "Stats": "Stats", "Today": "Aujourd'hui",
                     "Videos": "Vidéos", "Highlights": "Résumés", "Live": "Direct", "● Live": "● Direct", "Men": "Hommes", "Women": "Femmes",
                     "Later today": "Plus tard", "Order of play": "Programme", "Latest highlights": "Derniers résumés", "All highlights": "Tous les résumés",
                     "Latest champions": "Derniers vainqueurs", "All tournaments": "Tous les tournois", "Coming up": "À venir", "Next week": "Semaine prochaine",
                     "Every score, newest first": "Tous les résultats, les plus récents d'abord", "Today by court": "Aujourd'hui, court par court",
                     "Titles, streaks, upsets": "Titres, séries et surprises", "Players": "Joueurs", "Full ranking →": "Classement complet →",
                     "EVERY PLAYER · EVERY DRAW": "CHAQUE JOUEUR · CHAQUE TABLEAU", "Every player.": "Chaque joueur.", "Every draw.": "Chaque tableau.",
                     "Men's ranking": "Classement hommes", "Women's ranking": "Classement femmes", "By country ›": "Par pays ›", "All countries": "Tous les pays",
                     "Player": "Joueur", "Points": "Points", "Match ›": "Match ›", "▶ Video ›": "▶ Vidéo ›", "▶ Highlights ›": "▶ Résumé ›",
                     "RETIRED": "ABANDON", "Data:": "Données :", "Photo credits": "Crédits photo", "About": "À propos", "Beyond100 Tennis": "Beyond100 Tennis",
                     "Tennis": "Tennis", "Padel": "Padel", "Champion": "Vainqueurs", "Champions": "Vainqueurs", "Final": "Finale", "Finals": "Finale",
                     "Winner": "Vainqueurs", "Runners-up": "Finalistes", "Playing now": "En direct", "Players in the spotlight": "Joueurs à la une",
                     "Premier Padel and the CUPRA FIP Tour: results, draws and rankings.": "Premier Padel et CUPRA FIP Tour : résultats, tableaux et classement.",
                     "Order of play today ›": "Programme du jour ›", "All tournaments ›": "Tous les tournois ›", "All": "Tous", "All events": "Tous les tournois",
                     "Show older results": "Voir les résultats précédents", "All players": "Tous les joueurs", "Power Ranking": "Power Ranking",
                     "Race to the Finals": "Race to the Finals"},
           "parts": [("Round of 128", "1er tour"), ("Round of 64", "Trente-deuxièmes de finale"), ("Round of 32", "Seizièmes de finale"), ("Round of 16", "Huitièmes"),
                     ("Quarterfinals", "Quarts"), ("Quarter-finals", "Quarts"), ("Quarter", "Quarts"), ("Semifinals", "Demi-finales"), ("Semi-finals", "Demi-finales"),
                     ("Finals", "Finale"), ("Qualifying", "Qualifications"), ("Men", "Hommes"), ("Women", "Femmes"),
                     ("Today · first match at", "Aujourd'hui · premier match à"), ("local time", "heure locale"), ("Official ranking of", "Classement officiel du"),
                     ("places moved this week.", "places gagnées ou perdues cette semaine."), ("Search", "Rechercher parmi"), ("players", "joueurs"),
                     ("matches", "matchs"), ("match", "match")]},
}
LANGS["it"]["parts"] = sorted(LANGS["it"]["parts"], key=lambda x: -len(x[0]))
LANGS["fr"]["parts"] = sorted(LANGS["fr"]["parts"], key=lambda x: -len(x[0]))


def lpath(en_path, lang):
    return en_path.replace("/padel/", f"/padel/{lang}/", 1)


def _alts_all(en_path):
    c = lambda u: SITE_BASE + (u[: -len("index.html")] if u.endswith("index.html") else u[:-5])
    return (f'<link rel="alternate" hreflang="en" href="{c(en_path)}">' + "".join(
        f'<link rel="alternate" hreflang="{lg}" href="{c(lpath(en_path, lg))}">' for lg in LANGS)
        + f'<link rel="alternate" hreflang="x-default" href="{c(en_path)}">')


def _text_lang(t, L):
    s_ = t.strip()
    if not s_ or not re.search(r"[A-Za-z]{2}", s_):
        return t
    lead, trail = t[: len(t) - len(t.lstrip())], t[len(t.rstrip()):]
    if s_ in L["exact"]:
        return lead + L["exact"][s_] + trail
    out = s_
    for a, b in L["parts"]:
        out = re.sub(r"(?<![\w'])" + re.escape(a) + r"(?![\w'])", b, out)
    mon = L["months"]
    out = re.sub(r"(?<=\d )(" + "|".join(mon) + r")\b|\b(" + "|".join(mon) + r")(?= \d{4})", lambda m: mon[m.group(1) or m.group(2)], out)
    return lead + out + trail


def translate_lang(page, en_path, lang):
    L = LANGS[lang]
    c = lambda u: SITE_BASE + (u[: -len("index.html")] if u.endswith("index.html") else u[:-5])
    lp = lpath(en_path, lang)
    title, desc = L["meta"][en_path]
    s_ = page.replace('<html lang="en">', f'<html lang="{lang}">', 1)
    s_ = re.sub(r"<title>.*?</title>", f"<title>{title}</title>", s_, count=1, flags=re.S)
    s_ = re.sub(r'(<meta (?:name="description"|property="og:description") content=")[^"]*', lambda m: m.group(1) + desc, s_)
    s_ = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + title, s_)
    s_ = s_.replace(f'<link rel="canonical" href="{c(en_path)}">', f'<link rel="canonical" href="{c(lp)}">', 1)
    s_ = s_.replace(f'<meta property="og:url" content="{c(en_path)}">', f'<meta property="og:url" content="{c(lp)}">', 1)
    s_ = s_.replace("</head>", _alts_all(en_path) + "</head>", 1)
    links = {a: lpath(a, lang) for a in EN_PAGES}
    links.update({"/padel/rankings.html": lpath("/padel/rankings-men.html", lang), "/padel/": f"/padel/{lang}/"})
    for a, b in links.items():
        s_ = s_.replace(f'href="{a}"', f'href="{b}"')
    parts = re.split(r"(<script\b.*?</script>|<style\b.*?</style>|<[^>]+>)", s_, flags=re.S)
    return "".join(p if (p.startswith("<") or not p) else _text_lang(p, L) for p in parts)


def make_all(out):
    """Versões es/it/fr das páginas principais; as inglesas ganham hreflang para todas e as ligações no rodapé."""
    done = []
    cc = lambda u: u[: -len("index.html")] if u.endswith("index.html") else u[:-5]
    for en_path in EN_PAGES:
        fp = os.path.join(out, en_path.lstrip("/"))
        if not os.path.exists(fp):
            continue
        with open(fp, encoding="utf-8") as f:
            page = f.read()
        foot = " · ".join([f'<a href="{cc(en_path)}" hreflang="en">English</a>'] + [f'<a href="{cc(lpath(en_path, lg))}" hreflang="{lg}">{L["name"]}</a>' for lg, L in LANGS.items()])
        for lg in LANGS:
            tr = translate_lang(page, en_path, lg)
            tr = tr.replace("</footer>", f" · {foot}</footer>", 1)
            ep = os.path.join(out, lpath(en_path, lg).lstrip("/"))
            os.makedirs(os.path.dirname(ep), exist_ok=True)
            with open(ep, "w", encoding="utf-8") as f:
                f.write(tr)
            done.append(ep)
        if "hreflang=" not in page:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(page.replace("</head>", _alts_all(en_path) + "</head>", 1).replace("</footer>", f" · {foot}</footer>", 1))
    return done
