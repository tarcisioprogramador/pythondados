"""Configuração do pytest: garante que o pacote `etl` seja importável."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
