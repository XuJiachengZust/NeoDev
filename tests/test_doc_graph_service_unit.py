from service.services import doc_graph_service


def test_document_key_includes_product_version_when_binding_is_version_scoped():
    binding = {"product_version_id": 23}

    key = doc_graph_service._document_key(binding)

    assert key == "doc_id: $doc_id, product_id: $product_id, product_version_id: $product_version_id"


def test_document_key_keeps_legacy_product_scope_without_version():
    binding = {"product_version_id": None}

    key = doc_graph_service._document_key(binding, doc_id_param="source_doc_id")

    assert key == "doc_id: $source_doc_id, product_id: $product_id"


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

    document_call = calls[0]
    relation_call = calls[-1]
    assert "d.product_name = $product_name" in document_call[0]
    assert "d.version_name = $version_name" in document_call[0]
    assert "r.product_name = $product_name" in relation_call[0]
    assert "r.version_name = $version_name" in relation_call[0]
    assert document_call[1]["product_name"] == "NeoDev SP"
    assert document_call[1]["version_name"] == "neodev-sp"
    assert relation_call[1]["product_name"] == "NeoDev SP"
    assert relation_call[1]["version_name"] == "neodev-sp"


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

    document_call = calls[0]
    project_link_call = next(call for call in calls if "HAS_DOCUMENT" in call[0])
    relation_call = calls[-1]

    assert "d.project_name = $project_name" in document_call[0]
    assert "r.project_name = $project_name" in project_link_call[0]
    assert "r.project_name = $project_name" in relation_call[0]
    assert document_call[1]["project_name"] == "NeoDev Docs"
    assert project_link_call[1]["project_name"] == "NeoDev Docs"
    assert relation_call[1]["project_name"] == "NeoDev Docs"
