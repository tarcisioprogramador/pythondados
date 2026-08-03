"""Camada de extração: ingestão a partir de CSV ou da mock API local."""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd

from etl import config

logger = logging.getLogger("datapipeline.extract")

PAGINA_API = 5000  # paginação da mock API


def _timestamp_ingestao() -> str:
    """Timestamp UTC da ingestão (rastreabilidade/linhagem)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Extração via CSV
# ---------------------------------------------------------------------------
def extrair_csv(pasta: str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Lê os arquivos brutos de dados/raw. Tudo como texto para normalizar depois."""
    pasta = Path(pasta) if pasta else config.DATA_RAW_DIR
    arquivos = {
        "businesses": pasta / "businesses.csv",
        "transactions": pasta / "transactions.csv",
    }

    dados: dict[str, pd.DataFrame] = {}
    for nome, caminho in arquivos.items():
        if not caminho.exists():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {caminho}\n"
                "→ Rode antes: python scripts/generate_data.py"
            )
        df = pd.read_csv(caminho, dtype=str, encoding="utf-8")
        df["data_ingestao"] = _timestamp_ingestao()
        dados[nome] = df
        logger.info("📥 CSV lido: %s (%d registros)", caminho.name, len(df))

    return dados


# ---------------------------------------------------------------------------
# Extração via API (mock local)
# ---------------------------------------------------------------------------
def _get_json(url: str, offset: int = 0, limite: int = PAGINA_API) -> list[dict]:
    """Requisita uma página JSON da API com tratamento de erros."""
    separador = "&" if "?" in url else "?"
    url_paginada = f"{url}{separador}offset={offset}&limit={limite}"
    # Windows: 'localhost' resolve para ::1 (IPv6) e trava ~2s por requisição
    # quando o servidor escuta só em IPv4. Força o IP explícito.
    partes = urlsplit(url_paginada)
    if partes.hostname == "localhost":
        netloc = partes.netloc.replace("localhost", "127.0.0.1", 1)
        url_paginada = urlunsplit((partes.scheme, netloc, partes.path, partes.query, partes.fragment))

    try:
        with urllib.request.urlopen(url_paginada, timeout=10) as resposta:
            return json.loads(resposta.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ConnectionError(
            f"Falha ao acessar a API em {url_paginada}: {exc}\n"
            "→ A mock API está rodando? Use: python api/mock_api.py"
        ) from exc


def extrair_api(url_base: str | None = None) -> dict[str, pd.DataFrame]:
    """Consome a mock API com paginação real (demonstra ingestão via API)."""
    base = (url_base or config.API_URL).rstrip("/")
    endpoints = {
        "businesses": "/api/v1/businesses",
        "transactions": "/api/v1/transactions",
    }

    dados: dict[str, pd.DataFrame] = {}
    for nome, endpoint in endpoints.items():
        registros: list[dict] = []
        offset = 0
        while True:
            pagina = _get_json(f"{base}{endpoint}", offset=offset)
            registros.extend(pagina)
            if len(pagina) < PAGINA_API:
                break
            offset += PAGINA_API

        df = pd.DataFrame(registros)
        df["data_ingestao"] = _timestamp_ingestao()
        dados[nome] = df
        logger.info("🌐 API consumida: %s (%d registros via %d página(s))", endpoint, len(df), (len(df) // PAGINA_API) + 1)

    return dados


# ---------------------------------------------------------------------------
# Seleção automática da fonte
# ---------------------------------------------------------------------------
def extrair(fonte: str = "auto") -> dict[str, pd.DataFrame]:
    """Extrai dados da fonte escolhida.

    - 'csv'  → lê de data/raw
    - 'api'  → consome a mock API local
    - 'auto' → CSV se existir, senão API
    """
    if fonte == "csv":
        return extrair_csv()
    if fonte == "api":
        return extrair_api()

    csvs_existem = (config.DATA_RAW_DIR / "businesses.csv").exists() and (
        config.DATA_RAW_DIR / "transactions.csv"
    ).exists()
    if csvs_existem:
        return extrair_csv()
    return extrair_api()
