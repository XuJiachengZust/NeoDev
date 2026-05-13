from service import migrate


class _FakeCursor:
    def __init__(self):
        self.statements = []

    def execute(self, sql, params=None):
        self.statements.append((sql, params))


def test_runtime_upgrade_sql_backfills_version_scoped_document_metadata():
    cursor = _FakeCursor()

    migrate._run_upgrade_sql(cursor)

    sql = cursor.statements[0][0]
    assert "ALTER TABLE IF EXISTS doc_bindings" in sql
    assert "ADD COLUMN IF NOT EXISTS product_version_id" in sql
    assert "UPDATE documents AS d" in sql
    assert "DROP INDEX IF EXISTS uq_documents_doc_version" in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_doc_version" in sql
    assert "ON documents(doc_id, product_version_id);" in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_binding_path" in sql


def test_runtime_upgrade_sql_enforces_product_and_version_name_uniqueness_only():
    cursor = _FakeCursor()

    migrate._run_upgrade_sql(cursor)

    sql = cursor.statements[0][0]
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_products_name" in sql
    assert "ON products(name);" in sql
    assert "DROP INDEX IF EXISTS uq_projects_name" in sql
    assert "ON projects(name);" not in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_product_versions_product_name" in sql
    assert "ON product_versions(product_id, version_name);" in sql


def test_runtime_upgrade_sql_allows_branch_lookup_to_return_multiple_versions():
    cursor = _FakeCursor()

    migrate._run_upgrade_sql(cursor)

    sql = cursor.statements[0][0]
    assert "DROP INDEX IF EXISTS uq_pvb_project_branch" in sql
    assert "CREATE INDEX IF NOT EXISTS idx_product_version_branches_project_branch" in sql
    assert "ON product_version_branches(project_id, branch_name);" in sql
    assert "ALTER TABLE IF EXISTS doc_bindings" in sql
    assert "ALTER COLUMN product_version_id SET NOT NULL" in sql
    assert "uq_doc_bindings_active_product_legacy" not in sql
    assert "WHERE is_active = true AND product_version_id IS NULL" not in sql


def test_runtime_upgrade_sql_rejects_doc_source_reuse_across_versions():
    cursor = _FakeCursor()

    migrate._run_upgrade_sql(cursor)

    sql = cursor.statements[0][0]
    assert "ADD COLUMN IF NOT EXISTS git_source_key TEXT NOT NULL DEFAULT ''" in sql
    assert "UPDATE doc_bindings" in sql
    assert "lower(btrim(repo_url))" not in sql
    assert "WHEN btrim(repo_url) <> '' THEN" in sql
    assert "lower(split_part(btrim(repo_url), '://', 1))" in sql
    assert "lower(split_part(split_part(btrim(repo_url), '://', 2), '/', 1))" in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_bindings_active_git_source_key" in sql
    assert "ON doc_bindings(git_source_key, default_branch)" in sql
    assert "AND product_version_id IS NOT NULL" not in sql
