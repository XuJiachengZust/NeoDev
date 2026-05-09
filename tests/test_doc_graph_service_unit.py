import pytest

from service.services import doc_graph_service


def test_document_key_includes_product_version_when_binding_is_version_scoped():
    binding = {"product_version_id": 23}

    key = doc_graph_service._document_key(binding)

    assert key == "doc_id: $doc_id, product_id: $product_id, product_version_id: $product_version_id"


def test_document_key_rejects_missing_product_version():
    binding = {"id": 9, "product_version_id": None}

    with pytest.raises(ValueError, match="product_version_id"):
        doc_graph_service._document_key(binding, doc_id_param="source_doc_id")


def test_relation_graph_write_passes_product_version_id(monkeypatch):
    calls = []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, **params):
            calls.append((query, params))

    class Driver:
        def session(self, database=None):
            return Session()

        def close(self):
            pass

    monkeypatch.setattr(doc_graph_service, "_load_config", lambda: ({"neo4j_uri": "bolt://neo4j"}, None))
    monkeypatch.setattr(doc_graph_service, "_create_driver", lambda config: Driver())
    monkeypatch.setattr(doc_graph_service, "resolve_document_project", lambda conn, binding: None)
    monkeypatch.setattr(
        doc_graph_service,
        "_document_version_scope",
        lambda conn, binding: {
            "product_name": "NeoDev SP",
            "version_name": "neodev-sp",
        },
    )

    doc_graph_service.upsert_document_graph(
        object(),
        binding={"id": 9, "product_id": 2, "product_version_id": 4},
        document={
            "id": 11,
            "doc_id": "DOC-1",
            "relations_json": {"target": ["DOC-2"]},
        },
    )

    relation_params = calls[-1][1]
    assert relation_params["product_version_id"] == 4


def test_document_graph_writes_name_version_scope(monkeypatch):
    calls = []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, **params):
            calls.append((query, params))

    class Driver:
        def session(self, database=None):
            return Session()

        def close(self):
            pass

    monkeypatch.setattr(doc_graph_service, "_load_config", lambda: ({"neo4j_uri": "bolt://neo4j"}, None))
    monkeypatch.setattr(doc_graph_service, "_create_driver", lambda config: Driver())
    monkeypatch.setattr(doc_graph_service, "resolve_document_project", lambda conn, binding: None)
    monkeypatch.setattr(
        doc_graph_service,
        "_document_version_scope",
        lambda conn, binding: {
            "product_name": "NeoDev SP",
            "version_name": "neodev-sp",
        },
    )

    doc_graph_service.upsert_document_graph(
        object(),
        binding={"id": 9, "product_id": 2, "product_version_id": 4},
        document={
            "id": 11,
            "doc_id": "DOC-1",
            "relations_json": {"target": ["DOC-2"]},
        },
    )

    document_call = next(call for call in calls if "MERGE (d:Document" in call[0])
    relation_call = calls[-1]
    assert "d.product_name = $product_name" in document_call[0]
    assert "d.version_name = $version_name" in document_call[0]
    assert "r.product_name = $product_name" in relation_call[0]
    assert "r.version_name = $version_name" in relation_call[0]
    assert document_call[1]["product_name"] == "NeoDev SP"
    assert document_call[1]["version_name"] == "neodev-sp"
    assert relation_call[1]["product_name"] == "NeoDev SP"
    assert relation_call[1]["version_name"] == "neodev-sp"


def test_document_graph_writes_version_graph_node_and_links_document(monkeypatch):
    calls = []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, **params):
            calls.append((query, params))

    class Driver:
        def session(self, database=None):
            return Session()

        def close(self):
            pass

    monkeypatch.setattr(doc_graph_service, "_load_config", lambda: ({"neo4j_uri": "bolt://neo4j"}, None))
    monkeypatch.setattr(doc_graph_service, "_create_driver", lambda config: Driver())
    monkeypatch.setattr(doc_graph_service, "resolve_document_project", lambda conn, binding: None)
    monkeypatch.setattr(
        doc_graph_service,
        "_document_version_scope",
        lambda conn, binding: {
            "product_name": "NeoDev SP",
            "version_name": "neodev-sp",
        },
    )

    doc_graph_service.upsert_document_graph(
        object(),
        binding={"id": 9, "product_id": 2, "product_version_id": 4},
        document={
            "id": 11,
            "doc_id": "DOC-1",
            "relative_path": "docs/a.md",
            "relations_json": {},
        },
    )

    graph_call = next(call for call in calls if "MERGE (g:DocumentGraph" in call[0])
    graph_link_call = next(call for call in calls if "CONTAINS_DOCUMENT" in call[0])

    assert "product_name: $product_name" in graph_call[0]
    assert "version_name: $version_name" in graph_call[0]
    assert graph_call[1]["product_name"] == "NeoDev SP"
    assert graph_call[1]["version_name"] == "neodev-sp"
    assert "MERGE (g)-[r:CONTAINS_DOCUMENT" in graph_link_call[0]
    assert graph_link_call[1]["product_name"] == "NeoDev SP"
    assert graph_link_call[1]["version_name"] == "neodev-sp"


