from datetime import datetime, timezone

import pytest

from service.services import branch_analysis_service


def _patch_valid_scope(monkeypatch, status_rows=None):
    monkeypatch.setattr(
        branch_analysis_service.product_version_service,
        "get_version",
        lambda conn, version_id: {"id": version_id, "product_id": 7},
    )
    monkeypatch.setattr(
        branch_analysis_service.product_service,
        "get_product",
        lambda conn, product_id: {"id": product_id, "code": "UNIT"},
    )
    monkeypatch.setattr(
        branch_analysis_service.project_service,
        "get_project",
        lambda conn, project_id: {"id": project_id, "name": "unit-project"},
    )
    monkeypatch.setattr(
        branch_analysis_service.product_version_service,
        "list_branches",
        lambda conn, version_id: [
            {"product_version_id": version_id, "project_id": 11, "branch": "release/unit"}
        ],
    )
    monkeypatch.setattr(
        branch_analysis_service.status_repo,
        "get_status",
        lambda conn, project_id, branch: status_rows or [],
    )
    monkeypatch.setattr(
        branch_analysis_service.version_repo,
        "find_by_project_and_branch",
        lambda conn, project_id, branch: None,
    )
    monkeypatch.setattr(
        branch_analysis_service,
        "branch_snapshot_service",
        type(
            "SnapshotService",
            (),
            {"get_current_snapshot": staticmethod(lambda conn, project_id, branch: None)},
        ),
        raising=False,
    )


def test_analyze_version_branch_syncs_graph_only(monkeypatch):
    now = datetime.now(timezone.utc)
    status_rows = [
        {
            "id": 31,
            "project_id": 11,
            "branch": "release/unit",
            "status": "completed",
            "started_at": now,
            "finished_at": now,
            "updated_at": now,
            "error_message": None,
            "extra": {
                "analysis_action": "graph_sync",
                "progress": {"stage": "completed", "done": 1, "total": 1},
            },
        }
    ]
    _patch_valid_scope(monkeypatch, status_rows=status_rows)
    calls = []

    def fake_sync(conn, project_id):
        calls.append({"project_id": project_id})
        return {
            "project_id": project_id,
            "versions_synced": 1,
            "commits_synced": 3,
            "graph_actions": [
                {"version_id": 5, "branch": "release/unit", "action": "full"}
            ],
            "graph_errors": None,
        }

    monkeypatch.setattr(branch_analysis_service, "_sync_project_graph", fake_sync)

    completed = []

    def fake_set_completed(conn, project_id, branch, extra=None):
        completed.append({"project_id": project_id, "branch": branch, "extra": extra})
        status_rows[0]["extra"] = extra

    monkeypatch.setattr(
        branch_analysis_service.status_repo,
        "set_completed",
        fake_set_completed,
    )

    running = []

    def fake_set_running(conn, project_id, branch):
        running.append({"project_id": project_id, "branch": branch})
        return True

    monkeypatch.setattr(
        branch_analysis_service.status_repo,
        "set_running",
        fake_set_running,
    )

    monkeypatch.setattr(
        branch_analysis_service.status_repo,
        "has_running",
        lambda conn, project_id: False,
    )

    class DummyConn:
        def commit(self):
            pass

        def rollback(self):
            pass

    result = branch_analysis_service.analyze_version_branch(
        DummyConn(),
        product_version_id=23,
        project_id=11,
        branch="release/unit",
        force=True,
    )

    assert running == [{"project_id": 11, "branch": "release/unit"}]
    assert calls == [{"project_id": 11}]
    assert completed == [
        {
            "project_id": 11,
            "branch": "release/unit",
            "extra": {
                "analysis_action": "graph_sync",
                "force_requested": True,
                "progress": {"stage": "completed", "done": 1, "total": 1},
                "sync": {
                    "project_id": 11,
                    "versions_synced": 1,
                    "commits_synced": 3,
                    "graph_actions": [
                        {"version_id": 5, "branch": "release/unit", "action": "full"}
                    ],
                    "graph_errors": None,
                },
            },
        }
    ]
    task = result["analysis_task"]
    assert task["analysis_task_id"] == 31
    assert task["product_version_id"] == 23
    assert task["project_id"] == 11
    assert task["branch"] == "release/unit"
    assert task["status"] == "completed"
    assert task["analysis_action"] == "graph_sync"
    assert task["progress"]["stage"] == "completed"
    assert result["sync"]["commits_synced"] == 3


