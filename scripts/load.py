"""Etapa 3 — Carga: grava os dados transformados no banco de dados.

Conecta no PostgreSQL (via docker-compose) ou cai para SQLite
automaticamente. Executa o schema, carrega staging/dimensões/fato,
cria as views analíticas (gold) e registra as execuções.

Uso:
    python scripts/load.py                 # carga normal (idempotente)
    python scripts/load.py --reset-db      # recria todas as tabelas do zero
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl import config  # noqa: E402
from etl.database import conectar, vendor  # noqa: E402
from etl.extractors import extrair_csv  # noqa: E402
from etl.loaders import (  # noqa: E402
    carregar_dimensoes,
    carregar_fato,
    carregar_staging,
    criar_schema,
    executar_marts,
    registrar_execucao,
    resetar_banco,
)
from etl.logging_config import configurar_logging  # noqa: E402


def ler_processados() -> dict[str, pd.DataFrame]:
    """Lê a camada silver/gold gerada pelo transform.py."""
    pasta = config.DATA_PROCESSED_DIR
    return {
        "dim_category": pd.read_csv(pasta / "dim_category.csv"),
        "dim_time": pd.read_csv(pasta / "dim_time.csv"),
        "dim_business": pd.read_csv(pasta / "dim_business.csv"),
        "fact_sales": pd.read_csv(pasta / "fact_sales.csv"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Etapa 3 — Carga no banco de dados.")
    parser.add_argument("--reset-db", action="store_true", help="Recria o schema do zero")
    args = parser.parse_args()

    configurar_logging()
    engine = conectar()

    if args.reset_db:
        resetar_banco(engine)

    # 1) Schema
    t0 = time.time()
    criar_schema(engine)
    registrar_execucao(engine, "schema", "OK", duracao_seg=time.time() - t0)

    # 2) Staging (bronze) a partir dos dados brutos
    t0 = time.time()
    bruto = extrair_csv()
    carregar_staging(engine, bruto)
    registrar_execucao(engine, "staging", "OK", duracao_seg=time.time() - t0)

    # 3) Dimensões + fato (silver/gold) a partir do processado
    t0 = time.time()
    processado = ler_processados()
    carregar_dimensoes(
        engine,
        {chave: processado[chave] for chave in ("dim_category", "dim_time", "dim_business")},
    )

    fato = processado["fact_sales"]
    batch_id = str(fato["batch_id"].iloc[0]) if "batch_id" in fato.columns else ""
    carregar_fato(engine, fato, batch_id)
    registrar_execucao(engine, "carga_silver_gold", "OK",
                       registros=len(fato), duracao_seg=time.time() - t0)

    # 4) Views analíticas (gold)
    t0 = time.time()
    executar_marts(engine)
    registrar_execucao(engine, "marts", "OK", duracao_seg=time.time() - t0)

    print(f"\n✅ Carga concluída no banco: {vendor(engine)}!")
    print(f"   Fato carregada: {len(fato):,} vendas (batch {batch_id})".replace(",", "."))
    print("\n")


if __name__ == "__main__":
    main()
