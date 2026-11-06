"""Textos do site em vários idiomas (EN é a língua principal; ES, FR, DE, IT em /es/, /fr/, /de/, /it/).

Só as páginas principais são traduzidas (início, resultados, jogadores, stats, créditos). As páginas de jogador e de torneio
ficam em inglês (nomes e resultados não mudam). Para acrescentar um idioma: copia um bloco, traduz, acrescenta a LANGS.
"""

LANGS = {"en": "English", "es": "Español", "fr": "Français", "de": "Deutsch", "it": "Italiano"}

# textos extra (valores por defeito em inglês; usados também quando falta uma tradução)
EN = {
    "players": "Players", "search": "Search a player", "player": "Player", "streak": "Streak", "last": "Last match",
    "players_lead": "Wins, losses and streaks from the matches we track.", "week": "This week in numbers",
    "w_matches": "matches", "w_tourn": "tournaments", "w_three": "three-setters", "w_tb": "tie-breaks",
    "w_comeback": "comebacks", "w_bagel": "6-0 sets", "w_top": "Most wins", "next": "Next matches", "f_match": "match",
    "x_playing": "Playing now", "x_updated": "updated {t} UTC", "x_upset": "Upset of the week",
    "x_upset_line": "#{a} beat #{b}: a gap of {g} places.", "x_climbing": "Climbing the rankings",
    "x_nl_h": "The weekly numbers, in your inbox",
    "x_nl_p": "One email a week: champions, upsets and the stats from the Challenger and ITF circuit.",
    "x_subscribe": "Subscribe", "x_stats": "Stats",
    "x_stats_lead": "Running totals since {d}, singles only. Rates are the share of matches.",
    "x_stats_empty": "Stats appear once we have tracked a few more matches.",
    "x_by_surface": "By surface", "x_by_level": "By level", "x_countries": "Countries (singles wins)",
    "x_surface": "Surface", "x_matches": "Matches", "x_3sets": "3 sets", "x_tb": "Tie-break", "x_comeback": "Comeback",
    "x_level": "Level", "x_country": "Country", "x_w": "W", "x_l": "L", "x_winrate": "Win rate",
    "x_t_matches": "matches tracked", "x_t_players": "players", "x_t_tb": "matches with a tie-break",
    "x_t_comebacks": "comebacks", "x_credits": "Photo credits",
    "x_credits_p": "Player photos come from Wikimedia Commons under free licences (CC0, public domain, CC BY, CC BY-SA). "
                   "Each photo is credited to its author below and on the player page.",
    "x_credit": "Credit", "x_source": "Source", "x_language": "Language",
    "x_rankings": "Rankings", "x_rank_lead": "Latest ranking we have for each player seen in the matches we track. Not the full ATP/WTA list.",
    "x_rank": "Rank", "x_pts": "Points", "x_move": "Change", "x_seen": "Seen",
}

# nomes das rondas e superfícies (valores em inglês usados nos dados -> tradução)
ROUNDS_EN = ["Round of 128", "Round of 64", "Round of 32", "Round of 16", "Quarterfinals", "Semifinals", "Final"]

