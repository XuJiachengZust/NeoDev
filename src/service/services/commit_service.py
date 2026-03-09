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
    conn,
    project_id: int,
    version_id: int,
    *,
    message: str | None = None,
    committed_at_from: str | None = None,
    committed_at_to: str | None = None,
    id: int | None = None,
    sha: str | None = None,
) -> list[dict] | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    ver = version_repo.find_by_id(conn, version_id)
    if ver is None or ver.get("project_id") != project_id:
        return None
    if any(
        x is not None and (x != "" if isinstance(x, str) else True)
        for x in (message, committed_at_from, committed_at_to, id, sha)
    ):
        return commit_repo.list_by_version_id_filtered(
            conn,
            project_id,
            version_id,
            message=message,
            committed_at_from=committed_at_from,
            committed_at_to=committed_at_to,
            id=id,
            sha=sha,
        )
    return commit_repo.list_by_version_id(conn, project_id, version_id)
