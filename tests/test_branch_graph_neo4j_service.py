from types import SimpleNamespace

from gitnexus_parser.graph import create_knowledge_graph


class FakeResult:
    def __init__(self, row=None):
        self._row = row or {"written": 0, "count": 0}

    def single(self):
        return self._row

    def __iter__(self):
        return iter([])


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
    def __init__(self, row=None):
        self.calls = []
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, **kwargs):
        self.calls.append((query, kwargs))
        return FakeResult(self.row)

    def execute_write(self, fn, **kwargs):
        return fn(FakeTx(self), **kwargs)


class FakeDriver:
    def __init__(self, row=None):
        self.sessions = []
        self.closed = False
        self.row = row

    def session(self, database=None):
        session = FakeSession(self.row)
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
    monkeypatch.setattr(
        branch_graph_neo4j_service.graph_management_repository,
        "list_active_nodes_for_branch",
        lambda conn, project_id, branch_name: [],
    )
    monkeypatch.setattr(
        branch_graph_neo4j_service.graph_management_repository,
        "list_active_edges_for_branch",
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
        version_scope={
            "product_version_id": 23,
            "product_name": "NeoDev SP",
            "version_name": "V1",
            "project_name": "NeoDev",
        },
    )

    all_calls = [call for session in driver.sessions for call in session.calls]
    delete_call = next(call for call in all_calls if "DETACH DELETE n" in call[0])
    branch_graph_call = next(call for call in all_calls if "MERGE (g:BranchGraph" in call[0])
    root_link_call = next(call for call in all_calls if "UNWIND $roots AS root" in call[0])
    node_calls = [call for call in all_calls if "UNWIND $nodes AS row" in call[0]]
    rel_calls = [call for call in all_calls if "UNWIND $rels AS rel" in call[0]]
    all_queries = "\n".join(call[0] for call in all_calls)

    assert "ON (n.product_name, n.version_name, n.project_name, n.branch_name)" in all_queries
    assert "CREATE INDEX code_node_scope_file_path IF NOT EXISTS FOR (n:CodeNode) ON (n.product_name, n.version_name, n.project_name, n.branch_name, n.file_path)" in all_queries
    assert "CREATE INDEX code_node_scope_name IF NOT EXISTS FOR (n:CodeNode) ON (n.product_name, n.version_name, n.project_name, n.branch_name, n.name)" in all_queries
    assert "CREATE INDEX code_node_scope_qualified_name IF NOT EXISTS FOR (n:CodeNode) ON (n.product_name, n.version_name, n.project_name, n.branch_name, n.qualified_name)" in all_queries
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
        "product_version_id": 23,
        "product_name": "NeoDev SP",
        "version_name": "V1",
        "project_name": "NeoDev",
    }
    node_ids = {row["id"] for call in node_calls for row in call[1]["nodes"]}
    assert "project:3:branch:release/V1:node:Folder:src" in node_ids
    assert "project:3:branch:release/V1:node:File:src/app.py" in node_ids
    assert "project:3:branch:release/V1:node:Function:src/app.py:main" in node_ids
    node_props = {row["id"]: row["props"] for call in node_calls for row in call[1]["nodes"]}
    assert node_props["project:3:branch:release/V1:node:File:src/app.py"]["branch"] == "release/V1"
    assert node_props["project:3:branch:release/V1:node:File:src/app.py"]["product_version_id"] == 23
    assert node_props["project:3:branch:release/V1:node:File:src/app.py"]["product_name"] == "NeoDev SP"
    assert node_props["project:3:branch:release/V1:node:File:src/app.py"]["version_name"] == "V1"
    assert node_props["project:3:branch:release/V1:node:File:src/app.py"]["project_name"] == "NeoDev"
    rel_rows = [row for call in rel_calls for row in call[1]["rels"]]
    assert rel_rows[0]["props"]["branch_name"] == "release/V1"
    assert rel_rows[0]["props"]["product_version_id"] == 23
    assert rel_rows[0]["props"]["product_name"] == "NeoDev SP"
    assert rel_rows[0]["props"]["version_name"] == "V1"
    assert rel_rows[0]["props"]["project_name"] == "NeoDev"
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
                "product_version_id": 23,
                "product_name": "NeoDev SP",
                "version_name": "V1",
                "project_name": "NeoDev",
                "type": "CONTAINS",
            },
        }
    ]
    assert result["nodes_written"] == 3
    assert result["relationships_written"] == 3
    assert driver.closed is True


