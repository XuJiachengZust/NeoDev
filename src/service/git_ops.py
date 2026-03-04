"""Git read-only operations for Phase 4: branches, HEAD, commit list. Uses subprocess for testability."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def get_branches(repo_path: str) -> list[str]:
    """
    Return list of local branch names. Returns [] if repo_path is not a directory or not a git repo.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return []
    try:
        r = subprocess.run(
            ["git", "branch", "--format=%(refname:short)"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode != 0:
            return []
        return [line.strip() for line in (r.stdout or "").strip().splitlines() if line.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def get_head_commit(repo_path: str, branch: str | None = None) -> str | None:
    """
    Return commit SHA (up to 40 chars) for the given branch, or current HEAD if branch is None.
    Returns None if not a git repo or branch does not exist.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return None
    ref = branch if branch else "HEAD"
    try:
        r = subprocess.run(
            ["git", "rev-parse", ref],
            cwd=repo,
            capture_output=True,
            text=True,
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
    Returns [] if repo_path is not a git repo.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return []
    rev_range = f"{since_sha}..{branch}" if since_sha else branch
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
