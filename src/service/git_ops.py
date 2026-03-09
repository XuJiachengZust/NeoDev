"""Git read-only operations for Phase 4: branches, HEAD, commit list. Uses subprocess for testability."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _resolve_ref(repo: Path, branch: str) -> str:
    """Return a git ref that exists: prefer local branch, fallback to origin/<branch>."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--verify", branch],
            cwd=repo, capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return branch
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    remote_ref = f"origin/{branch}"
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--verify", remote_ref],
            cwd=repo, capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            return remote_ref
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return branch


def get_branches(repo_path: str) -> list[str]:
    """
    Return list of branch names (local + remote-tracking, deduplicated).
    After a fresh clone only the default branch is local; remote branches are
    included by stripping the 'origin/' prefix so callers see all available branches.
    Returns [] if repo_path is not a directory or not a git repo.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return []
    branches: set[str] = set()
    try:
        r = subprocess.run(
            ["git", "branch", "--format=%(refname:short)"],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        if r.returncode == 0:
            for line in (r.stdout or "").strip().splitlines():
                name = line.strip()
                if name:
                    branches.add(name)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    try:
        r = subprocess.run(
            ["git", "branch", "-r", "--format=%(refname:short)"],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        if r.returncode == 0:
            for line in (r.stdout or "").strip().splitlines():
                name = line.strip()
                if not name or name.endswith("/HEAD"):
                    continue
                if name.startswith("origin/"):
                    name = name[len("origin/"):]
                branches.add(name)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return sorted(branches)


def get_head_commit(repo_path: str, branch: str | None = None) -> str | None:
    """
    Return commit SHA (up to 40 chars) for the given branch, or current HEAD if branch is None.
    Automatically falls back to origin/<branch> when the local branch doesn't exist.
    Returns None if not a git repo or branch does not exist.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return None
    ref = _resolve_ref(repo, branch) if branch else "HEAD"
    try:
        r = subprocess.run(
            ["git", "rev-parse", ref],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
        if r.returncode != 0:
            return None
        return (r.stdout or "").strip()[:40]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def list_commits(
    repo_path: str,
    branch: str = "HEAD",
    since_sha: str | None = None,
    max_count: int = 5000,
) -> list[dict[str, Any]]:
    """
    Return list of commits from since_sha (exclusive) to branch tip. Each dict has
    commit_sha, message, author, committed_at (ISO string or None).
    Automatically falls back to origin/<branch> when the local branch doesn't exist.
    Returns [] if repo_path is not a git repo.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return []
    resolved = _resolve_ref(repo, branch) if branch != "HEAD" else branch
    rev_range = f"{since_sha}..{resolved}" if since_sha else resolved
    try:
        # Format: sha\\nsubject\\nauthor\\ndate (ISO)
        r = subprocess.run(
            [
                "git", "log", rev_range,
                f"--max-count={max_count}",
                "--format=%H%n%s%n%an%n%aI",
            ],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if r.returncode != 0:
            return []
        lines = (r.stdout or "").strip().splitlines()
        result = []
        i = 0
        while i + 4 <= len(lines):
            sha = lines[i].strip()[:40]
            message = lines[i + 1].strip() if i + 1 < len(lines) else ""
            author = lines[i + 2].strip() if i + 2 < len(lines) else ""
            committed_at = lines[i + 3].strip() if i + 3 < len(lines) else None
            result.append({
                "commit_sha": sha,
                "message": message,
                "author": author,
                "committed_at": committed_at or None,
            })
            i += 4
        return result
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def fetch_repo(repo_path: str) -> None:
    """
    Run `git fetch` in the given repo root to update remote refs.
    Raises RuntimeError on failure (e.g. not a repo, fetch failed, timeout).
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        raise RuntimeError(f"Not a directory: {repo_path}")
    logger.info("git fetch --all in %s", repo)
    try:
        r = subprocess.run(
            ["git", "fetch", "--all"],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if r.returncode != 0:
            logger.error("git fetch failed in %s: %s", repo, r.stderr or r.stdout or "unknown")
            raise RuntimeError(f"git fetch failed: {r.stderr or r.stdout or 'unknown'}")
        logger.info("git fetch done in %s", repo)
    except subprocess.TimeoutExpired as e:
        logger.error("git fetch timed out in %s", repo)
        raise RuntimeError("git fetch timed out") from e
    except FileNotFoundError as e:
        logger.error("git not found")
        raise RuntimeError("git not found") from e
