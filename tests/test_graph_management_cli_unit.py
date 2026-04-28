from types import SimpleNamespace


class FakeConn:
    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None


def _patch_db(monkeypatch, module):
    monkeypatch.setattr(module.psycopg2, "connect", lambda _: FakeConn())
    monkeypatch.setattr(module, "get_database_url", lambda: "postgresql://test")


def test_handle_node_type_add_calls_service(monkeypatch):
    from service.cli.commands import graph

    _patch_db(monkeypatch, graph)
    captured = {}

    def fake_create_node_type(conn, **kwargs):
        captured.update(kwargs)
        return {"project_id": kwargs["project_id"], "type_key": kwargs["type_key"]}

    monkeypatch.setattr(graph.graph_management_service, "create_node_type", fake_create_node_type)

    payload = graph.handle_node_type_add(
        SimpleNamespace(
            command_name="graph type node add",
            project_id=7,
            key="SERVICE",
            name="服务",
            description="业务服务",
        )
    )

    assert payload["ok"] is True
    assert payload["command"] == "graph type node add"
    assert payload["data"]["node_type"]["type_key"] == "SERVICE"
    assert captured == {
        "project_id": 7,
        "type_key": "SERVICE",
        "name": "服务",
        "description": "业务服务",
    }


def test_handle_edge_add_calls_service_with_properties(monkeypatch):
    from service.cli.commands import graph

    _patch_db(monkeypatch, graph)
    captured = {}

    def fake_create_edge(conn, **kwargs):
        captured.update(kwargs)
        return {"edge_id": kwargs["edge_id"], "type_key": kwargs["type_key"]}

    monkeypatch.setattr(graph.graph_management_service, "create_edge", fake_create_edge)

    payload = graph.handle_edge_add(
        SimpleNamespace(
            command_name="graph edge add",
            project_id=1,
            edge_id="edge-1",
            from_node_id="node-a",
            to_node_id="node-b",
            type="DEPENDS_ON",
            prop=["weight=3", "reason=runtime"],
        )
    )

    assert payload["ok"] is True
    assert payload["command"] == "graph edge add"
    assert payload["data"]["edge"]["edge_id"] == "edge-1"
    assert captured["properties"] == {"weight": "3", "reason": "runtime"}


def test_handle_project_refresh_graph_calls_service(monkeypatch):
    from service.cli.commands import project

    _patch_db(monkeypatch, project)
    monkeypatch.setattr(
        project.project_service,
        "get_project",
        lambda conn, project_id: {"id": project_id, "name": "demo"},
    )
    captured = {}

    def fake_refresh_graph(conn, **kwargs):
        captured.update(kwargs)
        return {"project_id": kwargs["project_id"], "graph_action": "full"}

    monkeypatch.setattr(project.project_service, "refresh_graph", fake_refresh_graph)

    payload = project.handle_project_refresh_graph(
        SimpleNamespace(
            command_name="project refresh-graph",
            project_id=9,
            project_name=None,
            branch="main",
            version_id=12,
        )
    )

    assert payload["ok"] is True
    assert payload["command"] == "project refresh-graph"
    assert captured == {"project_id": 9, "version_id": 12, "branch": "main"}


def test_handle_project_refresh_commit_graph_calls_service(monkeypatch):
    from service.cli.commands import project

    _patch_db(monkeypatch, project)
    monkeypatch.setattr(
        project.project_service,
        "get_project",
        lambda conn, project_id: {"id": project_id, "name": "demo"},
    )
    captured = {}

    def fake_refresh_commit_graph(conn, **kwargs):
        captured.update(kwargs)
        return {"project_id": kwargs["project_id"], "graph_action": "commit_incremental"}

    monkeypatch.setattr(project.project_service, "refresh_commit_graph", fake_refresh_commit_graph)

    payload = project.handle_project_refresh_commit_graph(
        SimpleNamespace(
            command_name="project refresh-commit-graph",
            project_id=9,
            project_name=None,
            branch="main",
            version_id=12,
            commit_sha="a" * 40,
            max_changed_files=25,
        )
    )

    assert payload["ok"] is True
    assert payload["command"] == "project refresh-commit-graph"
    assert captured == {
        "project_id": 9,
        "version_id": 12,
        "branch": "main",
        "commit_sha": "a" * 40,
        "max_changed_files": 25,
    }
