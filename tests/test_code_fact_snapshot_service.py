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


def test_clear_branch_graph_delegates_to_repository(monkeypatch):
    from service.services import branch_snapshot_service

    calls = {}

    def fake_clear(conn, project_id, branch_name):
        calls["clear"] = {"project_id": project_id, "branch_name": branch_name}
        return {"deleted_snapshots": 2, "deleted_memberships": 5}

    monkeypatch.setattr(branch_snapshot_service.snapshot_repo, "clear_branch_graph", fake_clear)

    result = branch_snapshot_service.clear_branch_graph(
        object(),
        project_id=3,
        branch=" release/x ",
    )

    assert calls["clear"] == {"project_id": 3, "branch_name": "release/x"}
    assert result == {"deleted_snapshots": 2, "deleted_memberships": 5}


def test_refresh_graph_for_branch_clears_existing_branch_before_rebuild(monkeypatch):
    from types import SimpleNamespace

    from service.services import branch_snapshot_service
    from service.services import sync_service

    events = []

    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "git@example.com:unit/repo.git"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: events.append("fetch"))
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: "a" * 40)
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous, current: events.append("restore"))
    monkeypatch.setattr(sync_service, "_load_graph_config", lambda: {})

    def fake_run_pipeline(*args, **kwargs):
        events.append("pipeline")
        return SimpleNamespace(
            snapshot_hash="same-hash",
            code_facts=[
                {
                    "fact_id": "Function:manual-replaced",
                    "symbol_key": "manual-replaced",
                    "node_type": "Function",
                    "name": "manual_replaced",
                }
            ],
        )

    import gitnexus_parser.ingestion.pipeline as pipeline

    monkeypatch.setattr(pipeline, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(
        branch_snapshot_service,
        "get_current_snapshot",
        lambda conn, project_id, branch: {"id": 9, "snapshot_hash": "same-hash"},
    )
    monkeypatch.setattr(
        branch_snapshot_service,
        "clear_branch_graph",
        lambda conn, project_id, branch: events.append("clear") or {"deleted_snapshots": 1},
        raising=False,
    )
    from service.services import manual_graph_sync_service

    monkeypatch.setattr(
        manual_graph_sync_service,
        "clear_project_graph",
        lambda conn, project_id: events.append("clear_neo4j"),
    )

    def fake_create_snapshot(conn, **kwargs):
        events.append("create_snapshot")
        return {"id": 10, "entry_count": len(kwargs["code_facts"]), "snapshot_hash": kwargs["snapshot_hash"]}

    monkeypatch.setattr(branch_snapshot_service, "create_snapshot_from_code_facts", fake_create_snapshot)

    from service.services import doc_code_link_service

    monkeypatch.setattr(
        doc_code_link_service,
        "rebuild_links_for_branch_snapshot",
        lambda conn, **kwargs: events.append("rebuild_links") or {"resolved": 0},
    )

    class DummyConn:
        def commit(self):
            events.append("commit")

    result = sync_service.refresh_graph_for_branch(DummyConn(), 3, "release/x")

    assert events.index("clear") < events.index("create_snapshot")
    assert events.index("clear_neo4j") < events.index("pipeline")
    assert result["graph_action"] == "full_refresh"
    assert result["current_snapshot_id"] == 10


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
