"""Links internos sem '.html' (5/11/2026): a Cloudflare redireciona /x.html para /x (308) e /pasta/index.html para /pasta/.
Ligar já ao endereço final poupa um redirecionamento por link ao Google e ao visitante. Corre no fim, sobre a pasta do site.
Só mexe em href="..." de links internos (relativos ou do próprio domínio); nada em scripts, imagens ou ficheiros de dados."""
import os
import re
import sys

SITE = (os.environ.get("SITE_URL") or "https://beyond100tennis.com").rstrip("/")
RX = re.compile(r'href="((?:' + re.escape(SITE) + r')?(?![a-z][a-z0-9+.-]*:|//|#)[^"#?]*?)\.html((?:[?#][^"]*)?)"')


def fix(m):
    path, tail = m.group(1), m.group(2)
    if path == "index" or path.endswith("/index"):
        path = path[:-5] or "./"
    return f'href="{path}{tail}"'


def main(root):
    n_files = n_links = 0
    for d, _, fs in os.walk(root):
        for fn in fs:
            if not fn.endswith(".html"):
                continue
            p = os.path.join(d, fn)
            with open(p, encoding="utf-8", errors="surrogateescape") as f:
                s = f.read()
            new, k = RX.subn(fix, s)
            if k:
                with open(p, "w", encoding="utf-8", errors="surrogateescape") as f:
                    f.write(new)
                n_files += 1
                n_links += k
    print(f"Links limpos: {n_links} links em {n_files} páginas.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "site")
