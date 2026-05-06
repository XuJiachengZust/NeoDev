from service.services import doc_graph_service


class FakeResult:
    def single(self):
        return {}


class FakeSession:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return FakeResult()


class FakeDriver:
    def __init__(self):
        self.sessions = []
        self.closed = False

    def session(self, database=None):
        session = FakeSession()
        self.sessions.append(session)
        return session

    def close(self):
        self.closed = True


def test_upsert_document_graph_links_document_project_by_repo_url(monkeypatch):
    driver = FakeDriver()
    monkeypatch.setattr(
        doc_graph_service,
        "_load_config",
        lambda: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(doc_graph_service, "_create_driver", lambda config: driver)
    monkeypatch.setattr(
        doc_graph_service.project_repository,
        "list_all",
        lambda conn: [
            {
                "id": 4,
                "name": "das-docs",
                "repo_path": "git@example.com:aidsc/das-docs.git",
                "repo_url": "git@example.com:aidsc/das-docs.git",
                "product_id": 1,
            }
        ],
    )

    result = doc_graph_service.upsert_document_graph(
        object(),
        binding={
            "id": 1,
            "product_id": 1,
            "repo_path": "/data/requirement_docs/das-docs",
            "repo_url": "git@example.com:aidsc/das-docs.git",
        },
        document={
            "id": 42,
            "doc_id": "DSC-DOC-0001",
            "title": "Doc",
            "doc_type": "prd",
            "relative_path": "prd/overview.md",
            "status": "active",
            "content_hash": "hash",
            "relations_json": {"target": []},
        },
    )

    all_calls = [call for session in driver.sessions for call in session.calls]
    all_queries = "\n".join(call[0] for call in all_calls)
    project_link_call = next(call for call in all_calls if "HAS_DOCUMENT" in call[0])

    assert result == {"status": "updated", "project_id": 4}
    assert "MERGE (p:Project {project_id: $project_id})" in all_queries
    assert "MERGE (p)-[r:HAS_DOCUMENT" in all_queries
    assert project_link_call[1]["project_id"] == 4
    assert project_link_call[1]["document_id"] == 42
    assert project_link_call[1]["doc_binding_id"] == 1
    assert project_link_call[1]["doc_id"] == "DSC-DOC-0001"
    assert driver.closed is True


def test_resolve_document_project_falls_back_to_binding_directory_name(monkeypatch):
    monkeypatch.setattr(
        doc_graph_service.project_repository,
        "list_all",
        lambda conn: [
            {
                "id": 4,
                "name": "das-docs",
                "repo_path": "",
                "repo_url": "",
                "product_id": 1,
            }
        ],
    )

    project = doc_graph_service.resolve_document_project(
        object(),
        {
            "product_id": 1,
            "repo_path": "/data/requirement_docs/das-docs",
            "repo_url": "",
        },
    )

    assert project["id"] == 4
