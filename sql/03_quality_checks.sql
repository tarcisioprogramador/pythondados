-- ============================================================
-- DataPipeline Pro — Qualidade de dados no banco (SQL)
-- Roda com: python scripts/quality_check.py --banco
-- ============================================================

-- Diagnóstico de integridade e consistência da camada gold
DROP VIEW IF EXISTS vw_qualidade_dados;
CREATE VIEW vw_qualidade_dados AS
SELECT 'fato_sem_negocio'        AS check_sql, COUNT(*) AS quantidade
FROM fact_sales f LEFT JOIN dim_business b USING (business_key)
WHERE b.business_key IS NULL

UNION ALL
SELECT 'fato_sem_data', COUNT(*)
FROM fact_sales f LEFT JOIN dim_time t USING (date_key)
WHERE t.date_key IS NULL

UNION ALL
SELECT 'fato_valor_invalido', COUNT(*)
FROM fact_sales WHERE valor <= 0 OR valor IS NULL

UNION ALL
SELECT 'fato_avaliacao_fora_faixa', COUNT(*)
FROM fact_sales WHERE avaliacao IS NOT NULL AND (avaliacao < 1 OR avaliacao > 5)

UNION ALL
SELECT 'duplicados_transaction_id', COUNT(*) - COUNT(DISTINCT transaction_id)
FROM fact_sales

UNION ALL
SELECT 'dimensao_sem_fato', COUNT(*)
FROM dim_business b LEFT JOIN fact_sales f USING (business_key)
WHERE f.sale_key IS NULL;

-- Totais por tabela (para acompanhar volume de dados)
DROP VIEW IF EXISTS vw_totais_tabelas;
CREATE VIEW vw_totais_tabelas AS
SELECT 'stg_businesses'     AS tabela, COUNT(*) AS registros FROM stg_businesses
UNION ALL SELECT 'stg_transactions', COUNT(*) FROM stg_transactions
UNION ALL SELECT 'dim_category',     COUNT(*) FROM dim_category
UNION ALL SELECT 'dim_time',         COUNT(*) FROM dim_time
UNION ALL SELECT 'dim_business',     COUNT(*) FROM dim_business
UNION ALL SELECT 'fact_sales',       COUNT(*) FROM fact_sales
UNION ALL SELECT 'pipeline_executions', COUNT(*) FROM pipeline_executions;