def test_replace_branch_graph_projects_manual_cross_project_edges(monkeypatch):
    from service.services import branch_graph_neo4j_service

    driver = FakeDriver()
    graph = create_knowledge_graph()
    monkeypatch.setattr(branch_graph_neo4j_service, "_create_driver", lambda config: driver)
    monkeypatch.setattr(
        branch_graph_neo4j_service.doc_code_link_repository,
        "list_active_for_branch",
        lambda conn, project_id, branch_name: [],
    )
    monkeypatch.setattr(
        branch_graph_neo4j_service,
        "graph_management_repository",
        SimpleNamespace(
            list_active_nodes_for_branch=lambda conn, project_id, branch_name: [
                {
                    "project_id": 9,
                    "node_id": "Function:src/views/business/tagManage/api.ts:addTag",
                    "type_key": "Function",
                    "name": "addTag",
                    "properties": {
                        "api_id": "CreateTag",
                        "file_path": "src/views/business/tagManage/api.ts",
                    },
                    "source": "manual",
                    "file_path": None,
                    "status": "active",
                }
            ],
            list_active_edges_for_branch=lambda conn, project_id, branch_name: [
                {
                    "project_id": 9,
                    "edge_id": "calls_tag_addTag_add",
                    "from_node_id": "Function:src/views/business/tagManage/api.ts:addTag",
                    "to_node_id": "Method:src/main/java/com/dbapp/dsc/controller/TagController.java:add",
                    "from_project_id": 9,
                    "to_project_id": 8,
                    "type_key": "CALLS",
                    "properties": {
                        "api_id": "CreateTag",
                        "http_path": "/webapi/tag/add",
                        "http_method": "POST",
                        "gateway_json": "api/apis/CreateTag.json",
                    },
                    "status": "active",
                }
            ],
        ),
        raising=False,
    )

    result = branch_graph_neo4j_service.replace_branch_graph(
        conn=object(),
        config={"neo4j_uri": "bolt://neo4j:7687"},
        database=None,
        graph=graph,
        project_id=9,
        branch_name="release/V2.0R26C01",
        graph_id=77,
        head_commit="abc",
        version_scope={
            "product_version_id": 23,
            "product_name": "DSC",
            "version_name": "V2.0R26C01",
            "project_name": "dsc-front",
        },
    )

    all_calls = [call for session in driver.sessions for call in session.calls]
    node_rows = [row for call in all_calls if "UNWIND $nodes AS row" in call[0] for row in call[1]["nodes"]]
    rel_rows = [row for call in all_calls if "UNWIND $rels AS rel" in call[0] for row in call[1]["rels"]]

    manual_node = next(row for row in node_rows if row["props"].get("source") == "manual")
    manual_rel = next(row for row in rel_rows if row["id"] == "project:9:branch:release/V2.0R26C01:node:calls_tag_addTag_add")

    assert manual_node["id"] == "project:9:branch:release/V2.0R26C01:node:Function:src/views/business/tagManage/api.ts:addTag"
    assert manual_node["props"]["name"] == "addTag"
    assert manual_node["props"]["file_path"] == "src/views/business/tagManage/api.ts"
    assert manual_node["props"]["api_id"] == "CreateTag"
    assert manual_rel["source_id"] == "project:9:branch:release/V2.0R26C01:node:Function:src/views/business/tagManage/api.ts:addTag"
    assert manual_rel["target_id"] == "project:8:branch:release/V2.0R26C01:node:Method:src/main/java/com/dbapp/dsc/controller/TagController.java:add"
    assert manual_rel["relationship_type"] == "CALLS"
    assert manual_rel["props"]["api_id"] == "CreateTag"
    assert manual_rel["props"]["http_path"] == "/webapi/tag/add"
    assert manual_rel["props"]["gateway_json"] == "api/apis/CreateTag.json"
    assert result["manual_nodes_written"] == 1
    assert result["manual_relationships_written"] == 1


