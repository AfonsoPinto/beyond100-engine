// 11/11/2026: país do visitante (só o código de 2 letras que a Cloudflare já conhece), para o site escolher a transmissão
// de padel que passa no país de quem está a ver. Não guarda nada.
export async function onRequestGet({ request }) {
  const c = (request.cf && request.cf.country) || "";
  return new Response(JSON.stringify({ c }), { headers: { "content-type": "application/json", "cache-control": "private, max-age=3600" } });
}
