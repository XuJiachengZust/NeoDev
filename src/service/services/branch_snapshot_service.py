"""Branch snapshot metadata orchestration."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from gitnexus_parser.ingestion.facts import build_file_fact_id
from gitnexus_parser.ingestion.walker import walk_repository_paths

from service.repositories import branch_snapshot_repository as snapshot_repo


def create_snapshot_from_repo(
    conn,
    *,
    repo_path: str,
    project_id: int,
    branch: str,
    head_commit: str | None,
    last_parsed_commit: str | None,
    created_from_action: str,
    repo_id: int | None = None,
    base_snapshot_id: int | None = None,
) -> dict[str, Any]:
    normalized_branch = (branch or "").strip()
    resolved_repo_id = repo_id if repo_id is not None else project_id
    if base_snapshot_id is None and created_from_action in {"incremental", "commit_incremental"}:
        current = snapshot_repo.get_current_snapshot(conn, project_id, normalized_branch)
        base_snapshot_id = current.get("id") if current else None

    snapshot = snapshot_repo.create_snapshot(
        conn,
        project_id=project_id,
        repo_id=resolved_repo_id,
        branch=normalized_branch,
        head_commit=head_commit,
        last_parsed_commit=last_parsed_commit,
        base_snapshot_id=base_snapshot_id,
        created_from_action=created_from_action,
        status="completed",
    )
    entries = _build_file_entries(Path(repo_path), project_id=project_id, repo_id=resolved_repo_id)
    entry_count = snapshot_repo.replace_entries(conn, snapshot["id"], entries)
    snapshot["entry_count"] = entry_count
    return snapshot


def clone_snapshot(
    conn,
    *,
    source_snapshot_id: int,
    project_id: int,
    branch: str,
    head_commit: str | None,
    last_parsed_commit: str | None,
    repo_id: int | None = None,
) -> dict[str, Any]:
    resolved_repo_id = repo_id if repo_id is not None else project_id
    snapshot = snapshot_repo.create_snapshot(
        conn,
        project_id=project_id,
        repo_id=resolved_repo_id,
        branch=(branch or "").strip(),
        head_commit=head_commit,
        last_parsed_commit=last_parsed_commit,
        base_snapshot_id=source_snapshot_id,
        created_from_action="copy_data",
        status="completed",
    )
    entry_count = snapshot_repo.copy_entries(
        conn,
        source_snapshot_id,
        snapshot["id"],
        project_id=project_id,
        repo_id=resolved_repo_id,
    )
    snapshot["entry_count"] = entry_count
    return snapshot


def get_current_snapshot(conn, project_id: int, branch: str) -> dict[str, Any] | None:
    return snapshot_repo.get_current_snapshot(conn, project_id, (branch or "").strip())


def list_entries(conn, snapshot_id: int, *, visible_only: bool = True) -> list[dict[str, Any]]:
    return snapshot_repo.list_entries(conn, snapshot_id, visible_only=visible_only)


def _build_file_entries(repo_path: Path, *, project_id: int, repo_id: int) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in sorted(walk_repository_paths(str(repo_path)), key=lambda entry: entry.path):
        full_path = repo_path / item.path
        try:
            content = full_path.read_bytes()
        except OSError:
            continue
        file_content_hash = hashlib.sha256(content).hexdigest()
        entries.append(
            {
                "project_id": project_id,
                "repo_id": repo_id,
                "file_path": item.path,
                "file_node_id": build_file_fact_id(
                    repo_id=repo_id,
                    file_path=item.path,
                    file_content_hash=file_content_hash,
                ),
                "file_content_hash": file_content_hash,
                "visible": True,
            }
        )
    return entries
