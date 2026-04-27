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
    from service.services import graph_semantic_search_service

    monkeypatch.setattr(
        graph_semantic_search_service.product_version_service,
        "get_version",
        lambda conn, version_id: {"id": version_id, "product_id": 7, "version_name": "V1.0"},
    )
    monkeypatch.setattr(
        graph_semantic_search_service.product_version_service,
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
        graph_semantic_search_service.project_service,
        "get_project",
        lambda conn, project_id: {
            "id": project_id,
            "name": "api-service",
            "neo4j_database": "neo4j",
        },
    )
    monkeypatch.setattr(
        graph_semantic_search_service,
        "_load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j", "neo4j_user": "neo4j", "neo4j_password": "pw"}, "neo4j"),
    )
    monkeypatch.setattr(
        graph_semantic_search_service,
        "_create_neo4j_driver",
        lambda config: driver,
    )


def test_semantic_search_degrades_to_text_search_with_version_scope(monkeypatch):
    from service.services import graph_semantic_search_service

    driver = FakeDriver(
        [
            FakeRecord(
                {
                    "entity_id": "Function:auth:login",
                    "entity_type": "Function",
                    "name": "login",
                    "file_path": "src/auth.py",
                    "description": "Validate user login token",
                    "score": 0.4,
                    "semantic_status": "degraded",
                }
            )
        ]
    )
    _patch_valid_scope(monkeypatch, driver)
    monkeypatch.setattr(
        graph_semantic_search_service.llm_client,
        "embedding_completion",
        lambda query: (_ for _ in ()).throw(ValueError("missing api key")),
    )

    result = graph_semantic_search_service.semantic_search(
        object(),
        product_version_id=23,
        query="login token",
        top_k=3,
    )

    assert result["product_version_id"] == 23
    assert result["query"] == "login token"
    assert result["top_k"] == 3
    assert result["semantic_status"] == "degraded"
    assert result["scope"] == [
        {"project_id": 11, "project_name": "api-service", "branch": "release/V1.0"}
    ]
    assert result["results"] == [
        {
            "product_version_id": 23,
            "project_id": 11,
            "project_name": "api-service",
            "branch": "release/V1.0",
            "entity_type": "Function",
            "entity_id": "Function:auth:login",
            "file_path": "src/auth.py",
            "description": "Validate user login token",
            "score": 0.4,
            "semantic_status": "degraded",
        }
    ]
    call = driver.sessions[0]["session"].calls[0]
    assert call["params"]["project_id"] == 11
    assert call["params"]["branch"] == "release/V1.0"
    assert call["params"]["limit"] == 3
    assert "vector.similarity" not in call["query"]
    assert driver.closed is True


def test_semantic_search_rejects_unbound_product_version(monkeypatch):
    from service.services import graph_semantic_search_service

    monkeypatch.setattr(
        graph_semantic_search_service.product_version_service,
        "get_version",
        lambda conn, version_id: {"id": version_id, "product_id": 7, "version_name": "V1.0"},
    )
    monkeypatch.setattr(
        graph_semantic_search_service.product_version_service,
        "list_branches",
        lambda conn, version_id: [],
    )

    with pytest.raises(graph_semantic_search_service.GraphSemanticSearchError) as exc_info:
        graph_semantic_search_service.semantic_search(
            object(),
            product_version_id=23,
            query="anything",
        )

    assert exc_info.value.category == "invalid_scope"
    assert exc_info.value.details == {"product_version_id": 23}


def test_semantic_search_validates_query_and_top_k():
    from service.services import graph_semantic_search_service

    with pytest.raises(graph_semantic_search_service.GraphSemanticSearchError) as query_exc:
        graph_semantic_search_service.semantic_search(object(), product_version_id=23, query=" ")
    assert query_exc.value.category == "invalid_argument"

    with pytest.raises(graph_semantic_search_service.GraphSemanticSearchError) as top_k_exc:
        graph_semantic_search_service.semantic_search(
            object(),
            product_version_id=23,
            query="login",
            top_k=0,
        )
    assert top_k_exc.value.category == "invalid_argument"
