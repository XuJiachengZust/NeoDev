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


def get_default_branch(repo_path: str) -> str | None:
    """Return the default branch name (e.g. main, master) by reading HEAD symbolic ref."""
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return None
    try:
        r = subprocess.run(
            ["git", "symbolic-ref", "refs/remotes/origin/HEAD", "--short"],
            cwd=repo, capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            ref = r.stdout.strip()
            return ref.removeprefix("origin/")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    # fallback: current HEAD branch
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo, capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip() and r.stdout.strip() != "HEAD":
            return r.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    # fallback: check common names
    for name in ("main", "master"):
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--verify", f"origin/{name}"],
                cwd=repo, capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                return name
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    return None


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

    # 配置环境变量：禁用交互式提示、跳过 SSL 验证（如果需要）
    env = {
        **subprocess.os.environ,
        "GIT_TERMINAL_PROMPT": "0",  # 禁用交互式密码提示
        "GIT_ASKPASS": "echo",       # 避免弹出凭据对话框
        "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o StrictHostKeyChecking=no",  # SSH 非交互模式
    }

    try:
        r = subprocess.run(
            ["git", "fetch", "--all", "--prune"],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,  # 增加到 120 秒
            env=env,
        )
        if r.returncode != 0:
            stderr = (r.stderr or "").strip()
            stdout = (r.stdout or "").strip()
            error_msg = stderr or stdout or "unknown"
            logger.error("git fetch failed in %s: %s", repo, error_msg)
            # 如果是认证失败，提供更明确的错误信息
            if "authentication" in error_msg.lower() or "credentials" in error_msg.lower():
                raise RuntimeError(f"git fetch 认证失败，请检查仓库凭据配置: {error_msg}")
            raise RuntimeError(f"git fetch failed: {error_msg}")
        logger.info("git fetch done in %s", repo)
    except subprocess.TimeoutExpired as e:
        logger.error("git fetch timed out (120s) in %s", repo)
        raise RuntimeError("git fetch 超时（120秒），请检查网络连接或仓库 URL") from e
    except FileNotFoundError as e:
        logger.error("git not found")
        raise RuntimeError("git not found") from e


def show_commit(repo_path: str, commit_sha: str, stat_only: bool = False) -> str | None:
    """获取 commit 详细信息。stat_only=True 时只返回 --stat 统计。"""
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return None
    cmd = ["git", "show", commit_sha]
    if stat_only:
        cmd.append("--stat")
    try:
        r = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if r.returncode != 0:
            return None
        return r.stdout or ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def diff_commit(
    repo_path: str,
    commit_sha: str,
    file_path: str | None = None,
    context_lines: int = 3,
    stat_only: bool = False,
) -> str | None:
    """获取 commit 的 unified diff 或 --stat。"""
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return None
    cmd = ["git", "diff", f"{commit_sha}^..{commit_sha}"]
    if stat_only:
        cmd.append("--stat")
    else:
        cmd.append(f"-U{context_lines}")
    if file_path:
        cmd.extend(["--", file_path])
    try:
        r = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if r.returncode != 0:
            return None
        return r.stdout or ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def log_range(
    repo_path: str,
    from_ref: str | None = None,
    to_ref: str = "HEAD",
    path: str | None = None,
    max_count: int = 50,
    show_stat: bool = False,
) -> str | None:
    """获取 ref 范围内的提交列表。"""
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return None
    clamped = max(1, min(max_count, 200))
    if from_ref:
        rev_range = f"{from_ref}..{to_ref}"
    else:
        rev_range = to_ref
    cmd = ["git", "log", rev_range, f"--max-count={clamped}"]
    if show_stat:
        cmd.append("--stat")
    if path:
        cmd.extend(["--", path])
    try:
        r = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if r.returncode != 0:
            return None
        return r.stdout or ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
