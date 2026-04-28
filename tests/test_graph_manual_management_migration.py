from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MIGRATION_FILE = ROOT / "docker" / "migrations" / "020_graph_manual_management.sql"
DOCKERFILE_POSTGRES = ROOT / "docker" / "Dockerfile.postgres"


def test_graph_manual_management_migration_file_is_registered():
    assert MIGRATION_FILE.exists(), f"migration file missing: {MIGRATION_FILE}"
    sql = MIGRATION_FILE.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS graph_node_types" in sql
    assert "CREATE TABLE IF NOT EXISTS graph_relation_types" in sql
    assert "CREATE TABLE IF NOT EXISTS graph_nodes" in sql
    assert "CREATE TABLE IF NOT EXISTS graph_edges" in sql
    assert "chk_graph_edges_relation_owner" in sql
    dockerfile = DOCKERFILE_POSTGRES.read_text(encoding="utf-8")
    assert "020_graph_manual_management.sql" in dockerfile


def _apply_migration(conn):
    assert MIGRATION_FILE.exists(), f"migration file missing: {MIGRATION_FILE}"
    with conn.cursor() as cur:
        cur.execute(MIGRATION_FILE.read_text(encoding="utf-8"))
    conn.commit()


def test_graph_manual_management_tables_exist(
    metadata_migration_pg_conn,
    metadata_migration_schema_name,
):
    _apply_migration(metadata_migration_pg_conn)

    with metadata_migration_pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT to_regclass(%s) IS NOT NULL,
                   to_regclass(%s) IS NOT NULL,
                   to_regclass(%s) IS NOT NULL,
                   to_regclass(%s) IS NOT NULL
            """,
            (
                f"{metadata_migration_schema_name}.graph_node_types",
                f"{metadata_migration_schema_name}.graph_relation_types",
                f"{metadata_migration_schema_name}.graph_nodes",
                f"{metadata_migration_schema_name}.graph_edges",
            ),
        )
        row = cur.fetchone()

    assert row == (True, True, True, True)


def test_graph_manual_management_columns_and_constraints_exist(
    metadata_migration_pg_conn,
    metadata_migration_schema_name,
):
    _apply_migration(metadata_migration_pg_conn)

    with metadata_migration_pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name IN (
                'graph_node_types',
                'graph_relation_types',
                'graph_nodes',
                'graph_edges'
              )
            """,
            (metadata_migration_schema_name,),
        )
        table_columns: dict[str, set[str]] = {}
        for table_name, column_name in cur.fetchall():
            table_columns.setdefault(table_name, set()).add(column_name)

        cur.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = %s
              AND tablename IN (
                'graph_node_types',
                'graph_relation_types',
                'graph_nodes',
                'graph_edges'
              )
            """,
            (metadata_migration_schema_name,),
        )
        indexes = {name: definition for name, definition in cur.fetchall()}

        cur.execute(
            """
            SELECT c.conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint AS c
            JOIN pg_class AS t ON t.oid = c.conrelid
            JOIN pg_namespace AS n ON n.oid = t.relnamespace
            WHERE n.nspname = %s
              AND c.conname IN (
                'chk_graph_node_types_status',
                'chk_graph_relation_types_status',
                'chk_graph_nodes_status',
                'chk_graph_edges_status',
                'chk_graph_edges_relation_owner'
              )
            """,
            (metadata_migration_schema_name,),
        )
        constraints = {name: definition for name, definition in cur.fetchall()}

    assert {
        "project_id",
        "type_key",
        "name",
        "description",
        "status",
    }.issubset(table_columns["graph_node_types"])
    assert {
        "project_id",
        "type_key",
        "name",
        "allowed_from_types",
        "allowed_to_types",
        "cross_project_allowed",
        "status",
    }.issubset(table_columns["graph_relation_types"])
    assert {
        "project_id",
        "node_id",
        "type_key",
        "name",
        "properties",
        "source",
        "repo_id",
        "file_path",
        "content_hash",
        "status",
    }.issubset(table_columns["graph_nodes"])
    assert {
        "project_id",
        "edge_id",
        "from_node_id",
        "to_node_id",
        "from_project_id",
        "to_project_id",
        "type_key",
        "properties",
        "status",
    }.issubset(table_columns["graph_edges"])

    assert "uq_graph_node_types_project_key" in indexes
    assert "(project_id, type_key)" in indexes["uq_graph_node_types_project_key"]
    assert "uq_graph_relation_types_project_key" in indexes
    assert "(project_id, type_key)" in indexes["uq_graph_relation_types_project_key"]
    assert "uq_graph_nodes_project_node_id" in indexes
    assert "(project_id, node_id)" in indexes["uq_graph_nodes_project_node_id"]
    assert "uq_graph_edges_project_edge_id" in indexes
    assert "(project_id, edge_id)" in indexes["uq_graph_edges_project_edge_id"]
    assert "idx_graph_edges_from_node" in indexes
    assert "idx_graph_edges_to_node" in indexes

    assert set(constraints) == {
        "chk_graph_node_types_status",
        "chk_graph_relation_types_status",
        "chk_graph_nodes_status",
        "chk_graph_edges_status",
        "chk_graph_edges_relation_owner",
    }
