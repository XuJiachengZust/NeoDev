"""Impact analysis service: create task (main + commits) in one transaction (Phase 3)."""

from service.repositories import commit_repository as commit_repo
from service.repositories import impact_analysis_repository as impact_repo
from service.repositories import project_repository as project_repo


def list_analyses(conn, project_id: int) -> list[dict] | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    return impact_repo.list_by_project_id(conn, project_id)


def get_analysis(conn, project_id: int, analysis_id: int) -> dict | None:
    if project_repo.find_by_id(conn, project_id) is None:
        return None
    row = impact_repo.find_by_id(conn, analysis_id)
    if row is None or row.get("project_id") != project_id:
        return None
    row["commit_ids"] = impact_repo.get_commit_ids(conn, analysis_id)
    return row


def create_analysis(
    conn, project_id: int, commit_ids: list[int], status: str = "pending"
) -> tuple[dict | None, str | None]:
    """Returns (analysis_dict, error). error in ('not_found', 'invalid_commits')."""
    if project_repo.find_by_id(conn, project_id) is None:
        return None, "not_found"
    if not commit_ids:
        return None, "empty_commits"
    for cid in commit_ids:
        c = commit_repo.find_by_id(conn, cid)
        if c is None or c.get("project_id") != project_id:
            return None, "invalid_commits"
    row = impact_repo.create(conn, project_id, status)
    impact_repo.add_commits(conn, row["id"], commit_ids)
    row["commit_ids"] = commit_ids
    return row, None
