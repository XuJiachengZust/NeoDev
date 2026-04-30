from types import SimpleNamespace


class FakeConn:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

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
            branch="release/x",
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
    assert captured["branch"] == "release/x"
    assert captured["properties"] == {"weight": "3", "reason": "runtime"}


def test_handle_node_add_passes_branch_and_commits(monkeypatch):
    from service.cli.commands import graph

    conn = FakeConn()
    monkeypatch.setattr(graph.psycopg2, "connect", lambda _: conn)
    monkeypatch.setattr(graph, "get_database_url", lambda: "postgresql://test")
    captured = {}

    def fake_create_node(conn, **kwargs):
        captured.update(kwargs)
        return {"node_id": kwargs["node_id"], "type_key": kwargs["type_key"]}

    monkeypatch.setattr(graph.graph_management_service, "create_node", fake_create_node)

    payload = graph.handle_node_add(
        SimpleNamespace(
            command_name="graph node add",
            project_id=1,
            branch="release/x",
            node_id="manual-login",
            type="SERVICE",
            name="Login Service",
            prop=["owner=sec"],
        )
    )

    assert payload["ok"] is True
    assert captured["branch"] == "release/x"
    assert captured["properties"] == {"owner": "sec"}
    assert conn.commits == 1
    assert conn.rollbacks == 0


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
        )
    )

    assert payload["ok"] is True
    assert payload["command"] == "project refresh-graph"
    assert captured == {"project_id": 9, "branch": "main"}
