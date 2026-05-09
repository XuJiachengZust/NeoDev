from pathlib import Path
import shutil
import uuid

import service.repositories.doc_binding_repository as doc_binding_repository
import service.repositories.document_repository as document_repository
import service.repositories.document_scan_error_repository as scan_error_repository
from service.services import doc_import_service


class FakeConn:
    pass


ROOT = Path(__file__).resolve().parent.parent


def _make_doc_repo() -> Path:
    path = ROOT / ".codex-tmp" / "doc-import-unit" / uuid.uuid4().hex
    path.mkdir(parents=True)
    return path


def test_import_binding_builds_chunks_and_reuses_changed_embeddings(monkeypatch):
    repo_path = _make_doc_repo()
    (repo_path / ".git").mkdir()
    doc_path = repo_path / "neosuperpower" / "plans" / "guide.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text(
        """---
doc_id: DOC-IMPORT-1
title: Import Guide
aliases:
  - Import Guide
tags:
  - neodev/docs
created: 2026-04-28
updated: 2026-04-28
related:
  - "[[ROOT]]"
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - ROOT
---

# Import

The import service chunks documents.
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        doc_import_service.doc_binding_repository,
        "find_by_id",
        lambda conn, doc_binding_id: {
            "id": doc_binding_id,
            "product_id": 7,
            "product_version_id": 17,
            "repo_path": str(repo_path),
            "repo_url": "",
            "default_branch": "main",
        },
    )
    monkeypatch.setattr(doc_import_service, "_sync_git_repo", lambda binding: None)
    monkeypatch.setattr(doc_import_service, "_last_commit_for_path", lambda repo_path, relative_path: "c" * 40)
    monkeypatch.setattr(
        doc_import_service.document_repository,
        "upsert",
        lambda conn, **kwargs: {"id": 11, **kwargs},
    )
    monkeypatch.setattr(
        doc_import_service.doc_graph_service,
        "upsert_document_graph",
        lambda *args, **kwargs: {"status": "updated"},
    )
    monkeypatch.setattr(
        doc_import_service.document_chunk_repository,
        "replace_document_chunks",
        lambda conn, document_id, chunks: [{"id": index + 101, **chunk} for index, chunk in enumerate(chunks)],
    )
    embedded = []
    monkeypatch.setattr(
        doc_import_service.doc_vector_service,
        "embed_chunks",
        lambda conn, document, chunks, force=False: embedded.extend(chunks) or {"embedded_count": len(chunks), "reused_count": 0},
    )
    monkeypatch.setattr(
        doc_import_service.document_repository,
        "mark_missing_deleted",
        lambda conn, doc_binding_id, active_paths: [],
    )

    try:
        result = doc_import_service.import_binding(FakeConn(), 5)
    finally:
        shutil.rmtree(repo_path, ignore_errors=True)

    assert result["imported_count"] == 1
    assert result["chunk_count"] >= 1
    assert embedded
    assert result["documents"][0]["relative_path"] == "neosuperpower/plans/guide.md"
    assert "body_text" not in result["documents"][0]
    assert "front_matter_json" not in result["documents"][0]


def test_import_binding_persists_last_document_commit(monkeypatch):
    repo_path = _make_doc_repo()
    (repo_path / ".git").mkdir()
    doc_path = repo_path / "prd" / "reliable-version.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text(
        """---
doc_id: DOC-COMMIT-1
title: Reliable Commit
aliases:
  - Reliable Commit
tags:
  - neodev/docs
created: 2026-05-06
updated: 2026-05-06
related:
  - "[[ROOT]]"
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - ROOT
---

