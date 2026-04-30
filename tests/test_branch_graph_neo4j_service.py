from gitnexus_parser.graph import create_knowledge_graph


class FakeResult:
    def __init__(self, row=None):
        self._row = row or {"written": 0, "count": 0}

    def single(self):
        return self._row


class FakeTx:
    def __init__(self, session):
        self.session = session

    def run(self, query, **kwargs):
        self.session.calls.append((query, kwargs))
        if "RETURN count(r) AS written" in query:
            if "UNWIND $rels" in query:
                key = "rels"
            elif "UNWIND $roots" in query:
                key = "roots"
            else:
                key = "links"
            return FakeResult({"written": len(kwargs.get(key, []))})
        return FakeResult()


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

    def execute_write(self, fn, **kwargs):
        return fn(FakeTx(self), **kwargs)


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


def test_replace_branch_graph_scopes_nodes_by_project_branch(monkeypatch):
    from service.services import branch_graph_neo4j_service

    driver = FakeDriver()
    graph = create_knowledge_graph()
    graph.addNode({"id": "Folder:src", "label": "Folder", "properties": {"path": "src"}})
    graph.addNode({"id": "File:src/app.py", "label": "File", "properties": {"filePath": "src/app.py"}})
    graph.addNode({"id": "Function:src/app.py:main", "label": "Function", "properties": {"name": "main"}})
    graph.addRelationship(
        {
            "id": "contains:folder-file",
            "sourceId": "Folder:src",
            "targetId": "File:src/app.py",
            "type": "CONTAINS",
        }
    )
    graph.addRelationship(
        {
            "id": "contains:file-function",
            "sourceId": "File:src/app.py",
            "targetId": "Function:src/app.py:main",
            "type": "CONTAINS",
        }
    )

    monkeypatch.setattr(branch_graph_neo4j_service, "_create_driver", lambda config: driver)
    monkeypatch.setattr(
        branch_graph_neo4j_service.doc_code_link_repository,
        "list_active_for_branch",
        lambda conn, project_id, branch_name: [],
    )

    result = branch_graph_neo4j_service.replace_branch_graph(
        conn=object(),
        config={"neo4j_uri": "bolt://neo4j:7687"},
        database=None,
        graph=graph,
        project_id=3,
        branch_name="release/V1",
        graph_id=9,
        head_commit="abc",
    )

    all_calls = [call for session in driver.sessions for call in session.calls]
    delete_call = next(call for call in all_calls if "DETACH DELETE n" in call[0])
    branch_graph_call = next(call for call in all_calls if "MERGE (g:BranchGraph" in call[0])
    root_link_call = next(call for call in all_calls if "UNWIND $roots AS root" in call[0])
    node_calls = [call for call in all_calls if "UNWIND $nodes AS row" in call[0]]
    rel_calls = [call for call in all_calls if "UNWIND $rels AS rel" in call[0]]
    all_queries = "\n".join(call[0] for call in all_calls)

    assert delete_call[1] == {"project_id": 3, "branch_name": "release/V1"}
    assert "MATCH (n:Folder {project_id: $project_id, branch_name: $branch_name})" in all_queries
    assert "MATCH (n:File {project_id: $project_id, branch_name: $branch_name})" in all_queries
    assert "MATCH (n:Function {project_id: $project_id, branch_name: $branch_name})" in all_queries
    assert "MATCH (g:BranchGraph {project_id: $project_id, branch_name: $branch_name})" in all_queries
    assert "GraphNode" not in all_queries
    assert "MERGE (n:Folder {id: row.id})" in all_queries
    assert "MERGE (n:File {id: row.id})" in all_queries
    assert "MERGE (n:CodeNode:Function {id: row.id})" in all_queries
    assert "MERGE (p:Project {project_id: $project_id})" in all_queries
    assert "MERGE (g:BranchGraph {graph_id: $graph_id})" in all_queries
    assert "MATCH (source:Folder {id: rel.source_id})" in all_queries
    assert "MATCH (target:File {id: rel.target_id})" in all_queries
    assert "MATCH (source:File {id: rel.source_id})" in all_queries
    assert "MATCH (target:Function {id: rel.target_id})" in all_queries
    assert "MATCH (target:Folder {id: root.target_id})" in all_queries
    assert branch_graph_call[1] == {
        "project_id": 3,
        "branch_name": "release/V1",
        "graph_id": 9,
        "head_commit": "abc",
    }
    node_ids = {row["id"] for call in node_calls for row in call[1]["nodes"]}
    assert "project:3:branch:release/V1:node:Folder:src" in node_ids
    assert "project:3:branch:release/V1:node:File:src/app.py" in node_ids
    assert "project:3:branch:release/V1:node:Function:src/app.py:main" in node_ids
    node_props = {row["id"]: row["props"] for call in node_calls for row in call[1]["nodes"]}
    assert node_props["project:3:branch:release/V1:node:File:src/app.py"]["branch"] == "release/V1"
    rel_rows = [row for call in rel_calls for row in call[1]["rels"]]
    assert {
        (row["source_label"], row["target_label"], row["source_id"], row["target_id"])
        for row in rel_rows
    } == {
        (
            "Folder",
            "File",
            "project:3:branch:release/V1:node:Folder:src",
            "project:3:branch:release/V1:node:File:src/app.py",
        ),
        (
            "File",
            "Function",
            "project:3:branch:release/V1:node:File:src/app.py",
            "project:3:branch:release/V1:node:Function:src/app.py:main",
        ),
    }
    assert root_link_call[1]["roots"] == [
            {
                "id": "project:3:branch:release/V1:branch_graph:9:contains:Folder:src",
                "target_id": "project:3:branch:release/V1:node:Folder:src",
                "target_label": "Folder",
                "props": {
                "project_id": 3,
                "branch_name": "release/V1",
                "branch": "release/V1",
                "graph_id": 9,
                "type": "CONTAINS",
            },
        }
    ]
    assert result["nodes_written"] == 3
    assert result["relationships_written"] == 3
    assert driver.closed is True


def test_rebuild_doc_code_links_targets_real_nodes(monkeypatch):
    from service.services import branch_graph_neo4j_service

    driver = FakeDriver()
    monkeypatch.setattr(
        branch_graph_neo4j_service.doc_code_link_repository,
        "list_active_for_branch",
        lambda conn, project_id, branch_name: [
            {
                "id": 7,
                "doc_id": "doc-1",
                "doc_node_id": "section-1",
                "code_locator_json": {"code_node_id": "Function:src/app.py:main"},
                "relation_type": "IMPLEMENTS",
                "source": "manual",
                "confidence": 1.0,
            }
        ],
    )

    written = branch_graph_neo4j_service._rebuild_doc_code_links(
        object(),
        driver,
        database=None,
        project_id=3,
        branch_name="release/V1",
        graph_id=9,
    )

    all_calls = [call for session in driver.sessions for call in session.calls]
    link_call = next(call for call in all_calls if "UNWIND $links AS link" in call[0])

    assert written == 1
    assert "MATCH (code:CodeNode {id: link.scoped_code_node_id})" in link_call[0]
    assert link_call[1]["links"][0]["code_label"] == "Function"
    assert "GraphNode" not in link_call[0]
