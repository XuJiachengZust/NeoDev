"""Project service: orchestration only (Phase 3)."""

import logging

from service.repositories import project_repository as repo

logger = logging.getLogger(__name__)


def list_projects(conn) -> list[dict]:
    return repo.list_all(conn)


def get_project(conn, project_id: int) -> dict | None:
    return repo.find_by_id(conn, project_id)


def _init_repo_and_sync(conn, project: dict) -> dict:
    """创建项目后自动：克隆/解析仓库 → 获取默认分支 → 创建版本 → 同步提交+构建图。
    返回 init_result dict，不会抛出异常。"""
    from service import git_ops
    from service.repositories import branch_repository as branch_repo
    from service.services import sync_service, version_service

    project_id = project["id"]
    result = {"default_branch": None, "version_id": None, "sync": None, "error": None}

    try:
        local_root = sync_service._resolve_local_repo(project, project_id)
        git_ops.fetch_repo(local_root)
    except Exception as e:
        logger.warning("project_id=%s: 初始化仓库失败: %s", project_id, e)
        result["error"] = f"仓库拉取失败: {e}"
        return result

    # 持久化分支列表
    try:
        live_branches = git_ops.get_branches(local_root)
        if live_branches:
            branch_repo.upsert_many(conn, project_id, live_branches)
    except Exception as e:
        logger.warning("project_id=%s: 同步分支列表失败: %s", project_id, e)

    # 获取默认分支
    default_branch = git_ops.get_default_branch(local_root)
    if not default_branch:
        result["error"] = "无法检测默认分支"
        return result
    result["default_branch"] = default_branch

    # 创建默认版本
    version, err = version_service.create_version(conn, project_id, default_branch)
    if err or not version:
        result["error"] = f"创建默认版本失败: {err}"
        return result
    conn.commit()
    result["version_id"] = version["id"]

    # 同步提交并构建图
    try:
        sync_result = sync_service.sync_commits_for_version(conn, project_id, version["id"])
        result["sync"] = sync_result
    except Exception as e:
        logger.warning("project_id=%s: 同步提交/构建图失败: %s", project_id, e)
        result["error"] = f"同步提交失败: {e}"

    return result


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
) -> dict:
    project = repo.create(
        conn, name, repo_path, watch_enabled, neo4j_database, neo4j_identifier,
        repo_username=repo_username, repo_password=repo_password,
        repo_url=repo_url,
    )
    conn.commit()

    # 自动拉取仓库并构建图
    init_result = _init_repo_and_sync(conn, project)
    project["init_result"] = init_result
    logger.info("project_id=%s: 创建完成, init_result=%s", project["id"], init_result)
    return project


def update_project(conn, project_id: int, **kwargs) -> dict | None:
    return repo.update(conn, project_id, **kwargs)


def delete_project(conn, project_id: int) -> bool:
    return repo.delete(conn, project_id)
