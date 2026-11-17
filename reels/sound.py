"""Som dos Reels, todo gerado por código (sem música de terceiros, sem direitos a pagar): batida, pancadas na bola,
choques, sopros, público. Python puro (sem numpy), 44,1 kHz mono."""
import array, math, random, wave

SR = 44100


class Mix:
    def __init__(self, dur):
        self.n = int(dur * SR) + SR
        self.b = array.array("f", bytes(4 * self.n))
        self.rnd = random.Random(11)

    def _add(self, i0, samples, vol):
        b, n = self.b, self.n
        for k, v in enumerate(samples):
            j = i0 + k
            if 0 <= j < n: b[j] += v * vol

    # ---------------------------------------------------------- peças
    def kick(self, t, vol=0.9):
        L = int(0.32 * SR); ph = 0.0; out = []
        for k in range(L):
            x = k / SR; f = 45 + 95 * math.exp(-x * 28); ph += 2 * math.pi * f / SR
            out.append(math.sin(ph) * math.exp(-x * 9))
        self._add(int(t * SR), out, vol)

    def hat(self, t, vol=0.18):
        L = int(0.06 * SR); prev = 0.0; out = []
        for k in range(L):
            r = self.rnd.uniform(-1, 1); out.append((r - prev) * math.exp(-k / SR * 70)); prev = r
        self._add(int(t * SR), out, vol)

    def clap(self, t, vol=0.25):
        L = int(0.18 * SR); out = []
        for k in range(L):
            x = k / SR; env = sum(math.exp(-(x - d) * 60) for d in (0, 0.012, 0.024) if x >= d)
            out.append(self.rnd.uniform(-1, 1) * env * 0.5)
        self._add(int(t * SR), out, vol)

    def pop(self, t, vol=0.6, pitch=1.0):
        """pancada de raquete / choque de bolas: estalo curto + tom"""
        L = int(0.09 * SR); out = []; ph = 0.0
        for k in range(L):
            x = k / SR; ph += 2 * math.pi * 900 * pitch * (1 - 0.4 * x / 0.09) / SR
            out.append((0.55 * self.rnd.uniform(-1, 1) * math.exp(-x * 160) + 0.6 * math.sin(ph) * math.exp(-x * 55)))
        self._add(int(t * SR), out, vol)

    def thock(self, t, vol=0.35):
        """ressalto no chão: mais grave e abafado"""
        L = int(0.12 * SR); out = []; ph = 0.0
        for k in range(L):
            x = k / SR; ph += 2 * math.pi * (260 - 600 * x) / SR
            out.append(math.sin(ph) * math.exp(-x * 40) + 0.2 * self.rnd.uniform(-1, 1) * math.exp(-x * 120))
        self._add(int(t * SR), out, vol)

    def glass(self, t, vol=0.45):
        """bola no vidro: estalo seco e brilhante"""
        L = int(0.2 * SR); out = []
        for k in range(L):
            x = k / SR
            out.append(sum(math.sin(2 * math.pi * f * x) for f in (1650, 2420, 3310)) / 3 * math.exp(-x * 30) + 0.4 * self.rnd.uniform(-1, 1) * math.exp(-x * 90))
        self._add(int(t * SR), out, vol)

    def boom(self, t, vol=0.8):
        """impacto grave (surpresa, título)"""
        L = int(1.4 * SR); ph = 0.0; out = []; lp = 0.0
        for k in range(L):
            x = k / SR; f = 32 + 70 * math.exp(-x * 6); ph += 2 * math.pi * f / SR
            lp += 0.02 * (self.rnd.uniform(-1, 1) - lp)
            out.append(math.sin(ph) * math.exp(-x * 2.6) + 1.5 * lp * math.exp(-x * 5))
        self._add(int(t * SR), out, vol)

    def whoosh(self, t, dur=0.45, vol=0.3):
        L = int(dur * SR); out = []; lp = 0.0
        for k in range(L):
            x = k / L; a = 0.02 + 0.25 * math.sin(math.pi * x)
            lp += a * (self.rnd.uniform(-1, 1) - lp)
            out.append(lp * math.sin(math.pi * x) ** 2 * 2)
        self._add(int(t * SR), out, vol)

    def crowd(self, t0, t1, level=0.12, swell=None):
        """público: ruído filtrado com murmúrio; swell=(t, altura) para a ovação"""
        i0, i1 = int(t0 * SR), int(t1 * SR); lp = lp2 = 0.0; out = []
        for k in range(i1 - i0):
            x = (i0 + k) / SR
            lp += 0.08 * (self.rnd.uniform(-1, 1) - lp); lp2 += 0.3 * (lp - lp2)
            g = level * (0.8 + 0.2 * math.sin(x * 1.7) * math.sin(x * 0.63))
            if swell and x >= swell[0]:
                g += swell[1] * min(1, (x - swell[0]) / 0.25) * math.exp(-(x - swell[0]) / 2.6)
            fade = min(1, (x - t0) / 0.6, (t1 - x) / 0.8)
            out.append(lp2 * 4 * g * fade)
        self._add(i0, out, 1.0)

    def pad(self, t0, t1, notes=(110.0, 164.81, 220.0, 261.63), vol=0.05):
        i0, i1 = int(t0 * SR), int(t1 * SR); out = []
        for k in range(i1 - i0):
            x = k / SR; a = min(1, x / 1.5, (t1 - t0 - x) / 1.2)
            out.append(a * sum(math.sin(2 * math.pi * f * x + j) for j, f in enumerate(notes)) / len(notes))
        self._add(i0, out, vol)

    def beat(self, t0, t1, bpm=104, mute=(), vol=1.0):
        """batida: bombo nos tempos, palmas no 2 e no 4, prato nos contratempos; mute=[(a, b)] tira o bombo"""
        q = 60 / bpm; t = t0; i = 0
        while t < t1:
            m = any(a <= t < b for a, b in mute)
            if not m: self.kick(t, 0.75 * vol)
            if i % 2 == 1 and not m: self.clap(t, 0.2 * vol)
            self.hat(t + q / 2, 0.14 * vol)
            t += q; i += 1

    def heartbeat(self, t0, t1, every=0.78, vol=0.55):
        t = t0
        while t < t1:
            self.kick(t, vol); self.kick(t + 0.16, vol * 0.6); t += every

    def riser(self, t0, t1, vol=0.12):
        i0, i1 = int(t0 * SR), int(t1 * SR); out = []; ph = 0.0; lp = 0.0
        for k in range(i1 - i0):
            x = k / (i1 - i0); ph += 2 * math.pi * (180 + 520 * x * x) / SR
            lp += (0.02 + 0.3 * x) * (self.rnd.uniform(-1, 1) - lp)
            out.append((0.5 * math.sin(ph) + lp) * x * x)
        self._add(i0, out, vol)

    # ---------------------------------------------------------- sons reais (reels/sfx, CC0 do Freesound)
    def sample(self, t, cat, vol=0.7, loop_to=None):
        """toca um som gravado da categoria (uma das variantes, ao acaso); loop_to repete até esse tempo (ambiente)"""
        xs = SFX.get(cat)
        if not xs: return False
        smp = self.rnd.choice(xs)
        if loop_to:
            out = []; L = int((loop_to - t) * SR)
            while len(out) < L: out.extend(smp)
            out = out[:L]; f = int(0.8 * SR)
            for k in range(min(f, L)): out[k] *= k / f; out[L - 1 - k] *= k / f
            self._add(int(t * SR), out, vol)
        else:
            self._add(int(t * SR), smp, vol)
        return True

    # ---------------------------------------------------------- saída
    def write(self, path, dur):
        n = int(dur * SR); peak = max(1e-6, max(abs(v) for v in self.b[:n]))
        g = 0.89 / peak
        out = array.array("h", (int(max(-1, min(1, self.b[i] * g * min(1, i / (0.02 * SR), (n - i) / (0.4 * SR)))) * 32767) for i in range(n)))
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(out.tobytes())


def _load_sfx():
    import glob, os
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sfx"); out = {}
    for f in sorted(glob.glob(os.path.join(d, "*.wav"))):
        try:
            with wave.open(f) as w:
                if w.getframerate() != SR or w.getnchannels() != 1 or w.getsampwidth() != 2: continue
                a = array.array("h"); a.frombytes(w.readframes(w.getnframes()))
            out.setdefault(os.path.basename(f).rsplit("_", 1)[0], []).append([v / 32768 for v in a])
        except Exception:
            pass
    return out


SFX = _load_sfx()


def mux(video, wav, out):
    import subprocess
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-shortest", "-use_editlist", "0", "-movflags", "+faststart", out])
    return r.returncode == 0
