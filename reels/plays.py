"""Biblioteca de jogadas (ilustradas) para o ponto de campeonato: 5 de padel e 5 de ténis.
Cada jogada é uma lista de acontecimentos da bola (t, x, y, z, quem, tipo):
  quem = índice do jogador que bate (None para ressaltos, vidros e saídas); tipo = fh, bh, smash, serve, bounce, glass, out.
Os jogadores mexem-se sozinhos para chegar à bola (point.build_play); 'moves' acrescenta corridas de quem não chega.
Padel: 0 e 1 = par campeão (y < 0, 0 à esquerda), 2 e 3 = adversários (y > 0, 2 à esquerda). Ténis: 0 = campeão (y < 0), 1 = adversário.
Escolha (choose): ligada ao jogo real e sem repetir a mesma jogada nas últimas semanas."""

PADEL = {
    "por3": dict(title=("POR 3!", "Smash out over the back wall"),
                 homes=[(-2.4, -4.5), (2.5, -8.0), (-2.0, 7.4), (2.3, 5.0)],
                 ev=[(0.0, -1.8, 7.6, 1.0, 2, "fh"), (0.78, 1.5, -6.2, 0.0, None, "bounce"), (1.18, 2.3, -10.0, 1.35, None, "glass"),
                     (1.55, 2.4, -8.5, 0.95, 1, "fh"), (3.15, -1.6, 7.9, 0.0, None, "bounce"), (3.5, -1.8, 10.0, 1.9, None, "glass"),
                     (3.95, -1.5, 8.8, 1.15, 2, "fh"), (5.55, -1.0, -3.4, 2.75, 0, "smash"), (5.82, 1.9, 6.6, 0.0, None, "bounce"),
                     (6.25, 2.6, 10.0, 4.7, None, "out"), (6.9, 3.0, 14.0, 2.0, None, "out")],
                 moves={3: [(5.9, 2.2, 7.5), (6.4, 2.9, 8.9)]}),
    "por4": dict(title=("POR 4!", "Smash out over the side wall"),
                 homes=[(-2.2, -3.6), (2.0, -3.8), (-2.0, 8.0), (2.2, 8.4)],
                 ev=[(0.0, 2.2, 8.6, 0.9, 3, "fh"), (1.55, 0.9, -3.6, 2.8, 1, "smash"), (1.8, 4.2, 4.2, 0.0, None, "bounce"),
                     (2.15, 5.0, 6.0, 3.6, None, "out"), (2.7, 7.6, 7.8, 1.2, None, "out")],
                 moves={2: [(1.9, 0.4, 6.8), (2.5, 3.4, 6.4)], 3: [(1.0, 2.4, 7.2), (2.3, 3.9, 6.2)]}),
    "vibora": dict(title=("VÍBORA!", "Off the side glass, unreturnable"),
                   homes=[(-2.2, -4.2), (2.3, -4.6), (-2.0, 8.2), (2.2, 7.8)],
                   ev=[(0.0, -1.8, 8.4, 0.9, 2, "fh"), (1.4, -1.6, -4.4, 2.3, 0, "smash"), (1.85, -3.8, 7.6, 0.0, None, "bounce"),
                       (2.05, -5.0, 8.9, 0.6, None, "glass"), (2.45, -3.4, 9.7, 0.0, None, "bounce"), (2.9, -2.6, 9.9, 0.0, None, "bounce")],
                   moves={2: [(1.5, -2.6, 7.8), (2.2, -3.4, 8.6), (2.7, -3.0, 9.2)], 3: [(1.6, 0.6, 7.6)]}),
    "volley": dict(title=("REFLEX VOLLEY.", "Four players at the net"),
                   homes=[(-1.4, -2.7), (1.4, -2.6), (-1.6, 2.7), (1.6, 2.7)],
                   ev=[(0.0, 1.6, 2.8, 0.85, 3, "fh"), (0.45, 1.2, -2.6, 0.9, 1, "fh"), (0.9, -1.4, 2.6, 0.95, 2, "bh"),
                       (1.35, -1.0, -2.7, 1.0, 0, "fh"), (1.8, 1.8, 2.5, 0.9, 3, "bh"), (2.25, 0.6, -2.5, 1.4, 1, "fh"),
                       (2.63, 0.1, 3.2, 0.0, None, "bounce"), (3.0, 0.6, 6.6, 0.25, None, "bounce"), (3.3, 0.8, 10.0, 0.5, None, "glass"),
                       (3.65, 0.8, 8.8, 0.0, None, "bounce")],
                   moves={2: [(2.5, -0.6, 3.4), (2.9, -0.2, 4.0)], 3: [(2.45, 1.0, 3.3), (2.9, 0.9, 4.2)]}),
    "globo": dict(title=("LOB WINNER.", "Over the net players, dead off the glass"),
                  homes=[(-2.3, -8.4), (2.4, -8.6), (-1.6, 2.8), (1.8, 2.6)],
                  ev=[(0.0, 0.8, 2.4, 1.0, 3, "fh"), (0.85, 1.8, -8.3, 0.9, 1, "fh"), (2.6, -1.2, 8.6, 0.0, None, "bounce"),
                      (2.95, -1.6, 10.0, 1.6, None, "glass"), (3.4, -2.0, 9.0, 0.0, None, "bounce")],
                  moves={2: [(1.2, -1.6, 3.2), (2.2, -1.6, 5.5), (3.2, -1.8, 7.4)], 3: [(1.4, 1.6, 3.4), (2.6, 0.6, 5.0)]}),
}