def test_analyze_version_branch_marks_failed_when_graph_sync_fails(monkeypatch):
    _patch_valid_scope(monkeypatch, status_rows=[])

    monkeypatch.setattr(
        branch_analysis_service.status_repo,
        "has_running",
        lambda conn, project_id: False,
    )
    monkeypatch.setattr(
        branch_analysis_service.status_repo,
        "set_running",
        lambda conn, project_id, branch: True,
    )

    failed = []

    def fake_set_failed(conn, project_id, branch, error_message, extra=None):
        failed.append(
            {
                "project_id": project_id,
                "branch": branch,
                "error_message": error_message,
                "extra": extra,
            }
        )

    monkeypatch.setattr(branch_analysis_service.status_repo, "set_failed", fake_set_failed)

    def fake_sync(conn, project_id):
        raise RuntimeError("sync failed")

    monkeypatch.setattr(branch_analysis_service, "_sync_project_graph", fake_sync)

    class DummyConn:
        def commit(self):
            pass

        def rollback(self):
            pass

    with pytest.raises(branch_analysis_service.BranchAnalysisError) as exc_info:
        branch_analysis_service.analyze_version_branch(
            DummyConn(),
            product_version_id=23,
            project_id=11,
            branch="release/unit",
        )

    assert exc_info.value.category == "internal_error"
    assert "sync failed" in exc_info.value.message
    assert failed[0]["extra"]["analysis_action"] == "graph_sync"


def test_get_analysis_status_rejects_wrong_branch(monkeypatch):
    _patch_valid_scope(monkeypatch)

    with pytest.raises(branch_analysis_service.BranchAnalysisError) as exc_info:
        branch_analysis_service.get_analysis_status(
            object(),
            product_version_id=23,
            project_id=11,
            branch="feature/not-bound",
        )

    assert exc_info.value.category == "invalid_scope"
    assert exc_info.value.details["expected_branch"] == "release/unit"
    assert exc_info.value.details["actual_branch"] == "feature/not-bound"


def test_get_analysis_status_returns_not_started_without_status_row(monkeypatch):
    _patch_valid_scope(monkeypatch, status_rows=[])

    result = branch_analysis_service.get_analysis_status(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/unit",
    )

    task = result["analysis_task"]
    assert task["analysis_task_id"] is None
    assert task["status"] == "not_started"
    assert task["progress"] == {}


def test_get_analysis_status_includes_contract_snapshot_fields(monkeypatch):
    now = datetime.now(timezone.utc)
    status_rows = [
        {
            "id": 32,
            "project_id": 11,
            "branch": "release/unit",
            "status": "completed",
            "started_at": now,
            "finished_at": now,
            "updated_at": now,
            "error_message": None,
            "extra": {
                "analysis_action": "graph_sync",
            },
        }
    ]
    _patch_valid_scope(monkeypatch, status_rows=status_rows)
    monkeypatch.setattr(
        branch_analysis_service.version_repo,
        "find_by_project_and_branch",
        lambda conn, project_id, branch: {
            "id": 5,
            "project_id": project_id,
            "branch": branch,
            "last_parsed_commit": "b" * 40,
        },
    )
    monkeypatch.setattr(
        branch_analysis_service.branch_snapshot_service,
        "get_current_snapshot",
        lambda conn, project_id, branch: {
            "id": 77,
            "head_commit": "a" * 40,
            "last_parsed_commit": "a" * 40,
            "created_from_action": "incremental",
        },
    )

    result = branch_analysis_service.get_analysis_status(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/unit",
    )

    task = result["analysis_task"]
    assert task["current_snapshot_id"] == 77
    assert task["head_commit"] == "a" * 40
    assert task["last_parsed_commit"] == "a" * 40
    assert task["created_from_action"] == "incremental"
