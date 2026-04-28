import pytest


def test_semantic_search_returns_document_chunks(monkeypatch):
    from service.services import graph_semantic_search_service

    monkeypatch.setattr(
        graph_semantic_search_service.product_version_service,
        "get_version",
        lambda conn, version_id: {"id": version_id, "product_id": 7, "version_name": "V1.0"},
    )
    monkeypatch.setattr(
        graph_semantic_search_service.doc_semantic_search_service,
        "search_chunks",
        lambda conn, *, product_version_id, query, top_k: {
            "product_version_id": product_version_id,
            "query": query,
            "top_k": top_k,
            "semantic_status": "vectorized",
            "results": [
                {
                    "document_id": 11,
                    "doc_id": "DOC-1",
                    "title": "Login PRD",
                    "doc_type": "prd",
                    "relative_path": "prd/login.md",
                    "chunk_id": 101,
                    "chunk_index": 0,
                    "heading_path": "Login",
                    "snippet": "Login token requirements",
                    "score": 0.91,
                    "semantic_status": "vectorized",
                }
            ],
            "degraded_reasons": [],
        },
    )

    result = graph_semantic_search_service.semantic_search(
        object(),
        product_version_id=23,
        query="login token",
        top_k=3,
    )

    assert result["product_version_id"] == 23
    assert result["semantic_status"] == "vectorized"
    assert result["results"][0]["chunk_id"] == 101
    assert "entity_id" not in result["results"][0]
    assert "entity_type" not in result["results"][0]


def test_semantic_search_rejects_unknown_product_version(monkeypatch):
    from service.services import graph_semantic_search_service

    monkeypatch.setattr(
        graph_semantic_search_service.product_version_service,
        "get_version",
        lambda conn, version_id: None,
    )

    with pytest.raises(graph_semantic_search_service.GraphSemanticSearchError) as exc_info:
        graph_semantic_search_service.semantic_search(
            object(),
            product_version_id=23,
            query="anything",
        )

    assert exc_info.value.category == "not_found"
    assert exc_info.value.details == {"product_version_id": 23}


def test_semantic_search_validates_query_and_top_k():
    from service.services import graph_semantic_search_service

    with pytest.raises(graph_semantic_search_service.GraphSemanticSearchError) as query_exc:
        graph_semantic_search_service.semantic_search(object(), product_version_id=23, query=" ")
    assert query_exc.value.category == "invalid_argument"

    with pytest.raises(graph_semantic_search_service.GraphSemanticSearchError) as top_k_exc:
        graph_semantic_search_service.semantic_search(
            object(),
            product_version_id=23,
            query="login",
            top_k=0,
        )
    assert top_k_exc.value.category == "invalid_argument"
