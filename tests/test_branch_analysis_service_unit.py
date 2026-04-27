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


def test_analyze_version_branch_wraps_preprocess_and_returns_status(monkeypatch):
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
                "analysis_action": "full",
                "progress": {"stage": "completed", "done": 1, "total": 1},
            },
        }
    ]
    _patch_valid_scope(monkeypatch, status_rows=status_rows)
    calls = []

    def fake_run_preprocess(conn, project_id, branch, force=False):
        calls.append({"project_id": project_id, "branch": branch, "force": force})
        return {"status": "completed"}

    monkeypatch.setattr(
        branch_analysis_service.ai_preprocessor_service,
        "run_preprocess",
        fake_run_preprocess,
    )

    result = branch_analysis_service.analyze_version_branch(
        object(),
        product_version_id=23,
        project_id=11,
        branch="release/unit",
        force=True,
    )

    assert calls == [{"project_id": 11, "branch": "release/unit", "force": True}]
    task = result["analysis_task"]
    assert task["analysis_task_id"] == 31
    assert task["product_version_id"] == 23
    assert task["project_id"] == 11
    assert task["branch"] == "release/unit"
    assert task["status"] == "completed"
    assert task["analysis_action"] == "full"
    assert task["progress"]["stage"] == "completed"


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
