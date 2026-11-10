// Cloudflare Pages Function: API da página /admin/ do Beyond100.
// Segurança: só responde a pedidos autenticados pelo Cloudflare Access (JWT verificado aqui) e do email do dono.
// Variáveis/segredos do projeto Pages (Settings > Variables and secrets):
//   GITHUB_TOKEN (segredo)  ACCESS_TEAM_DOMAIN  ACCESS_AUD  ADMIN_EMAIL
//   Estatísticas (opcional): CF_API_TOKEN (segredo, Account Analytics: Read)  CF_ACCOUNT_ID  CF_SITE_TAG
const OWNER = "AfonsoPinto";
const REPO = "beyond100";            // dados (privado): ficheiros editados no Admin
const ENGINE = "beyond100-engine";   // código e workflows (público): execuções, variáveis
const BRANCH = "main";

const EDIT_FILES = {            // ficheiros que o admin pode ler e gravar
  "handles.json": "obj",
  "handles_torneios.json": "obj",
  "qualifying_ids.json": "ids",
  "categorias_manual.json": "cats",
  "archived_posts.json": "pids",   // posts arquivados no Instagram (não contam para o máximo do dia)
  "photos/aliases.json": "names",
  "padel/photos/aliases.json": "names",
  "photos/photographers.json": "names",
  "padel/photos/photographers.json": "names",
};
const READ_FILES = ["results.json", "categorias_faltam.json", "categorias_torneios.json", "posts.json", "carousels.json", "stats.json", "spend.json", "news_log.json", "usage.json", "api_calls.json", "padel/data/posts.json", "padel/data/state.json", "padel/photos/scan_log.json", "photos/inbox_log.json", "padel/photos/inbox_log.json", "gsc.json", "popular.json", "reach.json", "photos/handles_cache.json", "espn_rank.json", "newsletter_state.json"];
const WORKFLOWS = {             // workflow -> inputs permitidos
  "update.yml": ["checks", "min_age"],
  "photo_inbox.yml": ["sport", "url_b64", "credit", "fallback", "dry", "replace"],
  "rebuild_stats.yml": [],
  "gsc.yml": [],
  "audit.yml": ["apply"],
  "repost.yml": ["match_id"],
  "fix_photos.yml": ["names", "block"],
  "categorias.yml": [],
  "torneios_ig.yml": ["apply"],
  "test_photos.yml": [],
  "newsletter.yml": [],
};
const VARS = ["PADEL_PUBLISH", "PADEL_MAX_POSTS_PER_DAY", "PADEL_FIP_MAX_PER_DAY", "PADEL_SEND_FROM", "PADEL_SEND_TO", "PADEL_SEND_GAP_MIN", "PADEL_MIN_SCORE", "PADEL_QF", "PADEL_SURPRISE_GAP", "PADEL_MAX_REQ", "POST_MIN_SCORE", "STORY_PENALTY", "STORY_COMEBACK", "TITLE_STYLE", "MAX_POSTS_PER_DAY", "NO_PHOTO_EXTRA", "PHOTO_BONUS", "WEEKLY_HOUR", "WEEKLY_DAY",
  "STORY_HOUR", "TRACK_MAX_PRIO", "KEEP_ARCHIVE", "HISTORY", "CAPTION_WEB_CONTEXT", "CAPTION_MODEL", "CAPTION_WEB_MIN_SCORE", "ANTHROPIC_CREDIT_USD", "ANTHROPIC_CREDIT_DATE", "ANTHROPIC_ALERT_USD", "NEWS_ENABLED", "NEWS_MAX_PER_DAY", "NEWS_SCAN_HOURS", "CF_BEACON_TOKEN", "CAPTION_LITE_BELOW", "PREVIEW_ENABLED", "PREVIEW_MAX_PER_DAY", "PREVIEW_H2H", "NEWSLETTER_USER", "CARD_STYLE", "RISING_ENABLED", "RISING_DAY", "RISING_HOUR", "THROWBACK_ENABLED", "THROWBACK_DAY", "THROWBACK_HOUR", "FIRST_COMMENT", "ROAD_ENABLED", "POWER_ENABLED", "PHOTO_GALLERY", "PHOTO_MAX_AGE_Y", "RECORDS_ENABLED", "HISTORY_MIRROR", "SEND_FROM", "SEND_TO", "SEND_GAP_MIN", "SEND_WEAK_FROM", "SEND_STRONG_SCORE", "EXTRA_POSTS", "EXCEPTION_SCORE", "SEND_LATE_SCORE", "MEN_FIRST", "SEND_MORNING_UNTIL", "SEND_MORNING_MAX", "SEND_MORNING_EXC", "SEND_MORNING_MIN"];

