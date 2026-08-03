"""DataPipeline Pro — Qualidade de Dados.

Transparência do pipeline: checks de qualidade antes vs depois, linhagem
das camadas (bronze/silver/gold) e log das execuções.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import carregar_dados, chip, fmt_int, layout_base

st.set_page_config(page_title="Qualidade — DataPipeline Pro", page_icon="✅", layout="wide")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');
.stApp { background: radial-gradient(1200px 640px at 18% -12%, #17223f 0%, #0b1120 58%) fixed, #0b1120; }
.block-container { padding-top: 1.4rem; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: #f1f5f9; }
p, li, label { color: #cbd5e1; }
[data-testid="stSidebar"] { background: #0c1424; border-right: 1px solid #1e293b; }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 6px 0 18px; }
.kpi-card { background: linear-gradient(180deg, #141d33 0%, #101829 100%); border: 1px solid #1e293b; border-radius: 14px; padding: 16px 18px 14px; position: relative; overflow: hidden; }
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, #34D399, #22D3EE 60%, transparent); opacity: .8; }
.kpi-label { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 1.6px; text-transform: uppercase; color: #6ee7b7; margin-bottom: 6px; }
.kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 24px; font-weight: 700; color: #f1f5f9; line-height: 1.15; }
.kpi-sub { font-size: 12px; color: #94a3b8; margin-top: 6px; }
.check-row { font-family: 'JetBrains Mono', monospace; font-size: 13px; padding: 7px 4px; border-bottom: 1px solid #1e293b; color: #cbd5e1; }
.badge-pass { color: #34d399; background: #34d3991a; border: 1px solid #34d39955; border-radius: 999px; padding: 1px 10px; font-size: 11px; margin-right: 8px; }
.badge-fail { color: #f87171; background: #f871711a; border: 1px solid #f8717155; border-radius: 999px; padding: 1px 10px; font-size: 11px; margin-right: 8px; }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

dados = carregar_dados()
vendas = dados["vendas"]
qualidade = dados["qualidade"]
linhagem = dados["linhagem"]
execucoes = dados["execucoes"]

st.markdown(
    "<h1 style='margin-bottom:2px'>✅ Qualidade de Dados</h1>"
    "<p style='margin-top:0;color:#94a3b8'>Validação, linhagem e observabilidade do pipeline</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPIs do pipeline
# ---------------------------------------------------------------------------
resumo_antes = qualidade["resumo"]["antes"] if qualidade else {"pass": 0, "total": 0}
resumo_depois = qualidade["resumo"]["depois"] if qualidade else {"pass": 0, "total": 0}
ultima_exec = "—"
duracao = "—"
if execucoes is not None and not execucoes.empty:
    ultima_exec = str(execucoes.iloc[0]["data_execucao"])
    dur = float(execucoes.iloc[0]["duracao_seg"] or 0)
    duracao = f"{dur:.1f}s"

kpis = [
    ("Checks — antes", f"{resumo_antes['pass']}/{resumo_antes['total']}",
     "sobre os dados brutos ingeridos"),
    ("Checks — depois", f"{resumo_depois['pass']}/{resumo_depois['total']}",
     "após limpeza e padronização"),
    ("Última execução", str(ultima_exec), f"duracão {duracao}"),
    ("Vendas na camada gold", fmt_int(len(vendas)), "fact_sales"),
]
cards = "".join(
    f"<div class='kpi-card'><div class='kpi-label'>{nome}</div>"
    f"<div class='kpi-value'>{valor}</div><div class='kpi-sub'>{sub}</div></div>"
    for nome, valor, sub in kpis
)
st.markdown(f"<div class='kpi-grid'>{cards}</div>", unsafe_allow_html=True)

st.markdown(
    "<div class='chip-row'>"
    + chip("FONTE: " + dados["origem"].upper())
    + chip(f"{fmt_int(vendas['valor'].sum())} RECEITA TOTAL", "#34D399")
    + "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Checks antes vs depois
# ---------------------------------------------------------------------------
if qualidade:
    col1, col2 = st.columns(2)

    def _render_checks(checks: list[dict], titulo: str) -> None:
        st.markdown(f"### {titulo}")
        linhas = []
        for c in checks:
            badge = "PASS" if c["status"] == "PASS" else "FAIL"
            classe = "badge-pass" if c["status"] == "PASS" else "badge-fail"
            linhas.append(
                f"<div class='check-row'><span class='{classe}'>{badge}</span>"
                f"{c['check']} · <span style='color:#7dd3fc'>{c['coluna']}</span>"
                f"<span style='float:right;color:#94a3b8'>{c['valor']} / {c['limite']}</span></div>"
            )
        st.markdown("".join(linhas), unsafe_allow_html=True)

    with col1:
        _render_checks(qualidade["antes"], "🔴 Antes — dados brutos")
    with col2:
        _render_checks(qualidade["depois"], "🟢 Depois — dados limpos")
else:
    st.info("Nenhum relatório de qualidade encontrado. Rode o pipeline para gerar: `python scripts/run_pipeline.py`.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Linhagem (camadas)
# ---------------------------------------------------------------------------
st.markdown("### 🧬 Linhagem dos dados (camadas)")

camadas = pd.DataFrame({
    "camada": ["bronze", "silver", "gold"],
    "tabela": ["stg_* (raw)", "dim_* (normalizado)", "fact_sales (analítico)"],
    "cor": ["#60A5FA", "#A78BFA", "#34D399"],
})
if linhagem is not None and not linhagem.empty:
    soma = linhagem["registros"].sum()
    camadas.loc[0, "qtd"] = int(linhagem[linhagem["camada"] == "bronze"]["registros"].sum())
    camadas.loc[1, "qtd"] = int(linhagem[linhagem["camada"] == "silver"]["registros"].sum())
    camadas.loc[2, "qtd"] = int(linhagem[linhagem["camada"] == "gold"]["registros"].sum())
else:
    camadas["qtd"] = [len(vendas), len(vendas) + 100, len(vendas)]
camadas["pct"] = camadas["qtd"] / camadas["qtd"].sum() * 100

fig = px.bar(
    camadas, x="qtd", y="camada", orientation="h", color="camada",
    color_discrete_map={"bronze": "#60A5FA", "silver": "#A78BFA", "gold": "#34D399"},
    text="qtd",
)
fig.update_traces(
    texttemplate="%{text:,} registros",
    textposition="outside",
    hovertemplate="%{y} · %{customdata}<br><b>%{x:,}</b> registros<extra></extra>",
    customdata=camadas["tabela"],
)
layout_base(fig, "Volume de dados por camada", altura=300)
fig.update_xaxes(visible=False)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.markdown(
    "<div style='font-family:JetBrains Mono,monospace;font-size:12px;color:#64748b'>"
    "bronze = ingestão bruta · silver = dimensões normalizadas (star schema) · "
    "gold = fato + views analíticas</div>",
    unsafe_allow_html=True,
)

st.markdown("---")

# ---------------------------------------------------------------------------
# Execuções recentes + guia
# ---------------------------------------------------------------------------
col1, col2 = st.columns([1.6, 1])

with col1:
    st.markdown("### 🕓 Execuções recentes do pipeline")
    if execucoes is not None and not execucoes.empty:
        st.dataframe(
            execucoes.head(12),
            width="stretch",
            hide_index=True,
            column_config={
                "execution_id": st.column_config.NumberColumn("#"),
                "data_execucao": st.column_config.TextColumn("Data"),
                "etapa": st.column_config.TextColumn("Etapa"),
                "status": st.column_config.TextColumn("Status"),
                "registros": st.column_config.NumberColumn("Registros", format="%d"),
                "duracao_seg": st.column_config.NumberColumn("Duração (s)", format="%.1f"),
            },
        )
    else:
        st.info("Log de execuções disponível após carregar os dados no banco (`scripts/load.py`).")

with col2:
    st.markdown("### 🚀 Como reproduzir")
    st.code(
        "# 1. Banco PostgreSQL (opcional — usa SQLite se ausente)\n"
        "docker compose up -d\n\n"
        "# 2. Dados sintéticos\n"
        "python scripts/generate_data.py\n\n"
        "# 3. Pipeline completo\n"
        "python scripts/run_pipeline.py\n\n"
        "# 4. Dashboard\n"
        "streamlit run dashboard/app.py\n\n"
        "# 5. Qualidade no banco (SQL)\n"
        "python scripts/quality_check.py --banco",
        language="bash",
    )
