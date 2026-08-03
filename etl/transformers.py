"""Camada de transformação: limpeza, padronização e modelagem dimensional.

Converte dados brutos (bronze) em dimensões e fatos (silver) prontos para
análise, seguindo o modelo star schema:

    dim_category <-- dim_business --> fact_sales --> dim_time
"""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
import pandas as pd

from etl import config

logger = logging.getLogger("datapipeline.transform")

# Identificador único do batch de processamento (rastreabilidade)
BATCH_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

# ---------------------------------------------------------------------------
# Utilitários de padronização
# ---------------------------------------------------------------------------

FORMATOS_DATA = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%Y-%m-%d %H:%M:%S",
]


def normalizar_texto(serie: pd.Series) -> pd.Series:
    """Remove espaços extras das bordas e colapsa espaços repetidos."""
    return serie.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)


def normalizar_cnpj(valor) -> str:
    """Mantém apenas os dígitos do CNPJ (remove pontos, barra e traço)."""
    if valor is None or pd.isna(valor):
        return ""
    return re_sub_digitos(str(valor))


def re_sub_digitos(texto: str) -> str:
    return "".join(c for c in texto if c.isdigit())[:14]


def validar_cnpj(cnpj: str) -> bool:
    """Valida um CNPJ usando o algoritmo real dos dígitos verificadores (mod 11)."""
    cnpj = normalizar_cnpj(cnpj)
    if len(cnpj) != 14 or cnpj in {c * 14 for c in "0123456789"}:
        return False

    def _digito(base: str, pesos: list[int]) -> int:
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    base12 = cnpj[:12]
    d1 = _digito(base12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = _digito(base12 + str(d1), [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])

    return cnpj == base12 + str(d1) + str(d2)


def parsear_data(serie: pd.Series) -> pd.Series:
    """Converte datas em formatos mistos (ISO, dd/mm/aaaa etc.) para datetime."""
    valores = []

    def _converter(valor):
        if valor is None or pd.isna(valor):
            return np.nan
        texto = str(valor).strip()
        if texto.lower() in {"nan", "none", "null", "na", ""}:
            return np.nan
        for fmt in FORMATOS_DATA:
            try:
                return datetime.strptime(texto, fmt)
            except ValueError:
                continue
        return np.nan

    for v in serie:
        valores.append(_converter(v))
    return pd.Series(valores, index=serie.index, dtype="datetime64[ns]")


def parsear_valor_monetario(serie: pd.Series) -> pd.Series:
    """Converte valores monetários em texto (ex.: 'R$ 1.234,56') para float."""
    limpos = serie.astype(str).str.replace(r"[R$\s]", "", regex=True)

    def _converter(valor):
        if pd.isna(valor):                     # NaN/None/NA vêm como float
            return np.nan
        valor = str(valor).strip()
        if not valor or valor.lower() in {"nan", "none", "null", "na"}:
            return np.nan
        if "," in valor and "." in valor:      # 1.234,56 -> 1234.56
            valor = valor.replace(".", "").replace(",", ".")
        elif "," in valor:                     # 12,5 -> 12.5
            valor = valor.replace(",", ".")
        try:
            return float(valor)
        except ValueError:
            return np.nan

    return limpos.map(_converter)


def regiao_do_estado(uf: str) -> str:
    """Mapeia a UF para a região geográfica do Brasil."""
    regioes = {
        "N": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
        "NE": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
        "CO": ["DF", "GO", "MT", "MS"],
        "SE": ["ES", "MG", "RJ", "SP"],
        "S": ["PR", "RS", "SC"],
    }
    uf = str(uf).strip().upper()
    for regiao, estados in regioes.items():
        if uf in estados:
            return regiao
    return "OUTROS"


# ---------------------------------------------------------------------------
# Limpeza dos dados brutos
# ---------------------------------------------------------------------------

def limpar_businesses(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e padroniza a tabela de negócios (bronze -> silver)."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Remoção de duplicados e registros sem identificador
    total_inicial = len(df)
    df = df.dropna(subset=["business_id"])
    df = df.drop_duplicates(subset=["business_id"], keep="first")

    for col in ["nome", "categoria", "setor", "cidade", "estado", "endereco"]:
        if col in df.columns:
            df[col] = normalizar_texto(df[col].fillna(""))

    if "nome" in df.columns:
        df["nome"] = df["nome"].str.title()
    if "estado" in df.columns:
        df["estado"] = df["estado"].str.upper()

    # CNPJ: normaliza e valida (dígitos verificadores)
    if "cnpj" in df.columns:
        df["cnpj"] = df["cnpj"].map(normalizar_cnpj)
        cnpj_valido = df["cnpj"].map(validar_cnpj)
        df.loc[~cnpj_valido, "cnpj"] = None

    # Datas: formatos mistos -> datetime
    if "data_abertura" in df.columns:
        df["data_abertura"] = parsear_data(df["data_abertura"])
        df.loc[df["data_abertura"].isna(), "data_abertura"] = None

    # Números
    if "num_funcionarios" in df.columns:
        df["num_funcionarios"] = pd.to_numeric(df["num_funcionarios"], errors="coerce")

    removidos = total_inicial - len(df)
    if removidos:
        logger.info("🧹 businesses: %d duplicado(s)/inválido(s) removido(s)", removidos)
    return df.reset_index(drop=True)


def limpar_transacoes(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa e padroniza a tabela de transações (bronze -> silver)."""
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    total_inicial = len(df)

    # Duplicados
    df = df.dropna(subset=["transaction_id"])
    df = df.drop_duplicates(subset=["transaction_id"], keep="first")

    # Datas em formatos mistos
    df["data_venda"] = parsear_data(df["data_venda"])
    df = df[df["data_venda"].notna()]

    # Valores monetários e quantidades
    df["valor"] = parsear_valor_monetario(df["valor"])
    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce")

    # Consistência: remove valores negativos ou zero (erro de lançamento)
    invalidos_valor = df["valor"].isna() | (df["valor"] <= 0)
    if invalidos_valor.any():
        logger.warning("🚫 transactions: %d registro(s) com valor inválido removido(s)", invalidos_valor.sum())
    df = df[~invalidos_valor]

    # Avaliação entre 1 e 5
    df["avaliacao"] = pd.to_numeric(df["avaliacao"], errors="coerce")
    fora_faixa = df["avaliacao"].notna() & ~df["avaliacao"].between(1, 5)
    df.loc[fora_faixa, "avaliacao"] = np.nan

    for col in ["forma_pagamento", "canal"]:
        if col in df.columns:
            df[col] = normalizar_texto(df[col].fillna("")).str.upper()

    removidos = total_inicial - len(df)
    if removidos:
        logger.info("🧹 transactions: %d registro(s) inválido(s) removido(s)", removidos)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Modelagem dimensional (star schema)
# ---------------------------------------------------------------------------

def construir_dimensoes(
    businesses: pd.DataFrame,
    transacoes: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Gera as dimensões dim_category, dim_time e dim_business com chaves substitutas."""
    # ---- dim_category ----
    categorias = (
        businesses[["categoria", "setor"]]
        .drop_duplicates()
        .sort_values("categoria")
        .reset_index(drop=True)
    )
    categorias.insert(0, "category_key", range(1, len(categorias) + 1))
    mapa_categoria = dict(zip(categorias["categoria"], categorias["category_key"]))

    # ---- dim_time ----
    datas = pd.to_datetime(pd.concat([transacoes["data_venda"]])).dt.date
    unicas = pd.Series(sorted(set(datas)))
    dim_time = pd.DataFrame(
        {
            "date_key": unicas.map(lambda d: int(d.strftime("%Y%m%d"))),
            "data": unicas.map(lambda d: d.isoformat()),
            "ano": unicas.map(lambda d: d.year),
            "mes": unicas.map(lambda d: d.month),
            "dia": unicas.map(lambda d: d.day),
            "trimestre": unicas.map(lambda d: (d.month - 1) // 3 + 1),
            "dia_semana": unicas.map(lambda d: d.weekday()),  # 0=segunda
        }
    )
    nomes_mes = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
        7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
    }
    nomes_dia = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    dim_time["nome_mes"] = dim_time["mes"].map(nomes_mes)
    dim_time["nome_dia_semana"] = dim_time["dia_semana"].map(lambda d: nomes_dia[d])
    dim_time["fim_semana"] = dim_time["dia_semana"].isin([5, 6])

    # ---- dim_business ----
    dim_business = businesses.copy()
    dim_business["categoria_key"] = dim_business["categoria"].map(mapa_categoria)
    dim_business["regiao"] = dim_business["estado"].map(regiao_do_estado)
    dim_business.insert(0, "business_key", range(1, len(dim_business) + 1))

    colunas_business = [
        "business_key", "business_id", "nome", "cnpj", "categoria", "categoria_key",
        "cidade", "estado", "regiao", "endereco", "data_abertura",
        "num_funcionarios", "email", "telefone",
    ]
    dim_business = dim_business[[c for c in colunas_business if c in dim_business.columns]]

    logger.info(
        "🏗️  Dimensões criadas: %d categorias | %d datas | %d negócios",
        len(categorias), len(dim_time), len(dim_business),
    )
    return {
        "dim_category": categorias,
        "dim_time": dim_time,
        "dim_business": dim_business,
    }


def construir_fato(
    transacoes: pd.DataFrame,
    dim_business: pd.DataFrame,
    dim_time: pd.DataFrame,
) -> pd.DataFrame:
    """Gera a tabela fato fact_sales com chaves estrangeiras e métricas derivadas."""
    fato = transacoes.copy()

    mapa_business = dict(zip(dim_business["business_id"], dim_business["business_key"]))

    fato["business_key"] = fato["business_id"].map(mapa_business)
    fato["date_key"] = pd.to_datetime(fato["data_venda"]).dt.strftime("%Y%m%d").astype(int)

    # Ticket médio por linha de venda
    fato["ticket_medio"] = np.where(
        fato["quantidade"].fillna(0) > 0,
        fato["valor"] / fato["quantidade"],
        fato["valor"],
    )

    # Chave substituta sequencial + chave natural única (idempotência)
    fato["sale_key"] = range(1, len(fato) + 1)
    fato["batch_id"] = BATCH_ID

    colunas_fato = [
        "sale_key", "transaction_id", "business_key", "date_key", "valor",
        "quantidade", "ticket_medio", "forma_pagamento", "canal", "avaliacao", "batch_id",
    ]
    fato = fato[[c for c in colunas_fato if c in fato.columns]]

    logger.info("📊 Fato criado: %d linhas de venda", len(fato))
    return fato


def criar_metricas_negocios(fato: pd.DataFrame, dim_business: pd.DataFrame) -> pd.DataFrame:
    """Agrega métricas por negócio (camada gold pré-calculada para o dashboard)."""
    metricas = (
        fato.groupby("business_key", as_index=False)
        .agg(
            receita_total=("valor", "sum"),
            qtd_vendas=("valor", "count"),
            ticket_medio=("valor", "mean"),
            avaliacao_media=("avaliacao", "mean"),
            ultima_venda=("date_key", "max"),
        )
        .sort_values("receita_total", ascending=False)
    )
    metricas = metricas.merge(
        dim_business[["business_key", "nome", "categoria", "cidade", "estado", "regiao"]],
        on="business_key",
        how="left",
    )
    return metricas


# ---------------------------------------------------------------------------
# Orquestração da transformação
# ---------------------------------------------------------------------------

def transformar(extrato: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Executa todo o fluxo de transformação e retorna os DataFrames prontos."""
    logger.info("🔄 Iniciando transformação (batch=%s)...", BATCH_ID)

    businesses_limpos = limpar_businesses(extrato["businesses"])
    transacoes_limpas = limpar_transacoes(extrato["transactions"])

    # Integridade referencial: mantém apenas transações de negócios conhecidos
    ids_validos = set(businesses_limpos["business_id"])
    transacoes_limpas = transacoes_limpas[transacoes_limpas["business_id"].isin(ids_validos)]

    dimensoes = construir_dimensoes(businesses_limpos, transacoes_limpas)
    fato = construir_fato(transacoes_limpas, dimensoes["dim_business"], dimensoes["dim_time"])
    metricas = criar_metricas_negocios(fato, dimensoes["dim_business"])

    logger.info("✅ Transformação concluída: %d vendas | %d negócios", len(fato), len(dimensoes["dim_business"]))
    return {
        "stg_businesses": businesses_limpos,
        "stg_transactions": transacoes_limpas,
        "dim_category": dimensoes["dim_category"],
        "dim_time": dimensoes["dim_time"],
        "dim_business": dimensoes["dim_business"],
        "fact_sales": fato,
        "metricas_negocios": metricas,
    }


def salvar_transformados(dados: dict[str, pd.DataFrame], pasta=None) -> None:
    """Persiste os DataFrames transformados em data/processed como CSV."""
    pasta = pasta or config.DATA_PROCESSED_DIR
    pasta.mkdir(parents=True, exist_ok=True)

    for nome, df in dados.items():
        if df is None or df.empty:
            continue
        df.to_csv(pasta / f"{nome}.csv", index=False, encoding="utf-8")
        logger.info("💾 Transformado salvo: %s/%s.csv (%d linhas)", pasta.name, nome, len(df))
