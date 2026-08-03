# 🌍 Guia de Deploy — Publicando o site na internet

Este guia publica o **DataPipeline Pro** gratuitamente no **Streamlit Community Cloud**
(share.streamlit.io). Você só precisa de uma conta no GitHub.

---

## ✅ O que já está pronto

- Repositório git inicializado e com o primeiro commit feito
- `data/processed`, `data/quality` e `data/exemplo.csv` **incluídos** no repositório
  (o site publicado usa esses arquivos para exibir o dashboard)
- Tema configurado em `.streamlit/config.toml`
- `requirements.txt` na raiz (o Streamlit Cloud instala automaticamente)

---

## Passo 1 — Criar o repositório no GitHub

1. Acesse **https://github.com/new**
2. **Repository name**: `datapipeline-pro` (ou outro nome)
3. Deixe como **Public** (importante para o recrutador ver)
4. **Não** marque "Add a README file" nem crie `.gitignore` (já temos tudo)
5. Clique em **Create repository**

## Passo 2 — Enviar o projeto para o GitHub

No terminal do projeto, rode (substitua `SEU_USUARIO`):

```bash
git remote add origin https://github.com/SEU_USUARIO/datapipeline-pro.git
git push -u origin main
```

> O GitHub vai pedir seu login/senha. Se não aceitar a senha, use um **token**:
> GitHub → Settings → Developer settings → Personal access tokens → Generate new token
> (marque a opção `repo`) e use-o como senha.

## Passo 3 — Criar o app no Streamlit Community Cloud

1. Acesse **https://share.streamlit.io** e entre com seu **GitHub**
   (o cadastro também é feito pelo GitHub)
2. Clique em **New app**
3. Selecione: **Repository** = `SEU_USUARIO/datapipeline-pro`
4. **Branch** = `main` · **Main file path** = `dashboard/app.py`
5. Clique em **Deploy** ☁️

Em ~1–2 minutos o site estará no ar com um link público do tipo:
`https://SEU_USUARIO-datapipeline-pro.streamlit.app`

## Passo 4 — Compartilhar

Envie o link no seu currículo, LinkedIn e no e-mail para o recrutador! 🎉

---

## Atualizar o site depois

Qualquer alteração no código é publicada automaticamente ao dar push:

```bash
git add .
git commit -m "atualização"
git push
```

---

## Alternativas de hospedagem

| Plataforma | Como | Observação |
|------------|------|------------|
| **Hugging Face Spaces** | criar Space (SDK: Streamlit) → `app_file: dashboard/app.py` | sem precisar de GitHub |
| **Railway / Render** | novo serviço web → comando `streamlit run dashboard/app.py` | plano gratuito limitado |
| **Docker (próprio servidor)** | `docker compose up` + expor porta | controle total |

---

## ⚠️ Observações

- O site publicado exibe os dados da **camada processada** (commitada no repo).
  Para atualizar os dados, rode o pipeline localmente e faça push das novas CSVs.
- O **PostgreSQL** não roda no deploy gratuito — o site usa o fallback de CSVs,
  que é o comportamento esperado e documentado no projeto.
