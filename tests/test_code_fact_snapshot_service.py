def test_create_snapshot_from_code_facts_writes_snapshot_and_fact_membership(monkeypatch):
    from service.services import branch_snapshot_service

    calls = {}

    def fake_create_snapshot(conn, **kwargs):
        calls["snapshot"] = kwargs
        return {"id": 42, **kwargs}

    def fake_upsert_many(conn, facts):
        calls["facts"] = list(facts)
        return len(facts)

    def fake_replace_facts(conn, snapshot_id, fact_ids):
        calls["snapshot_facts"] = {"snapshot_id": snapshot_id, "fact_ids": list(fact_ids)}
        return len(fact_ids)

    monkeypatch.setattr(branch_snapshot_service.snapshot_repo, "create_snapshot", fake_create_snapshot)
    monkeypatch.setattr(branch_snapshot_service.code_fact_repo, "upsert_many", fake_upsert_many)
    monkeypatch.setattr(branch_snapshot_service.snapshot_repo, "replace_facts", fake_replace_facts)

    snapshot = branch_snapshot_service.create_snapshot_from_code_facts(
        object(),
        project_id=3,
        branch="release/x",
        head_commit="a" * 40,
        snapshot_hash="snapshot-hash",
        code_facts=[
            {
                "fact_id": "Method:m1",
                "symbol_key": "project:3:Method:src/a.py:A.m",
                "node_type": "Method",
                "file_path": "src/a.py",
                "qualified_name": "A.m",
                "name": "m",
                "content_hash": "h1",
                "structure_hash": "s1",
            }
        ],
    )

    assert snapshot["id"] == 42
    assert snapshot["entry_count"] == 1
    assert calls["snapshot"] == {
        "project_id": 3,
        "branch_name": "release/x",
        "head_commit": "a" * 40,
        "snapshot_hash": "snapshot-hash",
        "status": "completed",
    }
    assert calls["facts"][0]["fact_id"] == "Method:m1"
    assert calls["snapshot_facts"] == {"snapshot_id": 42, "fact_ids": ["Method:m1"]}


def test_list_product_version_code_facts_uses_repository_scope(monkeypatch):
    from service.services import branch_snapshot_service

    calls = {}

    def fake_list(conn, product_version_id, node_types=None):
        calls["args"] = {
            "product_version_id": product_version_id,
            "node_types": node_types,
        }
        return [
            {
                "fact_id": "Function:login",
                "node_type": "Function",
                "branch_name": "release/V1",
                "snapshot_id": 7,
            }
        ]

    monkeypatch.setattr(branch_snapshot_service.code_fact_repo, "list_by_product_version", fake_list)

    rows = branch_snapshot_service.list_product_version_code_facts(
        object(),
        product_version_id=23,
        node_types=["Function"],
    )

    assert calls["args"] == {"product_version_id": 23, "node_types": ["Function"]}
    assert rows[0]["fact_id"] == "Function:login"
