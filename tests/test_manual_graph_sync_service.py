class FakeSession:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, **params):
        self.calls.append({"query": query, "params": params})


class FakeDriver:
    def __init__(self):
        self.session_obj = FakeSession()
        self.closed = False

    def session(self, database=None):
        self.database = database
        return self.session_obj

    def close(self):
        self.closed = True


def _patch_driver(monkeypatch, service):
    driver = FakeDriver()
    monkeypatch.setattr(service.project_service, "get_project", lambda conn, project_id: {"id": project_id})
    monkeypatch.setattr(
        service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j", "neo4j_user": "neo4j", "neo4j_password": "pw"}, "neo4j"),
    )
    monkeypatch.setattr(service, "_create_driver", lambda config: driver)
    return driver


def test_sync_node_upserts_code_fact_graph_node(monkeypatch):
    from service.services import manual_graph_sync_service

    driver = _patch_driver(monkeypatch, manual_graph_sync_service)

    manual_graph_sync_service.sync_node(
        object(),
        project_id=3,
        node={"node_id": "manual-login", "type_key": "SERVICE", "name": "Login Service", "properties": {}},
        fact={"fact_id": "manual:3:node:manual-login", "node_type": "Function", "metadata_json": {"source": "manual"}},
    )

    call = driver.session_obj.calls[0]
    assert "MERGE (n:GraphNode:CodeFact" in call["query"]
    assert call["params"]["props"]["id"] == "manual:3:node:manual-login"
    assert call["params"]["props"]["source"] == "manual"
    assert call["params"]["props"]["manual_node_id"] == "manual-login"
    assert driver.closed is True


def test_sync_edge_normalizes_relation_type_and_upserts_relationship(monkeypatch):
    from service.services import manual_graph_sync_service

    driver = _patch_driver(monkeypatch, manual_graph_sync_service)

    manual_graph_sync_service.sync_edge(
        object(),
        project_id=3,
        branch="release/x",
        snapshot_id=501,
        edge={
            "edge_id": "edge-1",
            "from_node_id": "manual-a",
            "to_node_id": "manual-b",
            "type_key": "depends-on",
            "properties": {"weight": "3"},
            "status": "active",
        },
    )

    call = driver.session_obj.calls[0]
    assert "MERGE (a)-[r:DEPENDS_ON {id: $edge_id}]->(b)" in call["query"]
    assert call["params"]["source_fact_id"] == "manual:3:node:manual-a"
    assert call["params"]["target_fact_id"] == "manual:3:node:manual-b"
    assert call["params"]["props"]["branch_name"] == "release/x"
    assert call["params"]["props"]["snapshot_id"] == 501


def test_archive_node_marks_neo4j_node_archived(monkeypatch):
    from service.services import manual_graph_sync_service

    driver = _patch_driver(monkeypatch, manual_graph_sync_service)

    manual_graph_sync_service.archive_node(
        object(),
        project_id=3,
        node={"node_id": "manual-login"},
        fact_id="manual:3:node:manual-login",
    )

    call = driver.session_obj.calls[0]
    assert "MATCH (n:GraphNode {id: $fact_id, project_id: $project_id})" in call["query"]
    assert "SET n.status = 'archived'" in call["query"]
    assert call["params"]["fact_id"] == "manual:3:node:manual-login"


def test_clear_project_graph_deletes_project_graph_nodes(monkeypatch):
    from service.services import manual_graph_sync_service

    driver = _patch_driver(monkeypatch, manual_graph_sync_service)

    manual_graph_sync_service.clear_project_graph(object(), project_id=3)

    call = driver.session_obj.calls[0]
    assert "MATCH (n:GraphNode {project_id: $project_id})" in call["query"]
    assert "DETACH DELETE n" in call["query"]
    assert call["params"]["project_id"] == 3
