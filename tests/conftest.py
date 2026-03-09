"""Pytest fixtures for impact analysis schema tests (Phase 2): PG connection and test repo path."""

import os
from pathlib import Path

import pytest


def _get_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/neodev"
    )


def _get_test_repo_path() -> str:
    return os.environ.get("TEST_REPO_PATH", r"D:\PycharmProjects\codeAnalysis")


def _run_migration_if_needed(conn) -> None:
    """Apply all SQL migrations in docker/migrations (idempotent)."""
    migration_dir = Path(__file__).resolve().parent.parent / "docker" / "migrations"
    if not migration_dir.is_dir():
        return
    conn.rollback()
    for migration_path in sorted(migration_dir.glob("*.sql")):
        sql = migration_path.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            for stmt in sql.split(";"):
                stmt = stmt.strip()
                # Drop leading comment lines so "-- comment\nCREATE TABLE ..." is executed
                stmt = "\n".join(
                    line for line in stmt.split("\n") if not line.strip().startswith("--")
                ).strip()
                if stmt:
                    cur.execute(stmt)
    conn.commit()


@pytest.fixture(scope="session")
def db_connection():
    """Session-scoped PG connection; skips if PostgreSQL is not available. Applies migration if tables missing."""
    try:
        import psycopg2
        conn = psycopg2.connect(_get_database_url())
        conn.rollback()
        _run_migration_if_needed(conn)
        yield conn
        conn.close()
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.fixture
def pg_conn(db_connection):
    """Alias for db_connection; use for tests that need a connection."""
    yield db_connection


@pytest.fixture(scope="session")
def test_repo_path() -> str:
    """Path to Git repo used as projects.repo_path in insert-chain tests (default: codeAnalysis)."""
    return _get_test_repo_path()


@pytest.fixture
def client_with_db(pg_conn):
    """TestClient with get_db overridden to use test PG connection. Rolls back before yield for isolation."""
    from fastapi.testclient import TestClient

    from service.dependencies import get_db
    from service.main import app

    def override_get_db():
        yield pg_conn

    app.dependency_overrides[get_db] = override_get_db
    try:
        pg_conn.rollback()
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
