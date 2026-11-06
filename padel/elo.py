"""Favorito pelo Elo (ranking Elo da Padel API, grátis): força de cada par = média do Elo dos dois jogadores;
probabilidade estimada pela fórmula clássica do Elo (escala 400). É uma estimativa NOSSA a partir do Elo publicado,
não a probabilidade oficial da Padel API (essa só existe no plano Pro). Sem Elo dos dois jogadores dos dois pares: None."""
import json
import os

DATA = os.path.join(os.path.dirname(__file__), "data")
_map = None


def _load():
    global _map
    if _map is None:
        _map = {}
        try:
            d = json.load(open(os.path.join(DATA, "elo.json"), encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        for cat in ("men", "women"):
            for x in (d.get(cat) or {}).get("rows") or []:
                if x.get("id") is not None and isinstance(x.get("points"), (int, float)):
                    _map[str(x["id"])] = x["points"]
        try:                                                   # fichas com Elo (jogadores fora do top 200 do ranking Elo)
            pl = json.load(open(os.path.join(DATA, "players.json"), encoding="utf-8"))
            for pid, p in pl.items():
                e = p.get("elo") if isinstance(p, dict) else None
                if isinstance(e, dict) and isinstance(e.get("points"), (int, float)):
                    _map.setdefault(str(pid), e["points"])
        except (OSError, ValueError):
            pass
    return _map


def pair(team):
    """Elo do par (média) ou None se faltar o de algum jogador."""
    m = _load()
    v = [m.get(str(p.get("id"))) for p in team or []]
    return sum(v) / len(v) if len(v) == 2 and all(isinstance(x, (int, float)) for x in v) else None


def chance(team_a, team_b):
    """Probabilidade estimada (0-1) de team_a ganhar, ou None."""
    a, b = pair(team_a), pair(team_b)
    if a is None or b is None:
        return None
    return 1 / (1 + 10 ** ((b - a) / 400))
