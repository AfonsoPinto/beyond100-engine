// Beyond100: a cada 5 minutos chama https://beyond100tennis.com/api/kick?cron=1 (horários + resultados rápidos) (que vê no ESPN se algum jogo ATP/WTA acabou
// e, se sim, manda atualizar o site). Não tem segredos: toda a lógica e o token estão no site (Cloudflare Pages).
export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(fetch("https://beyond100tennis.com/api/kick?cron=1", { headers: { "User-Agent": "beyond100-kick-cron" } }));
  },
  async fetch() {
    return new Response("beyond100 kick cron: ok");
  },
};
