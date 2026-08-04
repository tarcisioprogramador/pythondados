# 🗄️ PostgreSQL grátis (Neon) + Secrets no Streamlit Cloud

> Conecta seu dashboard publicado a um **PostgreSQL real e gratuito** (Neon).
> Com `DATABASE_URL` configurado, o dashboard prioriza o banco e mostra
> "fonte: banco de dados (postgresql)" — ótimo para o portfólio.

---

## Parte 1 — Criar o banco grátis no Neon (~3 min)

1. Acesse **https://neon.tech** → crie uma conta gratuita (pode usar Google/GitHub).
2. No dashboard, clique em **Create project**.
   - **Name:** `datapipeline` (ou o nome que quiser)
   - **Region:** escolha a mais próxima (ex: São Paulo `sa-east-1`)
   - Plano **Free** (0,5 GB de storage — mais que suficiente).
3. Na tela seguinte, aparecem as **connection strings**. Copie a que usa o
   driver **Python/psycopg** (dialeto `postgresql+psycopg`). Exemplo:
   ```
   postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/datapipeline?sslmode=require
   ```
   > ⚠️ Guarde essa string — o Neon mostra a senha apenas uma vez.
   > Ela já vem com `?sslmode=require` (SSL obrigatório do Neon).

---

## Parte 2 — Popular o banco com os dados do pipeline (local)

Rode o pipeline **apontando para o Neon** para criar as tabelas e carregar os dados:

```bash
# Windows (bash/terminal)
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/datapipeline?sslmode=require"
export PIPELINE_DB_ONLY=1

# Gera e roda o pipeline completo (cria schema, carrega e valida)
python scripts/generate_data.py --businesses 120 --dias 1260
python scripts/run_pipeline.py
```

> 💡 Alternativa: crie um arquivo `.env` na raiz do projeto com
> `DATABASE_URL=...` — o `etl/config.py` já carrega `.env` automaticamente.

Ao final, o log deve mostrar conexão com o Neon (`banco de dados conectado`).

---

## Parte 3 — Configurar o secret no Streamlit Cloud

1. No painel do Streamlit Cloud, abra seu app → **Settings** (engrenagem).
2. Aba **Secrets**.
3. Cole (substitua pela SUA connection string):
   ```toml
   DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST.neon.tech/datapipeline?sslmode=require"
   PIPELINE_DB_ONLY = "1"
   ```
   > `PIPELINE_DB_ONLY=1` faz o app tentar **apenas** o PostgreSQL (sem o
   > fallback para SQLite local) — falha rápido e cai para os parquet se o
   > Neon estiver fora. Evita ~4s de timeout extra na primeira carga.
4. Clique em **Save**. O app reinicia automaticamente.

---

## Parte 4 — Verificar

1. Abra seu site publicado.
2. O rodapé/cabeçalho deve mostrar **"Fonte: banco de dados (postgresql)"**
   (ou verifique no canto da sidebar: `Fonte de dados: banco de dados (postgresql)`).
3. Se algo falhar, o dashboard **cai automaticamente para os parquet commitados**
   — o site nunca fica fora do ar.

---

## 🛡️ Segurança

- O secret fica **apenas** no painel do Streamlit Cloud — nunca no repositório.
- `.gitignore` já exclui `.env` e `.streamlit/secrets.toml` — nunca commite segredos.
- O Neon Free possui autosuspend (o banco "dorme" após ~5 min sem uso e acorda
  sozinho na próxima consulta — pode levar ~1-2 s extras na primeira carga).

---

## ❓ Problemas comuns

| Sintoma | Causa / Solução |
|---|---|
| `sslmode` ausente na string | Adicione `?sslmode=require` ao final da DATABASE_URL |
| Timeout ao conectar | O banco está dormindo (autosuspend) → a primeira carga após a pausa leva ~4s a mais e acorda sozinho; recarregue se necessário |
| Senha com caracteres especiais | Encode: `@` vira `%40`, `#` vira `%23`, `:` vira `%3A` |
| Dashboard mostra "parquet" | O Neon não está acessível ou vazio — o fallback funcionou como esperado |
