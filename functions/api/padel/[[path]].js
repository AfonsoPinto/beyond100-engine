// Beyond Padel: resultados frescos para o site, sem gastar minutos do GitHub.
// GET /api/padel/matches/<torneio>?date=AAAA-MM-DD  ->  jogos desse dia (resultado, estado, court, hora).
// GET /api/padel/live                               ->  { live: true/false } para o sinal da barra de cima (uma resposta só, em vez de um pedido por torneio).
// GET /api/padel/videos/<torneio>                   ->  transmissões oficiais do torneio (YouTube / Red Bull TV).
// Vai à Padel API com a chave guardada na Cloudflare (variável PADEL_API_KEY do projeto Pages). Nunca expõe a chave.
//
// 16/11/2026 — a Padel API avisou que o nosso cliente insistia depois dos 429 e ignorava o Retry-After. O que mudou:
//  1. Respeitamos o Retry-After: um 429 abre uma pausa global (guardada na cache da Cloudflare) e, enquanto durar, NÃO há um único pedido à Padel API.
//  2. Guardamos sempre a última resposta boa (6 h) e servimo-la em vez de ir outra vez à API quando algo corre mal.
//  3. As falhas também ficam em cache: um pedido que acabou de correr mal não se repete nos minutos seguintes.
//  4. Dias já passados ficam em cache muito mais tempo (não mudam) e datas longe de hoje são recusadas sem tocar na API.
const TTL = 300;             // resultados do dia: 5 min (era 2 min, que dava uma ida à API por cada atualização da página)
const OLD_TTL = 21600;       // dias já passados: 6 h (o resultado já não muda)
const VID_TTL = 900;         // vídeos: 15 min
const LIVE_TTL = 600;        // sinal "há jogos a decorrer": 10 min
const STALE_TTL = 21600;     // última resposta boa guardada à parte: 6 h
const FAIL_TTL = 300;        // falha que não é 429: 5 min sem repetir
const COOL_MIN = 60, COOL_MAX = 3600, COOL_DEFAULT = 300;

const J = (obj, status = 200, maxAge = TTL) => new Response(JSON.stringify(obj), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": `public, max-age=${maxAge}`,
             "access-control-allow-origin": "*" },
});

// ---------- pausa global depois de um 429 ----------
const COOL_KEY = new Request("https://cache.beyond100/padel-cooldown");

async function cooling() {
  const hit = await caches.default.match(COOL_KEY);
  if (!hit) return 0;
  const j = await hit.json().catch(() => null);
  const left = j && j.until ? Math.ceil((j.until - Date.now()) / 1000) : 0;
  return left > 0 ? left : 0;
}

// Lê o Retry-After (segundos ou data) e trava-o entre 1 e 60 minutos. Sem cabeçalho: 5 minutos.
function retryAfter(r) {
  const h = (r.headers.get("retry-after") || "").trim();
  let s = /^\d+$/.test(h) ? Number(h) : NaN;
  if (!Number.isFinite(s) && h) {
    const t = Date.parse(h);
    if (Number.isFinite(t)) s = Math.ceil((t - Date.now()) / 1000);
  }
  if (!Number.isFinite(s) || s < 0) s = COOL_DEFAULT;
  return Math.min(COOL_MAX, Math.max(COOL_MIN, s));
}

