"""Project service orchestration."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from service.repositories import branch_analysis_status_repository as status_repo
from service.repositories import project_repository as repo

logger = logging.getLogger(__name__)

INIT_BRANCH = "__project_init__"
INIT_STEPS = [
    ("repository_clone", "拉取仓库"),
    ("branch_discovery", "检测分支"),
    ("default_branch", "确定默认分支"),
    ("graph_refresh", "刷新分支图谱"),
    ("completed", "完成"),
]


@dataclass(slots=True)
class ProjectServiceError(Exception):
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def list_projects(conn) -> list[dict]:
    return repo.list_all(conn)


def get_project(conn, project_id: int) -> dict | None:
    return repo.find_by_id(conn, project_id)


def find_projects_by_name(conn, name: str) -> list[dict]:
    return repo.find_by_name(conn, name)


def get_init_status(conn, project_id: int) -> dict | None:
    project = get_project(conn, project_id)
    if not project:
        return None
    rows = status_repo.get_status(conn, project_id, INIT_BRANCH)
    if not rows:
        progress = _progress("not_started", 0, "项目初始化未开始")
        return {
            "project": project,
            "init_status": {
                "status": "not_started",
                "progress": progress,
                "key_nodes": progress["key_nodes"],
                "error_message": None,
            },
        }
    row = rows[0]
    extra = row.get("extra") or {}
    progress = extra.get("progress") or _progress(row.get("status") or "unknown", 0)
    return {
        "project": project,
        "init_status": {
            "status": row.get("status"),
            "progress": progress,
            "key_nodes": extra.get("key_nodes") or progress.get("key_nodes") or [],
            "started_at": row.get("started_at"),
            "updated_at": row.get("updated_at"),
            "finished_at": row.get("finished_at"),
            "error_message": row.get("error_message"),
            "init_result": extra.get("init_result"),
        },
    }


def create_project(
    conn,
    name: str,
    repo_path: str,
    watch_enabled: bool = False,
    neo4j_database: str | None = None,
    neo4j_identifier: str | None = None,
    repo_username: str | None = None,
    repo_password: str | None = None,
    repo_url: str | None = None,
    async_init: bool = False,
    overwrite_existing: bool = False,
) -> dict:
    matches = find_projects_by_name(conn, name) if overwrite_existing else []
    if matches:
        selected = max(matches, key=lambda row: row["id"])
        project = repo.update(
            conn,
            selected["id"],
            name=name,
            repo_path=repo_path,
            repo_url=repo_url,
            watch_enabled=watch_enabled,
            neo4j_database=neo4j_database,
            neo4j_identifier=neo4j_identifier,
            repo_username=repo_username,
            repo_password=repo_password,
        )
        project["overwritten"] = True
        project["duplicate_project_ids"] = [row["id"] for row in matches if row["id"] != selected["id"]]
    else:
        project = repo.create(
            conn,
            name,
            repo_path,
            watch_enabled,
            neo4j_database,
            neo4j_identifier,
            repo_username=repo_username,
            repo_password=repo_password,
            repo_url=repo_url,
        )
        project["overwritten"] = False
        project["duplicate_project_ids"] = []
    conn.commit()

    if async_init:
        init_result = _queued_init_result(project["id"])
        project["init_result"] = init_result
        status_repo.set_running(conn, project["id"], INIT_BRANCH)
        status_repo.update_progress(conn, project["id"], INIT_BRANCH, init_result["progress"])
        conn.commit()
        _start_background_init(project["id"])
        logger.info("project_id=%s: created, background graph refresh queued", project["id"])
        return project

    init_result = _init_repo_and_refresh_default_branch(conn, project)
    project["init_result"] = init_result
    logger.info("project_id=%s: created, init_result=%s", project["id"], init_result)
    return project


def update_project(conn, project_id: int, **kwargs) -> dict | None:
    return repo.update(conn, project_id, **kwargs)


def delete_project(conn, project_id: int) -> bool:
    return repo.delete(conn, project_id)


def refresh_graph(conn, *, project_id: int, branch: str) -> dict:
    """Fetch the project repository and rebuild graph state for one branch."""
    from service.services import sync_service

    normalized_branch = _required_text(branch, "branch")
    project = get_project(conn, project_id)
    if not project:
        raise ProjectServiceError(
            category="not_found",
            message="project not found",
            details={"project_id": project_id},
        )

    result = sync_service.refresh_graph_for_branch(conn, project_id, normalized_branch)
    if result is None:
        raise ProjectServiceError(
            category="not_found",
            message="project branch refresh target not found",
            details={"project_id": project_id, "branch": normalized_branch},
        )
    result["project_id"] = project_id
    result["branch"] = normalized_branch
    result["refresh_mode"] = "project_branch_rebuild"
    return result


def _init_repo_and_refresh_default_branch(conn, project: dict) -> dict:
    from service import git_ops
    from service.repositories import branch_repository as branch_repo
    from service.services import sync_service

    project_id = project["id"]
    result = {
        "status": "running",
        "default_branch": None,
        "sync": None,
        "error": None,
    }

    try:
        _update_init_progress(conn, project_id, "repository_clone", 0, "正在拉取仓库")
        local_root = sync_service._resolve_local_repo(project, project_id)
        git_ops.fetch_repo(local_root)
    except Exception as exc:
        logger.warning("project_id=%s: repository init failed: %s", project_id, exc)
        _fail_init(conn, project_id, result, f"仓库拉取失败: {exc}")
        return result

    _update_init_progress(conn, project_id, "branch_discovery", 1, "正在检测分支")
    try:
        live_branches = git_ops.get_branches(local_root)
        if live_branches:
            branch_repo.upsert_many(conn, project_id, live_branches)
            conn.commit()
    except Exception as exc:
        logger.warning("project_id=%s: branch list sync failed: %s", project_id, exc)

    default_branch = git_ops.get_default_branch(local_root)
    if not default_branch:
        _fail_init(conn, project_id, result, "未找到默认分支")
        return result
    result["default_branch"] = default_branch
    _update_init_progress(conn, project_id, "default_branch", 2, f"默认分支: {default_branch}")

    try:
        _update_init_progress(conn, project_id, "graph_refresh", 3, f"刷新默认分支图谱: {default_branch}")
        result["sync"] = sync_service.refresh_graph_for_branch(conn, project_id, default_branch)
    except Exception as exc:
        logger.warning("project_id=%s: graph refresh failed: %s", project_id, exc)
        _fail_init(conn, project_id, result, f"图谱刷新失败: {exc}")
        return result

    _complete_init(conn, project_id, result)
    return result


def _run_background_init(project_id: int) -> None:
    import psycopg2

    from service.dependencies import get_database_url

    conn = psycopg2.connect(get_database_url())
    try:
        project = get_project(conn, project_id)
        if not project:
            logger.warning("project_id=%s: background init skipped, project not found", project_id)
            return
        _init_repo_and_refresh_default_branch(conn, project)
    except Exception:
        conn.rollback()
        logger.exception("project_id=%s: background init failed", project_id)
    finally:
        conn.close()


def _start_background_init(project_id: int) -> None:
    thread = threading.Thread(
        target=_run_background_init,
        args=(project_id,),
        name=f"neodev-project-init-{project_id}",
        daemon=True,
    )
    thread.start()


def _key_nodes(current_stage: str, done: int) -> list[dict]:
    nodes = []
    for index, (stage, label) in enumerate(INIT_STEPS, start=1):
        if index <= done:
            status = "completed"
        elif stage == current_stage:
            status = "running"
        else:
            status = "pending"
        nodes.append({"stage": stage, "label": label, "status": status})
    return nodes


def _progress(stage: str, done: int, detail: str | None = None) -> dict:
    payload = {
        "stage": stage,
        "done": done,
        "total": len(INIT_STEPS),
        "key_nodes": _key_nodes(stage, done),
    }
    if detail:
        payload["detail"] = detail
    return payload


def _ensure_init_running(conn, project_id: int) -> None:
    rows = status_repo.get_status(conn, project_id, INIT_BRANCH)
    if rows and rows[0].get("status") == "running":
        return
    status_repo.set_running(conn, project_id, INIT_BRANCH)
    conn.commit()


def _update_init_progress(conn, project_id: int, stage: str, done: int, detail: str | None = None) -> None:
    _ensure_init_running(conn, project_id)
    status_repo.update_progress(conn, project_id, INIT_BRANCH, _progress(stage, done, detail))
    conn.commit()


def _complete_init(conn, project_id: int, result: dict) -> None:
    result["status"] = "completed"
    progress = _progress("completed", len(INIT_STEPS), "图谱刷新完成")
    status_repo.set_completed(
        conn,
        project_id,
        INIT_BRANCH,
        extra={"progress": progress, "key_nodes": progress["key_nodes"], "init_result": result},
    )
    conn.commit()


def _fail_init(conn, project_id: int, result: dict, error: str) -> None:
    result["status"] = "failed"
    result["error"] = error
    progress = _progress("failed", 0, error)
    status_repo.set_failed(
        conn,
        project_id,
        INIT_BRANCH,
        error_message=error,
        extra={"progress": progress, "key_nodes": progress["key_nodes"], "init_result": result},
    )
    conn.commit()


def _queued_init_result(project_id: int) -> dict:
    progress = _progress("queued", 0, "项目已登记，后台刷新默认分支图谱")
    return {
        "status": "queued",
        "mode": "background",
        "task_branch": INIT_BRANCH,
        "default_branch": None,
        "sync": None,
        "error": None,
        "progress": progress,
        "key_nodes": progress["key_nodes"],
        "status_command": f"neodev project init-status --project-id {project_id}",
    }


def _required_text(value: str | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ProjectServiceError(
            category="invalid_argument",
            message=f"{field_name} is required",
            details={"field": field_name},
        )
    return text
