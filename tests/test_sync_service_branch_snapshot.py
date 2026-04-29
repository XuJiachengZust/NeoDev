from types import SimpleNamespace


class FakeConn:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def test_refresh_graph_for_branch_creates_code_fact_snapshot(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import branch_snapshot_service, doc_code_link_service, sync_service

    calls = {}
    head = "c" * 40

    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: head)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: None)
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: None)
    monkeypatch.setattr(sync_service, "_load_graph_config", lambda: {"neo4j_uri": "bolt://neo4j"})

    def fake_run_pipeline(local_root, config, **kwargs):
        calls["pipeline"] = {"local_root": local_root, "config": config, **kwargs}
        return SimpleNamespace(
            snapshot_hash="snapshot-hash",
            code_facts=[
                {
                    "project_id": 3,
                    "fact_id": "Function:login",
                    "symbol_key": "project:3:Function:src/auth.py:login",
                    "node_type": "Function",
                }
            ],
        )

    monkeypatch.setattr(pipeline, "run_pipeline", fake_run_pipeline)
    monkeypatch.setattr(branch_snapshot_service, "get_current_snapshot", lambda conn, project_id, branch: None)

    def fake_create_snapshot(conn, **kwargs):
        calls["snapshot"] = kwargs
        return {"id": 99, "entry_count": len(kwargs["code_facts"])}

    monkeypatch.setattr(branch_snapshot_service, "create_snapshot_from_code_facts", fake_create_snapshot)
    monkeypatch.setattr(
        doc_code_link_service,
        "rebuild_links_for_branch_snapshot",
        lambda conn, **kwargs: calls.setdefault("links", kwargs) or {"links_checked": 0},
    )

    result = sync_service.refresh_graph_for_branch(FakeConn(), project_id=3, branch="main")

    assert result["graph_action"] == "full_refresh"
    assert result["head_commit"] == head
    assert result["current_snapshot_id"] == 99
    assert result["snapshot_hash"] == "snapshot-hash"
    assert result["code_fact_count"] == 1
    assert calls["pipeline"]["branch"] == "main"
    assert calls["pipeline"]["project_id"] == 3
    assert calls["pipeline"]["incremental"] is False
    assert calls["snapshot"]["branch"] == "main"
    assert calls["snapshot"]["snapshot_hash"] == "snapshot-hash"
    assert calls["links"] == {"project_id": 3, "branch_name": "main", "snapshot_id": 99}


def test_refresh_graph_for_branch_rebuilds_doc_links_when_snapshot_hash_unchanged(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import branch_snapshot_service, doc_code_link_service, sync_service

    calls = {}

    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: "c" * 40)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: None)
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: None)
    monkeypatch.setattr(sync_service, "_load_graph_config", lambda: {})
    monkeypatch.setattr(
        pipeline,
        "run_pipeline",
        lambda *args, **kwargs: SimpleNamespace(snapshot_hash="same", code_facts=[]),
    )
    monkeypatch.setattr(
        branch_snapshot_service,
        "get_current_snapshot",
        lambda conn, project_id, branch: {"id": 77, "snapshot_hash": "same"},
    )
    monkeypatch.setattr(
        doc_code_link_service,
        "rebuild_links_for_branch_snapshot",
        lambda conn, **kwargs: calls.setdefault("links", kwargs) or {"links_checked": 1},
    )

    result = sync_service.refresh_graph_for_branch(FakeConn(), project_id=3, branch="main")

    assert result["graph_action"] == "no_change"
    assert result["current_snapshot_id"] == 77
    assert calls["links"] == {"project_id": 3, "branch_name": "main", "snapshot_id": 77}
