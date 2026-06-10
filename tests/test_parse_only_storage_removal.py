from types import SimpleNamespace


class FakeConn:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class FailingCommitConn(FakeConn):
    def commit(self):
        self.commits += 1
        raise RuntimeError("commit failed")


class FailingSecondCommitConn(FakeConn):
    def commit(self):
        self.commits += 1
        if self.commits == 1:
            raise RuntimeError("commit failed")
        raise RuntimeError("failure-state commit failed")


def test_refresh_graph_for_branch_replaces_neo4j_branch_graph(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import sync_service

    calls = {}
    graph = object()

    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: calls.setdefault("fetch", local_root))
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: "c" * 40)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: calls.setdefault("restore", current_branch))
    monkeypatch.setattr(sync_service.branch_graph_repo, "get_by_project_branch", lambda conn, project_id, branch_name: None)
    monkeypatch.setattr(
        sync_service.product_version_service,
        "list_versions_by_project_branch",
        lambda conn, project_id, branch_name: [
            {
                "id": 23,
                "product_name": "NeoDev SP",
                "version_name": "V1",
                "project_name": "NeoDev",
            }
        ],
    )

    def fake_upsert(conn, *, project_id, branch_name, status):
        calls["upsert_graph"] = {"project_id": project_id, "branch_name": branch_name, "status": status}
        return {"id": 9, "project_id": project_id, "branch_name": branch_name, "status": status}

    def fake_start_run(conn, **kwargs):
        calls["start_run"] = kwargs
        return {"id": 17, **kwargs}

    def fake_complete_run(conn, **kwargs):
        calls["complete_run"] = kwargs
        return {"id": kwargs["run_id"], "status": "completed"}

    def fake_mark_ready(conn, **kwargs):
        calls["mark_ready"] = kwargs
        return {"id": kwargs["graph_id"], "status": "ready"}

    monkeypatch.setattr(sync_service.branch_graph_repo, "upsert", fake_upsert)
    monkeypatch.setattr(sync_service.branch_graph_repo, "start_refresh_run", fake_start_run)
    monkeypatch.setattr(sync_service.branch_graph_repo, "complete_refresh_run", fake_complete_run)
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_ready", fake_mark_ready)
    monkeypatch.setattr(
        sync_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687", "neo4j_user": "neo4j", "neo4j_password": "pw"}, None),
    )
    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "branch_has_graph", lambda **kwargs: False)

    def fake_replace_branch_graph(**kwargs):
        calls["neo4j_replace"] = kwargs
        return {"status": "updated", "nodes_written": 4, "relationships_written": 3}

    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "replace_branch_graph", fake_replace_branch_graph)

    def fake_run_pipeline(local_root, config, **kwargs):
        calls["pipeline"] = {"local_root": local_root, "config": config, **kwargs}
        return SimpleNamespace(node_count=4, relationship_count=3, file_count=2, graph=graph)

    monkeypatch.setattr(pipeline, "run_pipeline", fake_run_pipeline)

    conn = FakeConn()
    result = sync_service.refresh_graph_for_branch(conn, project_id=3, branch="main")

    assert result["graph_action"] == "full_replace"
    assert result["graph_id"] == 9
    assert result["run_id"] == 17
    assert result["node_count"] == 4
    assert result["edge_count"] == 3
    assert result["file_count"] == 2
    assert "current_snapshot_id" not in result
    assert "code_fact_count" not in result
    assert calls["pipeline"]["write_neo4j"] is True
    assert calls["pipeline"]["incremental"] is False
    assert calls["neo4j_replace"]["graph"] is graph
    assert calls["neo4j_replace"]["project_id"] == 3
    assert calls["neo4j_replace"]["branch_name"] == "main"
    assert calls["neo4j_replace"]["graph_id"] == 9
    assert calls["neo4j_replace"]["version_scope"] == {
        "product_version_id": 23,
        "product_name": "NeoDev SP",
        "version_name": "V1",
        "project_name": "NeoDev",
    }
    assert calls["upsert_graph"]["status"] == "running"
    assert calls["mark_ready"]["node_count"] == 4
    assert calls["mark_ready"]["edge_count"] == 3
    assert conn.commits == 1


