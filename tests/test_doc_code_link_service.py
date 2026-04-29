def test_create_link_resolves_unique_visible_symbol(monkeypatch):
    from service.services import doc_code_link_service

    calls = {}

    monkeypatch.setattr(
        doc_code_link_service.repo,
        "create",
        lambda conn, **kwargs: {"id": 10, **kwargs, "resolution_status": "unresolved"},
    )
    monkeypatch.setattr(
        doc_code_link_service.repo,
        "get_product_version_branch",
        lambda conn, product_version_id, project_id: {
            "product_version_id": product_version_id,
            "project_id": project_id,
            "branch_name": "release/V1",
        },
    )
    monkeypatch.setattr(
        doc_code_link_service.branch_snapshot_service,
        "get_current_snapshot",
        lambda conn, project_id, branch: {"id": 77},
    )
    monkeypatch.setattr(
        doc_code_link_service.code_fact_repository,
        "list_visible_by_symbol",
        lambda conn, **kwargs: [{"fact_id": "Function:login", "symbol_key": kwargs["symbol_key"]}],
    )

    def fake_set_resolution(conn, **kwargs):
        calls["resolution"] = kwargs
        return {"id": kwargs["link_id"], "resolution_status": kwargs["resolution_status"]}

    monkeypatch.setattr(doc_code_link_service.repo, "set_resolution", fake_set_resolution)

    link = doc_code_link_service.create_link(
        object(),
        product_id=3,
        product_version_id=23,
        doc_id="DOC-1",
        doc_node_id="DOC-1#sec",
        code_project_id=11,
        symbol_key="project:11:Function:src/auth.py:login",
        relation_type="IMPLEMENTS",
    )

    assert link["resolution_status"] == "resolved"
    assert calls["resolution"]["resolved_fact_id"] == "Function:login"
    assert calls["resolution"]["resolved_snapshot_id"] == 77


def test_list_code_facts_for_doc_re_resolves_stale_link(monkeypatch):
    from service.services import doc_code_link_service

    monkeypatch.setattr(
        doc_code_link_service.repo,
        "list_by_product_version_doc",
        lambda conn, product_version_id, doc_id: [
            {
                "id": 10,
                "product_version_id": product_version_id,
                "doc_id": doc_id,
                "code_project_id": 11,
                "symbol_key": "project:11:Function:src/auth.py:login",
                "resolved_fact_id": "old-fact",
            }
        ],
    )
    monkeypatch.setattr(
        doc_code_link_service.repo,
        "get_product_version_branch",
        lambda conn, product_version_id, project_id: {"branch_name": "release/V1"},
    )
    monkeypatch.setattr(
        doc_code_link_service.branch_snapshot_service,
        "get_current_snapshot",
        lambda conn, project_id, branch: {"id": 77},
    )
    monkeypatch.setattr(
        doc_code_link_service.branch_snapshot_service,
        "list_fact_ids",
        lambda conn, snapshot_id: ["new-fact"],
    )
    monkeypatch.setattr(
        doc_code_link_service.code_fact_repository,
        "list_visible_by_symbol",
        lambda conn, **kwargs: [{"fact_id": "new-fact", "name": "login"}],
    )
    monkeypatch.setattr(
        doc_code_link_service.repo,
        "set_resolution",
        lambda conn, **kwargs: {"id": kwargs["link_id"], "resolution_status": kwargs["resolution_status"]},
    )

    result = doc_code_link_service.list_code_facts_for_doc(
        object(),
        product_version_id=23,
        doc_id="DOC-1",
    )

    assert result["resolved"] == 1
    assert result["code_facts"] == [{"fact_id": "new-fact", "name": "login"}]
