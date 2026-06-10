from service.services.git_consistency_service import GitConsistencyError
from service.cli.errors import CliError


class FakeConn:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class FailingCommitConn(FakeConn):
    def commit(self):
        self.commits += 1
        raise RuntimeError("commit failed")


def test_apply_post_push_update_runs_doc_code_and_graph_in_one_transaction(monkeypatch):
    from service.services import post_push_update_service

    conn = FakeConn()
    calls = {}
    payload = {
        "project": {"project_id": 13, "project_name": "NeoDev", "doc_binding_id": 7},
        "branch": "main",
        "commit_range": ["d" * 40, "c" * 40],
        "commit_results": [
            {
                "commit_sha": "d" * 40,
                "scope": "document",
                "documents": ["docs/requirements/example.md"],
            },
            {
                "commit_sha": "c" * 40,
                "scope": "code",
                "doc_change_id": "d" * 40,
                "commit_message": "feat: implement\n\nDocChange-ID: " + "d" * 40,
            },
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        post_push_update_service.doc_import_service,
        "import_binding",
        lambda conn, doc_binding_id, force=False: {
            "doc_binding_id": doc_binding_id,
            "documents": [{"id": 21, "relative_path": "requirements/example.md"}],
        },
    )

    def fake_register_doc_change(conn, **kwargs):
        calls["register"] = kwargs
        return {
            "doc_change": {
                "id": 31,
                "doc_change_id": kwargs["doc_change_id"],
                "status": "pending_implementation",
            },
            "document": {"id": kwargs["document_id"]},
        }

    monkeypatch.setattr(post_push_update_service.doc_change_service, "register_doc_change", fake_register_doc_change)

    def fake_verify(conn, **kwargs):
        calls["verify"] = kwargs
        return {
            "status": "verified",
            "commit_sha": kwargs["commit_sha"],
            "doc_change_id": "d" * 40,
        }

    monkeypatch.setattr(post_push_update_service.git_consistency_service, "verify_doc_change", fake_verify)

    def fake_refresh(conn, **kwargs):
        calls["refresh"] = kwargs
        return {
            "status": "completed",
            "head_commit": "c" * 40,
            "node_count": 3,
            "edge_count": 2,
        }

    monkeypatch.setattr(post_push_update_service.project_service, "refresh_graph", fake_refresh)

    result = post_push_update_service.apply_post_push_update(conn, payload)

    assert result["status"] == "completed"
    assert result["atomic"] is True
    assert result["transaction_status"] == "committed"
    assert result["rollback_status"] == "not_needed"
    assert result["doc_import_results"][0]["doc_binding_id"] == 7
    assert result["docchange_register_results"][0]["doc_change_id"] == "d" * 40
    assert result["docchange_link_results"][0]["commit_sha"] == "c" * 40
    assert result["graph_refresh_result"]["head_commit"] == "c" * 40
    assert calls["register"]["document_id"] == 21
    assert calls["verify"]["project_id"] == 13
    assert calls["refresh"]["commit"] is False
    assert calls["refresh"]["commit_failure_state"] is False
    assert calls["refresh"]["restore_neo4j_on_error"] is True
    assert conn.commits == 1
    assert conn.rollbacks == 0


def test_apply_post_push_update_rolls_back_when_docchange_verification_fails(monkeypatch):
    from service.services import post_push_update_service

    conn = FakeConn()
    payload = {
        "project": {"project_id": 13},
        "branch": "main",
        "commit_range": ["c" * 40],
        "commit_results": [
            {
                "commit_sha": "c" * 40,
                "scope": "code",
                "doc_change_id": "d" * 40,
                "commit_message": "feat: implement\n\nDocChange-ID: " + "d" * 40,
            }
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )

    def fail_verify(conn, **kwargs):
        raise GitConsistencyError(
            category="not_found",
            message="doc change not found",
            details={"dangerous_commit_required": True},
        )

    monkeypatch.setattr(post_push_update_service.git_consistency_service, "verify_doc_change", fail_verify)

    try:
        post_push_update_service.apply_post_push_update(conn, payload)
    except post_push_update_service.PostPushUpdateError as exc:
        assert exc.category == "not_found"
        assert exc.details["rollback_status"] == "rolled_back"
    else:
        raise AssertionError("expected post-push update failure")

    assert conn.commits == 0
    assert conn.rollbacks == 1


def test_apply_post_push_update_commits_when_graph_refresh_skips_unchanged(monkeypatch):
    from service.services import post_push_update_service

    conn = FakeConn()
    payload = {
        "project": {"project_id": 13, "doc_binding_id": 7},
        "branch": "main",
        "commit_range": ["d" * 40],
        "commit_results": [
            {
                "commit_sha": "d" * 40,
                "scope": "document",
                "documents": ["docs/requirements/example.md"],
            }
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        post_push_update_service.doc_import_service,
        "import_binding",
        lambda conn, doc_binding_id, force=False: {
            "doc_binding_id": doc_binding_id,
            "documents": [{"id": 21, "relative_path": "docs/requirements/example.md"}],
        },
    )
    monkeypatch.setattr(
        post_push_update_service.doc_change_service,
        "register_doc_change",
        lambda conn, **kwargs: {"doc_change": {"doc_change_id": kwargs["doc_change_id"]}},
    )
    monkeypatch.setattr(
        post_push_update_service.project_service,
        "refresh_graph",
        lambda conn, **kwargs: {
            "graph_action": "skipped_unchanged",
            "head_commit": "c" * 40,
        },
    )

    result = post_push_update_service.apply_post_push_update(conn, payload)

    assert result["transaction_status"] == "committed"
    assert result["graph_refresh_result"]["graph_action"] == "skipped_unchanged"
    assert conn.commits == 1
    assert conn.rollbacks == 0


def test_apply_post_push_update_restores_neo4j_when_commit_fails_after_graph_replace(monkeypatch):
    from service.services import post_push_update_service

    conn = FailingCommitConn()
    restored = {}
    payload = {
        "project": {"project_id": 13},
        "branch": "main",
        "commit_range": ["c" * 40],
        "commit_results": [
            {
                "commit_sha": "c" * 40,
                "scope": "code",
                "doc_change_id": "d" * 40,
                "commit_message": "feat: implement\n\nDocChange-ID: " + "d" * 40,
            }
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        post_push_update_service.git_consistency_service,
        "verify_doc_change",
        lambda conn, **kwargs: {"status": "verified", "commit_sha": kwargs["commit_sha"]},
    )
    monkeypatch.setattr(
        post_push_update_service.project_service,
        "refresh_graph",
        lambda conn, **kwargs: {
            "graph_action": "full_replace",
            "head_commit": "c" * 40,
            "_neo4j_restore": {
                "config": {"neo4j_uri": "bolt://neo4j:7687"},
                "database": None,
                "snapshot": {"project_id": 13, "branch_name": "main", "nodes": [], "relationships": []},
            },
        },
    )

    def fake_restore(**kwargs):
        restored.update(kwargs)
        return {"status": "restored", "nodes_restored": 0, "relationships_restored": 0}

    monkeypatch.setattr(post_push_update_service.branch_graph_neo4j_service, "restore_branch_graph_snapshot", fake_restore)

    try:
        post_push_update_service.apply_post_push_update(conn, payload)
    except post_push_update_service.PostPushUpdateError as exc:
        assert exc.category == "internal_error"
        assert exc.details["rollback_status"] == "rolled_back"
        assert exc.details["graph_refresh_result"]["graph_action"] == "full_replace"
        assert "_neo4j_restore" not in exc.details["graph_refresh_result"]
        assert exc.details["neo4j_restore_result"]["status"] == "restored"
    else:
        raise AssertionError("expected commit failure")

    assert restored["snapshot"]["project_id"] == 13
    assert conn.commits == 1
    assert conn.rollbacks >= 1


def test_apply_post_push_update_reports_rollback_failed_when_neo4j_restore_fails(monkeypatch):
    from service.services import post_push_update_service

    conn = FailingCommitConn()
    payload = {
        "project": {"project_id": 13},
        "branch": "main",
        "commit_range": ["c" * 40],
        "commit_results": [
            {
                "commit_sha": "c" * 40,
                "scope": "code",
                "doc_change_id": "d" * 40,
                "commit_message": "feat: implement\n\nDocChange-ID: " + "d" * 40,
            }
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        post_push_update_service.git_consistency_service,
        "verify_doc_change",
        lambda conn, **kwargs: {"status": "verified", "commit_sha": kwargs["commit_sha"]},
    )
    monkeypatch.setattr(
        post_push_update_service.project_service,
        "refresh_graph",
        lambda conn, **kwargs: {
            "graph_action": "full_replace",
            "head_commit": "c" * 40,
            "_neo4j_restore": {
                "config": {"neo4j_uri": "bolt://neo4j:7687"},
                "database": None,
                "snapshot": {"project_id": 13, "branch_name": "main", "nodes": [], "relationships": []},
            },
        },
    )
    monkeypatch.setattr(
        post_push_update_service.branch_graph_neo4j_service,
        "restore_branch_graph_snapshot",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("restore failed")),
    )

    try:
        post_push_update_service.apply_post_push_update(conn, payload)
    except post_push_update_service.PostPushUpdateError as exc:
        assert exc.category == "internal_error"
        assert exc.details["rollback_status"] == "rollback_failed"
        assert exc.details["neo4j_restore_error"] == "restore failed"
        assert "_neo4j_restore" not in exc.details["graph_refresh_result"]
    else:
        raise AssertionError("expected commit failure")

    assert conn.commits == 1
    assert conn.rollbacks >= 1


def test_apply_post_push_update_rolls_back_doc_work_when_graph_refresh_fails(monkeypatch):
    from service.services import post_push_update_service

    conn = FakeConn()
    payload = {
        "project": {"project_id": 13, "doc_binding_id": 7},
        "branch": "main",
        "commit_range": ["d" * 40],
        "commit_results": [
            {
                "commit_sha": "d" * 40,
                "scope": "document",
                "documents": ["docs/requirements/example.md"],
            }
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        post_push_update_service.doc_import_service,
        "import_binding",
        lambda conn, doc_binding_id, force=False: {
            "doc_binding_id": doc_binding_id,
            "documents": [{"id": 21, "relative_path": "docs/requirements/example.md"}],
        },
    )
    monkeypatch.setattr(
        post_push_update_service.doc_change_service,
        "register_doc_change",
        lambda conn, **kwargs: {"doc_change": {"doc_change_id": kwargs["doc_change_id"]}},
    )

    def fail_refresh(conn, **kwargs):
        raise post_push_update_service.project_service.ProjectServiceError(
            category="internal_error",
            message="graph refresh failed",
            details={"phase": "neo4j_replace"},
        )

    monkeypatch.setattr(post_push_update_service.project_service, "refresh_graph", fail_refresh)

    try:
        post_push_update_service.apply_post_push_update(conn, payload)
    except post_push_update_service.PostPushUpdateError as exc:
        assert exc.category == "internal_error"
        assert exc.details["rollback_status"] == "rolled_back"
        assert exc.details["phase"] == "neo4j_replace"
    else:
        raise AssertionError("expected graph refresh failure")

    assert conn.commits == 0
    assert conn.rollbacks == 1


def test_apply_post_push_update_reports_rollback_failed_when_sync_restore_fails(monkeypatch):
    from service.services import post_push_update_service
    from service.services import sync_service

    conn = FakeConn()
    payload = {
        "project": {"project_id": 13},
        "branch": "main",
        "commit_range": ["c" * 40],
        "commit_results": [
            {
                "commit_sha": "c" * 40,
                "scope": "code",
                "doc_change_id": "d" * 40,
                "commit_message": "feat: implement\n\nDocChange-ID: " + "d" * 40,
            }
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        post_push_update_service.git_consistency_service,
        "verify_doc_change",
        lambda conn, **kwargs: {"status": "verified", "commit_sha": kwargs["commit_sha"]},
    )

    def fail_refresh(conn, **kwargs):
        raise sync_service.GraphRefreshRollbackError(
            "graph refresh failed; Neo4j restore failed: restore failed",
            restore_error=RuntimeError("restore failed"),
        )

    monkeypatch.setattr(post_push_update_service.project_service, "refresh_graph", fail_refresh)

    try:
        post_push_update_service.apply_post_push_update(conn, payload)
    except post_push_update_service.PostPushUpdateError as exc:
        assert exc.category == "internal_error"
        assert exc.details["rollback_status"] == "rollback_failed"
        assert exc.details["neo4j_restore_error"] == "restore failed"
    else:
        raise AssertionError("expected graph refresh rollback failure")

    assert conn.commits == 0
    assert conn.rollbacks == 1


def test_apply_post_push_update_preserves_project_service_rollback_status(monkeypatch):
    from service.services import post_push_update_service

    conn = FakeConn()
    payload = {
        "project": {"project_id": 13},
        "branch": "main",
        "commit_range": ["c" * 40],
        "commit_results": [
            {
                "commit_sha": "c" * 40,
                "scope": "code",
                "doc_change_id": "d" * 40,
                "commit_message": "feat: implement\n\nDocChange-ID: " + "d" * 40,
            }
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        post_push_update_service.git_consistency_service,
        "verify_doc_change",
        lambda conn, **kwargs: {"status": "verified", "commit_sha": kwargs["commit_sha"]},
    )

    def fail_refresh(conn, **kwargs):
        raise post_push_update_service.project_service.ProjectServiceError(
            category="internal_error",
            message="graph refresh rollback failed",
            details={"rollback_status": "rollback_failed", "neo4j_restore_error": "restore failed"},
        )

    monkeypatch.setattr(post_push_update_service.project_service, "refresh_graph", fail_refresh)

    try:
        post_push_update_service.apply_post_push_update(conn, payload)
    except post_push_update_service.PostPushUpdateError as exc:
        assert exc.category == "internal_error"
        assert exc.details["rollback_status"] == "rollback_failed"
        assert exc.details["neo4j_restore_error"] == "restore failed"
    else:
        raise AssertionError("expected project service rollback failure")

    assert conn.rollbacks == 1


def test_apply_post_push_update_preserves_git_consistency_rollback_status(monkeypatch):
    from service.services import post_push_update_service

    conn = FakeConn()
    payload = {
        "project": {"project_id": 13},
        "branch": "main",
        "commit_range": ["c" * 40],
        "commit_results": [
            {
                "commit_sha": "c" * 40,
                "scope": "code",
                "doc_change_id": "d" * 40,
                "commit_message": "feat: implement\n\nDocChange-ID: " + "d" * 40,
            }
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )

    def fail_verify(conn, **kwargs):
        raise GitConsistencyError(
            category="internal_error",
            message="verify rollback failed",
            details={"rollback_status": "rollback_failed"},
        )

    monkeypatch.setattr(post_push_update_service.git_consistency_service, "verify_doc_change", fail_verify)

    try:
        post_push_update_service.apply_post_push_update(conn, payload)
    except post_push_update_service.PostPushUpdateError as exc:
        assert exc.details["rollback_status"] == "rollback_failed"
    else:
        raise AssertionError("expected git consistency failure")

    assert conn.rollbacks == 1


def test_apply_post_push_update_preserves_cli_error_rollback_status(monkeypatch):
    from service.services import post_push_update_service

    conn = FakeConn()
    payload = {
        "project": {"project_id": 13, "doc_binding_id": 7},
        "branch": "main",
        "commit_range": ["d" * 40],
        "commit_results": [
            {
                "commit_sha": "d" * 40,
                "scope": "document",
                "documents": ["docs/requirements/example.md"],
            }
        ],
    }

    monkeypatch.setattr(
        post_push_update_service.project_repository,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "name": "NeoDev"},
    )

    def fail_import(conn, doc_binding_id, force=False):
        raise CliError(
            category="internal_error",
            message="import rollback failed",
            details={"rollback_status": "rollback_failed"},
        )

    monkeypatch.setattr(post_push_update_service.doc_import_service, "import_binding", fail_import)

    try:
        post_push_update_service.apply_post_push_update(conn, payload)
    except post_push_update_service.PostPushUpdateError as exc:
        assert exc.details["rollback_status"] == "rollback_failed"
    else:
        raise AssertionError("expected CLI failure")

    assert conn.rollbacks == 1
