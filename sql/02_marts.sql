-- ============================================================
-- DataPipeline Pro — Marts analíticos (camada GOLD)
-- Views SQL consumidas pelo dashboard.
-- Padrão DROP IF EXISTS + CREATE: portável PostgreSQL/SQLite e
-- idempotente (pode ser executado várias vezes).
-- ============================================================

-- KPIs globais do negócio
DROP VIEW IF EXISTS vw_kpis_gerais;
CREATE VIEW vw_kpis_gerais AS
SELECT
    COUNT(*)                            AS total_vendas,
    ROUND(SUM(f.valor), 2)              AS receita_total,
    ROUND(AVG(f.valor), 2)              AS ticket_medio,
    COUNT(DISTINCT f.business_key)      AS negocios_ativos,
    ROUND(AVG(f.avaliacao), 2)          AS avaliacao_media,
    MIN(t.data)                         AS primeira_venda,
    MAX(t.data)                         AS ultima_venda
FROM fact_sales f
LEFT JOIN dim_time t ON f.date_key = t.date_key;

-- Receita, volume e ticket médio por mês
DROP VIEW IF EXISTS vw_receita_mensal;
CREATE VIEW vw_receita_mensal AS
SELECT
    t.ano,
    t.mes,
    t.nome_mes,
    ROUND(SUM(f.valor), 2) AS receita,
    COUNT(*)               AS qtd_vendas,
    ROUND(AVG(f.valor), 2) AS ticket_medio
FROM fact_sales f
JOIN dim_time t ON f.date_key = t.date_key
GROUP BY t.ano, t.mes, t.nome_mes
ORDER BY t.ano, t.mes;

-- Ranking de negócios (receita, ticket médio e avaliação)
DROP VIEW IF EXISTS vw_ranking_negocios;
CREATE VIEW vw_ranking_negocios AS
SELECT
    b.business_key,
    b.nome,
    b.categoria,
    b.cidade,
    b.estado,
    COUNT(*)                AS qtd_vendas,
    ROUND(SUM(f.valor), 2)  AS receita_total,
    ROUND(AVG(f.valor), 2)  AS ticket_medio,
    ROUND(AVG(f.avaliacao), 2) AS avaliacao_media
FROM fact_sales f
JOIN dim_business b ON f.business_key = b.business_key
GROUP BY b.business_key, b.nome, b.categoria, b.cidade, b.estado;

-- Vendas por categoria de negócio
DROP VIEW IF EXISTS vw_vendas_por_categoria;
CREATE VIEW vw_vendas_por_categoria AS
SELECT
    c.categoria,
    c.setor,
    COUNT(*)                AS qtd_vendas,
    ROUND(SUM(f.valor), 2)  AS receita_total,
    ROUND(AVG(f.valor), 2)  AS ticket_medio
FROM fact_sales f
JOIN dim_business b ON f.business_key = b.business_key
JOIN dim_category c  ON b.categoria_key = c.category_key
GROUP BY c.categoria, c.setor
ORDER BY receita_total DESC;

-- Vendas por cidade / região
DROP VIEW IF EXISTS vw_vendas_por_cidade;
CREATE VIEW vw_vendas_por_cidade AS
SELECT
    b.cidade,
    b.estado,
    b.regiao,
    COUNT(*)                AS qtd_vendas,
    ROUND(SUM(f.valor), 2)  AS receita_total
FROM fact_sales f
JOIN dim_business b ON f.business_key = b.business_key
GROUP BY b.cidade, b.estado, b.regiao
ORDER BY receita_total DESC;

-- Distribuição por forma de pagamento
DROP VIEW IF EXISTS vw_formas_pagamento;
CREATE VIEW vw_formas_pagamento AS
SELECT
    f.forma_pagamento,
    COUNT(*)                AS qtd_vendas,
    ROUND(SUM(f.valor), 2)  AS receita_total
FROM fact_sales f
GROUP BY f.forma_pagamento
ORDER BY receita_total DESC;

-- Distribuição por canal de venda
DROP VIEW IF EXISTS vw_canais;
CREATE VIEW vw_canais AS
SELECT
    f.canal,
    COUNT(*)                AS qtd_vendas,
    ROUND(SUM(f.valor), 2)  AS receita_total
FROM fact_sales f
GROUP BY f.canal
ORDER BY receita_total DESC;

-- Sazonalidade por dia da semana
DROP VIEW IF EXISTS vw_sazonalidade_dia;
CREATE VIEW vw_sazonalidade_dia AS
SELECT
    t.dia_semana,
    t.nome_dia_semana,
    COUNT(*)                AS qtd_vendas,
    ROUND(SUM(f.valor), 2)  AS receita_total
FROM fact_sales f
JOIN dim_time t ON f.date_key = t.date_key
GROUP BY t.dia_semana, t.nome_dia_semana
ORDER BY t.dia_semana;

-- Sazonalidade por mês (agrega todos os anos)
DROP VIEW IF EXISTS vw_sazonalidade_mes;
CREATE VIEW vw_sazonalidade_mes AS
SELECT
    t.mes,
    t.nome_mes,
    COUNT(*)                AS qtd_vendas,
    ROUND(SUM(f.valor), 2)  AS receita_total
FROM fact_sales f
JOIN dim_time t ON f.date_key = t.date_key
GROUP BY t.mes, t.nome_mes
ORDER BY t.mes;

-- Distribuição das avaliações
DROP VIEW IF EXISTS vw_avaliacoes;
CREATE VIEW vw_avaliacoes AS
SELECT
    ROUND(f.avaliacao, 0) AS avaliacao,
    COUNT(*)              AS qtd_vendas
FROM fact_sales f
WHERE f.avaliacao IS NOT NULL
GROUP BY ROUND(f.avaliacao, 0)
ORDER BY avaliacao;

-- Linhagem: contagem de registros por camada e tabela
DROP VIEW IF EXISTS vw_linhagem;
CREATE VIEW vw_linhagem AS
SELECT 'bronze' AS camada, 'stg_businesses'  AS tabela, COUNT(*) AS registros FROM stg_businesses
UNION ALL
SELECT 'bronze', 'stg_transactions', COUNT(*) FROM stg_transactions
UNION ALL
SELECT 'silver', 'dim_category',      COUNT(*) FROM dim_category
UNION ALL
SELECT 'silver', 'dim_time',          COUNT(*) FROM dim_time
UNION ALL
SELECT 'silver', 'dim_business',      COUNT(*) FROM dim_business
UNION ALL
SELECT 'gold',   'fact_sales',        COUNT(*) FROM fact_sales;

-- Últimas execuções do pipeline (observabilidade)
DROP VIEW IF EXISTS vw_ultimas_execucoes;
CREATE VIEW vw_ultimas_execucoes AS
SELECT
    execution_id,
    data_execucao,
    etapa,
    status,
    registros,
    duracao_seg
FROM pipeline_executions
ORDER BY execution_id DESC
LIMIT 50;
