from dataclasses import dataclass
from typing import Any

from service.services import doc_semantic_search_service
from service.services import product_version_service


@dataclass
class GraphSemanticSearchError(Exception):
    category: str
    message: str
    details: dict | None = None


def semantic_search(
    conn,
    *,
    product_version_id: int,
    query: str,
    top_k: int = 5,
) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        raise GraphSemanticSearchError(
            category="invalid_argument",
            message="query is required",
        )
    if top_k < 1 or top_k > 50:
        raise GraphSemanticSearchError(
            category="invalid_argument",
            message="top_k must be between 1 and 50",
            details={"top_k": top_k},
        )

    version = product_version_service.get_version(conn, product_version_id)
    if not version:
        raise GraphSemanticSearchError(
            category="not_found",
            message="product version not found",
            details={"product_version_id": product_version_id},
        )

    return doc_semantic_search_service.search_chunks(
        conn,
        product_version_id=product_version_id,
        query=query,
        top_k=top_k,
    )
