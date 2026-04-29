from types import SimpleNamespace


def test_list_version_code_facts_api_validates_version_scope(monkeypatch):
    from service.routers import product_versions

    monkeypatch.setattr(product_versions, "_check_product", lambda db, product_id: None)
    monkeypatch.setattr(
        product_versions.service,
        "get_version",
        lambda db, version_id: {"id": version_id, "product_id": 3},
    )
    monkeypatch.setattr(
        product_versions.service,
        "list_code_facts",
        lambda db, version_id, node_types=None: [
            {"fact_id": "Function:login", "node_type": "Function"}
        ],
    )

    rows = product_versions.list_version_code_facts(
        product_id=3,
        version_id=23,
        node_type=["Function"],
        db=object(),
    )

    assert rows == [{"fact_id": "Function:login", "node_type": "Function"}]


def test_create_doc_code_link_api_calls_service(monkeypatch):
    from service.routers import product_versions

    monkeypatch.setattr(product_versions, "_check_product", lambda db, product_id: None)
    monkeypatch.setattr(
        product_versions.service,
        "get_version",
        lambda db, version_id: {"id": version_id, "product_id": 3},
    )

    calls = {}

    def fake_create_link(db, **kwargs):
        calls.update(kwargs)
        return {"id": 7, "resolution_status": "resolved"}

    monkeypatch.setattr(product_versions.doc_code_link_service, "create_link", fake_create_link)

    result = product_versions.create_doc_code_link(
        product_id=3,
        version_id=23,
        body=product_versions.DocCodeLinkCreate(
            doc_id="DOC-1",
            doc_node_id="DOC-1#sec",
            code_project_id=11,
            symbol_key="project:11:Function:src/auth.py:login",
            relation_type="IMPLEMENTS",
        ),
        db=object(),
    )

    assert result == {"id": 7, "resolution_status": "resolved"}
    assert calls["product_id"] == 3
    assert calls["product_version_id"] == 23
    assert calls["code_project_id"] == 11


def test_list_doc_code_facts_api_calls_service(monkeypatch):
    from service.routers import product_versions

    monkeypatch.setattr(product_versions, "_check_product", lambda db, product_id: None)
    monkeypatch.setattr(
        product_versions.service,
        "get_version",
        lambda db, version_id: {"id": version_id, "product_id": 3},
    )
    monkeypatch.setattr(
        product_versions.doc_code_link_service,
        "list_code_facts_for_doc",
        lambda db, product_version_id, doc_id: {
            "product_version_id": product_version_id,
            "doc_id": doc_id,
            "code_facts": [{"fact_id": "Function:login"}],
        },
    )

    result = product_versions.list_doc_code_facts(
        product_id=3,
        version_id=23,
        doc_id="DOC-1",
        db=object(),
    )

    assert result["code_facts"] == [{"fact_id": "Function:login"}]
