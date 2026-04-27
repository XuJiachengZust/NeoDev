"""Pytest fixtures for shared PG-backed tests."""

import os
import uuid
from pathlib import Path

import psycopg2
import pytest


ROOT = Path(__file__).resolve().parent.parent
MIGRATION_FILE = ROOT / "docker" / "migrations" / "018_cli_metadata_foundation.sql"


def _get_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/neodev"
    )


def _get_test_repo_path() -> str:
    return os.environ.get("TEST_REPO_PATH", r"D:\PycharmProjects\codeAnalysis")


def _run_all_migrations_if_needed(conn) -> None:
    migration_dir = ROOT / "docker" / "migrations"
    if not migration_dir.is_dir():
        return

    conn.rollback()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT to_regclass('public.projects'),
                   to_regclass('public.requirement_split_suggestions')
            """
        )
        projects_table, latest_table = cur.fetchone()

    if projects_table and latest_table:
        return

    for migration_path in sorted(migration_dir.glob("*.sql")):
        sql = migration_path.read_text(encoding="utf-8")
        with conn.cursor() as cur:
            normalized_sql = "\n".join(
                line for line in sql.splitlines() if not line.strip().startswith("--")
            ).strip()
            if not normalized_sql:
                continue
            # Keep PL/pgSQL blocks intact; naive ';' splitting breaks DO $$ ... $$; migrations.
            if "$$" in normalized_sql:
                cur.execute(normalized_sql)
                continue
            for stmt in normalized_sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
    conn.commit()


def _run_migration_if_needed(conn) -> None:
    if not MIGRATION_FILE.exists():
        pytest.skip(f"metadata migration file missing: {MIGRATION_FILE}")

    with conn.cursor() as cur:
        cur.execute(MIGRATION_FILE.read_text(encoding="utf-8"))
    conn.commit()


def _connect_postgres(skip_context: str):
    try:
        return psycopg2.connect(_get_database_url())
    except Exception as exc:
        pytest.skip(f"postgres not available for {skip_context}: {exc}")


def _create_isolated_metadata_context(prefix: str, skip_context: str) -> tuple[object, str]:
    conn = _connect_postgres(skip_context)
    schema_name = f"{prefix}_{uuid.uuid4().hex[:8]}"
    try:
        with conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
            cur.execute(f'SET search_path TO "{schema_name}", public')
        conn.commit()
        _run_migration_if_needed(conn)
        return conn, schema_name
    except Exception:
        conn.close()
        raise


@pytest.fixture(scope="session")
def db_connection():
    """Session-scoped PG connection for generic DB-backed tests."""
    conn = _connect_postgres("generic DB tests")
    try:
        conn.rollback()
        _run_all_migrations_if_needed(conn)
        yield conn
    finally:
        conn.close()


@pytest.fixture
def pg_conn(db_connection):
    """Fresh PG connection per test; the session connection only bootstraps migrations."""
    conn = _connect_postgres("PG-backed test")
    try:
        yield conn
    finally:
        if not conn.closed:
            conn.rollback()
        conn.close()


@pytest.fixture(scope="session")
def test_repo_path() -> str:
    """Path to Git repo used as projects.repo_path in insert-chain tests."""
    return _get_test_repo_path()


@pytest.fixture
def client_with_db(pg_conn):
    """TestClient with get_db overridden to use test PG connection."""
    from unittest.mock import AsyncMock, patch

    from fastapi.testclient import TestClient

    from service.dependencies import get_db
    from service.main import app

    def override_get_db():
        yield pg_conn

    app.dependency_overrides[get_db] = override_get_db
    try:
        pg_conn.rollback()
        with patch("service.checkpointer.init_checkpointer", new=AsyncMock(return_value=None)), patch(
            "service.checkpointer.close_checkpointer", new=AsyncMock(return_value=None)
        ):
            with TestClient(app) as c:
                yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="module")
def metadata_migration_context():
    conn, schema_name = _create_isolated_metadata_context(
        "tmp_metadata_migration", "metadata migration test"
    )
    try:
        yield {"conn": conn, "schema_name": schema_name}
    finally:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public")
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        conn.commit()
        conn.close()


@pytest.fixture(scope="module")
def metadata_migration_pg_conn(metadata_migration_context):
    yield metadata_migration_context["conn"]


@pytest.fixture(scope="module")
def metadata_migration_schema_name(metadata_migration_context):
    return metadata_migration_context["schema_name"]


@pytest.fixture(scope="module")
def metadata_public_pg_conn(metadata_migration_pg_conn):
    yield metadata_migration_pg_conn


@pytest.fixture(scope="module")
def metadata_repo_context():
    conn, schema_name = _create_isolated_metadata_context(
        "tmp_metadata_repo", "metadata repository test"
    )
    try:
        yield {"conn": conn, "schema_name": schema_name}
    finally:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute("SET search_path TO public")
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        conn.commit()
        conn.close()


@pytest.fixture()
def metadata_repo_pg_conn(metadata_repo_context):
    yield metadata_repo_context["conn"]


@pytest.fixture(scope="module")
def metadata_repo_schema_name(metadata_repo_context):
    return metadata_repo_context["schema_name"]


@pytest.fixture()
def metadata_db_case(metadata_repo_pg_conn, metadata_repo_schema_name):
    metadata_repo_pg_conn.rollback()
    with metadata_repo_pg_conn.cursor() as cur:
        cur.execute(f'SET search_path TO "{metadata_repo_schema_name}", public')
    metadata_repo_pg_conn.commit()
    try:
        yield metadata_repo_pg_conn
    finally:
        metadata_repo_pg_conn.rollback()
