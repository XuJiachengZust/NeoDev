"""Version service: orchestration (Phase 3)."""

from psycopg2 import IntegrityError

from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo


def list_versions(conn, project_id: int) -> list[dict] | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    return version_repo.list_by_project_id(conn, project_id)


def create_version(
    conn, project_id: int, branch: str | None, version_name: str | None = None
) -> tuple[dict | None, str | None]:
    """Returns (version_dict, error_detail). error_detail for 409 duplicate. branch is optional."""
    if project_repo.find_by_id(conn, project_id) is None:
        return None, "not_found"
    if branch is not None and not branch.strip():
        branch = None
    try:
        row = version_repo.create(conn, project_id, branch, version_name)
        return row, None
    except IntegrityError:
        return None, "duplicate_branch"


def delete_version(conn, project_id: int, version_id: int) -> str | None:
    """Returns None on success, 'not_found' if project or version missing."""
    if project_repo.find_by_id(conn, project_id) is None:
        return "not_found"
    ver = version_repo.find_by_id(conn, version_id)
    if ver is None or ver.get("project_id") != project_id:
        return "not_found"
    version_repo.delete(conn, version_id)
    return None
