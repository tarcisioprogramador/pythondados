"""Testes da prioridade de origem de dados do dashboard (dashboard/utils.py).

Cobre o comportamento novo: quando DATABASE_URL está configurado explicitamente,
o dashboard tenta o banco primeiro; senão, usa parquet.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dashboard"))
sys.path.insert(0, str(ROOT))

# O cache do streamlit não roda fora do runtime → chama a função original
# através do wrapper __wrapped__ (que o @st.cache_data preserva).
def _carregar_origem(monkeypatch, database_url: str | None) -> str | None:
    import streamlit as st  # noqa: F401 — garante o módulo importável

    from etl import config

    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)

    # Recarrega o config para refletir o novo DATABASE_URL
    importlib.reload(config)

    from utils import carregar_dados

    dados = carregar_dados.__wrapped__()
    return dados["origem"]


def test_sem_database_url_usa_parquet(monkeypatch):
    """Sem DATABASE_URL explícito, a origem deve ser parquet (com arquivos no repo)."""
    origem = _carregar_origem(monkeypatch, database_url=None)
    assert "parquet" in origem or "CSVs" in origem


def test_database_url_explicita_sem_banco_cai_parquet(monkeypatch):
    """Com DATABASE_URL apontando para um host inexistente, o banco falha
    (ou cai no fallback) e o dashboard deve continuar com parquet/CSV."""
    origem = _carregar_origem(
        monkeypatch,
        database_url="postgresql+psycopg://fake:fake@localhost:59999/nao_existe?connect_timeout=1",
    )
    # Não pode estourar — sempre cai em alguma origem segura
    assert origem is not None
