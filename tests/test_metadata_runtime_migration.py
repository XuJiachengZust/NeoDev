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
