import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIGRATION_FILE = ROOT / "docker" / "migrations" / "018_cli_metadata_foundation.sql"
REQUIRED_COLUMNS = {
    "doc_bindings": {
        "product_id",
        "repo_path",
        "repo_url",
        "default_branch",
        "is_active",
    },
    "documents": {
        "doc_binding_id",
        "doc_id",
        "relative_path",
        "doc_type",
        "front_matter_json",
        "relations_json",
        "status",
        "last_seen_commit",
        "last_scanned_at",
        "title",
    },
    "doc_changes": {
        "document_id",
        "doc_change_id",
        "source_commit",
        "summary",
        "details_json",
        "created_by",
        "implemented_at",
        "status",
    },
    "code_change_links": {
        "doc_change_id",
        "project_id",
        "branch",
        "commit_sha",
        "commit_message",
    },
    "dangerous_commit_records": {
        "project_id",
        "branch",
        "commit_sha",
        "status",
        "risk_level",
        "reason",
        "resolved_by",
        "resolved_at",
        "extra_json",
    },
}
EXPECTED_DEFAULT_TOKENS = {
    "doc_bindings": {
        "repo_path": ["''"],
        "repo_url": ["''"],
        "default_branch": ["'main'"],
        "is_active": ["true"],
    },
    "documents": {
        "doc_type": ["'markdown'"],
        "front_matter_json": ["{}", "jsonb"],
        "relations_json": ["{}", "jsonb"],
        "status": ["'active'"],
    },
    "doc_changes": {
        "details_json": ["{}", "jsonb"],
    },
    "dangerous_commit_records": {
        "risk_level": ["'medium'"],
        "extra_json": ["{}", "jsonb"],
    },
}


def test_metadata_migration_runs_outside_public_schema(metadata_migration_pg_conn, metadata_migration_schema_name):
    with metadata_migration_pg_conn.cursor() as cur:
        cur.execute("SELECT current_schema()")
        current_schema = cur.fetchone()[0]

    assert metadata_migration_schema_name != "public"
    assert current_schema == metadata_migration_schema_name


def test_cli_metadata_tables_exist(metadata_migration_pg_conn, metadata_migration_schema_name):
    metadata_migration_pg_conn.rollback()
    with metadata_migration_pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT to_regclass(%s) IS NOT NULL,
                   to_regclass(%s) IS NOT NULL,
                   to_regclass(%s) IS NOT NULL,
                   to_regclass(%s) IS NOT NULL,
                   to_regclass(%s) IS NOT NULL
            """,
            (
                f"{metadata_migration_schema_name}.doc_bindings",
                f"{metadata_migration_schema_name}.documents",
                f"{metadata_migration_schema_name}.doc_changes",
                f"{metadata_migration_schema_name}.code_change_links",
                f"{metadata_migration_schema_name}.dangerous_commit_records",
            ),
        )
        row = cur.fetchone()
    assert row == (True, True, True, True, True)


def test_doc_changes_has_unique_doc_change_id(metadata_migration_pg_conn, metadata_migration_schema_name):
    with metadata_migration_pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = %s
              AND tablename = 'doc_changes'
            """,
            (metadata_migration_schema_name,),
        )
        index_map = {name: definition for name, definition in cur.fetchall()}

    assert "uq_doc_changes_doc_change_id" in index_map
    assert "CREATE UNIQUE INDEX" in index_map["uq_doc_changes_doc_change_id"]
    assert "(doc_change_id)" in index_map["uq_doc_changes_doc_change_id"]