def test_refresh_graph_for_branch_can_defer_pg_commit_for_atomic_call(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import sync_service

    calls = {}
    graph = object()
    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: "c" * 40)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: None)
    monkeypatch.setattr(sync_service.branch_graph_repo, "get_by_project_branch", lambda conn, project_id, branch_name: None)
    monkeypatch.setattr(sync_service.product_version_service, "list_versions_by_project_branch", lambda conn, project_id, branch_name: [])
    monkeypatch.setattr(sync_service.branch_graph_repo, "upsert", lambda conn, **kwargs: {"id": 9, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "start_refresh_run", lambda conn, **kwargs: {"id": 17, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_ready", lambda conn, **kwargs: calls.setdefault("mark_ready", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "complete_refresh_run", lambda conn, **kwargs: calls.setdefault("complete_run", kwargs))
    monkeypatch.setattr(
        sync_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "branch_has_graph", lambda **kwargs: False)
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "replace_branch_graph",
        lambda **kwargs: calls.setdefault("replace", kwargs) or {"status": "updated", "nodes_written": 1, "relationships_written": 1},
    )
    monkeypatch.setattr(
        pipeline,
        "run_pipeline",
        lambda *args, **kwargs: SimpleNamespace(node_count=1, relationship_count=1, file_count=1, graph=graph),
    )

    conn = FakeConn()
    result = sync_service.refresh_graph_for_branch(conn, project_id=3, branch="main", commit=False)

    assert result["graph_action"] == "full_replace"
    assert calls["replace"]["graph"] is graph
    assert conn.commits == 0


def test_refresh_graph_for_branch_captures_neo4j_snapshot_for_atomic_restore(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import sync_service

    calls = {}
    graph = object()
    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: "c" * 40)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: None)
    monkeypatch.setattr(sync_service.branch_graph_repo, "get_by_project_branch", lambda conn, project_id, branch_name: None)
    monkeypatch.setattr(sync_service.product_version_service, "list_versions_by_project_branch", lambda conn, project_id, branch_name: [])
    monkeypatch.setattr(sync_service.branch_graph_repo, "upsert", lambda conn, **kwargs: {"id": 9, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "start_refresh_run", lambda conn, **kwargs: {"id": 17, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_ready", lambda conn, **kwargs: calls.setdefault("mark_ready", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "complete_refresh_run", lambda conn, **kwargs: calls.setdefault("complete_run", kwargs))
    monkeypatch.setattr(
        sync_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "branch_has_graph", lambda **kwargs: False)
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "snapshot_branch_graph",
        lambda **kwargs: calls.setdefault("snapshot", kwargs) or {"project_id": kwargs["project_id"], "branch_name": kwargs["branch_name"]},
    )
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "replace_branch_graph",
        lambda **kwargs: calls.setdefault("replace", kwargs) or {"status": "updated", "nodes_written": 1, "relationships_written": 1},
    )
    monkeypatch.setattr(
        pipeline,
        "run_pipeline",
        lambda *args, **kwargs: SimpleNamespace(node_count=1, relationship_count=1, file_count=1, graph=graph),
    )

    conn = FakeConn()
    result = sync_service.refresh_graph_for_branch(
        conn,
        project_id=3,
        branch="main",
        commit=False,
        restore_neo4j_on_error=True,
    )

    assert calls["snapshot"]["project_id"] == 3
    assert calls["snapshot"]["branch_name"] == "main"
    assert result["_neo4j_restore"]["config"] == {"neo4j_uri": "bolt://neo4j:7687"}
    assert result["_neo4j_restore"]["snapshot"]["branch_name"] == "main"
    assert conn.commits == 0


def test_refresh_graph_for_branch_restores_neo4j_when_pg_commit_fails(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import sync_service

    calls = {}
    graph = object()
    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: "c" * 40)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: None)
    monkeypatch.setattr(sync_service.branch_graph_repo, "get_by_project_branch", lambda conn, project_id, branch_name: None)
    monkeypatch.setattr(sync_service.product_version_service, "list_versions_by_project_branch", lambda conn, project_id, branch_name: [])
    monkeypatch.setattr(sync_service.branch_graph_repo, "upsert", lambda conn, **kwargs: {"id": 9, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "start_refresh_run", lambda conn, **kwargs: {"id": 17, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_ready", lambda conn, **kwargs: calls.setdefault("mark_ready", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "complete_refresh_run", lambda conn, **kwargs: calls.setdefault("complete_run", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_failed", lambda conn, **kwargs: calls.setdefault("mark_failed", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "fail_refresh_run", lambda conn, **kwargs: calls.setdefault("fail_run", kwargs))
    monkeypatch.setattr(
        sync_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "branch_has_graph", lambda **kwargs: False)
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "snapshot_branch_graph",
        lambda **kwargs: {"project_id": kwargs["project_id"], "branch_name": kwargs["branch_name"]},
    )
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "replace_branch_graph",
        lambda **kwargs: {"status": "updated", "nodes_written": 1, "relationships_written": 1},
    )
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "restore_branch_graph_snapshot",
        lambda **kwargs: calls.setdefault("restore", kwargs) or {"status": "restored"},
    )
    monkeypatch.setattr(
        pipeline,
        "run_pipeline",
        lambda *args, **kwargs: SimpleNamespace(node_count=1, relationship_count=1, file_count=1, graph=graph),
    )

    conn = FailingCommitConn()
    try:
        sync_service.refresh_graph_for_branch(
            conn,
            project_id=3,
            branch="main",
            commit=True,
            commit_failure_state=False,
            restore_neo4j_on_error=True,
        )
    except RuntimeError as exc:
        assert "commit failed" in str(exc)
    else:
        raise AssertionError("expected commit failure")

    assert calls["restore"]["snapshot"]["project_id"] == 3
    assert calls["mark_failed"]["graph_id"] == 9
    assert calls["fail_run"]["run_id"] == 17
    assert conn.commits == 1


def test_refresh_graph_for_branch_reports_rollback_failed_when_neo4j_restore_fails(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import sync_service

    calls = {}
    graph = object()
    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: "c" * 40)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: None)
    monkeypatch.setattr(sync_service.branch_graph_repo, "get_by_project_branch", lambda conn, project_id, branch_name: None)
    monkeypatch.setattr(sync_service.product_version_service, "list_versions_by_project_branch", lambda conn, project_id, branch_name: [])
    monkeypatch.setattr(sync_service.branch_graph_repo, "upsert", lambda conn, **kwargs: {"id": 9, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "start_refresh_run", lambda conn, **kwargs: {"id": 17, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_ready", lambda conn, **kwargs: calls.setdefault("mark_ready", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "complete_refresh_run", lambda conn, **kwargs: calls.setdefault("complete_run", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_failed", lambda conn, **kwargs: calls.setdefault("mark_failed", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "fail_refresh_run", lambda conn, **kwargs: calls.setdefault("fail_run", kwargs))
    monkeypatch.setattr(
        sync_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "branch_has_graph", lambda **kwargs: False)
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "snapshot_branch_graph",
        lambda **kwargs: {"project_id": kwargs["project_id"], "branch_name": kwargs["branch_name"]},
    )
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "replace_branch_graph",
        lambda **kwargs: {"status": "updated", "nodes_written": 1, "relationships_written": 1},
    )
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "restore_branch_graph_snapshot",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("restore failed")),
    )
    monkeypatch.setattr(
        pipeline,
        "run_pipeline",
        lambda *args, **kwargs: SimpleNamespace(node_count=1, relationship_count=1, file_count=1, graph=graph),
    )

    conn = FailingCommitConn()
    try:
        sync_service.refresh_graph_for_branch(
            conn,
            project_id=3,
            branch="main",
            commit=True,
            commit_failure_state=False,
            restore_neo4j_on_error=True,
        )
    except sync_service.GraphRefreshRollbackError as exc:
        assert exc.rollback_status == "rollback_failed"
        assert str(exc.restore_error) == "restore failed"
    else:
        raise AssertionError("expected graph refresh rollback failure")

    assert calls["mark_failed"]["graph_id"] == 9
    assert calls["fail_run"]["run_id"] == 17
    assert conn.commits == 1


