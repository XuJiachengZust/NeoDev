"""Git pre-push hook guard for NeoDev DocChange verification."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import check_git_commit_scope


ZERO_SHA = "0" * 40


def check_pre_push(
    *,
    repo_root: Path | None,
    project_id: int | None,
    stdin_text: str,
    remote_name: str | None = None,
) -> dict[str, Any]:
    resolved_repo = _resolve_repo_root(repo_root)
    if resolved_repo is None:
        return {"ok": True, "checked_count": 0, "skipped": "not a git repository", "errors": []}
    resolved_project_id = project_id or _resolve_project_id(resolved_repo)
    if resolved_project_id is None:
        return {
            "ok": False,
            "checked_count": 0,
            "errors": [
                {
                    "category": "not_ready",
                    "message": "NeoDev project_id is required for pre-push verification",
                    "details": {"source": "NEODEV_PROJECT_ID or .neodev/project.json"},
                }
            ],
        }

    failed: list[dict[str, Any]] = []
    checked_count = 0
    for ref in _parse_refs(stdin_text):
        branch = _branch_from_ref(ref["local_ref"]) or _branch_from_ref(ref["remote_ref"]) or "HEAD"
        commits = _rev_list(resolved_repo, ref["remote_sha"], ref["local_sha"], remote_name=remote_name)
        for commit_sha in commits:
            paths = _commit_paths(resolved_repo, commit_sha)
            scope = check_git_commit_scope.classify_paths(paths)["scope"]
            if scope in {"document", "empty"}:
                continue
            checked_count += 1
            if scope == "mixed":
                failed.append(
                    {
                        "commit_sha": commit_sha,
                        "scope": scope,
                        "errors": [
                            {
                                "category": "invalid_scope",
                                "message": "NeoDev commit scope is mixed. Split document and code changes.",
                                "details": {"paths": paths},
                            }
                        ],
                    }
                )
                continue
            verify = _verify_commit(
                resolved_repo,
                project_id=resolved_project_id,
                branch=branch,
                commit_sha=commit_sha,
            )
            if not verify.get("ok"):
                failed.append({"commit_sha": commit_sha, "scope": scope, **verify})

    return {
        "ok": not failed,
        "checked_count": checked_count,
        "failed_commits": failed,
        "errors": [] if not failed else [{"category": "conflict", "message": "pre-push verification failed", "details": {}}],
    }


def _resolve_repo_root(repo_root: Path | None) -> Path | None:
    if repo_root is not None:
        return repo_root.resolve()
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).resolve()


def _resolve_project_id(repo_root: Path) -> int | None:
    env_value = os.environ.get("NEODEV_PROJECT_ID")
    if env_value:
        try:
            return int(env_value)
        except ValueError:
            return None
    config_path = repo_root / ".neodev" / "project.json"
    if not config_path.exists():
        return None
    try:
        value = json.loads(config_path.read_text(encoding="utf-8")).get("project_id")
        return int(value)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _parse_refs(stdin_text: str) -> list[dict[str, str]]:
    refs = []
    for line in stdin_text.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        refs.append(
            {
                "local_ref": parts[0],
                "local_sha": parts[1],
                "remote_ref": parts[2],
                "remote_sha": parts[3],
            }
        )
    return refs


def _branch_from_ref(ref: str) -> str | None:
    prefix = "refs/heads/"
    return ref[len(prefix) :] if ref.startswith(prefix) else None


def _rev_list(repo_root: Path, remote_sha: str, local_sha: str, *, remote_name: str | None) -> list[str]:
    if local_sha == ZERO_SHA:
        return []
    if remote_sha == ZERO_SHA:
        args = ["git", "-C", str(repo_root), "rev-list", "--reverse", local_sha]
    else:
        args = ["git", "-C", str(repo_root), "rev-list", "--reverse", f"{remote_sha}..{local_sha}"]
    proc = subprocess.run(args, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _commit_paths(repo_root: Path, commit_sha: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit_sha],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]


def _verify_commit(repo_root: Path, *, project_id: int, branch: str, commit_sha: str) -> dict[str, Any]:
    cli = _resolve_cli()
    if not cli:
        return {
            "ok": False,
            "errors": [
                {
                    "category": "not_ready",
                    "message": "NeoDev CLI is not installed or not on PATH",
                    "details": {},
                }
            ],
        }
    message = subprocess.check_output(
        ["git", "-C", str(repo_root), "log", "-1", "--format=%B", commit_sha],
        text=True,
    )
    proc = subprocess.run(
        [
            *cli,
            "git",
            "verify-doc-change",
            "--project-id",
            str(project_id),
            "--branch",
            branch,
            "--commit-sha",
            commit_sha,
            "--commit-message",
            message,
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        payload = {
            "ok": False,
            "errors": [
                {
                    "category": "internal_error",
                    "message": "NeoDev CLI returned non-JSON output",
                    "details": {"stdout": proc.stdout, "stderr": proc.stderr},
                }
            ],
        }
    return payload


def _resolve_cli() -> list[str] | None:
    configured = os.environ.get("NEODEV_CLI")
    if configured:
        return shlex.split(configured, posix=os.name != "nt")
    found = shutil.which("neodev")
    if found and os.name == "nt" and found.lower().endswith(".cmd"):
        client = Path(found).with_name("neodev_client.py")
        if client.is_file():
            return [sys.executable, str(client)]
    return [found] if found else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("remote_name", nargs="?")
    parser.add_argument("remote_url", nargs="?")
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--project-id", type=int)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    payload = check_pre_push(
        repo_root=args.repo_root,
        project_id=args.project_id,
        stdin_text=os.sys.stdin.read(),
        remote_name=args.remote_name,
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
