// Beyond100 ténis: jogos ATP/WTA (incl. WTA 125) a decorrer, a partir do scoreboard público do ESPN. Grátis, sem chave, sem quota.
// GET /api/tennis/live -> {ts, fin:[acabados há pouco, com w = vencedor], matches:[{lg,t,r,court,p:[{n,c,f}],s:[[..],[..]],tb:[[..],[..]]}]}, em cache 30 s (um pedido ao ESPN por liga a cada 30 s, só com visitas).
const TTL = 30;
const ISO2 = {"ARG":"ar","AUS":"au","AUT":"at","BEL":"be","BIH":"ba","BOL":"bo","BRA":"br","BUL":"bg","CAN":"ca","CHI":"cl","CHN":"cn","COL":"co","CRO":"hr","CYP":"cy","CZE":"cz","DEN":"dk","ECU":"ec","EGY":"eg","ESP":"es","EST":"ee","FIN":"fi","FRA":"fr","GBR":"gb","GEO":"ge","GER":"de","GRE":"gr","HKG":"hk","HUN":"hu","IND":"in","INA":"id","IRL":"ie","ISR":"il","ITA":"it","JPN":"jp","KAZ":"kz","KOR":"kr","LAT":"lv","LTU":"lt","MEX":"mx","MDA":"md","MON":"mc","NED":"nl","NOR":"no","NZL":"nz","PAR":"py","PER":"pe","PHI":"ph","POL":"pl","POR":"pt","ROU":"ro","RSA":"za","SLO":"si","SRB":"rs","SUI":"ch","SVK":"sk","SWE":"se","THA":"th","TPE":"tw","TUN":"tn","TUR":"tr","UKR":"ua","URU":"uy","USA":"us","UZB":"uz","VEN":"ve","BAR":"bb","DOM":"do","MAR":"ma","LUX":"lu","ISL":"is","MNE":"me","MKD":"mk","ARM":"am","QAT":"qa","UAE":"ae","VIE":"vn","MAS":"my","SGP":"sg","PUR":"pr","CRC":"cr","GUA":"gt","ESA":"sv","ALG":"dz","ZIM":"zw","NGR":"ng","KEN":"ke","IRI":"ir","PAK":"pk","LBN":"lb","JOR":"jo"};
Object.assign(ISO2, { SER: "rs", ROM: "ro", TPO: "tw" });
const J = (obj, status = 200, maxAge = TTL) => new Response(JSON.stringify(obj), {
  status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": `public, max-age=${maxAge}`, "access-control-allow-origin": "*" } });

async function league(lg) {
  const r = await fetch(`https://site.api.espn.com/apis/site/v2/sports/tennis/${lg}/scoreboard`, { headers: { "User-Agent": "Mozilla/5.0 (compatible; Beyond100/0.1)" } });
  if (!r.ok) throw new Error("espn " + r.status);
  const j = await r.json(), out = [];
  for (const ev of j.events || []) {
    for (const g of ev.groupings || [{ competitions: ev.competitions || [] }]) {
      const gn = ((g.grouping || {}).displayName || "").toLowerCase();
      if (gn.includes("doubles")) continue;
      for (const c of g.competitions || []) {
        const st = (c.status || {}).type || {};
        const fin = st.state === "post" && st.completed && Date.now() - Date.parse(c.date || 0) < 8 * 3600e3;   // acabou há pouco (começou nas últimas 8 h)
        if ((st.state !== "in" && !fin) || (c.competitors || []).length !== 2) continue;
        const p = c.competitors.map(x => {
          const a = x.athlete || {}, cc = (((a.flag || {}).href || "").match(/\/([a-z]{3})\.png/) || [])[1] || "";
          return { n: a.displayName || "", c: cc.toUpperCase(), f: ISO2[cc.toUpperCase()] || "" };
        });
        if (!p[0].n || !p[1].n) continue;
        const ls = c.competitors.map(x => x.linescores || []);
        const sv = c.competitors.findIndex(x => x.possession === true);
        out.push({ done: fin ? 1 : 0, w: fin ? c.competitors.findIndex(x => x.winner === true) : null, st: st.name || "", lg, t: ev.name || "", r: (c.round || {}).displayName || "", court: (c.venue || {}).court || "", p, sv: sv >= 0 ? sv : null,
                   s: ls.map(l => l.map(v => Math.round(v.value || 0))), tb: ls.map(l => l.map(v => v.tiebreak ?? null)) });
      }
    }
  }
  return out;
}

export async function onRequestGet({ params, waitUntil }) {
  const parts = Array.isArray(params.path) ? params.path : [params.path];
  if (parts[0] !== "live") return J({ error: "not found" }, 404, 60);
  const key = new Request("https://cache.beyond100/tennis/live");
  const hit = await caches.default.match(key);
  if (hit) return hit;
  const rows = [];
  let ok = 0;
  for (const lg of ["atp", "wta"]) {
    try { rows.push(...await league(lg)); ok++; } catch (e) { /* uma liga em baixo não estraga a outra */ }
  }
  if (!ok) return J({ error: "upstream" }, 502, 30);
  // "matches" = só a decorrer (o que todas as páginas já usam); "fin" = acabados há pouco (a página do jogo mostra logo o resultado final)
  const res = J({ ts: Date.now(), matches: rows.filter(m => !m.done), fin: rows.filter(m => m.done) });
  waitUntil(caches.default.put(key, res.clone()));
  return res;
}
