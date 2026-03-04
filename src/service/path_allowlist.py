"""Path allowlist: optional restriction via ALLOWED_BASE_PATHS; default allows any local path."""

import os
from pathlib import Path
from typing import List, Optional


def _get_allowed_bases() -> Optional[List[Path]]:
    raw = os.environ.get("ALLOWED_BASE_PATHS", "").strip()
    if not raw:
        return None
    return [Path(p.strip()).resolve() for p in raw.split(os.pathsep) if p.strip()]


def is_path_allowed(path: str) -> bool:
    """True if no allowlist is set (any local path), or path is under one of the allowed bases."""
    bases = _get_allowed_bases()
    if bases is None:
        return True
    try:
        resolved = Path(path).resolve()
        if not resolved.exists():
            resolved = resolved.parent
        for base in bases:
            try:
                resolved.relative_to(base)
                return True
            except ValueError:
                continue
        return False
    except (OSError, RuntimeError):
        return False


def ensure_path_allowed(path: str) -> None:
    """Raise ValueError only when ALLOWED_BASE_PATHS is set and path is not under any base."""
    if not is_path_allowed(path):
        raise ValueError(f"Path not allowed (must be under ALLOWED_BASE_PATHS): {path}")
