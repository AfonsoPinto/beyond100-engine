// Beyond Padel: resultados frescos para o site, sem gastar minutos do GitHub.
// GET /api/padel/matches/<torneio>?date=AAAA-MM-DD  ->  jogos desse dia (resultado, estado, court, hora), em cache 2 min.
// GET /api/padel/videos/<torneio>  ->  transmissões oficiais do torneio (YouTube / Red Bull TV), em cache 15 min.
// Vai à Padel API com a chave guardada na Cloudflare (variável PADEL_API_KEY do projeto Pages). Nunca expõe a chave.
const TTL = 120;                                  // resultados: 2 min (cada torneio/dia faz no máximo 30 pedidos por hora, só quando há visitas)

const J = (obj, status = 200, maxAge = TTL) => new Response(JSON.stringify(obj), {
  status,
  headers: { "content-type": "application/json; charset=utf-8", "cache-control": `public, max-age=${maxAge}`,
             "access-control-allow-origin": "*" },
});

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
    const vk = new Request(`https://cache.beyond100/padel-videos/${parts[1]}`);
    const vh = await caches.default.match(vk);
    if (vh) return vh;
    let vr;
    try {
      vr = await fetch(`https://padelapi.org/api/tournaments/${parts[1]}/videos?per_page=50`, { headers: { Authorization: `Bearer ${env.PADEL_API_KEY}`,
        Accept: "application/json", "User-Agent": "Beyond100/0.1 (beyond100tennis.com)" } });
    } catch (e) { return J({ error: "upstream" }, 502, 30); }
    if (!vr.ok) return J({ error: "upstream " + vr.status }, 502, vr.status === 429 ? 120 : 60);
    const vj = await vr.json();
    const rows = (vj.data || []).map(v => ({ name: v.name, url: v.url, type: v.type, started_at: v.started_at, photo_url: v.photo_url }));
    const vres = J({ ts: Date.now(), tournament: Number(parts[1]), videos: rows }, 200, 900);
    waitUntil(caches.default.put(vk, vres.clone()));
    return vres;
  }
  if (parts[0] !== "matches" || !/^\d{1,7}$/.test(parts[1] || "")) return J({ error: "not found" }, 404, 60);
  const date = url.searchParams.get("date") || "";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return J({ error: "date" }, 400, 60);
  if (!env.PADEL_API_KEY) return J({ error: "not configured" }, 503, 60);
  const cache = caches.default;
  const key = new Request(`https://cache.beyond100/padel/${parts[1]}/${date}`);
  const hit = await cache.match(key);
  if (hit) return hit;
  const api = `https://padelapi.org/api/tournaments/${parts[1]}/matches?played_at=${date}&per_page=50`;
  let r;
  try {
    r = await fetch(api, { headers: { Authorization: `Bearer ${env.PADEL_API_KEY}`, Accept: "application/json",
                                      "User-Agent": "Beyond100/0.1 (beyond100tennis.com)" } });
  } catch (e) {
    return J({ error: "upstream" }, 502, 30);
  }
  if (!r.ok) return J({ error: "upstream " + r.status }, 502, r.status === 429 ? 120 : 30);
  const j = await r.json();
  const slim = (j.data || []).filter(m => m.status !== "bye").map(m => ({
    id: m.id, status: m.status, score: Array.isArray(m.score) ? m.score : null, winner: m.winner === "team_1" || m.winner === "team_2" ? m.winner : null,
    court: m.court, court_order: m.court_order, schedule_label: m.schedule_label, round: m.round, category: m.category,
    round_name: m.round_name, scheduled_at: m.scheduled_at, seeds: m.seeds,
    players: m.players ? { team_1: (m.players.team_1 || []).map(p => ({ id: p.id, name: p.name, short_name: p.short_name })),
                           team_2: (m.players.team_2 || []).map(p => ({ id: p.id, name: p.name, short_name: p.short_name })) } : null,
  }));
  const res = J({ ts: Date.now(), tournament: Number(parts[1]), date, matches: slim });
  waitUntil(cache.put(key, res.clone()));
  return res;
}
