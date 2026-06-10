"""Post-push NeoDev graph and DocChange update orchestration."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import check_docchange_trailer
import check_git_commit_scope


STATE_DIR = "post_push_graph_update"
SKILL_HINT = {"skill": "neodev-rd-knowledge", "action": "interpret_post_push_result"}
INTERNAL_PATH_PREFIXES = (".git/", ".neodev/")
REGISTERABLE_DOC_EXTENSIONS = {".md", ".markdown", ".mdx"}


class PostPushError(Exception):
    def __init__(
        self,
        category: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
        after_remote_write: bool = False,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.details = details or {}
        self.after_remote_write = after_remote_write

    def to_error(self) -> dict[str, Any]:
        return {"category": self.category, "message": self.message, "details": self.details}


def run_post_push(repo_root: Path | None = None) -> dict[str, Any]:
    run_id = uuid.uuid4().hex
    started_at = _now()
    resolved_repo = _resolve_repo_root(repo_root)
    base = _base_payload(run_id, started_at, resolved_repo)
    remote_write_done = False

    if resolved_repo is None:
        base.update(
            {
                "hook_status": "not_ready",
                "rollback_status": "not_needed",
                "errors": [
                    {
                        "category": "not_ready",
                        "message": "not a git repository",
                        "details": {},
                    }
                ],
            }
        )
        return _finalize(base)

    try:
        project = _resolve_project(resolved_repo)
        branch = _resolve_branch(resolved_repo)
        commits = _resolve_commits(resolved_repo, branch, project)
        cli = _resolve_cli()
        if not cli:
            raise PostPushError("not_ready", "NeoDev CLI is not installed or not on PATH")

        base["project"] = {
            "project_id": project.get("project_id"),
            "project_name": project.get("project_name"),
            "branch": branch,
            "source": project.get("source", "local"),
        }
        base["commit_range"] = commits
        base["run_record"]["push_key"] = _push_key(commits)

        if not commits:
            base.update(
                {
                    "hook_status": "skipped",
                    "rollback_status": "not_needed",
                    "graph_refresh_result": _skipped_graph_result(
                        resolved_repo,
                        "no new commits",
                    ),
                }
            )
            return _finish_run(resolved_repo, base, remote_write_done)

        planned = _plan_commits(resolved_repo, commits)
        base["classification_summary"] = planned["classification_summary"]
        base["commit_results"] = planned["commit_results"]
        if planned["errors"]:
            raise PostPushError(
                planned["errors"][0]["category"],
                planned["errors"][0]["message"],
                details=planned["errors"][0].get("details") or {},
            )

        if not planned["document_commits"] and not planned["code_commits"]:
            base.update(
                {
                    "hook_status": "skipped",
                    "rollback_status": "not_needed",
                    "graph_refresh_result": _skipped_graph_result(
                        resolved_repo,
                        "no document or code changes",
                        commits[-1] if commits else None,
                    ),
                }
            )
            return _finish_run(resolved_repo, base, remote_write_done)

        atomic_request = _build_atomic_payload(base, project, branch, planned)
        atomic_payload_file = _write_atomic_payload(resolved_repo, run_id, atomic_request)
        atomic = _run_cli_json(
            cli,
            [
                "git",
                "post-push-graph-update",
                "--payload-file",
                str(atomic_payload_file),
                "--json",
            ],
            cwd=resolved_repo,
        )
        atomic_data = atomic.get("data") or {}
        remote_project = atomic_data.get("project") or {}
        if remote_project.get("project_id") is not None:
            base["project"]["project_id"] = remote_project.get("project_id")
        if remote_project.get("project_name"):
            base["project"]["project_name"] = remote_project.get("project_name")
        base["doc_import_results"] = atomic_data.get("doc_import_results") or []
        base["docchange_register_results"] = atomic_data.get("docchange_register_results") or []
        base["docchange_link_results"] = atomic_data.get("docchange_link_results") or []
        refresh_data = atomic_data.get("graph_refresh_result") or {}
        if not refresh_data.get("head_commit"):
            raise PostPushError(
                "invalid_result",
                "post-push graph update result missing graph_refresh_result.head_commit",
                details={
                    "data": atomic_data,
                    "rollback_status": _invalid_atomic_rollback_status(atomic_data),
                },
                after_remote_write=True,
            )
        base["graph_refresh_result"] = {"status": "completed", **refresh_data}
        base["hook_status"] = "success"
        base["rollback_status"] = atomic_data.get("rollback_status") or "not_needed"
        remote_write_done = True
    except PostPushError as exc:
        base["errors"].append(exc.to_error())
        if exc.after_remote_write or remote_write_done:
            _mark_remote_failure(base, exc)
        elif exc.category == "not_ready":
            base["hook_status"] = "not_ready"
            base["rollback_status"] = "not_needed"
        else:
            base["hook_status"] = "failed"
            base["rollback_status"] = "not_needed"
    return _finish_run(resolved_repo, base, remote_write_done)


def _base_payload(run_id: str, started_at: str, repo_root: Path | None) -> dict[str, Any]:
    return {
        "hook_status": "running",
        "project": {"project_id": None, "project_name": None, "branch": None, "source": "local"},
        "repo_root": str(repo_root) if repo_root else None,
        "commit_range": [],
        "classification_summary": {"document": 0, "code": 0, "mixed": 0, "empty": 0},
        "commit_results": [],
        "doc_import_results": [],
        "docchange_register_results": [],
        "docchange_link_results": [],
        "graph_refresh_result": {"status": "pending"},
        "run_record": {
            "persistence_mode": "append_history+overwrite_latest",
            "run_id": run_id,
            "started_at": started_at,
            "latest_status": "running",
        },
        "rollback_status": "not_needed",
        "errors": [],
        "skill_hint": SKILL_HINT,
    }


def _finalize(payload: dict[str, Any]) -> dict[str, Any]:
    payload["run_record"]["finished_at"] = _now()
    payload["run_record"]["latest_status"] = payload["hook_status"]
    return payload


def _finish_run(repo_root: Path, payload: dict[str, Any], remote_write_done: bool) -> dict[str, Any]:
    finalized = _finalize(payload)
    try:
        _persist_run(repo_root, finalized)
    except OSError as exc:
        finalized["errors"].append(
            {
                "category": "persistence_failed",
                "message": "post-push run persistence failed",
                "details": {"error": str(exc)},
            }
        )
        finalized["hook_status"] = "failed"
        if remote_write_done:
            _mark_rollback_failed(finalized)
        else:
            finalized["rollback_status"] = "not_needed"
        finalized["run_record"]["latest_status"] = finalized["hook_status"]
        finalized["run_record"]["persistence_error"] = str(exc)
    return finalized


def _mark_rollback_failed(payload: dict[str, Any]) -> None:
    payload["hook_status"] = "failed"
    payload["rollback_status"] = "rollback_failed"
    payload["rollback_summary"] = {
        "mode": "manual_recovery_required",
        "message": (
            "Remote NeoDev CLI writes may already be committed. The plugin layer has no transaction "
            "handle or rollback CLI for doc imports, DocChange records, CodeChangeLinks, or Neo4j graph writes."
        ),
    }


def _mark_remote_failure(payload: dict[str, Any], error: PostPushError) -> None:
    rollback_status = _rollback_status_from_error(error)
    payload["hook_status"] = "failed"
    payload["rollback_status"] = rollback_status
    if rollback_status == "rollback_failed":
        payload["rollback_summary"] = {
            "mode": "manual_recovery_required",
            "message": (
                "The server-side post-push graph update reported that rollback did not complete. "
                "Manual NeoDev recovery is required before trusting graph or DocChange state."
            ),
        }


def _rollback_status_from_error(error: PostPushError) -> str:
    details = error.details or {}
    if details.get("rollback_status"):
        return str(details["rollback_status"])
    payload = details.get("payload") or {}
    first = (payload.get("errors") or [{}])[0]
    first_details = first.get("details") or {}
    if first_details.get("rollback_status"):
        return str(first_details["rollback_status"])
    return "rollback_failed"


def _invalid_atomic_rollback_status(data: dict[str, Any]) -> str:
    status = str(data.get("rollback_status") or "")
    if status in {"rolled_back", "rollback_failed"}:
        return status
    return "rollback_failed"


def _build_atomic_payload(
    base: dict[str, Any],
    project: dict[str, Any],
    branch: str,
    planned: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": base["run_record"]["run_id"],
        "project": {
            "project_id": project.get("project_id"),
            "project_name": project.get("project_name"),
            "doc_binding_id": project.get("doc_binding_id"),
        },
        "branch": branch,
        "push_key": base["run_record"].get("push_key"),
        "commit_range": list(base.get("commit_range") or []),
        "commit_results": planned["commit_results"],
    }


def _write_atomic_payload(repo_root: Path, run_id: str, payload: dict[str, Any]) -> Path:
    state = _state_path(repo_root)
    state.mkdir(parents=True, exist_ok=True)
    target = state / f"{run_id}-payload.json"
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(target)
    return target


def _resolve_repo_root(repo_root: Path | None) -> Path | None:
    if repo_root is not None:
        return repo_root.resolve()
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).resolve()


def _resolve_project(repo_root: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    config_path = repo_root / ".neodev" / "project.json"
    if config_path.exists():
        try:
            data.update(json.loads(config_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            data = {}

    project_id = _first_int(os.environ.get("NEODEV_PROJECT_ID"), data.get("project_id"))
    project_name = _first_text(os.environ.get("NEODEV_PROJECT_NAME"), data.get("project_name"), data.get("name"))
    doc_binding_id = _first_int(os.environ.get("NEODEV_DOC_BINDING_ID"), data.get("doc_binding_id"))
    if project_id is None and not project_name:
        raise PostPushError(
            "not_ready",
            "project is required for post-push graph refresh",
            details={"source": "NEODEV_PROJECT_ID, NEODEV_PROJECT_NAME, or .neodev/project.json"},
        )
    return {
        "project_id": project_id,
        "project_name": project_name,
        "doc_binding_id": doc_binding_id,
        "source": "local",
    }


def _resolve_branch(repo_root: Path) -> str:
    env_branch = _first_text(os.environ.get("NEODEV_BRANCH"))
    if env_branch:
        return env_branch
    for args in (["git", "-C", str(repo_root), "branch", "--show-current"], ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"]):
        proc = subprocess.run(args, text=True, capture_output=True, check=False)
        branch = proc.stdout.strip()
        if proc.returncode == 0 and branch and branch != "HEAD":
            return branch
    return "HEAD"


def _resolve_commits(repo_root: Path, branch: str, project: dict[str, Any]) -> list[str]:
    head = _git_output(repo_root, ["rev-parse", "HEAD"])
    latest_head = _latest_head(repo_root, branch, project)
    upstream = _git_output(repo_root, ["rev-parse", "--verify", "@{u}"], allow_fail=True)

    if latest_head == head:
        return []

    ranges: list[str] = []
    if latest_head and latest_head != head:
        ranges.append(f"{latest_head}..{head}")
    elif upstream and upstream != head:
        ranges.append(f"{upstream}..{head}")
    elif upstream == head:
        previous_upstream = _git_output(repo_root, ["rev-parse", "--verify", "@{u}@{1}"], allow_fail=True)
        if previous_upstream and previous_upstream != head:
            ranges.append(f"{previous_upstream}..{head}")

    for rev_range in ranges:
        commits = _rev_list(repo_root, rev_range)
        if commits:
            return commits
    return [head]


def _plan_commits(repo_root: Path, commits: list[str]) -> dict[str, Any]:
    summary = {"document": 0, "code": 0, "mixed": 0, "empty": 0}
    commit_results: list[dict[str, Any]] = []
    document_commits: list[dict[str, Any]] = []
    code_commits: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for commit_sha in commits:
        paths = _commit_paths(repo_root, commit_sha)
        classification = check_git_commit_scope.classify_paths(paths)
        scope = classification["scope"]
        summary[scope] += 1
        item = {
            "commit_sha": commit_sha,
            "scope": scope,
            "documents": _registerable_document_paths(classification["documents"]),
            "document_paths": classification["documents"],
            "code": classification["code"],
            "route": _route_for_scope(scope),
        }
        commit_results.append(item)
        if scope == "mixed":
            errors.append(
                {
                    "category": "invalid_scope",
                    "message": "NeoDev commit scope is mixed. Split document and code changes.",
                    "details": {"commit_sha": commit_sha, "paths": paths},
                }
            )
        elif scope == "code":
            message = _commit_message(repo_root, commit_sha)
            trailer = check_docchange_trailer.validate_message(message)
            if not trailer.get("ok"):
                first = (trailer.get("errors") or [{}])[0]
                errors.append(
                    {
                        "category": "invalid_argument",
                        "message": first.get("message") or "DocChange-ID trailer is required",
                        "details": {"commit_sha": commit_sha, "errors": trailer.get("errors") or []},
                    }
                )
            else:
                item["commit_message"] = message
                item["doc_change_id"] = trailer["doc_change_id"]
                code_commits.append(item)
        elif scope == "document":
            if len(item["documents"]) > 1:
                errors.append(
                    {
                        "category": "invalid_scope",
                        "message": "NeoDev document commits must change at most one controlled source document.",
                        "details": {"commit_sha": commit_sha, "paths": item["documents"]},
                    }
                )
            elif item["documents"]:
                document_commits.append(item)

    return {
        "classification_summary": summary,
        "commit_results": commit_results,
        "document_commits": document_commits,
        "code_commits": code_commits,
        "errors": errors,
    }


def _route_for_scope(scope: str) -> str:
    return {
        "document": "atomic_post_push_update",
        "code": "atomic_post_push_update",
        "mixed": "rollback_failure",
        "empty": "skip",
    }.get(scope, "unknown")


def _skipped_graph_result(repo_root: Path, reason: str, head_commit: str | None = None) -> dict[str, Any]:
    result = {"status": "skipped", "reason": reason}
    head = head_commit or _git_output(repo_root, ["rev-parse", "HEAD"], allow_fail=True)
    if head:
        result["head_commit"] = head
    return result


def _commit_paths(repo_root: Path, commit_sha: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit_sha],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise PostPushError(
            "internal_error",
            "commit paths unavailable",
            details={"commit_sha": commit_sha, "stderr": proc.stderr},
        )
    return [_normalize_path(line) for line in proc.stdout.splitlines() if _normalize_path(line)]


def _normalize_path(value: str) -> str:
    path = value.strip().replace("\\", "/")
    if not path:
        return ""
    if any(path == prefix[:-1] or path.startswith(prefix) for prefix in INTERNAL_PATH_PREFIXES):
        return ""
    return path


def _commit_message(repo_root: Path, commit_sha: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "log", "-1", "--format=%B", commit_sha],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise PostPushError(
            "internal_error",
            "commit message unavailable",
            details={"commit_sha": commit_sha, "stderr": proc.stderr},
        )
    return proc.stdout


def _run_cli_json(cli: list[str], args: list[str], *, cwd: Path, after_remote_write: bool = True) -> dict[str, Any]:
    proc = subprocess.run([*cli, *args], cwd=cwd, text=True, capture_output=True, check=False)
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PostPushError(
            "internal_error",
            "NeoDev CLI returned non-JSON output",
            details={"args": args, "stdout": proc.stdout, "stderr": proc.stderr},
            after_remote_write=after_remote_write,
        ) from exc

    if proc.returncode != 0 or not payload.get("ok"):
        first = (payload.get("errors") or [{}])[0]
        raise PostPushError(
            first.get("category") or "internal_error",
            first.get("message") or "NeoDev CLI command failed",
            details={"args": args, "payload": payload, "stderr": proc.stderr},
            after_remote_write=after_remote_write,
        )
    return payload


def _resolve_cli() -> list[str] | None:
    configured = os.environ.get("NEODEV_CLI")
    if configured:
        return _split_cli(configured)
    found = shutil.which("neodev")
    if found and os.name == "nt" and found.lower().endswith(".cmd"):
        client = Path(found).with_name("neodev_client.py")
        if client.is_file():
            return [sys.executable, str(client)]
    return [found] if found else None


def _split_cli(value: str) -> list[str]:
    parts = shlex.split(value, posix=os.name != "nt")
    if os.name == "nt":
        return [_strip_wrapping_quotes(part) for part in parts]
    return parts


def _strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _git_output(repo_root: Path, args: list[str], *, allow_fail: bool = False) -> str | None:
    proc = subprocess.run(["git", "-C", str(repo_root), *args], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        if allow_fail:
            return None
        raise PostPushError("internal_error", "git command failed", details={"args": args, "stderr": proc.stderr})
    return proc.stdout.strip()


def _rev_list(repo_root: Path, rev_range: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-list", "--reverse", rev_range],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _latest_head(repo_root: Path, branch: str, project: dict[str, Any]) -> str | None:
    latest_file = _state_path(repo_root) / "latest.json"
    if not latest_file.exists():
        return None
    try:
        latest = json.loads(latest_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(latest, dict):
        return None
    for key in _business_key_candidates(project, branch):
        record = latest.get(key)
        head = _head_from_latest_record(record)
        if head:
            return head
    for record in latest.values():
        if _latest_record_matches_project(record, project, branch):
            head = _head_from_latest_record(record)
            if head:
                return head
    return None


def _head_from_latest_record(record: Any) -> str | None:
    if not isinstance(record, dict):
        return None
    graph = record.get("graph_refresh_result") or {}
    head = graph.get("head_commit")
    return str(head) if head else None


def _latest_record_matches_project(record: Any, project: dict[str, Any], branch: str) -> bool:
    if not isinstance(record, dict):
        return False
    record_project = record.get("project") or {}
    if record_project.get("branch") != branch:
        return False
    project_id = project.get("project_id")
    if project_id and str(record_project.get("project_id") or "") == str(project_id):
        return True
    project_name = project.get("project_name")
    return bool(project_name and record_project.get("project_name") == project_name)


def _persist_run(repo_root: Path, payload: dict[str, Any]) -> None:
    state = _state_path(repo_root)
    state.mkdir(parents=True, exist_ok=True)
    history = state / "history.jsonl"
    with history.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    latest_file = state / "latest.json"
    try:
        latest = json.loads(latest_file.read_text(encoding="utf-8")) if latest_file.exists() else {}
    except (OSError, json.JSONDecodeError):
        latest = {}
    latest[_business_key(payload)] = payload
    tmp = latest_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(latest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(latest_file)


def _business_key(payload: dict[str, Any]) -> str:
    project = payload.get("project") or {}
    branch = project.get("branch") or "HEAD"
    return _business_key_from_values(project, branch, repo_root=payload.get("repo_root"))


def _business_key_from_values(project: dict[str, Any], branch: str, repo_root: str | None = None) -> str:
    project_key = project.get("project_id") or project.get("project_name") or repo_root or "unknown"
    return f"project:{project_key}:branch:{branch}"


def _business_key_candidates(project: dict[str, Any], branch: str) -> list[str]:
    keys = []
    for project_key in (project.get("project_id"), project.get("project_name")):
        if project_key:
            keys.append(f"project:{project_key}:branch:{branch}")
    return keys


def _push_key(commits: list[str]) -> str | None:
    if not commits:
        return None
    return f"{commits[0]}..{commits[-1]}" if len(commits) > 1 else commits[0]


def _registerable_document_paths(paths: list[str]) -> list[str]:
    return [
        path
        for path in paths
        if Path(path).suffix.lower() in REGISTERABLE_DOC_EXTENSIONS
    ]


def _state_path(repo_root: Path) -> Path:
    return repo_root / ".neodev" / STATE_DIR


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _first_int(*values: Any) -> int | None:
    for value in values:
        if value is None or value == "":
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)

    payload = run_post_push(args.repo_root)
    if args.json_output:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"post-push graph update: {payload['hook_status']}")
    return 0 if payload["hook_status"] in {"success", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
