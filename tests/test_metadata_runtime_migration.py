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


def test_runtime_upgrade_sql_enforces_name_lookup_uniqueness():
    cursor = _FakeCursor()

    migrate._run_upgrade_sql(cursor)

    sql = cursor.statements[0][0]
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_products_name" in sql
    assert "ON products(name);" in sql
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_projects_name" in sql
    assert "ON projects(name);" in sql


def test_runtime_upgrade_sql_enforces_branch_scope_uniqueness():
    cursor = _FakeCursor()

    migrate._run_upgrade_sql(cursor)

    sql = cursor.statements[0][0]
    assert "CREATE UNIQUE INDEX IF NOT EXISTS uq_pvb_project_branch" in sql
    assert "ON product_version_branches(project_id, branch_name);" in sql
    assert "ALTER TABLE IF EXISTS doc_bindings" in sql
    assert "ALTER COLUMN product_version_id SET NOT NULL" in sql
