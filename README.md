# 🚀 DataPipeline Pro — Engenharia de Dados com Python & SQL

> Pipeline completo de dados de **negócios locais**: ingestão (API/CSV) → transformação
> (Python + SQL) → armazenamento (PostgreSQL/SQLite) → qualidade de dados → **dashboard interativo**.

Este projeto simula um ambiente real de Engenharia de Dados: modelagem em **camadas**
(bronze → silver → gold), **star schema**, validação de qualidade, **observabilidade**
(log de execuções) e um painel analítico em Streamlit — tudo reproduzível com um comando.

---

## 🏗️ Arquitetura

```
                ┌──────────────────────────────────────────────────────────┐
                │                    PIPELINE ETL (Python)                 │
                │                                                          │
  CSV ────────► │  1. EXTRAÇÃO      2. TRANSFORMAÇÃO     3. CARGA         │
                │  ──────────       ─────────────────    ─────────        │
  Mock API ───► │  ingestão         limpeza · normaliza  schema + staging │
  (localhost)   │  (paginada)       star schema · métricas  dims + fato    │
                │                                   │     views analíticas │
                └───────────────────────────────────┼──────────────────────┘
                                                    ▼
                              ┌──────────────────────────────────┐
                              │    PostgreSQL (produção)          │
                              │    SQLite (fallback automático)   │
                              └──────────────────────────────────┘
                                                    │
                                                    ▼
                                        ┌─────────────────────┐
                                        │  DASHBOARD (Streamlit)│
                                        │  KPIs · rankings ·   │
                                        │  filtros · qualidade │
                                        └─────────────────────┘
```

### Modelagem em camadas (data lakehouse)

| Camada | Tabelas | Papel |
|--------|---------|-------|
| 🟦 **Bronze** | `stg_businesses`, `stg_transactions` | Dados brutos como foram ingeridos (com duplicatas e erros — sem constraints) |
| 🟪 **Silver** | `dim_category`, `dim_time`, `dim_business` | Dimensões normalizadas com chaves substitutas |
| 🟩 **Gold** | `fact_sales`, views `vw_*` | Fato + marts analíticos prontos para consumo |

```
        ┌──────────────┐        ┌──────────────┐
        │  dim_category │◄──────│  dim_business │
        └──────────────┘        └──────┬───────┘
                                       │
                              ┌────────▼────────┐        ┌────────────┐
                              │   fact_sales    │───────►│  dim_time  │
                              └─────────────────┘        └────────────┘
```

---

## ⚙️ Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| ETL & automação | **Python** (pandas, SQLAlchemy, psycopg) |
| Armazenamento | **PostgreSQL** (Docker) com **fallback SQLite** |
| Transformações | **SQL** (DDL, views analíticas, quality checks) |
| Dashboard | **Streamlit + Plotly** |
| Qualidade | Checks de completude, unicidade, consistência, faixa e formato |
| Testes | **pytest** |

---

## 📁 Estrutura do projeto

```
├── api/                  # Mock API de negócios locais (páginação real)
├── dashboard/            # 🌐 SITE de análise de dados (Streamlit)
│   ├── app.py            # Landing page (hero, arquitetura, CTAs)
│   ├── pages/            # Visão Geral · Análises · Qualidade · Analisador
│   ├── analisador.py     # Motor de análise automática de CSVs
│   └── utils.py          # Carregamento de dados + tema
├── data/
│   ├── raw/              # Bronze: CSVs ingeridos (brutos)
│   ├── processed/        # Silver/Gold: dims, fato e métricas
│   ├── quality/          # Relatórios de qualidade (JSON)
│   └── exemplo.csv       # Amostra para testar o Analisador
├── etl/                  # Pacote reutilizável (config, db, extract, transform, load, quality)
├── scripts/              # CLI do pipeline (generate, extract, transform, load, quality, run)
├── sql/
│   ├── 01_schema.sql     # DDL portável (PostgreSQL/SQLite)
│   ├── 02_marts.sql      # Views analíticas (camada gold)
│   └── 03_quality_checks.sql  # Qualidade executada direto no banco
├── .streamlit/           # Tema global do site
└── tests/                # Testes unitários (25 testes)
```

---

## 🔄 Pipeline de dados

### 1. Extração
- **CSV**: lê `data/raw` (gerado pelo `generate_data.py` com **CNPJ válido** — dígitos verificadores reais).
- **API**: consome a mock API local (`/api/v1/businesses`, `/api/v1/transactions`) com **paginação**.
- Rastreabilidade: timestamp de ingestão (`data_ingestao`) em cada registro.

### 2. Transformação
- Limpeza: remoção de **duplicatas**, tratamento de **nulos**, **valores negativos** e transações órfãs.
- Padronização: CNPJ (máscara + validação), datas em **formatos mistos**, valores `R$ 1.234,56` → float, maiúsculas.
- Modelagem: chaves substitutas, `dim_time` (sazonalidade), métricas derivadas (`ticket_medio`, receita por negócio).

