from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_code_fact_rebuild_migration_drops_obsolete_storage_tables():
    sql = (
        ROOT / "docker" / "migrations" / "021_code_fact_snapshot_rebuild.sql"
    ).read_text(encoding="utf-8")

    obsolete_tables = {
        "branch_snapshot_entries",
        "versions",
        "commits",
        "requirement_commits",
        "impact_analysis_commits",
        "requirements",
        "impact_analyses",
        "version_feature_summaries",
        "product_requirement_commits",
        "product_bug_commits",
        "product_requirements",
        "product_bugs",
        "requirement_split_suggestions",
        "requirement_doc_meta",
    }
    for table_name in obsolete_tables:
        assert f"DROP TABLE IF EXISTS {table_name} CASCADE;" in sql


def test_code_fact_rebuild_migration_keeps_mvp_document_and_git_tables():
    sql = (
        ROOT / "docker" / "migrations" / "021_code_fact_snapshot_rebuild.sql"
    ).read_text(encoding="utf-8")

    mvp_tables = {
        "doc_bindings",
        "documents",
        "document_chunks",
        "document_scan_errors",
        "doc_changes",
        "code_change_links",
        "dangerous_commit_records",
    }
    for table_name in mvp_tables:
        assert f"DROP TABLE IF EXISTS {table_name} CASCADE;" not in sql


def test_code_fact_rebuild_migration_uses_text_for_long_code_identifiers():
    sql = (
        ROOT / "docker" / "migrations" / "021_code_fact_snapshot_rebuild.sql"
    ).read_text(encoding="utf-8")

    expected_columns = [
        "fact_id         TEXT NOT NULL",
        "symbol_key      TEXT NOT NULL",
        "parent_fact_id  TEXT",
        "fact_id     TEXT NOT NULL",
        "symbol_key           TEXT NOT NULL",
        "resolved_fact_id     TEXT",
    ]
    for column_definition in expected_columns:
        assert column_definition in sql


def test_code_fact_identifier_widening_migration_exists():
    sql = (
        ROOT / "docker" / "migrations" / "022_widen_code_fact_identifiers.sql"
    ).read_text(encoding="utf-8")

    for statement in [
        "ALTER TABLE IF EXISTS code_facts ALTER COLUMN fact_id TYPE TEXT",
        "ALTER TABLE IF EXISTS code_facts ALTER COLUMN symbol_key TYPE TEXT",
        "ALTER TABLE IF EXISTS code_facts ALTER COLUMN parent_fact_id TYPE TEXT",
        "ALTER TABLE IF EXISTS branch_snapshot_facts ALTER COLUMN fact_id TYPE TEXT",
        "ALTER TABLE IF EXISTS doc_code_links ALTER COLUMN symbol_key TYPE TEXT",
        "ALTER TABLE IF EXISTS doc_code_links ALTER COLUMN resolved_fact_id TYPE TEXT",
    ]:
        assert statement in sql


def test_project_api_does_not_register_obsolete_version_commit_routers():
    source = (ROOT / "src" / "service" / "routers" / "api.py").read_text(
        encoding="utf-8"
    )

    assert "from service.routers import commits" not in source
    assert "from service.routers import versions" not in source
    assert "router.include_router(commits.router" not in source
    assert "router.include_router(versions.router" not in source
