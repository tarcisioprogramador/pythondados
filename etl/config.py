"""Configuração central do projeto: caminhos, ambiente e banco de dados."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Windows: garante que o console aceite UTF-8 (emoji e acentos nos logs)
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

# Carrega as variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

# ---------------------------------------------------------------------------
# Caminhos do projeto
# ---------------------------------------------------------------------------
PROJETO_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW_DIR = Path(os.getenv("DATA_RAW_DIR", PROJETO_ROOT / "data" / "raw"))
DATA_PROCESSED_DIR = Path(os.getenv("DATA_PROCESSED_DIR", PROJETO_ROOT / "data" / "processed"))
DATA_QUALITY_DIR = Path(os.getenv("DATA_QUALITY_DIR", PROJETO_ROOT / "data" / "quality"))
LOG_DIR = Path(os.getenv("LOG_DIR", PROJETO_ROOT / "logs"))
SQL_DIR = PROJETO_ROOT / "sql"

# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------
POSTGRES_PADRAO = "postgresql+psycopg://datapipeline:datapipeline@localhost:5432/datapipeline"
SQLITE_PADRAO = f"sqlite:///{(PROJETO_ROOT / 'data' / 'datapipeline.db').as_posix()}"

# DATABASE_URL vindo do ambiente (.env). Se vazio, usa o padrão (PostgreSQL).
DATABASE_URL = os.getenv("DATABASE_URL", POSTGRES_PADRAO) or POSTGRES_PADRAO

# Se "PIPELINE_DB_ONLY=1", desativa o fallback automático para SQLite.
DB_SOMENTE_POSTGRES = os.getenv("PIPELINE_DB_ONLY", "").lower() in {"1", "true", "postgres", "postgresql"}

# ---------------------------------------------------------------------------
# Fonte de dados (API mock local)
# ---------------------------------------------------------------------------
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")


def garantir_diretorios() -> None:
    """Cria as pastas de dados/log caso não existam."""
    for pasta in (DATA_RAW_DIR, DATA_PROCESSED_DIR, DATA_QUALITY_DIR, LOG_DIR):
        pasta.mkdir(parents=True, exist_ok=True)