const J = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

function b64u(s) { s = s.replace(/-/g, "+").replace(/_/g, "/"); while (s.length % 4) s += "="; return Uint8Array.from(atob(s), c => c.charCodeAt(0)); }

async function verifyAccess(request, env) {
  if (!env.ACCESS_TEAM_DOMAIN || !env.ACCESS_AUD || !env.ADMIN_EMAIL || !env.GITHUB_TOKEN) {
    return { error: "Admin não configurado (faltam variáveis no Cloudflare Pages).", status: 503 };
  }
  const tok = request.headers.get("Cf-Access-Jwt-Assertion");
  if (!tok) return { error: "Sem sessão do Cloudflare Access.", status: 401 };
  try {
    const [h, p, s] = tok.split(".");
    const head = JSON.parse(new TextDecoder().decode(b64u(h)));
    const pay = JSON.parse(new TextDecoder().decode(b64u(p)));
    const certs = await (await fetch(`https://${env.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`, { cf: { cacheTtl: 3600 } })).json();
    const jwk = certs.keys.find(k => k.kid === head.kid);
    if (!jwk) throw new Error("kid");
    const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
    const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64u(s), new TextEncoder().encode(h + "." + p));
    const aud = Array.isArray(pay.aud) ? pay.aud : [pay.aud];
    if (!ok || !aud.includes(env.ACCESS_AUD) || pay.exp * 1000 < Date.now()) throw new Error("jwt");
    if ((pay.email || "").toLowerCase() !== env.ADMIN_EMAIL.toLowerCase()) return { error: "Email não autorizado.", status: 403 };
    return { email: pay.email };
  } catch (e) {
    return { error: "Sessão inválida.", status: 401 };
  }
}

function gh(env, path, init = {}) {
  const repo = path.startsWith("/actions") ? ENGINE : REPO;   // workflows e variáveis vivem no repositório do motor
  return fetch(`https://api.github.com/repos/${OWNER}/${repo}${path}`, {
    ...init,
    headers: { Authorization: `Bearer ${String(env.GITHUB_TOKEN).replace(/[^\x21-\x7E]/g, "")}`, Accept: "application/vnd.github+json", "User-Agent": "beyond100-admin",
      "X-GitHub-Api-Version": "2022-11-28", ...(init.headers || {}) },
  });
}

const utf8 = s => decodeURIComponent(escape(atob(s.replace(/\n/g, ""))));
const toB64 = s => btoa(unescape(encodeURIComponent(s)));

