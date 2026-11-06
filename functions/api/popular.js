// GET /api/popular -> {ts, days, pages:[{path, views}]}: páginas de JOGADORES e TORNEIOS mais vistas no site (Cloudflare Web Analytics),
// só caminhos públicos (/p/, /t/, /padel/p/, /padel/t/) e só contagens agregadas. Em cache 6 h. Usado pelo motor para dar prioridade
// a quem as pessoas procuram. Segredos usados: CF_API_TOKEN, CF_ACCOUNT_ID, CF_SITE_TAG (os mesmos das estatísticas do Admin).
const DAYS = 14;
const J = (o, s = 200, age = 21600) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json", "cache-control": `public, max-age=${age}` } });

export async function onRequestGet({ env, waitUntil }) {
  const key = new Request("https://cache.beyond100/popular");
  const hit = await caches.default.match(key);
  if (hit) return hit;
  if (!env.CF_API_TOKEN || !env.CF_ACCOUNT_ID || !env.CF_SITE_TAG) return J({ error: "not configured" }, 503, 300);
  const end = new Date(), start = new Date(Date.now() - DAYS * 864e5);
  const tag = String(env.CF_SITE_TAG).replace(/[^A-Za-z0-9]/g, ""), acc = String(env.CF_ACCOUNT_ID).replace(/[^A-Za-z0-9]/g, "");
  const base = `siteTag:"${tag}",datetime_geq:"${start.toISOString()}",datetime_leq:"${end.toISOString()}"`;
  const call = async (f, n) => {
    const q = `query{viewer{accounts(filter:{accountTag:"${acc}"}){pages:rumPageloadEventsAdaptiveGroups(filter:${f},limit:${n},orderBy:[count_DESC]){count dimensions{requestPath}}}}}`;
    const r = await fetch("https://api.cloudflare.com/client/v4/graphql", { method: "POST",
      headers: { Authorization: `Bearer ${String(env.CF_API_TOKEN).replace(/[^\x21-\x7E]/g, "")}`, "Content-Type": "application/json" }, body: JSON.stringify({ query: q }) });
    return [r, await r.json().catch(() => ({}))];
  };
  let [r, j] = await call(`{${base},OR:[{requestPath_like:"/p/%"},{requestPath_like:"/t/%"},{requestPath_like:"/padel/p/%"},{requestPath_like:"/padel/t/%"}]}`, 300);
  if (!r.ok || j.errors) [r, j] = await call(`{${base}}`, 1000);          // filtro não aceite: traz tudo e filtra aqui
  if (!r.ok || j.errors) return J({ error: "cloudflare", detail: JSON.stringify(j.errors || r.status).slice(0, 200) }, 502, 300);
  const pages = (((j.data || {}).viewer || {}).accounts || [{}])[0].pages || [];
  const ok = (p) => /^\/(padel\/)?(p|t)\//.test(p);
  const res = J({ ts: Date.now(), days: DAYS, pages: pages.map(p => ({ path: p.dimensions.requestPath.replace(/\?.*$/, ""), views: p.count })).filter(p => ok(p.path)).slice(0, 300) });
  waitUntil(caches.default.put(key, res.clone()));
  return res;
}
