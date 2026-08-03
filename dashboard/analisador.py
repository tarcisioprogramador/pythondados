"""Analisador automático de arquivos de dados (CSV).

Detecta os tipos das colunas (numérica, data, categórica), calcula KPIs,
agregações e insights — funciona com qualquer CSV, sem configuração.
"""

from __future__ import annotations

import pandas as pd

LIMITE_TOP = 8          # top N valores por coluna categórica
LIMITE_DETECCAO = 200   # amostra usada na detecção de tipos


def detectar_tipo(coluna: pd.Series) -> str:
    """Classifica a coluna em 'numerica', 'data' ou 'categorica'."""
    nao_nulos = coluna.dropna()
    if nao_nulos.empty:
        return "vazia"
    if nao_nulos.nunique() == 1:
        return "constante"

    amostra = nao_nulos.head(LIMITE_DETECCAO)

    # 1) Já é datetime
    if pd.api.types.is_datetime64_any_dtype(coluna):
        return "data"

    # 2) String que parece data (ISO ou dd/mm/aaaa)
    eh_texto = pd.api.types.is_object_dtype(amostra) or pd.api.types.is_string_dtype(amostra)
    if eh_texto:
        parseado = pd.to_datetime(amostra.astype(str), errors="coerce")
        if parseado.notna().mean() > 0.8 and len(parseado) >= 3:
            return "data"

    # 3) Numérica (nativa ou convertível)
    if pd.api.types.is_numeric_dtype(coluna):
        return "numerica"
    numerica = pd.to_numeric(amostra, errors="coerce")
    if numerica.notna().mean() > 0.8:
        return "numerica"
    # Decimal brasileiro ("2,5") ou separador de milhar ("1.234,56")
    numerica2 = pd.to_numeric(amostra.astype(str).str.replace(",", ".", regex=False), errors="coerce")
    if numerica2.notna().mean() > 0.8:
        return "numerica"

    return "categorica"


def _estatisticas_numericas(df: pd.DataFrame, coluna: str) -> dict:
    s = pd.to_numeric(df[coluna], errors="coerce")
    return {
        "coluna": coluna,
        "media": float(s.mean()) if s.notna().any() else 0.0,
        "mediana": float(s.median()) if s.notna().any() else 0.0,
        "soma": float(s.sum()) if s.notna().any() else 0.0,
        "min": float(s.min()) if s.notna().any() else 0.0,
        "max": float(s.max()) if s.notna().any() else 0.0,
        "desvio": float(s.std()) if s.notna().sum() > 1 else 0.0,
        "nulos": int(s.isna().sum()),
    }


def _top_categorias(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    top = (
        df[coluna].fillna("(vazio)")
        .value_counts()
        .head(LIMITE_TOP)
        .rename_axis("valor")
        .reset_index(name="contagem")
    )
    top["pct"] = top["contagem"] / len(df) * 100
    return top


def _serie_temporal(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Agrupa a coluna de data por dia; se longa demais, reduz para mensal."""
    datas = pd.to_datetime(df[coluna], errors="coerce").dropna()
    serie = datas.value_counts().sort_index().rename_axis("data").reset_index(name="contagem")
    if len(serie) > 90:
        serie["mes"] = pd.to_datetime(serie["data"]).dt.to_period("M").astype(str)
        serie = serie.groupby("mes", as_index=False)["contagem"].sum()
    return serie


def gerar_analise(df: pd.DataFrame) -> dict:
    """Gera a análise completa de um DataFrame."""
    df = df.copy()
    tipos = {col: detectar_tipo(df[col]) for col in df.columns}

    resumo = {
        "linhas": len(df),
        "colunas": len(df.columns),
        "nulos_total": int(df.isna().sum().sum()),
        "duplicados": int(df.duplicated().sum()),
    }

    numericas = [
        _estatisticas_numericas(df, col)
        for col, tipo in tipos.items() if tipo == "numerica"
    ]
    categorias = [
        {"coluna": col, "top": _top_categorias(df, col)}
        for col, tipo in tipos.items() if tipo == "categorica"
    ]
    datas = [
        {"coluna": col, "serie": _serie_temporal(df, col)}
        for col, tipo in tipos.items() if tipo == "data"
    ]

    insights = _gerar_insights(df, resumo, numericas, categorias)
    return {
        "resumo": resumo,
        "tipos": tipos,
        "numericas": numericas,
        "categorias": categorias,
        "datas": datas,
        "insights": insights,
    }


def _gerar_insights(
    df: pd.DataFrame,
    resumo: dict,
    numericas: list[dict],
    categorias: list[dict],
) -> list[str]:
    """Insights automáticos: qualidade, concentração e correlações."""
    insights: list[str] = []

    if resumo["duplicados"]:
        insights.append(
            f"⚠️ Foram encontradas <b>{resumo['duplicados']:,}</b> linhas duplicadas "
            f"({resumo['duplicados'] / max(resumo['linhas'], 1):.1%} da base).".replace(",", ".")
        )
    if resumo["nulos_total"]:
        pct = resumo["nulos_total"] / (resumo["linhas"] * max(resumo["colunas"], 1)) * 100
        insights.append(f"🕳️ {resumo['nulos_total']:,} células vazias ({pct:.1f}% do total).".replace(",", "."))

    for cat in categorias:
        top = cat["top"]
        if not top.empty:
            maior = top.iloc[0]
            insights.append(
                f"🏆 Em <b>{cat['coluna']}</b>, o valor mais comum é "
                f"<b>{maior['valor']}</b> ({maior['pct']:.1f}% dos registros)."
            )

    if len(numericas) >= 2:
        colunas = [n["coluna"] for n in numericas]
        corr = df[colunas].apply(pd.to_numeric, errors="coerce").corr()
        for i in range(len(colunas)):
            for j in range(i + 1, len(colunas)):
                r = corr.iloc[i, j]
                if abs(r) >= 0.7 and not pd.isna(r):
                    sentido = "positiva" if r > 0 else "negativa"
                    insights.append(
                        f"🔗 Correlação {sentido} <b>forte ({r:.2f})</b> entre "
                        f"<b>{colunas[i]}</b> e <b>{colunas[j]}</b>."
                    )

    if not insights:
        insights.append("✨ Nenhum problema evidente — a base está limpa e pronta para análise.")
    return insights