def test_refresh_graph_for_branch_restore_failure_is_not_masked_by_failure_state_commit(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import sync_service

    calls = {}
    graph = object()
    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: "c" * 40)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: None)
    monkeypatch.setattr(sync_service.branch_graph_repo, "get_by_project_branch", lambda conn, project_id, branch_name: None)
    monkeypatch.setattr(sync_service.product_version_service, "list_versions_by_project_branch", lambda conn, project_id, branch_name: [])
    monkeypatch.setattr(sync_service.branch_graph_repo, "upsert", lambda conn, **kwargs: {"id": 9, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "start_refresh_run", lambda conn, **kwargs: {"id": 17, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_ready", lambda conn, **kwargs: calls.setdefault("mark_ready", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "complete_refresh_run", lambda conn, **kwargs: calls.setdefault("complete_run", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_failed", lambda conn, **kwargs: calls.setdefault("mark_failed", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "fail_refresh_run", lambda conn, **kwargs: calls.setdefault("fail_run", kwargs))
    monkeypatch.setattr(
        sync_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "branch_has_graph", lambda **kwargs: False)
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "snapshot_branch_graph",
        lambda **kwargs: {"project_id": kwargs["project_id"], "branch_name": kwargs["branch_name"]},
    )
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "replace_branch_graph",
        lambda **kwargs: {"status": "updated", "nodes_written": 1, "relationships_written": 1},
    )
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "restore_branch_graph_snapshot",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("restore failed")),
    )
    monkeypatch.setattr(
        pipeline,
        "run_pipeline",
        lambda *args, **kwargs: SimpleNamespace(node_count=1, relationship_count=1, file_count=1, graph=graph),
    )

    conn = FailingSecondCommitConn()
    try:
        sync_service.refresh_graph_for_branch(
            conn,
            project_id=3,
            branch="main",
            commit=True,
            restore_neo4j_on_error=True,
        )
    except sync_service.GraphRefreshRollbackError as exc:
        assert exc.rollback_status == "rollback_failed"
        assert str(exc.restore_error) == "restore failed"
        assert str(exc.commit_error) == "failure-state commit failed"
    else:
        raise AssertionError("expected graph refresh rollback failure")

    assert conn.commits == 2
    assert calls["mark_failed"]["graph_id"] == 9
    assert calls["fail_run"]["run_id"] == 17


