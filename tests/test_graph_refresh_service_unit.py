import pytest


class FakeRecord(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class FakeSession:
    def __init__(self, records):
        self.records = records
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, **params):
        self.calls.append({"query": query, "params": params})
        return self.records


class FakeDriver:
    def __init__(self, records):
        self.records = records
        self.sessions = []
        self.closed = False

    def session(self, database=None):
        session = FakeSession(self.records)
        self.sessions.append({"database": database, "session": session})
        return session

    def close(self):
        self.closed = True


def _patch_valid_scope(monkeypatch, driver):
    from service.services import graph_refresh_service

    monkeypatch.setattr(
        graph_refresh_service.graph_query_service,
        "_validate_scope",
        lambda conn, product_version_id, project_id, branch: {
            "product": {"id": 7, "code": "UNIT"},
            "version": {"id": product_version_id, "product_id": 7, "version_name": "V1.0"},
            "project": {"id": project_id, "name": "api-service"},
            "branch": "release/V1.0",
        },
    )
    monkeypatch.setattr(
        graph_refresh_service,
        "_load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j", "neo4j_user": "neo4j", "neo4j_password": "pw"}, "neo4j"),
    )
    monkeypatch.setattr(
        graph_refresh_service,
        "_create_neo4j_driver",
        lambda config: driver,
    )


def test_refresh_nodes_marks_scoped_nodes(monkeypatch):
    from service.services import graph_refresh_service

    driver = FakeDriver([FakeRecord({"updated_count": 2})])
    _patch_valid_scope(monkeypatch, driver)

    result = graph_refresh_service.refresh_nodes(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/V1.0",
        node_ids=["Function:auth:login", "Function:auth:login"],
        paths=["src/auth.py"],
        commit_sha="a" * 40,
    )

    assert result["project_id"] == 11
    assert result["branch"] == "release/V1.0"
    assert result["refresh_scope"] == {
        "product_version_id": 23,
        "project_id": 11,
        "branch": "release/V1.0",
        "node_ids": ["Function:auth:login"],
        "paths": ["src/auth.py"],
        "commit_sha": "a" * 40,
    }
    assert result["graph_nodes_updated"] == 2
    assert result["ai_descriptions_updated"] == 0
    assert result["embeddings_reused"] == 0
    assert result["embeddings_regenerated"] == 0
    assert result["status"] == "completed"
    assert result["semantic_status"] == "refresh_requested"
    assert result["degraded_reasons"] == []
    call = driver.sessions[0]["session"].calls[0]
    assert call["params"]["node_ids"] == ["Function:auth:login"]
    assert call["params"]["paths"] == ["src/auth.py"]
    assert call["params"]["commit_sha"] == "a" * 40
    assert driver.closed is True


def test_refresh_nodes_returns_degraded_when_neo4j_missing(monkeypatch):
    from service.services import graph_refresh_service

    monkeypatch.setattr(
        graph_refresh_service.graph_query_service,
        "_validate_scope",
        lambda conn, product_version_id, project_id, branch: {
            "product": {"id": 7, "code": "UNIT"},
            "version": {"id": product_version_id, "product_id": 7, "version_name": "V1.0"},
            "project": {"id": project_id, "name": "api-service"},
            "branch": "release/V1.0",
        },
    )
    monkeypatch.setattr(
        graph_refresh_service,
        "_load_neo4j_config",
        lambda project: (None, None),
    )

    result = graph_refresh_service.refresh_nodes(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/V1.0",
    )

    assert result["status"] == "degraded"
    assert result["graph_nodes_updated"] == 0
    assert result["refresh_scope"]["node_ids"] == []
    assert result["refresh_scope"]["paths"] == []
    assert result["degraded_reasons"][0]["reason"] == "neo4j_not_configured"


def test_refresh_nodes_rejects_blank_path():
    from service.services import graph_refresh_service

    with pytest.raises(graph_refresh_service.GraphRefreshError) as raised:
        graph_refresh_service.refresh_nodes(
            object(),
            product_version_id=23,
            project_id=11,
            branch="release/V1.0",
            paths=[""],
        )

    assert raised.value.category == "invalid_argument"
