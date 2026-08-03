"""Mock API — simula a API de dados de negócios locais.

Serve os dados gerados (data/raw) via HTTP com paginação real, permitindo
demonstrar a ingestão via API no pipeline (scripts/extract.py --fonte api).

Endpoints:
    GET /health                    → status da API
    GET /api/v1/businesses         → lista de negócios (paginação)
    GET /api/v1/transactions       → lista de transações (paginação)

Uso:
    python api/mock_api.py              # porta 8000
    python api/mock_api.py --port 9000
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from etl import config  # noqa: E402

PAGINA = 5000  # registros por página


def _carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carrega os CSVs gerados em data/raw."""
    businesses = pd.read_csv(config.DATA_RAW_DIR / "businesses.csv", dtype=str)
    transacoes = pd.read_csv(config.DATA_RAW_DIR / "transactions.csv", dtype=str)
    return businesses, transacoes


class Handler(BaseHTTPRequestHandler):
    businesses: pd.DataFrame = pd.DataFrame()
    transacoes: pd.DataFrame = pd.DataFrame()

    def log_message(self, fmt, *args):  # noqa: A003
        sys.stdout.write(f"  📡 {self.address_string()} {fmt % args}\n")

    # ------------------------------------------------------------------
    def do_GET(self):  # noqa: N802
        caminho = urlparse(self.path)
        rota = caminho.path
        params = parse_qs(caminho.query)

        if rota == "/health":
            return self._responder({"status": "ok", "servico": "mock-api-negocios"})

        offset = int(params.get("offset", ["0"])[0])
        limite = min(int(params.get("limit", [str(PAGINA)])[0]), 10000)

        if rota == "/api/v1/businesses":
            return self._responder(self._paginar(self.businesses, offset, limite))
        if rota == "/api/v1/transactions":
            return self._responder(self._paginar(self.transacoes, offset, limite))

        self.send_error(404, f"Rota não encontrada: {rota}")

    # ------------------------------------------------------------------
    def _paginar(self, df: pd.DataFrame, offset: int, limite: int) -> list[dict]:
        pagina = df.iloc[offset: offset + limite]
        return json.loads(pagina.to_json(orient="records", force_ascii=False))

    def _responder(self, dados) -> None:
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(corpo)


def main() -> None:
    parser = argparse.ArgumentParser(description="Mock API de negócios locais.")
    parser.add_argument("--port", type=int, default=8000, help="Porta (padrão: 8000)")
    args = parser.parse_args()

    config.garantir_diretorios()
    Handler.businesses, Handler.transacoes = _carregar_dados()

    # 127.0.0.1 (IPv4) evita o problema do 'localhost' resolvendo para ::1 no Windows
    servidor = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("\n🚀 Mock API rodando em http://localhost:%d" % args.port)
    print(f"   • GET /api/v1/businesses   ({len(Handler.businesses):,} registros)".replace(",", "."))
    print(f"   • GET /api/v1/transactions ({len(Handler.transacoes):,} registros)".replace(",", "."))
    print("   • Ctrl+C para encerrar\n")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 API encerrada.")


if __name__ == "__main__":
    main()