function validate(kind, data) {
  if (kind === "obj") {
    if (typeof data !== "object" || Array.isArray(data) || !data) return "Tem de ser um objeto nome -> perfil.";
    for (const [k, v] of Object.entries(data)) {
      if (k.startsWith("_")) continue;
      if (typeof v !== "string" || !/^@?[A-Za-z0-9._]{1,30}$/.test(v)) return `Perfil inválido para "${k}": ${v}`;
    }
  } else if (kind === "names") {             // apelido no ficheiro -> nome completo do jogador (importação de fotos)
    if (typeof data !== "object" || Array.isArray(data) || !data) return "Tem de ser um objeto.";
    for (const [k, v] of Object.entries(data)) {
      if (typeof v !== "string" || v.length > 60 || !/^[\p{L}' .-]+$/u.test(v) || v.trim().split(/\s+/).length < 2) return `Nome inválido para "${k}": ${v}`;
    }
  } else if (kind === "ids") {
    if (!Array.isArray(data) || !data.every(n => Number.isInteger(n) && n > 0)) return "Tem de ser uma lista de números.";
  } else if (kind === "pids") {
    if (!Array.isArray(data) || data.length > 500 || !data.every(n => typeof n === "string" && /^[A-Za-z0-9_-]{1,80}$/.test(n))) return "Tem de ser uma lista de ids de posts.";
  } else if (kind === "cats") {
    if (!Array.isArray(data)) return "Tem de ser uma lista.";
    for (const e of data) {
      if (!e || typeof e.city !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(e.start || "") || !/^(Challenger (50|75|100|125|175)|WTA (125|250|500|1000)|ATP (250|500|1000))$/.test(e.label || "") || !["m", "w"].includes(e.g)) {
        return "Entrada de categoria inválida: " + JSON.stringify(e);
      }
    }
  }
  return null;
}

export async function onRequest({ request, env, params }) {
  const who = await verifyAccess(request, env);
  if (who.error) return J({ error: who.error }, who.status);
  const url = new URL(request.url);
  const route = (params.path || []).join("/");
  if (request.method !== "GET") {                    // proteção CSRF: pedido tem de vir da própria página
    const o = request.headers.get("Origin");
    if (!request.headers.get("X-Admin") || (o && new URL(o).host !== url.host)) return J({ error: "Pedido recusado." }, 403);
  }
  try {
    if (route === "me") return J({ email: who.email, vars: VARS, workflows: Object.keys(WORKFLOWS), files: Object.keys(EDIT_FILES) });

    if (route === "file" && request.method === "GET") {
      const name = url.searchParams.get("name");
      if (!(name in EDIT_FILES) && !READ_FILES.includes(name)) return J({ error: "Ficheiro não permitido." }, 403);
      if (name in EDIT_FILES) {
        const r = await gh(env, `/contents/${name}?ref=${BRANCH}`);
        if (r.status === 404) return J({ content: name.endsWith("ids.json") || name.includes("cats") || name.includes("manual") || name.includes("archived") ? "[]" : "{}", sha: null });
        if (!r.ok) return J({ error: "GitHub: " + r.status }, 502);
        const j = await r.json();
        return J({ content: utf8(j.content), sha: j.sha });
      }
      const r = await gh(env, `/contents/${name}?ref=${BRANCH}`, { headers: { Accept: "application/vnd.github.raw+json" } });
      if (r.status === 404) return J({ content: "[]", sha: null });
      if (!r.ok) return J({ error: "GitHub: " + r.status }, 502);
      return J({ content: await r.text(), sha: null });
    }

    if (route === "file" && request.method === "PUT") {
      const b = await request.json();
      if (!(b.name in EDIT_FILES)) return J({ error: "Ficheiro não permitido." }, 403);
      let data;
      try { data = JSON.parse(b.content); } catch (e) { return J({ error: "JSON inválido." }, 400); }
      const bad = validate(EDIT_FILES[b.name], data);
      if (bad) return J({ error: bad }, 400);
      const body = { message: `Admin: update ${b.name}`, branch: BRANCH, content: toB64(JSON.stringify(data, null, 1) + "\n") };
      if (b.sha) body.sha = b.sha;
      const r = await gh(env, `/contents/${b.name}`, { method: "PUT", body: JSON.stringify(body) });
      if (!r.ok) return J({ error: "GitHub: " + r.status + " " + (await r.text()).slice(0, 200) }, 502);
      const j = await r.json();
      return J({ ok: true, sha: j.content.sha });
    }

    if (route === "run" && request.method === "POST") {
      const b = await request.json();
      if (!(b.workflow in WORKFLOWS)) return J({ error: "Workflow não permitido." }, 403);
      const inputs = {};
      for (const [k, v] of Object.entries(b.inputs || {})) {
        if (!WORKFLOWS[b.workflow].includes(k)) return J({ error: "Campo não permitido: " + k }, 400);
        if (typeof v !== "string" || v.length > 400 || /[\r\n`$;|&<>]/.test(v)) return J({ error: "Valor inválido em " + k }, 400);
        inputs[k] = v;
      }
      const r = await gh(env, `/actions/workflows/${b.workflow}/dispatches`, { method: "POST", body: JSON.stringify({ ref: BRANCH, inputs }) });
      if (r.status !== 204) return J({ error: "GitHub: " + r.status + " " + (await r.text()).slice(0, 200) }, 502);
      return J({ ok: true });
    }

    if (route === "analytics") {
      if (!env.CF_API_TOKEN || !env.CF_ACCOUNT_ID || !env.CF_SITE_TAG) return J({ error: "Estatísticas não configuradas (CF_API_TOKEN, CF_ACCOUNT_ID, CF_SITE_TAG)." }, 503);
      const days = Math.min(Math.max(parseInt(url.searchParams.get("days") || "7", 10) || 7, 1), 30);
      const end = new Date(), start = new Date(Date.now() - days * 864e5);
      const base = `siteTag:"${String(env.CF_SITE_TAG).replace(/[^A-Za-z0-9]/g, "")}",datetime_geq:"${start.toISOString()}",datetime_leq:"${end.toISOString()}"`;
      const build = (f) => {
      const grp = (alias, dim, n, ord) => `${alias}:rumPageloadEventsAdaptiveGroups(filter:${f},limit:${n},orderBy:[${ord}]){count sum{visits} dimensions{${dim}}}`;
      return `query{viewer{accounts(filter:{accountTag:"${String(env.CF_ACCOUNT_ID).replace(/[^A-Za-z0-9]/g, "")}"}){
        total:rumPageloadEventsAdaptiveGroups(filter:${f},limit:1){count sum{visits}}
        ${grp("daily", "date", 40, "date_ASC")} ${grp("pages", "requestPath", 200, "count_DESC")} ${grp("countries", "countryName", 15, "count_DESC")}
        ${grp("refs", "refererHost", 15, "count_DESC")} ${grp("devices", "deviceType", 5, "count_DESC")}}}}`; };
      const call = async (f) => { const r = await fetch("https://api.cloudflare.com/client/v4/graphql", { method: "POST",
        headers: { Authorization: `Bearer ${String(env.CF_API_TOKEN).replace(/[^\x21-\x7E]/g, "")}`, "Content-Type": "application/json" }, body: JSON.stringify({ query: build(f) }) });
        return [r, await r.json()]; };
      // exclui o próprio admin das estatísticas; se o filtro não for aceite, tenta sem ele
      const sport = url.searchParams.get("sport");
      const sf = sport === "padel" ? `,requestPath_like:"/padel%"` : sport === "tenis" ? `,AND:[{requestPath_notlike:"/admin%"},{requestPath_notlike:"/padel%"}]` : `,requestPath_notlike:"/admin%"`;
      let [r, j] = await call(`{${base}${sf}}`);
      if (!r.ok || j.errors) [r, j] = await call(`{${base}}`);
      if (!r.ok || j.errors) return J({ error: "Cloudflare: " + JSON.stringify(j.errors || r.status).slice(0, 300) }, 502);
      const a = j.data.viewer.accounts[0] || {};
      return J({ days, total: (a.total || [])[0] || { count: 0, sum: { visits: 0 } }, daily: a.daily, pages: a.pages, countries: a.countries, refs: a.refs, devices: a.devices });
    }

    if (route === "run_status") {                    // progresso da última execução de um workflow (passos do job)
      const wf = url.searchParams.get("workflow") || "";
      if (!(wf in WORKFLOWS)) return J({ error: "Workflow não permitido." }, 403);
      const r = await gh(env, `/actions/workflows/${wf}/runs?per_page=1`);
      if (!r.ok) return J({ error: "GitHub: " + r.status }, 502);
      const run = ((await r.json()).workflow_runs || [])[0];
      if (!run) return J({ run: null });
      const jr = await gh(env, `/actions/runs/${run.id}/jobs`);
      const jobs = jr.ok ? (await jr.json()).jobs || [] : [];
      const steps = (jobs[0] && jobs[0].steps || []).map(s => ({ name: s.name, status: s.status, conclusion: s.conclusion, started: s.started_at, done: s.completed_at }));
      return J({ run: { status: run.status, conclusion: run.conclusion, at: run.created_at, started: run.run_started_at, url: run.html_url }, steps });
    }

    if (route === "runs") {
      const r = await gh(env, "/actions/runs?per_page=15");
      if (!r.ok) return J({ error: "GitHub: " + r.status }, 502);
      const j = await r.json();
      return J(j.workflow_runs.map(x => ({ name: x.name, status: x.status, conclusion: x.conclusion, at: x.created_at, url: x.html_url, event: x.event })));
    }

    if (route === "vars" && request.method === "GET") {
      // uma lista paginada (30 por página) em vez de um pedido por variável: o Worker só pode fazer 50 pedidos
      const out = Object.fromEntries(VARS.map(n => [n, null]));
      for (let page = 1; page <= 10; page++) {
        const r = await gh(env, `/actions/variables?per_page=30&page=${page}`);
        if (!r.ok) return J({ error: "GitHub: " + r.status }, 502);
        const j = await r.json();
        for (const x of j.variables || []) if (x.name in out) out[x.name] = x.value;
        if ((j.variables || []).length < 30) break;
      }
      return J(out);
    }

    if (route === "vars" && request.method === "PUT") {
      const b = await request.json();
      if (!VARS.includes(b.name)) return J({ error: "Variável não permitida." }, 403);
      if (typeof b.value !== "string" || !/^[A-Za-z0-9_,.\- ]{0,80}$/.test(b.value)) return J({ error: "Valor inválido." }, 400);
      if (b.value === "") {                       // vazio = repor o valor por omissão do código (apaga a variável)
        const d = await gh(env, `/actions/variables/${b.name}`, { method: "DELETE" });
        if (!d.ok && d.status !== 404) return J({ error: "GitHub: " + d.status }, 502);
        return J({ ok: true });
      }
      let r = await gh(env, `/actions/variables/${b.name}`, { method: "PATCH", body: JSON.stringify({ name: b.name, value: b.value }) });
      if (r.status === 404) r = await gh(env, "/actions/variables", { method: "POST", body: JSON.stringify({ name: b.name, value: b.value }) });
      if (!r.ok) return J({ error: "GitHub: " + r.status }, 502);
      return J({ ok: true });
    }
    return J({ error: "Rota desconhecida." }, 404);
  } catch (e) {
    return J({ error: "Erro: " + e.message }, 500);
  }
}
