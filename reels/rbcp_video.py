"""Reels de padel com o vídeo oficial "Social Newscut Clean" do Red Bull Content Pool (19/11/2026, Afonso).

O vídeo é pedido no browser (tarefa de segunda) e o link chega a rbcp/video_inbox.json. Aqui (no GitHub):
descarrega o vídeo, põe por cima os nossos grafismos (placar das finais, marca, crédito; Python/ffmpeg, SEM IA —
regra "AI Prohibition" do RBCP) e junta-o aos Reels (reels.json, kind "rbcp"), que saem pelo publicador normal
(1 Reel por dia por conta; este tem prioridade). Legenda só com factos (sem IA).
Crédito obrigatório dos vídeos (termos 4.6 a): "© Red Bull Media House"; no Instagram marcar @redbull (4.6 c).

  python -m reels.rbcp_video            faz os Reels dos vídeos novos
  python -m reels.rbcp_video test out.mp4   vídeo de teste (só cores) para ver o grafismo"""
import datetime as dt
import json
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
NAVY, DEEP, CREAM, VOLT, SOFT = (12, 46, 74), (8, 26, 44), (247, 242, 230), (217, 242, 61), (169, 192, 214)
FD = "fonts"
CREDIT = "© Red Bull Media House"

FINALS = {}                                                        # preenchido por cada vídeo (ver finals_of)
INBOX = os.path.join("rbcp", "video_inbox.json")
TAGS = "@redbull @premierpadel"


def f(name, size):
    for n in (name, "Inter-Bold.otf"):
        p = os.path.join(FD, n)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.truetype("DejaVuSans-Bold.ttf", size)


def fit(d, text, name, size, max_w):
    while size > 20 and d.textlength(text, font=f(name, size)) > max_w:
        size -= 2
    return f(name, size)


