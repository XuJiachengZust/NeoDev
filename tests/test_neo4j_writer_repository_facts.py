from gitnexus_parser.neo4j_writer import ensure_constraints, write_graph
from gitnexus_parser.graph.types import NodeLabel
from typing import get_args


class FakeResult:
    def __init__(self, written=1):
        self.written = written

    def single(self):
        return {"written": self.written}


class FakeTx:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append({"query": query, "params": params})
        if "rels" in params:
            return FakeResult(len(params["rels"]))
        return FakeResult()


class FakeSession:
    def __init__(self):
        self.calls = []
        self.transactions = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, query, **params):
        self.calls.append({"query": query, "params": params})
        return FakeResult()

    def execute_write(self, fn):
        tx = FakeTx()
        self.transactions.append(tx)
        return fn(tx)


class FakeDriver:
    def __init__(self):
        self.sessions = []

    def session(self, database=None):
        session = FakeSession()
        self.sessions.append(session)
        return session


class FakeGraph:
    def iterNodes(self):
        yield {
            "id": "file-fact-1",
            "label": "File",
            "properties": {
                "project_id": 11,
                "filePath": "src/a.py",
                "file_content_hash": "h1",
            },
        }
        yield {
            "id": "func-fact-1",
            "label": "Function",
            "properties": {
                "project_id": 11,
                "filePath": "src/a.py",
                "name": "handle",
                "file_content_hash": "h1",
            },
        }

    def iterRelationships(self):
        yield {
            "id": "rel-1",
            "sourceId": "file-fact-1",
            "targetId": "func-fact-1",
            "type": "DEFINES",
            "confidence": 1.0,
            "reason": "",
        }


def test_constraints_use_id_only_not_branch_key():
    driver = FakeDriver()

    ensure_constraints(driver)

    queries = [call["query"] for call in driver.sessions[0].calls]
    assert any("REQUIRE n.id IS UNIQUE" in query for query in queries)
    assert all("n.branch" not in query for query in queries)


def test_constraints_cover_all_declared_node_labels():
    driver = FakeDriver()

    ensure_constraints(driver)

    queries = [call["query"] for call in driver.sessions[0].calls]
    constrained_labels = {
        query.split("FOR (n:", 1)[1].split(")", 1)[0]
        for query in queries
    }
    assert set(get_args(NodeLabel)).issubset(constrained_labels)


def test_write_graph_merges_repository_fact_nodes_without_branch_identity():
    driver = FakeDriver()

    nodes, rels = write_graph(FakeGraph(), driver, project_id=11)

    tx_calls = [
        call
        for session in driver.sessions
        for tx in session.transactions
        for call in tx.calls
    ]
    node_query = tx_calls[0]["query"]
    rel_query = tx_calls[2]["query"]
    assert nodes == 2
    assert rels == 1
    assert "UNWIND $nodes AS row" in node_query
    assert "MERGE (n:File {id: row.id})" in node_query
    assert "branch: $branch" not in node_query
    assert "{id: $sourceId, branch: $branch}" not in rel_query
    assert "UNWIND $rels AS rel" in rel_query
    assert "MATCH (a {id: rel.sourceId})" in rel_query


def test_write_graph_preserves_existing_doc_code_relationships():
    driver = FakeDriver()

    write_graph(FakeGraph(), driver, project_id=11)

    queries = [
        call["query"]
        for session in driver.sessions
        for tx in session.transactions
        for call in tx.calls
    ]
    joined = "\n".join(queries).upper()
    assert "DELETE" not in joined
    assert "DETACH" not in joined
    assert "MERGE (A)-[R:" in joined
