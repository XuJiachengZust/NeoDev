import sys
from types import SimpleNamespace

from service.services import node_service


class FakeRecord(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class FakeSession:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, params=None, **kwargs):
        self.calls.append({"query": query, "params": params or kwargs})
        return [FakeRecord({"id": "func-fact-1", "label": "Function", "name": "handle", "properties": {}})]


class FakeDriver:
    def __init__(self):
        self.session_obj = FakeSession()
        self.closed = False

    def session(self, database=None):
        return self.session_obj

    def close(self):
        self.closed = True


def test_list_nodes_by_version_uses_snapshot_visible_fact_ids(monkeypatch):
    driver = FakeDriver()

    monkeypatch.setitem(
        sys.modules,
        "neo4j",
        SimpleNamespace(GraphDatabase=SimpleNamespace(driver=lambda uri, auth: driver)),
    )
    monkeypatch.setattr(
        node_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "api", "neo4j_database": "neo4j"},
    )
    monkeypatch.setattr(
        node_service.version_repo,
        "find_by_id",
        lambda conn, version_id: {"id": version_id, "project_id": 7, "branch": "feature/a"},
    )
    monkeypatch.setattr(
        node_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j", "neo4j_user": "neo4j", "neo4j_password": "pw"}, "neo4j"),
    )
    monkeypatch.setattr(
        node_service,
        "branch_snapshot_service",
        type(
            "SnapshotService",
            (),
            {
                "get_current_snapshot": staticmethod(lambda conn, project_id, branch: {"id": 501}),
                "list_fact_ids": staticmethod(lambda conn, snapshot_id: ["file-fact-1", "func-fact-1"]),
            },
        ),
        raising=False,
    )

    result = node_service.list_nodes_by_version(object(), 7, 9, name="han", type_filter="Function")

    call = driver.session_obj.calls[0]
    assert result[0]["id"] == "func-fact-1"
    assert call["params"]["visible_fact_ids"] == ["file-fact-1", "func-fact-1"]
    assert "visible_fact_ids" in call["query"]
    assert "n.branch = $branch" not in call["query"]
    assert driver.closed is True
