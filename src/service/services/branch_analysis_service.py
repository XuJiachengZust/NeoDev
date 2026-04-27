"""Branch analysis orchestration for product-version scoped CLI commands."""

from dataclasses import dataclass, field
from typing import Any

from fastapi import HTTPException

from service.repositories import ai_preprocess_status_repository as status_repo
from service.services import product_service
from service.services import product_version_service
from service.services import project_service
from service.repositories import version_repository as version_repo


@dataclass(slots=True)
class BranchAnalysisError(Exception):
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def analyze_version_branch(
    conn,
    product_version_id: int,
    project_id: int,
    branch: str,
    force: bool = False,
) -> dict:
    context = _validate_scope(conn, product_version_id, project_id, branch)
    try:
        _mark_running(conn, project_id, context["branch"])
        sync_result = _sync_project_graph(conn, project_id)
        if sync_result is None:
            raise BranchAnalysisError(
                category="not_found",
                message="project not found",
                details={"project_id": project_id},
            )
        extra = {
            "analysis_action": "graph_sync",
            "ai_analysis_removed": True,
            "force_requested": bool(force),
            "progress": {"stage": "completed", "done": 1, "total": 1},
            "sync": sync_result,
        }
        status_repo.set_completed(conn, project_id, context["branch"], extra=extra)
        conn.commit()
    except HTTPException as exc:
        if exc.status_code == 404:
            raise BranchAnalysisError(category="not_found", message=str(exc.detail)) from exc
        raise BranchAnalysisError(
            category="internal_error",
            message=str(exc.detail),
            details={"status_code": exc.status_code},
        ) from exc
    except BranchAnalysisError:
        raise
    except Exception as exc:
        conn.rollback()
        status_repo.set_failed(
            conn,
            project_id,
            context["branch"],
            error_message=str(exc),
            extra={
                "analysis_action": "graph_sync",
                "ai_analysis_removed": True,
                "force_requested": bool(force),
            },
        )
        conn.commit()
        raise BranchAnalysisError(
            category="internal_error",
            message=str(exc),
            details={"project_id": project_id, "branch": context["branch"]},
        ) from exc

    analysis_task = _current_task(conn, context)
    return {
        "product": context["product"],
        "version": context["version"],
        "project": context["project"],
        "analysis_task": analysis_task,
        "sync": sync_result,
        "ai_analysis_removed": True,
    }


def _mark_running(conn, project_id: int, branch: str) -> None:
    if status_repo.has_running(conn, project_id):
        raise BranchAnalysisError(
            category="conflict",
            message="project analysis is already running",
            details={"code": "PROJECT_BUSY", "project_id": project_id},
        )
    if not status_repo.set_running(conn, project_id, branch):
        raise BranchAnalysisError(
            category="conflict",
            message="project analysis is already running",
            details={"code": "PROJECT_BUSY", "project_id": project_id},
        )
    conn.commit()


def _sync_project_graph(conn, project_id: int) -> dict | None:
    from service.services import sync_service

    return sync_service.sync_commits_for_project(conn, project_id)


def get_analysis_status(
    conn,
    product_version_id: int,
    project_id: int,
    branch: str,
) -> dict:
    context = _validate_scope(conn, product_version_id, project_id, branch)
    return {
        "product": context["product"],
        "version": context["version"],
        "project": context["project"],
        "analysis_task": _current_task(conn, context),
    }


def _validate_scope(conn, product_version_id: int, project_id: int, branch: str) -> dict:
    normalized_branch = (branch or "").strip()
    if not normalized_branch:
        raise BranchAnalysisError(
            category="invalid_argument",
            message="branch is required",
        )

    version = product_version_service.get_version(conn, product_version_id)
    if not version:
        raise BranchAnalysisError(
            category="not_found",
            message="product version not found",
            details={"product_version_id": product_version_id},
        )
    product = product_service.get_product(conn, version["product_id"])
    if not product:
        raise BranchAnalysisError(
            category="not_found",
            message="product not found",
            details={"product_id": version["product_id"]},
        )

    project = project_service.get_project(conn, project_id)
    if not project:
        raise BranchAnalysisError(
            category="not_found",
            message="project not found",
            details={"project_id": project_id},
        )

    branches = product_version_service.list_branches(conn, product_version_id)
    mapping = next((row for row in branches if row["project_id"] == project_id), None)
    if not mapping:
        raise BranchAnalysisError(
            category="invalid_scope",
            message="project is not bound to this product version",
            details={"product_version_id": product_version_id, "project_id": project_id},
        )
    if mapping["branch"] != normalized_branch:
        raise BranchAnalysisError(
            category="invalid_scope",
            message="branch is not bound to this product version project mapping",
            details={
                "product_version_id": product_version_id,
                "project_id": project_id,
                "expected_branch": mapping["branch"],
                "actual_branch": normalized_branch,
            },
        )

    return {
        "product": product,
        "version": version,
        "project": project,
        "branch_mapping": mapping,
        "branch": normalized_branch,
    }


def _current_task(conn, context: dict) -> dict:
    project_id = context["project"]["id"]
    branch = context["branch"]
    rows = status_repo.get_status(conn, project_id, branch)
    row = rows[0] if rows else {}
    extra = row.get("extra") or {}
    progress = extra.get("progress") or {}
    legacy_version = version_repo.find_by_project_and_branch(conn, project_id, branch) or {}
    analysis_action = extra.get("analysis_action") or extra.get("graph_action")
    return {
        "analysis_task_id": row.get("id"),
        "product_version_id": context["version"]["id"],
        "project_id": project_id,
        "branch": branch,
        "status": row.get("status") or "not_started",
        "analysis_action": analysis_action,
        "progress": progress,
        "current_snapshot_id": extra.get("current_snapshot_id"),
        "head_commit": extra.get("head_commit"),
        "last_parsed_commit": extra.get("last_parsed_commit")
        or legacy_version.get("last_parsed_commit"),
        "created_from_action": extra.get("created_from_action") or analysis_action,
        "started_at": row.get("started_at"),
        "finished_at": row.get("finished_at"),
        "heartbeat_at": row.get("updated_at"),
        "error_message": row.get("error_message"),
    }
