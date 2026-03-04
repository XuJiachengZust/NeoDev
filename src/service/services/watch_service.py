"""Watch service (Phase 4): three-step trigger strategy for Git scan (copy-data / incremental / full)."""

from __future__ import annotations

from typing import Any

from service import git_ops
from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo


def _add_branch_to_nodes_if_available(driver, source_branch: str, new_branch: str, database: str | None = None) -> bool:
    """Call add_branch_to_nodes when Phase 1 is implemented; return True if called, False otherwise."""
    try:
        from gitnexus_parser.neo4j_writer import add_branch_to_nodes
        add_branch_to_nodes(driver, source_branch, new_branch, database=database)
        return True
    except (ImportError, AttributeError):
        return False


def run_once(
    conn,
    project_id: int,
    config: dict[str, Any] | None = None,
    *,
    pipeline_runner=None,
    neo4j_driver=None,
) -> dict | None:
    """
    Run one scan pass for the project: for each version (branch), decide copy-data / incremental / full,
    call pipeline or add_branch_to_nodes, and update versions.last_parsed_commit.
    Returns summary dict or None if project not found / not watchable.
    pipeline_runner(repo_path, config, branch, incremental, since_commit) for test injection.
    neo4j_driver only needed when add_branch_to_nodes is used (Phase 1).
    """
    config = config or {}
    project = project_repo.find_by_id(conn, project_id)
    if not project:
        return None
    if not project.get("watch_enabled"):
        return {"project_id": project_id, "skipped": True, "reason": "watch_disabled"}
    repo_path = (project.get("repo_path") or "").strip()
    if not repo_path:
        return {"project_id": project_id, "skipped": True, "reason": "no_repo_path"}

    versions = version_repo.list_by_project_id(conn, project_id)
    actions = []

    def run_pipeline(repo_path: str, cfg: dict, branch: str, incremental: bool, since_commit: str | None):
        if pipeline_runner:
            return pipeline_runner(repo_path, cfg, branch, incremental, since_commit)
        from gitnexus_parser.ingestion.pipeline import run_pipeline as _run
        return _run(
            repo_path, cfg,
            branch=branch,
            write_neo4j=bool(cfg.get("neo4j_uri")),
            incremental=incremental,
            since_commit=since_commit,
        )

    for ver in versions:
        branch = ver.get("branch")
        if not branch:
            continue
        head = git_ops.get_head_commit(repo_path, branch)
        if not head:
            continue
        last = ver.get("last_parsed_commit")

        if last is None:
            # New branch or first time: try copy-data from another version with same HEAD
            source = next(
                (v for v in versions if v["id"] != ver["id"] and (v.get("last_parsed_commit") or "") == head),
                None,
            )
            if source and neo4j_driver and _add_branch_to_nodes_if_available(
                neo4j_driver, source["branch"], branch, config.get("neo4j_database")
            ):
                version_repo.update_last_parsed_commit(conn, ver["id"], head)
                conn.commit()
                actions.append({"version_id": ver["id"], "branch": branch, "action": "copy_data"})
                continue
            # Full run
            run_pipeline(repo_path, config, branch, False, None)
            version_repo.update_last_parsed_commit(conn, ver["id"], head)
            conn.commit()
            actions.append({"version_id": ver["id"], "branch": branch, "action": "full"})
            continue

        if head != last:
            run_pipeline(repo_path, config, branch, True, last)
            version_repo.update_last_parsed_commit(conn, ver["id"], head)
            conn.commit()
            actions.append({"version_id": ver["id"], "branch": branch, "action": "incremental"})

    return {"project_id": project_id, "actions": actions}