### 3. Carga
- Cria schema, carrega staging (bronze), faz **upsert** nas dimensões e **recarga completa** da fato (idempotente).
- Executa as views analíticas (gold) e registra cada etapa em `pipeline_executions`.

### 4. Qualidade de dados
- **16 checks** automáticos: completude, unicidade, consistência, faixa (avaliação 1–5) e formato (CNPJ).
- Relatório **antes vs depois** em JSON + checks via **SQL** direto no banco.

> 📊 Exemplo real de um run: qualidade de **10/16 → 16/16** checks aprovados,
> removendo ~12 mil registros inválidos de 369 mil vendas brutas.

---

## 🚀 Como executar

### Pré-requisitos
- Python 3.10+
- (Opcional) Docker — para PostgreSQL; sem ele, o pipeline usa SQLite automaticamente

### Passo a passo

```bash
# 1. Banco PostgreSQL (opcional — usa SQLite se estiver fora)
docker compose up -d

# 2. Ambiente Python
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt

# 3. Gerar dados sintéticos (com defeitos propositais para a demo de qualidade)
python scripts/generate_data.py --businesses 120 --dias 1260

# 4. Rodar o pipeline completo (extração → transformação → qualidade → carga)
python scripts/run_pipeline.py

# 5. Abrir o dashboard
streamlit run dashboard/app.py
```

### Etapas individuais (opcional)

```bash
python scripts/extract.py                # extração (auto: CSV → API)
python scripts/extract.py --fonte api    # ingestão via mock API (rode antes: python api/mock_api.py)
python scripts/transform.py              # limpeza + modelagem + relatório de qualidade
python scripts/load.py                   # carga no banco (--reset-db para recriar o schema)
python scripts/quality_check.py          # relatório antes vs depois (arquivos)
python scripts/quality_check.py --banco  # checks SQL no banco (camada gold)

python -m pytest tests -q                # testes unitários
```

---

## 🌐 Site de análise de dados

O projeto é um **site completo** (Streamlit) com tema próprio "console de operações de dados":

| Página | Conteúdo |
|--------|----------|
| **🏠 Início** (landing) | Hero com pipeline visual, estatísticas ao vivo, arquitetura em camadas e CTAs |
| **📈 Visão Geral** | KPIs (receita, vendas, ticket, negócios, avaliação) · receita mensal · ranking top 10 · receita por cidade · sazonalidade · canais — com **filtros dinâmicos** (categoria, cidade, período) |
| **📊 Análises Estratégicas** | Heatmap categoria × mês · ticket médio · perfil receita × avaliação · Pareto 80/20 · dia útil vs fim de semana · evolução de canais · pagamentos · avaliações · tendência MoM |
| **✅ Qualidade de Dados** | Checks antes vs depois · linhagem das camadas (bronze/silver/gold) · log de execuções do pipeline |
| **📤 Analisador de Arquivos** | Envie **qualquer CSV** e receba KPIs, tipos detectados, histogramas, correlações, distribuições e insights automáticos (ou teste com `data/exemplo.csv`) |

O site lê do **banco de dados** e, se indisponível, dos CSVs processados — nunca quebra na demo.

---

## 🌍 Publicar na internet (deploy gratuito)

O site pode ser publicado **de graça** no [Streamlit Community Cloud](https://streamlit.io/cloud):

1. Suba o projeto para um repositório no GitHub (incluindo `data/exemplo.csv`).
2. Acesse [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Selecione o repositório e defina: **Main file = `dashboard/app.py`**.
4. Clique em **Deploy**. Em ~1 minuto você terá um link público para enviar ao recrutador. 🎉

> Alternativas: Hugging Face Spaces (`app_file: dashboard/app.py`), Railway ou Render.
> O pipeline roda localmente — o site publicado usa `data/processed` + `data/exemplo.csv`
> (commitados no repositório) para exibir o dashboard e o analisador.

---

## ✅ Diferenciais para o portfólio

- **Arquitetura em camadas** (bronze/silver/gold) e **star schema** com chaves substitutas
- **Idempotência**: rerun seguro (upsert + recarga da fato por batch)
- **Fallback de banco**: PostgreSQL em produção, SQLite na demo — 100% reproduzível
- **Qualidade de dados** com relatório quantificado antes vs depois
- **Observabilidade**: logs, tabela `pipeline_executions` e views de linhagem
- **Ingestão via API com paginação** e dados sintéticos com **CNPJ válido de verdade**
- **Testes unitários** (16) e SQL portável entre dois dialetos
- 100% **em português**, comentado e documentado

---

## 🗺️ Roadmap (próximos passos)

- Orquestração com **Airflow** / Prefect
- Testes de qualidade com **Great Expectations**
- Transformações com **dbt** e materialização incremental
- Escrita em **Parquet** e partição por data
- Dashboard multi-tenant com autenticação

---

## 👨‍💻 Autor

**Tarcisio Alves** — Engenharia de Dados | Python | SQL | Automação
