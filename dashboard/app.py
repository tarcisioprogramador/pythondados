"""DataPipeline Pro — Site de Análise de Dados.

Página inicial (landing): apresenta o projeto como produto — pipeline,
arquitetura, funcionalidades — e leva o visitante ao painel analítico.
"""

from __future__ import annotations

import streamlit as st

from utils import carregar_dados, fmt_brl, fmt_int

st.set_page_config(
    page_title="DataPipeline Pro — Análise de Dados",
    page_icon="🚀",
    layout="wide",
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600;700&display=swap');

.stApp { background: radial-gradient(1200px 640px at 18% -12%, #17223f 0%, #0b1120 58%) fixed, #0b1120; }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1180px; }
h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: #f1f5f9; }
p, li { color: #cbd5e1; }
[data-testid="stSidebar"] { background: #0c1424; border-right: 1px solid #1e293b; }

.topbar { display: flex; align-items: center; gap: 12px; margin-bottom: 34px; }
.logo { width: 38px; height: 38px; border-radius: 10px; background: linear-gradient(135deg, #22D3EE, #A78BFA); display: flex; align-items: center; justify-content: center; font-size: 19px; box-shadow: 0 0 24px #22D3EE55; }
.nome-site { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 18px; color: #f1f5f9; letter-spacing: .3px; }
.tag-site { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 2px; color: #7dd3fc; text-transform: uppercase; }

.hero { margin: 8px 0 18px; }
.hero-eyebrow { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: 3px; color: #22D3EE; text-transform: uppercase; margin-bottom: 12px; }
.hero-titulo { font-size: 44px; line-height: 1.08; margin: 0; }
.hero-titulo .grad { background: linear-gradient(90deg, #22D3EE, #A78BFA); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.hero-sub { font-size: 16.5px; color: #94a3b8; max-width: 640px; margin: 14px 0 0; line-height: 1.55; }

.fluxo { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 26px 0 6px; }
.etapa { font-family: 'JetBrains Mono', monospace; font-size: 12px; letter-spacing: 1px; color: #cbd5e1; border: 1px solid #1e293b; background: #101829; border-radius: 8px; padding: 8px 14px; }
.etapa.destaque { color: #0b1120; background: linear-gradient(90deg, #22D3EE, #7dd3fc); border-color: #22D3EE; font-weight: 700; }
.seta { color: #334155; font-size: 16px; }

.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 26px 0 8px; }
.stat { background: linear-gradient(180deg, #141d33 0%, #101829 100%); border: 1px solid #1e293b; border-radius: 12px; padding: 14px 16px; }
.stat .v { font-family: 'JetBrains Mono', monospace; font-size: 21px; font-weight: 700; color: #f1f5f9; }
.stat .l { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: 1.4px; text-transform: uppercase; color: #64748b; margin-top: 4px; }

.secao-titulo { font-size: 24px; margin: 46px 0 4px; }
.secao-sub { color: #94a3b8; font-size: 14.5px; margin-bottom: 18px; }

.feature-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.feature { background: linear-gradient(180deg, #131c31 0%, #101829 100%); border: 1px solid #1e293b; border-radius: 13px; padding: 18px 18px 14px; }
.feature .icone { font-size: 22px; }
.feature .t { font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 15.5px; color: #f1f5f9; margin: 8px 0 4px; }
.feature .d { font-size: 13px; color: #94a3b8; line-height: 1.5; }

.camadas { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 6px; }
.camada { border-radius: 13px; padding: 16px 18px; border: 1px solid; }
.camada.bronze { background: #13213b; border-color: #60A5FA44; }
.camada.silver { background: #1a1733; border-color: #A78BFA44; }
.camada.gold { background: #0f2a23; border-color: #34D39944; }
.camada .n { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 2px; text-transform: uppercase; }
.camada.bronze .n { color: #93c5fd; } .camada.silver .n { color: #c4b5fd; } .camada.gold .n { color: #6ee7b7; }
.camada .t { font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 16px; color: #f1f5f9; margin: 6px 0 4px; }
.camada .d { font-size: 12.5px; color: #94a3b8; line-height: 1.5; }
.camada .tabelas { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #64748b; margin-top: 8px; }

.passo { display: flex; gap: 16px; align-items: flex-start; margin-bottom: 18px; }
.passo-num { font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: #0b1120; background: linear-gradient(135deg, #22D3EE, #7dd3fc); border-radius: 9px; min-width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; }
.passo .t { font-family: 'Space Grotesk', sans-serif; font-weight: 600; color: #f1f5f9; font-size: 16px; margin-bottom: 2px; }
.passo .d { color: #94a3b8; font-size: 13.5px; line-height: 1.5; }

.badge { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #cbd5e1; border: 1px solid #1e293b; background: #101829; border-radius: 999px; padding: 5px 13px; margin: 0 6px 8px 0; display: inline-block; }

.cta { display: flex; gap: 14px; margin-top: 26px; }
[data-testid="stPageLink"] a { font-family: 'Space Grotesk', sans-serif; font-weight: 600; border-radius: 10px; padding: 11px 20px; text-decoration: none; border: 1px solid; transition: all .18s ease; }
[data-testid="stPageLink"] a:hover { transform: translateY(-1px); }
.link-primario a { color: #0b1120 !important; background: linear-gradient(90deg, #22D3EE, #7dd3fc); border-color: #22D3EE !important; }
.link-secundario a { color: #cbd5e1 !important; background: #101829; border-color: #1e293b !important; }
.link-secundario a:hover { border-color: #22D3EE88 !important; color: #f1f5f9 !important; }

.painel-card { background: linear-gradient(180deg, #131c31 0%, #101829 100%); border: 1px solid #1e293b; border-radius: 13px; padding: 18px; }
.painel-card:hover { border-color: #22D3EE66; }
.painel-card .i { font-size: 22px; }
.painel-card .t { font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 15.5px; color: #f1f5f9; margin: 8px 0 4px; }
.painel-card .d { font-size: 12.5px; color: #94a3b8; line-height: 1.5; margin-bottom: 10px; }

.footer { margin-top: 54px; padding-top: 18px; border-top: 1px solid #1e293b; font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #475569; text-align: center; }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Dados vivos (fallback se o pipeline ainda não rodou)
# ---------------------------------------------------------------------------
dados = None
try:
    dados = carregar_dados()
except FileNotFoundError:
    dados = None
    st.info("💡 Rode o pipeline para ver os números reais no site: `python scripts/run_pipeline.py`")
except Exception as exc:  # noqa: BLE001
    dados = None
    st.warning(f"Não foi possível carregar os dados: {exc}")

# ---------------------------------------------------------------------------
# Topbar
# ---------------------------------------------------------------------------
st.markdown(
    "<div class='topbar'>"
    "<div class='logo'>🚀</div>"
    "<div><div class='nome-site'>DataPipeline Pro</div>"
    "<div class='tag-site'>Engenharia de Dados · Python + SQL</div></div>"
    "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    "<div class='hero'>"
    "<div class='hero-eyebrow'>● Pipeline de dados em produção</div>"
    "<h1 class='hero-titulo'>Do dado bruto<br>ao <span class='grad'>insight</span>.</h1>"
    "<p class='hero-sub'>Uma plataforma completa de análise de dados para negócios locais: "
    "ingestão via API ou CSV, transformação com Python e SQL, validação de qualidade "
    "e um painel interativo — tudo conectado em um único fluxo.</p>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='fluxo'>"
    "<span class='etapa'>📥 INGESTÃO</span><span class='seta'>→</span>"
    "<span class='etapa'>🧹 TRANSFORMAÇÃO</span><span class='seta'>→</span>"
    "<span class='etapa'>✅ QUALIDADE</span><span class='seta'>→</span>"
    "<span class='etapa'>💾 CARGA</span><span class='seta'>→</span>"
    "<span class='etapa destaque'>📊 INSIGHT</span>"
    "</div>",
    unsafe_allow_html=True,
)

col_a, col_b = st.columns([1, 1])
with col_a:
    st.page_link(
        "pages/1_📈_Visão_Geral.py",
        label="🔍  Explorar o painel",
        width="stretch",
        help="KPIs, rankings e análises dos negócios",
    )
with col_b:
    st.page_link(
        "pages/4_📤_Analisador.py",
        label="📤  Analisar meus dados",
        width="stretch",
        help="Envie um CSV e receba análises automáticas",
    )

# ---------------------------------------------------------------------------
# Stats ao vivo
# ---------------------------------------------------------------------------
if dados is not None:
    vendas = dados["vendas"]
    receita = float(vendas["valor"].sum())
    qualidade = (dados["qualidade"] or {}).get("resumo", {}).get("depois")
    q_texto = f"{qualidade.get('pass', '—')}/{qualidade.get('total', '—')}" if qualidade else "—"
    st.markdown(
        "<div class='stats-grid'>"
        f"<div class='stat'><div class='v'>{fmt_int(len(vendas))}</div><div class='l'>Vendas analisadas</div></div>"
        f"<div class='stat'><div class='v'>{fmt_brl(receita)}</div><div class='l'>Receita total</div></div>"
        f"<div class='stat'><div class='v'>{fmt_int(vendas['business_key'].nunique())}</div><div class='l'>Negócios</div></div>"
        f"<div class='stat'><div class='v'>{q_texto}</div><div class='l'>Checks de qualidade</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div class='stats-grid'>"
        "<div class='stat'><div class='v'>--</div><div class='l'>Rode o pipeline para ver os números</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# O que é
# ---------------------------------------------------------------------------
st.markdown("<h2 class='secao-titulo'>O que é</h2>", unsafe_allow_html=True)
st.markdown(
    "<p class='secao-sub'>Cada etapa de um ambiente real de dados, organizada em camadas "
    "e com qualidade mensurável.</p>",
    unsafe_allow_html=True,
)

features = [
    ("📥", "Ingestão de dados", "Consome dados via API (com paginação) ou arquivos CSV, com rastreabilidade de cada carga."),
    ("🧹", "Transformação", "Limpeza, padronização e criação de métricas com Python, modelando em star schema."),
    ("🗄️", "Banco de dados", "PostgreSQL em produção, com fallback automático para SQLite na demonstração."),
    ("✅", "Qualidade de dados", "Checagens de nulos, duplicados, faixas e formatos — com relatório antes vs depois."),
    ("⚙️", "Automação", "Pipeline orquestrado em etapas, com logs de execução e observabilidade."),
    ("📊", "Dashboard", "KPIs, rankings, filtros dinâmicos e insights estratégicos em tempo real."),
]
cards = "".join(
    f"<div class='feature'><div class='icone'>{i}</div><div class='t'>{t}</div><div class='d'>{d}</div></div>"
    for i, t, d in features
)
st.markdown(f"<div class='feature-grid'>{cards}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Arquitetura
# ---------------------------------------------------------------------------
st.markdown("<h2 class='secao-titulo'>Arquitetura em camadas</h2>", unsafe_allow_html=True)
st.markdown(
    "<p class='secao-sub'>Modelagem no padrão data lakehouse: cada camada tem um papel claro.</p>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='camadas'>"
    "<div class='camada bronze'><div class='n'>Camada 01 · Bronze</div><div class='t'>Dados brutos</div>"
    "<div class='d'>Registros exatamente como foram ingeridos, sem tratamento.</div>"
    "<div class='tabelas'>stg_businesses · stg_transactions</div></div>"
    "<div class='camada silver'><div class='n'>Camada 02 · Silver</div><div class='t'>Dados limpos</div>"
    "<div class='d'>Dimensões normalizadas com chaves substitutas (star schema).</div>"
    "<div class='tabelas'>dim_category · dim_time · dim_business</div></div>"
    "<div class='camada gold'><div class='n'>Camada 03 · Gold</div><div class='t'>Dados analíticos</div>"
    "<div class='d'>Fato de vendas e views prontas para consumo e dashboard.</div>"
    "<div class='tabelas'>fact_sales · vw_* (marts)</div></div>"
    "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Como funciona
# ---------------------------------------------------------------------------
st.markdown("<h2 class='secao-titulo'>Como funciona</h2>", unsafe_allow_html=True)
st.markdown(
    "<p class='secao-sub'>Do arquivo/API ao gráfico, em quatro passos executáveis.</p>",
    unsafe_allow_html=True,
)
passos = [
    ("1", "Gere ou ingira os dados", "Script gera dados sintéticos realistas de negócios locais (CNPJ válido, vendas com sazonalidade) — ou consuma a mock API com paginação."),
    ("2", "Transforme e modele", "Python limpa duplicatas, normaliza CNPJ/datas/moedas e constrói o star schema; SQL cria as views analíticas."),
    ("3", "Valide e carregue", "16 checks de qualidade quantificam o ganho antes vs depois; a carga é idempotente e registra cada execução."),
    ("4", "Explore no painel", "O dashboard lê a camada gold e apresenta KPIs, rankings, filtros e insights com tema próprio."),
]
passos_html = "".join(
    f"<div class='passo'><div class='passo-num'>{n}</div>"
    f"<div><div class='t'>{t}</div><div class='d'>{d}</div></div></div>"
    for n, t, d in passos
)
st.markdown(passos_html, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Conheça o painel
# ---------------------------------------------------------------------------
st.markdown("<h2 class='secao-titulo'>Conheça o painel</h2>", unsafe_allow_html=True)
st.markdown(
    "<p class='secao-sub'>Quatro áreas para explorar os dados.</p>",
    unsafe_allow_html=True,
)

p1, p2, p3, p4 = st.columns(4)
with p1:
    st.markdown(
        "<div class='painel-card'><div class='i'>📈</div><div class='t'>Visão Geral</div>"
        "<div class='d'>KPIs, receita mensal, ranking e distribuições com filtros dinâmicos.</div></div>",
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_📈_Visão_Geral.py", label="Abrir →", width="stretch")
with p2:
    st.markdown(
        "<div class='painel-card'><div class='i'>📊</div><div class='t'>Análises</div>"
        "<div class='d'>Sazonalidade, Pareto, perfil dos negócios e tendências.</div></div>",
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_📊_Análises.py", label="Abrir →", width="stretch")
with p3:
    st.markdown(
        "<div class='painel-card'><div class='i'>✅</div><div class='t'>Qualidade</div>"
        "<div class='d'>Checks antes vs depois, linhagem das camadas e log de execuções.</div></div>",
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_✅_Qualidade.py", label="Abrir →", width="stretch")
with p4:
    st.markdown(
        "<div class='painel-card'><div class='i'>📤</div><div class='t'>Analisador</div>"
        "<div class='d'>Envie um CSV qualquer e receba KPIs, gráficos e insights automáticos.</div></div>",
        unsafe_allow_html=True,
    )
    st.page_link("pages/4_📤_Analisador.py", label="Abrir →", width="stretch")

# ---------------------------------------------------------------------------
# Stack
# ---------------------------------------------------------------------------
st.markdown("<h2 class='secao-titulo'>Tecnologias</h2>", unsafe_allow_html=True)
st.markdown(
    "<div>"
    + "".join(f"<span class='badge'>{t}</span>" for t in [
        "Python", "Pandas", "NumPy", "SQL", "PostgreSQL", "SQLite",
        "SQLAlchemy", "Streamlit", "Plotly", "Docker", "pytest", "psycopg",
    ])
    + "</div>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    "<div class='footer'>DataPipeline Pro · Engenharia de Dados · Ingestão → Transformação → "
    "Qualidade → Carga → Dashboard<br>dados sintéticos gerados localmente · modelo star schema</div>",
    unsafe_allow_html=True,
)
