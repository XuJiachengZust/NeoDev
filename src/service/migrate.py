"""Database initialization entrypoint for local/API startup."""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg2

from service.dependencies import get_database_url

logger = logging.getLogger(__name__)

_INIT_SQL_PATHS = [
    Path("/app/docker/init.sql"),
    Path(__file__).resolve().parent.parent.parent / "docker" / "init.sql",
]
_INIT_LOCK_ID = 80430001


def _is_initialized(cur) -> bool:
    cur.execute(
        """
        SELECT to_regclass('public.branch_graphs') IS NOT NULL
           AND to_regclass('public.graph_refresh_runs') IS NOT NULL
           AND EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'doc_code_links'
                  AND column_name = 'code_locator_json'
           )
        """
    )
    return bool(cur.fetchone()[0])


def run_migrations() -> None:
    """Initialize the database from the single consolidated SQL file."""
    init_sql_path = next((path for path in _INIT_SQL_PATHS if path.is_file()), None)
    if init_sql_path is None:
        logger.warning("database init SQL not found")
        return

    try:
        conn = psycopg2.connect(get_database_url())
    except Exception as exc:
        logger.error("database initialization connection failed: %s", exc)
        return

    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(%s)", (_INIT_LOCK_ID,))
            if _is_initialized(cur):
                conn.commit()
                logger.info("database initialization already applied")
                return
            cur.execute(init_sql_path.read_text(encoding="utf-8-sig"))
        conn.commit()
        logger.info("database initialization SQL applied: %s", init_sql_path)
    except Exception as exc:
        conn.rollback()
        logger.error("database initialization failed: %s", exc)
    finally:
        conn.close()