def _get_column_defaults(conn, schema_name, table_name, column_names):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, column_default
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
              AND column_name = ANY(%s)
            """,
            (schema_name, table_name, list(column_names)),
        )
        return {column_name: column_default for column_name, column_default in cur.fetchall()}


def _assert_expected_defaults(conn, schema_name):
    for table_name, column_tokens in EXPECTED_DEFAULT_TOKENS.items():
        defaults = _get_column_defaults(conn, schema_name, table_name, column_tokens.keys())
        assert set(defaults) == set(column_tokens)
        for column_name, tokens in column_tokens.items():
            default_expr = defaults[column_name]
            assert default_expr is not None
            default_expr = default_expr.lower()
            for token in tokens:
                assert token.lower() in default_expr


def test_required_columns_exist(metadata_migration_pg_conn, metadata_migration_schema_name):
    with metadata_migration_pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name IN (
                'doc_bindings',
                'documents',
                'doc_changes',
                'code_change_links',
                'dangerous_commit_records'
              )
            """,
            (metadata_migration_schema_name,),
        )
        table_columns = {}
        for table_name, column_name in cur.fetchall():
            table_columns.setdefault(table_name, set()).add(column_name)

    for table_name, expected in REQUIRED_COLUMNS.items():
        assert table_name in table_columns
        assert expected.issubset(table_columns[table_name])


def test_defaults_are_defined_on_core_tables(metadata_migration_pg_conn, metadata_migration_schema_name):
    _assert_expected_defaults(metadata_migration_pg_conn, metadata_migration_schema_name)


