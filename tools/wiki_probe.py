import json, re, urllib.request, html
def get(page):
    u = f"https://en.wikipedia.org/w/api.php?action=parse&page={page}&prop=text&format=json&formatversion=2"
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Beyond100Bot/1.0 (beyond100tennis.com)"}), timeout=40) as r:
        return json.load(r)["parse"]["text"]
def clean(seg):
    seg = re.sub(r'<span class="flagicon">.*?</span>', "[F]", seg, flags=re.S)
    seg = re.sub(r'\s(style|class|data-sort-value|href)="[^"]*"', "", seg)
    seg = re.sub(r"<sup.*?</sup>", "", seg, flags=re.S)
    return seg
for page in ("2026_ATP_Tour", "2026_WTA_Tour"):
    t = get(page)
    for anchor, n in (("Titles_information", 3500), ("Singles", 3000)):
        i = t.find(f'id="{anchor}"')
        print("=====", page, anchor)
        print(re.sub(r"<[^>]+>", " ", clean(t[i:i + n])).replace("\n\n", "\n")[:2500])