def test_entity_context_filters_by_name_scope(monkeypatch):
    from service.services import branch_graph_neo4j_service

    driver = FakeDriver(
        {
            "entity": {"id": "project:3:branch:release/V1:node:Function:src/app.py:main", "node_id": "Function:src/app.py:main"},
            "entity_labels": ["CodeNode", "Function"],
            "paths": [],
        }
    )
    monkeypatch.setattr(branch_graph_neo4j_service, "_create_driver", lambda config: driver)

    branch_graph_neo4j_service.entity_context(
        config={"neo4j_uri": "bolt://neo4j:7687"},
        database=None,
        project_id=3,
        project_name="NeoDev",
        branch_name="release/V1",
        product_name="NeoDev SP",
        version_name="V1",
        entity_id="Function:src/app.py:main",
        depth=2,
    )

    query, params = driver.sessions[0].calls[0]
    assert "MATCH (entity {" in query
    assert "entity.product_name = $product_name" in query
    assert "entity.version_name = $version_name" in query
    assert "entity.project_name = $project_name" in query
    assert "entity.branch_name = $branch_name" in query
    assert "r.product_name = $product_name" in query
    assert "r.version_name = $version_name" in query
    assert "r.project_name = $project_name" in query
    assert "r.branch_name = $branch_name" in query
    assert params["product_name"] == "NeoDev SP"
    assert params["version_name"] == "V1"
    assert params["project_name"] == "NeoDev"
    assert params["branch_name"] == "release/V1"
    assert params["project_id"] == 3


def test_get_chain_filters_by_name_scope(monkeypatch):
    from service.services import branch_graph_neo4j_service

    driver = FakeDriver(
        {
            "start": {"id": "project:3:branch:release/V1:node:Function:src/app.py:main", "node_id": "Function:src/app.py:main"},
            "start_labels": ["CodeNode", "Function"],
            "paths": [],
        }
    )
    monkeypatch.setattr(branch_graph_neo4j_service, "_create_driver", lambda config: driver)

    branch_graph_neo4j_service.get_chain(
        config={"neo4j_uri": "bolt://neo4j:7687"},
        database=None,
        project_id=3,
        project_name="NeoDev",
        branch_name="release/V1",
        product_name="NeoDev SP",
        version_name="V1",
        locator={"type": "symbol", "value": "main"},
        depth=2,
    )

    query, params = driver.sessions[0].calls[0]
    assert "MATCH (start {" in query
    assert "start.product_name = $product_name" in query
    assert "start.version_name = $version_name" in query
    assert "start.project_name = $project_name" in query
    assert "start.branch_name = $branch_name" in query
    assert "r.product_name = $product_name" in query
    assert "r.version_name = $version_name" in query
    assert "r.project_name = $project_name" in query
    assert "r.branch_name = $branch_name" in query
    assert params["product_name"] == "NeoDev SP"
    assert params["version_name"] == "V1"
    assert params["project_name"] == "NeoDev"
    assert params["branch_name"] == "release/V1"
    assert params["project_id"] == 3


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


def test_upsert_doc_code_link_writes_single_link_when_code_node_exists(monkeypatch):
    from service.services import branch_graph_neo4j_service

    class LinkTx(FakeTx):
        def run(self, query, **kwargs):
            self.session.calls.append((query, kwargs))
            if "RETURN count(code) AS count" in query:
                return FakeResult({"count": 1})
            if "RETURN count(r) AS written" in query:
                return FakeResult({"written": 1})
            return FakeResult()

    class LinkSession(FakeSession):
        def execute_write(self, fn, **kwargs):
            return fn(LinkTx(self), **kwargs)

    class LinkDriver(FakeDriver):
        def session(self, database=None):
            session = LinkSession()
            self.sessions.append(session)
            return session

    driver = LinkDriver()
    monkeypatch.setattr(branch_graph_neo4j_service, "_create_driver", lambda config: driver)

    result = branch_graph_neo4j_service.upsert_doc_code_link(
        config={"neo4j_uri": "bolt://neo4j:7687"},
        database=None,
        project_id=3,
        branch_name="release/V1",
        graph_id=9,
        link={
            "id": 7,
            "doc_id": "doc-1",
            "doc_node_id": "section-1",
            "relation_type": "IMPLEMENTS",
            "code_locator_json": {"code_node_id": "Function:src/app.py:main"},
            "source": "manual",
            "confidence": 0.9,
        },
        version_scope={
            "product_version_id": 23,
            "product_name": "NeoDev SP",
            "version_name": "V1",
            "project_name": "NeoDev",
        },
    )

    all_calls = [call for session in driver.sessions for call in session.calls]
    assert result == {
        "status": "linked",
        "written": 1,
        "code_node_id": "Function:src/app.py:main",
        "scoped_code_node_id": "project:3:branch:release/V1:node:Function:src/app.py:main",
    }
    assert any("MATCH (code:CodeNode {id: $scoped_code_node_id})" in call[0] for call in all_calls)
    assert any("MERGE (doc)-[r:LINKS_TO_CODE {id: link.id}]->(code)" in call[0] for call in all_calls)