def pill(d, x, y, text, fill, fg, size=30):
    ft = f("Inter-ExtraBold.otf", size)
    tw = d.textlength(text, font=ft)
    d.rounded_rectangle([x, y, x + tw + 40, y + size + 26], radius=(size + 26) // 2, fill=fill)
    d.text((x + 20 + tw / 2, y + (size + 26) / 2), text, font=ft, fill=fg, anchor="mm")
    return x + tw + 40


def shade(img, y0, y1, a0, a1):
    d = ImageDraw.Draw(img)
    for y in range(y0, y1):
        d.line([(0, y), (W, y)], fill=DEEP + (int(a0 + (a1 - a0) * (y - y0) / max(1, y1 - y0)),))


def brand_layer():
    """Sempre visível: marca em cima, crédito em baixo (termos 4.6 a: crédito junto ao conteúdo)."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shade(im, 180, 420, 150, 0)
    shade(im, H - 560, H - 380, 0, 150)
    d = ImageDraw.Draw(im)
    TY = 262                                                       # abaixo do nome da conta e do "Áudio original" do Instagram
    x = pill(d, 60, TY, "BEYOND PADEL", CREAM, NAVY, 30)
    pill(d, x + 14, TY, f"{FINALS['tournament']} · {FINALS.get('tag', 'FINALS')}", (0, 0, 0, 0), CREAM, 30)
    d.rounded_rectangle([x + 14, TY, x + 14 + d.textlength(f"{FINALS['tournament']} · {FINALS.get('tag', 'FINALS')}", font=f("Inter-ExtraBold.otf", 30)) + 40, TY + 56],
                        radius=28, outline=CREAM, width=3)
    BY = H - 440                                                   # acima da legenda e dos botões do Instagram
    d.text((W - 160, BY), CREDIT, font=f("Inter-SemiBold.otf", 28), fill=SOFT, anchor="rm")
    d.text((60, BY), "@beyond100.padel", font=f("Inter-Bold.otf", 30), fill=CREAM, anchor="lm")
    return im


def score_layer(fin):
    """Placar ao estilo de transmissão (diferente dos cartões dos posts): uma final de cada vez, a subir de baixo."""
    im = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, x1 = 48, W - 150                                           # não passa por baixo dos botões do Instagram (direita)
    d.rounded_rectangle([x0, 0, x0 + 330, 64], radius=18, fill=VOLT)
    d.rectangle([x0, 40, x0 + 330, 64], fill=VOLT)
    d.text((x0 + 24, 32), f"{fin['label']}'S FINAL", font=f("Inter-ExtraBold.otf", 30), fill=NAVY, anchor="lm")
    d.rounded_rectangle([x0, 64, x1, 344], radius=22, fill=DEEP + (235,))
    d.rectangle([x0, 64, x0 + 40, 100], fill=DEEP + (235,))
    n = len(fin["sets"])
    bw, gap = 96, 10
    bx = x1 - 24 - n * bw - (n - 1) * gap
    rows = [(fin["w"], [s.split("-")[0] for s in fin["sets"]], True), (fin["l"].upper(), [s.split("-")[1] for s in fin["sets"]], False)]
    for r, (name, games, win) in enumerate(rows):
        cy = 134 + r * 140
        if r:
            d.line([(x0 + 24, cy - 70), (x1 - 24, cy - 70)], fill=(36, 80, 122, 255), width=2)
        if win:
            d.polygon([(x0 + 26, cy - 14), (x0 + 26, cy + 14), (x0 + 46, cy)], fill=VOLT)
        nf = fit(d, name, "InterDisplay-Black.otf" if win else "Inter-Bold.otf", 54 if win else 44, bx - x0 - 90)
        d.text((x0 + 64, cy), name, font=nf, fill=CREAM if win else SOFT, anchor="lm")
        for i, g in enumerate(games):
            gx = bx + i * (bw + gap)
            other = rows[1 - r][1][i]
            won = int(g) > int(other)
            d.rounded_rectangle([gx, cy - 46, gx + bw, cy + 46], radius=14, fill=VOLT if won else (36, 80, 122, 255))
            d.text((gx + bw / 2, cy), g, font=f("InterDisplay-Black.otf", 56), fill=NAVY if won else CREAM, anchor="mm")
    tx = f"{FINALS['tournament']} · {FINALS['date']}"
    tf = f("Inter-Bold.otf", 26)
    tw = d.textlength(tx, font=tf)
    d.rounded_rectangle([x0 + 346, 12, x0 + 346 + tw + 36, 58], radius=23, fill=DEEP + (235,))
    d.text((x0 + 364, 35), tx, font=tf, fill=CREAM, anchor="lm")
    return im


def end_layer():
    im = Image.new("RGBA", (W, H), DEEP + (235,))
    d = ImageDraw.Draw(im)
    d.text((W / 2, 820), "BEYOND PADEL", font=f("InterDisplay-Black.otf", 92), fill=CREAM, anchor="mm")
    d.text((W / 2, 930), "Every draw, not just the finals", font=f("Inter-SemiBold.otf", 40), fill=SOFT, anchor="mm")
    pill(d, W / 2 - 230, 1010, "Follow @beyond100.padel", VOLT, NAVY, 34)
    d.text((W / 2, 1220), CREDIT, font=f("Inter-SemiBold.otf", 30), fill=SOFT, anchor="mm")
    return im


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", p],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 30)


def render(src, dst):
    os.makedirs("_reel", exist_ok=True)
    brand_layer().save("_reel/brand.png")
    for i, fin in enumerate(FINALS["finals"][:2]):
        score_layer(fin).save(f"_reel/score{i}.png")
    if len(FINALS["finals"]) < 2:
        Image.new("RGBA", (W, 420), (0, 0, 0, 0)).save("_reel/score1.png")
    end_layer().save("_reel/end.png")
    T = dur(src)
    e0 = max(0.0, T - 3.0)
    y0 = 1000                                                      # placar: entra a subir, fica, sai a descer (acima da zona da legenda)
    def mv(a, b):
        return (f"if(lt(t,{a}+0.35),{H}-(t-{a})/0.35*({H}-{y0}),if(gt(t,{b}-0.3),{y0}+(t-({b}-0.3))/0.3*({H}-{y0}),{y0}))")
    fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1[v0];"
          f"[v0][1:v]overlay=0:0:enable='lt(t,{e0})'[v1];"
          f"[v1][2:v]overlay=0:'{mv(0.4, 2.6)}':enable='between(t,0.4,2.6)'[v2];"
          f"[v2][3:v]overlay=0:'{mv(2.7, 4.9)}':enable='between(t,2.7,4.9)'[v3];"
          f"[4:v]format=rgba,fade=t=in:st={e0}:d=0.4:alpha=1[e];[v3][e]overlay=0:0:enable='gte(t,{e0})'[v]")
    tmp = dst + ".part.mp4"
    # 19/11/2026: qualidade medida (SSIM contra o original): 2 passagens "slow" a ~6 Mb/s = 0,991 vs 0,987 antes,
    # mantendo os 25 fps do original (passar a 30 fps repetia fotogramas) e cabendo nos 25 MB do site.
    kbps = int(min(6500, max(2500, 22e6 * 8 / max(T, 1) / 1000 - 192)))
    common = ["-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-profile:v", "high", "-pix_fmt", "yuv420p",
              "-b:v", f"{kbps}k", "-maxrate", f"{int(kbps * 1.5)}k", "-bufsize", f"{kbps * 2}k", "-g", "50", "-t", str(T)]
    inputs = ["-i", src,
              "-loop", "1", "-t", str(T), "-i", "_reel/brand.png",
              "-loop", "1", "-t", str(T), "-i", "_reel/score0.png",
              "-loop", "1", "-t", str(T), "-i", "_reel/score1.png",
              "-loop", "1", "-t", str(T), "-i", "_reel/end.png"]
    log = os.path.join("_reel", "x264")
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, *common, "-pass", "1", "-passlogfile", log, "-an", "-f", "null", os.devnull], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, *common, "-pass", "2", "-passlogfile", log,
                    "-map", "0:a?", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-15:TP=-1.5",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, dst)
    return T


def finals_of(event, day=None):
    """As finais (homens primeiro) do torneio Premier deste evento do RBCP, ou None se ainda não acabaram.
    Se houver dois torneios na mesma cidade, fica o que acabou mais perto (antes) do dia do pedido."""
    from padel import rbcp
    D = "padel/data"
    tours = rbcp._load(f"{D}/tournaments.json", {})
    day = day or dt.date.today().isoformat()
    cands = [(tid, t) for tid, t in tours.items() if rbcp.same_event({"event": event}, t.get("name"))
             and (t.get("start_date") or "") <= day and set(re.findall(r"20\d\d", event)) <= set(re.findall(r"20\d\d", (t.get("name") or "") + (t.get("end_date") or "")))]
    for tid, t in sorted(cands, key=lambda x: x[1].get("end_date") or "", reverse=True):
        ms = rbcp._load(f"{D}/matches/{tid}.json", [])
        fins = []
        for m in sorted([m for m in ms if m.get("round") == 1 and (m.get("draw") or "main") == "main" and m.get("winner") in ("team_1", "team_2")],
                        key=lambda m: m.get("category") != "men"):
            w = m["winner"]; l = "team_2" if w == "team_1" else "team_1"
            sn = lambda ps: " / ".join((p.get("short_name") or (p.get("name") or "?").split()[-1]) for p in ps)
            sets = [f"{re.sub(r'[^0-9].*', '', str(s.get(w)))}-{re.sub(r'[^0-9].*', '', str(s.get(l)))}" for s in m.get("score") or []]
            fins.append({"label": "MEN" if m.get("category") == "men" else "WOMEN", "w": sn(m["players"][w]).upper(), "l": sn(m["players"][l]),
                         "sets": sets, "date": m.get("played_at"), "full": [" / ".join(p.get("name") for p in m["players"][w]), " ".join(sets)]})
        if not fins:
            return None
        name = re.sub(r"\s*20\d\d$", "", t.get("name") or "").strip()
        try:
            date = dt.date.fromisoformat(max(f["date"] for f in fins)).strftime("%d %b %Y").upper()
        except (TypeError, ValueError):
            date = ""
        return {"tid": tid, "tournament": name.upper(), "name": name, "date": date, "finals": fins}
    return None


def caption(F):
    lines = [f"{F['name']} champions 🏆"]
    for x in F["finals"]:
        lines.append(f"{x['label'].title()}: {x['full'][0]} · {x['full'][1]}")
    lines += [f"🎥 © Red Bull Media House · {TAGS}", "Follow @beyond100.padel for every draw, not just the finals.", "",
              "#padel #BeyondPadel #PremierPadel"]
    return "\n".join(lines)


def make():
    """Faz os Reels dos vídeos pedidos (rbcp/video_inbox.json, que o motor nunca reescreve; o tratado fica em rbcp/done.json)."""
    import requests
    from padel import rbcp
    from reels import make as rm
    items = rm_load_inbox()
    if not items:
        return
    st = rm.load()
    done = rbcp.done_load()
    todo = []
    for it in items:
        pid = re.sub(r"[^A-Za-z0-9-]", "", it.get("productId") or "")
        k = "V:" + pid
        if pid and f"rbcp-{pid}" not in st["done"] and not (done.get(k) or {}).get("ok") and (done.get(k) or {}).get("tries", 0) < 3:
            todo.append((pid, it))
    if not todo:
        return
    if not rm.ffmpeg_ok():                                          # corre antes do reels.make: instala o ffmpeg se faltar
        print("RBCP vídeo: ffmpeg indisponível, fica para a próxima."); return
    os.makedirs(rm.DIR, exist_ok=True)
    os.makedirs("_reel", exist_ok=True)
    for pid, it in todo:
        k, rid = "V:" + pid, f"rbcp-{pid}"
        url = rbcp.link(it)
        F = finals_of(it.get("event") or "", it.get("downloaded"))
        if F is None and url:
            try:
                old = (dt.date.today() - dt.date.fromisoformat(it.get("downloaded") or "")).days > 10
            except ValueError:
                old = True
            if old:                                                    # o link já caducou (7 dias): desiste
                done[k] = {"tries": 3, "why": "sem finais"}; continue
        if not url or not F:
            print(f"RBCP vídeo {pid}: {'sem link' if not url else 'finais do evento ainda não encontradas'}, fica para depois.")
            if not url:
                done[k] = {"tries": 3, "why": "sem link"}
            continue
        FINALS.clear(); FINALS.update(F)
        src = os.path.join("_reel", "src.mp4")
        dst = os.path.join(rm.DIR, rid + ".mp4")
        try:
            r = requests.get(url, timeout=180)
            if r.status_code != 200 or not r.headers.get("content-type", "").startswith("video"):
                raise ValueError(f"HTTP {r.status_code}")
            open(src, "wb").write(r.content)
            T = render(src, dst)
            if os.path.getsize(dst) > 24e6:                             # o site (Cloudflare Pages) não serve ficheiros > 25 MB
                os.replace(dst, src)
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
                                "-maxrate", "4M", "-bufsize", "8M", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", dst], check=True)
        except Exception as e:
            n = (done.get(k) or {}).get("tries", 0) + 1
            done[k] = {"tries": n, "why": type(e).__name__}
            print(f"RBCP vídeo {pid}: falhou ({type(e).__name__}: {str(e)[:100] if 'http' not in str(e) else ''}), tentativa {n}/3")
            continue
        finally:
            try: os.remove(src)
            except OSError: pass
        st["items"].append(dict(id=rid, kind="rbcp", sport="padel", gender="men", tournament=F["name"], champ=F["finals"][0]["w"],
                                file=os.path.basename(dst), due=rm.iso(rm.now()), made=rm.iso(rm.now()), caption=caption(F), posted=None,
                                v=rm.VERSION, rbcp=pid))
        st["done"].append(rid)
        done[k] = {"ok": it.get("downloaded") or dt.date.today().isoformat()}
        print(f"RBCP vídeo {pid}: Reel feito ({F['name']}, {T:.0f}s, {os.path.getsize(dst) / 1e6:.1f} MB).")
    json.dump(st, open(rm.STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    rbcp.done_save(done)


def rm_load_inbox():
    try:
        return json.load(open(INBOX, encoding="utf-8"))
    except (OSError, ValueError):
        return []


def test(dst):
    FINALS.update({"tournament": "DUBAI P1", "name": "Dubai P1", "date": "15 NOV 2026",
                   "finals": [{"label": "MEN", "w": "AUGSBURGER / LEBRÓN", "l": "Libaak / Alfonso", "sets": ["7-6", "5-7", "6-3"]},
                              {"label": "WOMEN", "w": "FERNÁNDEZ / CALVO", "l": "Josemaría / González", "sets": ["7-5", "6-1"]}]})
    os.makedirs("_reel", exist_ok=True)
    src = "_reel/test.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=25:d=30",
                    "-f", "lavfi", "-i", "sine=f=220:d=30", "-shortest", "-pix_fmt", "yuv420p", src], check=True)
    render(src, dst)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "test":
        test(sys.argv[2])
    else:
        make()
