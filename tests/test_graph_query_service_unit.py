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


def _capture_and_return(captured, payload):
    def _inner(**kwargs):
        captured["kwargs"] = kwargs
        return payload

    return _inner


def test_entity_context_reads_current_branch_graph_from_neo4j(monkeypatch):
    from service.services import graph_query_service

    _patch_valid_scope(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        graph_query_service.branch_graph_repository,
        "get_by_project_branch",
        lambda conn, project_id, branch: {
            "id": 91,
            "status": "ready",
            "head_commit": "abc",
            "node_count": 3,
            "edge_count": 2,
        },
    )
    monkeypatch.setattr(
        graph_query_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(
        graph_query_service.branch_graph_neo4j_service,
        "entity_context",
        _capture_and_return(captured, {
            "entity": {"id": "project:11:branch:release/V1.0:node:Function:auth:login", "node_id": "Function:auth:login"},
            "neighbors": [{"id": "project:11:branch:release/V1.0:node:File:auth.py", "node_id": "File:auth.py"}],
            "edges": [{"type": "CONTAINS"}],
            "context_summary": ["Function:auth:login"],
        }),
    )

    result = graph_query_service.entity_context(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/V1.0",
        entity_id="Function:auth:login",
        depth=1,
    )

    assert result["entity"]["node_id"] == "Function:auth:login"
    assert result["neighbors"][0]["node_id"] == "File:auth.py"
    assert result["edges"] == [{"type": "CONTAINS"}]
    assert result["degraded_reasons"] == []
    assert captured["kwargs"]["product_name"] == "UNIT"
    assert captured["kwargs"]["version_name"] == "V1.0"
    assert captured["kwargs"]["project_name"] == "api-service"
    assert captured["kwargs"]["branch_name"] == "release/V1.0"


def test_get_chain_reads_current_branch_graph_from_neo4j(monkeypatch):
    from service.services import graph_query_service

    _patch_valid_scope(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        graph_query_service.branch_graph_repository,
        "get_by_project_branch",
        lambda conn, project_id, branch: {
            "id": 91,
            "status": "ready",
            "head_commit": "abc",
            "node_count": 3,
            "edge_count": 2,
        },
    )
    monkeypatch.setattr(
        graph_query_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(
        graph_query_service.branch_graph_neo4j_service,
        "get_chain",
        _capture_and_return(captured, {
            "start_node": {"id": "project:11:branch:release/V1.0:node:Function:auth:login", "node_id": "Function:auth:login"},
            "nodes": [{"node_id": "Function:auth:login"}],
            "edges": [{"type": "CALLS"}],
            "path_summary": ["Function:auth:login"],
        }),
    )

    result = graph_query_service.get_chain(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/V1.0",
        start_node="Function:auth:login",
        depth=2,
    )

    assert result["start_node"]["node_id"] == "Function:auth:login"
    assert result["snapshot_id"] == 91
    assert result["head_commit"] == "abc"
    assert result["nodes"] == [{"node_id": "Function:auth:login"}]
    assert result["edges"] == [{"type": "CALLS"}]
    assert result["degraded_reasons"] == []
    assert captured["kwargs"]["product_name"] == "UNIT"
    assert captured["kwargs"]["version_name"] == "V1.0"
    assert captured["kwargs"]["project_name"] == "api-service"
    assert captured["kwargs"]["branch_name"] == "release/V1.0"


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
