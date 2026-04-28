"""Document chunk semantic search backed by pgvector."""

from __future__ import annotations

from typing import Any

from service.repositories import document_chunk_repository
from service.services import llm_client
from service.services import product_version_service


def search_chunks(
    conn,
    *,
    product_version_id: int,
    query: str,
    top_k: int,
) -> dict[str, Any]:
    version = product_version_service.get_version(conn, product_version_id)
    product_id = int(version["product_id"])
    embedding, embedding_error = _embed_query(query)
    if not embedding:
        return {
            "product_version_id": product_version_id,
            "query": query,
            "top_k": top_k,
            "semantic_status": "not_vectorized",
            "results": [],
            "degraded_reasons": [
                {
                    "reason": "query_embedding_failed",
                    "error_message": embedding_error or "embedding is empty",
                }
            ],
        }

    rows = document_chunk_repository.search_chunks(
        conn,
        product_id=product_id,
        embedding=embedding,
        top_k=top_k,
    )
    return {
        "product_version_id": product_version_id,
        "query": query,
        "top_k": top_k,
        "semantic_status": "vectorized" if rows else "empty",
        "results": [_format_chunk(row) for row in rows],
        "degraded_reasons": [],
    }


def _embed_query(query: str) -> tuple[list[float] | None, str | None]:
    try:
        return llm_client.embedding_completion(query), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _format_chunk(row: dict) -> dict[str, Any]:
    chunk_text = str(row.get("chunk_text") or "")
    return {
        "document_id": row.get("document_id"),
        "doc_id": row.get("doc_id"),
        "title": row.get("title"),
        "doc_type": row.get("doc_type"),
        "relative_path": row.get("relative_path"),
        "chunk_id": row.get("chunk_id"),
        "chunk_index": row.get("chunk_index"),
        "heading_path": row.get("heading_path") or "",
        "snippet": _snippet(chunk_text),
        "score": float(row.get("score") or 0),
        "semantic_status": "vectorized",
    }


def _snippet(text: str, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."
