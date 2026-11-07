// GET /api/kick: chamado a cada 5 min por um Worker com cron (e inofensivo se alguém o chamar à mão).
// Se um jogo ATP/WTA da lista site/data/watch.json já acabou no ESPN (grátis), manda correr a atualização do site em modo
// rápido (fast=1: só ESPN, 0 pedidos à API de ténis, sem padel). Não corre se já houver uma atualização a decorrer/na fila
// ou se a última começou há menos de GAP minutos (poupa minutos do GitHub). Segredo usado: GITHUB_TOKEN (o mesmo do admin).
const OWNER = "AfonsoPinto", REPO = "beyond100-engine", GAP_MIN = 12;
// Horários (UTC) que antes eram "schedule" no GitHub: num repositório público o GitHub desliga-os após 60 dias sem commits,
// por isso quem os dispara é o Worker (chama isto a cada 5 min). [dia da semana (0=domingo, -1=todos), hora, minuto, workflow]
const SCHEDULE = [[1, 4, 15, "padel_photo_scan.yml"], [1, 5, 15, "categorias.yml"], [1, 5, 40, "gsc.yml"], [1, 6, 25, "ig_token.yml"],
  [-1, 9, 45, "watchdog.yml"], [-1, 13, 45, "watchdog.yml"], [-1, 17, 45, "watchdog.yml"], [-1, 21, 45, "watchdog.yml"]];
const J = (o, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json", "cache-control": "no-store" } });

async function finished(lg, watch) {
  const r = await fetch(`https://site.api.espn.com/apis/site/v2/sports/tennis/${lg}/scoreboard`, { headers: { "User-Agent": "Mozilla/5.0 (compatible; Beyond100/0.1)" } });
  if (!r.ok) return [];
  const j = await r.json(), out = [];
  for (const ev of j.events || []) for (const g of ev.groupings || [{ competitions: ev.competitions || [] }]) for (const c of g.competitions || []) {
    const st = (c.status || {}).type || {};
    if (watch.has(String(c.id)) && st.state === "post") out.push(String(c.id));
  }
  return out;
}

async function scheduled(env) {
  // 1) atualização completa de hora a hora (minutos 5-9) e 2) tarefas semanais/diárias, sem duplicar se já houver uma recente
  const now = new Date(), m = now.getUTCMinutes(), h = now.getUTCHours(), d = now.getUTCDay(), out = [];
  const gh = (path, opt = {}) => fetch(`https://api.github.com/repos/${OWNER}/${REPO}${path}`, { ...opt,
    headers: { Authorization: `Bearer ${String(env.GITHUB_TOKEN || "").replace(/[^\x21-\x7E]/g, "")}`, Accept: "application/vnd.github+json", "User-Agent": "beyond100-kick", "content-type": "application/json" } });
  const recent = async (wf, mins) => {
    const runs = ((await (await gh(`/actions/workflows/${wf}/runs?per_page=3`)).json()).workflow_runs) || [];
    return runs.some(r => r.status !== "completed" || Date.now() - Date.parse(r.created_at) < mins * 60e3);
  };
  const go = async (wf, inputs) => (await gh(`/actions/workflows/${wf}/dispatches`, { method: "POST", body: JSON.stringify({ ref: "main", inputs: inputs || {} }) })).status;
  if (!env.GITHUB_TOKEN) return out;
  // completa: entre os minutos 5 e 20 (3 chamadas do Worker), se não houver uma COMPLETA nos últimos 40 min nem nenhuma a correr
  // (as rápidas, "Fast update", não contam: antes uma rápida 15 min antes saltava a hora inteira)
  if (m >= 5 && m < 20) {
    const runs = ((await (await gh(`/actions/workflows/update.yml/runs?per_page=10`)).json()).workflow_runs) || [];
    const busy = runs.some(r => r.status !== "completed");
    const full = runs.some(r => (r.display_title || r.name) !== "Fast update" && Date.now() - Date.parse(r.created_at) < 40 * 60e3);
    if (!busy && !full) out.push(["update.yml", await go("update.yml")]);
  }
  for (const [dw, hh, mm, wf] of SCHEDULE) {
    if ((dw === -1 || dw === d) && h === hh && m >= mm && m < mm + 5 && !(await recent(wf, 30))) out.push([wf, await go(wf)]);
  }
  return out;
}

export async function onRequestGet({ request, env, waitUntil }) {
  if (new URL(request.url).searchParams.get("cron") === "1") {          // chamada do Worker: horários primeiro
    try { const s = await scheduled(env); if (s.length) console.log("kick schedule", JSON.stringify(s)); } catch (e) { console.log("kick schedule error", String(e)); }
  }
  const gate = new Request("https://cache.beyond100/kick");          // no máximo uma verificação a cada 4 min, venha de onde vier
  const hit = await caches.default.match(gate);
  if (hit) return J({ skip: "recent check", last: await hit.json() });
  const remember = (o) => { waitUntil(caches.default.put(gate, new Response(JSON.stringify(o), { headers: { "cache-control": "max-age=240" } }))); return J(o); };
  let watch;
  try {
    const w = await env.ASSETS.fetch(new URL("/data/watch.json", request.url));
    watch = new Set(((await w.json()).ids) || []);
  } catch (e) { return remember({ skip: "no watch list" }); }
  if (!watch.size) return remember({ skip: "nothing to watch" });
  const done = [...await finished("atp", watch).catch(() => []), ...await finished("wta", watch).catch(() => [])];
  if (!done.length) return remember({ watching: watch.size, finished: 0 });
  if (!env.GITHUB_TOKEN) return remember({ finished: done, skip: "no token" });
  const gh = (path, opt = {}) => fetch(`https://api.github.com/repos/${OWNER}/${REPO}${path}`, { ...opt,
    headers: { Authorization: `Bearer ${String(env.GITHUB_TOKEN).replace(/[^\x21-\x7E]/g, "")}`, Accept: "application/vnd.github+json", "User-Agent": "beyond100-kick", "content-type": "application/json" } });
  const runs = ((await (await gh("/actions/workflows/update.yml/runs?per_page=5")).json()).workflow_runs) || [];
  if (runs.some(r => r.status !== "completed")) return remember({ finished: done, skip: "update already running" });
  const last = runs[0] ? Date.parse(runs[0].created_at) : 0;
  if (Date.now() - last < GAP_MIN * 60e3) return remember({ finished: done, skip: "last update too recent" });
  const r = await gh("/actions/workflows/update.yml/dispatches", { method: "POST", body: JSON.stringify({ ref: "main", inputs: { fast: "1" } }) });
  return remember({ finished: done, dispatched: r.status === 204 });
}
