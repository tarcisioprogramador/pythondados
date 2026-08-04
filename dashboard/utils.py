"""Utilitários compartilhados do dashboard (DataPipeline Pro)."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from etl import config

# Paleta do painel (tema "console de operações de dados")
CORES = [
    "#22D3EE", "#A78BFA", "#34D399", "#F59E0B", "#F87171",
    "#60A5FA", "#F472B6", "#2DD4BF", "#FBBF24", "#94A3B8",
]


# ---------------------------------------------------------------------------
# Formatação pt-BR
# ---------------------------------------------------------------------------
def fmt_brl(valor) -> str:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "—"
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_int(valor) -> str:
    try:
        v = int(valor)
    except (TypeError, ValueError):
        return "—"
    return f"{v:,}".replace(",", ".")


def fmt_curto(valor) -> str:
    """Formato compacto para eixos: R$ 1,2 mi | R$ 345 mil | R$ 89."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "—"
    if v >= 1_000_000:
        return f"R$ {v / 1e6:.1f} mi".replace(".", ",")
    if v >= 1_000:
        return f"R$ {v / 1e3:.0f} mil".replace(".", ",")
    return f"R$ {v:.0f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Carregamento de dados (Parquet → banco → CSVs processados)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=86400, show_spinner="Carregando dados do pipeline...")
def carregar_dados() -> dict:
    """Carrega vendas + dimensões da camada processada.

    Ordem de preferência (todos contêm os mesmos dados da camada gold):
      1. Parquet  (data/processed) — leitura ~10x mais rápida (padrão)
      2. Banco de dados            — quando o pipeline rodou com banco local
      3. CSVs processados          — último recurso

    O cache dura 24 h (os dados são estáticos em um portfólio), então a
    primeira visita carrega rápido e as seguintes são instantâneas.
    """
    config.garantir_diretorios()
    processado = config.DATA_PROCESSED_DIR

    def _parquet(nome: str) -> pathlib.Path:
        return processado / f"{nome}.parquet"

    def _csv(nome: str) -> pathlib.Path:
        return processado / f"{nome}.csv"

    origem = "CSVs processados"
    fato = dim_b = dim_c = dim_t = None
    linhagem = execucoes = None

    # 1) Parquet (mais rápido) — mesmo conteúdo da camada processada
    if _parquet("fact_sales").exists():
        fato = pd.read_parquet(_parquet("fact_sales"))
        dim_b = pd.read_parquet(_parquet("dim_business"))
        dim_c = pd.read_parquet(_parquet("dim_category"))
        dim_t = pd.read_parquet(_parquet("dim_time"))
        origem = "camada gold · parquet"

    # 2) Banco de dados (views da camada gold)
    if fato is None:
        try:
            from etl.database import conectar, vendor
            engine = conectar()
            fato = pd.read_sql("SELECT * FROM fact_sales", engine)
            dim_b = pd.read_sql("SELECT * FROM dim_business", engine)
            dim_c = pd.read_sql("SELECT * FROM dim_category", engine)
            dim_t = pd.read_sql("SELECT * FROM dim_time", engine)
            origem = f"banco de dados ({vendor(engine)})"
            try:
                linhagem = pd.read_sql("SELECT * FROM vw_linhagem", engine)
                execucoes = pd.read_sql("SELECT * FROM vw_ultimas_execucoes", engine)
            except Exception:  # noqa: BLE001 — views ainda não criadas
                pass
        except Exception:  # noqa: BLE001 — sem banco disponível, usa os CSVs
            pass

    # 3) CSVs processados (último recurso)
    if fato is None:
        if not _csv("fact_sales").exists():
            raise FileNotFoundError(
                "Nenhum dado encontrado. Rode o pipeline primeiro:\n\n"
                "    python scripts/generate_data.py\n"
                "    python scripts/run_pipeline.py"
            )
        fato = pd.read_csv(_csv("fact_sales"))
        dim_b = pd.read_csv(_csv("dim_business"))
        dim_c = pd.read_csv(_csv("dim_category"))
        dim_t = pd.read_csv(_csv("dim_time"))

    vendas = (
        fato.merge(
            dim_b[["business_key", "nome", "cnpj", "categoria",
                   "cidade", "estado", "regiao"]],
            on="business_key", how="left",
        )
        .merge(dim_c[["categoria", "setor"]], on="categoria", how="left")
        .merge(dim_t, on="date_key", how="left")
    )
    vendas["data"] = pd.to_datetime(vendas["data"], errors="coerce")
    vendas = vendas.dropna(subset=["data"])

    # Métricas por negócio
    metricas = None
    caminho_metricas = _parquet("metricas_negocios")
    if caminho_metricas.exists():
        metricas = pd.read_parquet(caminho_metricas)
    elif _csv("metricas_negocios").exists():
        metricas = pd.read_csv(_csv("metricas_negocios"))

    # Linhagem por camada (parquet: contagem vem do metadado — instantânea;
    # CSV: varredura binária, sem decodificar o texto inteiro)
    if linhagem is None:
        def _contar(nome: str) -> int:
            parquet = _parquet(nome)
            if parquet.exists():
                try:
                    import pyarrow.parquet as pq
                    return pq.ParquetFile(parquet).metadata.num_rows
                except Exception:  # noqa: BLE001
                    pass
            caminho = _csv(nome)
            if not caminho.exists():
                return 0
            with open(caminho, "rb") as arquivo:
                return max(sum(1 for _ in arquivo) - 1, 0)

        # Camada bronze lida da camada processada (stg limpos) — assim o site
        # funciona no deploy sem depender do data/raw (regenerável pelo pipeline)
        linhagem = pd.DataFrame(
            [
                {"camada": "bronze", "tabela": "stg_businesses",
                 "registros": _contar("stg_businesses")},
                {"camada": "bronze", "tabela": "stg_transactions",
                 "registros": _contar("stg_transactions")},
                {"camada": "silver", "tabela": "dim_category",
                 "registros": _contar("dim_category")},
                {"camada": "silver", "tabela": "dim_time",
                 "registros": _contar("dim_time")},
                {"camada": "silver", "tabela": "dim_business",
                 "registros": _contar("dim_business")},
                {"camada": "gold", "tabela": "fact_sales",
                 "registros": _contar("fact_sales")},
            ]
        )

    # Relatório de qualidade mais recente
    try:
        from etl.quality import carregar_relatorio_latest
        qualidade = carregar_relatorio_latest()
    except Exception:  # noqa: BLE001
        qualidade = None

    return {
        "vendas": vendas,
        "metricas": metricas,
        "origem": origem,
        "linhagem": linhagem,
        "execucoes": execucoes,
        "qualidade": qualidade,
    }


