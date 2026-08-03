"""Conexão com o banco de dados.

PostgreSQL é o banco principal (produção). Caso ele não esteja disponível
(Docker parado, por exemplo), o pipeline faz fallback automático para SQLite,
garantindo que a demonstração funcione em qualquer máquina.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from etl import config

logger = logging.getLogger("datapipeline.db")

_engine: Engine | None = None


def _criar_engine(url: str) -> Engine:
    """Cria um engine SQLAlchemy adequado ao dialeto informado."""
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False})

        # SQLite não habilita foreign keys por padrão
        @event.listens_for(engine, "connect")
        def _ativar_fk(conn_bruto, _record):  # noqa: ANN001
            cursor = conn_bruto.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine

    return create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 4},  # falha rápido se o Postgres estiver fora
    )


def conectar() -> Engine:
    """Retorna o engine ativo, testando PostgreSQL e caindo para SQLite se preciso."""
    global _engine

    if _engine is not None:
        return _engine

    config.garantir_diretorios()

    if config.DATABASE_URL.startswith("sqlite"):
        tentativas = [("sqlite (configurado)", config.DATABASE_URL)]
    elif config.DB_SOMENTE_POSTGRES:
        tentativas = [("postgresql (obrigatório)", config.DATABASE_URL)]
    else:
        tentativas = [
            ("postgresql", config.DATABASE_URL),
            ("sqlite (fallback)", config.SQLITE_PADRAO),
        ]

    for nome, url in tentativas:
        try:
            engine = _criar_engine(url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            destino = url.split("//")[-1].split("@")[-1]
            logger.info("✅ Banco de dados conectado: %s (%s)", nome, destino)
            _engine = engine
            return engine
        except Exception as exc:  # noqa: BLE001
            logger.warning("⚠️  Falha ao conectar em %s: %s", nome, exc)

    raise RuntimeError("❌ Nenhum banco de dados disponível.")


def vendor(engine: Engine) -> str:
    """Dialeto do banco em uso: 'postgresql' ou 'sqlite'."""
    return engine.dialect.name


def _dividir_statements(sql: str) -> list[str]:
    """Divide um arquivo SQL em statements, ignorando comentários e linhas vazias."""
    sem_comentarios = "\n".join(
        linha.split("--")[0] for linha in sql.splitlines() if not linha.strip().startswith("--")
    )
    sem_blocos = re.sub(r"/\*.*?\*/", "", sem_comentarios, flags=re.S)
    return [s.strip() for s in sem_blocos.split(";") if s.strip()]


def executar_arquivo_sql(engine: Engine, caminho: Path) -> None:
    """Executa um arquivo .sql no banco, statement por statement."""
    sql = caminho.read_text(encoding="utf-8")
    statements = _dividir_statements(sql)
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
    logger.info("📄 SQL executado: %s (%d statement(s))", caminho.name, len(statements))
