"""Avisa os motores com IndexNow (Bing, Yandex, Seznam, Naver) das páginas que mudaram hoje. O Google não usa IndexNow: lê o sitemap.
Corre depois do deploy. Nunca falha o workflow."""
import json
import sys

import requests

import result_card as rc

import time
_t = time.gmtime()
if "--force" not in sys.argv and not (_t.tm_hour in (8, 14, 20) and _t.tm_min < 30):
    print("IndexNow: só às 08h, 14h e 20h UTC.")
    sys.exit(0)
try:
    urls = [rc.clean_url(u) for u in json.load(open("indexnow_urls.json", encoding="utf-8"))][:9000]   # endereço final (sem .html)
except Exception:
    urls = []
if not urls:
    print("IndexNow: nada para avisar.")
    sys.exit(0)
host = rc.SITE_BASE.split("//", 1)[1].rstrip("/")
try:
    r = requests.post("https://api.indexnow.org/indexnow", json={"host": host, "key": rc.INDEXNOW_KEY,
                      "keyLocation": f"{rc.SITE_BASE}/{rc.INDEXNOW_KEY}.txt", "urlList": urls}, timeout=30)
    print(f"IndexNow: {len(urls)} páginas -> {r.status_code}")
except Exception as e:
    print("IndexNow: erro", type(e).__name__)