# Reliable Commit
""",
        encoding="utf-8",
    )
    commit_hash = "a" * 40
    upserts = []

    monkeypatch.setattr(
        doc_import_service.doc_binding_repository,
        "find_by_id",
        lambda conn, doc_binding_id: {
            "id": doc_binding_id,
            "product_id": 7,
            "product_version_id": 17,
            "repo_path": str(repo_path),
            "repo_url": "",
            "default_branch": "main",
        },
    )
    monkeypatch.setattr(doc_import_service, "_sync_git_repo", lambda binding: None)
    monkeypatch.setattr(
        doc_import_service,
        "_last_commit_for_path",
        lambda repo_path, relative_path: commit_hash,
    )

    def fake_upsert(conn, **kwargs):
        upserts.append(kwargs)
        return {"id": 11, **kwargs}

    monkeypatch.setattr(doc_import_service.document_repository, "upsert", fake_upsert)
    monkeypatch.setattr(
        doc_import_service.doc_graph_service,
        "upsert_document_graph",
        lambda *args, **kwargs: {"status": "updated"},
    )
    monkeypatch.setattr(
        doc_import_service.document_chunk_repository,
        "replace_document_chunks",
        lambda conn, document_id, chunks: [],
    )
    monkeypatch.setattr(
        doc_import_service.doc_vector_service,
        "embed_chunks",
        lambda conn, document, chunks, force=False: {"embedded_count": 0, "reused_count": 0},
    )
    monkeypatch.setattr(
        doc_import_service.document_repository,
        "mark_missing_deleted",
        lambda conn, doc_binding_id, active_paths: [],
    )

    try:
        result = doc_import_service.import_binding(FakeConn(), 5)
    finally:
        shutil.rmtree(repo_path, ignore_errors=True)

    assert upserts[0]["last_seen_commit"] == commit_hash
    assert result["documents"][0]["last_seen_commit"] == commit_hash


def test_import_binding_overwrites_duplicate_doc_id_and_continues(metadata_db_case, monkeypatch):
    repo_path = _make_doc_repo()
    try:
        _assert_import_binding_overwrites_duplicate_doc_id_and_continues(
            metadata_db_case,
            monkeypatch,
            repo_path,
        )
    finally:
        shutil.rmtree(repo_path, ignore_errors=True)


def _assert_import_binding_overwrites_duplicate_doc_id_and_continues(
    metadata_db_case,
    monkeypatch,
    repo_path: Path,
):
    token = uuid.uuid4().hex[:8]
    product_id = _create_product(metadata_db_case, f"IMPORTDUP-{token}")
    product_version_id = _create_version(metadata_db_case, product_id, f"V-{token}")
    binding = doc_binding_repository.create(
        metadata_db_case,
        product_id=product_id,
        product_version_id=product_version_id,
        repo_path=str(repo_path),
    )
    document_repository.create(
        metadata_db_case,
        doc_binding_id=binding["id"],
        product_version_id=product_version_id,
        doc_id=f"DOC-DUP-{token}",
        relative_path="prd/existing.md",
        doc_type="prd",
        front_matter_json={},
        relations_json={},
        status="active",
        title="Existing",
    )
    (repo_path / ".git").mkdir()
    _write_doc(
        repo_path / "prd" / "duplicate.md",
        f"""
doc_id: DOC-DUP-{token}
title: Duplicate
{_obsidian_properties("Duplicate")}
doc_type: prd
product_key: IMPORTDUP-{token}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )
    _write_doc(
        repo_path / "prd" / "fresh.md",
        f"""
doc_id: DOC-FRESH-{token}
title: Fresh
{_obsidian_properties("Fresh")}
doc_type: prd
product_key: IMPORTDUP-{token}
status: active
relations:
  target:
    - PROJECT-{token}
""".strip(),
    )
    monkeypatch.setattr(doc_import_service, "_sync_git_repo", lambda binding: None)
    monkeypatch.setattr(
        doc_import_service,
        "_last_commit_for_path",
        lambda repo_path, relative_path: "d" * 40,
    )
    monkeypatch.setattr(
        doc_import_service.doc_graph_service,
        "upsert_document_graph",
        lambda *args, **kwargs: {"status": "updated"},
    )
    monkeypatch.setattr(
        doc_import_service.document_chunk_repository,
        "replace_document_chunks",
        lambda conn, document_id, chunks: [],
    )
    monkeypatch.setattr(
        doc_import_service.doc_vector_service,
        "embed_chunks",
        lambda conn, document, chunks, force=False: {"embedded_count": 0, "reused_count": 0},
    )

    result = doc_import_service.import_binding(metadata_db_case, binding["id"])

    assert result["imported_count"] == 2
    assert result["failed_count"] == 0
    by_doc_id = {document["doc_id"]: document for document in result["documents"]}
    assert by_doc_id[f"DOC-DUP-{token}"]["doc_binding_id"] == binding["id"]
    assert by_doc_id[f"DOC-DUP-{token}"]["product_version_id"] == product_version_id
    assert by_doc_id[f"DOC-DUP-{token}"]["relative_path"] == "prd/duplicate.md"
    assert by_doc_id[f"DOC-FRESH-{token}"]["doc_binding_id"] == binding["id"]
    assert scan_error_repository.list_by_binding(metadata_db_case, binding["id"]) == []


def _create_product(conn, code: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO products (name, code)
            VALUES (%s, %s)
            RETURNING id
            """,
            (f"doc-import-product-{code}", code),
        )
        return cur.fetchone()[0]


def _create_version(conn, product_id: int, version_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO product_versions (product_id, version_name)
            VALUES (%s, %s)
            RETURNING id
            """,
            (product_id, version_name),
        )
        return cur.fetchone()[0]


def _write_doc(path: Path, front_matter: str, body: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front_matter}\n---\n\n{body}\n", encoding="utf-8")


def _obsidian_properties(title: str) -> str:
    return f"""
aliases:
  - {title}
tags:
  - neodev/docs
created: 2026-05-07
updated: 2026-05-07
related:
  - "[[PROJECT-REF]]"
""".strip()
