"""Sync service (Phase 4): sync Git commits to PG for a project."""

from service import git_ops
from service.repositories import commit_repository as commit_repo
from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo


def sync_commits_for_project(conn, project_id: int) -> dict | None:
    """
    Sync commits from Git repo to PG for all versions of the project.
    Returns summary dict with project_id, versions_synced, commits_synced; or None if project not found.
    """
    project = project_repo.find_by_id(conn, project_id)
    if not project:
        return None
    repo_path = (project.get("repo_path") or "").strip()
    versions = version_repo.list_by_project_id(conn, project_id)
    total_commits = 0
    for ver in versions:
        branch = ver.get("branch")
        if not branch:
            continue
        commits = git_ops.list_commits(repo_path, branch=branch)
        if commits:
            n = commit_repo.upsert_commits(
                conn, project_id, ver["id"], commits
            )
            total_commits += n
    conn.commit()
    return {
        "project_id": project_id,
        "versions_synced": len(versions),
        "commits_synced": total_commits,
    }
