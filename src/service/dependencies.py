"""FastAPI dependencies: PG connection for Phase 3 impact analysis API."""

import os
from collections.abc import Generator

import psycopg2
from psycopg2.extensions import connection as PgConnection


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
