"""DataPipeline Pro — Visão Geral.

Painel principal do site: KPIs estratégicos, evolução da receita,
ranking de negócios e distribuições.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import CORES, carregar_dados, chip, fmt_brl, fmt_int, injetar_css_mobile, layout_base

st.set_page_config(page_title="Visão Geral — DataPipeline Pro", page_icon="📈", layout="wide")

# ---------------------------------------------------------------------------
# CSS — tema "console de operações de dados"
# ---------------------------------------------------------------------------
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600;700&display=swap');

.stApp { background: radial-gradient(1200px 640px at 18% -12%, #17223f 0%, #0b1120 58%) fixed, #0b1120; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; }

h1, h2, h3, h4 { font-family: 'Space Grotesk', sans-serif !important; color: #f1f5f9; }
p, li, label { color: #cbd5e1; }

[data-testid="stSidebar"] {
    background: #0c1424;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] { background: #16233f; }
[data-testid="stSidebar"] hr { border-color: #1e293b; }

.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin: 6px 0 18px; }
.kpi-card {
    background: linear-gradient(180deg, #141d33 0%, #101829 100%);
    border: 1px solid #1e293b;
    border-radius: 14px;
    padding: 16px 18px 14px;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #22D3EE, #A78BFA 60%, transparent);
    opacity: .8;
}
.kpi-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 1.6px; text-transform: uppercase; color: #7dd3fc; margin-bottom: 6px; }
.kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 25px; font-weight: 700; color: #f1f5f9; line-height: 1.15; }
.kpi-delta { font-family: 'Inter', sans-serif; font-size: 12px; margin-top: 7px; color: #94a3b8; }
.kpi-delta.up { color: #34d399; }
.kpi-delta.down { color: #f87171; }

.chip-row { margin-bottom: 14px; }
.footer-note { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #475569; text-align: center; margin-top: 26px; }
div[data-testid="stDataFrame"] { border: 1px solid #1e293b; border-radius: 10px; }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
injetar_css_mobile()

# ---------------------------------------------------------------------------
# Carregamento e filtros
# ---------------------------------------------------------------------------
dados = carregar_dados()
vendas: pd.DataFrame = dados["vendas"]

st.sidebar.markdown("### 🎛️ Filtros")

categorias = sorted(vendas["categoria"].dropna().unique().tolist())
cidades = sorted(vendas["cidade"].dropna().unique().tolist())

sel_categorias = st.sidebar.multiselect("Categorias", categorias, default=categorias)
sel_cidades = st.sidebar.multiselect("Cidades", cidades, default=cidades)

min_data = vendas["data"].min().date()
max_data = vendas["data"].max().date()
sel_periodo = st.sidebar.date_input(
    "Período", value=(min_data, max_data), min_value=min_data, max_value=max_data
)

if isinstance(sel_periodo, tuple) and len(sel_periodo) == 2:
    inicio, fim = sel_periodo
else:
    inicio, fim = min_data, max_data

df = vendas[
    vendas["categoria"].isin(sel_categorias)
    & vendas["cidade"].isin(sel_cidades)
    & (vendas["data"].dt.date >= inicio)
    & (vendas["data"].dt.date <= fim)
].copy()

st.sidebar.markdown("---")
st.sidebar.caption(f"Fonte de dados: **{dados['origem']}**")

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
st.markdown(
    "<h1 style='margin-bottom:0'>📈 Visão Geral</h1>"
    "<p style='margin-top:0;color:#94a3b8'>KPIs estratégicos e distribuições do negócio</p>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='chip-row'>"
    + chip(f"FONTE: {dados['origem'].upper()}")
    + chip(f"PERÍODO: {df['data'].dt.date.min()} → {df['data'].dt.date.max()}")
    + chip(f"{fmt_int(len(df))} VENDAS")
    + chip(f"{fmt_int(df['business_key'].nunique())} NEGÓCIOS", "#A78BFA")
    + "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
receita = float(df["valor"].sum())
vendas_qtd = int(len(df))
ticket = receita / vendas_qtd if vendas_qtd else 0
avaliacao = df["avaliacao"].mean()
avaliacao = 0 if pd.isna(avaliacao) else float(avaliacao)

# Delta do último mês completo vs o anterior
df["mes_ano"] = df["data"].dt.to_period("M")
mensal = df.groupby("mes_ano")["valor"].sum()
if len(mensal) >= 2:
    delta = (mensal.iloc[-1] - mensal.iloc[-2]) / mensal.iloc[-2] * 100
else:
    delta = 0.0
seta = "▲" if delta >= 0 else "▼"
classe = "up" if delta >= 0 else "down"
delta_html = (
    f"<div class='kpi-delta {classe}'>{seta} {abs(delta):.1f}% no último mês "
    f"vs anterior</div>"
)

kpis = [
    ("Receita total", fmt_brl(receita), delta_html),
    ("Vendas realizadas", fmt_int(vendas_qtd), ""),
    ("Ticket médio", fmt_brl(ticket), ""),
    ("Negócios ativos", fmt_int(df["business_key"].nunique()), ""),
    ("Avaliação média", f"{avaliacao:.2f} ★", ""),
]

cards = "".join(
    f"<div class='kpi-card'><div class='kpi-label'>{nome}</div>"
    f"<div class='kpi-value'>{valor}</div>{extra}</div>"
    for nome, valor, extra in kpis
)
st.markdown(f"<div class='kpi-grid'>{cards}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Gráficos — linha 1: receita mensal + categorias
# ---------------------------------------------------------------------------
col1, col2 = st.columns([1.6, 1])

with col1:
    mensal_df = (
        df.groupby("mes_ano", as_index=False)
        .agg(receita=("valor", "sum"), vendas=("valor", "count"))
        .sort_values("mes_ano")
    )
    mensal_df["rotulo"] = mensal_df["mes_ano"].astype(str)
    fig = px.area(
        mensal_df, x="rotulo", y="receita",
        markers=True, line_shape="spline",
        color_discrete_sequence=["#22D3EE"],
    )
    fig.update_traces(
        hovertemplate="%{x}<br><b>%{customdata}</b><extra></extra>",
        customdata=[fmt_brl(v) for v in mensal_df["receita"]],
    )
    layout_base(fig, "📈 Receita mensal", altura=360)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

with col2:
    cat_df = (
        df.groupby("categoria", as_index=False)
        .agg(receita=("valor", "sum"))
        .sort_values("receita", ascending=False)
    )
    fig = px.pie(
        cat_df, names="categoria", values="receita", hole=0.58,
        color_discrete_sequence=CORES,
    )
    fig.update_traces(
        hovertemplate="%{label}<br><b>%{customdata}</b> · %{percent}<extra></extra>",
        customdata=[fmt_brl(v) for v in cat_df["receita"]],
    )
    layout_base(fig, "🥧 Receita por categoria", altura=360)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# Gráficos — linha 2: ranking + cidades
# ---------------------------------------------------------------------------
col1, col2 = st.columns([1.6, 1])

with col1:
    top = (
        df.groupby("nome", as_index=False)
        .agg(receita=("valor", "sum"), vendas=("valor", "count"))
        .sort_values("receita", ascending=False)
        .head(10)
        .iloc[::-1]
    )
    fig = px.bar(
        top, x="receita", y="nome", orientation="h",
        color="receita", color_continuous_scale=["#16233f", "#22D3EE"],
    )
    fig.update_traces(
        hovertemplate="%{y}<br><b>%{customdata}</b><extra></extra>",
        customdata=[fmt_brl(v) for v in top["receita"]],
    )
    fig.update_coloraxes(showscale=False)
    layout_base(fig, "🏆 Top 10 negócios por receita", altura=390)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

with col2:
    cidades_df = (
        df.groupby(["cidade", "estado"], as_index=False)
        .agg(receita=("valor", "sum"))
        .sort_values("receita", ascending=False)
        .head(8)
        .iloc[::-1]
    )
    cidades_df["rotulo"] = cidades_df["cidade"] + "/" + cidades_df["estado"]
    fig = px.bar(
        cidades_df, x="receita", y="rotulo", orientation="h",
        color_discrete_sequence=["#A78BFA"],
    )
    fig.update_traces(
        hovertemplate="%{y}<br><b>%{customdata}</b><extra></extra>",
        customdata=[fmt_brl(v) for v in cidades_df["receita"]],
    )
    layout_base(fig, "📍 Receita por cidade (top 8)", altura=390)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# Gráficos — linha 3: sazonalidade + canais
# ---------------------------------------------------------------------------
col1, col2 = st.columns([1.3, 1])

with col1:
    # Receita média diária por dia da semana (normaliza pela quantidade de dias)
    dias = df.groupby(["nome_dia_semana", "data"]).size().reset_index()
    contagem_dias = dias.groupby("nome_dia_semana")["data"].nunique()
    semanal = (
        df.groupby("nome_dia_semana", as_index=False)
        .agg(receita=("valor", "sum"))
        .merge(contagem_dias.rename("dias"), on="nome_dia_semana")
    )
    ordem = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    semanal["nome_dia_semana"] = pd.Categorical(semanal["nome_dia_semana"], categories=ordem, ordered=True)
    semanal = semanal.sort_values("nome_dia_semana")
    semanal["media_diaria"] = semanal["receita"] / semanal["dias"]

    fig = px.bar(
        semanal, x="nome_dia_semana", y="media_diaria",
        color_discrete_sequence=["#34D399"],
    )
    fig.update_traces(
        hovertemplate="%{x}<br><b>%{customdata}</b><extra></extra>",
        customdata=[fmt_brl(v) for v in semanal["media_diaria"]],
    )
    layout_base(fig, "🗓️ Sazonalidade: receita média diária por dia da semana", altura=360)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

with col2:
    canais = (
        df.groupby("canal", as_index=False)
        .agg(receita=("valor", "sum"))
        .sort_values("receita", ascending=False)
    )
    fig = px.bar(
        canais, x="canal", y="receita",
        color="canal", color_discrete_sequence=CORES,
    )
    fig.update_traces(
        hovertemplate="%{x}<br><b>%{customdata}</b> · %{y:.0%}<extra></extra>",
        customdata=[f"{v / receita:.1%}" for v in canais["receita"]],
    )
    fig.update_layout(showlegend=False)
    layout_base(fig, "🛒 Receita por canal de venda", altura=360)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.markdown(
    "<div class='footer-note'>DataPipeline Pro · Python + SQL + PostgreSQL + Streamlit · "
    "modelo star schema · dados sintéticos gerados localmente</div>",
    unsafe_allow_html=True,
)
