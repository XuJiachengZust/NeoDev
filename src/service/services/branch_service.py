"""Branch service: persist git branches and list for UI binding."""

import os
from pathlib import Path

from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url

from service import git_ops
from service.path_allowlist import ensure_path_allowed
from service.repositories import branch_repository as branch_repo
from service.repositories import project_repository as project_repo


def _is_remote_url(repo_path: str) -> bool:
    value = (repo_path or "").strip()
    return (
        value.startswith("http://")
        or value.startswith("https://")
        or value.startswith("git@")
        or ("://" in value and not os.path.isdir(value))
    )


def _default_clone_base() -> str:
    # branch_service.py -> services -> service -> src -> NeoDev -> parent / repos
    neodev_root = Path(__file__).resolve().parent.parent.parent.parent
    return str((neodev_root.parent / "repos").resolve())


def _resolve_scan_repo_path(conn, project_id: int, project: dict) -> str:
    repo_path = (project.get("repo_path") or "").strip()
    if not repo_path or not _is_remote_url(repo_path):
        return repo_path

    clone_base = os.environ.get("REPO_CLONE_BASE", "").strip() or _default_clone_base()
    target_path = os.path.join(clone_base, str(project_id))
    ensure_path_allowed(clone_base)
    ensure_path_allowed(target_path)

    local_root = ensure_repo_from_url(
        repo_path,
        target_path,
        branch=None,
        username=project.get("repo_username"),
        password=project.get("repo_password"),
    )
    if local_root != repo_path:
        project_repo.update(conn, project_id, repo_path=local_root)
    return local_root


def list_project_branches(conn, project_id: int) -> tuple[list[str] | None, str | None]:
    """Returns (branches, err). Sync from git when repo_path is valid, then read from table."""
    project = project_repo.find_by_id(conn, project_id)
    if project is None:
        return None, "not_found"

    scan_repo_path = _resolve_scan_repo_path(conn, project_id, project)
    if scan_repo_path:
        live_branches = git_ops.get_branches(scan_repo_path)
        if live_branches:
            branch_repo.upsert_many(conn, project_id, live_branches)

    return branch_repo.list_by_project_id(conn, project_id), None

