import json, re, urllib.request
def get(page):
    u = f"https://en.wikipedia.org/w/api.php?action=parse&page={page}&prop=text&format=json&formatversion=2"
    with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Beyond100Bot/1.0 (beyond100tennis.com)"}), timeout=40) as r:
        return json.load(r)["parse"]["text"]
t = get("2026_WTA_Tour")
i = t.find("Titles_won_by_player")
seg = t[i:i + 9000]
seg = re.sub(r'<span class="flagicon">.*?</span>', "[F]", seg, flags=re.S)
seg = re.sub(r'\s(style|class|data-sort-value)="[^"]*"', "", seg)
print(seg[:6000])
