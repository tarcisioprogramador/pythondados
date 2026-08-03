"""Testes do analisador automático de dados (dashboard/analisador.py)."""

import pandas as pd

from dashboard.analisador import detectar_tipo, gerar_analise


class TestDetectarTipo:
    def test_coluna_numerica(self):
        assert detectar_tipo(pd.Series([1, 2, 3, 10])) == "numerica"

    def test_coluna_numerica_convertivel(self):
        assert detectar_tipo(pd.Series(["1", "2,5", "3", "8"])) == "numerica"

    def test_coluna_categorica(self):
        assert detectar_tipo(pd.Series(["restaurante", "mercado", "padaria", "restaurante"])) == "categorica"

    def test_coluna_data_iso(self):
        assert detectar_tipo(pd.Series(["2024-01-01", "2024-01-02", "2024-01-03"])) == "data"

    def test_coluna_vazia(self):
        assert detectar_tipo(pd.Series([None, None, None])) == "vazia"


class TestGerarAnalise:
    def test_resumo_qualidade(self):
        df = pd.DataFrame({"x": [1, None, 3, 1], "categoria": ["A", "B", "A", "A"]})
        analise = gerar_analise(df)
        assert analise["resumo"]["nulos_total"] == 1
        assert analise["resumo"]["duplicados"] == 1  # linha [1, "A"] repetida
        assert analise["tipos"]["x"] == "numerica"
        assert analise["tipos"]["categoria"] == "categorica"

    def test_estatisticas_numericas(self):
        df = pd.DataFrame({"v": [10, 20, 30, 40]})
        analise = gerar_analise(df)
        stats = analise["numericas"][0]
        assert stats["media"] == 25.0
        assert stats["min"] == 10.0
        assert stats["max"] == 40.0

    def test_insight_de_concentracao(self):
        df = pd.DataFrame({"cat": ["A"] * 90 + ["B"] * 10})
        analise = gerar_analise(df)
        assert any("cat" in i and "A" in i for i in analise["insights"])

    def test_correlacao_forte(self):
        df = pd.DataFrame({"a": range(1, 21), "b": [x * 2 for x in range(1, 21)]})
        analise = gerar_analise(df)
        assert any("Correlação positiva" in i for i in analise["insights"])
