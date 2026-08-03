"""Etapa 1 — Extração: ingestão de dados via CSV ou mock API.

Uso:
    python scripts/extract.py                 # auto: CSV se existir, senão API
    python scripts/extract.py --fonte csv
    python scripts/extract.py --fonte api --url http://localhost:8000
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from etl import config  # noqa: E402
from etl.extractors import extrair  # noqa: E402
from etl.logging_config import configurar_logging  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Etapa 1 — Extração de dados.")
    parser.add_argument("--fonte", choices=["auto", "csv", "api"], default="auto",
                        help="Fonte de dados (padrão: auto)")
    parser.add_argument("--url", default=None, help="URL da API (padrão: .env API_URL)")
    parser.add_argument("--no-salvar", action="store_true",
                        help="Não persistir os dados extraídos em data/raw")
    args = parser.parse_args()

    configurar_logging()

    if args.fonte == "api" and args.url:
        from etl import extractors
        dados = extractors.extrair_api(args.url)
    else:
        dados = extrair(args.fonte)

    if not args.no_salvar:
        config.garantir_diretorios()
        for nome, df in dados.items():
            df.to_csv(config.DATA_RAW_DIR / f"{nome}.csv", index=False, encoding="utf-8")
            print(f"💾 Extraído salvo: data/raw/{nome}.csv ({len(df):,} registros)".replace(",", "."))

    print("\n✅ Extração concluída!\n")


if __name__ == "__main__":
    main()
