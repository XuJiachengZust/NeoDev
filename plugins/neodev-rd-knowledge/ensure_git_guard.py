"""Install NeoDev managed Git hooks for the current repository."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


MARKER = "NEODEV-GIT-GUARD"
GUARD_VERSION = "1"
HOOKS = ("commit-msg", "pre-push")


def ensure_git_guard(repo_root: Path | None = None, *, dry_run: bool = False) -> dict[str, Any]:
    resolved_repo = _resolve_repo_root(repo_root)
    if resolved_repo is None:
        return {
            "ok": True,
            "status": "skipped",
            "reason": "not a git repository",
            "installed": [],
            "updated": [],
            "chained": [],
        }

    hooks_dir = _resolve_hooks_dir(resolved_repo)
    plugin_root = Path(__file__).resolve().parent
    python_bin = _to_hook_path(Path(sys.executable))
    installed: list[str] = []
    updated: list[str] = []
    chained: list[dict[str, str]] = []

    for hook_name in HOOKS:
        hook_path = hooks_dir / hook_name
        user_hook = None
        existing_text = hook_path.read_text(encoding="utf-8", errors="replace") if hook_path.exists() else ""
        if hook_path.exists() and MARKER not in existing_text:
            user_hook = _preserve_user_hook(hooks_dir, hook_name, hook_path, dry_run=dry_run)
            chained.append({"hook": hook_name, "user_hook": str(user_hook)})

        content = _render_hook(
            hook_name,
            plugin_root=plugin_root,
            python_bin=python_bin,
            user_hook=user_hook,
        )
        if existing_text == content:
            continue
        if hook_path.exists() and MARKER in existing_text:
            updated.append(hook_name)
        elif user_hook is None:
            installed.append(hook_name)
        if not dry_run:
            hooks_dir.mkdir(parents=True, exist_ok=True)
            hook_path.write_text(content, encoding="utf-8", newline="\n")
            _make_executable(hook_path)

    return {
        "ok": True,
        "status": "ready",
        "repo_root": str(resolved_repo),
        "hooks_dir": str(hooks_dir),
        "installed": installed,
        "updated": updated,
        "chained": chained,
        "guard_version": GUARD_VERSION,
    }


def _resolve_repo_root(repo_root: Path | None) -> Path | None:
    if repo_root is not None:
        return repo_root.resolve()
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).resolve()


def _resolve_hooks_dir(repo_root: Path) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--git-path", "hooks"],
        text=True,
        capture_output=True,
        check=True,
    )
    raw = Path(proc.stdout.strip())
    return raw.resolve() if raw.is_absolute() else (repo_root / raw).resolve()


def _preserve_user_hook(hooks_dir: Path, hook_name: str, hook_path: Path, *, dry_run: bool) -> Path:
    preserved_dir = hooks_dir / ".neodev-user-hooks"
    preserved = preserved_dir / hook_name
    counter = 1
    while preserved.exists():
        preserved = preserved_dir / f"{hook_name}.{counter}"
        counter += 1
    if not dry_run:
        preserved_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(hook_path), str(preserved))
        _make_executable(preserved)
    return preserved


def _render_hook(
    hook_name: str,
    *,
    plugin_root: Path,
    python_bin: str,
    user_hook: Path | None,
) -> str:
    plugin_root_text = _shell_quote(_to_hook_path(plugin_root))
    python_text = _shell_quote(python_bin)
    user_hook_text = _shell_quote(_to_hook_path(user_hook)) if user_hook else "''"
    script = "git_guard_commit_msg.py" if hook_name == "commit-msg" else "git_guard_pre_push.py"
    if hook_name == "pre-push":
        return f"""#!/usr/bin/env sh
# {MARKER} version {GUARD_VERSION}; managed by NeoDev RD Knowledge.
PYTHON_BIN={python_text}
PLUGIN_ROOT={plugin_root_text}
USER_HOOK={user_hook_text}
TMP_FILE="$(mktemp "${{TMPDIR:-/tmp}}/neodev-pre-push.XXXXXX")" || exit 1
cat > "$TMP_FILE"
"$PYTHON_BIN" "$PLUGIN_ROOT/{script}" "$@" < "$TMP_FILE"
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
  rm -f "$TMP_FILE"
  exit "$STATUS"
fi
if [ -n "$USER_HOOK" ] && [ -f "$USER_HOOK" ]; then
  if [ -x "$USER_HOOK" ]; then
    "$USER_HOOK" "$@" < "$TMP_FILE"
  else
    sh "$USER_HOOK" "$@" < "$TMP_FILE"
  fi
  STATUS=$?
  rm -f "$TMP_FILE"
  exit "$STATUS"
fi
rm -f "$TMP_FILE"
exit 0
"""
    return f"""#!/usr/bin/env sh
# {MARKER} version {GUARD_VERSION}; managed by NeoDev RD Knowledge.
PYTHON_BIN={python_text}
PLUGIN_ROOT={plugin_root_text}
USER_HOOK={user_hook_text}
if [ -n "$USER_HOOK" ] && [ -f "$USER_HOOK" ]; then
  if [ -x "$USER_HOOK" ]; then
    "$USER_HOOK" "$@"
  else
    sh "$USER_HOOK" "$@"
  fi
  STATUS=$?
  if [ "$STATUS" -ne 0 ]; then
    exit "$STATUS"
  fi
fi
exec "$PYTHON_BIN" "$PLUGIN_ROOT/{script}" "$@"
"""


def _to_hook_path(path: Path | None) -> str:
    if path is None:
        return ""
    return str(path.resolve()).replace("\\", "/")


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _make_executable(path: Path) -> None:
    if os.name != "nt":
        path.chmod(path.stat().st_mode | 0o111)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    payload = ensure_git_guard(args.repo_root, dry_run=args.dry_run)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
