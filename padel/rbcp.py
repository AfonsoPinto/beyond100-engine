"""Fotos do Red Bull Content Pool (RBCP) para os posts de padel (18/11/2026, Afonso).

Licença "EDITORIAL Use" (termos do RBCP, 4.2 e 4.6):
- cobertura de eventos (uso editorial, sem publicidade): posts de resultados/notícias e, desde 18/11/2026 (Afonso), as fotos
  dos jogadores no site (só fotos a solo; a mais recente ganha à foto própria; sai do site quando acaba a licença);
- válida 6 meses a contar do dia do download (aqui: 182 dias; depois a foto deixa de ser usada e é apagada);
- crédito "Premier Padel / Red Bull Content Pool" na imagem e, no Instagram, marcar @redbull e o fotógrafo (@premierpadel);
- "AI Prohibition": a foto não pode passar por IA. O motor só a recorta e compõe em Python; as legendas destes posts
  não usam IA (só factos fixos).

Os pedidos de download são feitos no browser (na conta do Afonso); só o link de download chega aqui, em rbcp/inbox.json.
  python -m padel.rbcp fetch    busca as fotos pedidas e guarda-as em rbcp/photos/<productId>.jpg (+ rbcp/photos.json)
  python -m padel.rbcp needs    escreve rbcp/needs.json: de quem falta foto (torneios Premier a decorrer primeiro, depois o top 100)
"""
import datetime as dt
import json
import os
import re
import sys
import unicodedata

ROOT = "rbcp"
LIB = os.path.join(ROOT, "photos")
META = os.path.join(ROOT, "photos.json")
INBOX = os.path.join(ROOT, "inbox.json")
NEEDS = os.path.join(ROOT, "needs.json")
VALID_DAYS = 182
CREDIT = "Premier Padel / Red Bull Content Pool"
TAGS = "@premierpadel @redbull"


def _load(p, d):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return d


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]+", " ", s).split()


def _age(e, today=None):
    try:
        return ((today or dt.date.today()) - dt.date.fromisoformat(e.get("downloaded"))).days
    except (TypeError, ValueError):
        return 10 ** 6


def valid():
    """{productId: dados} das fotos dentro da licença (e com ficheiro)."""
    out = {}
    for pid, e in _load(META, {}).items():
        if _age(e) < VALID_DAYS and os.path.exists(os.path.join(LIB, pid + ".jpg")):
            out[pid] = e
    return out


def _names_in(e):
    """Nomes das pessoas na foto: os da etiqueta Person e os do título ("Leandro Augsburger and Juan Lebron")."""
    t = e.get("title") or ""
    names = list(e.get("persons") or []) + re.split(r",| and | y | e ", t)
    return [norm(n) for n in names if n.strip()]


def matches(e, player):
    """A foto é deste jogador? Nome próprio + apelido (ou apelido do circuito) iguais a uma pessoa da foto."""
    full = norm(player.get("name"))
    short = norm(player.get("short_name"))
    if not full:
        return False
    first, last = full[0], full[-1]
    for n in _names_in(e):
        if not n:
            continue
        if first in n and (last in n or (short and short[-1] in n)):
            return True
    return False


_SKIP = {"premier", "padel", "p1", "p2", "major", "fip", "2026", "2027"}


def same_event(ph, tournament):
    tn = set(norm(tournament or "")) - _SKIP
    return bool(tn) and tn <= set(norm((ph or {}).get("event") or ""))


def photo_for(player, tournament=None):
    """Melhor foto válida do jogador: do próprio torneio primeiro, depois a mais recente.
    Devolve {"path", "credit", "pid", "rbcp", "event"} ou None."""
    cands = [(pid, e) for pid, e in valid().items() if matches(e, player)]
    if not cands:
        return None
    tn = set(norm(tournament or "")) - _SKIP
    def key(x):
        ev = set(norm(x[1].get("event") or ""))
        same = bool(tn) and tn <= ev
        pair = len(_names_in(x[1])) >= 2                         # foto com o par todo
        return (same, pair, x[1].get("downloaded") or "", x[0])
    pid, e = max(cands, key=key)
    return {"path": os.path.join(LIB, pid + ".jpg"), "credit": e.get("credit") or CREDIT, "pid": player.get("id"), "rbcp": pid,
            "event": e.get("event")}


def solo(e):
    """Foto de um jogador só (para o site: perfil e miniaturas). Pela etiqueta Person; sem ela, pelo título."""
    ps = [x for x in (e.get("persons") or []) if (x or "").strip()]
    if ps:
        return len(ps) == 1
    return not re.search(r",| and | y | e | & |/", e.get("title") or "")


def site_photos(players):
    """{id do jogador: {"path", "credit", "rbcp", "downloaded"}}: a foto a solo válida mais recente de cada jogador."""
    have = [(pid, e) for pid, e in valid().items() if solo(e)]
    out = {}
    if not have:
        return out
    for p in players:
        c = [(e.get("downloaded") or "", pid, e) for pid, e in have if matches(e, p)]
        if c:
            d, pid, e = max(c)
            out[str(p.get("id"))] = {"path": os.path.join(LIB, pid + ".jpg"), "credit": e.get("credit") or CREDIT, "rbcp": pid, "downloaded": d}
    return out


