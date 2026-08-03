"""Camada de carga: schema, staging, dimensões, fato, marts e log de execução."""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl import config
from etl.database import executar_arquivo_sql

logger = logging.getLogger("datapipeline.load")

# Chave natural de cada dimensão (usada no upsert portável)
CHAVES_DIMENSOES = {
    "dim_category": "categoria",
    "dim_time": "date_key",
    "dim_business": "business_id",
}

# Coluna de chave primária (substituta) de cada dimensão
COLUNAS_PK = {
    "dim_category": "category_key",
    "dim_time": "date_key",
    "dim_business": "business_key",
}

# Tipos esperados por tabela — usados na coerção antes do insert para que a
# carga funcione tanto no PostgreSQL (tipagem forte) quanto no SQLite.
TIPOS_COLUNAS: dict[str, dict[str, str]] = {
    "dim_category": {"category_key": "int", "categoria": "text", "setor": "text"},
    "dim_time": {
        "date_key": "int", "data": "text", "ano": "int", "mes": "int", "dia": "int",
        "trimestre": "int", "dia_semana": "int", "nome_mes": "text",
        "nome_dia_semana": "text", "fim_semana": "int",
    },
    "dim_business": {
        "business_key": "int", "business_id": "text", "nome": "text", "cnpj": "text",
        "categoria": "text", "categoria_key": "int", "cidade": "text", "estado": "text",
        "regiao": "text", "endereco": "text", "data_abertura": "text",
        "num_funcionarios": "int", "email": "text", "telefone": "text",
    },
    "fact_sales": {
        "sale_key": "int", "transaction_id": "text", "business_key": "int", "date_key": "int",
        "valor": "real", "quantidade": "real", "ticket_medio": "real",
        "forma_pagamento": "text", "canal": "text", "avaliacao": "real", "batch_id": "text",
    },
}


def _coercao(df: pd.DataFrame, tabela: str) -> pd.DataFrame:
    """Ajusta os tipos do DataFrame ao schema da tabela antes do insert.

    O pandas envia bool/float/datetime para colunas INTEGER/TEXT/REAL, o que
    quebraria no PostgreSQL (tipagem forte). Aqui convertemos:
      - bool -> int (fim_semana)
      - float sem NaN -> int (num_funcionarios, chaves)
      - datetime -> texto ISO (data_abertura)
      - NaN/NaT -> None (NULL no banco)
    """
    df = df.copy()
    tipos = TIPOS_COLUNAS.get(tabela, {})
    colunas = tipos.keys() if tipos else df.columns

    for col in colunas:
        if col not in df.columns:
            continue
        tipo = tipos.get(col, "text") if tipos else "text"
        if tipo == "int":
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].astype("Int64")  # inteiro anulável (NA -> NULL)
        elif tipo == "real":
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:  # text
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")  # NaT -> NaN
            df[col] = df[col].where(df[col].notna(), None)
    return df

TABELAS = ["fact_sales", "dim_business", "dim_time", "dim_category",
           "stg_transactions", "stg_businesses", "pipeline_executions"]


def resetar_banco(engine: Engine) -> None:
    """Apaga todas as tabelas do pipeline (ordem respeitando as foreign keys)."""
    with engine.begin() as conn:
        for tabela in TABELAS:
            conn.execute(text(f"DROP TABLE IF EXISTS {tabela}"))
    logger.info("🗑️  Banco resetado: %d tabela(s) removida(s)", len(TABELAS))


def criar_schema(engine: Engine) -> None:
    """Cria as tabelas (camadas bronze e silver) a partir de sql/01_schema.sql."""
    executar_arquivo_sql(engine, config.SQL_DIR / "01_schema.sql")


def executar_marts(engine: Engine) -> None:
    """Cria/atualiza as views analíticas (camada gold) de sql/02_marts.sql."""
    executar_arquivo_sql(engine, config.SQL_DIR / "02_marts.sql")


def carregar_staging(engine: Engine, dados: dict[str, pd.DataFrame]) -> None:
    """Recarrega as tabelas de staging (bronze) — truncate + insert."""
    with engine.begin() as conn:
        for nome in ("stg_businesses", "stg_transactions"):
            conn.execute(text(f"DELETE FROM {nome}"))

        for tabela, coluna_bruta in (("stg_businesses", "businesses"), ("stg_transactions", "transactions")):
            df = dados.get(coluna_bruta)
            if df is None or df.empty:
                continue
            df = _coercao(df, tabela)
            df.to_sql(tabela, conn, if_exists="append", index=False)
            logger.info("📥 Staging carregada: %s (%d linhas)", tabela, len(df))


def carregar_dimensoes(engine: Engine, dimensoes: dict[str, pd.DataFrame]) -> None:
    """Faz upsert nas dimensões (silver): insere apenas chaves novas.

    Chaves substitutas posicionais (1..N) podem colidir com linhas existentes
    em reruns com dados novos — por isso reatribuímos as chaves das linhas
    novas a partir do MAX atual da tabela.
    """
    with engine.begin() as conn:
        for tabela, df in dimensoes.items():
            chave = CHAVES_DIMENSOES[tabela]
            col_pk = COLUNAS_PK[tabela]
            df = _coercao(df, tabela)
            existentes = set(pd.read_sql(f'SELECT "{chave}" FROM "{tabela}"', conn)[chave])
            novos = df[~df[chave].isin(existentes)].copy()
            if not novos.empty:
                if col_pk != chave:  # dim_time usa date_key como chave natural
                    max_pk = conn.execute(text(f'SELECT COALESCE(MAX("{col_pk}"), 0) FROM "{tabela}"')).scalar()
                    novos[col_pk] = range(int(max_pk) + 1, int(max_pk) + 1 + len(novos))
                novos.to_sql(tabela, conn, if_exists="append", index=False)
            logger.info("🗂️  Dimensão %s: %d novas de %d", tabela, len(novos), len(df))


def carregar_fato(engine: Engine, fato: pd.DataFrame, batch_id: str) -> None:
    """Carrega a tabela fato (gold) — recarga completa (ETL full refresh).

    Recarregar a fato inteira garante idempotência: rodar o pipeline
    novamente não duplica linhas nem viola a unicidade de transaction_id.
    """
    if fato is None or fato.empty:
        logger.warning("⚠️  Fato vazio — nada a carregar.")
        return
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fact_sales"))
        _coercao(fato, "fact_sales").to_sql("fact_sales", conn, if_exists="append", index=False)
        logger.info("📈 Fato carregada: %d linhas (batch %s)", len(fato), batch_id)


def registrar_execucao(
    engine: Engine,
    etapa: str,
    status: str,
    registros: int = 0,
    duracao_seg: float = 0.0,
    detalhes: str = "",
) -> None:
    """Registra cada etapa do pipeline na tabela pipeline_executions (observabilidade)."""
    try:
        with engine.begin() as conn:
            max_id = conn.execute(text("SELECT COALESCE(MAX(execution_id), 0) FROM pipeline_executions")).scalar()
            conn.execute(
                text(
                    "INSERT INTO pipeline_executions "
                    "(execution_id, data_execucao, etapa, status, registros, duracao_seg, detalhes) "
                    "VALUES (:id, :data, :etapa, :status, :reg, :dur, :det)"
                ),
                {
                    "id": int(max_id) + 1,
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "etapa": etapa,
                    "status": status,
                    "reg": registros,
                    "dur": round(duracao_seg, 2),
                    "det": detalhes[:500],
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("⚠️  Não foi possível registrar execução (%s): %s", etapa, exc)
