"""Configuração de logging do pipeline: console + arquivo com data/hora."""

from __future__ import annotations

import logging
import sys
from datetime import datetime

from etl import config


def configurar_logging() -> logging.Logger:
    """Configura e retorna o logger global do pipeline."""
    config.garantir_diretorios()
    logger = logging.getLogger("datapipeline")

    # Evita duplicar handlers se a função for chamada mais de uma vez
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formato = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)-24s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler de console
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formato)
    logger.addHandler(console)

    # Handler de arquivo (logs/pipeline_AAAAMMDD_HHMMSS.log)
    arquivo = config.LOG_DIR / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
    file_handler = logging.FileHandler(arquivo, encoding="utf-8")
    file_handler.setFormatter(formato)
    logger.addHandler(file_handler)

    logger.info("Log do pipeline iniciado -> %s", arquivo)
    return logger
