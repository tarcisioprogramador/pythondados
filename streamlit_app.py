"""DataPipeline Pro — Entry point padrão do Streamlit Cloud.

O Streamlit Cloud procura `streamlit_app.py` na raiz por padrão. Este
arquivo garante que o deploy funcione mesmo sem configurar o campo
"Main file path" — basta carregar a aplicação em dashboard/app.py.
"""

import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))

# Torna os módulos do dashboard importáveis (utils, analisador, etc.)
sys.path.insert(0, os.path.join(RAIZ, "dashboard"))

with open(os.path.join(RAIZ, "dashboard", "app.py"), encoding="utf-8") as arquivo:
    exec(compile(arquivo.read(), "dashboard/app.py", "exec"))
