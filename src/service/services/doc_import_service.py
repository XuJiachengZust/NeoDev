"""Git-backed document import pipeline."""

from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from service.cli.errors import CliError
from service.repositories import doc_binding_repository
from service.repositories import document_chunk_repository
from service.repositories import document_repository
from service.repositories import document_scan_error_repository
from service.services import doc_chunk_service
from service.services import doc_graph_service
from service.services import doc_vector_service
from service.services.doc_scan_service import should_ignore_markdown_path
from service.services.doc_validation_service import DocumentValidationError
from service.services.doc_validation_service import validate_front_matter


def import_binding(conn, doc_binding_id: int, *, force: bool = False) -> dict[str, Any]:
    binding = doc_binding_repository.find_by_id(conn, doc_binding_id)
    if not binding:
        raise CliError(category="not_found", message="doc binding not found")
    _sync_git_repo(binding)
    repo_path = Path(binding["repo_path"])
    if not repo_path.is_dir():
        raise CliError(
            category="not_found",
            message="document repository path does not exist",
            details={"repo_path": str(repo_path)},
        )
    if not (repo_path / ".git").exists():
        raise CliError(
            category="invalid_scope",
            message="document import requires a git checkout",
            details={"repo_path": str(repo_path)},
        )

    imported = []
    errors = []
    active_paths: list[str] = []
    chunk_count = 0
    embedded_count = 0
    reused_count = 0

    for path in sorted(repo_path.rglob("*.md")):
        relative_path = path.relative_to(repo_path).as_posix()
        if should_ignore_markdown_path(relative_path):
            continue
        active_paths.append(relative_path)
        try:
            parsed = _read_markdown_document(path)
            front_matter = validate_front_matter(parsed["front_matter"])
            body_text = parsed["body_text"]
            content_hash = _content_hash(front_matter, body_text)
            last_seen_commit = _last_commit_for_path(repo_path, relative_path)
            document = document_repository.upsert(
                conn,
                doc_binding_id=binding["id"],
                doc_id=front_matter["doc_id"],
                relative_path=relative_path,
                doc_type=front_matter["doc_type"],
                front_matter_json=front_matter,
                relations_json=front_matter["relations"],
                status=front_matter["status"],
                last_seen_commit=last_seen_commit,
                last_scanned_at=datetime.now(timezone.utc),
                title=front_matter["title"],
                body_text=body_text,
                content_hash=content_hash,
                graph_status="pending",
                chunk_status="pending",
            )
            doc_graph_service.upsert_document_graph(conn, binding=binding, document=document)
            chunks = doc_chunk_service.chunk_markdown(body_text)
            persisted_chunks = document_chunk_repository.replace_document_chunks(
                conn,
                document["id"],
                chunks,
            )
            vector_stats = doc_vector_service.embed_chunks(
                conn,
                document,
                persisted_chunks,
                force=force,
            )
            chunk_count += len(persisted_chunks)
            embedded_count += int(vector_stats.get("embedded_count") or 0)
            reused_count += int(vector_stats.get("reused_count") or 0)
            imported.append({**document, "chunk_count": len(persisted_chunks)})
        except DocumentValidationError as exc:
            errors.append(_record_error(conn, binding["id"], relative_path, exc.message, exc.details))
        except Exception as exc:  # noqa: BLE001
            errors.append(_record_error(conn, binding["id"], relative_path, str(exc), {}))

    deleted = document_repository.mark_missing_deleted(conn, binding["id"], active_paths)
    return {
        "doc_binding_id": binding["id"],
        "imported_count": len(imported),
        "updated_count": len(imported),
        "deleted_count": len(deleted),
        "failed_count": len(errors),
        "chunk_count": chunk_count,
        "embedded_count": embedded_count,
        "reused_count": reused_count,
        "documents": imported,
        "errors": errors,
    }


def _sync_git_repo(binding: dict) -> None:
    repo_path = Path(binding.get("repo_path") or "")
    repo_url = (binding.get("repo_url") or "").strip()
    branch = (binding.get("default_branch") or "main").strip()
    if repo_path.is_dir() and (repo_path / ".git").exists():
        _run_git(["git", "-C", str(repo_path), "fetch", "--all"])
        _run_git(["git", "-C", str(repo_path), "checkout", branch])
        _run_git(["git", "-C", str(repo_path), "pull", "--ff-only"])
        return
    if repo_path.exists() or not repo_url:
        return
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    _run_git(["git", "clone", "--branch", branch, repo_url, str(repo_path)])


def _run_git(args: list[str]) -> None:
    proc = subprocess.run(args, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise CliError(
            category="internal_error",
            message="git document repository sync failed",
            details={"command": args, "stderr": proc.stderr},
        )


def _last_commit_for_path(repo_path: Path, relative_path: str) -> str:
    _ensure_path_clean(repo_path, relative_path)
    proc = subprocess.run(
        ["git", "-C", str(repo_path), "log", "-1", "--format=%H", "--", relative_path],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise CliError(
            category="internal_error",
            message="git document commit lookup failed",
            details={"relative_path": relative_path, "stderr": proc.stderr},
        )
    commit_hash = proc.stdout.strip()
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit_hash):
        raise CliError(
            category="invalid_scope",
            message="document file has no committed git version",
            details={"relative_path": relative_path},
        )
    return commit_hash.lower()


def _ensure_path_clean(repo_path: Path, relative_path: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(repo_path), "status", "--porcelain", "--", relative_path],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise CliError(
            category="internal_error",
            message="git document status lookup failed",
            details={"relative_path": relative_path, "stderr": proc.stderr},
        )
    if proc.stdout.strip():
        raise CliError(
            category="invalid_scope",
            message="document file has uncommitted changes; commit before import",
            details={"relative_path": relative_path, "git_status": proc.stdout.strip()},
        )


def _read_markdown_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("document must start with YAML front matter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("document front matter must be closed with ---") from exc
    front_matter_text = "\n".join(lines[1:end])
    try:
        front_matter = yaml.safe_load(front_matter_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML front matter: {exc}") from exc
    return {"front_matter": front_matter, "body_text": "\n".join(lines[end + 1 :]).strip()}


def _content_hash(front_matter: dict, body_text: str) -> str:
    raw = yaml.safe_dump(front_matter, sort_keys=True, allow_unicode=True) + "\0" + body_text
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _record_error(conn, binding_id: int, relative_path: str, message: str, details: dict) -> dict:
    return document_scan_error_repository.create(
        conn,
        doc_binding_id=binding_id,
        relative_path=relative_path,
        error_code="document_import_failed",
        error_message=message,
        details_json=details,
    )
