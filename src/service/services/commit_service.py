"""Commit service: read-only (Phase 3)."""

from service.repositories import commit_repository as commit_repo
from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo


def list_commits(
    conn,
    project_id: int,
    version_id: int | None = None,
    requirement_id: int | None = None,
) -> list[dict] | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    return commit_repo.list_by_project_id(
        conn, project_id, version_id=version_id, requirement_id=requirement_id
    )


def list_commits_by_version(
    conn, project_id: int, version_id: int
) -> list[dict] | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    ver = version_repo.find_by_id(conn, version_id)
    if ver is None or ver.get("project_id") != project_id:
        return None
    return commit_repo.list_by_version_id(conn, project_id, version_id)
