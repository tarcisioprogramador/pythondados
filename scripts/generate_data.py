"""Gerador de dados sintéticos — negócios locais brasileiros.

Gera dois CSVs em data/raw:
  - businesses.csv   : cadastro de negócios (CNPJ válido, categoria, cidade...)
  - transactions.csv : vendas diárias (3,5 anos)

De propósito, o gerador injeta defeitos de qualidade de dados (~2% das linhas)
para o pipeline demonstrar limpeza e validação:
  - duplicatas, nulos, valores negativos, CNPJ inválido
  - datas e valores monetários em formatos mistos
  - avaliações fora da faixa 1-5 e transações órfãs

Uso:  python scripts/generate_data.py --businesses 120 --dias 1260 --seed 42
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from etl import config  # noqa: E402

# ---------------------------------------------------------------------------
# Catálogos (dados de apoio)
# ---------------------------------------------------------------------------

CATEGORIAS = [
    ("RESTAURANTES",   "Alimentação",           ["Padaria", "Restaurante", "Pizzaria", "Hamburgueria", "Sushi"]),
    ("BELEZA",         "Beleza & Estética",     ["Salão de Beleza", "Barbearia", "Studio de Sobrancelhas"]),
    ("SAUDE",          "Saúde & Fitness",       ["Academia", "Studio de Pilates", "Clínica de Estética"]),
    ("AUTOMOTIVO",     "Oficinas & Automotivo", ["Oficina Mecânica", "Auto Peças", "Lava-Rápido"]),
    ("TECNOLOGIA",     "Tecnologia",            ["Consultoria de TI", "Loja de Informática", "Desenvolvimento Web"]),
    ("VAREJO",         "Varejo & Moda",         ["Boutique", "Mercado", "Farmácia"]),
    ("EDUCACAO",       "Educação",              ["Escola de Idiomas", "Curso Técnico", "Reforço Escolar"]),
    ("CASA",           "Casa & Reformas",       ["Imobiliária", "Escritório de Arquitetura", "Pinturas"]),
    ("PET",            "Pet",                   ["Pet Shop", "Banho & Tosa", "Veterinária"]),
    ("SERVICOS",       "Serviços Financeiros",  ["Contabilidade", "Assessoria de Crédito", "Consultoria Financeira"]),
]

PREFIXOS = ["Doce", "Bom", "Prime", "Ideal", "Top", "Master", "Central", "Real", "Nova", "Alfa", "Global", "Casa"]
SUFIXOS = ["Mais", "Premium", "Popular", "Executivo", "Express", "Vip", "Ltda", "ME"]

CIDADES = [
    ("São Paulo", "SP"), ("Rio de Janeiro", "RJ"), ("Belo Horizonte", "MG"),
    ("Curitiba", "PR"), ("Porto Alegre", "RS"), ("Salvador", "BA"), ("Recife", "PE"),
    ("Fortaleza", "CE"), ("Brasília", "DF"), ("Campinas", "SP"), ("Florianópolis", "SC"),
    ("Goiânia", "GO"), ("Manaus", "AM"), ("Vitória", "ES"), ("Niterói", "RJ"),
]

RUAS = ["Rua das Flores", "Av. Central", "Rua 7 de Setembro", "Av. Paulista", "Rua XV de Novembro",
        "Rua das Palmeiras", "Av. Brasil", "Rua do Comércio", "Av. Rio Branco", "Rua Sete de Abril"]

FORMAS_PAGAMENTO = [("PIX", 0.45), ("Cartão de Crédito", 0.25), ("Cartão de Débito", 0.15),
                    ("Dinheiro", 0.10), ("Boleto", 0.05)]
CANAIS = [("Loja física", 0.55), ("Delivery", 0.25), ("Online", 0.20)]

# Pesos mensais (sazonalidade: fim de ano + janeiro fortes) e diários (fim de semana)
PESO_MES = {1: 1.10, 2: 0.95, 3: 0.95, 4: 0.90, 5: 0.95, 6: 0.95,
            7: 0.90, 8: 0.90, 9: 0.95, 10: 1.00, 11: 1.10, 12: 1.35}
PESO_DIA_SEMANA = [1.00, 1.00, 1.00, 1.10, 1.25, 1.60, 1.60]  # 0=segunda


# ---------------------------------------------------------------------------
# CNPJ com dígitos verificadores reais
# ---------------------------------------------------------------------------

def _dv(base: list[int], pesos: list[int]) -> int:
    resto = sum(int(d) * p for d, p in zip(base, pesos)) % 11
    return 0 if resto < 2 else 11 - resto


def gerar_cnpj(mascarado: bool = False) -> str:
    """Gera um CNPJ válido (dígitos verificadores corretos), opcionalmente mascarado."""
    base = [random.randint(0, 9) for _ in range(12)]
    base.append(_dv(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
    base.append(_dv(base, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
    numero = "".join(map(str, base))
    if mascarado:
        return f"{numero[:2]}.{numero[2:5]}.{numero[5:8]}/{numero[8:12]}-{numero[12:]}"
    return numero


def _as_float(valor) -> float:
    """Converte valores que podem já estar no formato 'R$ 1.234,56' para float."""
    texto = str(valor).replace("R$", "").strip()
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    return float(texto)


def gerar_cnpj_invalido() -> str:
    """CNPJ com dígito verificador incorreto (defeito proposital)."""
    valido = gerar_cnpj(mascarado=random.random() < 0.5)
    digito_errado = str((int(valido[-1]) + 3) % 10)
    return valido[:-1] + digito_errado


# ---------------------------------------------------------------------------
# Geração de negócios
# ---------------------------------------------------------------------------

def gerar_businesses(qtd: int) -> pd.DataFrame:
    registros = []
    for i in range(1, qtd + 1):
        codigo, setor, tipos = random.choice(CATEGORIAS)
        tipo = random.choice(tipos)
        cidade, estado = random.choice(CIDADES)

        nome = f"{random.choice(PREFIXOS)} {tipo} {random.choice(SUFIXOS)}"
        cnpj = gerar_cnpj(mascarado=random.random() < 0.5)
        endereco = f"{random.choice(RUAS)}, {random.randint(10, 999)}"
        abertura = date(random.randint(2000, 2024), random.randint(1, 12), random.randint(1, 28))
        funcs = random.randint(1, 80)
        email = f"contato@{nome.lower().replace(' ', '').replace('&', '')}.com.br"
        telefone = f"({random.randint(11, 99)}) {random.randint(3000, 9999)}-{random.randint(1000, 9999)}"

        registros.append({
            "business_id": f"BUS{i:04d}",
            "nome": nome,
            "cnpj": cnpj,
            "categoria": codigo,
            "setor": setor,
            "cidade": cidade,
            "estado": estado,
            "endereco": endereco,
            "data_abertura": abertura.isoformat(),
            "num_funcionarios": funcs,
            "email": email,
            "telefone": telefone,
        })

    df = pd.DataFrame(registros)

    # ---- Defeitos propositais (qualidade de dados) ----
    rng = random.Random()
    for _ in range(int(qtd * 0.02)):            # nomes em minúsculas
        df.loc[rng.randint(0, len(df) - 1), "nome"] = df.loc[rng.randint(0, len(df) - 1), "nome"].lower()
    for _ in range(int(qtd * 0.02)):            # CNPJ inválido
        linha = rng.randint(0, len(df) - 1)
        df.loc[linha, "cnpj"] = gerar_cnpj_invalido()
    for _ in range(int(qtd * 0.015)):           # CNPJ vazio
        df.loc[rng.randint(0, len(df) - 1), "cnpj"] = ""
    for _ in range(int(qtd * 0.02)):            # data de abertura em dd/mm/aaaa
        linha = rng.randint(0, len(df) - 1)
        df.loc[linha, "data_abertura"] = df.loc[linha, "data_abertura"][8:10] + "/" + df.loc[linha, "data_abertura"][5:7] + "/" + df.loc[linha, "data_abertura"][:4]
    for _ in range(int(qtd * 0.015)):           # endereço vazio
        df.loc[rng.randint(0, len(df) - 1), "endereco"] = ""
    for _ in range(3):                          # duplicatas exatas
        df = pd.concat([df, df.iloc[[rng.randint(0, len(df) - 1)]]], ignore_index=True)

    return df


# ---------------------------------------------------------------------------
# Geração de transações
# ---------------------------------------------------------------------------

def gerar_transacoes(businesses: pd.DataFrame, dias: int) -> pd.DataFrame:
    data_fim = date(2026, 6, 30)
    data_inicio = data_fim - timedelta(days=dias)

    rng = np.random.default_rng(42)
    transacoes: list[dict] = []
    total_ids = set(businesses["business_id"])
    base_ratings = {bus: min(5.0, max(3.0, rng.normal(4.2, 0.4))) for bus in total_ids}
    tamanhos = {bus: rng.uniform(0.4, 2.6) for bus in total_ids}

    for idx, row in businesses.iterrows():
        business_id = row["business_id"]
        tamanho = tamanhos[business_id]
        # Poisson com a média diária multiplicada pelos dias — evita negócios
        # sem nenhuma venda (erro comum: amostrar o Poisson antes de multiplicar)
        n_vendas = int(rng.poisson(1.6 * tamanho * dias))

        for j in range(n_vendas):
            # data com sazonalidade de mês (fim de ano) e fim de semana
            while True:
                mes = int(rng.choice(range(1, 13), p=[PESO_MES[m] / sum(PESO_MES.values()) for m in range(1, 13)]))
                anos_validos = [
                    y for y in range(data_inicio.year, data_fim.year + 1)
                    if data_inicio <= date(y, mes, 15) <= data_fim
                ]
                ano = int(rng.choice(anos_validos))
                dia_tentativa = date(ano, mes, int(rng.integers(1, 28)))
                if not (data_inicio <= dia_tentativa <= data_fim):
                    continue
                peso = PESO_DIA_SEMANA[dia_tentativa.weekday()]
                if rng.random() * max(PESO_DIA_SEMANA) <= peso:
                    break

            valor = float(rng.lognormal(mean=4.5 + 0.35 * tamanho, sigma=0.75))
            transacoes.append({
                "transaction_id": f"TXN{idx:04d}{j:06d}",
                "business_id": business_id,
                "data_venda": dia_tentativa.isoformat(),
                "valor": valor,
                "quantidade": int(rng.integers(1, 6)),
                "forma_pagamento": rng.choice([p for p, _ in FORMAS_PAGAMENTO], p=[w for _, w in FORMAS_PAGAMENTO]),
                "canal": rng.choice([c for c, _ in CANAIS], p=[w for _, w in CANAIS]),
                "avaliacao": round(min(5.0, max(1.0, base_ratings[business_id] + rng.normal(0, 0.6))), 1),
            })

    df = pd.DataFrame(transacoes)
    df = df.sort_values("data_venda").reset_index(drop=True)

    # ---- Defeitos propositais ----
    # Converte para texto/object antes: o pandas 3.x não permite inserir
    # strings em colunas numéricas (LossySetitemError)
    df = df.astype(object)
    rng2 = random.Random()
    n = len(df)
    for _ in range(int(n * 0.02)):                      # valores em formato "R$ 1.234,56"
        linha = rng2.randint(0, n - 1)
        df.loc[linha, "valor"] = f"R$ {_as_float(df.loc[linha, 'valor']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    for _ in range(int(n * 0.015)):                     # valores negativos
        linha = rng2.randint(0, n - 1)
        df.loc[linha, "valor"] = -abs(_as_float(df.loc[linha, "valor"]))
    for _ in range(int(n * 0.005)):                     # valor vazio
        df.loc[rng2.randint(0, n - 1), "valor"] = ""
    for _ in range(int(n * 0.015)):                     # datas em dd/mm/aaaa
        linha = rng2.randint(0, n - 1)
        df.loc[linha, "data_venda"] = df.loc[linha, "data_venda"][8:10] + "/" + df.loc[linha, "data_venda"][5:7] + "/" + df.loc[linha, "data_venda"][:4]
    for _ in range(int(n * 0.01)):                      # data vazia
        df.loc[rng2.randint(0, n - 1), "data_venda"] = ""
    for _ in range(int(n * 0.02)):                      # avaliação fora de 1-5
        df.loc[rng2.randint(0, n - 1), "avaliacao"] = rng2.choice([0, 7, 9, 10])
    for _ in range(int(n * 0.015)):                     # avaliação vazia
        df.loc[rng2.randint(0, n - 1), "avaliacao"] = ""
    for _ in range(int(n * 0.03)):                      # quantidade vazia
        df.loc[rng2.randint(0, n - 1), "quantidade"] = ""
    for _ in range(int(n * 0.005)):                     # transações órfãs (negócio inexistente)
        df.loc[rng2.randint(0, n - 1), "business_id"] = "BUS9999"
    for _ in range(5):                                  # duplicatas exatas
        df = pd.concat([df, df.iloc[[rng2.randint(0, len(df) - 1)]]], ignore_index=True)

    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dados sintéticos de negócios locais.")
    parser.add_argument("--businesses", type=int, default=120, help="Quantidade de negócios")
    parser.add_argument("--dias", type=int, default=1260, help="Dias de histórico de vendas")
    parser.add_argument("--seed", type=int, default=42, help="Semente de aleatoriedade")
    parser.add_argument("--saida", type=str, default=None, help="Pasta de saída (padrão: data/raw)")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    config.garantir_diretorios()
    saida = Path(args.saida) if args.saida else config.DATA_RAW_DIR
    saida.mkdir(parents=True, exist_ok=True)

    businesses = gerar_businesses(args.businesses)
    transacoes = gerar_transacoes(businesses, args.dias)

    businesses.to_csv(saida / "businesses.csv", index=False, encoding="utf-8")
    transacoes.to_csv(saida / "transactions.csv", index=False, encoding="utf-8")

    print("\n✅ Dados sintéticos gerados:")
    print(f"   • {saida / 'businesses.csv'}   → {len(businesses):,} negócios".replace(",", "."))
    print(f"   • {saida / 'transactions.csv'} → {len(transacoes):,} vendas".replace(",", "."))
    datas_validas = transacoes[transacoes["data_venda"].str.len() == 10]["data_venda"]
    print(f"   • Período: {datas_validas.min()} a {datas_validas.max()}")
    print("   ⚠️  Defeitos propositais injetados para o pipeline demonstrar limpeza de dados.\n")


if __name__ == "__main__":
    main()
