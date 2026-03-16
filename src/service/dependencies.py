"""FastAPI dependencies: PG connection for Phase 3 impact analysis API."""

import os
from collections.abc import Generator

import psycopg2
from psycopg2.extensions import connection as PgConnection

from service.storage import RequirementDocStorage


def get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/neodev",
    )


def get_db() -> Generator[PgConnection, None, None]:
    """Yield a PG connection; commit on success, rollback on error. Caller must not persist connection."""
    conn = psycopg2.connect(get_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_requirement_doc_storage() -> RequirementDocStorage:
    """返回需求文档文件存储实例（使用环境变量 REQUIREMENT_DOCS_ROOT）。"""
    return RequirementDocStorage()
