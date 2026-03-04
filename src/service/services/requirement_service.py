"""Requirement service: orchestration + requirement_commits (Phase 3)."""

from service.repositories import commit_repository as commit_repo
from service.repositories import project_repository as project_repo
from service.repositories import requirement_repository as req_repo


def list_requirements(conn, project_id: int) -> list[dict] | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    return req_repo.list_by_project_id(conn, project_id)


def get_requirement(conn, project_id: int, requirement_id: int) -> dict | None:
    proj = project_repo.find_by_id(conn, project_id)
    if proj is None:
        return None
    req = req_repo.find_by_id(conn, requirement_id)
    if req is None or req.get("project_id") != project_id:
        return None
    req["commit_ids"] = req_repo.get_commit_ids(conn, requirement_id)
    return req


def create_requirement(
    conn,
    project_id: int,
    title: str,
    description: str | None = None,
    external_id: str | None = None,
) -> dict | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    return req_repo.create(conn, project_id, title, description, external_id)


def update_requirement(
    conn,
    project_id: int,
    requirement_id: int,
    title: str | None = None,
    description: str | None = None,
    external_id: str | None = None,
) -> dict | None:
    req = get_requirement(conn, project_id, requirement_id)
    if req is None:
        return None
    return req_repo.update(conn, requirement_id, title, description, external_id)


def delete_requirement(conn, project_id: int, requirement_id: int) -> bool:
    req = get_requirement(conn, project_id, requirement_id)
    if req is None:
        return False
    return req_repo.delete(conn, requirement_id)


def _commits_belong_to_project(conn, project_id: int, commit_ids: list[int]) -> bool:
    for cid in commit_ids:
        c = commit_repo.find_by_id(conn, cid)
        if c is None or c.get("project_id") != project_id:
            return False
    return True


def bind_requirement_commits(
    conn, project_id: int, requirement_id: int, commit_ids: list[int]
) -> str | None:
    """Returns None on success, 'not_found' or 'invalid_commits' on error."""
    req = get_requirement(conn, project_id, requirement_id)
    if req is None:
        return "not_found"
    if not commit_ids:
        return None
    if not _commits_belong_to_project(conn, project_id, commit_ids):
        return "invalid_commits"
    req_repo.bind_commits(conn, requirement_id, commit_ids)
    return None


def unbind_requirement_commits(
    conn, project_id: int, requirement_id: int, commit_ids: list[int]
) -> str | None:
    req = get_requirement(conn, project_id, requirement_id)
    if req is None:
        return "not_found"
    req_repo.unbind_commits(conn, requirement_id, commit_ids)
    return None