# ---------------------------------------------------------------------------
# Layout padrão dos gráficos (tema consistente do painel)
# ---------------------------------------------------------------------------
def layout_base(fig, titulo: str | None = None, altura: int = 380, eixo_y: str | None = None):
    """Aplica o tema do painel a uma figura plotly."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#cbd5e1", size=13),
        title=dict(
            text=titulo,
            font=dict(family="Space Grotesk, sans-serif", size=17, color="#f1f5f9"),
            x=0.01,
            xanchor="left",
        ),
        height=altura,
        margin=dict(l=10, r=10, t=52, b=10),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.04, x=0.5, xanchor="center",
            font=dict(size=12),
        ),
        hoverlabel=dict(bgcolor="#1e293b", font_color="#e2e8f0", font_family="Inter"),
        colorway=CORES,
    )
    fig.update_xaxes(gridcolor="#1e293b", linecolor="#1e293b", zerolinecolor="#1e293b")
    fig.update_yaxes(gridcolor="#1e293b", linecolor="#1e293b", zerolinecolor="#1e293b", title=eixo_y)
    return fig


def chip(texto: str, cor: str = "#22D3EE") -> str:
    """Badge HTML estilizado para o cabeçalho do painel."""
    return (
        f'<span style="font-family:JetBrains Mono,monospace;font-size:12px;'
        f'letter-spacing:.5px;color:{cor};background:{cor}1a;border:1px solid {cor}55;'
        f'border-radius:999px;padding:3px 12px;margin-right:6px;">{texto}</span>'
    )


# ---------------------------------------------------------------------------
# CSS responsivo (mobile) — compartilhado por todas as páginas
# ---------------------------------------------------------------------------
CSS_MOBILE = """
/* Empilha as colunas do Streamlit em telas pequenas */
@media (max-width: 48em) {
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="stHorizontalBlock"] > div { min-width: 100% !important; width: 100% !important; }

    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
    }
    .hero-titulo { font-size: 30px !important; }
    .hero-sub { font-size: 14.5px !important; }
    .topbar { margin-bottom: 22px; }

    /* Grades de cards: 4-6 colunas viram 2 */
    .stats-grid, .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .feature-grid, .camadas { grid-template-columns: 1fr; }
    .kpi-value { font-size: 17px !important; }
    .stat .v { font-size: 15px !important; }
    .secao-titulo { font-size: 21px !important; }
    .secao { font-size: 16px !important; }
    .cta { flex-direction: column; }
    .footer { font-size: 10.5px; }
    .check-row { font-size: 12px; }
    .empty-box { padding: 28px 14px !important; }
}

/* Telas muito estreitas: 1 coluna só */
@media (max-width: 30em) {
    .stats-grid, .kpi-grid { grid-template-columns: 1fr; }
}
"""


def injetar_css_mobile() -> None:
    """Aplica o CSS responsivo compartilhado (usado por todas as páginas)."""
    st.markdown(f"<style>{CSS_MOBILE}</style>", unsafe_allow_html=True)
