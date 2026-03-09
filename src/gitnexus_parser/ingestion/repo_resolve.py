"""Resolve Git repo root from path or URL. No config; all inputs via parameters."""

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse, urlunparse, quote

# Prevent Git from opening /dev/tty for credential prompt in non-interactive environments.
_GIT_ENV = {**os.environ, "LANG": "C", "GIT_TERMINAL_PROMPT": "0"}


def _url_with_auth(repo_url: str, username: str | None, password: str | None) -> str:
    """Build URL with embedded credentials for GitLab/private server. Safe for special chars."""
    if not username and not password:
        return repo_url
    parsed = urlparse(repo_url)
    user = quote(username or "", safe="") if username else ""
    passwd = quote(password or "", safe="") if password else ""
    netloc = f"{user}:{passwd}@{parsed.netloc}" if user or passwd else parsed.netloc
    return urlunparse(parsed._replace(netloc=netloc))


def list_remote_branches(
    repo_url: str,
    username: str | None = None,
    password: str | None = None,
) -> list[str]:
    """
    List branch names from a remote repo (git ls-remote --heads).
    For GitLab/private: pass username and password (or token as password).
    Returns sorted list of branch names; raises RuntimeError on failure.
    """
    url = _url_with_auth(repo_url, username, password)
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--heads", url],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=_GIT_ENV,
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("git ls-remote timed out") from e
    except FileNotFoundError:
        raise RuntimeError("git not found")
    if result.returncode != 0:
        raise RuntimeError(f"git ls-remote failed: {result.stderr or result.stdout or 'unknown'}")
    branches = []
    prefix = "refs/heads/"
    for line in (result.stdout or "").strip().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if ref.startswith(prefix):
            branches.append(ref[len(prefix) :])
    return sorted(branches)


def list_local_branches(repo_path: str) -> list[str]:
    """
    List branch names in a local repo (git for-each-ref refs/heads).
    repo_path must be repo root or any path inside it; uses resolve_repo_root first.
    Returns sorted list; raises RuntimeError on failure.
    """
    root = resolve_repo_root(repo_path)
    if root is None:
        raise RuntimeError("Not a Git repository or path invalid")
    try:
        result = subprocess.run(
            ["git", "for-each-ref", "refs/heads", "--format=%(refname:short)"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            env=_GIT_ENV,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise RuntimeError("git for-each-ref failed") from e
    if result.returncode != 0:
        raise RuntimeError(f"git for-each-ref failed: {result.stderr or 'unknown'}")
    branches = [line.strip() for line in (result.stdout or "").strip().splitlines() if line.strip()]
    return sorted(branches)


def resolve_repo_root(path: str) -> str | None:
    """
    Find Git repository root from the given path (may be repo root or any subdirectory).
    Returns absolute path of repo root, or None if not inside a Git repo / path invalid.
    """
    path = os.path.normpath(path)
    if not os.path.isdir(path):
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            env=_GIT_ENV,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None
    if result.returncode != 0 or not (result.stdout or "").strip():
        return None
    root = result.stdout.strip()
    return str(Path(root).resolve())


def ensure_repo_from_url(
    repo_url: str,
    target_path: str,
    branch: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    """
    Ensure target_path is a Git repo: clone if missing or not a repo, else return existing root.
    If branch is given, clone that branch (-b branch).
    For GitLab/private: pass username and password (or token as password).
    Raises ValueError if target_path exists and is not a Git repo; raises on clone failure.
    """
    url = _url_with_auth(repo_url, username, password)
    target_path = os.path.normpath(target_path)
    if os.path.exists(target_path):
        root = resolve_repo_root(target_path)
        if root is not None:
            return root
        raise ValueError(
            f"Target path exists and is not a Git repository: {target_path}. "
            "Use an empty directory or an existing clone."
        )
    parent = os.path.dirname(target_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    cmd = ["git", "clone", url, target_path]
    if branch:
        cmd = ["git", "clone", "-b", branch, url, target_path]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=True,
            env=_GIT_ENV,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"git clone failed: {e.stderr or e}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("git clone timed out") from e

    root = resolve_repo_root(target_path)
    if root is not None:
        return root

    # Fallback: on Windows, resolve_repo_root may fail due to path style
    # differences between git output and OS; verify .git exists as sanity check.
    git_dir = Path(target_path) / ".git"
    if git_dir.is_dir() or git_dir.is_file():
        return str(Path(target_path).resolve())

    clone_detail = (result.stderr or result.stdout or "").strip()
    raise RuntimeError(
        f"Clone finished but repo root could not be resolved: {target_path}. "
        f"git output: {clone_detail}"
    )