def test_document_graph_writes_project_name_to_document_and_relationships(monkeypatch):
    calls = []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, **params):
            calls.append((query, params))

    class Driver:
        def session(self, database=None):
            return Session()

        def close(self):
            pass

    monkeypatch.setattr(doc_graph_service, "_load_config", lambda: ({"neo4j_uri": "bolt://neo4j"}, None))
    monkeypatch.setattr(doc_graph_service, "_create_driver", lambda config: Driver())
    monkeypatch.setattr(
        doc_graph_service,
        "resolve_document_project",
        lambda conn, binding: {"id": 7, "name": "NeoDev Docs", "repo_path": "", "repo_url": "", "product_id": 2},
    )
    monkeypatch.setattr(
        doc_graph_service,
        "_document_version_scope",
        lambda conn, binding: {"product_name": "NeoDev SP", "version_name": "neodev-sp"},
    )

    doc_graph_service.upsert_document_graph(
        object(),
        binding={"id": 9, "product_id": 2, "product_version_id": 4},
        document={
            "id": 11,
            "doc_id": "DOC-1",
            "relative_path": "docs/a.md",
            "relations_json": {"target": ["DOC-2"]},
        },
    )

    document_call = next(call for call in calls if "MERGE (d:Document" in call[0])
    project_link_call = next(call for call in calls if "HAS_DOCUMENT" in call[0])
    relation_call = calls[-1]

    assert "d.project_name = $project_name" in document_call[0]
    assert "r.project_name = $project_name" in project_link_call[0]
    assert "r.project_name = $project_name" in relation_call[0]
    assert document_call[1]["project_name"] == "NeoDev Docs"
    assert project_link_call[1]["project_name"] == "NeoDev Docs"
    assert relation_call[1]["project_name"] == "NeoDev Docs"


def test_document_graph_fails_before_write_when_version_scope_missing(monkeypatch):
    calls = []

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, **params):
            calls.append((query, params))

    class Driver:
        def session(self, database=None):
            return Session()

        def close(self):
            pass

    monkeypatch.setattr(doc_graph_service, "_load_config", lambda: ({"neo4j_uri": "bolt://neo4j"}, None))
    monkeypatch.setattr(doc_graph_service, "_create_driver", lambda config: Driver())
    monkeypatch.setattr(doc_graph_service, "resolve_document_project", lambda conn, binding: None)
    monkeypatch.setattr(
        doc_graph_service,
        "_document_version_scope",
        lambda conn, binding: {"product_name": "NeoDev SP", "version_name": None},
    )

    with pytest.raises(ValueError, match="document graph version scope"):
        doc_graph_service.upsert_document_graph(
            object(),
            binding={"id": 9, "product_id": 2, "product_version_id": 4},
            document={
                "id": 11,
                "doc_id": "DOC-1",
                "relative_path": "docs/a.md",
                "relations_json": {"target": ["DOC-2"]},
            },
        )

    assert calls == []


def test_document_graph_summary_reads_documents_from_version_graph(monkeypatch):
    calls = []

    class Result:
        def __iter__(self):
            return iter(
                [
                    {
                        "doc_id": "DOC-1",
                        "title": "Overview",
                        "relative_path": "docs/overview.md",
                        "doc_type": "prd",
                        "project_name": "NeoDev Docs",
                    }
                ]
            )

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def run(self, query, **params):
            calls.append((query, params))
            return Result()

    class Driver:
        def session(self, database=None):
            return Session()

        def close(self):
            pass

    monkeypatch.setattr(doc_graph_service, "_load_config", lambda: ({"neo4j_uri": "bolt://neo4j"}, None))
    monkeypatch.setattr(doc_graph_service, "_create_driver", lambda config: Driver())

    summary = doc_graph_service.document_graph_summary(
        product_name="NeoDev SP",
        version_name="neodev-sp",
    )

    query, params = calls[0]
    assert "MATCH (g:DocumentGraph {product_name: $product_name, version_name: $version_name})" in query
    assert "CONTAINS_DOCUMENT" in query
    assert params == {"product_name": "NeoDev SP", "version_name": "neodev-sp"}
    assert summary["document_count"] == 1
    assert summary["documents"][0]["doc_id"] == "DOC-1"
