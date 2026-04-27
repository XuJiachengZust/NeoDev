from service.cli.errors import CliError
from service.services import doc_change_service


def test_register_doc_change_generates_id_when_missing(monkeypatch):
    document = {"id": 17, "doc_id": "REQ-17"}
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
    )

    assert result["doc_change"]["document_id"] == 17
    assert result["doc_change"]["doc_change_id"].startswith("DC-REQ-17-")
    assert created_rows[0]["status"] == "pending_implementation"


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
