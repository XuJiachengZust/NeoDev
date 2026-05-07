from service.repositories import document_repository


class _Cursor:
    def __init__(self):
        self.sql = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.sql = sql
        self.params = params

    def fetchone(self):
        return {
            "id": 1,
            "doc_binding_id": 9,
            "product_version_id": self.params[1],
            "doc_id": self.params[2],
            "relative_path": self.params[3],
        }


class _Conn:
    def __init__(self):
        self.cursor_obj = _Cursor()

    def cursor(self, cursor_factory=None):
        return self.cursor_obj


def test_upsert_uses_version_scoped_conflict_target_when_version_is_present():
    conn = _Conn()

    document_repository.upsert(
        conn,
        doc_binding_id=9,
        product_version_id=4,
        doc_id="DOC-1",
        relative_path="docs/a.md",
    )

    assert "ON CONFLICT (doc_id, product_version_id)" in conn.cursor_obj.sql


def test_upsert_uses_binding_path_conflict_target_for_legacy_documents():
    conn = _Conn()

    document_repository.upsert(
        conn,
        doc_binding_id=9,
        product_version_id=None,
        doc_id="DOC-1",
        relative_path="docs/a.md",
    )

    assert "ON CONFLICT (doc_binding_id, relative_path)" in conn.cursor_obj.sql
