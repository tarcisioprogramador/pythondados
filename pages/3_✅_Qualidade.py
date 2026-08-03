"""Wrapper do multipage na raiz — carrega dashboard/pages/3_✅_Qualidade.py."""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "dashboard"))

CAMINHO = os.path.join(RAIZ, "dashboard", "pages", "3_✅_Qualidade.py")
with open(CAMINHO, encoding="utf-8") as arquivo:
    exec(compile(arquivo.read(), "3_✅_Qualidade.py", "exec"))