TX = {
    "es": {
        "x_rankings": "Rankings", "x_rank_lead": "Último ranking de cada jugador visto en los partidos que seguimos. No es la lista completa ATP/WTA.",
        "x_rank": "Puesto", "x_pts": "Puntos", "x_move": "Cambio", "x_seen": "Visto",
        "title": "Últimos resultados", "lead": "Challenger, ITF y el circuito más allá del top 100.",
        "empty": "Aún no hay resultados. Vuelve pronto.", "nav": "Resultados", "home": "Inicio",
        "h1a": "El tenis más allá", "h1b": "del top 100.",
        "desc": "Resultados en directo, tarjetas claras y las historias de las pistas Challenger, ITF y WTA.",
        "follow": "Sigue a @beyond100.tennis", "all": "Todos los resultados",
        "note": "Los resultados son solo informativos y pueden contener retrasos o errores.",
        "f_all": "Todos", "f_men": "Hombres", "f_women": "Mujeres", "f_singles": "Individuales", "f_doubles": "Dobles",
        "f_alltour": "Todos los torneos", "f_matches": "partidos", "f_more": "Mostrar más", "f_tournament": "Torneo",
        "f_player": "Buscar jugador", "f_highlights": "Destacados", "f_games": "de los juegos", "f_champion": "Campeón",
        "f_bracket": "Cuadro", "f_tbd": "Por decidir", "f_search_tour": "Buscar torneo", "f_tournaments": "Todos los torneos",
        "b_comeback": "Remontada", "b_bagel": "Rosco (6-0)", "b_breadstick": "Palito (6-1)", "b_super": "Supertie-break",
        "b_tb": "{n} tie-break", "b_closest": "El más igualado del día",
        "players": "Jugadores", "search": "Buscar un jugador", "player": "Jugador", "streak": "Racha", "last": "Último partido",
        "players_lead": "Victorias, derrotas y rachas de los partidos que seguimos.", "week": "Esta semana en cifras",
        "w_matches": "partidos", "w_tourn": "torneos", "w_three": "a tres sets", "w_tb": "tie-breaks",
        "w_comeback": "remontadas", "w_bagel": "sets 6-0", "w_top": "Más victorias", "next": "Próximos partidos", "f_match": "partido",
        "x_playing": "Jugando ahora", "x_updated": "actualizado {t} UTC", "x_upset": "Sorpresa de la semana",
        "x_upset_line": "El n.º {a} venció al n.º {b}: una diferencia de {g} puestos.", "x_climbing": "Subiendo en el ranking",
        "x_nl_h": "Los números de la semana, en tu correo",
        "x_nl_p": "Un correo a la semana: campeones, sorpresas y las estadísticas del circuito Challenger e ITF.",
        "x_subscribe": "Suscribirme", "x_stats": "Estadísticas",
        "x_stats_lead": "Totales acumulados desde {d}, solo individuales. Los porcentajes son sobre el total de partidos.",
        "x_stats_empty": "Las estadísticas aparecerán cuando hayamos seguido algunos partidos más.",
        "x_by_surface": "Por superficie", "x_by_level": "Por nivel", "x_countries": "Países (victorias en individuales)",
        "x_surface": "Superficie", "x_matches": "Partidos", "x_3sets": "3 sets", "x_tb": "Tie-break", "x_comeback": "Remontada",
        "x_level": "Nivel", "x_country": "País", "x_w": "V", "x_l": "D", "x_winrate": "% de victorias",
        "x_t_matches": "partidos seguidos", "x_t_players": "jugadores", "x_t_tb": "partidos con tie-break",
        "x_t_comebacks": "remontadas", "x_credits": "Créditos de las fotos",
        "x_credits_p": "Las fotos de los jugadores proceden de Wikimedia Commons con licencias libres (CC0, dominio público, CC BY, CC BY-SA). "
                       "Cada foto se atribuye a su autor aquí abajo y en la página del jugador.",
        "x_credit": "Crédito", "x_source": "Fuente", "x_language": "Idioma",
        "_rounds": ["Ronda de 128", "Ronda de 64", "Ronda de 32", "Octavos de final", "Cuartos de final", "Semifinales", "Final"],
        "_surfaces": {"clay": "Tierra batida", "hard": "Pista dura", "grass": "Hierba", "carpet": "Moqueta"},
    },
    "fr": {
        "x_rankings": "Classements", "x_rank_lead": "Dernier classement connu de chaque joueur vu dans les matchs que nous suivons. Ce n'est pas la liste complète ATP/WTA.",
        "x_rank": "Rang", "x_pts": "Points", "x_move": "Évolution", "x_seen": "Vu",
        "title": "Derniers résultats", "lead": "Challenger, ITF et le circuit au-delà du top 100.",
        "empty": "Pas encore de résultats. Revenez bientôt.", "nav": "Résultats", "home": "Accueil",
        "h1a": "Le tennis au-delà", "h1b": "du top 100.",
        "desc": "Scores en direct, cartes de résultats claires et les histoires des courts Challenger, ITF et WTA.",
        "follow": "Suivre @beyond100.tennis", "all": "Tous les résultats",
        "note": "Les scores sont fournis à titre informatif et peuvent contenir des retards ou des erreurs.",
        "f_all": "Tous", "f_men": "Hommes", "f_women": "Femmes", "f_singles": "Simples", "f_doubles": "Doubles",
        "f_alltour": "Tous les tournois", "f_matches": "matchs", "f_more": "Afficher plus", "f_tournament": "Tournoi",
        "f_player": "Rechercher un joueur", "f_highlights": "À la une", "f_games": "des jeux", "f_champion": "Champion",
        "f_bracket": "Tableau", "f_tbd": "À déterminer", "f_search_tour": "Rechercher un tournoi", "f_tournaments": "Tous les tournois",
        "b_comeback": "Remontada", "b_bagel": "Bagel (6-0)", "b_breadstick": "Baguette (6-1)", "b_super": "Super tie-break",
        "b_tb": "{n} tie-break", "b_closest": "Le plus serré du jour",
        "players": "Joueurs", "search": "Rechercher un joueur", "player": "Joueur", "streak": "Série", "last": "Dernier match",
        "players_lead": "Victoires, défaites et séries des matchs que nous suivons.", "week": "La semaine en chiffres",
        "w_matches": "matchs", "w_tourn": "tournois", "w_three": "en trois sets", "w_tb": "tie-breaks",
        "w_comeback": "remontées", "w_bagel": "sets 6-0", "w_top": "Plus de victoires", "next": "Prochains matchs", "f_match": "match",
        "x_playing": "En cours", "x_updated": "mis à jour {t} UTC", "x_upset": "Surprise de la semaine",
        "x_upset_line": "Le n° {a} a battu le n° {b} : un écart de {g} places.", "x_climbing": "En hausse au classement",
        "x_nl_h": "Les chiffres de la semaine, dans votre boîte mail",
        "x_nl_p": "Un e-mail par semaine : champions, surprises et statistiques du circuit Challenger et ITF.",
        "x_subscribe": "S'abonner", "x_stats": "Statistiques",
        "x_stats_lead": "Totaux cumulés depuis le {d}, simples uniquement. Les taux sont la part des matchs.",
        "x_stats_empty": "Les statistiques apparaîtront quand nous aurons suivi quelques matchs de plus.",
        "x_by_surface": "Par surface", "x_by_level": "Par niveau", "x_countries": "Pays (victoires en simple)",
        "x_surface": "Surface", "x_matches": "Matchs", "x_3sets": "3 sets", "x_tb": "Tie-break", "x_comeback": "Remontée",
        "x_level": "Niveau", "x_country": "Pays", "x_w": "V", "x_l": "D", "x_winrate": "% de victoires",
        "x_t_matches": "matchs suivis", "x_t_players": "joueurs", "x_t_tb": "matchs avec tie-break",
        "x_t_comebacks": "remontées", "x_credits": "Crédits photo",
        "x_credits_p": "Les photos des joueurs viennent de Wikimedia Commons sous licences libres (CC0, domaine public, CC BY, CC BY-SA). "
                       "Chaque photo est attribuée à son auteur ci-dessous et sur la page du joueur.",
        "x_credit": "Crédit", "x_source": "Source", "x_language": "Langue",
        "_rounds": ["64es de finale", "32es de finale", "16es de finale", "Huitièmes de finale", "Quarts de finale", "Demi-finales", "Finale"],
        "_surfaces": {"clay": "Terre battue", "hard": "Dur", "grass": "Gazon", "carpet": "Moquette"},
    },
    "de": {
        "x_rankings": "Ranglisten", "x_rank_lead": "Letzte bekannte Platzierung jedes Spielers aus den Spielen, die wir verfolgen. Nicht die vollständige ATP/WTA-Liste.",
        "x_rank": "Rang", "x_pts": "Punkte", "x_move": "Änderung", "x_seen": "Gesehen",
        "title": "Aktuelle Ergebnisse", "lead": "Challenger, ITF und die Tour jenseits der Top 100.",
        "empty": "Noch keine Ergebnisse. Bald wieder vorbeischauen.", "nav": "Ergebnisse", "home": "Start",
        "h1a": "Tennis jenseits", "h1b": "der Top 100.",
        "desc": "Live-Ergebnisse, klare Ergebniskarten und die Geschichten von den Challenger-, ITF- und WTA-Plätzen.",
        "follow": "Folge @beyond100.tennis", "all": "Alle Ergebnisse",
        "note": "Ergebnisse dienen nur zur Information und können Verzögerungen oder Fehler enthalten.",
        "f_all": "Alle", "f_men": "Herren", "f_women": "Damen", "f_singles": "Einzel", "f_doubles": "Doppel",
        "f_alltour": "Alle Turniere", "f_matches": "Spiele", "f_more": "Mehr anzeigen", "f_tournament": "Turnier",
        "f_player": "Spieler suchen", "f_highlights": "Top-Spiele", "f_games": "der Spiele", "f_champion": "Sieger",
        "f_bracket": "Turnierbaum", "f_tbd": "Noch offen", "f_search_tour": "Turnier suchen", "f_tournaments": "Alle Turniere",
        "b_comeback": "Comeback", "b_bagel": "Bagel (6:0)", "b_breadstick": "Breadstick (6:1)", "b_super": "Match-Tiebreak",
        "b_tb": "{n} Tiebreak", "b_closest": "Knappstes Spiel des Tages",
        "players": "Spieler", "search": "Spieler suchen", "player": "Spieler", "streak": "Serie", "last": "Letztes Spiel",
        "players_lead": "Siege, Niederlagen und Serien aus den Spielen, die wir verfolgen.", "week": "Die Woche in Zahlen",
        "w_matches": "Spiele", "w_tourn": "Turniere", "w_three": "Dreisatzspiele", "w_tb": "Tiebreaks",
        "w_comeback": "Comebacks", "w_bagel": "6:0-Sätze", "w_top": "Meiste Siege", "next": "Nächste Spiele", "f_match": "Spiel",
        "x_playing": "Läuft gerade", "x_updated": "aktualisiert {t} UTC", "x_upset": "Überraschung der Woche",
        "x_upset_line": "Nr. {a} schlug Nr. {b}: ein Unterschied von {g} Plätzen.", "x_climbing": "Aufsteiger in der Rangliste",
        "x_nl_h": "Die Zahlen der Woche, in Ihrem Postfach",
        "x_nl_p": "Eine E-Mail pro Woche: Sieger, Überraschungen und Statistiken von der Challenger- und ITF-Tour.",
        "x_subscribe": "Abonnieren", "x_stats": "Statistiken",
        "x_stats_lead": "Laufende Summen seit {d}, nur Einzel. Quoten sind der Anteil an den Spielen.",
        "x_stats_empty": "Statistiken erscheinen, sobald wir einige weitere Spiele erfasst haben.",
        "x_by_surface": "Nach Belag", "x_by_level": "Nach Level", "x_countries": "Länder (Einzelsiege)",
        "x_surface": "Belag", "x_matches": "Spiele", "x_3sets": "3 Sätze", "x_tb": "Tiebreak", "x_comeback": "Comeback",
        "x_level": "Level", "x_country": "Land", "x_w": "S", "x_l": "N", "x_winrate": "Siegquote",
        "x_t_matches": "erfasste Spiele", "x_t_players": "Spieler", "x_t_tb": "Spiele mit Tiebreak",
        "x_t_comebacks": "Comebacks", "x_credits": "Bildnachweise",
        "x_credits_p": "Spielerfotos stammen von Wikimedia Commons unter freien Lizenzen (CC0, gemeinfrei, CC BY, CC BY-SA). "
                       "Jedes Foto ist unten und auf der Spielerseite seinem Urheber zugeordnet.",
        "x_credit": "Nachweis", "x_source": "Quelle", "x_language": "Sprache",
        "_rounds": ["Runde der letzten 128", "Runde der letzten 64", "Runde der letzten 32", "Achtelfinale", "Viertelfinale", "Halbfinale", "Finale"],
        "_surfaces": {"clay": "Sand", "hard": "Hartplatz", "grass": "Rasen", "carpet": "Teppich"},
    },
    "it": {
        "x_rankings": "Classifiche", "x_rank_lead": "Ultima posizione nota di ogni giocatore visto nelle partite che seguiamo. Non è la lista completa ATP/WTA.",
        "x_rank": "Pos.", "x_pts": "Punti", "x_move": "Variazione", "x_seen": "Visto",
        "title": "Ultimi risultati", "lead": "Challenger, ITF e il circuito oltre la top 100.",
        "empty": "Ancora nessun risultato. Torna presto.", "nav": "Risultati", "home": "Home",
        "h1a": "Il tennis oltre", "h1b": "la top 100.",
        "desc": "Punteggi dal vivo, schede dei risultati chiare e le storie dei campi Challenger, ITF e WTA.",
        "follow": "Segui @beyond100.tennis", "all": "Tutti i risultati",
        "note": "I punteggi sono solo informativi e possono contenere ritardi o errori.",
        "f_all": "Tutti", "f_men": "Uomini", "f_women": "Donne", "f_singles": "Singolare", "f_doubles": "Doppio",
        "f_alltour": "Tutti i tornei", "f_matches": "partite", "f_more": "Mostra altro", "f_tournament": "Torneo",
        "f_player": "Cerca giocatore", "f_highlights": "In evidenza", "f_games": "dei giochi", "f_champion": "Campione",
        "f_bracket": "Tabellone", "f_tbd": "Da definire", "f_search_tour": "Cerca torneo", "f_tournaments": "Tutti i tornei",
        "b_comeback": "Rimonta", "b_bagel": "Bagel (6-0)", "b_breadstick": "Grissino (6-1)", "b_super": "Super tie-break",
        "b_tb": "{n} tie-break", "b_closest": "La più equilibrata del giorno",
        "players": "Giocatori", "search": "Cerca un giocatore", "player": "Giocatore", "streak": "Serie", "last": "Ultima partita",
        "players_lead": "Vittorie, sconfitte e serie delle partite che seguiamo.", "week": "La settimana in numeri",
        "w_matches": "partite", "w_tourn": "tornei", "w_three": "al terzo set", "w_tb": "tie-break",
        "w_comeback": "rimonte", "w_bagel": "set 6-0", "w_top": "Più vittorie", "next": "Prossime partite", "f_match": "partita",
        "x_playing": "In campo ora", "x_updated": "aggiornato {t} UTC", "x_upset": "Sorpresa della settimana",
        "x_upset_line": "Il n. {a} ha battuto il n. {b}: una differenza di {g} posizioni.", "x_climbing": "In salita nel ranking",
        "x_nl_h": "I numeri della settimana, nella tua casella",
        "x_nl_p": "Una email a settimana: campioni, sorprese e statistiche dal circuito Challenger e ITF.",
        "x_subscribe": "Iscriviti", "x_stats": "Statistiche",
        "x_stats_lead": "Totali dal {d}, solo singolare. Le percentuali sono la quota di partite.",
        "x_stats_empty": "Le statistiche compariranno quando avremo seguito qualche partita in più.",
        "x_by_surface": "Per superficie", "x_by_level": "Per livello", "x_countries": "Paesi (vittorie in singolare)",
        "x_surface": "Superficie", "x_matches": "Partite", "x_3sets": "3 set", "x_tb": "Tie-break", "x_comeback": "Rimonta",
        "x_level": "Livello", "x_country": "Paese", "x_w": "V", "x_l": "S", "x_winrate": "% vittorie",
        "x_t_matches": "partite seguite", "x_t_players": "giocatori", "x_t_tb": "partite con tie-break",
        "x_t_comebacks": "rimonte", "x_credits": "Crediti fotografici",
        "x_credits_p": "Le foto dei giocatori provengono da Wikimedia Commons con licenze libere (CC0, pubblico dominio, CC BY, CC BY-SA). "
                       "Ogni foto è attribuita al suo autore qui sotto e nella pagina del giocatore.",
        "x_credit": "Credito", "x_source": "Fonte", "x_language": "Lingua",
        "_rounds": ["Turno di 128", "Turno di 64", "Turno di 32", "Ottavi di finale", "Quarti di finale", "Semifinali", "Finale"],
        "_surfaces": {"clay": "Terra rossa", "hard": "Cemento", "grass": "Erba", "carpet": "Sintetico"},
    },
}


def tx_for(lang, base_en):
    """Textos da página em `lang` (cai para inglês quando falta uma chave)."""
    out = dict(base_en)
    out.update(EN)
    out.update({k: v for k, v in TX.get(lang, {}).items() if not k.startswith("_")})
    return out


def tr_for(lang, base_en):
    """Nomes de rondas e superfícies traduzidos (cópia de I18N['en'] com as traduções)."""
    tr = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base_en.items()}
    t = TX.get(lang)
    if not t:
        return tr
    mapping = dict(zip(ROUNDS_EN, t["_rounds"]))
    tr["rounds"] = {k: mapping.get(v, v) for k, v in base_en["rounds"].items()}
    tr["surfaces"] = dict(base_en["surfaces"], **t["_surfaces"])
    return tr
