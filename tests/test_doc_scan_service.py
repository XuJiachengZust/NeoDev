import uuid
import shutil
from pathlib import Path

import service.repositories.doc_binding_repository as doc_binding_repository
import service.repositories.document_repository as document_repository
import service.repositories.document_scan_error_repository as scan_error_repository
from service.services import doc_scan_service


def _create_product(conn, code: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO products (name, code)
            VALUES (%s, %s)
            RETURNING id
            """,
            (f"doc-scan-product-{code}", code),
        )
        return cur.fetchone()[0]


def _write_doc(path: Path, front_matter: str, body: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front_matter}\n---\n\n{body}\n", encoding="utf-8")


def _make_doc_repo() -> Path:
    path = Path.cwd() / ".test-tmp" / f"doc-scan-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    return path


def test_doc_scan_registers_valid_controlled_documents(metadata_db_case):
    doc_repo = _make_doc_repo()
    try:
        _assert_doc_scan_registers_valid_controlled_documents(metadata_db_case, doc_repo)
    finally:
        shutil.rmtree(doc_repo, ignore_errors=True)


def _assert_doc_scan_registers_valid_controlled_documents(metadata_db_case, tmp_path):
    token = uuid.uuid4().hex[:8]
    product_code = f"DOCSCAN-{token}"
    product_id = _create_product(metadata_db_case, product_code)
    binding = doc_binding_repository.create(
        metadata_db_case,
        product_id=product_id,
        repo_path=str(tmp_path),
    )
    _write_doc(
        tmp_path / "prd" / "overview.md",
        f"""
doc_id: DOC-{token}
title: Product Overview
doc_type: prd
product_key: {product_code}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )
    _write_doc(
        tmp_path / "notes" / "ignored.md",
        f"""
doc_id: IGNORED-{token}
title: Ignored
doc_type: note
product_key: {product_code}
status: draft
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )

    result = doc_scan_service.scan_binding(metadata_db_case, binding["id"])

    assert result["registered_count"] == 1
    assert result["error_count"] == 0
    assert result["ignored_count"] == 1
    documents = document_repository.list_by_binding(metadata_db_case, binding["id"])
    assert len(documents) == 1
    assert documents[0]["doc_id"] == f"DOC-{token}"
    assert documents[0]["relative_path"] == "prd/overview.md"
    assert documents[0]["doc_type"] == "prd"
    assert documents[0]["title"] == "Product Overview"
    assert documents[0]["front_matter_json"]["product_key"] == product_code
    assert documents[0]["relations_json"] == {"target": [f"PROJECT-{token}"]}


def test_doc_scan_records_invalid_front_matter_without_registering_doc(metadata_db_case):
    doc_repo = _make_doc_repo()
    try:
        _assert_doc_scan_records_invalid_front_matter_without_registering_doc(
            metadata_db_case,
            doc_repo,
        )
    finally:
        shutil.rmtree(doc_repo, ignore_errors=True)


def _assert_doc_scan_records_invalid_front_matter_without_registering_doc(
    metadata_db_case,
    tmp_path,
):
    token = uuid.uuid4().hex[:8]
    product_code = f"DOCBAD-{token}"
    product_id = _create_product(metadata_db_case, product_code)
    binding = doc_binding_repository.create(
        metadata_db_case,
        product_id=product_id,
        repo_path=str(tmp_path),
    )
    _write_doc(
        tmp_path / "tech-design" / "missing-relations.md",
        f"""
doc_id: DOC-BAD-{token}
title: Missing Relations
doc_type: tech-design
product_key: {product_code}
status: draft
relations:
  related:
    - DOC-OTHER
""".strip(),
    )

    result = doc_scan_service.scan_binding(metadata_db_case, binding["id"])

    assert result["registered_count"] == 0
    assert result["error_count"] == 1
    assert document_repository.list_by_binding(metadata_db_case, binding["id"]) == []
    errors = scan_error_repository.list_by_binding(metadata_db_case, binding["id"])
    assert len(errors) == 1
    assert errors[0]["relative_path"] == "tech-design/missing-relations.md"
    assert errors[0]["error_code"] == "invalid_front_matter"
    assert "relations.target" in errors[0]["error_message"]


def test_doc_scan_rejects_invalid_doc_type_and_status(metadata_db_case):
    doc_repo = _make_doc_repo()
    try:
        _assert_doc_scan_rejects_invalid_doc_type_and_status(metadata_db_case, doc_repo)
    finally:
        shutil.rmtree(doc_repo, ignore_errors=True)


def _assert_doc_scan_rejects_invalid_doc_type_and_status(metadata_db_case, tmp_path):
    token = uuid.uuid4().hex[:8]
    product_code = f"DOCTYPE-{token}"
    product_id = _create_product(metadata_db_case, product_code)
    binding = doc_binding_repository.create(
        metadata_db_case,
        product_id=product_id,
        repo_path=str(tmp_path),
    )
    _write_doc(
        tmp_path / "prd" / "invalid-type.md",
        f"""
doc_id: DOC-TYPE-{token}
title: Invalid Type
doc_type: note
product_key: {product_code}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )
    _write_doc(
        tmp_path / "tech-design" / "invalid-status.md",
        f"""
doc_id: DOC-STATUS-{token}
title: Invalid Status
doc_type: tech-design
product_key: {product_code}
status: planned
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )

    result = doc_scan_service.scan_binding(metadata_db_case, binding["id"])

    assert result["registered_count"] == 0
    assert result["error_count"] == 2
    errors = scan_error_repository.list_by_binding(metadata_db_case, binding["id"])
    assert {error["details_json"]["field"] for error in errors} == {
        "doc_type",
        "status",
    }


def test_doc_scan_updates_existing_document_on_rescan(metadata_db_case):
    doc_repo = _make_doc_repo()
    try:
        _assert_doc_scan_updates_existing_document_on_rescan(metadata_db_case, doc_repo)
    finally:
        shutil.rmtree(doc_repo, ignore_errors=True)


def _assert_doc_scan_updates_existing_document_on_rescan(metadata_db_case, tmp_path):
    token = uuid.uuid4().hex[:8]
    product_code = f"DOCUP-{token}"
    product_id = _create_product(metadata_db_case, product_code)
    binding = doc_binding_repository.create(
        metadata_db_case,
        product_id=product_id,
        repo_path=str(tmp_path),
    )
    doc_path = tmp_path / "prototype" / "flow.md"
    _write_doc(
        doc_path,
        f"""
doc_id: DOC-UP-{token}
title: First Title
doc_type: prototype
product_key: {product_code}
status: draft
relations:
  target:
    - USER-FLOW
""".strip(),
    )
    first = doc_scan_service.scan_binding(metadata_db_case, binding["id"])
    assert first["registered_count"] == 1

    _write_doc(
        doc_path,
        f"""
doc_id: DOC-UP-{token}
title: Updated Title
doc_type: prototype
product_key: {product_code}
status: active
relations:
  target:
    - USER-FLOW
    - API-FLOW
""".strip(),
    )
    second = doc_scan_service.scan_binding(metadata_db_case, binding["id"])

    documents = document_repository.list_by_binding(metadata_db_case, binding["id"])
    assert second["registered_count"] == 1
    assert len(documents) == 1
    assert documents[0]["title"] == "Updated Title"
    assert documents[0]["status"] == "active"
    assert documents[0]["relations_json"] == {"target": ["USER-FLOW", "API-FLOW"]}
