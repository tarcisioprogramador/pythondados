"""Validação e qualidade de dados.

Executa checks configuráveis (completude, unicidade, consistência, faixa e
formato) sobre os dados brutos e transformados, gerando um relatório
"antes vs depois" que demonstra o ganho de qualidade do pipeline.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from etl import config
from etl.transformers import parsear_valor_monetario, validar_cnpj

logger = logging.getLogger("datapipeline.quality")


# ---------------------------------------------------------------------------
# Checks individuais
# ---------------------------------------------------------------------------

def checar_completude(df: pd.DataFrame, colunas: list[str] | None = None, limite: float = 0.05) -> list[dict]:
    """Porcentagem de nulos por coluna (limite padrão: 5%)."""
    colunas = colunas or list(df.columns)
    resultados = []
    for col in colunas:
        if col not in df.columns:
            continue
        pct_nulos = df[col].isna().mean()
        resultados.append(
            {
                "check": "Completude (sem nulos)",
                "coluna": col,
                "status": "PASS" if pct_nulos <= limite else "FAIL",
                "valor": f"{pct_nulos:.2%}",
                "limite": f"≤ {limite:.0%}",
                "detalhe": f"{int(df[col].isna().sum())} de {len(df)} registros",
            }
        )
    return resultados


def checar_unicidade(df: pd.DataFrame, coluna: str) -> list[dict]:
    """Registros duplicados em uma coluna identificadora."""
    duplicados = int(df[coluna].duplicated().sum())
    return [
        {
            "check": "Unicidade (sem duplicados)",
            "coluna": coluna,
            "status": "PASS" if duplicados == 0 else "FAIL",
            "valor": str(duplicados),
            "limite": "0",
            "detalhe": f"coluna {coluna}",
        }
    ]


def checar_nao_negativos(df: pd.DataFrame, colunas: list[str]) -> list[dict]:
    """Valores negativos (inconsistentes) em colunas monetárias/quantitativas."""
    resultados = []
    for col in colunas:
        if col not in df.columns:
            continue
        numerica = pd.to_numeric(df[col], errors="coerce")
        negativos = int((numerica < 0).sum())
        resultados.append(
            {
                "check": "Consistência (sem negativos)",
                "coluna": col,
                "status": "PASS" if negativos == 0 else "FAIL",
                "valor": str(negativos),
                "limite": "0",
                "detalhe": f"valores negativos em {col}",
            }
        )
    return resultados


def checar_faixa(df: pd.DataFrame, coluna: str, minimo: float, maximo: float) -> list[dict]:
    """Valores dentro de uma faixa esperada."""
    numerica = pd.to_numeric(df[coluna], errors="coerce")
    fora = int((numerica.notna() & ~numerica.between(minimo, maximo)).sum())
    return [
        {
            "check": f"Faixa válida ({minimo:.0f}-{maximo:.0f})",
            "coluna": coluna,
            "status": "PASS" if fora == 0 else "FAIL",
            "valor": str(fora),
            "limite": "0",
            "detalhe": f"valores fora de [{minimo:.0f}, {maximo:.0f}]",
        }
    ]


def checar_cnpj(df: pd.DataFrame, coluna: str = "cnpj") -> list[dict]:
    """CNPJs preenchidos e com dígitos verificadores corretos."""
    if coluna not in df.columns:
        return []
    preenchido = df[coluna].fillna("").astype(str).str.strip().ne("")
    invalidos = int((preenchido & ~df[coluna].fillna("").map(validar_cnpj)).sum())
    return [
        {
            "check": "Formato (CNPJ válido)",
            "coluna": coluna,
            "status": "PASS" if invalidos == 0 else "FAIL",
            "valor": str(invalidos),
            "limite": "0",
            "detalhe": "CNPJs com dígito verificador incorreto",
        }
    ]


def checar_integridade_referencial(
    transacoes: pd.DataFrame, businesses: pd.DataFrame, coluna: str = "business_id"
) -> list[dict]:
    """Transações que referenciam negócios inexistentes (órfãs)."""
    ids_validos = set(businesses[coluna].dropna())
    orfas = int((~transacoes[coluna].isin(ids_validos)).sum())
    return [
        {
            "check": "Integridade referencial",
            "coluna": coluna,
            "status": "PASS" if orfas == 0 else "FAIL",
            "valor": str(orfas),
            "limite": "0",
            "detalhe": "transações sem negócio correspondente",
        }
    ]


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------

def executar_checks(dados: dict[str, pd.DataFrame]) -> list[dict]:
    """Roda todos os checks sobre os dados fornecidos.

    Aceita tanto as chaves do extrato bruto ('businesses'/'transactions')
    quanto as do estado transformado ('stg_businesses'/'stg_transactions').
    """
    checks: list[dict] = []

    businesses = dados.get("businesses")
    if businesses is None:
        businesses = dados.get("stg_businesses")
    transacoes = dados.get("transactions")
    if transacoes is None:
        transacoes = dados.get("stg_transactions")

    if businesses is not None:
        checks += checar_completude(
            businesses, ["business_id", "nome", "cnpj", "categoria", "cidade", "estado"]
        )
        checks += checar_unicidade(businesses, "business_id")
        checks += checar_cnpj(businesses)

    if transacoes is not None:
        # Cópia numérica para os checks de consistência (o bruto é texto)
        transacoes = transacoes.copy()
        if "valor" in transacoes.columns:
            transacoes["valor_num"] = parsear_valor_monetario(transacoes["valor"])

        checks += checar_completude(
            transacoes, ["transaction_id", "business_id", "data_venda", "valor"]
        )
        checks += checar_unicidade(transacoes, "transaction_id")
        checks += checar_nao_negativos(transacoes, ["valor_num"])
        if "avaliacao" in transacoes.columns:
            checks += checar_faixa(transacoes, "avaliacao", 1, 5)

    if businesses is not None and transacoes is not None:
        checks += checar_integridade_referencial(transacoes, businesses)

    return checks


def executar_relatorio_qualidade(
    bruto: dict[str, pd.DataFrame], transformado: dict[str, pd.DataFrame]
) -> dict:
    """Gera o relatório antes vs depois: compara checks do bruto e do transformado."""
    checks_antes = executar_checks(bruto)
    checks_depois = executar_checks(transformado)

    def _resumo(lista: list[dict]) -> dict:
        total = len(lista)
        ok = sum(1 for c in lista if c["status"] == "PASS")
        return {"total": total, "pass": ok, "fail": total - ok}

    return {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "resumo": {"antes": _resumo(checks_antes), "depois": _resumo(checks_depois)},
        "antes": checks_antes,
        "depois": checks_depois,
    }


def salvar_relatorio(relatorio: dict, pasta=None) -> Path:
    """Salva o relatório de qualidade em JSON (data/quality)."""
    pasta = Path(pasta) if pasta else config.DATA_QUALITY_DIR
    pasta.mkdir(parents=True, exist_ok=True)

    caminho = pasta / f"relatorio_qualidade_{datetime.now():%Y%m%d_%H%M%S}.json"
    caminho.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")

    # Cópia com nome fixo, para o dashboard ler a versão mais recente
    (pasta / "relatorio_qualidade_latest.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logger.info("📋 Relatório de qualidade salvo em %s", caminho)
    return caminho


def carregar_relatorio_latest(pasta=None) -> dict | None:
    """Carrega o relatório de qualidade mais recente (usado pelo dashboard)."""
    pasta = Path(pasta) if pasta else config.DATA_QUALITY_DIR
    caminho = pasta / "relatorio_qualidade_latest.json"
    if not caminho.exists():
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))
