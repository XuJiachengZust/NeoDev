import pytest


def test_create_node_rejects_unregistered_type(monkeypatch):
    from service.services import graph_management_service

    monkeypatch.setattr(
        graph_management_service.repo,
        "get_node_type",
        lambda conn, project_id, type_key: None,
    )

    with pytest.raises(graph_management_service.GraphManagementError) as exc_info:
        graph_management_service.create_node(
            object(),
            project_id=1,
            node_id="node-1",
            type_key="SERVICE",
            name="Auth Service",
        )

    assert exc_info.value.category == "invalid_type"
    assert exc_info.value.details == {"project_id": 1, "type_key": "SERVICE"}


def test_update_node_rejects_identity_fields(monkeypatch):
    from service.services import graph_management_service

    with pytest.raises(graph_management_service.GraphManagementError) as exc_info:
        graph_management_service.update_node(
            object(),
            project_id=1,
            node_id="node-1",
            updates={"file_path": "src/changed.py"},
        )

    assert exc_info.value.category == "invalid_argument"
    assert exc_info.value.details == {"identity_fields": ["file_path"]}


def test_create_edge_rejects_owner_project_outside_endpoints(monkeypatch):
    from service.services import graph_management_service

    monkeypatch.setattr(
        graph_management_service.repo,
        "get_relation_type",
        lambda conn, project_id, type_key: {
            "project_id": project_id,
            "type_key": type_key,
            "cross_project_allowed": True,
        },
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "get_node_by_any_project",
        lambda conn, node_id: {
            "from-node": {"project_id": 1, "node_id": "from-node", "type_key": "SERVICE"},
            "to-node": {"project_id": 2, "node_id": "to-node", "type_key": "DATABASE"},
        }.get(node_id),
    )

    with pytest.raises(graph_management_service.GraphManagementError) as exc_info:
        graph_management_service.create_edge(
            object(),
            project_id=3,
            edge_id="edge-1",
            from_node_id="from-node",
            to_node_id="to-node",
            type_key="DEPENDS_ON",
        )

    assert exc_info.value.category == "invalid_scope"
    assert exc_info.value.details == {
        "project_id": 3,
        "from_project_id": 1,
        "to_project_id": 2,
    }


def test_create_edge_rejects_cross_project_when_type_disallows(monkeypatch):
    from service.services import graph_management_service

    monkeypatch.setattr(
        graph_management_service.repo,
        "get_relation_type",
        lambda conn, project_id, type_key: {
            "project_id": project_id,
            "type_key": type_key,
            "cross_project_allowed": False,
        },
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "get_node_by_any_project",
        lambda conn, node_id: {
            "from-node": {"project_id": 1, "node_id": "from-node", "type_key": "SERVICE"},
            "to-node": {"project_id": 2, "node_id": "to-node", "type_key": "DATABASE"},
        }.get(node_id),
    )

    with pytest.raises(graph_management_service.GraphManagementError) as exc_info:
        graph_management_service.create_edge(
            object(),
            project_id=1,
            edge_id="edge-1",
            from_node_id="from-node",
            to_node_id="to-node",
            type_key="DEPENDS_ON",
        )

    assert exc_info.value.category == "invalid_scope"
    assert exc_info.value.details == {
        "type_key": "DEPENDS_ON",
        "cross_project_allowed": False,
    }


def test_create_edge_persists_valid_cross_project_edge(monkeypatch):
    from service.services import graph_management_service

    captured = {}
    monkeypatch.setattr(
        graph_management_service.repo,
        "get_relation_type",
        lambda conn, project_id, type_key: {
            "project_id": project_id,
            "type_key": type_key,
            "cross_project_allowed": True,
        },
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "get_node_by_any_project",
        lambda conn, node_id: {
            "from-node": {"project_id": 1, "node_id": "from-node", "type_key": "SERVICE"},
            "to-node": {"project_id": 2, "node_id": "to-node", "type_key": "DATABASE"},
        }.get(node_id),
    )

    def fake_upsert_edge(conn, **kwargs):
        captured.update(kwargs)
        return {"edge_id": kwargs["edge_id"], "cross_project": True, **kwargs}

    monkeypatch.setattr(graph_management_service.repo, "upsert_edge", fake_upsert_edge)

    result = graph_management_service.create_edge(
        object(),
        project_id=1,
        edge_id="edge-1",
        from_node_id="from-node",
        to_node_id="to-node",
        type_key="DEPENDS_ON",
    )

    assert result["edge_id"] == "edge-1"
    assert captured["from_project_id"] == 1
    assert captured["to_project_id"] == 2
