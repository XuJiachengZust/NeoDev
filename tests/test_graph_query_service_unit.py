import pytest


def _patch_valid_scope(monkeypatch):
    from service.services import graph_query_service

    monkeypatch.setattr(
        graph_query_service.product_version_service,
        "get_version",
        lambda conn, version_id: {"id": version_id, "product_id": 7, "version_name": "V1.0"},
    )
    monkeypatch.setattr(
        graph_query_service.product_service,
        "get_product",
        lambda conn, product_id: {"id": product_id, "code": "UNIT"},
    )
    monkeypatch.setattr(
        graph_query_service.project_service,
        "get_project",
        lambda conn, project_id: {"id": project_id, "name": "api-service"},
    )
    monkeypatch.setattr(
        graph_query_service.product_version_service,
        "list_branches",
        lambda conn, version_id: [
            {
                "product_version_id": version_id,
                "project_id": 11,
                "project_name": "api-service",
                "branch_name": "release/V1.0",
            }
        ],
    )


def test_entity_context_returns_storage_removed_degraded_result(monkeypatch):
    from service.services import graph_query_service

    _patch_valid_scope(monkeypatch)

    result = graph_query_service.entity_context(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/V1.0",
        entity_id="Function:auth:login",
        depth=1,
    )

    assert result["entity"] is None
    assert result["neighbors"] == []
    assert result["edges"] == []
    assert result["degraded_reasons"] == [
        {
            "project_id": 11,
            "branch": "release/V1.0",
            "reason": "code_node_storage_removed",
        }
    ]


def test_get_chain_returns_storage_removed_empty_chain(monkeypatch):
    from service.services import graph_query_service

    _patch_valid_scope(monkeypatch)

    result = graph_query_service.get_chain(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/V1.0",
        start_node="Function:auth:login",
        depth=2,
    )

    assert result["start_node"] is None
    assert result["snapshot_id"] is None
    assert result["head_commit"] is None
    assert result["nodes"] == []
    assert result["edges"] == []
    assert result["degraded_reasons"][0]["reason"] == "code_node_storage_removed"


def test_get_chain_requires_exactly_one_start_locator(monkeypatch):
    from service.services import graph_query_service

    _patch_valid_scope(monkeypatch)

    with pytest.raises(graph_query_service.GraphQueryError) as missing:
        graph_query_service.get_chain(
            object(),
            product_version_id=23,
            project_id=11,
            branch="release/V1.0",
        )
    assert missing.value.category == "invalid_argument"

    with pytest.raises(graph_query_service.GraphQueryError) as duplicate:
        graph_query_service.get_chain(
            object(),
            product_version_id=23,
            project_id=11,
            branch="release/V1.0",
            start_node="Function:auth:login",
            symbol="login",
        )
    assert duplicate.value.category == "invalid_argument"


def test_graph_query_rejects_branch_outside_product_version(monkeypatch):
    from service.services import graph_query_service

    _patch_valid_scope(monkeypatch)

    with pytest.raises(graph_query_service.GraphQueryError) as exc_info:
        graph_query_service.entity_context(
            object(),
            product_version_id=23,
            project_id=11,
            branch="feature/not-bound",
            entity_id="Function:auth:login",
        )

    assert exc_info.value.category == "invalid_scope"
    assert exc_info.value.details["expected_branch"] == "release/V1.0"
    assert exc_info.value.details["actual_branch"] == "feature/not-bound"
