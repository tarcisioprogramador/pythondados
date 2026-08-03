"""Testes do módulo de qualidade de dados."""

import pandas as pd

from etl.quality import executar_relatorio_qualidade
from etl.transformers import limpar_businesses, limpar_transacoes


def _bruto():
    """Dados brutos com defeitos propositais (realistas: ~5% de problemas)."""
    n = 40
    business_ids = [f"BUS{i:03d}" for i in range(1, n + 1)]

    businesses = pd.DataFrame(
        {
            "business_id": business_ids,
            "nome": [f"Negócio {i}" for i in range(1, n + 1)],
            "cnpj": ["11222333000181"] * n,
            "categoria": ["ALIMENTACAO"] * n,
            "setor": ["Alimentação"] * n,
            "cidade": ["São Paulo"] * n,
            "estado": ["SP"] * n,
            "endereco": ["Rua A, 10"] * n,
            "data_abertura": ["2020-01-15"] * n,
            "num_funcionarios": ["10"] * n,
            "email": ["a@b.com"] * n,
            "telefone": ["111"] * n,
        }
    )
    # Defeitos: duplicata exata, CNPJ vazio, CNPJ inválido, nome minúsculo,
    # data em formato brasileiro (todos ≈ 2,5% do total — abaixo do limite de 5%)
    businesses = pd.concat(
        [businesses, businesses.iloc[[0]]], ignore_index=True
    )  # duplicata
    businesses.loc[1, "cnpj"] = ""                 # vazio
    businesses.loc[2, "cnpj"] = "99999999999999"   # dígito inválido
    businesses.loc[3, "nome"] = "negócio 4 em minúsculo"
    businesses.loc[4, "data_abertura"] = "15/01/2020"

    transacoes = pd.DataFrame(
        {
            "transaction_id": [f"T{i}" for i in range(1, 11)] + ["T1"],
            "business_id": ["BUS001"] * 11,
            "data_venda": ["2024-01-15"] * 11,
            "valor": ["89.90"] * 11,
            "quantidade": ["2"] * 11,
            "forma_pagamento": ["PIX"] * 11,
            "canal": ["Loja física"] * 11,
            "avaliacao": ["4.5"] * 11,
        }
    )
    transacoes.loc[1, "valor"] = "R$ 1.234,56"     # formato monetário BR
    transacoes.loc[1, "data_venda"] = "15/01/2024"  # data em formato BR
    transacoes.loc[1, "forma_pagamento"] = "pix"    # minúsculo
    transacoes.loc[2, "valor"] = "-50.0"            # negativo (inconsistente)
    transacoes.loc[3, "data_venda"] = ""            # data vazia
    transacoes.loc[4, "avaliacao"] = "9"            # fora da faixa 1-5
    transacoes.loc[5, "avaliacao"] = ""             # avaliação vazia

    return {"businesses": businesses, "transactions": transacoes}


def _transformado():
    bruto = _bruto()
    return {
        "stg_businesses": limpar_businesses(bruto["businesses"]),
        "stg_transactions": limpar_transacoes(bruto["transactions"]),
    }


class TestRelatorioQualidade:
    def test_detecta_defeitos_no_bruto(self):
        relatorio = executar_relatorio_qualidade(_bruto(), _transformado())
        resumo_antes = relatorio["resumo"]["antes"]
        # O bruto deve ter pelo menos um check falhando
        assert resumo_antes["fail"] >= 3

    def test_estado_limpo_100_porcento_ok(self):
        relatorio = executar_relatorio_qualidade(_bruto(), _transformado())
        resumo_depois = relatorio["resumo"]["depois"]
        assert resumo_depois["pass"] == resumo_depois["total"]
        assert resumo_depois["fail"] == 0

    def test_relatorio_contem_antes_e_depois(self):
        relatorio = executar_relatorio_qualidade(_bruto(), _transformado())
        assert relatorio["antes"] and relatorio["depois"]
        assert all(c["status"] in {"PASS", "FAIL"} for c in relatorio["depois"])
