"""Testes dos transformadores (limpeza, padronização e CNPJ)."""

import pandas as pd
import pytest

from etl.transformers import (
    limpar_businesses,
    limpar_transacoes,
    normalizar_cnpj,
    parsear_valor_monetario,
    validar_cnpj,
)


# ---------------------------------------------------------------------------
# CNPJ
# ---------------------------------------------------------------------------
class TestCNPJ:
    def test_cnpj_valido_sem_mascara(self):
        # CNPJ conhecido válido: 11.222.333/0001-81
        assert validar_cnpj("11222333000181") is True

    def test_cnpj_valido_com_mascara(self):
        assert validar_cnpj("11.222.333/0001-81") is True

    def test_cnpj_invalido_digito_errado(self):
        assert validar_cnpj("11222333000182") is False

    def test_cnpj_repetido_e_curto(self):
        assert validar_cnpj("00000000000000") is False
        assert validar_cnpj("12345") is False

    def test_normalizar_cnpj(self):
        assert normalizar_cnpj("11.222.333/0001-81") == "11222333000181"


# ---------------------------------------------------------------------------
# Valores monetários
# ---------------------------------------------------------------------------
class TestValoresMonetarios:
    def test_formato_brasileiro(self):
        serie = pd.Series(["R$ 1.234,56", "89.90", "12,5"])
        resultado = parsear_valor_monetario(serie)
        assert resultado.iloc[0] == pytest.approx(1234.56)
        assert resultado.iloc[1] == pytest.approx(89.90)
        assert resultado.iloc[2] == pytest.approx(12.5)

    def test_valor_vazio_vira_nan(self):
        serie = pd.Series(["", "   ", "abc"])
        resultado = parsear_valor_monetario(serie)
        assert resultado.isna().all()


# ---------------------------------------------------------------------------
# Limpeza de negócios
# ---------------------------------------------------------------------------
class TestLimparBusinesses:
    def _base(self):
        return pd.DataFrame(
            {
                "business_id": ["BUS1", "BUS1", "BUS2", "BUS3"],
                "nome": ["Padaria  Doce  Pão", "Padaria  Doce  Pão", "mercado bom preço", "Oficina Top"],
                "cnpj": ["11222333000181", "11222333000181", "11.222.333/0001-81", "99999999999999"],
                "categoria": ["ALIMENTACAO", "ALIMENTACAO", "VAREJO", "AUTOMOTIVO"],
                "setor": ["Alimentação", "Alimentação", "Varejo", "Automotivo"],
                "cidade": ["São Paulo", "São Paulo", "Rio de Janeiro", "Curitiba"],
                "estado": ["SP", "SP", "rj", "PR"],
                "endereco": ["Rua  A", "Rua  A", "Av. B", ""],
                "data_abertura": ["15/01/2020", "15/01/2020", "2021-03-10", "2019-12-01"],
                "num_funcionarios": ["10", "10", "25", "8"],
                "email": ["a@b.com", "a@b.com", "c@d.com", "e@f.com"],
                "telefone": ["111", "111", "222", "333"],
            }
        )

    def test_remove_duplicados_e_padroniza(self):
        df = limpar_businesses(self._base())
        assert len(df) == 3  # BUS1 duplicado removido
        assert df.iloc[0]["nome"] == "Padaria Doce Pão"
        assert df.iloc[1]["nome"] == "Mercado Bom Preço"
        assert df.iloc[1]["estado"] == "RJ"  # uppercase

    def test_cnpj_invalido_vira_nulo(self):
        df = limpar_businesses(self._base())
        invalido = df[df["business_id"] == "BUS3"]["cnpj"]
        assert pd.isna(invalido.iloc[0])

    def test_data_mista_parseada(self):
        df = limpar_businesses(self._base())
        df = df.sort_values("business_id").reset_index(drop=True)
        assert str(df.iloc[0]["data_abertura"].date()) == "2020-01-15"


# ---------------------------------------------------------------------------
# Limpeza de transações
# ---------------------------------------------------------------------------
class TestLimparTransacoes:
    def _base(self):
        return pd.DataFrame(
            {
                "transaction_id": ["T1", "T1", "T2", "T3", "T4"],
                "business_id": ["BUS1"] * 5,
                "data_venda": ["2024-01-15", "2024-01-15", "15/01/2024", "2024-01-15", ""],
                "valor": ["89.90", "89.90", "R$ 1.234,56", "-50.0", "10.0"],
                "quantidade": ["2", "2", "3", "1", "1"],
                "forma_pagamento": ["PIX", "PIX", "pix", "CRÉDITO", "PIX"],
                "canal": ["Loja física", "Loja física", "online", "Loja física", "Loja física"],
                "avaliacao": ["4.5", "4.5", "9", "4.0", "4.0"],
            }
        )

    def test_limpeza_completa(self):
        df = limpar_transacoes(self._base())
        assert len(df) == 2  # duplicata, negativa e data vazia removidas
        assert df["valor"].min() > 0
        assert df["valor"].max() == pytest.approx(1234.56)

    def test_data_mista_e_padronizacao(self):
        df = limpar_transacoes(self._base())
        df = df.sort_values("transaction_id").reset_index(drop=True)
        linha = df[df["transaction_id"] == "T2"].iloc[0]
        assert str(linha["data_venda"].date()) == "2024-01-15"
        assert linha["forma_pagamento"] == "PIX"
        assert linha["canal"] == "ONLINE"

    def test_avaliacao_fora_da_faixa_vira_nan(self):
        df = limpar_transacoes(self._base())
        linha = df[df["transaction_id"] == "T2"].iloc[0]
        assert pd.isna(linha["avaliacao"])
