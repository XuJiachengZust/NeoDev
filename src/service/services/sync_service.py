"""Repository graph refresh service."""

from __future__ import annotations

import os
import subprocess
import hashlib
import logging
import time
from pathlib import Path

from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url, resolve_repo_root

from service import git_ops
from service.path_allowlist import ensure_path_allowed
from service.repositories import branch_graph_repository as branch_graph_repo
from service.repositories import graph_management_repository
from service.repositories import project_repository as project_repo
from service.services import branch_graph_neo4j_service
from service.services import neo4j_config_service
from service.services import product_version_service

logger = logging.getLogger(__name__)


class GraphRefreshRollbackError(RuntimeError):
    rollback_status = "rollback_failed"

    def __init__(
        self,
        message: str,
        *,
        restore_error: Exception,
        commit_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.restore_error = restore_error
        self.commit_error = commit_error


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


def refresh_graph_for_branch(
    conn,
    project_id: int,
    branch: str,
    *,
    commit: bool = True,
    commit_failure_state: bool = True,
    restore_neo4j_on_error: bool = False,
) -> dict | None:
    project = project_repo.find_by_id(conn, project_id)
    if not project:
        return None
    normalized_branch = (branch or "").strip()
    if not normalized_branch:
        return None

    timings: dict[str, float] = {}

    def timed(name: str, callback):
        started = time.perf_counter()
        value = callback()
        timings[name] = round(time.perf_counter() - started, 4)
        return value

    local_root = timed("resolve_local_repo", lambda: _resolve_local_repo(project, project_id))
    timed("git_fetch", lambda: git_ops.fetch_repo(local_root))
    previous_branch = timed("git_checkout", lambda: _git_checkout(local_root, normalized_branch))
    graph = None
    run = None
    neo4j_restore_context = None
    neo4j_replace_committed = False

    try:
        head = timed("git_head", lambda: git_ops.get_head_commit(local_root, normalized_branch))
        existing_graph = branch_graph_repo.get_by_project_branch(conn, project_id, normalized_branch)
        version_scope = _branch_version_scope(conn, project_id, normalized_branch)
        neo4j_config, neo4j_database = neo4j_config_service.load_neo4j_config(project)
        if not neo4j_config:
            raise RuntimeError("Neo4j is not configured for branch graph refresh")
        has_existing_neo4j_graph = False
        if existing_graph and existing_graph.get("status") == "ready" and existing_graph.get("head_commit") == head:
            has_existing_neo4j_graph = timed(
                "neo4j_existing_graph_check",
                lambda: branch_graph_neo4j_service.branch_has_graph(
                    config=neo4j_config,
                    database=neo4j_database,
                    project_id=project_id,
                    branch_name=normalized_branch,
                    version_scope=version_scope,
                ),
            )
        has_manual_graph_operations = False
        if (
            existing_graph
            and existing_graph.get("status") == "ready"
            and existing_graph.get("head_commit") == head
            and has_existing_neo4j_graph
        ):
            has_manual_graph_operations = timed(
                "manual_graph_operation_check",
                lambda: graph_management_repository.has_operations_for_branch(
                    conn,
                    project_id,
                    normalized_branch,
                ),
            )
        if (
            existing_graph
            and existing_graph.get("status") == "ready"
            and existing_graph.get("head_commit") == head
            and has_existing_neo4j_graph
            and not has_manual_graph_operations
        ):
            logger.info(
                "branch graph refresh skipped project_id=%s branch=%s timings=%s",
                project_id,
                normalized_branch,
                timings,
            )
            return {
                "project_id": project_id,
                "branch": normalized_branch,
                "graph_id": existing_graph["id"],
                "run_id": None,
                "head_commit": head,
                "graph_action": "skipped_unchanged",
                "node_count": existing_graph.get("node_count") or 0,
                "edge_count": existing_graph.get("edge_count") or 0,
                "file_count": None,
                "graph_hash": existing_graph.get("graph_hash"),
                "timings": timings,
                "graph_errors": [],
            }
        graph = branch_graph_repo.upsert(
            conn,
            project_id=project_id,
            branch_name=normalized_branch,
            status="running",
        )
        run = branch_graph_repo.start_refresh_run(
            conn,
            graph_id=graph["id"],
            project_id=project_id,
            branch_name=normalized_branch,
            head_commit_before=(existing_graph or {}).get("head_commit"),
        )
        from gitnexus_parser.ingestion.pipeline import run_pipeline

        pipeline_result = timed(
            "pipeline_total",
            lambda: run_pipeline(
                local_root,
                config={},
                branch=normalized_branch,
                project_id=project_id,
                write_neo4j=True,
                incremental=False,
                since_commit=None,
            ),
        )
        if pipeline_result.graph is None:
            raise RuntimeError("Parser did not return a graph for Neo4j writing")
        pipeline_timings = getattr(pipeline_result, "timings", None)
        if pipeline_timings:
            timings["pipeline_breakdown"] = pipeline_timings
        graph_hash = _graph_hash(
            project_id=project_id,
            branch_name=normalized_branch,
            head_commit=head,
            node_count=pipeline_result.node_count,
            edge_count=pipeline_result.relationship_count,
        )
        branch_graph_repo.mark_ready(
            conn,
            graph_id=graph["id"],
            head_commit=head,
            graph_hash=graph_hash,
            node_count=pipeline_result.node_count,
            edge_count=pipeline_result.relationship_count,
        )
        branch_graph_repo.complete_refresh_run(
            conn,
            run_id=run["id"],
            head_commit_after=head,
            node_count=pipeline_result.node_count,
            edge_count=pipeline_result.relationship_count,
            metadata_json={
                "file_count": pipeline_result.file_count,
                "neo4j_write": None,
                "timings": timings,
            },
        )

        if restore_neo4j_on_error:
            neo4j_snapshot = timed(
                "neo4j_snapshot_branch_graph",
                lambda: branch_graph_neo4j_service.snapshot_branch_graph(
                    config=neo4j_config,
                    database=neo4j_database,
                    project_id=project_id,
                    branch_name=normalized_branch,
                    version_scope=version_scope,
                ),
            )
            neo4j_restore_context = {
                "config": neo4j_config,
                "database": neo4j_database,
                "snapshot": neo4j_snapshot,
            }

        neo4j_write = timed(
            "neo4j_replace_branch_graph",
            lambda: branch_graph_neo4j_service.replace_branch_graph(
                conn=conn,
                config=neo4j_config,
                database=neo4j_database,
                graph=pipeline_result.graph,
                project_id=project_id,
                branch_name=normalized_branch,
                graph_id=graph["id"],
                head_commit=head,
                version_scope=version_scope,
            ),
        )
        neo4j_replace_committed = True
        if commit:
            timed("pg_commit", conn.commit)
        logger.info(
            "branch graph refresh completed project_id=%s branch=%s nodes=%s edges=%s timings=%s",
            project_id,
            normalized_branch,
            pipeline_result.node_count,
            pipeline_result.relationship_count,
            timings,
        )
        return {
            "project_id": project_id,
            "branch": normalized_branch,
            "graph_id": graph["id"],
            "run_id": run["id"],
            "head_commit": head,
            "graph_action": "full_replace",
            "node_count": pipeline_result.node_count,
            "edge_count": pipeline_result.relationship_count,
            "file_count": pipeline_result.file_count,
            "graph_hash": graph_hash,
            "neo4j_write": neo4j_write,
            "timings": timings,
            "graph_errors": [],
            **({"_neo4j_restore": neo4j_restore_context} if neo4j_restore_context else {}),
        }
    except Exception as exc:
        restore_context = neo4j_restore_context if neo4j_replace_committed else None
        neo4j_restore_context = None
        restore_error = None
        try:
            _restore_neo4j_snapshot(
                restore_context=restore_context,
                timings=timings,
            )
        except Exception as caught:
            restore_error = caught
        if graph is not None:
            branch_graph_repo.mark_failed(conn, graph_id=graph["id"], error_message=str(exc))
        if run is not None:
            branch_graph_repo.fail_refresh_run(conn, run_id=run["id"], error_message=str(exc))
        commit_error = None
        if commit and commit_failure_state:
            try:
                conn.commit()
            except Exception as caught:
                commit_error = caught
        if restore_error is not None:
            raise GraphRefreshRollbackError(
                f"{exc}; Neo4j restore failed: {restore_error}",
                restore_error=restore_error,
                commit_error=commit_error,
            ) from exc
        if commit_error is not None:
            raise commit_error from exc
        raise
    finally:
        _restore_checkout(local_root, previous_branch, normalized_branch)


def _graph_hash(
    *,
    project_id: int,
    branch_name: str,
    head_commit: str | None,
    node_count: int,
    edge_count: int,
) -> str:
    payload = f"{project_id}\0{branch_name}\0{head_commit or ''}\0{node_count}\0{edge_count}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _restore_neo4j_snapshot(*, restore_context: dict | None, timings: dict[str, float]) -> dict | None:
    if not restore_context:
        return None
    started = time.perf_counter()
    try:
        return branch_graph_neo4j_service.restore_branch_graph_snapshot(**restore_context)
    finally:
        timings["neo4j_restore_branch_graph"] = round(time.perf_counter() - started, 4)


def _branch_version_scope(conn, project_id: int, branch_name: str) -> dict:
    rows = product_version_service.list_versions_by_project_branch(conn, project_id, branch_name)
    if not rows:
        return {}
    if len(rows) > 1:
        raise RuntimeError(
            f"branch is bound to multiple product versions: project_id={project_id}, branch={branch_name}"
        )
    row = rows[0]
    return {
        "product_version_id": row.get("id"),
        "product_name": row.get("product_name"),
        "version_name": row.get("version_name"),
        "project_name": row.get("project_name"),
    }


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
