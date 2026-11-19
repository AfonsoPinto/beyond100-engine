import json, re, urllib.request, html
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Beyond100Bot/1.0 (beyond100tennis.com)"}), timeout=40) as r:
        return json.load(r)
for page in ("2026_ATP_Tour", "2026_WTA_Tour"):
    d = get(f"https://en.wikipedia.org/w/api.php?action=parse&page={page}&prop=text|sections&format=json&formatversion=2")
    t = d["parse"]["text"]
    secs = [s["line"] for s in d["parse"]["sections"]]
    print(page, "secções:", secs[:40])
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", t, re.S):
        hdr = re.findall(r"<th[^>]*>(.*?)</th>", m.group(1), re.S)[:10]
        hdr = [re.sub(r"<[^>]+>", "", html.unescape(h)).strip() for h in hdr]
        if any("Total" in h for h in hdr) or any("Player" in h for h in hdr):
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S)
            print("  tabela:", hdr, "linhas:", len(rows))
            for r in rows[1:4]:
                cells = [re.sub(r"<[^>]+>", "", html.unescape(c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
                print("    ", cells[:10])
