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
                "branch": "release/V1.0",
            }
        ],
    )
    monkeypatch.setattr(
        graph_query_service.version_repo,
        "find_by_project_and_branch",
        lambda conn, project_id, branch: {
            "id": 5,
            "project_id": project_id,
            "branch": branch,
            "last_parsed_commit": "a" * 40,
        },
    )
    monkeypatch.setattr(
        graph_query_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j", "neo4j_user": "neo4j", "neo4j_password": "pw"}, "neo4j"),
    )
    monkeypatch.setattr(
        graph_query_service,
        "_create_neo4j_driver",
        lambda config: driver,
    )
    monkeypatch.setattr(
        graph_query_service,
        "branch_snapshot_service",
        type(
            "SnapshotService",
            (),
            {
                "get_current_snapshot": staticmethod(
                    lambda conn, project_id, branch: {
                        "id": 501,
                        "head_commit": "c" * 40,
                        "last_parsed_commit": "c" * 40,
                        "created_from_action": "incremental",
                    }
                ),
                "list_entries": staticmethod(
                    lambda conn, snapshot_id: [
                        {"file_node_id": "file-fact-auth", "file_path": "src/auth.py"}
                    ]
                ),
            },
        ),
        raising=False,
    )


def test_entity_context_returns_scoped_neighbors(monkeypatch):
    from service.services import graph_query_service

    driver = FakeDriver(
        [
            FakeRecord(
                {
                    "source_node": {
                        "id": "Function:auth:login",
                        "label": "Function",
                        "name": "login",
                        "file_path": "src/auth.py",
                        "description": "Validate token",
                    },
                    "neighbors": [
                        {
                            "id": "File:src/auth.py",
                            "label": "File",
                            "name": "auth.py",
                            "file_path": "src/auth.py",
                            "description": "",
                        }
                    ],
                    "edges": [
                        {
                            "source": "File:src/auth.py",
                            "target": "Function:auth:login",
                            "type": "DEFINES",
                            "direction": "inbound",
                        }
                    ],
                }
            )
        ]
    )
    _patch_valid_scope(monkeypatch, driver)

    result = graph_query_service.entity_context(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/V1.0",
        entity_id="Function:auth:login",
        depth=1,
    )

    assert result["product_version_id"] == 23
    assert result["project_id"] == 11
    assert result["branch"] == "release/V1.0"
    assert result["depth"] == 1
    assert result["entity"]["entity_id"] == "Function:auth:login"
    assert result["entity"]["entity_type"] == "Function"
    assert result["neighbors"][0]["entity_id"] == "File:src/auth.py"
    assert result["edges"] == [
        {
            "source": "File:src/auth.py",
            "target": "Function:auth:login",
            "type": "DEFINES",
            "direction": "inbound",
        }
    ]
    call = driver.sessions[0]["session"].calls[0]
    assert call["params"]["entity_id"] == "Function:auth:login"
    assert call["params"]["project_id"] == 11
    assert call["params"]["branch"] == "release/V1.0"
    assert call["params"]["visible_file_ids"] == ["file-fact-auth"]
    assert "visible_file_ids" in call["query"]
    assert "node.branch = $branch" not in call["query"]
    assert driver.closed is True


def test_get_chain_returns_nodes_edges_and_commit_scope(monkeypatch):
    from service.services import graph_query_service

    driver = FakeDriver(
        [
            FakeRecord(
                {
                    "start_node": {
                        "id": "Function:auth:login",
                        "label": "Function",
                        "name": "login",
                        "file_path": "src/auth.py",
                        "description": "Validate token",
                    },
                    "nodes": [
                        {
                            "id": "Function:auth:login",
                            "label": "Function",
                            "name": "login",
                            "file_path": "src/auth.py",
                            "description": "Validate token",
                        },
                        {
                            "id": "Function:token:decode",
                            "label": "Function",
                            "name": "decode",
                            "file_path": "src/token.py",
                            "description": "Decode token",
                        },
                    ],
                    "edges": [
                        {
                            "source": "Function:auth:login",
                            "target": "Function:token:decode",
                            "type": "CALLS",
                            "direction": "outbound",
                        }
                    ],
                    "affected_commits": ["b" * 40],
                }
            )
        ]
    )
    _patch_valid_scope(monkeypatch, driver)
    monkeypatch.setattr(
        graph_query_service.branch_snapshot_service,
        "get_current_snapshot",
        lambda conn, project_id, branch: {
            "id": 501,
            "head_commit": "c" * 40,
            "last_parsed_commit": "c" * 40,
            "created_from_action": "incremental",
        },
    )
    monkeypatch.setattr(
        graph_query_service.branch_snapshot_service,
        "list_entries",
        lambda conn, snapshot_id: [
            {"file_node_id": "file-fact-auth", "file_path": "src/auth.py"}
        ],
    )

    result = graph_query_service.get_chain(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/V1.0",
        start_node="Function:auth:login",
        depth=2,
    )

    assert result["start_node"]["entity_id"] == "Function:auth:login"
    assert result["snapshot_id"] == 501
    assert result["branch"] == "release/V1.0"
    assert result["head_commit"] == "c" * 40
    assert result["depth"] == 2
    assert [node["entity_id"] for node in result["nodes"]] == [
        "Function:auth:login",
        "Function:token:decode",
    ]
    assert result["edges"][0]["type"] == "CALLS"
    assert result["affected_commits"] == ["b" * 40]
    assert result["path_summary"] == [
        "Function:auth:login -[CALLS]-> Function:token:decode"
    ]
    call = driver.sessions[0]["session"].calls[0]
    assert call["params"]["start_node"] == "Function:auth:login"
    assert call["params"]["visible_file_ids"] == ["file-fact-auth"]
    assert "1..2" in call["query"]
    assert "node.branch = $branch" not in call["query"]


def test_get_chain_requires_exactly_one_start_locator(monkeypatch):
    from service.services import graph_query_service

    _patch_valid_scope(monkeypatch, FakeDriver([]))

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

    _patch_valid_scope(monkeypatch, FakeDriver([]))

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
