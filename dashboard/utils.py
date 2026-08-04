"""Utilitários compartilhados do dashboard (DataPipeline Pro)."""

from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Sincroniza secrets do Streamlit Cloud → variáveis de ambiente
# ---------------------------------------------------------------------------
# No Streamlit Community Cloud, secrets definidos no painel (Settings →
# Secrets) ficam disponíveis apenas via st.secrets — eles NÃO viram variáveis
# de ambiente automaticamente. Como o etl.config lê os.getenv("DATABASE_URL"),
# este bloco injeta os secrets no ambiente ANTES de importar o config.
# Fora do Streamlit (pipeline local, testes) o try/except mantém tudo igual.
import pandas as pd
import streamlit as st

# Sincroniza secrets do Streamlit Cloud → variáveis de ambiente. No Streamlit
# Community Cloud, secrets do painel ficam só em st.secrets (não viram env vars
# automaticamente). Como etl.config lê os.getenv("DATABASE_URL"), injetamos aqui
# ANTES de importar o config. Fora do runtime do Streamlit, o try/except segue.
try:
    for _chave in ("DATABASE_URL", "PIPELINE_DB_ONLY", "API_URL"):
        if _chave in st.secrets and _chave not in os.environ:
            os.environ[_chave] = str(st.secrets[_chave])
except Exception:  # noqa: BLE001 — sem runtime do Streamlit, segue normal
    pass

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
      1. Banco de dados — quando DATABASE_URL está configurado explicitamente
         (ex: Neon/PostgreSQL na nuvem) — demonstra o banco real no portfólio
      2. Parquet  (data/processed) — leitura ~10x mais rápida (padrão)
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

    # Um DATABASE_URL explícito (diferente do default localhost) indica que o
    # usuário configurou um banco real (ex: Neon) → prioriza o banco.
    banco_explicito = config.DATABASE_URL not in ("", config.POSTGRES_PADRAO)

    def _ler_banco() -> bool:
        """Tenta ler todas as tabelas da camada gold do banco. Retorna True se ok."""
        nonlocal fato, dim_b, dim_c, dim_t, linhagem, execucoes, origem
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
            return True
        except Exception:  # noqa: BLE001 — sem banco disponível, segue para parquet/CSV
            fato = None
            return False

    # 1) Banco de dados primeiro, quando configurado explicitamente (ex: Neon)
    if banco_explicito:
        _ler_banco()

    # 2) Parquet (mais rápido) — mesmo conteúdo da camada processada.
    #    Se o pyarrow estiver ausente ou o arquivo corrompido, cai no
    #    banco/CSV automaticamente (não derruba o site).
    if fato is None and _parquet("fact_sales").exists():
        try:
            fato = pd.read_parquet(_parquet("fact_sales"))
            dim_b = pd.read_parquet(_parquet("dim_business"))
            dim_c = pd.read_parquet(_parquet("dim_category"))
            dim_t = pd.read_parquet(_parquet("dim_time"))
            origem = "camada gold · parquet"
        except Exception:  # noqa: BLE001 — parquet indisponível → segue para banco/CSV
            fato = None

    # 3) Banco de dados como fallback (quando não foi priorizado acima)
    if fato is None and not banco_explicito:
        _ler_banco()

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
        try:
            metricas = pd.read_parquet(caminho_metricas)
        except Exception:  # noqa: BLE001
            metricas = None
    if metricas is None and _csv("metricas_negocios").exists():
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
/* ── Tablet (até 768px / 48em) ──────────────────────────────── */
@media (max-width: 48em) {
    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="stHorizontalBlock"] > div { min-width: 100% !important; width: 100% !important; }

    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1rem !important;
    }
    .hero-titulo { font-size: 28px !important; line-height: 1.15 !important; }
    .hero-sub { font-size: 14px !important; }
    .topbar { margin-bottom: 18px; }

    /* KPIs: 5 colunas → 3 colunas */
    .kpi-grid { grid-template-columns: repeat(3, 1fr); gap: 10px; }
    .kpi-card { padding: 12px 14px 10px; }
    .kpi-label { font-size: 10px !important; letter-spacing: 1.2px !important; }
    .kpi-value { font-size: 16px !important; }
    .kpi-sub { font-size: 11px !important; }

    /* Stats grid: 4 colunas → 2 colunas */
    .stats-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .stat .v { font-size: 15px !important; }
    .stat .l { font-size: 10px !important; }

    .feature-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
    .camadas { grid-template-columns: 1fr; }
    .secao-titulo { font-size: 20px !important; }
    .secao { font-size: 15px !important; }
    .insight { font-size: 12.5px !important; padding: 10px 14px !important; }
    .cta { flex-direction: column; }
    .footer { font-size: 10.5px; }
    .check-row { font-size: 12px; }
    .empty-box { padding: 24px 12px !important; }

    /* Gráficos Plotly: menor altura em tablet */
    .stPlotlyChart { height: auto !important; }
}

/* ── Mobile (até 480px / 30em) ──────────────────────────────── */
@media (max-width: 30em) {
    .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
    }

    .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .kpi-card { padding: 10px 12px 8px; }
    .kpi-value { font-size: 14px !important; }
    .kpi-label { font-size: 9px !important; }

    .stats-grid { grid-template-columns: 1fr; }
    .stat .v { font-size: 14px !important; }

    .feature-grid { grid-template-columns: 1fr; }
    .hero-titulo { font-size: 24px !important; }
    .hero-sub { font-size: 13px !important; }

    /* Gráficos: touch otimizado */
    .stPlotlyChart { touch-action: manipulation; }

    /* Tabelas e elementos largos */
    [data-testid="stDataFrame"] { font-size: 12px !important; }

    .check-row { font-size: 11px; padding: 8px !important; }
    .footer { font-size: 9.5px; padding: 10px !important; }
}
"""


def injetar_css_mobile() -> None:
    """Aplica o CSS responsivo compartilhado (usado por todas as páginas)."""
    st.markdown(f"<style>{CSS_MOBILE}</style>", unsafe_allow_html=True)
