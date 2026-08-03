"""Checagem de qualidade de dados.

Modo arquivo (padrão): compara a qualidade dos dados brutos vs transformados.
Modo banco: executa os checks SQL (sql/03_quality_checks.sql) no banco.

Uso:
    python scripts/quality_check.py
    python scripts/quality_check.py --banco
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl import config  # noqa: E402
from etl.database import conectar, executar_arquivo_sql  # noqa: E402
from etl.extractors import extrair_csv  # noqa: E402
from etl.logging_config import configurar_logging  # noqa: E402
from etl.quality import executar_relatorio_qualidade, salvar_relatorio  # noqa: E402


def _imprimir_tabela_checks(checks: list[dict], titulo: str) -> None:
    print(f"\n{titulo}")
    print("-" * 88)
    for c in checks:
        icone = "✅" if c["status"] == "PASS" else "❌"
        print(f"  {icone} [{c['status']:4s}] {c['check']:<32s} {c['coluna']:<18s} valor={c['valor']:<10s} limite={c['limite']}")
    print("-" * 88)


def modo_arquivo() -> None:
    """Compara qualidade bruto vs transformado a partir dos CSVs."""
    bruto = extrair_csv()
    transformado = {
        "stg_businesses": pd.read_csv(config.DATA_PROCESSED_DIR / "stg_businesses.csv", dtype=str),
        "stg_transactions": pd.read_csv(config.DATA_PROCESSED_DIR / "stg_transactions.csv", dtype=str),
    }
    relatorio = executar_relatorio_qualidade(bruto, transformado)
    salvar_relatorio(relatorio)

    _imprimir_tabela_checks(relatorio["antes"], "QUALIDADE — ANTES (dados brutos)")
    _imprimir_tabela_checks(relatorio["depois"], "QUALIDADE — DEPOIS (dados limpos)")

    r = relatorio["resumo"]
    print(f"\n📈 Evolução: {r['antes']['pass']}/{r['antes']['total']} → {r['depois']['pass']}/{r['depois']['total']} checks OK")
    print("✅ Qualidade dos dados validada!\n")


def modo_banco() -> None:
    """Executa os checks SQL direto no banco (camada gold)."""
    engine = conectar()
    executar_arquivo_sql(engine, config.SQL_DIR / "03_quality_checks.sql")

    from sqlalchemy import text
    with engine.connect() as conn:
        print("\nCHECKS SQL NO BANCO (camada gold)")
        print("-" * 60)
        for linha in conn.execute(text("SELECT check_sql, quantidade FROM vw_qualidade_dados")):
            ok = "✅" if linha.quantidade == 0 else "❌"
            print(f"  {ok} {linha.check_sql:<32s} → {linha.quantidade}")

        print("\nTOTAIS POR TABELA")
        print("-" * 60)
        for linha in conn.execute(text("SELECT tabela, registros FROM vw_totais_tabelas")):
            print(f"  • {linha.tabela:<22s} → {linha.registros:>10,}".replace(",", "."))
    print("\n✅ Checagem no banco concluída!\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Checagem de qualidade de dados.")
    parser.add_argument("--banco", action="store_true", help="Roda os checks SQL no banco")
    args = parser.parse_args()

    configurar_logging()
    if args.banco:
        modo_banco()
    else:
        modo_arquivo()


if __name__ == "__main__":
    main()
