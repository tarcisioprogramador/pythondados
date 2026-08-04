"""DataPipeline Pro — Análises Estratégicas.

Aprofunda os insights: sazonalidade, concentração de receita, perfil dos
negócios, canais/pagamentos e tendências — com KPIs e insights calculados
a partir dos dados filtrados.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils import CORES, carregar_dados, fmt_brl, fmt_int, injetar_css_mobile, layout_base

st.set_page_config(page_title="Análises — DataPipeline Pro", page_icon="📊", layout="wide")


# ---------------------------------------------------------------------------
# Filtro + agregações cacheadas (interações instantâneas)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def _analisar_vendas(categorias: tuple, cidades: tuple, anos: tuple) -> dict | None:
    """Filtra as vendas e pré-agrega tudo que a página exibe.

    A chave do cache são os filtros — a primeira seleção calcula, as
    seguintes respondem instantaneamente.
    """
    vendas = carregar_dados()["vendas"]

    df = vendas[
        vendas["categoria"].isin(categorias)
        & vendas["cidade"].isin(cidades)
        & vendas["data"].dt.year.isin(anos)
    ].copy()

    # Base vazia: a página mostra aviso em vez de gráficos quebrados
    if df.empty:
        return None

    df["mes_ano"] = df["data"].dt.to_period("M").astype(str)
    df["tipo_dia"] = np.where(
        df["fim_semana"].astype(str).str.lower().isin(["true", "1"]),
        "Fim de semana", "Dia útil",
    )

    # KPIs
    receita_total = float(df["valor"].sum())
    vendas_qtd = len(df)
    ticket_medio = receita_total / vendas_qtd if vendas_qtd else 0.0

    mensal = df.groupby("mes_ano")["valor"].sum().sort_index()
    crescimento = ((mensal.iloc[-1] / mensal.iloc[-2]) - 1) * 100 if len(mensal) >= 2 else 0.0

    perfil = (
        df.groupby(["nome", "categoria"], as_index=False)
        .agg(receita=("valor", "sum"), vendas=("valor", "count"), avaliacao=("avaliacao", "mean"))
    )
    perfil = perfil[perfil["avaliacao"].notna()].sort_values("receita", ascending=False).copy()
    n_negocios = len(perfil)
    top20_n = max(1, int(n_negocios * 0.2))
    share_top20 = perfil["receita"].iloc[:top20_n].sum() / receita_total * 100 if receita_total else 0

    media_util = float(df[df["tipo_dia"] == "Dia útil"]["valor"].mean() or 0)
    media_fds = float(df[df["tipo_dia"] == "Fim de semana"]["valor"].mean() or 0)
    # Evita ZeroDivisionError quando não há vendas em dias úteis na seleção
    variacao_fds = ((media_fds / media_util - 1) * 100) if media_util else 0.0

    # Gráficos
    pivot = df.pivot_table(index="categoria", columns="mes_ano", values="valor", aggfunc="sum", fill_value=0)

    dias = df.groupby(["nome_dia_semana", "data"]).size().reset_index()
    contagem = dias.groupby("nome_dia_semana")["data"].nunique()
    semanal = (
        df.groupby("nome_dia_semana", as_index=False)
        .agg(receita=("valor", "sum"))
        .merge(contagem.rename("dias"), on="nome_dia_semana")
    )
    ordem = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    semanal["nome_dia_semana"] = pd.Categorical(semanal["nome_dia_semana"], categories=ordem, ordered=True)
    semanal = semanal.sort_values("nome_dia_semana")
    semanal["media_diaria"] = semanal["receita"] / semanal["dias"]

    mensal_ticket = (
        df.groupby("mes_ano", as_index=False)
        .agg(ticket=("valor", "mean"), vendas=("valor", "count"))
        .sort_values("mes_ano")
    )

    concentracao = perfil.copy()
    concentracao["acumulado"] = concentracao["receita"].cumsum()
    concentracao["share"] = concentracao["acumulado"] / receita_total * 100 if receita_total else 0

    mensal_canal = df.groupby(["mes_ano", "canal"], as_index=False)["valor"].sum()
    mensal_canal["share"] = mensal_canal.groupby("mes_ano")["valor"].transform(lambda s: s / s.sum() * 100)

    pagamentos = (
        df.groupby("forma_pagamento", as_index=False)["valor"].sum()
        .sort_values("valor", ascending=False)
    )

    tipo = (
        df.groupby("tipo_dia", as_index=False)
        .agg(receita=("valor", "sum"))
        .merge(
            df.groupby(["tipo_dia", "data"]).size().reset_index()
            .groupby("tipo_dia")["data"].nunique().rename("dias"),
            on="tipo_dia",
        )
    )
    tipo["media_diaria"] = tipo["receita"] / tipo["dias"]

    cats = (
        df.groupby("categoria", as_index=False)
        .agg(receita=("valor", "sum"), vendas=("valor", "count"))
        .sort_values("receita", ascending=False)
    )
    cats["ticket"] = cats["receita"] / cats["vendas"]

    mensal_serie = mensal.reset_index().rename(columns={"valor": "receita"})
    mensal_serie["variacao"] = mensal_serie["receita"].pct_change() * 100

    # Histograma de avaliações pré-agrupado (leve para o cache)
    avaliacoes = (
        df["avaliacao"].dropna().round(1)
        .value_counts().sort_index()
        .rename_axis("avaliacao").reset_index(name="contagem")
    )

    return {
        "n_vendas": vendas_qtd,
        "n_negocios_brutos": int(df["business_key"].nunique()),
        "receita_total": receita_total,
        "ticket_medio": ticket_medio,
        "crescimento": crescimento,
        "n_negocios": n_negocios,
        "top20_n": top20_n,
        "share_top20": share_top20,
        "media_util": media_util,
        "media_fds": media_fds,
        "variacao_fds": variacao_fds,
        "pivot": pivot,
        "semanal": semanal,
        "mensal_ticket": mensal_ticket,
        "perfil": perfil,
        "concentracao": concentracao,
        "mensal_canal": mensal_canal,
        "pagamentos": pagamentos,
        "tipo": tipo,
        "cats": cats,
        "mensal_serie": mensal_serie,
        "avaliacoes": avaliacoes,
    }


# ---------------------------------------------------------------------------
# CSS — tema "console de operações de dados"
# ---------------------------------------------------------------------------
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600;700&display=swap');

.stApp { background: radial-gradient(1200px 640px at 18% -12%, #17223f 0%, #0b1120 58%) fixed, #0b1120; }
.block-container { padding-top: 1.4rem; }
h1, h2, h3, h4 { font-family: 'Space Grotesk', sans-serif !important; color: #f1f5f9; }
p, li, label { color: #cbd5e1; }
[data-testid="stSidebar"] { background: #0c1424; border-right: 1px solid #1e293b; }
[data-testid="stSidebar"] hr { border-color: #1e293b; }

.kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin: 10px 0 20px; }
.kpi-card { background: linear-gradient(180deg, #141d33 0%, #101829 100%); border: 1px solid #1e293b; border-radius: 14px; padding: 15px 18px 13px; position: relative; overflow: hidden; }
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, #A78BFA, #22D3EE 60%, transparent); opacity: .8; }
.kpi-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 1.6px; text-transform: uppercase; color: #c4b5fd; margin-bottom: 6px; }
.kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 23px; font-weight: 700; color: #f1f5f9; line-height: 1.15; }
.kpi-sub { font-family: 'Inter', sans-serif; font-size: 12px; color: #94a3b8; margin-top: 6px; }

.secao { font-family: 'Space Grotesk', sans-serif; font-size: 19px; font-weight: 600; color: #f1f5f9; margin: 26px 0 4px; padding-left: 12px; border-left: 3px solid #22D3EE; }
.insight { background: #16233f; border: 1px solid #22D3EE33; border-left: 3px solid #22D3EE; border-radius: 10px; padding: 12px 16px; font-family: 'Inter', sans-serif; font-size: 13.5px; color: #cbd5e1; margin: 14px 0 4px; }
.insight b { color: #7dd3fc; font-family: 'JetBrains Mono', monospace; }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
injetar_css_mobile()

# ---------------------------------------------------------------------------
# Filtros (sidebar)
# ---------------------------------------------------------------------------
dados = carregar_dados()
vendas = dados["vendas"]

st.sidebar.markdown("### 🎛️ Filtros")

categorias = sorted(vendas["categoria"].dropna().unique().tolist())
cidades = sorted(vendas["cidade"].dropna().unique().tolist())
anos = sorted(int(a) for a in vendas["data"].dt.year.unique().tolist())

sel_categorias = st.sidebar.multiselect("Categorias", categorias, default=categorias)
sel_cidades = st.sidebar.multiselect("Cidades", cidades, default=cidades)
sel_anos = st.sidebar.multiselect("Anos", anos, default=anos[-2:] if len(anos) > 2 else anos)

# ---------------------------------------------------------------------------
# Cálculo (cacheado por filtros)
# ---------------------------------------------------------------------------
res = _analisar_vendas(tuple(sel_categorias), tuple(sel_cidades), tuple(sel_anos))

if res is None:
    st.warning("Nenhum dado para os filtros selecionados. Ajuste os filtros na barra lateral.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(f"Fonte de dados: **{dados['origem']}**")

st.markdown(
    "<h1 style='margin-bottom:2px'>📊 Análises Estratégicas</h1>"
    "<p style='margin-top:0;color:#94a3b8'>Sazonalidade, concentração de receita e perfil dos negócios</p>",
    unsafe_allow_html=True,
)
st.caption(
    f"Base analisada: {fmt_int(res['n_vendas'])} vendas · {fmt_int(res['n_negocios_brutos'])} "
    f"negócios · anos {', '.join(str(a) for a in sel_anos)}"
)

# ---------------------------------------------------------------------------
# KPIs + insights calculados
# ---------------------------------------------------------------------------
receita_total = res["receita_total"]

kpis = [
    ("Receita total", fmt_brl(receita_total), f"{fmt_int(res['n_vendas'])} vendas"),
    ("Ticket médio", fmt_brl(res["ticket_medio"]), "por venda"),
    ("Crescimento", f"{res['crescimento']:+.1f}%", "último mês vs anterior"),
    ("Negócios", fmt_int(res["n_negocios"]), "na base filtrada"),
    ("Concentração", f"{res['share_top20']:.0f}%", f"receita dos {res['top20_n']} maiores"),
]
cards = "".join(
    f"<div class='kpi-card'><div class='kpi-label'>{nome}</div>"
    f"<div class='kpi-value'>{valor}</div><div class='kpi-sub'>{sub}</div></div>"
    for nome, valor, sub in kpis
)
st.markdown(f"<div class='kpi-grid'>{cards}</div>", unsafe_allow_html=True)

# Insight calculado (destaque do período)
media_util = res["media_util"]
media_fds = res["media_fds"]
variacao_fds = res["variacao_fds"]
sinal_fds = "+" if variacao_fds >= 0 else ""
st.markdown(
    f"<div class='insight'>💡 <b>{res['share_top20']:.0f}%</b> da receita vem de apenas "
    f"<b>{res['top20_n']}</b> dos <b>{res['n_negocios']}</b> negócios · o fim de semana movimenta "
    f"<b>{fmt_brl(media_fds)}</b> por venda vs <b>{fmt_brl(media_util)}</b> em dias úteis "
    f"({sinal_fds}{variacao_fds:.0f}%)</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# 1) Sazonalidade: heatmap categoria × mês
# ---------------------------------------------------------------------------
st.markdown("<div class='secao'>Sazonalidade</div>", unsafe_allow_html=True)

pivot = res["pivot"]
fig = go.Figure(
    data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=pivot.index,
        colorscale=[[0, "#131c31"], [0.5, "#164e63"], [1, "#22D3EE"]],
        hoverongaps=False,
        customdata=pivot.values,
        hovertemplate="%{y} · %{x}<br><b>%{customdata:,}</b><extra></extra>",
        colorbar=dict(title="R$", tickfont=dict(color="#94a3b8")),
    )
)
layout_base(fig, "🔥 Receita por categoria × mês", altura=420)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

col1, col2 = st.columns(2)

with col1:
    semanal = res["semanal"]
    fig = px.bar(
        semanal, x="nome_dia_semana", y="media_diaria",
        color_discrete_sequence=["#34D399"],
    )
    fig.update_traces(
        hovertemplate="%{x}<br><b>%{customdata}</b> por dia<extra></extra>",
        customdata=[fmt_brl(v) for v in semanal["media_diaria"]],
    )
    layout_base(fig, "🗓️ Receita média diária por dia da semana", altura=360)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col2:
    mensal_ticket = res["mensal_ticket"]
    fig = px.line(
        mensal_ticket, x="mes_ano", y="ticket", markers=True,
        line_shape="spline", color_discrete_sequence=["#F59E0B"],
    )
    fig.update_traces(
        hovertemplate="%{x}<br><b>%{customdata}</b><extra></extra>",
        customdata=[fmt_brl(v) for v in mensal_ticket["ticket"]],
    )
    layout_base(fig, "💰 Evolução do ticket médio mensal", altura=360)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# 2) Perfil dos negócios + concentração (Pareto)
# ---------------------------------------------------------------------------
st.markdown("<div class='secao'>Perfil dos negócios</div>", unsafe_allow_html=True)

col1, col2 = st.columns([1.5, 1])

with col1:
    perfil = res["perfil"]
    fig = px.scatter(
        perfil, x="avaliacao", y="receita", size="vendas", color="categoria",
        size_max=42, opacity=0.85, color_discrete_sequence=CORES,
    )
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>avaliação %{x:.2f} ★<br>receita %{customdata[1]}"
        "<br>%{customdata[2]} vendas<extra></extra>",
        customdata=list(zip(perfil["nome"], [fmt_brl(v) for v in perfil["receita"]], perfil["vendas"])),
    )
    layout_base(fig, "🎯 Receita × avaliação por negócio (bolha = volume)", altura=410)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col2:
    concentracao = res["concentracao"]
    n = len(concentracao)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(range(1, n + 1)), y=concentracao["receita"],
        marker_color="#22D3EE", opacity=0.55, name="Receita por negócio",
        hovertemplate="Posição %{x}<br><b>%{customdata}</b><extra></extra>",
        customdata=[fmt_brl(v) for v in concentracao["receita"]],
    ))
    fig.add_trace(go.Scatter(
        x=list(range(1, n + 1)), y=concentracao["share"], mode="lines+markers",
        line=dict(color="#F59E0B", width=2.5), name="% acumulado",
        hovertemplate="Posição %{x}<br><b>%{y:.1f}%</b> acumulado<extra></extra>",
    ))
    fig.add_hline(y=80, line_dash="dot", line_color="#475569",
                  annotation_text="meta 80/20", annotation_font_color="#94a3b8")
    layout_base(fig, "📉 Concentração de receita (Pareto)", altura=410)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# 3) Canais, pagamentos e avaliações
# ---------------------------------------------------------------------------
st.markdown("<div class='secao'>Canais, pagamentos e avaliações</div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    mensal_canal = res["mensal_canal"]
    fig = px.area(
        mensal_canal, x="mes_ano", y="share", color="canal",
        line_shape="spline", color_discrete_sequence=CORES,
    )
    fig.update_traces(hovertemplate="%{x}<br>%{fullData.name}: <b>%{y:.0f}%</b><extra></extra>")
    layout_base(fig, "🧩 Evolução da participação por canal (%)", altura=360)
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col2:
    pagamentos = res["pagamentos"]
    fig = px.pie(
        pagamentos, names="forma_pagamento", values="valor", hole=0.58,
        color_discrete_sequence=CORES,
    )
    fig.update_traces(
        hovertemplate="%{label}<br><b>%{customdata}</b> · %{percent}<extra></extra>",
        customdata=[fmt_brl(v) for v in pagamentos["valor"]],
        # Sem texto sobre as fatias (nomes/percentuais) — só no hover
        textinfo="none",
    )
    layout_base(fig, "💳 Receita por forma de pagamento", altura=360)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

col1, col2 = st.columns(2)

with col1:
    avaliacoes = res["avaliacoes"]
    fig = px.bar(
        avaliacoes, x="avaliacao", y="contagem",
        color_discrete_sequence=["#A78BFA"], opacity=0.9,
    )
    fig.update_traces(
        hovertemplate="avaliação %{x}<br><b>%{y:,}</b> vendas<extra></extra>",
    )
    layout_base(fig, "⭐ Distribuição das avaliações", altura=360)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col2:
    tipo = res["tipo"]
    fig = px.bar(
        tipo, x="tipo_dia", y="media_diaria",
        color="tipo_dia", color_discrete_sequence=["#60A5FA", "#F59E0B"],
    )
    fig.update_traces(
        hovertemplate="%{x}<br><b>%{customdata}</b> por dia<extra></extra>",
        customdata=[fmt_brl(v) for v in tipo["media_diaria"]],
    )
    fig.update_layout(showlegend=False)
    layout_base(fig, "⚡ Dia útil vs fim de semana (média/dia)", altura=360)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# 4) Tendências: categorias e crescimento
# ---------------------------------------------------------------------------
st.markdown("<div class='secao'>Tendências</div>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    cats = res["cats"]
    fig = px.bar(
        cats, x="receita", y="categoria", orientation="h",
        color="ticket", color_continuous_scale=["#164e63", "#22D3EE"],
    )
    fig.update_traces(
        hovertemplate="%{y}<br><b>%{customdata}</b><extra></extra>",
        customdata=[fmt_brl(v) for v in cats["receita"]],
    )
    fig.update_coloraxes(showscale=False)
    layout_base(fig, "🏗️ Receita por categoria", altura=360)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with col2:
    mensal_serie = res["mensal_serie"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=mensal_serie["mes_ano"], y=mensal_serie["receita"],
        marker_color="#22D3EE", opacity=0.5, name="Receita",
        hovertemplate="%{x}<br><b>%{customdata}</b><extra></extra>",
        customdata=[fmt_brl(v) for v in mensal_serie["receita"]],
    ))
    fig.add_trace(go.Scatter(
        x=mensal_serie["mes_ano"], y=mensal_serie["variacao"], mode="lines+markers",
        line=dict(color="#F59E0B", width=2), yaxis="y2", name="Variação %",
        hovertemplate="%{x}<br><b>%{y:+.1f}%</b><extra></extra>",
    ))
    fig.update_layout(
        yaxis2=dict(overlaying="y", side="right", showgrid=False, ticksuffix="%"),
    )
    layout_base(fig, "📈 Receita mensal + variação % (MoM)", altura=360)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

st.markdown(
    "<div class='footer-note' style='font-family:JetBrains Mono,monospace;font-size:12px;color:#475569;"
    "text-align:center;margin-top:28px;'>Análises geradas a partir da camada gold "
    "(fact_sales × dim_business × dim_time) · " + dados["origem"] + "</div>",
    unsafe_allow_html=True,
)
