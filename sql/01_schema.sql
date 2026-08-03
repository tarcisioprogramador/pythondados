-- ============================================================
-- DataPipeline Pro — Schema do banco de dados
-- Modelagem em camadas (data lakehouse):
--   BRONZE  → staging (dados brutos, sem tratamento)
--   SILVER  → dimensões normalizadas (star schema)
--   GOLD    → tabela fato + views analíticas (sql/02_marts.sql)
--
-- SQL portável: roda em PostgreSQL (produção) e SQLite (demo).
-- ============================================================

-- ------------------------------------------------------------------
-- CAMADA BRONZE — staging (dados exatamente como foram ingeridos)
-- Observação: sem constraints de unicidade — a camada bronze preserva
-- os dados brutos (inclusive duplicatas). Quem garante a unicidade é a
-- camada silver (dimensões) e a gold (fato).
-- ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS stg_businesses (
    business_id       TEXT,
    nome              TEXT,
    cnpj              TEXT,
    categoria         TEXT,
    setor             TEXT,
    cidade            TEXT,
    estado            TEXT,
    endereco          TEXT,
    data_abertura     TEXT,
    num_funcionarios  TEXT,
    email             TEXT,
    telefone          TEXT,
    data_ingestao     TEXT
);

CREATE TABLE IF NOT EXISTS stg_transactions (
    transaction_id   TEXT,
    business_id      TEXT,
    data_venda       TEXT,
    valor            TEXT,
    quantidade       TEXT,
    forma_pagamento  TEXT,
    canal            TEXT,
    avaliacao        TEXT,
    data_ingestao    TEXT
);

-- ------------------------------------------------------------------
-- CAMADA SILVER — dimensões
-- ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS dim_category (
    category_key  INTEGER PRIMARY KEY,
    categoria     TEXT UNIQUE NOT NULL,
    setor         TEXT
);

CREATE TABLE IF NOT EXISTS dim_time (
    date_key        INTEGER PRIMARY KEY,   -- AAAAMMDD
    data            TEXT NOT NULL,         -- ISO 8601
    ano             INTEGER,
    mes             INTEGER,
    dia             INTEGER,
    trimestre       INTEGER,
    dia_semana      INTEGER,               -- 0 = segunda-feira
    nome_mes        TEXT,
    nome_dia_semana TEXT,
    fim_semana      INTEGER
);

CREATE TABLE IF NOT EXISTS dim_business (
    business_key     INTEGER PRIMARY KEY,
    business_id      TEXT UNIQUE NOT NULL,
    nome             TEXT,
    cnpj             TEXT,
    categoria        TEXT,
    categoria_key    INTEGER,
    cidade           TEXT,
    estado           TEXT,
    regiao           TEXT,
    endereco         TEXT,
    data_abertura    TEXT,
    num_funcionarios INTEGER,
    email            TEXT,
    telefone         TEXT,
    FOREIGN KEY (categoria_key) REFERENCES dim_category (category_key)
);

-- ------------------------------------------------------------------
-- CAMADA GOLD — tabela fato
-- ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS fact_sales (
    sale_key        INTEGER PRIMARY KEY,
    transaction_id  TEXT UNIQUE NOT NULL,
    business_key    INTEGER NOT NULL,
    date_key        INTEGER NOT NULL,
    valor           REAL,
    quantidade      REAL,
    ticket_medio    REAL,
    forma_pagamento TEXT,
    canal           TEXT,
    avaliacao       REAL,
    batch_id        TEXT,
    FOREIGN KEY (business_key) REFERENCES dim_business (business_key),
    FOREIGN KEY (date_key)     REFERENCES dim_time (date_key)
);

-- ------------------------------------------------------------------
-- Observabilidade do pipeline
-- ------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pipeline_executions (
    execution_id  INTEGER PRIMARY KEY,
    data_execucao TEXT,
    etapa         TEXT,
    status        TEXT,
    registros     INTEGER,
    duracao_seg   REAL,
    detalhes      TEXT
);

-- Índices de performance para as consultas analíticas
CREATE INDEX IF NOT EXISTS idx_fact_business        ON fact_sales (business_key);
CREATE INDEX IF NOT EXISTS idx_fact_date            ON fact_sales (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_batch           ON fact_sales (batch_id);
CREATE INDEX IF NOT EXISTS idx_dim_business_cidade  ON dim_business (cidade);
CREATE INDEX IF NOT EXISTS idx_dim_business_categ   ON dim_business (categoria_key);
CREATE INDEX IF NOT EXISTS idx_fact_pagamento       ON fact_sales (forma_pagamento);
