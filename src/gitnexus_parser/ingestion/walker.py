"""Repository path walking: collect file paths with supported extensions only."""

import os
from dataclasses import dataclass
from typing import List, Optional, Set

from .utils import get_language_from_filename


DEFAULT_EXCLUDE_DIRS: Set[str] = frozenset({
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    "build", "dist", ".eggs", "*.egg-info", ".tox", ".mypy_cache", ".pytest_cache",
})


@dataclass
class FileEntry:
    path: str
    size: int = 0


def walk_repository_paths(
    root: str,
    *,
    exclude_dirs: Optional[Set[str]] = None,
    extensions_only: bool = True,
) -> List[FileEntry]:
    """
    Walk root directory and return list of file entries.
    Only includes files with supported language extensions when extensions_only is True.
    Paths are returned with forward slashes, relative to root (or absolute if root is abs).
    """
    exclude = exclude_dirs if exclude_dirs is not None else DEFAULT_EXCLUDE_DIRS
    root = os.path.normpath(root)
    if not os.path.isdir(root):
        return []
    result: List[FileEntry] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Skip excluded directories (case-insensitive on Windows)
        dirnames[:] = [
            d for d in dirnames
            if d not in exclude and d.lower() not in {x.lower() for x in exclude}
        ]
        rel_base = os.path.relpath(dirpath, root)
        if rel_base == ".":
            rel_base = ""
        for f in filenames:
            full = os.path.join(dirpath, f)
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            rel_path = os.path.join(rel_base, f) if rel_base else f
            rel_path = rel_path.replace("\\", "/")
            if extensions_only and get_language_from_filename(rel_path) is None:
                continue
            result.append(FileEntry(path=rel_path, size=size))
    return result
