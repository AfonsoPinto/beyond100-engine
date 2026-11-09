"""Publicação automática no Instagram, em dois passos:

  python publisher.py prepare   -> converte os cartões novos (out/post/*.png) em JPEG público (posts/) e põe-nos na fila
  python publisher.py send      -> envia a fila para o Instagram (só se PUBLISH_AUTO=1)

Duas maneiras de publicar (escolhe-se com PUBLISH_BACKEND):
  webhook : chama um webhook (Make, Zapier, n8n...) com {image_url, caption, id}; não precisa de app Meta própria
  graph   : API oficial do Instagram (precisa de IG_USER_ID e IG_ACCESS_TOKEN)

Segurança: sem PUBLISH_AUTO=1 não se envia nada; os posts ficam na fila (posts.json) e nos "Artifacts".
"""
import json
import os
import shutil
import sys
import time

from PIL import Image

POSTS_FILE = "posts.json"
POSTS_DIR = "posts"
CAROUSELS_FILE = "carousels.json"
STORIES_FILE = "stories.json"
SITE_URL = (os.environ.get("IMAGE_BASE_URL") or os.environ.get("SITE_URL") or "https://beyond100tennis.com").rstrip("/")
# IMAGE_BASE_URL (opcional): de onde o Instagram vai buscar as imagens, ex. https://beyond100.pages.dev (fora das regras de bots do domínio)
KEEP_DAYS = 30