def test_refresh_graph_for_branch_does_not_restore_when_neo4j_replace_transaction_fails(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import sync_service

    calls = {}
    graph = object()
    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: "c" * 40)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: None)
    monkeypatch.setattr(sync_service.branch_graph_repo, "get_by_project_branch", lambda conn, project_id, branch_name: None)
    monkeypatch.setattr(sync_service.product_version_service, "list_versions_by_project_branch", lambda conn, project_id, branch_name: [])
    monkeypatch.setattr(sync_service.branch_graph_repo, "upsert", lambda conn, **kwargs: {"id": 9, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "start_refresh_run", lambda conn, **kwargs: {"id": 17, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_ready", lambda conn, **kwargs: calls.setdefault("mark_ready", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "complete_refresh_run", lambda conn, **kwargs: calls.setdefault("complete_run", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_failed", lambda conn, **kwargs: calls.setdefault("mark_failed", kwargs))
    monkeypatch.setattr(sync_service.branch_graph_repo, "fail_refresh_run", lambda conn, **kwargs: calls.setdefault("fail_run", kwargs))
    monkeypatch.setattr(
        sync_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "branch_has_graph", lambda **kwargs: False)
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "snapshot_branch_graph",
        lambda **kwargs: {"project_id": kwargs["project_id"], "branch_name": kwargs["branch_name"]},
    )
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "replace_branch_graph",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("neo4j write failed")),
    )
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "restore_branch_graph_snapshot",
        lambda **kwargs: calls.setdefault("restore", kwargs),
    )
    monkeypatch.setattr(
        pipeline,
        "run_pipeline",
        lambda *args, **kwargs: SimpleNamespace(node_count=1, relationship_count=1, file_count=1, graph=graph),
    )

    conn = FakeConn()
    try:
        sync_service.refresh_graph_for_branch(
            conn,
            project_id=3,
            branch="main",
            commit=False,
            commit_failure_state=False,
            restore_neo4j_on_error=True,
        )
    except RuntimeError as exc:
        assert "neo4j write failed" in str(exc)
        assert not isinstance(exc, sync_service.GraphRefreshRollbackError)
    else:
        raise AssertionError("expected Neo4j replace failure")

    assert "restore" not in calls
    assert calls["mark_failed"]["graph_id"] == 9
    assert calls["fail_run"]["run_id"] == 17
    assert conn.commits == 0


