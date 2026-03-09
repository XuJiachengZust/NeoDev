"""Sync service (Phase 4): sync Git commits to PG for a project."""

import logging
import os
import subprocess
from pathlib import Path

from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url, resolve_repo_root

from service import git_ops
from service.path_allowlist import ensure_path_allowed
from service.repositories import commit_repository as commit_repo
from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo

logger = logging.getLogger(__name__)


def _git_checkout(repo_path: str, branch: str) -> str | None:
    """Checkout branch in repo_path; return previous HEAD branch or None.

    If the local branch doesn't exist, creates it from origin/<branch>.
    """
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        previous = r.stdout.strip() if r.returncode == 0 and r.stdout else None
        result = subprocess.run(
            ["git", "checkout", branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "checkout", "-b", branch, f"origin/{branch}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
        return previous
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def _default_config_paths() -> list[Path]:
    """Config file paths to try when env has no neo4j_uri (e.g. src/config.example.json)."""
    env_path = os.environ.get("CONFIG_PATH")
    if env_path:
        return [Path(env_path)]
    # __file__ = .../src/service/services/sync_service.py -> parent*3 = src
    src_dir = Path(__file__).resolve().parent.parent.parent
    return [
        src_dir / "config.json",
        src_dir / "config.example.json",
    ]


def _is_remote_url(repo_path: str) -> bool:
    """True if repo_path looks like a remote URL (http/https/git@)."""
    s = (repo_path or "").strip()
    if not s:
        return False
    return (
        s.startswith("http://")
        or s.startswith("https://")
        or s.startswith("git@")
        or ("://" in s and not os.path.isdir(s))
    )


def _resolve_local_repo(project: dict, project_id: int) -> str:
    """
    Resolve to a local repo root: clone to REPO_CLONE_BASE/project_id if repo_path is URL,
    else resolve_repo_root(repo_path). Raises ValueError/RuntimeError on failure.
    """
    repo_path = (project.get("repo_path") or "").strip()
    if not repo_path:
        raise RuntimeError("Project repo_path is empty")

    if _is_remote_url(repo_path):
        base = os.environ.get("REPO_CLONE_BASE", "").strip()
        if not base:
            neodev_root = Path(__file__).resolve().parent.parent.parent.parent
            base = str((neodev_root.parent / "repos").resolve())
        target_path = os.path.join(base, str(project_id))
        logger.info("project_id=%s: remote repo, ensuring clone at %s", project_id, target_path)
        ensure_path_allowed(base)
        ensure_path_allowed(target_path)
        local_root = ensure_repo_from_url(
            repo_path,
            target_path,
            branch=None,
            username=project.get("repo_username"),
            password=project.get("repo_password"),
        )
        logger.info("project_id=%s: clone/ensure done, local_root=%s", project_id, local_root)
        return local_root

    local_root = resolve_repo_root(repo_path)
    if local_root is None:
        raise RuntimeError(f"Invalid or not a Git repository path: {repo_path}")
    logger.info("project_id=%s: local repo, resolved root=%s", project_id, local_root)
    return local_root


def sync_commits_for_version(conn, project_id: int, version_id: int) -> dict | None:
    """
    Sync commits for a single version (branch) and run graph pipeline for that branch.
    Returns dict with project_id, version_id, branch, commits_synced, graph_action, graph_errors (if any);
    or None if project/version not found or version has no branch.
    """
    project = project_repo.find_by_id(conn, project_id)
    if not project:
        return None
    version = version_repo.find_by_id(conn, version_id)
    if not version or version.get("project_id") != project_id:
        return None
    branch = (version.get("branch") or "").strip()
    if not branch:
        return None

    logger.info("project_id=%s version_id=%s branch=%s: sync-commits start", project_id, version_id, branch)
    local_root = _resolve_local_repo(project, project_id)
    git_ops.fetch_repo(local_root)

    commits = git_ops.list_commits(local_root, branch=branch)
    commits_synced = 0
    if commits:
        commits_synced = commit_repo.upsert_commits(conn, project_id, version_id, commits)
    conn.commit()

    result = {
        "project_id": project_id,
        "version_id": version_id,
        "branch": branch,
        "commits_synced": commits_synced,
        "graph_action": None,
        "graph_errors": [],
    }

    config = {}
    try:
        from gitnexus_parser import load_config
        config = load_config()
        if not config.get("neo4j_uri"):
            for path in _default_config_paths():
                try:
                    config = load_config(path)
                    if config.get("neo4j_uri"):
                        logger.info("Loaded Neo4j config from %s", path)
                        break
                except Exception as e:
                    logger.debug("load_config(%s) failed: %s", path, e)
    except Exception as e:
        logger.debug("load_config failed: %s", e)

    if not config.get("neo4j_uri"):
        logger.info("project_id=%s version_id=%s: no neo4j_uri, skipping graph pipeline", project_id, version_id)
        return result

    head = git_ops.get_head_commit(local_root, branch)
    if not head:
        return result

    last = version.get("last_parsed_commit")
    incremental = bool(last)
    since_commit = last if last else None
    result["graph_action"] = "incremental" if incremental else "full"

    previous_branch: str | None = None
    try:
        previous_branch = _git_checkout(local_root, branch)
    except Exception as e:
        logger.warning("project_id=%s version_id=%s: checkout %s failed: %s", project_id, version_id, branch, e)
        result["graph_errors"].append(f"checkout {branch}: {e}")
        return result

    try:
        from gitnexus_parser.ingestion.pipeline import run_pipeline
        run_pipeline(
            local_root,
            config=config,
            branch=branch,
            project_id=project_id,
            write_neo4j=True,
            incremental=incremental,
            since_commit=since_commit,
        )
        version_repo.update_last_parsed_commit(conn, version_id, head)
        conn.commit()
        logger.info(
            "project_id=%s version_id=%s: graph %s done, last_parsed_commit=%s",
            project_id, version_id, result["graph_action"], head[:7],
        )
    except Exception as e:
        logger.exception("project_id=%s version_id=%s: graph pipeline failed: %s", project_id, version_id, e)
        result["graph_errors"].append(str(e))
    finally:
        if previous_branch and previous_branch != branch:
            try:
                subprocess.run(
                    ["git", "checkout", previous_branch],
                    cwd=local_root,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except Exception:
                pass

    return result


def sync_commits_for_project(conn, project_id: int) -> dict | None:
    """
    Sync commits and run graph pipeline for all versions of the project (each version independently).
    Returns summary dict with project_id, versions_synced, commits_synced, graph_actions, graph_errors;
    or None if project not found.
    Raises ValueError or RuntimeError on clone/fetch/path errors (caller should map to 502).
    """
    project = project_repo.find_by_id(conn, project_id)
    if not project:
        return None
    versions = version_repo.list_by_project_id(conn, project_id)
    total_commits = 0
    graph_actions = []
    graph_errors = []
    for ver in versions:
        if not (ver.get("branch") or "").strip():
            continue
        one = sync_commits_for_version(conn, project_id, ver["id"])
        if one is None:
            continue
        total_commits += one.get("commits_synced", 0)
        if one.get("graph_action"):
            graph_actions.append({"version_id": ver["id"], "branch": ver["branch"], "action": one["graph_action"]})
        graph_errors.extend(one.get("graph_errors") or [])
    result = {
        "project_id": project_id,
        "versions_synced": len([v for v in versions if (v.get("branch") or "").strip()]),
        "commits_synced": total_commits,
        "graph_actions": graph_actions,
        "graph_errors": graph_errors if graph_errors else None,
    }
    logger.info(
        "project_id=%s: sync-commits done, versions_synced=%s, commits_synced=%s",
        project_id, result["versions_synced"], result["commits_synced"],
    )
    return result
