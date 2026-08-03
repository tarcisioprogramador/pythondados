"""DataPipeline Pro — Entry point da raiz (Hugging Face Spaces).

O Hugging Face (SDK Streamlit) executa `streamlit run app.py` a partir da
raiz do repositório. Este arquivo carrega a aplicação principal (landing
page) em dashboard/app.py, mantendo o multipage (páginas em ./pages/).
"""

import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))

# Torna os módulos do dashboard importáveis (utils, analisador, etc.)
sys.path.insert(0, os.path.join(RAIZ, "dashboard"))

with open(os.path.join(RAIZ, "dashboard", "app.py"), encoding="utf-8") as arquivo:
    exec(compile(arquivo.read(), "dashboard/app.py", "exec"))
