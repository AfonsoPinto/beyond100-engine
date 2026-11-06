"""Atualiza categorias_torneios.json (Challenger 50/75/100/125/175 e WTA 250/500/1000) a partir da Wikipédia.

  python categorias.py                 -> ano atual e seguinte
  python categorias.py --years 2027    -> só esse ano
  python categorias.py --dry           -> mostra o que faria, sem gravar

Segurança: se uma página não puder ser lida ou der poucos resultados, mantém a lista anterior desse ano e avisa no log.
As correções feitas à mão ficam em categorias_manual.json (têm prioridade e nunca são apagadas).
No fim valida contra results.json: torneios recentes sem categoria vão para categorias_faltam.json (aparece no admin).
"""
import argparse
import datetime
import json
import os
import re
import sys
import unicodedata

import requests

FILE = "categorias_torneios.json"
MANUAL = "categorias_manual.json"
MISSING = "categorias_faltam.json"
API = "https://en.wikipedia.org/w/api.php"
UA = "Beyond100-bot/1.0 (https://beyond100tennis.com; contact via site)"
MONTHS = {m: i + 1 for i, m in enumerate("january february march april may june july august september october november december".split())}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})
CHALL = {50, 75, 100, 125, 175}
WTA = {250, 500, 1000}
# páginas por ano: (título, tipo). tipo m = Challenger masculino, w = WTA Tour
PAGES = [("{y} ATP Challenger Tour", "m"), ("{y} WTA Tour", "w"), ("{y} ATP Tour", "a")]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(r"\s+\d+\s*$", "", s.strip())
    return re.sub(r"[^a-z]+", " ", s).strip()


def get_html(title):
    r = requests.get(API, params={"action": "parse", "page": title, "prop": "text", "format": "json", "redirects": 1},
                     headers={"User-Agent": UA}, timeout=40)
    r.raise_for_status()
    j = r.json()
    if "error" in j:
        raise RuntimeError(j["error"].get("info", "erro"))
    return j["parse"]["text"]["*"]


def parse_date(txt, year):
    """'January 5', '5 January', 'Jan 5–11', '5 Jan' -> date ou None."""
    t = re.sub(r"\[.*?\]", "", txt or "").replace("–", "-").replace("—", "-")
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2})\b", t)
    if m and m.group(1).lower() in MONTHS:
        mon, day = MONTHS[m.group(1).lower()], int(m.group(2))
    else:
        m = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\b", t)
        if not (m and m.group(2).lower() in MONTHS):
            return None
        mon, day = MONTHS[m.group(2).lower()], int(m.group(1))
    try:
        return datetime.date(year, mon, day)
    except ValueError:
        return None


def expand(table):
    """Tabela HTML -> lista de linhas de texto, respeitando rowspan/colspan."""
    rows, pending = [], {}
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"], recursive=False)
        out, ci = [], 0
        it = iter(cells)
        cell = next(it, None)
        while cell is not None or ci in pending:
            if ci in pending:
                txt, left = pending[ci]
                out.append(txt)
                if left <= 1:
                    del pending[ci]
                else:
                    pending[ci] = (txt, left - 1)
                ci += 1
                continue
            txt = " ".join(cell.get_text(" ", strip=True).split())
            rs, cs = int(re.sub(r"\D", "", cell.get("rowspan", "1")) or 1), int(re.sub(r"\D", "", cell.get("colspan", "1")) or 1)
            for _ in range(cs):
                out.append(txt)
                if rs > 1:
                    pending[ci] = (txt, rs - 1)
                ci += 1
            cell = next(it, None)
        rows.append(out)
    return rows


def col_index(header, *keys):
    for i, h in enumerate(header):
        hl = h.lower()
        if any(k in hl for k in keys):
            return i
    return None


CAT_RE = {
    "m": re.compile(r"Challenger\s*(50|75|100|125|175)\b", re.I),
    "w": re.compile(r"WTA\s*(?:Tour\s*)?(?:Masters\s*)?(250|500|1000|125)\b", re.I),
    "a": re.compile(r"(?:ATP\s*(?:Tour\s*)?(?:Masters\s*)?|Masters\s*)(250|500|1000)\b", re.I),
}
LABEL = {"m": "Challenger {}", "w": "WTA {}", "a": "ATP {}"}
SURF = re.compile(r"\b(Hard|Clay|Grass|Carpet)\b", re.I)
DATE_PREFIX = re.compile(r"^\s*((?:[A-Za-z]{3,9}\.?\s+\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9})(?:\s*[-\u2013]\s*\d{1,2})?)\s*:?\s*")


