from pathlib import Path
import shutil
import uuid

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
