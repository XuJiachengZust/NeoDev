def test_create_node_with_branch_projects_manual_node_to_current_snapshot(monkeypatch):
    from service.services import graph_management_service

    calls = {"facts": [], "snapshot_facts": [], "logs": []}

    monkeypatch.setattr(
        graph_management_service,
        "_require_node_type",
        lambda conn, project_id, type_key: {"project_id": project_id, "type_key": type_key},
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "upsert_node",
        lambda conn, **kwargs: {
            "id": 101,
            "project_id": kwargs["project_id"],
            "node_id": kwargs["node_id"],
            "type_key": kwargs["type_key"],
            "name": kwargs["name"],
            "properties": kwargs["properties"],
            "status": "active",
        },
    )
    monkeypatch.setattr(
        graph_management_service,
        "branch_snapshot_service",
        type(
            "SnapshotService",
            (),
            {
                "get_current_snapshot": staticmethod(
                    lambda conn, project_id, branch: {"id": 501, "branch_name": branch}
                ),
                "add_fact": staticmethod(
                    lambda conn, snapshot_id, fact_id: calls["snapshot_facts"].append(
                        {"snapshot_id": snapshot_id, "fact_id": fact_id}
                    )
                ),
            },
        ),
        raising=False,
    )
    monkeypatch.setattr(
        graph_management_service.code_fact_repo,
        "upsert_many",
        lambda conn, facts: calls["facts"].extend(facts) or len(facts),
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "create_operation_log",
        lambda conn, **kwargs: calls["logs"].append(kwargs) or {"id": 77, **kwargs},
    )
    monkeypatch.setattr(
        graph_management_service,
        "manual_graph_sync_service",
        type("Sync", (), {"sync_node": staticmethod(lambda *args, **kwargs: None)}),
        raising=False,
    )

    node = graph_management_service.create_node(
        object(),
        project_id=3,
        branch="release/x",
        node_id="manual-login",
        type_key="SERVICE",
        name="Login Service",
        properties={"owner": "sec"},
    )

    assert node["node_id"] == "manual-login"
    assert calls["snapshot_facts"] == [
        {"snapshot_id": 501, "fact_id": "manual:3:node:manual-login"}
    ]
    fact = calls["facts"][0]
    assert fact["project_id"] == 3
    assert fact["fact_id"] == "manual:3:node:manual-login"
    assert fact["symbol_key"] == "manual:3:node:manual-login"
    assert fact["node_type"] == "Function"
    assert fact["qualified_name"] == "manual.SERVICE.manual-login"
    assert fact["metadata_json"]["source"] == "manual"
    assert fact["metadata_json"]["manual_node_id"] == "manual-login"
    assert fact["metadata_json"]["type_key"] == "SERVICE"
    assert fact["metadata_json"]["operation_id"] == 77
    assert calls["logs"][0]["object_kind"] == "node"
    assert calls["logs"][0]["operation"] == "upsert"
    assert calls["logs"][0]["snapshot_id"] == 501


def test_archive_node_with_branch_removes_manual_fact_from_current_snapshot(monkeypatch):
    from service.services import graph_management_service

    calls = {"removed": [], "logs": []}

    monkeypatch.setattr(
        graph_management_service.repo,
        "get_node",
        lambda conn, project_id, node_id: {
            "id": 101,
            "project_id": project_id,
            "node_id": node_id,
            "type_key": "SERVICE",
            "name": "Login Service",
            "properties": {},
            "status": "active",
        },
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "archive_node",
        lambda conn, project_id, node_id: {
            "id": 101,
            "project_id": project_id,
            "node_id": node_id,
            "type_key": "SERVICE",
            "name": "Login Service",
            "properties": {},
            "status": "archived",
        },
    )
    monkeypatch.setattr(
        graph_management_service,
        "branch_snapshot_service",
        type(
            "SnapshotService",
            (),
            {
                "get_current_snapshot": staticmethod(
                    lambda conn, project_id, branch: {"id": 501, "branch_name": branch}
                ),
                "remove_fact": staticmethod(
                    lambda conn, snapshot_id, fact_id: calls["removed"].append(
                        {"snapshot_id": snapshot_id, "fact_id": fact_id}
                    )
                ),
            },
        ),
        raising=False,
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "create_operation_log",
        lambda conn, **kwargs: calls["logs"].append(kwargs) or {"id": 88, **kwargs},
    )
    monkeypatch.setattr(
        graph_management_service,
        "manual_graph_sync_service",
        type("Sync", (), {"archive_node": staticmethod(lambda *args, **kwargs: None)}),
        raising=False,
    )

    node = graph_management_service.archive_node(
        object(),
        project_id=3,
        branch="release/x",
        node_id="manual-login",
    )

    assert node["status"] == "archived"
    assert calls["removed"] == [
        {"snapshot_id": 501, "fact_id": "manual:3:node:manual-login"}
    ]
    assert calls["logs"][0]["object_kind"] == "node"
    assert calls["logs"][0]["operation"] == "archive"
    assert calls["logs"][0]["before_json"]["status"] == "active"
    assert calls["logs"][0]["after_json"]["status"] == "archived"


def test_create_edge_with_branch_logs_and_syncs_manual_edge(monkeypatch):
    from service.services import graph_management_service

    calls = {"logs": [], "synced": []}

    monkeypatch.setattr(
        graph_management_service.repo,
        "get_relation_type",
        lambda conn, project_id, type_key: {
            "project_id": project_id,
            "type_key": type_key,
            "cross_project_allowed": True,
            "allowed_from_types": [],
            "allowed_to_types": [],
        },
    )
    monkeypatch.setattr(
        graph_management_service,
        "_require_node",
        lambda conn, node_id, project_id=None: {
            "project_id": project_id or 3,
            "node_id": node_id,
            "type_key": "SERVICE",
        },
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "upsert_edge",
        lambda conn, **kwargs: {"id": 201, **kwargs, "status": "active"},
    )
    monkeypatch.setattr(
        graph_management_service,
        "branch_snapshot_service",
        type(
            "SnapshotService",
            (),
            {
                "get_current_snapshot": staticmethod(
                    lambda conn, project_id, branch: {"id": 501, "branch_name": branch}
                )
            },
        ),
        raising=False,
    )
    monkeypatch.setattr(
        graph_management_service.repo,
        "create_operation_log",
        lambda conn, **kwargs: calls["logs"].append(kwargs) or {"id": 99, **kwargs},
    )
    monkeypatch.setattr(
        graph_management_service,
        "manual_graph_sync_service",
        type(
            "Sync",
            (),
            {
                "sync_edge": staticmethod(
                    lambda conn, **kwargs: calls["synced"].append(kwargs)
                )
            },
        ),
        raising=False,
    )

    edge = graph_management_service.create_edge(
        object(),
        project_id=3,
        branch="release/x",
        edge_id="edge-1",
        from_node_id="manual-a",
        to_node_id="manual-b",
        type_key="depends-on",
        properties={"weight": "3"},
    )

    assert edge["edge_id"] == "edge-1"
    assert calls["logs"][0]["object_kind"] == "edge"
    assert calls["logs"][0]["operation"] == "upsert"
    assert calls["logs"][0]["snapshot_id"] == 501
    assert calls["synced"][0]["branch"] == "release/x"
    assert calls["synced"][0]["snapshot_id"] == 501
    assert calls["synced"][0]["edge"]["edge_id"] == "edge-1"
