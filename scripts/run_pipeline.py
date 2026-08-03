"""Orquestrador do pipeline completo: extrair → transformar → carregar → validar.

Um único comando para demonstrar todo o fluxo de engenharia de dados,
com medição de tempo por etapa, logs e relatório de qualidade.

Uso:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --fonte api --reset-db
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl import config  # noqa: E402
from etl.extractors import extrair  # noqa: E402
from etl.logging_config import configurar_logging  # noqa: E402
from etl.quality import executar_relatorio_qualidade, salvar_relatorio  # noqa: E402
from etl.transformers import transformar  # noqa: E402


def _etapa(nome: str) -> float:
    print(f"\n{'=' * 70}\n  ▶  ETAPA: {nome}\n{'=' * 70}")
    return time.time()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline ETL completo — DataPipeline Pro.")
    parser.add_argument("--fonte", choices=["auto", "csv", "api"], default="auto",
                        help="Fonte de dados (padrão: auto)")
    parser.add_argument("--reset-db", action="store_true",
                        help="Recria o schema do banco antes de carregar")
    args = parser.parse_args()

    logger = configurar_logging()
    tempos: dict[str, float] = {}

    # 1) EXTRAÇÃO ----------------------------------------------------------
    t = _etapa("Extração (ingestão de dados)")
    t0 = t
    extrato_bruto = extrair(args.fonte)
    for nome, df in extrato_bruto.items():
        df.to_csv(config.DATA_RAW_DIR / f"{nome}.csv", index=False, encoding="utf-8")
        logger.info("💾 dados brutos persistidos: %s (%d registros)", nome, len(df))
    tempos["extracao"] = time.time() - t0

    # 2) TRANSFORMAÇÃO -----------------------------------------------------
    t = _etapa("Transformação (limpeza + modelagem star schema)")
    t0 = t
    transformado = transformar(extrato_bruto)
    from etl.transformers import salvar_transformados
    salvar_transformados(transformado)
    tempos["transformacao"] = time.time() - t0

    # 3) QUALIDADE (antes vs depois) --------------------------------------
    t = _etapa("Qualidade de dados (relatório antes vs depois)")
    t0 = t
    relatorio = executar_relatorio_qualidade(extrato_bruto, transformado)
    caminho_qualidade = salvar_relatorio(relatorio)
    tempos["qualidade"] = time.time() - t0

    # 4) CARGA ------------------------------------------------------------
    t = _etapa("Carga no banco (PostgreSQL/SQLite)")
    t0 = t
    from etl.database import conectar
    from etl.loaders import (carregar_dimensoes, carregar_fato, carregar_staging,
                             criar_schema, executar_marts, registrar_execucao)
    engine = conectar()

    if args.reset_db:
        from etl.loaders import resetar_banco
        resetar_banco(engine)

    criar_schema(engine)
    carregar_staging(engine, extrato_bruto)
    carregar_dimensoes(engine, {
        "dim_category": transformado["dim_category"],
        "dim_time": transformado["dim_time"],
        "dim_business": transformado["dim_business"],
    })
    fato = transformado["fact_sales"]
    carregar_fato(engine, fato, str(fato["batch_id"].iloc[0]))
    executar_marts(engine)
    tempos["carga"] = time.time() - t0
    registrar_execucao(engine, "pipeline_completo", "OK",
                       registros=len(fato), duracao_seg=sum(tempos.values()))

    # 5) RESUMO FINAL -----------------------------------------------------
    from etl.database import vendor

    caminho_log = next(
        (h.baseFilename for h in logger.handlers if hasattr(h, "baseFilename")),
        "logs/",
    )
    print(f"\n{'=' * 70}")
    print("  🎉 PIPELINE CONCLUÍDO COM SUCESSO")
    print(f"{'=' * 70}")
    print(f"  {'Etapa':<18s} {'Tempo':>8s}   {'Detalhe'}")
    print("  " + "-" * 60)
    for etapa, seg in tempos.items():
        print(f"  {etapa:<18s} {seg:>6.2f}s")
    print(f"  {'TOTAL':<18s} {sum(tempos.values()):>6.2f}s")
    print(f"  Banco          : {vendor(engine)}")
    print(f"  Vendas carregadas: {len(fato):,}".replace(",", "."))
    print(f"  Relatório qualidade: {caminho_qualidade}")
    print(f"  Log            : {caminho_log}")
    print(f"\n  ▶ Próximo passo: streamlit run dashboard/app.py\n")


if __name__ == "__main__":
    main()
