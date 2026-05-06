from service.cli.errors import CliError
from service.services import doc_change_service


def test_register_doc_change_requires_document_commit_when_id_missing(monkeypatch):
    document = {"id": 17, "doc_id": "REQ-17"}

    monkeypatch.setattr(
        doc_change_service.document_repository,
        "find_by_id",
        lambda conn, document_id: document if document_id == 17 else None,
    )

    try:
        doc_change_service.register_doc_change(
            object(),
            document_id=17,
            doc_change_id=None,
        )
    except CliError as exc:
        assert exc.category == "invalid_scope"
        assert exc.message == "document commit is required for DocChange-ID"
    else:
        raise AssertionError("expected CliError")


def test_register_doc_change_defaults_to_document_commit(monkeypatch):
    commit_hash = "b" * 40
    document = {"id": 17, "doc_id": "REQ-17", "last_seen_commit": commit_hash}
    created_rows = []

    monkeypatch.setattr(
        doc_change_service.document_repository,
        "find_by_id",
        lambda conn, document_id: document if document_id == 17 else None,
    )

    def fake_create(conn, **kwargs):
        created_rows.append(kwargs)
        return {"id": 31, **kwargs}

    monkeypatch.setattr(doc_change_service.doc_change_repository, "create", fake_create)

    result = doc_change_service.register_doc_change(
        object(),
        document_id=17,
        doc_change_id=None,
        source_commit=None,
    )

    assert result["doc_change"]["doc_change_id"] == commit_hash
    assert result["doc_change"]["source_commit"] == commit_hash
    assert created_rows[0]["doc_change_id"] == commit_hash
    assert created_rows[0]["source_commit"] == commit_hash


def test_register_doc_change_rejects_non_commit_doc_change_id(monkeypatch):
    document = {"id": 17, "doc_id": "REQ-17", "last_seen_commit": "b" * 40}

    monkeypatch.setattr(
        doc_change_service.document_repository,
        "find_by_id",
        lambda conn, document_id: document if document_id == 17 else None,
    )

    try:
        doc_change_service.register_doc_change(
            object(),
            document_id=17,
            doc_change_id="DC-REQ-17",
        )
    except CliError as exc:
        assert exc.category == "invalid_argument"
        assert exc.message == "DocChange-ID must be a 40-character document commit hash"
    else:
        raise AssertionError("expected CliError")


def test_show_doc_change_returns_document(monkeypatch):
    change = {"id": 9, "document_id": 17, "doc_change_id": "DC-17"}
    document = {"id": 17, "doc_id": "REQ-17"}

    monkeypatch.setattr(
        doc_change_service.doc_change_repository,
        "find_by_doc_change_id",
        lambda conn, doc_change_id: change if doc_change_id == "DC-17" else None,
    )
    monkeypatch.setattr(
        doc_change_service.document_repository,
        "find_by_id",
        lambda conn, document_id: document if document_id == 17 else None,
    )

    result = doc_change_service.show_doc_change(object(), doc_change_id="DC-17")

    assert result == {"doc_change": change, "document": document}


def test_register_doc_change_rejects_missing_document(monkeypatch):
    monkeypatch.setattr(
        doc_change_service.document_repository,
        "find_by_id",
        lambda conn, document_id: None,
    )

    try:
        doc_change_service.register_doc_change(
            object(),
            document_id=404,
            doc_change_id="DC-MISSING",
        )
    except CliError as exc:
        assert exc.category == "not_found"
        assert exc.message == "document not found"
    else:
        raise AssertionError("expected CliError")
