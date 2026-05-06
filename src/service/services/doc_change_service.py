import re

from service.cli.errors import CliError
from service.repositories import doc_change_repository
from service.repositories import document_repository


def register_doc_change(
    conn,
    document_id: int,
    doc_change_id: str | None = None,
    source_commit: str | None = None,
    summary: str | None = None,
    details_json: dict | None = None,
    created_by: str | None = None,
) -> dict:
    document = document_repository.find_by_id(conn, document_id)
    if not document:
        raise CliError(category="not_found", message="document not found")

    resolved_doc_change_id = doc_change_id or source_commit or document.get("last_seen_commit")
    if not resolved_doc_change_id:
        raise CliError(
            category="invalid_scope",
            message="document commit is required for DocChange-ID",
            details={"document_id": document_id},
        )
    if not _is_commit_hash(resolved_doc_change_id):
        raise CliError(
            category="invalid_argument",
            message="DocChange-ID must be a 40-character document commit hash",
            details={"doc_change_id": resolved_doc_change_id},
        )
    resolved_doc_change_id = resolved_doc_change_id.lower()
    resolved_source_commit = source_commit or resolved_doc_change_id
    if not _is_commit_hash(resolved_source_commit):
        raise CliError(
            category="invalid_argument",
            message="source_commit must be a 40-character document commit hash",
            details={"source_commit": resolved_source_commit},
        )
    resolved_source_commit = resolved_source_commit.lower()
    if resolved_source_commit != resolved_doc_change_id:
        raise CliError(
            category="invalid_argument",
            message="DocChange-ID and source_commit must match the document commit hash",
            details={
                "doc_change_id": resolved_doc_change_id,
                "source_commit": resolved_source_commit,
            },
        )
    change = doc_change_repository.create(
        conn,
        document_id=document_id,
        doc_change_id=resolved_doc_change_id,
        source_commit=resolved_source_commit,
        summary=summary,
        details_json=details_json,
        created_by=created_by,
        status="pending_implementation",
    )
    return {"doc_change": change, "document": document}


def show_doc_change(
    conn,
    change_id: int | None = None,
    doc_change_id: str | None = None,
) -> dict:
    change = _resolve_doc_change(conn, change_id=change_id, doc_change_id=doc_change_id)
    document = document_repository.find_by_id(conn, change["document_id"])
    return {"doc_change": change, "document": document}


def mark_implemented(
    conn,
    change_id: int | None = None,
    doc_change_id: str | None = None,
) -> dict:
    change = _resolve_doc_change(conn, change_id=change_id, doc_change_id=doc_change_id)
    updated = doc_change_repository.mark_implemented(conn, change["id"])
    if not updated:
        raise CliError(category="not_found", message="doc change not found")
    document = document_repository.find_by_id(conn, updated["document_id"])
    return {"doc_change": updated, "document": document}


def _resolve_doc_change(
    conn,
    change_id: int | None = None,
    doc_change_id: str | None = None,
) -> dict:
    if change_id is None and not doc_change_id:
        raise CliError(
            category="invalid_argument",
            message="provide --change-id or --doc-change-id",
        )
    if change_id is not None and doc_change_id:
        raise CliError(
            category="invalid_argument",
            message="provide only one doc change locator",
        )
    if change_id is not None:
        change = doc_change_repository.find_by_id(conn, change_id)
    else:
        change = doc_change_repository.find_by_doc_change_id(conn, doc_change_id)
    if not change:
        raise CliError(category="not_found", message="doc change not found")
    return change
def _is_commit_hash(value: str | None) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", str(value or "")))
