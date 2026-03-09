"""Incremental scan: git changed paths and per-branch scan state (last commit)."""

import json
import subprocess
from pathlib import Path
from typing import Optional

from .utils import get_language_from_filename


def get_head_commit(repo_path: str) -> Optional[str]:
    """Return current HEAD commit hash (short) or None if not a git repo."""
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return None
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
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


def get_changed_paths(
    repo_path: str,
    base_commit: str,
    head: str = "HEAD",
    *,
    supported_extensions_only: bool = True,
) -> list[str]:
    """
    Return list of file paths changed between base_commit and head (relative, forward slashes).
    If supported_extensions_only is True, filter to paths with supported language extensions.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return []
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", base_commit, head],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if r.returncode != 0:
            return []
        paths = [p.strip().replace("\\", "/") for p in (r.stdout or "").strip().splitlines() if p.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if supported_extensions_only:
        paths = [p for p in paths if get_language_from_filename(p) is not None]
    return paths


def _default_state_path(repo_path: str) -> Path:
    return Path(repo_path).resolve() / ".gitnexus" / "scan_state.json"


def load_scan_state(
    state_path: Optional[Path | str] = None,
    repo_path: Optional[str] = None,
) -> dict[str, str]:
    """
    Load branch -> last_scanned_commit from JSON file.
    state_path overrides repo_path; if neither gives a file, return {}.
    """
    if state_path is None and repo_path:
        state_path = _default_state_path(repo_path)
    if state_path is None:
        return {}
    path = Path(state_path)
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return dict(data) if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_scan_state(
    state_path: Optional[Path | str] = None,
    repo_path: Optional[str] = None,
    branch: Optional[str] = None,
    commit: Optional[str] = None,
) -> None:
    """
    Update state file: set state[branch] = commit, then write JSON.
    state_path overrides repo_path; if branch or commit is None, skip write.
    """
    if branch is None or commit is None:
        return
    if state_path is None and repo_path:
        state_path = _default_state_path(repo_path)
    if state_path is None:
        return
    path = Path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = load_scan_state(state_path=path)
    data[branch] = commit
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
