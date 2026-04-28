from pathlib import Path

from service.services import doc_import_service


class FakeConn:
    pass


def test_import_binding_builds_chunks_and_reuses_changed_embeddings(monkeypatch, tmp_path):
    (tmp_path / ".git").mkdir()
    doc_path = tmp_path / "docs" / "guide.md"
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
            "repo_path": str(tmp_path),
            "repo_url": "",
            "default_branch": "main",
        },
    )
    monkeypatch.setattr(doc_import_service, "_sync_git_repo", lambda binding: None)
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

    result = doc_import_service.import_binding(FakeConn(), 5)

    assert result["imported_count"] == 1
    assert result["chunk_count"] >= 1
    assert embedded
    assert result["documents"][0]["relative_path"] == "docs/guide.md"
