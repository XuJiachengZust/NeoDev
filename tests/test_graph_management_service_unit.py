import pytest


def test_list_node_types_includes_builtin_graph_types_when_project_has_no_manual_types(monkeypatch):
    from service.services import graph_management_service

    monkeypatch.setattr(
        graph_management_service.repo,
        "list_node_types",
        lambda conn, project_id: [],
    )

    result = graph_management_service.list_node_types(object(), project_id=9)
    type_keys = {row["type_key"] for row in result["node_types"]}

    assert {"Project", "BranchGraph", "Document", "File", "Folder", "Function"}.issubset(type_keys)
    assert result["count"] == len(result["node_types"])


def test_list_relation_types_includes_builtin_graph_types_and_manual_types(monkeypatch):
    from service.services import graph_management_service

    monkeypatch.setattr(
        graph_management_service.repo,
        "list_relation_types",
        lambda conn, project_id: [
            {
                "id": 31,
                "project_id": project_id,
                "type_key": "DEPENDS_ON",
                "name": "Depends On",
                "description": "manual relation",
                "allowed_from_types": [],
                "allowed_to_types": [],
                "cross_project_allowed": True,
                "status": "active",
            }
        ],
    )

    result = graph_management_service.list_relation_types(object(), project_id=9)
    type_keys = {row["type_key"] for row in result["edge_types"]}

    assert {"CALLS", "CONTAINS", "DEFINES", "HAS_BRANCH_GRAPH", "LINKS_TO_CODE"}.issubset(type_keys)
    assert "DEPENDS_ON" in type_keys
    assert result["count"] == len(result["edge_types"])


def test_create_node_accepts_builtin_graph_type_without_manual_registration(monkeypatch):
    from service.services import graph_management_service

    monkeypatch.setattr(
        graph_management_service.repo,
        "get_node_type",
        lambda conn, project_id, type_key: None,
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "upsert_node",
        lambda conn, **kwargs: {"project_id": kwargs["project_id"], "type_key": kwargs["type_key"]},
    )

    node = graph_management_service.create_node(
        object(),
        project_id=1,
        node_id="Function:src/app.py:main",
        type_key="Function",
        name="main",
    )

    assert node["type_key"] == "Function"


def test_create_edge_accepts_builtin_relation_type_without_manual_registration(monkeypatch):
    from service.services import graph_management_service

    monkeypatch.setattr(
        graph_management_service.repo,
        "get_relation_type",
        lambda conn, project_id, type_key: None,
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "get_node_by_any_project",
        lambda conn, node_id: {
            "source": {"project_id": 1, "node_id": "source", "type_key": "Function"},
            "target": {"project_id": 1, "node_id": "target", "type_key": "Function"},
        }.get(node_id),
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "upsert_edge",
        lambda conn, **kwargs: {"project_id": kwargs["project_id"], "type_key": kwargs["type_key"]},
    )

    edge = graph_management_service.create_edge(
        object(),
        project_id=1,
        edge_id="CALLS:source->target",
        from_node_id="source",
        to_node_id="target",
        type_key="CALLS",
    )

    assert edge["type_key"] == "CALLS"


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
