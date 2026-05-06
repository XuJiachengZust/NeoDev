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


def _write_doc_crlf(path: Path, front_matter: str, body: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\r\n{front_matter}\r\n---\r\n\r\n{body}\r\n", encoding="utf-8")


def _obsidian_properties(title: str) -> str:
    return f"""
aliases:
  - {title}
tags:
  - neodev/docs
created: 2026-04-27
updated: 2026-04-27
related:
  - "[[PROJECT-REF]]"
""".strip()


def _make_doc_repo() -> Path:
    path = Path.cwd() / ".test-tmp" / f"doc-scan-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    return path


def test_doc_scan_registers_valid_markdown_across_docs_root(metadata_db_case):
    doc_repo = _make_doc_repo()
    try:
        _assert_doc_scan_registers_valid_markdown_across_docs_root(metadata_db_case, doc_repo)
    finally:
        shutil.rmtree(doc_repo, ignore_errors=True)


def _assert_doc_scan_registers_valid_markdown_across_docs_root(metadata_db_case, tmp_path):
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
{_obsidian_properties("Product Overview")}
doc_type: prd
product_key: {product_code}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )
    _write_doc(
        tmp_path / "dsc" / "domain.md",
        f"""
doc_id: DOMAIN-{token}
title: Domain Note
{_obsidian_properties("Domain Note")}
doc_type: tech-design
product_key: {product_code}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )

    result = doc_scan_service.scan_binding(metadata_db_case, binding["id"])

    assert result["registered_count"] == 2
    assert result["error_count"] == 0
    assert result["ignored_count"] == 0
    documents = document_repository.list_by_binding(metadata_db_case, binding["id"])
    by_path = {document["relative_path"]: document for document in documents}
    assert set(by_path) == {"prd/overview.md", "dsc/domain.md"}
    assert by_path["prd/overview.md"]["doc_id"] == f"DOC-{token}"
    assert by_path["prd/overview.md"]["doc_type"] == "prd"
    assert by_path["prd/overview.md"]["title"] == "Product Overview"
    assert by_path["prd/overview.md"]["front_matter_json"]["product_key"] == product_code
    assert by_path["prd/overview.md"]["front_matter_json"]["aliases"] == ["Product Overview"]
    assert by_path["prd/overview.md"]["front_matter_json"]["tags"] == ["neodev/docs"]
    assert by_path["prd/overview.md"]["front_matter_json"]["related"] == ["[[PROJECT-REF]]"]
    assert by_path["prd/overview.md"]["relations_json"] == {"target": [f"PROJECT-{token}"]}
    assert by_path["dsc/domain.md"]["doc_id"] == f"DOMAIN-{token}"
    assert by_path["dsc/domain.md"]["doc_type"] == "tech-design"


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
{_obsidian_properties("Missing Relations")}
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
{_obsidian_properties("Invalid Type")}
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
{_obsidian_properties("Invalid Status")}
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
{_obsidian_properties("First Title")}
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
{_obsidian_properties("Updated Title")}
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


def test_doc_scan_requires_obsidian_properties(metadata_db_case):
    doc_repo = _make_doc_repo()
    try:
        _assert_doc_scan_requires_obsidian_properties(metadata_db_case, doc_repo)
    finally:
        shutil.rmtree(doc_repo, ignore_errors=True)


def _assert_doc_scan_requires_obsidian_properties(metadata_db_case, tmp_path):
    token = uuid.uuid4().hex[:8]
    product_code = f"DOC-OB-{token}"
    product_id = _create_product(metadata_db_case, product_code)
    binding = doc_binding_repository.create(
        metadata_db_case,
        product_id=product_id,
        repo_path=str(tmp_path),
    )
    _write_doc(
        tmp_path / "prd" / "missing-ob.md",
        f"""
doc_id: DOC-OB-{token}
title: Missing Obsidian Properties
doc_type: prd
product_key: {product_code}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )

    result = doc_scan_service.scan_binding(metadata_db_case, binding["id"])

    assert result["registered_count"] == 0
    assert result["error_count"] == 1
    errors = scan_error_repository.list_by_binding(metadata_db_case, binding["id"])
    assert set(errors[0]["details_json"]["missing_fields"]) == {
        "aliases",
        "tags",
        "created",
        "updated",
        "related",
    }


def test_doc_scan_accepts_obsidian_crlf_front_matter(metadata_db_case):
    doc_repo = _make_doc_repo()
    try:
        _assert_doc_scan_accepts_obsidian_crlf_front_matter(metadata_db_case, doc_repo)
    finally:
        shutil.rmtree(doc_repo, ignore_errors=True)


def _assert_doc_scan_accepts_obsidian_crlf_front_matter(metadata_db_case, tmp_path):
    token = uuid.uuid4().hex[:8]
    product_code = f"DOCCRLF-{token}"
    product_id = _create_product(metadata_db_case, product_code)
    binding = doc_binding_repository.create(
        metadata_db_case,
        product_id=product_id,
        repo_path=str(tmp_path),
    )
    _write_doc_crlf(
        tmp_path / "tech-design" / "crlf.md",
        f"""
doc_id: DOC-CRLF-{token}
title: CRLF Document
{_obsidian_properties("CRLF Document")}
doc_type: tech-design
product_key: {product_code}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )

    result = doc_scan_service.scan_binding(metadata_db_case, binding["id"])

    assert result["registered_count"] == 1
    assert result["error_count"] == 0


def test_doc_scan_includes_docs_directory(metadata_db_case):
    doc_repo = _make_doc_repo()
    try:
        token = uuid.uuid4().hex[:8]
        product_code = f"DOCDIR-{token}"
        product_id = _create_product(metadata_db_case, product_code)
        binding = doc_binding_repository.create(
            metadata_db_case,
            product_id=product_id,
            repo_path=str(doc_repo),
        )
        _write_doc(
            doc_repo / "docs" / "guide.md",
            f"""
doc_id: DOC-DIR-{token}
title: Docs Guide
{_obsidian_properties("Docs Guide")}
doc_type: tech-design
product_key: {product_code}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
        )

        result = doc_scan_service.scan_binding(metadata_db_case, binding["id"])

        assert result["registered_count"] == 1
        assert result["error_count"] == 0
        assert result["documents"][0]["relative_path"] == "docs/guide.md"
    finally:
        shutil.rmtree(doc_repo, ignore_errors=True)


def test_doc_scan_skips_hidden_markdown(metadata_db_case):
    doc_repo = _make_doc_repo()
    try:
        token = uuid.uuid4().hex[:8]
        product_code = f"DOCHIDDEN-{token}"
        product_id = _create_product(metadata_db_case, product_code)
        binding = doc_binding_repository.create(
            metadata_db_case,
            product_id=product_id,
            repo_path=str(doc_repo),
        )
        _write_doc(
            doc_repo / ".obsidian" / "workspace.md",
            f"""
doc_id: DOC-HIDDEN-{token}
title: Hidden Workspace
{_obsidian_properties("Hidden Workspace")}
doc_type: tech-design
product_key: {product_code}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
        )

        result = doc_scan_service.scan_binding(metadata_db_case, binding["id"])

        assert result["registered_count"] == 0
        assert result["error_count"] == 0
        assert result["ignored_count"] == 1
    finally:
        shutil.rmtree(doc_repo, ignore_errors=True)