def parse_page(html, year, kind):
    """Páginas de calendário da Wikipédia: tabelas com colunas 'Week of | Tournament | Champions…'. A categoria vem em texto dentro
    da célula do torneio ('Hard – Challenger 125 – 32S/24Q/16D'); a data da semana pode estar numa célula própria ou como prefixo ('January 5:').
    A chave guarda o texto antes da vírgula (nome + cidade); o matching no site aceita a cidade em qualquer parte dessa chave."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    entries, seen = [], set()
    for tb in soup.find_all("table"):
        rows = expand(tb)
        if len(rows) < 3:
            continue
        header = next((r for r in rows[:3] if col_index(r, "tournament") is not None), None)
        if header is None:
            continue
        ti, wi = col_index(header, "tournament"), col_index(header, "week", "date")
        last = None
        for r in rows[rows.index(header) + 1:]:
            if ti >= len(r):
                continue
            cell = r[ti]
            d = parse_date(r[wi], year) if (wi is not None and wi < len(r) and wi != ti) else None
            m = DATE_PREFIX.match(cell)
            if m and parse_date(m.group(1), year):
                d = d or parse_date(m.group(1), year)
                cell = cell[m.end():]
            d = d or last
            if d:
                last = d
            cm = CAT_RE[kind].search(cell)
            if not (d and cm):
                continue
            if re.search(r"cancel|postpon", cell, re.I):
                continue
            pre = SURF.split(cell)[0]
            key = norm(pre.split(",")[0])
            if not key:
                continue
            label = LABEL[kind].format(cm.group(1))
            if (key, d.isoformat(), label) in seen:
                continue
            seen.add((key, d.isoformat(), label))
            entries.append({"city": key, "start": d.isoformat(), "label": label, "g": "m" if kind == "a" else kind,
                            **({"days": 14} if label.endswith("1000") and kind in ("w", "a") else {})})
    return entries


def run(years, dry=False):
    old = []
    try:
        old = json.load(open(FILE, encoding="utf-8"))
    except (OSError, ValueError):
        pass
    keep = list(old)
    changed = False
    for y in years:
        for tpl, kind in PAGES:
            title = tpl.format(y=y)
            try:
                new = parse_page(get_html(title), y, kind)
            except Exception as e:
                print(f"AVISO {title}: não consegui ler ({e}); mantenho a lista anterior.")
                continue
            lo = 100 if kind == "m" else 20
            if not new:
                try:
                    from bs4 import BeautifulSoup
                    for tb in BeautifulSoup(get_html(title), "html.parser").find_all("table")[:6]:
                        rr = expand(tb)
                        print("  tabela:", rr[0][:8] if rr else "-", "|", (rr[1][:4] if len(rr) > 1 else ""))
                except Exception:
                    pass
            if len(new) < lo:
                print(f"AVISO {title}: só {len(new)} torneios reconhecidos (mínimo {lo}); mantenho a lista anterior.")
                continue
            ydate = f"{y}-"
            same = lambda e: (e.get("g", "m") == ("m" if kind == "a" else kind) and e["start"].startswith(ydate)
                              and e["label"].startswith({"m": "Challenger", "w": "WTA", "a": "ATP"}[kind]))
            before = [e for e in keep if same(e)]
            keep = [e for e in keep if not same(e)] + new
            print(f"{title}: {len(new)} torneios (antes {len(before)}).")
            changed = changed or sorted(map(json.dumps, before)) != sorted(map(json.dumps, new))
    if changed and not dry:
        keep.sort(key=lambda e: (e["start"], e["city"]))
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(keep, f, indent=0, ensure_ascii=False)
        print(f"{FILE} atualizado ({len(keep)} entradas).")
    elif not changed:
        print("Sem alterações.")
    return keep


def validate():
    """Torneios dos últimos 14 dias sem categoria -> categorias_faltam.json."""
    sys.path.insert(0, ".")
    import webapp
    try:
        res = json.load(open("results.json", encoding="utf-8"))
    except (OSError, ValueError):
        return
    lim = (datetime.date.today() - datetime.timedelta(days=14)).isoformat()
    miss = {}
    for r in res:
        if (r.get("date") or "") < lim:
            continue
        g, k, lv, tag = webapp.classify(r)
        if (lv == "challenger" and tag == "Challenger") or (lv == "tour" and tag in ("WTA", "ATP")):
            key = webapp.base_tournament(r.get("tournament", ""))
            miss.setdefault(key, {"tournament": key, "date": r["date"], "gender": g, "tour": r.get("tour")})
    out = sorted(miss.values(), key=lambda x: x["date"])
    with open(MISSING, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    for m in out:
        print(f"SEM CATEGORIA: {m['tournament']} ({m['date']}) — acrescenta-o no admin (categorias_manual.json).")
    if not out:
        print("Todos os torneios recentes têm categoria.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    ys = [int(x) for x in a.years.split(",") if x.strip()] or [datetime.date.today().year, datetime.date.today().year + 1]
    run(ys, a.dry)
    validate()