function startCooldown(secs, waitUntil) {
  const res = new Response(JSON.stringify({ until: Date.now() + secs * 1000 }), {
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": `public, max-age=${secs}` } });
  waitUntil(caches.default.put(COOL_KEY, res));
}

// ---------- última resposta boa ----------
const staleKey = k => new Request("https://cache.beyond100/padel-stale/" + k);

async function lastGood(k) {
  const hit = await caches.default.match(staleKey(k));
  if (!hit) return null;
  return hit.json().catch(() => null);
}

function keepGood(k, obj, waitUntil) {
  waitUntil(caches.default.put(staleKey(k), new Response(JSON.stringify(obj), {
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": `public, max-age=${STALE_TTL}` } })));
}

// Resposta quando a API não pode ser usada: a última boa que tivermos, senão vazio. Nunca um erro que o site mostre em branco.
async function fallback(k, empty, wait, waitUntil) {
  const old = await lastGood(k);
  const body = Object.assign({}, old || empty, { stale: true, retry_after: wait });
  const res = J(body, 200, Math.max(30, Math.min(wait || FAIL_TTL, OLD_TTL)));
  return res;
}

// Só datas perto de hoje: assim um robô não anda o calendário todo a gastar pedidos.
function dateAge(d) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return null;
  const t = Date.parse(d + "T00:00:00Z");
  if (!Number.isFinite(t)) return null;
  return Math.floor((Date.now() - t) / 864e5);        // dias desde essa data (negativo = futuro)
}

// Um pedido à Padel API com tudo o que foi combinado acima.
// Devolve { j } quando correu bem, { wait } quando temos de esperar, ou { fail: true }.
async function api(env, path, waitUntil) {
  const wait = await cooling();
  if (wait) return { wait };
  let r;
  try {
    r = await fetch("https://padelapi.org/api" + path, {
      headers: { Authorization: `Bearer ${env.PADEL_API_KEY}`, Accept: "application/json",
                 "User-Agent": "Beyond100/0.1 (beyond100tennis.com)" } });
  } catch (e) {
    return { fail: true };
  }
  if (r.status === 429) {
    const secs = retryAfter(r);
    startCooldown(secs, waitUntil);                   // a partir daqui ninguém mais toca na API até ela deixar
    return { wait: secs };
  }
  if (r.status === 403 || r.status === 401) {         // chave suspensa ou errada: não insistir
    startCooldown(COOL_MAX, waitUntil);
    return { wait: COOL_MAX };
  }
  if (!r.ok) return { fail: true };
  const j = await r.json().catch(() => null);
  return j ? { j } : { fail: true };
}

export async function onRequestGet({ request, env, params, waitUntil }) {
  const parts = Array.isArray(params.path) ? params.path : [params.path];
  const url = new URL(request.url);

  if (parts[0] === "yt") {                       // feed RSS de um canal (lista fechada), pela Cloudflare: o YouTube recusa às vezes os pedidos do GitHub
    const ok = ["UCK59dYVs3Wgwoe73nDTH6jw", "UC0YatYmg5JRYzXJPxIdRd8g", "UCEHUQZWBGZg6tRcnsQ6YXpQ", "UCjoBK1Z0nmC1iBIamE-5uJA",
                "UCT12ocLoA-sqRfs12yQM2Bg", "UCbcxFkd6B9xUU54InHv4Tig", "UCaBIVVpHjq6j3tSyxwTE-8Q", "UCY_5h5zaSwN7Or4kIJDYNXA"];   // ténis: ATP Challenger, Tennis TV, WTA, ATP Tour
    const cid = parts[1] || "";
    if (!ok.includes(cid)) return J({ error: "not found" }, 404, 60);
    const ck = new Request(`https://cache.beyond100/yt/${cid}`);
    const hit = await caches.default.match(ck);
    if (hit) return hit;
    let r;
    try {
      r = await fetch(`https://www.youtube.com/feeds/videos.xml?channel_id=${cid}`, { headers: { "User-Agent": "Mozilla/5.0 (compatible; Beyond100/0.1)" } });
    } catch (e) { return J({ error: "upstream" }, 502, 30); }
    if (!r.ok) return J({ error: "upstream " + r.status }, 502, 60);
    const res = new Response(await r.text(), { headers: { "content-type": "application/xml; charset=utf-8", "cache-control": "public, max-age=600" } });
    waitUntil(caches.default.put(ck, res.clone()));
    return res;
  }

  if (parts[0] === "videos" && /^\d{1,7}$/.test(parts[1] || "")) {
    if (!env.PADEL_API_KEY) return J({ error: "not configured" }, 503, 60);
    const k = `videos/${parts[1]}`;
    const vk = new Request("https://cache.beyond100/padel-" + k);
    const vh = await caches.default.match(vk);
    if (vh) return vh;
    const empty = { ts: Date.now(), tournament: Number(parts[1]), videos: [] };
    const out = await api(env, `/tournaments/${parts[1]}/videos?per_page=50`, waitUntil);
    if (out.wait || out.fail) {
      const res = await fallback(k, empty, out.wait || FAIL_TTL, waitUntil);
      waitUntil(caches.default.put(vk, res.clone()));       // a falha também fica em cache: não se repete já a seguir
      return res;
    }
    const rows = (out.j.data || []).map(v => ({ name: v.name, url: v.url, type: v.type, started_at: v.started_at, photo_url: v.photo_url }));
    const body = { ts: Date.now(), tournament: Number(parts[1]), videos: rows };
    const vres = J(body, 200, VID_TTL);
    keepGood(k, body, waitUntil);
    waitUntil(caches.default.put(vk, vres.clone()));
    return vres;
  }

  // Sinal para a barra de cima: "há algum jogo a decorrer?". Uma resposta só para todos os torneios, em cache 10 min.
  if (parts[0] === "live") {
    if (!env.PADEL_API_KEY) return J({ live: false }, 200, LIVE_TTL);
    const ids = (url.searchParams.get("t") || "").split(",").filter(x => /^\d{1,7}$/.test(x)).slice(0, 8).sort();
    if (!ids.length) return J({ live: false }, 200, LIVE_TTL);
    const k = "live/" + ids.join("-");
    const lk = new Request("https://cache.beyond100/padel-" + k);
    const lh = await caches.default.match(lk);
    if (lh) return lh;
    const date = new Date().toISOString().slice(0, 10);
    let live = false, bad = 0, wait = 0;
    for (const id of ids) {
      const out = await api(env, `/tournaments/${id}/matches?played_at=${date}&per_page=50`, waitUntil);
      if (out.wait) { wait = out.wait; bad++; break; }     // em pausa: pára já, não se tenta os outros
      if (out.fail) { bad++; continue; }
      live = live || (out.j.data || []).some(m => m.score && m.score.length && !m.winner
        && ["finished", "walkover", "retired", "cancelled", "bye"].indexOf(m.status) < 0);
      if (live) break;                                      // basta um
    }
    if (bad && !live) {
      const res = await fallback(k, { live: false }, wait || FAIL_TTL, waitUntil);
      waitUntil(caches.default.put(lk, res.clone()));
      return res;
    }
    const body = { ts: Date.now(), live };
    const res = J(body, 200, LIVE_TTL);
    keepGood(k, body, waitUntil);
    waitUntil(caches.default.put(lk, res.clone()));
    return res;
  }

  if (parts[0] !== "matches" || !/^\d{1,7}$/.test(parts[1] || "")) return J({ error: "not found" }, 404, 60);
  const date = url.searchParams.get("date") || "";
  const age = dateAge(date);
  if (age === null) return J({ error: "date" }, 400, 60);
  if (age > 400 || age < -30) return J({ error: "date" }, 400, 3600);    // fora da janela: nem chega à API
  if (!env.PADEL_API_KEY) return J({ error: "not configured" }, 503, 60);

  const ttl = age >= 2 ? OLD_TTL : TTL;                  // dia já fechado: guarda-se 6 h
  const k = `matches/${parts[1]}/${date}`;
  const key = new Request("https://cache.beyond100/padel-" + k);
  const hit = await caches.default.match(key);
  if (hit) return hit;

  const empty = { ts: Date.now(), tournament: Number(parts[1]), date, matches: [] };
  const out = await api(env, `/tournaments/${parts[1]}/matches?played_at=${date}&per_page=50`, waitUntil);
  if (out.wait || out.fail) {
    const res = await fallback(k, empty, out.wait || FAIL_TTL, waitUntil);
    waitUntil(caches.default.put(key, res.clone()));
    return res;
  }
  const slim = (out.j.data || []).filter(m => m.status !== "bye").map(m => ({
    id: m.id, status: m.status, score: Array.isArray(m.score) ? m.score : null, winner: m.winner === "team_1" || m.winner === "team_2" ? m.winner : null,
    court: m.court, court_order: m.court_order, schedule_label: m.schedule_label, round: m.round, category: m.category,
    round_name: m.round_name, scheduled_at: m.scheduled_at, seeds: m.seeds,
    players: m.players ? { team_1: (m.players.team_1 || []).map(p => ({ id: p.id, name: p.name, short_name: p.short_name })),
                           team_2: (m.players.team_2 || []).map(p => ({ id: p.id, name: p.name, short_name: p.short_name })) } : null,
  }));
  const body = { ts: Date.now(), tournament: Number(parts[1]), date, matches: slim };
  const res = J(body, 200, ttl);
  keepGood(k, body, waitUntil);
  waitUntil(caches.default.put(key, res.clone()));
  return res;
}