def test_refresh_graph_for_branch_skips_unchanged_existing_neo4j_graph(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import sync_service

    calls = {}
    head = "c" * 40

    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: calls.setdefault("fetch", local_root))
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: head)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: calls.setdefault("restore", current_branch))
    monkeypatch.setattr(
        sync_service.branch_graph_repo,
        "get_by_project_branch",
        lambda conn, project_id, branch_name: {
            "id": 9,
            "project_id": project_id,
            "branch_name": branch_name,
            "status": "ready",
            "head_commit": head,
            "node_count": 4,
            "edge_count": 3,
        },
    )
    monkeypatch.setattr(
        sync_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687", "neo4j_user": "neo4j", "neo4j_password": "pw"}, None),
    )
    monkeypatch.setattr(
        sync_service.product_version_service,
        "list_versions_by_project_branch",
        lambda conn, project_id, branch_name: [
            {
                "id": 23,
                "product_name": "NeoDev SP",
                "version_name": "V1",
                "project_name": "NeoDev",
            }
        ],
    )

    def fake_branch_has_graph(**kwargs):
        calls["branch_has_graph"] = kwargs
        return True

    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "branch_has_graph", fake_branch_has_graph)
    monkeypatch.setattr(
        sync_service.graph_management_repository,
        "has_operations_for_branch",
        lambda conn, project_id, branch_name: False,
    )
    monkeypatch.setattr(pipeline, "run_pipeline", lambda *args, **kwargs: calls.setdefault("pipeline", True))

    conn = FakeConn()
    result = sync_service.refresh_graph_for_branch(conn, project_id=3, branch="main")

    assert result["graph_action"] == "skipped_unchanged"
    assert result["graph_id"] == 9
    assert result["head_commit"] == head
    assert calls["branch_has_graph"]["version_scope"]["product_version_id"] == 23
    assert calls["branch_has_graph"]["version_scope"]["product_name"] == "NeoDev SP"
    assert "pipeline" not in calls
    assert conn.commits == 0


