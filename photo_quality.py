"""Filtro de qualidade das fotos usadas nos POSTS (ténis e padel), 9/11/2026.

Problemas que apareceram no Instagram: foto ampliada e desfocada (Chingotto), retrato minúsculo fora do court (Eala),
foto de cerimónia com várias pessoas (Tjen). Uma foto só vai para um cartão se:
  1. tiver detalhe real: comparamos a foto (normalizada a 900 px no lado menor) com ela própria reduzida a metade e
     ampliada de novo; se quase nada se perde, a foto já era "mole" (ampliada ou desfocada). Limite medido nas nossas fotos:
     abaixo de 1,0 é visivelmente má (24 de 588 no ténis, 3 de 18 no padel);
  2. o lado menor tiver pelo menos 450 px;
  3. não for uma foto de grupo/cerimónia: o nome do ficheiro no Commons não tem outro jogador conhecido nem palavras
     como "and", "ceremony", "team", "awards"... (fotos "X vs Y" também ficam de fora: são dois jogadores)
Não reconhece caras: só olha para a nitidez, o tamanho e o nome do ficheiro.
"""
import functools
import re
import unicodedata
import urllib.parse

MIN_DETAIL = 1.0
MIN_SIDE = 450
GROUP_WORDS = {"and", "with", "ceremony", "podium", "team", "teams", "doubles", "award", "awards", "gala", "press",
               "conference", "presentation", "players", "group", "winners", "finalists", "draw"}


@functools.lru_cache(maxsize=4096)
def detail(fp):
    """Detalhe da foto (média da diferença entre a foto e a sua versão a metade da resolução), ou 0 se não abrir."""
    try:
        from PIL import Image, ImageChops, ImageStat
        with Image.open(fp) as im0:
            side = min(im0.size)
            im = im0.convert("L")
        w, h = im.size
        k = 900 / max(1, min(w, h))
        im = im.resize((max(8, round(w * k)), max(8, round(h * k))), Image.LANCZOS)
        w, h = im.size
        sm = im.resize((max(4, w // 2), max(4, h // 2)), Image.LANCZOS).resize((w, h), Image.LANCZOS)
        return round(ImageStat.Stat(ImageChops.difference(im, sm)).mean[0], 3), side
    except Exception:
        return 0.0, 0


def _plain(t):
    return "".join(c for c in unicodedata.normalize("NFKD", t or "") if not unicodedata.combining(c)).lower()


def _words(page):
    f = urllib.parse.unquote((page or "").rsplit("/", 1)[-1])
    f = re.sub(r"edited[_ ]and[_ ]cropped", "cropped", f, flags=re.I)
    f = re.sub(r"^File:", "", f, flags=re.I)
    f = re.sub(r"\.(jpe?g|png|webp)$", "", f, flags=re.I)
    return [w for w in re.split(r"[\s_\-(),.&]+", _plain(f)) if w]


def group_photo(page, name, known_names=()):
    """True se o nome do ficheiro sugere várias pessoas: outro jogador conhecido ou palavras de cerimónia/grupo."""
    ws = _words(page)
    if not ws:
        return False
    if "&" in urllib.parse.unquote(page or "") or GROUP_WORDS & set(ws):
        return True
    mine = set(re.split(r"[\s\-]+", _plain(name)))
    for other in known_names or ():
        t = [x for x in re.split(r"[\s\-]+", _plain(other)) if len(x) > 2]
        if len(t) >= 2 and not set(t) <= mine and t[-1] not in mine and all(x in ws for x in (t[0], t[-1])):
            return True
    return False


def card_ok(fp, name="", page="", known_names=(), why=None):
    """A foto serve para um post? why (lista) recebe o motivo quando não serve."""
    d, side = detail(fp)
    reason = ("desfocada/ampliada" if d < MIN_DETAIL else "pequena" if side < MIN_SIDE
              else "foto de grupo/cerimónia" if group_photo(page, name, known_names) else "")
    if reason and why is not None:
        why.append(reason)
    return not reason
