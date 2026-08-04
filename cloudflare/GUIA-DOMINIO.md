# 🌐 Domínio próprio gratuito (EU.org + Cloudflare) — Guia completo

> Objetivo: ter seu site em um domínio de verdade, tipo **`datapipeline.eu.org`**,
> de graça, mascarando a URL do Streamlit Cloud via Cloudflare Worker.

---

## Parte 1 — Coloque o site no ar primeiro (Streamlit Cloud)

1. Acesse [streamlit.io/cloud](https://streamlit.io/cloud) e faça login com seu GitHub.
2. **New app** → repositório `tarcisioprogramador/pythondados` → ramo `main` → `streamlit_app.py` → **Deploy**.
3. Anote a URL gerada: `https://datapipeline-pro.streamlit.app` (exemplo).
4. Abra essa URL e confirme que o dashboard aparece.

> ⏱️ O domínio do EU.org pode levar dias/semanas para ser aprovado — por isso o
> Streamlit Cloud já te deixa com o site no ar enquanto isso.

---

## Parte 2 — Crie o domínio gratuito no EU.org

1. Acesse **https://nic.eu.org/arf/en/** (Registration Request Form).
2. Preencha com seus dados (nome, e-mail, país).
3. Em "Domain name", coloque o nome desejado: **`datapipeline.eu.org`**.
   - Pode pedir mais de um (ex: `datapipeline.eu.org` e `tarcisiodados.eu.org`).
4. Em **nameservers**, deixa para preencher na **Parte 3** (você vai usar os do Cloudflare).
5. Envie. Você receberá um e-mail de confirmação — clique no link.
6. Aguarde a aprovação (manual, feita por voluntários). Pode levar de **alguns dias a algumas semanas**.

---

## Parte 3 — Configure o Cloudflare (grátis)

1. Crie uma conta gratuita em **https://dash.cloudflare.com/sign-up**.
2. Em **Add a site**, digite `datapipeline.eu.org` e selecione o plano **Free**.
3. O Cloudflare vai te dar **2 nameservers**, ex:
   - `ada.ns.cloudflare.com`
   - `ben.ns.cloudflare.com`
4. Volte ao e-mail/painel do **EU.org** e informe esses 2 nameservers no seu domínio.
5. Quando o EU.org aprovar (o DNS propagar), o domínio fica ativo no Cloudflare.

---

## Parte 4 — Publique o Worker (máscara do Streamlit)

1. No painel do Cloudflare → **Workers & Pages** → **Create** → **Create Worker**.
2. Cole o conteúdo de **`cloudflare/worker.js`** (deste projeto).
3. **Antes de salvar**, troque a linha:
   ```js
   const STREAMLIT_APP = "https://datapipeline-pro.streamlit.app";
   ```
   pela URL **real** que você anotou na Parte 1.
4. Clique em **Deploy**.
5. Agora crie a rota: no Worker → **Settings** → **Domains & Routes** → **Add**:
   - **Route / Custom domain:** `datapipeline.eu.org/*` (ou o domínio aprovado)
   - Selecione o Worker.
6. Pronto! Acesse `https://datapipeline.eu.org` — o dashboard aparece com o seu domínio. 🎉

---

## Como funciona (resumo técnico)

- O Streamlit Community Cloud **não aceita domínio próprio** no plano gratuito
  (recurso exclusivo do pago "Streamlit for Teams").
- O **Cloudflare Worker** (grátis) serve uma página que embute o app via iframe
  com `?embed=true` — mantendo seu domínio na barra de endereços.
- O app Streamlit permite iframe por padrão (seu `config.toml` já tem
  `enableCORS = false` e `enableXsrfProtection = false`, o que facilita).

---

## Alternativa: redirecionamento simples (301)

Se você preferir que o visitante **vá direto** para o streamlit.app (sem máscara
de URL), o Worker pode ser só um redirect:

```js
export default {
  async fetch(request) {
    return Response.redirect("https://datapipeline-pro.streamlit.app", 301);
  },
};
```