def test_upsert_doc_code_link_uses_version_scoped_document_node(monkeypatch):
    from service.services import branch_graph_neo4j_service

    class LinkTx(FakeTx):
        def run(self, query, **kwargs):
            self.session.calls.append((query, kwargs))
            if "RETURN count(code) AS count" in query:
                return FakeResult({"count": 1})
            if "RETURN count(r) AS written" in query:
                return FakeResult({"written": 1})
            return FakeResult()

    class LinkSession(FakeSession):
        def execute_write(self, fn, **kwargs):
            return fn(LinkTx(self), **kwargs)

    class LinkDriver(FakeDriver):
        def session(self, database=None):
            session = LinkSession()
            self.sessions.append(session)
            return session

    driver = LinkDriver()
    monkeypatch.setattr(branch_graph_neo4j_service, "_create_driver", lambda config: driver)

    branch_graph_neo4j_service.upsert_doc_code_link(
        config={"neo4j_uri": "bolt://neo4j:7687"},
        database=None,
        project_id=3,
        branch_name="release/V1",
        graph_id=9,
        link={
            "id": 7,
            "doc_id": "doc-1",
            "doc_node_id": "section-1",
            "relation_type": "IMPLEMENTS",
            "code_locator_json": {"code_node_id": "Function:src/app.py:main"},
        },
        version_scope={
            "product_version_id": 23,
            "product_name": "NeoDev SP",
            "version_name": "V1",
            "project_name": "NeoDev",
        },
    )

    all_calls = [call for session in driver.sessions for call in session.calls]
    link_call = next(call for call in all_calls if "UNWIND $links AS link" in call[0])
    link = link_call[1]["links"][0]

    assert "MERGE (doc:Document {doc_id: link.doc_id, product_version_id: link.product_version_id})" in link_call[0]
    assert "doc.product_name = link.product_name" in link_call[0]
    assert "doc.version_name = link.version_name" in link_call[0]
    assert link["product_version_id"] == 23
    assert link["product_name"] == "NeoDev SP"
    assert link["version_name"] == "V1"


def test_upsert_doc_code_link_reports_missing_code_node(monkeypatch):
    from service.services import branch_graph_neo4j_service

    driver = FakeDriver()
    monkeypatch.setattr(branch_graph_neo4j_service, "_create_driver", lambda config: driver)

    result = branch_graph_neo4j_service.upsert_doc_code_link(
        config={"neo4j_uri": "bolt://neo4j:7687"},
        database=None,
        project_id=3,
        branch_name="release/V1",
        graph_id=9,
        link={
            "id": 7,
            "doc_id": "doc-1",
            "code_locator_json": {"code_node_id": "Function:missing"},
        },
    )

    assert result["status"] == "code_node_not_found"
    assert result["written"] == 0


def test_delete_doc_code_link_removes_relationship(monkeypatch):
    from service.services import branch_graph_neo4j_service

    class DeleteTx(FakeTx):
        def run(self, query, **kwargs):
            self.session.calls.append((query, kwargs))
            if "RETURN count(r) AS deleted" in query:
                return FakeResult({"deleted": 1})
            return FakeResult()

    class DeleteSession(FakeSession):
        def execute_write(self, fn, **kwargs):
            return fn(DeleteTx(self), **kwargs)

    class DeleteDriver(FakeDriver):
        def session(self, database=None):
            session = DeleteSession()
            self.sessions.append(session)
            return session

    driver = DeleteDriver()
    monkeypatch.setattr(branch_graph_neo4j_service, "_create_driver", lambda config: driver)

    result = branch_graph_neo4j_service.delete_doc_code_link(
        config={"neo4j_uri": "bolt://neo4j:7687"},
        database=None,
        link_id=7,
    )

    all_calls = [call for session in driver.sessions for call in session.calls]
    assert result == {"status": "deleted", "deleted": 1}
    assert any("MATCH (:Document)-[r:LINKS_TO_CODE {id: $relationship_id}]->()" in call[0] for call in all_calls)