def _load():
    try:
        with open(POSTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(posts):
    with open(POSTS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)


def prepare(out_dir="out"):
    src = os.path.join(out_dir, "post")
    posts = _load()
    os.makedirs(POSTS_DIR, exist_ok=True)
    n = 0
    for day, entries in posts.items():
        for e in entries:
            if e.get("image"):
                continue
            png = os.path.join(src, e["file"])
            if not os.path.exists(png):
                continue                       # entrada de uma execução anterior que já foi tratada
            stem = os.path.splitext(e["file"])[0] + "-" + day
            Image.open(png).convert("RGB").save(os.path.join(POSTS_DIR, stem + ".jpg"), quality=92)
            cap = os.path.splitext(png)[0] + ".txt"
            if os.path.exists(cap):
                shutil.copy(cap, os.path.join(POSTS_DIR, stem + ".txt"))
            fj = os.path.splitext(png)[0] + ".facts.json"
            if os.path.exists(fj):
                shutil.copy(fj, os.path.join(POSTS_DIR, stem + ".facts.json"))
            tg = os.path.splitext(png)[0] + ".tag"
            if os.path.exists(tg):
                shutil.copy(tg, os.path.join(POSTS_DIR, stem + ".tag"))
            e["image"], e["sent"] = stem + ".jpg", False
            n += 1
    # limpa ficheiros com mais de KEEP_DAYS dias
    cutoff = time.time() - KEEP_DAYS * 86400
    for fn in os.listdir(POSTS_DIR):
        fp = os.path.join(POSTS_DIR, fn)
        if os.path.getmtime(fp) < cutoff:
            os.remove(fp)
    _save(posts)
    print(f"Fila: {n} posts novos preparados.")


def _caption(e):
    fp = os.path.join(POSTS_DIR, os.path.splitext(e["image"])[0] + ".txt")
    fj = os.path.join(POSTS_DIR, os.path.splitext(e["image"])[0] + ".facts.json")
    if not os.path.exists(fp) and os.path.exists(fj):          # legenda adiada: escrita só agora, no momento de publicar
        try:
            import captions
            txt = captions.caption_from_pending(fj)
            if txt:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(txt)
        except Exception as ex:
            print("Legenda adiada falhou:", type(ex).__name__, ex)
    try:
        with open(fp, encoding="utf-8") as f:
            return f.read().strip()[:2200]
    except OSError:
        return ""


def _tag(e):
    """Perfis a marcar na foto (ficheiro .tag: 1.ª linha jogador, 2.ª torneio) -> (jogador, torneio)."""
    fp = os.path.join(POSTS_DIR, os.path.splitext(e["image"])[0] + ".tag")
    try:
        with open(fp, encoding="utf-8") as f:
            ls = (f.read().split("\n") + ["", ""])[:2]
        return ls[0].strip().lstrip("@"), ls[1].strip().lstrip("@")
    except OSError:
        return "", ""


def _user_tags(tag):
    """JSON no formato da API do Instagram: jogador no centro da foto, torneio no topo."""
    pl, tn = tag if isinstance(tag, tuple) else (tag, "")
    out = []
    if pl:
        out.append({"username": pl, "x": 0.5, "y": 0.45})
    if tn:
        out.append({"username": tn, "x": 0.5, "y": 0.12})
    return json.dumps(out) if out else ""


def _image_ready(url, wait_s=150):
    """O Instagram vai buscar a imagem ao site: só envia quando o URL já devolve mesmo um JPEG (o deploy do Cloudflare Pages
    pode demorar uns segundos; antes disso o Instagram recebe uma página HTML e dá o erro 'image format not supported')."""
    import requests
    t0, last = time.time(), ""
    while True:
        try:
            r = requests.get(url, timeout=20, headers={"Cache-Control": "no-cache"})
            if r.status_code == 200 and r.content[:3] == b"\xff\xd8\xff" and len(r.content) < 8 * 1024 * 1024:
                return True
            last = f"{r.status_code} {r.headers.get('content-type', '')}"
        except Exception as ex:
            last = type(ex).__name__
        if time.time() - t0 > wait_s:
            print(f"Imagem ainda não disponível ({last}): {url}")
            return False
        time.sleep(10)


def _send_webhook(url, image_url, caption, pid, tag=("", "")):
    import requests
    body = {"image_url": image_url, "caption": caption, "id": pid, "tag_username": tag[0], "tag_tournament": tag[1], "user_tags": _user_tags(tag)}
    r = requests.post(url, json=body, timeout=30)
    r.raise_for_status()


def _graph_host():
    """graph.instagram.com = 'Instagram API com login do Instagram' (sem página de Facebook); graph.facebook.com = login pelo Facebook."""
    return (os.environ.get("GRAPH_HOST") or "graph.facebook.com").strip()


def _gcheck(r):
    """Como raise_for_status, mas mostra no log a resposta da Meta (sem o token), para se perceber o erro."""
    if r.status_code >= 400:
        print("Instagram API:", r.status_code, (r.text or "")[:400].replace("\n", " "))
    r.raise_for_status()


def _send_graph(image_url, caption, tag=("", "")):
    import requests
    ver = os.environ.get("GRAPH_VERSION", "v21.0")
    uid, tok = os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"]
    base = f"https://{_graph_host()}/{ver}"
    data = {"image_url": image_url, "caption": caption, "access_token": tok}
    if _user_tags(tag):
        data["user_tags"] = _user_tags(tag)
    r = requests.post(f"{base}/{uid}/media", data=data, timeout=60)
    _gcheck(r)
    cid = r.json()["id"]
    for _ in range(6):                          # o Instagram precisa de uns segundos para processar a imagem
        st = requests.get(f"{base}/{cid}", params={"fields": "status_code", "access_token": tok}, timeout=30).json()
        if st.get("status_code") in (None, "FINISHED"):
            break
        time.sleep(5)
    r = requests.post(f"{base}/{uid}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60)
    _gcheck(r)
    _first_comment(r.json().get("id"), caption, tok)


def _first_comment(media_id, caption, tok):
    """Comenta logo a seguir a pergunta da legenda (puxa respostas). Só com a API oficial; FIRST_COMMENT=0 desliga."""
    if os.environ.get("FIRST_COMMENT", "1").strip() in ("0", "no", "off", "false") or not media_id:
        return
    q = next((ln.strip() for ln in (caption or "").split("\n") if ln.strip().endswith("?") and not ln.strip().startswith("#")), "")
    if not q:
        return
    import requests
    try:
        r = requests.post(f"{_graph_base()}/{media_id}/comments", data={"message": q[:300], "access_token": tok}, timeout=30)
        print("Primeiro comentário:", "ok" if r.status_code < 400 else f"falhou ({r.status_code})")
    except Exception as e:
        print("Primeiro comentário: erro", type(e).__name__)


def _graph_base():
    return f"https://{_graph_host()}/{os.environ.get('GRAPH_VERSION', 'v21.0')}"


def _graph_wait(cid, tok):
    import requests
    for _ in range(12):                          # o Instagram processa a imagem/vídeo em segundos
        st = requests.get(f"{_graph_base()}/{cid}", params={"fields": "status_code", "access_token": tok}, timeout=30).json()
        if st.get("status_code") in (None, "FINISHED"):
            return
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError("Instagram: " + str(st))
        time.sleep(5)


def _send_graph_carousel(urls, caption):
    """Carrossel pela API oficial: um contentor por imagem, um contentor CAROUSEL e a publicação."""
    import requests
    uid, tok = os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"]
    kids = []
    for u in urls[:10]:
        r = requests.post(f"{_graph_base()}/{uid}/media", data={"image_url": u, "is_carousel_item": "true", "access_token": tok}, timeout=60)
        _gcheck(r)
        kids.append(r.json()["id"])
    for k in kids:
        _graph_wait(k, tok)
    r = requests.post(f"{_graph_base()}/{uid}/media", data={"media_type": "CAROUSEL", "children": ",".join(kids),
                                                           "caption": caption, "access_token": tok}, timeout=60)
    _gcheck(r)
    cid = r.json()["id"]
    _graph_wait(cid, tok)
    r = requests.post(f"{_graph_base()}/{uid}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60)
    _gcheck(r)
    _first_comment(r.json().get("id"), caption, tok)


def _send_graph_story(url):
    import requests
    uid, tok = os.environ["IG_USER_ID"], os.environ["IG_ACCESS_TOKEN"]
    r = requests.post(f"{_graph_base()}/{uid}/media", data={"image_url": url, "media_type": "STORIES", "access_token": tok}, timeout=60)
    _gcheck(r)
    cid = r.json()["id"]
    _graph_wait(cid, tok)
    _gcheck(requests.post(f"{_graph_base()}/{uid}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60))


def _backend():
    return os.environ.get("PUBLISH_BACKEND", "webhook")


def _send_carousels():
    """Carrosséis (ex.: resumo semanal): webhook próprio com image_urls e image_1..image_10."""
    try:
        with open(CAROUSELS_FILE, encoding="utf-8") as f:
            queue = json.load(f)
    except (OSError, ValueError):
        return
    pending = [c for c in queue if not c.get("sent")]
    if not pending:
        return
    url = os.environ.get("MAKE_WEBHOOK_CAROUSEL_URL")
    if _backend() != "graph" and not url:
        print(f"{len(pending)} carrosséis na fila, mas falta MAKE_WEBHOOK_CAROUSEL_URL: nada enviado.")
        return
    import requests
    for c in pending:
        urls = [f"{SITE_URL}/posts/{n}" for n in c["images"]]
        if not all(_image_ready(u_, 60) for u_ in urls):
            continue
        body = {"id": c["id"], "caption": c["caption"][:2200], "image_urls": urls}
        body.update({f"image_{i}": u for i, u in enumerate(urls, 1)})
        try:
            if _backend() == "graph":
                _send_graph_carousel(urls, c["caption"][:2200])
            else:
                requests.post(url, json=body, timeout=30).raise_for_status()
        except Exception as ex:
            print(f"Carrossel {c['id']}: falhou ({type(ex).__name__}), tenta de novo mais tarde.")
            continue
        c["sent"], c["sent_at"] = True, time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        with open(CAROUSELS_FILE, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        print(f"Carrossel {c['id']}: enviado.")


def _send_stories():
    try:
        with open(STORIES_FILE, encoding="utf-8") as f:
            queue = json.load(f)
    except (OSError, ValueError):
        return
    today = time.strftime("%Y-%m-%d", time.gmtime())
    stale = [c for c in queue if not c.get("sent") and (c.get("created") or "")[:10] < today]
    for c in stale:                              # stories são do dia: as antigas nunca saem
        c["sent"], c["skipped"] = True, "stale"
    if stale:
        with open(STORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
    pending = [c for c in queue if not c.get("sent")]
    url = os.environ.get("MAKE_WEBHOOK_STORY_URL")
    if not pending:
        return
    if _backend() != "graph" and not url:
        print(f"{len(pending)} stories na fila, mas falta MAKE_WEBHOOK_STORY_URL: nada enviado.")
        return
    import requests
    for c in pending[:3]:                       # no máximo 3 por execução
        if not _image_ready(f"{SITE_URL}/posts/{c['image']}", 60):
            continue
        try:
            if _backend() == "graph":
                _send_graph_story(f"{SITE_URL}/posts/{c['image']}")
            else:
                requests.post(url, json={"id": c["id"], "image_url": f"{SITE_URL}/posts/{c['image']}"}, timeout=30).raise_for_status()
        except Exception as ex:
            print(f"Story {c['id']}: falhou ({type(ex).__name__}), tenta de novo mais tarde.")
            continue
        c["sent"], c["sent_at"] = True, time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        with open(STORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
        print(f"Story {c['id']}: enviado.")


def send():
    posts = _load()
    pending = [(d, e) for d, es in posts.items() for e in es if e.get("image") and not e.get("sent")]
    if os.environ.get("PUBLISH_AUTO") != "1":
        print(f"{len(pending)} posts na fila, mas PUBLISH_AUTO não está a 1: nada enviado.")
        return
    _send_carousels()
    _send_stories()
    if not pending:
        print("Fila vazia.")
        return
    backend = os.environ.get("PUBLISH_BACKEND", "webhook")
    limit = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 36 * 3600))
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Europe/Lisbon")
    env = lambda k, d: (os.environ.get(k) or "").strip() or d
    s_from, s_to = int(env("SEND_FROM", "8")), int(env("SEND_TO", "23"))
    gap_min, weak_from = int(env("SEND_GAP_MIN", "45")), int(env("SEND_WEAK_FROM", "20"))
    morning_until, morning_max = int(env("SEND_MORNING_UNTIL", "16")), int(env("SEND_MORNING_MAX", "2"))
    strong, exc = float(env("SEND_STRONG_SCORE", "8")), float(env("EXCEPTION_SCORE", "9"))
    morning_min = float(env("SEND_MORNING_MIN", "9"))
    max_day, extra = int(env("MAX_POSTS_PER_DAY", "3")), int(env("EXTRA_POSTS", "2"))
    now_l = datetime.fromisoformat(os.environ["SEND_TEST_NOW"]).replace(tzinfo=tz) if os.environ.get("SEND_TEST_NOW") else datetime.now(tz)
    in_window = s_from <= now_l.hour < s_to
    is_res = lambda e: str(e.get("id")).isdigit()
    is_prev = lambda e: str(e.get("id")).startswith("preview-")
    men_first = env("MEN_FIRST", "1") != "0"
    _gcache = {}

    def gender(e):                              # cartões antigos sem "gender": procura no arquivo de resultados
        if e.get("gender"):
            return e["gender"]
        if not _gcache:
            try:
                from result_card import load_results
                _gcache.update({r.get("id"): r.get("gender") for r in load_results()})
            except Exception:
                _gcache[None] = None
        return _gcache.get(e.get("id"))

    def prio(x):                                # MEN_FIRST=1: resultados masculinos primeiro; dentro de cada grupo, o maior interesse
        return ((1 if men_first and gender(x[1]) == "women" else 0), -(x[1].get("score") or 0))

    def sent_dt(e):
        try:
            return datetime.strptime(e["sent_at"], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)
        except (KeyError, ValueError):
            return None
    archived = set()                            # 9/11/2026: posts que o Afonso arquivou no Instagram não contam para o máximo do dia
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "archived_posts.txt"), encoding="utf-8") as f:
            archived = {ln.split("#")[0].strip() for ln in f if ln.split("#")[0].strip()}
    except OSError:
        pass
    sent = [(e, sent_dt(e)) for es in posts.values() for e in es if e.get("sent") and not e.get("skipped") and str(e.get("id")) not in archived]
    sent = [(e, t) for e, t in sent if t]
    res_today = sum(1 for e, t in sent if is_res(e) and t.date() == now_l.date())
    last = max([t for e, t in sent if not is_prev(e)], default=None)
    gap_ok = last is None or (now_l - last).total_seconds() >= gap_min * 60

    def send_one(d, e):
        url = f"{SITE_URL}/posts/{e['image']}"
        if not _image_ready(url):               # fica na fila e tenta na próxima execução
            return False
        try:
            if backend == "graph":
                _send_graph(url, _caption(e), _tag(e))
            else:
                _send_webhook(os.environ["MAKE_WEBHOOK_URL"], url, _caption(e), e.get("id"), _tag(e))
        except Exception as ex:                 # falhou: fica na fila para a próxima execução
            print(f"Post {e.get('id')}: falhou ({type(ex).__name__}), tenta de novo mais tarde.")
            return False
        e["sent"] = True
        e["sent_at"] = time.strftime("%Y-%m-%d %H:%M", time.gmtime())
        print(f"Post {e.get('id')}: enviado ({backend}).")
        _save(posts)
        return True

    # 9/11/2026 (pedido do Afonso): no máximo DAY_MAX_POSTS (3) por dia no feed, contando tudo (resultados, antevisões,
    # especiais e carrosséis), e que sejam os melhores do dia. Em vez de publicar à medida que os jogos acabam, há 3 horas de
    # publicação (POST_SLOTS, Lisboa: 13h, 18h, 21h); em cada uma sai o post com mais interesse na fila das últimas 24 h.
    # Um post excecional (SEND_NOW_SCORE, 12+: título, surpresa gigante) não espera pela hora, mas conta para os 3.
    day_max = int(env("DAY_MAX_POSTS", "3"))
    slots = sorted(int(x) for x in env("POST_SLOTS", "13,18,21").split(",") if x.strip().isdigit())
    now_score = float(env("SEND_NOW_SCORE", "12"))
    prev_score = float(env("PREVIEW_SCORE", "9"))
    other_score = float(env("SPECIAL_SCORE", "9"))
    for d, e in pending:                                          # antiguidade: resultados com mais de 24 h e antevisões com mais de 12 h não saem
        age = time.time() - (e.get("created") or 0) if e.get("created") else None
        old = d < limit or (age is not None and age > (12 if is_prev(e) else 24) * 3600)
        if old:
            e["sent"], e["skipped"] = True, "stale"
    _save(posts)
    pending = [(d, e) for d, e in pending if not e.get("sent")]
    if not pending:
        print("Fila vazia.")
        return
    try:
        with open(CAROUSELS_FILE, encoding="utf-8") as f:
            _car = json.load(f)
    except (OSError, ValueError):
        _car = []
    car_today = 0
    for c in _car:
        try:
            if c.get("sent") and datetime.strptime(c["sent_at"], "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("UTC")).astimezone(tz).date() == now_l.date():
                car_today += 1
        except (KeyError, ValueError, TypeError):
            pass
    sent_today = [e for e, t in sent if t.date() == now_l.date()]
    day_count = len(sent_today) + car_today
    # 9/11/2026: um 4.º post só para algo excecional (12+), no máximo 1 por dia e só se nenhum dos de hoje já era 12+
    exc_done = any(float(e.get("score") or 0) >= now_score for e in sent_today if is_res(e))
    best_pend = max((float(e.get("score") or 0) for _, e in pending if is_res(e)), default=0)
    cap = day_max + (1 if (best_pend >= now_score and not exc_done) else 0)
    if day_count >= cap:
        print(f"Já saíram {day_count} posts hoje (máximo {day_max}, +1 só para 12+): {len(pending)} esperam ou caducam.")
        return

    def value(e):
        if is_prev(e):
            return prev_score
        if not is_res(e):
            return float(e.get("score") or other_score)
        return float(e.get("score") or 0)
    # antevisões são antes do jogo: saem logo (dentro da janela), mas contam para o máximo do dia
    for d, e in [x for x in pending if is_prev(x[1])]:
        if in_window and day_count < day_max:
            print(f"Antevisão {e.get('id')}: sai já (antes do jogo), {day_count + 1}/{day_max} hoje.")
            if send_one(d, e):
                return
    pending = [x for x in pending if not is_prev(x[1])]
    if not pending:
        return
    order = sorted(pending, key=lambda x: (-value(x[1]), prio(x)[0], x[1].get("created") or 0))
    d, e = order[0]
    v = value(e)
    slots_open = sum(1 for h in slots if now_l.hour >= h)
    if v >= now_score and gap_ok and in_window:
        print(f"Post {e.get('id')} é excecional ({v:g}): sai já ({day_count + 1}/{cap} hoje).")
        send_one(d, e)
        return
    if not in_window:
        print(f"Fora da janela de publicação ({s_from}h-{s_to}h Lisboa): {len(pending)} posts esperam.")
        return
    if day_count >= day_max:
        print(f"Já saíram {day_count} posts hoje (máximo {day_max}); só um 12+ pode ainda sair.")
        return
    # 9/11/2026: fasquia por hora (SLOT_MIN, alinhada com POST_SLOTS): 13h só 10+, 18h só 9+, 21h o melhor que houver.
    # Se a hora cedo não tiver nada à altura, o lugar fica guardado para mais tarde (sai depois, com a fasquia dessa hora).
    mins = [float(x) for x in env("SLOT_MIN", "10,9,0").split(",") if x.strip()]
    cur = max((k for k, h in enumerate(slots) if now_l.hour >= h), default=None)
    bar = mins[cur] if cur is not None and cur < len(mins) else 0
    if slots_open and day_count < slots_open and v < bar:
        print(f"Hora de publicação ({slots[cur]}h), mas o melhor da fila ({e.get('id')}, {v:g}) não chega a {bar:g}: o lugar fica para mais tarde.")
        return
    if day_count >= slots_open:
        nxt = next((h for h in slots if h > now_l.hour), None)
        print(f"{day_count} publicados hoje; próxima hora de publicação: {f'{nxt}h' if nxt else 'amanhã'}. "
              f"Melhor na fila: {e.get('id')} ({v:g}).")
        return
    if not gap_ok:
        print(f"Último post há menos de {gap_min} min: espera pela próxima execução.")
        return
    print(f"Hora de publicação: sai o melhor da fila, {e.get('id')} ({v:g}), {day_count + 1}/{day_max} hoje.")
    send_one(d, e)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "prepare":
        prepare(sys.argv[2] if len(sys.argv) > 2 else "out")
    elif cmd == "send":
        send()
    else:
        sys.exit("Uso: python publisher.py prepare|send")