def test_metadata_key_indexes_and_constraints_exist(metadata_migration_pg_conn, metadata_migration_schema_name):
    with metadata_migration_pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = %s
              AND tablename IN (
                'doc_bindings',
                'documents',
                'doc_changes',
                'code_change_links',
                'dangerous_commit_records'
              )
            """,
            (metadata_migration_schema_name,),
        )
        index_map = {name: definition for name, definition in cur.fetchall()}

        cur.execute(
            """
            SELECT c.conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint AS c
            JOIN pg_class AS t ON t.oid = c.conrelid
            JOIN pg_namespace AS n ON n.oid = t.relnamespace
            WHERE n.nspname = %s
              AND c.conname IN (
                'chk_doc_changes_status',
                'chk_dangerous_commit_records_status'
            )
            """,
            (metadata_migration_schema_name,),
        )
        constraints = {name: definition for name, definition in cur.fetchall()}

    assert "uq_doc_bindings_active_product" in index_map
    assert "CREATE UNIQUE INDEX" in index_map["uq_doc_bindings_active_product"]
    assert "(product_id)" in index_map["uq_doc_bindings_active_product"]
    assert "WHERE (is_active = true)" in index_map["uq_doc_bindings_active_product"]

    assert "uq_documents_doc_id" in index_map
    assert "CREATE UNIQUE INDEX" in index_map["uq_documents_doc_id"]
    assert "(doc_id)" in index_map["uq_documents_doc_id"]
    assert "uq_documents_binding_path" in index_map
    assert "CREATE UNIQUE INDEX" in index_map["uq_documents_binding_path"]
    assert "(doc_binding_id, relative_path)" in index_map["uq_documents_binding_path"]
    assert "uq_doc_changes_doc_change_id" in index_map
    assert "CREATE UNIQUE INDEX" in index_map["uq_doc_changes_doc_change_id"]
    assert "(doc_change_id)" in index_map["uq_doc_changes_doc_change_id"]
    assert "idx_doc_bindings_product_id" in index_map
    assert "(product_id)" in index_map["idx_doc_bindings_product_id"]
    assert "idx_doc_changes_document_id" in index_map
    assert "(document_id)" in index_map["idx_doc_changes_document_id"]
    assert "idx_code_change_links_project_branch_sha" in index_map
    assert "(project_id, branch, commit_sha)" in index_map["idx_code_change_links_project_branch_sha"]
    assert "idx_code_change_links_doc_change_id" in index_map
    assert "(doc_change_id)" in index_map["idx_code_change_links_doc_change_id"]
    assert "idx_dangerous_commit_records_project_status_created" in index_map
    assert "(project_id, status, created_at)" in index_map[
        "idx_dangerous_commit_records_project_status_created"
    ]
    assert "idx_dangerous_commit_records_commit_sha" in index_map
    assert "(commit_sha)" in index_map["idx_dangerous_commit_records_commit_sha"]

    assert "chk_doc_changes_status" in constraints
    doc_change_statuses = set(re.findall(r"'([^']+)'", constraints["chk_doc_changes_status"]))
    assert doc_change_statuses == {
        "pending_implementation",
        "in_implementation",
        "implemented",
    }

    assert "chk_dangerous_commit_records_status" in constraints
    dangerous_statuses = set(
        re.findall(r"'([^']+)'", constraints["chk_dangerous_commit_records_status"])
    )
    assert dangerous_statuses == {"open", "resolved"}


def test_metadata_migration_is_idempotent(
    metadata_migration_pg_conn, metadata_migration_schema_name
):
    sql = MIGRATION_FILE.read_text(encoding="utf-8")
    with metadata_migration_pg_conn.cursor() as cur:
        cur.execute(sql)
    metadata_migration_pg_conn.commit()

    test_cli_metadata_tables_exist(metadata_migration_pg_conn, metadata_migration_schema_name)
    test_required_columns_exist(metadata_migration_pg_conn, metadata_migration_schema_name)
    test_defaults_are_defined_on_core_tables(
        metadata_migration_pg_conn, metadata_migration_schema_name
    )
    test_metadata_key_indexes_and_constraints_exist(
        metadata_migration_pg_conn, metadata_migration_schema_name
    )


def test_metadata_migration_backfills_missing_columns_on_existing_tables(metadata_migration_pg_conn):
    schema_name = f"tmp_cli_metadata_{uuid.uuid4().hex[:8]}"
    sql = MIGRATION_FILE.read_text(encoding="utf-8")
    try:
        with metadata_migration_pg_conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
            cur.execute(
                f"""
                CREATE TABLE "{schema_name}".doc_bindings (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
                    repo_path TEXT NOT NULL,
                    repo_url TEXT NOT NULL,
                    default_branch VARCHAR(255) NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
            cur.execute(
                f"""
                CREATE TABLE "{schema_name}".documents (
                    id SERIAL PRIMARY KEY,
                    doc_binding_id INTEGER NOT NULL REFERENCES "{schema_name}".doc_bindings(id) ON DELETE CASCADE,
                    doc_id VARCHAR(128) NOT NULL,
                    relative_path TEXT NOT NULL,
                    doc_type VARCHAR(64) NOT NULL,
                    front_matter_json JSONB NOT NULL,
                    relations_json JSONB NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    last_seen_commit VARCHAR(40),
                    last_scanned_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
            cur.execute(
                f"""
                CREATE TABLE "{schema_name}".doc_changes (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES "{schema_name}".documents(id) ON DELETE CASCADE,
                    doc_change_id VARCHAR(128) NOT NULL,
                    details_json JSONB NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
            cur.execute(
                f"""
                CREATE TABLE "{schema_name}".code_change_links (
                    id SERIAL PRIMARY KEY,
                    doc_change_id INTEGER NOT NULL REFERENCES "{schema_name}".doc_changes(id) ON DELETE CASCADE,
                    project_id INTEGER NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
                    branch VARCHAR(255) NOT NULL,
                    commit_sha VARCHAR(40) NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
            cur.execute(
                f"""
                CREATE TABLE "{schema_name}".dangerous_commit_records (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
                    branch VARCHAR(255) NOT NULL,
                    commit_sha VARCHAR(40) NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'open',
                    risk_level VARCHAR(32) NOT NULL,
                    extra_json JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
                """
            )
            cur.execute(f'SET LOCAL search_path TO "{schema_name}", public')
            cur.execute(sql)
        metadata_migration_pg_conn.commit()

        with metadata_migration_pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name IN (
                    'doc_bindings',
                    'documents',
                    'doc_changes',
                    'code_change_links',
                    'dangerous_commit_records'
                  )
                """,
                (schema_name,),
            )
            table_columns = {}
            for table_name, column_name in cur.fetchall():
                table_columns.setdefault(table_name, set()).add(column_name)

            assert "is_active" in table_columns["doc_bindings"]
        assert "title" in table_columns["documents"]
        assert "reason" in table_columns["dangerous_commit_records"]
        for table_name, expected in REQUIRED_COLUMNS.items():
            assert table_name in table_columns
            assert expected.issubset(table_columns[table_name])

        _assert_expected_defaults(metadata_migration_pg_conn, schema_name)
    finally:
        metadata_migration_pg_conn.rollback()
        with metadata_migration_pg_conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        metadata_migration_pg_conn.commit()
