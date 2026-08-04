// ============================================================
// DataPipeline Pro — Cloudflare Worker
// ------------------------------------------------------------
// Serve uma página que embute o app Streamlit em um iframe,
// mantendo o domínio (ex: https://datapipeline.mooo.com) na barra
// de endereços do navegador.
//
// Como o Streamlit Community Cloud NÃO aceita domínio próprio
// (recurso pago do "Streamlit for Teams"), este Worker mascara
// a URL final via iframe — grátis e confiável.
//
// Passos (detalhes no GUIA-FREEDNS.md):
//   1. Troque STREAMLIT_APP pela URL real do seu app publicado.
//   2. Suba este arquivo no Cloudflare (Workers & Pages → Create
//      Worker → cole o código → Deploy) e anote a URL workers.dev.
//   3. No FreeDNS (freedns.afraid.org), aponte seu subdomínio com
//      um registro CNAME para a URL do Worker:
//        datapipeline.mooo.com  →  SEU-WORKER.workers.dev
// ============================================================

// 🔁 URL real do seu app publicado no Streamlit Cloud
const STREAMLIT_APP = "https://pythondados.streamlit.app";

// URL embutível (embed=true remove a barra superior e o menu do Streamlit)
const EMBED_URL = `${STREAMLIT_APP}/?embed=true&embed_options=show_toolbar,show_padding,show_colored_line`;

const HTML = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>DataPipeline Pro — Análise de Dados</title>
<style>
  :root { color-scheme: dark; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  /* 100dvh acompanha a viewport real no mobile (barra de endereço); 100% é o fallback */
  html, body { height: 100%; height: 100dvh; background: #0b1120; overflow: hidden; }
  body { display: flex; flex-direction: column; }
  /* Barra fina com o domínio próprio (opcional) */
  .barra {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 18px; background: #0f172a; border-bottom: 1px solid #1e293b;
    font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #64748b;
  }
  .barra b { color: #22D3EE; font-weight: 600; letter-spacing: .5px; }
  iframe {
    flex: 1; width: 100%; border: 0; display: block;
  }
</style>
</head>
<body>
  <div class="barra">
    <span>DataPipeline <b>PRO</b></span>
    <span>engenharia de dados · python · sql</span>
  </div>
  <iframe src="${EMBED_URL}" allow="fullscreen" title="DataPipeline Pro"></iframe>
</body>
</html>`;

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // Ícone do navegador: resposta vazia (evita erro 404 no console)
    if (url.pathname === "/favicon.ico") {
      return new Response(null, { status: 204 });
    }

    return new Response(HTML, {
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "no-store",
        "x-content-type-options": "nosniff",
        "referrer-policy": "no-referrer",
        "content-security-policy": "frame-ancestors 'self'",
      },
    });
  },
};
