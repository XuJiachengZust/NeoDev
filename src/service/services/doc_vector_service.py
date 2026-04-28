"""Document chunk vectorization."""

from __future__ import annotations

from service.repositories import document_chunk_repository
from service.services import llm_client


def embed_chunks(conn, document: dict, chunks: list[dict], *, force: bool = False) -> dict:
    embedded_count = 0
    reused_count = 0
    model = llm_client.get_llm_config().get("model_embedding") or ""
    for chunk in chunks:
        if chunk.get("embedding") is not None and not force:
            reused_count += 1
            continue
        embedding_text = _embedding_text(document, chunk)
        embedding = llm_client.embedding_completion(embedding_text)
        document_chunk_repository.upsert_embedding(
            conn,
            chunk["id"],
            embedding=embedding,
            embedding_model=str(model),
        )
        embedded_count += 1
    return {"embedded_count": embedded_count, "reused_count": reused_count}


def _embedding_text(document: dict, chunk: dict) -> str:
    front_matter = document.get("front_matter_json") or {}
    relations = document.get("relations_json") or {}
    parts = [
        f"title: {document.get('title') or ''}",
        f"doc_id: {document.get('doc_id') or ''}",
        f"doc_type: {document.get('doc_type') or ''}",
        f"tags: {', '.join(front_matter.get('tags') or [])}",
        f"aliases: {', '.join(front_matter.get('aliases') or [])}",
        f"related: {', '.join(front_matter.get('related') or [])}",
        f"relations: {', '.join(relations.get('target') or [])}",
        f"heading: {chunk.get('heading_path') or ''}",
        str(chunk.get("chunk_text") or chunk.get("text") or ""),
    ]
    return "\n".join(part for part in parts if part.strip())
