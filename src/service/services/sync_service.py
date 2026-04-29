"""Repository graph refresh service."""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url, resolve_repo_root

from service import git_ops
from service.path_allowlist import ensure_path_allowed
from service.repositories import project_repository as project_repo

logger = logging.getLogger(__name__)


def _git_checkout(repo_path: str, branch: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        previous = result.stdout.strip() if result.returncode == 0 and result.stdout else None
        remote_ref = f"origin/{branch}"
        has_remote = subprocess.run(
            ["git", "rev-parse", "--verify", remote_ref],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        command = ["git", "checkout", "-B", branch, remote_ref] if has_remote.returncode == 0 else ["git", "checkout", branch]
        subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return previous
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def _restore_checkout(repo_path: str, previous_branch: str | None, current_branch: str) -> None:
    if not previous_branch or previous_branch == current_branch:
        return
    try:
        subprocess.run(
            ["git", "checkout", previous_branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        pass


def _load_graph_config() -> dict:
    config = {}
    try:
        from gitnexus_parser import load_config

        config = load_config()
        if not config.get("neo4j_uri"):
            for path in _default_config_paths():
                try:
                    config = load_config(path)
                    if config.get("neo4j_uri"):
                        break
                except Exception as exc:
                    logger.debug("load_config(%s) failed: %s", path, exc)
    except Exception as exc:
        logger.debug("load_config failed: %s", exc)
    return config


def _default_config_paths() -> list[Path]:
    env_path = os.environ.get("CONFIG_PATH")
    if env_path:
        return [Path(env_path)]
    src_dir = Path(__file__).resolve().parent.parent.parent
    return [src_dir / "config.json", src_dir / "config.example.json"]


def _is_remote_url(repo_path: str) -> bool:
    value = (repo_path or "").strip()
    return (
        value.startswith("http://")
        or value.startswith("https://")
        or value.startswith("git@")
        or ("://" in value and not os.path.isdir(value))
    )


def _resolve_local_repo(project: dict, project_id: int) -> str:
    repo_path = (project.get("repo_path") or "").strip()
    if not repo_path:
        raise RuntimeError("Project repo_path is empty")

    if _is_remote_url(repo_path):
        base = os.environ.get("REPO_CLONE_BASE", "").strip()
        if not base:
            neodev_root = Path(__file__).resolve().parent.parent.parent.parent
            base = str((neodev_root.parent / "repos").resolve())
        target_path = os.path.join(base, str(project_id))
        ensure_path_allowed(base)
        ensure_path_allowed(target_path)
        return ensure_repo_from_url(
            repo_path,
            target_path,
            branch=None,
            username=project.get("repo_username"),
            password=project.get("repo_password"),
        )

    local_root = resolve_repo_root(repo_path)
    if local_root is None:
        raise RuntimeError(f"Invalid or not a Git repository path: {repo_path}")
    return local_root


def refresh_graph_for_branch(conn, project_id: int, branch: str) -> dict | None:
    project = project_repo.find_by_id(conn, project_id)
    if not project:
        return None
    normalized_branch = (branch or "").strip()
    if not normalized_branch:
        return None

    local_root = _resolve_local_repo(project, project_id)
    git_ops.fetch_repo(local_root)
    previous_branch = _git_checkout(local_root, normalized_branch)
    head = git_ops.get_head_commit(local_root, normalized_branch)

    try:
        config = _load_graph_config()
        from gitnexus_parser.ingestion.pipeline import run_pipeline

        pipeline_result = run_pipeline(
            local_root,
            config=config,
            branch=normalized_branch,
            project_id=project_id,
            write_neo4j=bool(config.get("neo4j_uri")),
            incremental=False,
            since_commit=None,
        )

        from service.services import branch_snapshot_service, doc_code_link_service

        current = branch_snapshot_service.get_current_snapshot(conn, project_id, normalized_branch)
        if current and current.get("snapshot_hash") == pipeline_result.snapshot_hash:
            link_resolution = doc_code_link_service.rebuild_links_for_branch_snapshot(
                conn,
                project_id=project_id,
                branch_name=normalized_branch,
                snapshot_id=current["id"],
            )
            conn.commit()
            return {
                "project_id": project_id,
                "branch": normalized_branch,
                "head_commit": head,
                "graph_action": "no_change",
                "current_snapshot_id": current["id"],
                "snapshot_hash": pipeline_result.snapshot_hash,
                "snapshot_entry_count": len(pipeline_result.code_facts or []),
                "code_fact_count": len(pipeline_result.code_facts or []),
                "doc_code_link_resolution": link_resolution,
                "graph_errors": [],
            }

        snapshot = branch_snapshot_service.create_snapshot_from_code_facts(
            conn,
            project_id=project_id,
            branch=normalized_branch,
            head_commit=head,
            snapshot_hash=pipeline_result.snapshot_hash,
            code_facts=pipeline_result.code_facts or [],
        )
        link_resolution = doc_code_link_service.rebuild_links_for_branch_snapshot(
            conn,
            project_id=project_id,
            branch_name=normalized_branch,
            snapshot_id=snapshot["id"],
        )
        conn.commit()
        return {
            "project_id": project_id,
            "branch": normalized_branch,
            "head_commit": head,
            "graph_action": "full_refresh",
            "current_snapshot_id": snapshot.get("id"),
            "snapshot_hash": pipeline_result.snapshot_hash,
            "snapshot_entry_count": int(snapshot.get("entry_count") or 0),
            "code_fact_count": len(pipeline_result.code_facts or []),
            "doc_code_link_resolution": link_resolution,
            "graph_errors": [],
        }
    finally:
        _restore_checkout(local_root, previous_branch, normalized_branch)


def sync_commits_for_project(conn, project_id: int) -> dict | None:
    project = project_repo.find_by_id(conn, project_id)
    if not project:
        return None
    return {
        "project_id": project_id,
        "versions_synced": 0,
        "commits_synced": 0,
        "graph_actions": [],
        "graph_errors": None,
        "skipped": True,
        "reason": "commit_sync_removed_use_project_refresh_graph",
    }
