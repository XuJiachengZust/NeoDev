"""Watch service (Phase 4): three-step trigger strategy for Git scan (copy-data / incremental / full)."""

from __future__ import annotations

from typing import Any

from service import git_ops
from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo


def _branch_snapshot_service():
    patched = globals().get("branch_snapshot_service")
    if patched is not None:
        return patched
    from service.services import branch_snapshot_service as service

    return service


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
    call pipeline or clone branch snapshot references, and update versions.last_parsed_commit.
    Returns summary dict or None if project not found / not watchable.
    pipeline_runner(repo_path, config, branch, incremental, since_commit) for test injection.
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
            return pipeline_runner(
                repo_path,
                cfg,
                branch,
                incremental,
                since_commit,
                project_id=project_id,
            )
        from gitnexus_parser.ingestion.pipeline import run_pipeline as _run
        return _run(
            repo_path, cfg,
            branch=branch,
            project_id=project_id,
            write_neo4j=bool(cfg.get("neo4j_uri")),
            incremental=incremental,
            since_commit=since_commit,
        )

    def create_snapshot(branch: str, head_commit: str, action: str) -> None:
        _branch_snapshot_service().create_snapshot_from_repo(
            conn,
            repo_path=repo_path,
            project_id=project_id,
            branch=branch,
            head_commit=head_commit,
            last_parsed_commit=head_commit,
            created_from_action=action,
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
            if source:
                snapshot_service = _branch_snapshot_service()
                source_snapshot = snapshot_service.get_current_snapshot(
                    conn, project_id, source["branch"]
                )
                if source_snapshot:
                    snapshot_service.clone_snapshot(
                        conn,
                        source_snapshot_id=source_snapshot["id"],
                        project_id=project_id,
                        branch=branch,
                        head_commit=head,
                        last_parsed_commit=head,
                    )
                    version_repo.update_last_parsed_commit(conn, ver["id"], head)
                    conn.commit()
                    actions.append({"version_id": ver["id"], "branch": branch, "action": "copy_data"})
                    continue
            # Full run
            run_pipeline(repo_path, config, branch, False, None)
            create_snapshot(branch, head, "full")
            version_repo.update_last_parsed_commit(conn, ver["id"], head)
            conn.commit()
            actions.append({"version_id": ver["id"], "branch": branch, "action": "full"})
            continue

        if head != last:
            run_pipeline(repo_path, config, branch, True, last)
            create_snapshot(branch, head, "incremental")
            version_repo.update_last_parsed_commit(conn, ver["id"], head)
            conn.commit()
            actions.append({"version_id": ver["id"], "branch": branch, "action": "incremental"})

    return {"project_id": project_id, "actions": actions}