def fetch():
    """Busca as fotos pedidas no browser (links em rbcp/inbox.json). Sem IA: só descarrega e confirma que é uma imagem.
    Nunca escreve os links nos registos (são privados). Apaga as fotos fora da licença."""
    import requests
    from PIL import Image
    os.makedirs(LIB, exist_ok=True)
    meta, items, left, got = _load(META, {}), _load(INBOX, []), [], 0
    for it in items:
        pid = re.sub(r"[^A-Za-z0-9-]", "", it.get("productId") or "")
        if not pid or not it.get("url"):
            continue
        fn = os.path.join(LIB, pid + ".jpg")
        try:
            r = requests.get(it["url"], timeout=60)
            if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
                print(f"RBCP {pid}: ainda não ({r.status_code})"); left.append(it); continue
            with open(fn, "wb") as f:
                f.write(r.content)
            with Image.open(fn) as im:
                im.verify()
            meta[pid] = {k: it.get(k) for k in ("assetId", "persons", "title", "event", "credit", "usage", "downloaded")}
            got += 1
        except Exception as e:
            print(f"RBCP {pid}: falhou ({type(e).__name__})")
            if (it.get("tries") or 0) < 3:
                it["tries"] = (it.get("tries") or 0) + 1; left.append(it)
    gone = 0
    for pid in list(meta):                                       # fim da licença: deixa de existir
        if _age(meta[pid]) >= VALID_DAYS:
            try: os.remove(os.path.join(LIB, pid + ".jpg"))
            except OSError: pass
            meta.pop(pid); gone += 1
    os.makedirs(ROOT, exist_ok=True)
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(left, open(INBOX, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"RBCP: {got} fotos novas, {len(meta)} válidas, {gone} fora da licença, {len(left)} por buscar.")


def needs(limit=60):
    """De quem falta foto, por prioridade: 1) jogadores dos torneios Premier a decorrer (foto DESSE torneio);
    2) top 100 (homens e mulheres) sem foto nenhuma; 3) fotos a 3 semanas de acabar a licença;
    4) top 100 sem foto a solo recente (para o site: why "site", uma foto só desse jogador)."""
    from padel import cards
    D = "padel/data"
    tours = _load(f"{D}/tournaments.json", {})
    R = _load(f"{D}/rankings.json", {})
    today = dt.date.today().isoformat()
    have = valid()
    out, seen = [], set()
    def add(p, why, event=None):
        k = str(p.get("id"))
        if k in seen or not p.get("name"):
            return
        seen.add(k)
        out.append({"id": p.get("id"), "name": p["name"], "short_name": p.get("short_name"), "why": why, "event": event})
    for tid, t in tours.items():
        if (t.get("level") or "").lower() not in {"major", "p1", "p2", "finals"}:
            continue
        if not ((t.get("start_date") or "9") <= today <= (t.get("end_date") or "0")):
            continue
        ms = _load(f"{D}/matches/{tid}.json", [])
        alive = {}
        for m in ms:
            for side in ("team_1", "team_2"):
                for p in (m.get("players") or {}).get(side) or []:
                    alive[str(p.get("id"))] = p
        for p in alive.values():
            ph = photo_for(p, t.get("name"))
            ev_ok = ph and set(norm(t.get("name"))) - {"premier", "padel", "p1", "p2", "major", "2026", "2027"} <= set(norm(ph.get("event") or ""))
            if not ev_ok:
                add(p, "torneio", t.get("name"))
    rows = [((R.get(g) or {}).get("rows") or [])[:100] for g in ("men", "women")]
    for i in range(100):                                          # homens e mulheres alternados, por ranking
        for rs in rows:
            if i < len(rs):
                p = rs[i]
                if not (cards.photo_of(p["id"])[0] or photo_for(p)):
                    add(p, "top100")
    for pid, e in have.items():                                   # renovar antes de acabar a licença
        if VALID_DAYS - _age(e) <= 21:
            for n in (e.get("persons") or [])[:1]:
                add({"id": "rbcp-" + pid, "name": n}, "renovar")
    solo_ok = {str(k) for k in site_photos([p for rs in rows for p in rs])}
    for i in range(100):
        for rs in rows:
            if i < len(rs) and str(rs[i]["id"]) not in solo_ok:
                add(rs[i], "site")
    os.makedirs(ROOT, exist_ok=True)
    json.dump(out[:limit], open(NEEDS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"RBCP: {len(out)} pedidos de foto ({sum(1 for x in out if x['why'] == 'torneio')} do torneio a decorrer); {min(len(out), limit)} na lista.")


if __name__ == "__main__":
    {"fetch": fetch, "needs": needs}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__))()