def test_refresh_graph_for_branch_replaces_when_manual_graph_operations_exist(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import sync_service

    calls = {}
    head = "c" * 40
    graph = object()

    monkeypatch.setattr(
        sync_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "repo_path": "D:/repo"},
    )
    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "D:/repo")
    monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: calls.setdefault("fetch", local_root))
    monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: head)
    monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: "main")
    monkeypatch.setattr(sync_service, "_restore_checkout", lambda local_root, previous_branch, current_branch: calls.setdefault("restore", current_branch))
    monkeypatch.setattr(
        sync_service.branch_graph_repo,
        "get_by_project_branch",
        lambda conn, project_id, branch_name: {
            "id": 9,
            "project_id": project_id,
            "branch_name": branch_name,
            "status": "ready",
            "head_commit": head,
            "node_count": 4,
            "edge_count": 3,
        },
    )
    monkeypatch.setattr(
        sync_service.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687", "neo4j_user": "neo4j", "neo4j_password": "pw"}, None),
    )
    monkeypatch.setattr(
        sync_service.product_version_service,
        "list_versions_by_project_branch",
        lambda conn, project_id, branch_name: [
            {
                "id": 23,
                "product_name": "NeoDev SP",
                "version_name": "V1",
                "project_name": "NeoDev",
            }
        ],
    )
    monkeypatch.setattr(sync_service.branch_graph_neo4j_service, "branch_has_graph", lambda **kwargs: True)
    monkeypatch.setattr(
        sync_service,
        "graph_management_repository",
        SimpleNamespace(has_operations_for_branch=lambda conn, project_id, branch_name: True),
        raising=False,
    )
    monkeypatch.setattr(sync_service.branch_graph_repo, "upsert", lambda conn, **kwargs: {"id": 9, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "start_refresh_run", lambda conn, **kwargs: {"id": 17, **kwargs})
    monkeypatch.setattr(sync_service.branch_graph_repo, "mark_ready", lambda conn, **kwargs: {"id": kwargs["graph_id"], "status": "ready"})
    monkeypatch.setattr(sync_service.branch_graph_repo, "complete_refresh_run", lambda conn, **kwargs: calls.setdefault("complete_run", kwargs))
    monkeypatch.setattr(
        sync_service.branch_graph_neo4j_service,
        "replace_branch_graph",
        lambda **kwargs: calls.setdefault("neo4j_replace", kwargs) or {"status": "updated", "nodes_written": 4, "relationships_written": 3},
    )
    def fake_run_pipeline(local_root, config, **kwargs):
        calls["pipeline"] = kwargs
        return SimpleNamespace(node_count=4, relationship_count=3, file_count=2, graph=graph)

    monkeypatch.setattr(pipeline, "run_pipeline", fake_run_pipeline)

    conn = FakeConn()
    result = sync_service.refresh_graph_for_branch(conn, project_id=3, branch="main")

    assert result["graph_action"] == "full_replace"
    assert calls["pipeline"]["write_neo4j"] is True
    assert calls["neo4j_replace"]["graph"] is graph
    assert conn.commits == 1


def test_refresh_graph_for_branch_rejects_ambiguous_version_scope(monkeypatch):
    from service.services import sync_service

    monkeypatch.setattr(
        sync_service.product_version_service,
        "list_versions_by_project_branch",
        lambda conn, project_id, branch_name: [
            {"id": 23, "product_name": "NeoDev SP", "version_name": "V1", "project_name": "NeoDev"},
            {"id": 24, "product_name": "NeoDev SP", "version_name": "V2", "project_name": "NeoDev"},
        ],
    )

    try:
        sync_service._branch_version_scope(object(), 3, "main")
    except RuntimeError as exc:
        assert "branch is bound to multiple product versions" in str(exc)
    else:
        raise AssertionError("expected ambiguous version scope to be rejected")


def test_pipeline_result_no_longer_exposes_code_fact_storage_fields():
    from gitnexus_parser.ingestion.pipeline import PipelineResult

    fields = set(PipelineResult.__dataclass_fields__)

    assert "code_facts" not in fields
    assert "snapshot_hash" not in fields


def test_product_cli_code_storage_commands_are_noops(monkeypatch):
    from service.cli.commands import product as product_command

    version = {"id": 23, "product_id": 5, "version_name": "V1"}
    product = {"id": 5, "name": "Product"}
    project = {"id": 7, "name": "Code Project", "neo4j_database": None}
    graph = {"id": 91, "status": "ready", "branch_name": "release/V2.0"}
    neo4j_actions = []

    monkeypatch.setattr(product_command, "_resolve_version", lambda conn, args: version)
    monkeypatch.setattr(product_command.product_service, "get_product", lambda conn, product_id: product)
    monkeypatch.setattr(product_command.project_service, "get_project", lambda conn, project_id: project)
    monkeypatch.setattr(product_command, "_resolve_project", lambda conn, args: project)
    monkeypatch.setattr(product_command, "_with_db", lambda callback: callback(object()))

    def fake_bind_code_link(conn, **kwargs):
        return {"id": 31, **kwargs, "status": "active"}

    def fake_unbind_code_link(conn, **kwargs):
        return {
            "id": kwargs["link_id"],
            "project_id": 7,
            "branch_name": "release/V2.0",
            "status": "inactive",
        }

    monkeypatch.setattr(product_command.product_version_service, "bind_code_link", fake_bind_code_link)
    monkeypatch.setattr(product_command.product_version_service, "unbind_code_link", fake_unbind_code_link)
    monkeypatch.setattr(
        product_command.product_version_service,
        "get_bound_branch",
        lambda conn, product_version_id, project_id: {
            "product_version_id": product_version_id,
            "project_id": project_id,
            "branch_name": "release/V2.0",
            "branch": "release/V2.0",
        },
    )
    monkeypatch.setattr(
        product_command.product_version_service,
        "list_branches",
        lambda conn, version_id: [
            {
                "product_version_id": version_id,
                "project_id": 7,
                "branch_name": "release/V2.0",
                "branch": "release/V2.0",
            }
        ],
    )
    monkeypatch.setattr(
        product_command.product_version_service,
        "remove_branch",
        lambda conn, version_id, project_id: True,
    )
    monkeypatch.setattr(
        product_command.branch_graph_repo,
        "get_by_project_branch",
        lambda conn, project_id, branch_name: graph,
    )
    monkeypatch.setattr(
        product_command.neo4j_config_service,
        "load_neo4j_config",
        lambda project: ({"neo4j_uri": "bolt://neo4j:7687"}, None),
    )
    monkeypatch.setattr(
        product_command.branch_graph_neo4j_service,
        "code_node_exists",
        lambda **kwargs: kwargs["code_node_id"] == "Function:src/a.py:handle",
    )
    monkeypatch.setattr(
        product_command.branch_graph_neo4j_service,
        "upsert_doc_code_link",
        lambda **kwargs: neo4j_actions.append(("upsert", kwargs)) or {"status": "linked", "written": 1},
    )
    monkeypatch.setattr(
        product_command.branch_graph_neo4j_service,
        "delete_doc_code_link",
        lambda **kwargs: neo4j_actions.append(("delete", kwargs)) or {"status": "deleted", "deleted": 1},
    )
    monkeypatch.setattr(
        product_command.branch_graph_neo4j_service,
        "list_doc_code_facts",
        lambda **kwargs: [
            {
                "doc_id": "DOC-1",
                "doc_node_id": "section-1",
                "relation_type": "IMPLEMENTS",
                "code_node": {"node_id": "Function:src/a.py:handle"},
            }
        ],
    )

    facts_payload = product_command.handle_version_code_facts(
        SimpleNamespace(command_name="product version code-facts", doc_id=None, node_types=["Function"])
    )
    assert facts_payload["ok"] is True
    assert facts_payload["data"]["code_facts"][0]["code_node"]["node_id"] == "Function:src/a.py:handle"
    assert facts_payload["data"]["storage_status"] == "neo4j"

    link_payload = product_command.handle_version_link_code(
        SimpleNamespace(
            command_name="product version link-code",
            doc_id="DOC-1",
            doc_node_id=None,
            code_project_id=7,
            code_project_name=None,
            code_node_id="Function:src/a.py:handle",
            locator_json=None,
            relation_type="IMPLEMENTS",
            unlink=False,
            link_id=None,
            source="manual",
            confidence=None,
        )
    )
    assert link_payload["ok"] is True
    assert link_payload["data"]["link"]["id"] == 31
    assert link_payload["data"]["link_action"] == "bind"
    assert link_payload["data"]["mutation_action"] == "bind"
    assert link_payload["data"]["mutation_target"] == "code_link"
    assert link_payload["data"]["mutation_status"] == "active"
    assert link_payload["data"]["graph_status"] == "ready"
    assert link_payload["data"]["neo4j_link"]["status"] == "linked"
    assert link_payload["data"]["code_locator"] == {"code_node_id": "Function:src/a.py:handle"}
    assert neo4j_actions[-1][0] == "upsert"
    assert neo4j_actions[-1][1]["version_scope"] == {
        "product_version_id": 23,
        "product_name": "Product",
        "version_name": "V1",
        "project_name": "Code Project",
    }

    unlink_payload = product_command.handle_version_link_code(
        SimpleNamespace(
            command_name="product version link-code",
            doc_id=None,
            doc_node_id=None,
            code_project_id=7,
            code_project_name=None,
            code_node_id=None,
            locator_json=None,
            relation_type=None,
            unlink=True,
            link_id=12,
            source="manual",
            confidence=None,
        )
    )
    assert unlink_payload["ok"] is True
    assert unlink_payload["data"]["link_action"] == "unlink"
    assert unlink_payload["data"]["mutation_action"] == "unlink"
    assert unlink_payload["data"]["mutation_target"] == "code_link"
    assert unlink_payload["data"]["mutation_status"] == "inactive"
    assert unlink_payload["data"]["link_id"] == 12
    assert unlink_payload["data"]["link"]["status"] == "inactive"
    assert unlink_payload["data"]["neo4j_link"]["status"] == "deleted"
    assert neo4j_actions[-1][0] == "delete"

    unbind_payload = product_command.handle_version_unbind_branch(
        SimpleNamespace(
            command_name="product version unbind-branch",
            version_id=23,
            product_id=None,
            product_code=None,
            version_name=None,
            project_id=7,
            project_name=None,
        )
    )
    assert unbind_payload["ok"] is True
    assert unbind_payload["data"]["binding_removed"] is True
    assert unbind_payload["data"]["mutation_action"] == "unbind"
    assert unbind_payload["data"]["mutation_target"] == "branch"
    assert unbind_payload["data"]["mutation_status"] == "removed"


def test_product_version_bind_branch_auto_refreshes_missing_graph(monkeypatch):
    from service.cli.commands import product as product_command

    version = {"id": 23, "product_id": 5, "version_name": "V1"}
    product = {"id": 5, "name": "Product"}
    project = {"id": 7, "name": "Code Project", "product_id": 5}
    binding = {"id": 11, "product_version_id": 23, "project_id": 7, "branch_name": "main"}
    refreshed = {"graph_id": 99, "graph_action": "full_replace", "head_commit": "abc", "node_count": 4, "edge_count": 3}

    monkeypatch.setattr(product_command, "_resolve_version", lambda conn, args: version)
    monkeypatch.setattr(product_command.product_service, "get_product", lambda conn, product_id: product)
    monkeypatch.setattr(product_command, "_resolve_project", lambda conn, args: project)
    monkeypatch.setattr(product_command.product_version_service, "set_branch", lambda conn, version_id, project_id, branch: binding)
    monkeypatch.setattr(product_command.branch_graph_repo, "get_by_project_branch", lambda conn, project_id, branch_name: None)
    monkeypatch.setattr(product_command.project_service, "refresh_graph", lambda conn, project_id, branch: refreshed)
    monkeypatch.setattr(product_command, "_with_db", lambda callback: callback(object()))

    payload = product_command.handle_version_bind_branch(
        SimpleNamespace(
            command_name="product version bind-branch",
            version_id=23,
            product_id=None,
            product_code=None,
            version_name=None,
            project_id=7,
            project_name=None,
            branch="main",
        )
    )

    assert payload["ok"] is True
    assert payload["data"]["graph_status"] == "ready"
    assert payload["data"]["graph_action"] == "auto_refresh"
    assert payload["data"]["graph"]["graph_id"] == 99
