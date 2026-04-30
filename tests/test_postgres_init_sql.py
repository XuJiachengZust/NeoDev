from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INIT_SQL = ROOT / "docker" / "init.sql"
DOCKERFILE_POSTGRES = ROOT / "docker" / "Dockerfile.postgres"
MIGRATION_DIR = ROOT / "docker" / "migrations"


def test_postgres_image_uses_single_init_sql():
    assert INIT_SQL.exists(), f"init SQL missing: {INIT_SQL}"
    dockerfile = DOCKERFILE_POSTGRES.read_text(encoding="utf-8")

    assert "docker/init.sql" in dockerfile
    assert "docker/migrations/" not in dockerfile


def test_legacy_migration_sql_files_are_removed():
    assert not list(MIGRATION_DIR.glob("*.sql"))


def test_init_sql_contains_current_project_branch_graph_tables():
    sql = INIT_SQL.read_text(encoding="utf-8")

    for table_name in [
        "branch_graphs",
        "graph_refresh_runs",
        "graph_operation_logs",
        "doc_code_links",
    ]:
        assert f"CREATE TABLE IF NOT EXISTS {table_name}" in sql

    assert "CREATE TABLE IF NOT EXISTS code_facts" not in sql
    assert "CREATE TABLE code_facts" not in sql
    assert "CREATE TABLE IF NOT EXISTS branch_snapshot_facts" not in sql
    assert "CREATE TABLE branch_snapshot_facts" not in sql
    assert "CREATE TABLE IF NOT EXISTS branch_snapshots" not in sql
    assert "CREATE TABLE branch_snapshots" not in sql