TENNIS = {
    "fh_dtl": dict(title=("WINNER.", "Forehand down the line"),
                   homes=[(0.4, -12.0), (-2.2, 11.6)],
                   ev=[(0.0, -2.5, 11.4, 1.0, 1, "fh"), (0.8, 1.8, -8.5, 0.0, None, "bounce"), (1.25, 2.6, -12.2, 0.95, 0, "fh"),
                       (2.25, -2.2, 6.0, 0.0, None, "bounce"), (2.65, -2.6, 11.0, 1.0, 1, "fh"), (3.55, -1.0, -7.8, 0.0, None, "bounce"),
                       (3.9, -0.8, -11.4, 1.15, 0, "fh"), (4.6, 3.7, 8.3, 0.0, None, "bounce"), (5.3, 4.0, 15.0, 0.45, None, "out")],
                   moves={1: [(4.4, 3.0, 9.8), (5.4, 3.4, 10.4)]}),
    "bh_cc": dict(title=("WINNER.", "Backhand cross-court"),
                  homes=[(-0.4, -12.0), (1.4, 11.8)],
                  ev=[(0.0, 1.2, 11.6, 1.0, 1, "fh"), (0.85, -2.6, -8.4, 0.0, None, "bounce"), (1.3, -3.1, -12.0, 0.95, 0, "bh"),
                      (2.2, 2.0, 7.6, 0.0, None, "bounce"), (2.6, 2.4, 11.4, 1.0, 1, "fh"), (3.45, -2.4, -7.9, 0.0, None, "bounce"),
                      (3.9, -2.9, -11.6, 1.2, 0, "bh"), (4.62, 3.6, 6.6, 0.0, None, "bounce"), (5.2, 5.8, 11.5, 0.5, None, "out")],
                  moves={1: [(4.0, 1.2, 11.0), (4.7, 3.4, 10.0)]}),
    "ace": dict(title=("ACE.", "Unreturnable serve"),
                homes=[(0.55, -12.25), (-1.5, 12.0)],
                ev=[(0.0, 0.75, -12.0, 1.3, None, "toss"), (0.9, 0.75, -12.0, 2.85, 0, "serve"), (1.32, -0.3, 6.1, 0.0, None, "bounce"),
                    (1.75, -0.9, 11.8, 1.0, None, "out"), (2.25, -1.4, 16.0, 0.6, None, "out")],
                moves={1: [(1.0, -1.4, 12.0), (1.5, -0.9, 11.6)]}),
    "drop": dict(title=("DROP SHOT.", "Two bounces before the chase"),
                 homes=[(1.6, -11.6), (-0.6, 11.6)],
                 ev=[(0.0, -1.0, 11.5, 1.0, 1, "fh"), (0.85, 1.6, -7.8, 0.0, None, "bounce"), (1.3, 2.0, -11.4, 1.0, 0, "fh"),
                     (2.25, 1.0, 8.6, 0.0, None, "bounce"), (2.65, 1.2, 11.6, 0.9, 1, "bh"), (3.55, -0.6, -6.4, 0.0, None, "bounce"),
                     (3.95, -0.9, -8.6, 1.1, 0, "fh"), (4.95, 1.6, 2.2, 0.0, None, "bounce"), (5.45, 1.8, 3.0, 0.0, None, "bounce"),
                     (5.8, 2.0, 3.6, 0.0, None, "bounce")],
                 moves={1: [(3.0, 1.2, 11.0), (4.2, 1.6, 6.0), (5.5, 1.9, 3.9)]}),
    "passing": dict(title=("PASSING SHOT.", "Down the line past the net rusher"),
                    homes=[(-1.4, -11.8), (0.8, 11.8)],
                    ev=[(0.0, 0.5, 11.6, 1.0, 1, "fh"), (0.85, -2.0, -7.8, 0.0, None, "bounce"), (1.3, -2.5, -11.3, 1.0, 0, "bh"),
                        (2.1, -1.6, 6.8, 0.0, None, "bounce"), (2.4, -1.9, 6.0, 0.9, 1, "fh"), (3.2, 2.8, -8.5, 0.0, None, "bounce"),
                        (3.6, 3.2, -11.6, 1.15, 0, "fh"), (4.3, 4.2, 8.2, 0.0, None, "bounce"), (4.9, 4.5, 13.5, 0.5, None, "out")],
                    moves={1: [(3.0, -1.2, 3.0), (3.7, -0.2, 3.4), (4.2, 1.0, 3.5)]}),
}

LIB = {"padel": PADEL, "tennis": TENNIS}


def choose(sport, sets, surface=None, setting=None, recent=()):
    """Jogada para uma final: ligada ao jogo (tie-break → rally mais longo; terra → mais trocas; relva/pavilhão → serviço)
    e sem repetir as mais recentes dessa conta."""
    tb = bool(sets) and tuple(sets[-1][:2]) in ((7, 6), (6, 7))
    if sport == "padel":
        pref = ["globo", "volley", "vibora", "por3", "por4"] if tb else ["por3", "vibora", "por4", "volley", "globo"]
    else:
        if surface == "clay": pref = ["drop", "bh_cc", "passing", "fh_dtl", "ace"]
        elif surface == "grass": pref = ["ace", "passing", "fh_dtl", "bh_cc", "drop"]
        elif tb: pref = ["passing", "bh_cc", "fh_dtl", "drop", "ace"]
        else: pref = ["fh_dtl", "ace", "bh_cc", "passing", "drop"]
    for p in pref:
        if p not in recent: return p
    return pref[0]
