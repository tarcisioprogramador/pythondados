# 🌐 Domínio gratuito instantâneo — FreeDNS (afraid.org)

> Alternativa rápida ao EU.org (que leva semanas). Com o **FreeDNS** você tem
> um domínio como **`datapipeline.mooo.com`** em **minutos** — não em semanas.
>
> Para um app Streamlit no Streamlit Cloud, há duas formas de usar:
> **A) Redirecionamento nativo** (simples) ou **B) Máscara via Worker** (mantém
> o domínio na barra de endereços — usa o `cloudflare/worker.js`).

---

## Passo 1 — Criar a conta (2 min)

1. Acesse **https://freedns.afraid.org/signup/**
2. Preencha o cadastro (nome de usuário, e-mail, senha) e confirme o e-mail.

---

## Passo 2 — Registrar seu subdomínio grátis (1 min)

1. Entre no painel: **https://freedns.afraid.org**
2. Menu → **Subdomains** → **Add** (ou acesse direto:
   https://freedns.afraid.org/subdomain/)
3. Escolha um domínio público disponível (ex: **mooo.com** — é o mais famoso)
   e preencha:
   - **Subdomain:** `datapipeline`
   - **Destination:** a URL do seu site (ex: `pythondados.streamlit.app`)
   - **Type:** `URL` (redirecionamento) — ou `CNAME` para o Cloudflare Worker
4. Clique em **Save!** — pronto, o domínio já funciona. ✅

---

## Opção A — Redirecionamento simples (2 min, sem Worker)

Se você escolheu **Type: URL** no passo 2, o FreeDNS redireciona sozinho:

- `https://datapipeline.mooo.com` → redireciona para `https://pythondados.streamlit.app`
- O visitante vê o seu site, mas a **URL do navegador muda** para `streamlit.app`
- **Prós:** zero configuração extra · **Contras:** o domínio "some" na barra de endereços

### Ajuste fino (opcional)
No painel, em **Subdomains**, você pode trocar o *Type* entre:
- `URL` → redirect simples
- `URL Frame` → **máscara** (mantém o domínio na barra de endereços usando
  iframe — funciona para Streamlit com `?embed=true`)

> Teste com `https://datapipeline.mooo.com` — se aparecer o site, está pronto!

---

## Opção B — Máscara via Cloudflare Worker (mantém seu domínio)

Para manter `datapipeline.mooo.com` na barra de endereços **com o site inteiro
funcionando** (gráficos, filtros e WebSockets), use o **`cloudflare/worker.js`**
deste projeto:

### 1. Crie o Worker no Cloudflare (grátis)
1. Acesse **https://dash.cloudflare.com** → crie conta gratuita.
2. **Workers & Pages** → **Create** → **Create Worker**.
3. Cole o conteúdo de **`cloudflare/worker.js`**.
4. **Verifique** a linha (deve ter sua URL real):
   ```js
   const STREAMLIT_APP = "https://pythondados.streamlit.app";
   ```
5. Clique em **Deploy**. Anote a URL do Worker:
   `https://SEU-WORKER-SUBDOMINIO.workers.dev`

### 2. Aponte o FreeDNS para o Worker
1. No painel do FreeDNS → **Subdomains** → **Modify** seu subdomínio.
2. Configure:
   - **Type:** `CNAME`
   - **Subdomain:** `datapipeline`
   - **Destination:** `SEU-WORKER-SUBDOMINIO.workers.dev`
3. Salve. Aguarde propagação (minutos).

### 3. Resultado
- `https://datapipeline.mooo.com` → mostra seu dashboard **com seu domínio na
  barra de endereços**. 🎉

---

## ⚠️ Importante (primeiro resolva o deploy do site)

O app **ainda não está publicado** no Streamlit Cloud (o site retorna
"Not found"). Antes do domínio funcionar, publique o app:

1. [share.streamlit.io](https://share.streamlit.io) → **New app**
2. Repository: `tarcisioprogramador/pythondados` · Branch: `main` ·
   Main file: `streamlit_app.py`
3. **Deploy** → anote a URL real (ex: `https://pythondados.streamlit.app`)

Sem isso, o redirecionamento apontará para um site que não existe.

---

## ✅ Checklist final

- [ ] Conta criada no FreeDNS e e-mail confirmado
- [ ] Subdomínio criado (ex: `datapipeline.mooo.com`)
- [ ] App publicado no Streamlit Cloud (URL real anotada)
- [ ] Opção A: Type `URL` no FreeDNS → testado
- [ ] Opção B: Worker criado + CNAME apontando para `workers.dev`
- [ ] `cloudflare/worker.js` com `STREAMLIT_APP` = URL real
