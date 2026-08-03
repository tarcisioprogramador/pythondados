"""DataPipeline Pro — Analisador de Dados.

Envie um arquivo CSV e receba na hora: KPIs, gráficos, tabelas e insights
automáticos — funciona com qualquer dado, sem configuração.
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analisador import gerar_analise
from utils import CORES, fmt_int, layout_base

st.set_page_config(page_title="Analisador — DataPipeline Pro", page_icon="📤", layout="wide")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600;700&display=swap');
.stApp { background: radial-gradient(1200px 640px at 18% -12%, #17223f 0%, #0b1120 58%) fixed, #0b1120; }
.block-container { padding-top: 1.4rem; }
h1, h2, h3, h4 { font-family: 'Space Grotesk', sans-serif !important; color: #f1f5f9; }
p, li, label { color: #cbd5e1; }
[data-testid="stSidebar"] { background: #0c1424; border-right: 1px solid #1e293b; }
[data-testid="stSidebar"] hr { border-color: #1e293b; }

.kpi-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin: 10px 0 20px; }
.kpi-card { background: linear-gradient(180deg, #141d33 0%, #101829 100%); border: 1px solid #1e293b; border-radius: 13px; padding: 14px 16px 12px; position: relative; overflow: hidden; }
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, #22D3EE, #A78BFA 60%, transparent); opacity: .8; }
.kpi-label { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: 1.5px; text-transform: uppercase; color: #7dd3fc; margin-bottom: 5px; }
.kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 21px; font-weight: 700; color: #f1f5f9; line-height: 1.15; }
.kpi-sub { font-size: 11.5px; color: #94a3b8; margin-top: 5px; }

.secao { font-family: 'Space Grotesk', sans-serif; font-size: 18px; font-weight: 600; color: #f1f5f9; margin: 24px 0 4px; padding-left: 12px; border-left: 3px solid #22D3EE; }
.insight { background: #16233f; border: 1px solid #22D3EE33; border-left: 3px solid #22D3EE; border-radius: 10px; padding: 10px 15px; font-size: 13.5px; color: #cbd5e1; margin: 8px 0; }
.insight b { color: #7dd3fc; font-family: 'JetBrains Mono', monospace; }
.empty-box { text-align: center; padding: 40px 20px; border: 1px dashed #334155; border-radius: 14px; color: #94a3b8; }
div[data-testid="stDataFrame"] { border: 1px solid #1e293b; border-radius: 10px; }
[data-testid="stFileUploader"] section { border: 1px dashed #22D3EE66; border-radius: 12px; background: #101829; }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

st.markdown(
    "<h1 style='margin-bottom:2px'>📤 Analisador de Dados</h1>"
    "<p style='margin-top:0;color:#94a3b8'>Envie um CSV e receba KPIs, gráficos e insights automáticos</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Entrada: upload ou dados de exemplo
# ---------------------------------------------------------------------------
st.sidebar.markdown("### 🗂️ Fonte dos dados")
arquivo = st.sidebar.file_uploader(
    "Envie um arquivo CSV", type=["csv", "txt"],
    help="O analisador lê as primeiras 300 mil linhas (amostra) e detecta colunas numéricas, datas e categorias.",
)
usar_exemplo = st.sidebar.button("🧪 Usar dados de exemplo", width="stretch", key="btn_exemplo")
st.sidebar.markdown("---")
st.sidebar.caption("Funciona com qualquer CSV: vendas, cadastros, pesquisas, logs…")

df = None
nome_arquivo = ""
if usar_exemplo:
    from etl import config  # noqa: E402
    caminho_exemplo = config.PROJETO_ROOT / "data" / "exemplo.csv"
    if caminho_exemplo.exists():
        df = pd.read_csv(caminho_exemplo)
        nome_arquivo = "exemplo.csv"
    else:
        st.sidebar.warning("Arquivo de exemplo não encontrado. Rode o pipeline para gerá-lo.")
elif arquivo is not None:
    bruto = arquivo.getvalue()
    for encoding in ("utf-8", "latin-1"):
        try:
            # Limite de linhas: análise instantânea e memória controlada
            df = pd.read_csv(io.BytesIO(bruto), encoding=encoding, nrows=300_000)
            break
        except UnicodeDecodeError:
            continue
    nome_arquivo = arquivo.name

if df is None:
    st.markdown(
        "<div class='empty-box'>"
        "<div style='font-size:44px;margin-bottom:10px'>📂</div>"
        "<div style='font-family:Space Grotesk,sans-serif;font-size:18px;color:#e2e8f0'>Nenhum arquivo carregado</div>"
        "<div style='margin-top:6px'>Use o menu lateral para enviar um CSV ou carregar os dados de exemplo.</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ---------------------------------------------------------------------------
# Análise
# ---------------------------------------------------------------------------
analise = gerar_analise(df)
resumo = analise["resumo"]

pct_nulos = resumo["nulos_total"] / (resumo["linhas"] * max(resumo["colunas"], 1)) * 100
n_numericas = len(analise["numericas"])
n_categoricas = len(analise["categorias"])
n_datas = len(analise["datas"])

kpis = [
    ("Linhas", fmt_int(resumo["linhas"]), nome_arquivo),
    ("Colunas", fmt_int(resumo["colunas"]), f"{n_numericas} numéricas"),
    ("Células vazias", fmt_int(resumo["nulos_total"]), f"{pct_nulos:.1f}% da base"),
    ("Duplicadas", fmt_int(resumo["duplicados"]), "linhas repetidas"),
    ("Categóricas", fmt_int(n_categoricas), "colunas de texto"),
    ("Datas", fmt_int(n_datas), "colunas temporais"),
]
cards = "".join(
    f"<div class='kpi-card'><div class='kpi-label'>{nome}</div>"
    f"<div class='kpi-value'>{valor}</div><div class='kpi-sub'>{sub}</div></div>"
    for nome, valor, sub in kpis
)
st.markdown(f"<div class='kpi-grid'>{cards}</div>", unsafe_allow_html=True)

# --- Insights ---
st.markdown("<div class='secao'>💡 Insights automáticos</div>", unsafe_allow_html=True)
for insight in analise["insights"]:
    st.markdown(f"<div class='insight'>{insight}</div>", unsafe_allow_html=True)

# --- Pré-visualização ---
st.markdown("<div class='secao'>👁️ Pré-visualização dos dados</div>", unsafe_allow_html=True)
st.dataframe(df.head(200), width="stretch", hide_index=True)

# --- Tipos detectados ---
st.markdown("<div class='secao'>🏷️ Tipos detectados</div>", unsafe_allow_html=True)
tipos_df = pd.DataFrame(
    [{"Coluna": col, "Tipo detectado": {"numerica": "Numérica", "categorica": "Categórica",
                                        "data": "Data", "vazia": "Vazia", "constante": "Constante"}[tipo]}
     for col, tipo in analise["tipos"].items()]
)
st.dataframe(tipos_df, width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
# Colunas numéricas
# ---------------------------------------------------------------------------
if analise["numericas"]:
    st.markdown("<div class='secao'>🔢 Análise numérica</div>", unsafe_allow_html=True)

    if len(analise["numericas"]) >= 2:
        colunas_num = [n["coluna"] for n in analise["numericas"]]
        corr = df[colunas_num].apply(pd.to_numeric, errors="coerce").corr()
        fig = go.Figure(data=go.Heatmap(
            z=corr.values, x=corr.columns, y=corr.index,
            colorscale=[[0, "#134e4a"], [0.5, "#164e63"], [1, "#22D3EE"]],
            zmin=-1, zmax=1,
            text=corr.round(2).values, texttemplate="%{text}",
            hovertemplate="%{x} × %{y}: <b>%{z:.2f}</b><extra></extra>",
        ))
        layout_base(fig, "🔗 Matriz de correlação entre variáveis numéricas", altura=420)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    opcoes_num = [n["coluna"] for n in analise["numericas"]]
    sel_num = st.selectbox("Selecione a coluna numérica", opcoes_num, key="sel_num")
    stats = next(n for n in analise["numericas"] if n["coluna"] == sel_num)

    c1, c2 = st.columns([1.4, 1])
    with c1:
        serie = pd.to_numeric(df[sel_num], errors="coerce").dropna()
        fig = px.histogram(
            serie, nbins=min(40, max(10, len(serie) // 50)),
            color_discrete_sequence=["#22D3EE"], opacity=0.9,
        )
        fig.update_traces(
            hovertemplate="valor ~%{x}<br><b>%{y:,}</b> ocorrências<extra></extra>",
            marker_line_color="#0b1120", marker_line_width=0.6,
        )
        layout_base(fig, f"Histograma de {sel_num}", altura=380)
        fig.update_xaxes(title=sel_num)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with c2:
        st.markdown("##### 📐 Estatísticas")
        st.markdown(
            "<table style='width:100%;font-family:JetBrains Mono,monospace;font-size:13px'>"
            + "".join(
                f"<tr><td style='color:#64748b;padding:6px 4px'>{k}</td>"
                f"<td style='color:#e2e8f0;text-align:right;padding:6px 4px'>{v}</td></tr>"
                for k, v in [
                    ("Média", f"{stats['media']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                    ("Mediana", f"{stats['mediana']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                    ("Soma", fmt_int(stats["soma"])),
                    ("Mínimo", f"{stats['min']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                    ("Máximo", f"{stats['max']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                    ("Desvio padrão", f"{stats['desvio']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")),
                    ("Nulos", fmt_int(stats["nulos"])),
                ]
            )
            + "</table>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Colunas categóricas
# ---------------------------------------------------------------------------
if analise["categorias"]:
    st.markdown("<div class='secao'>🏷️ Análise categórica</div>", unsafe_allow_html=True)
    opcoes_cat = [c["coluna"] for c in analise["categorias"]]
    sel_cat = st.selectbox("Selecione a coluna categórica", opcoes_cat, key="sel_cat")
    cat = next(c for c in analise["categorias"] if c["coluna"] == sel_cat)
    top = cat["top"]

    c1, c2 = st.columns([1.4, 1])
    with c1:
        fig = px.bar(
            top, x="contagem", y="valor", orientation="h",
            color="contagem", color_continuous_scale=["#16233f", "#A78BFA"],
        )
        fig.update_traces(
            hovertemplate="%{y}<br><b>%{customdata}</b> registros · %{x:.1%}<extra></extra>",
            customdata=[fmt_int(v) for v in top["contagem"]],
        )
        fig.update_coloraxes(showscale=False)
        layout_base(fig, f"Top valores de {sel_cat}", altura=380)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with c2:
        fig = px.pie(
            top, names="valor", values="contagem", hole=0.58,
            color_discrete_sequence=CORES,
        )
        fig.update_traces(
            hovertemplate="%{label}<br><b>%{value:,}</b> · %{percent}<extra></extra>",
        )
        layout_base(fig, "Distribuição", altura=380)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ---------------------------------------------------------------------------
# Colunas de data
# ---------------------------------------------------------------------------
if analise["datas"]:
    st.markdown("<div class='secao'>🗓️ Análise temporal</div>", unsafe_allow_html=True)
    opcoes_data = [d["coluna"] for d in analise["datas"]]
    sel_data = st.selectbox("Selecione a coluna de data", opcoes_data, key="sel_data")
    serie_df = next(d for d in analise["datas"] if d["coluna"] == sel_data)["serie"]

    fig = px.area(
        serie_df, x=serie_df.columns[0], y="contagem",
        markers=True, line_shape="spline", color_discrete_sequence=["#34D399"],
    )
    fig.update_traces(
        hovertemplate="%{x}<br><b>%{y:,}</b> registros<extra></extra>",
    )
    layout_base(fig, f"Volume de registros ao longo do tempo ({sel_data})", altura=380)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.markdown(
    "<div class='footer-note' style='font-family:JetBrains Mono,monospace;font-size:12px;color:#475569;"
    "text-align:center;margin-top:28px;'>Análise gerada automaticamente em memória (até 300 mil linhas) — seus dados não são salvos</div>",
    unsafe_allow_html=True,
)
