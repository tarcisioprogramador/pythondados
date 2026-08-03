"""Etapa 2 — Transformação: limpeza, padronização e modelagem star schema.

Lê os dados brutos de data/raw, aplica as regras de qualidade e gera:
  - data/processed/dim_*.csv        (camada silver)
  - data/processed/fact_sales.csv   (camada gold)
  - data/quality/relatorio_*.json   (qualidade antes vs depois)

Uso:
    python scripts/transform.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl import config  # noqa: E402
from etl.extractors import extrair_csv  # noqa: E402
from etl.logging_config import configurar_logging  # noqa: E402
from etl.quality import executar_relatorio_qualidade, salvar_relatorio  # noqa: E402
from etl.transformers import salvar_transformados, transformar  # noqa: E402


def main() -> None:
    configurar_logging()

    # Lê os dados brutos e transforma
    extrato_bruto = extrair_csv()
    transformado = transformar(extrato_bruto)

    # Persiste a camada silver/gold
    salvar_transformados(transformado)

    # Relatório de qualidade: antes (bruto) vs depois (limpo)
    relatorio = executar_relatorio_qualidade(extrato_bruto, transformado)
    caminho = salvar_relatorio(relatorio)

    resumo = relatorio["resumo"]
    print("\n📋 Resumo de qualidade — antes vs depois:")
    print(f"   Antes : {resumo['antes']['pass']}/{resumo['antes']['total']} checks OK")
    print(f"   Depois: {resumo['depois']['pass']}/{resumo['depois']['total']} checks OK")
    print(f"   📄 Relatório completo: {caminho}")
    print("\n✅ Transformação concluída!\n")


if __name__ == "__main__":
    main()
