"""Scan controlled product documents and persist document metadata."""

from datetime import datetime, timezone
from pathlib import Path

import yaml

from service.repositories import doc_binding_repository
from service.repositories import document_repository
from service.repositories import document_scan_error_repository
from service.services.doc_validation_service import DocumentValidationError
from service.services.doc_validation_service import validate_front_matter


CONTROLLED_DIRECTORIES = {"prd", "prototype", "tech-design"}


def scan_binding(conn, doc_binding_id: int) -> dict:
    binding = doc_binding_repository.find_by_id(conn, doc_binding_id)
    if not binding:
        raise ValueError(f"doc binding not found: {doc_binding_id}")

    repo_path = Path(binding["repo_path"])
    if not repo_path.is_dir():
        error = document_scan_error_repository.create(
            conn,
            doc_binding_id=doc_binding_id,
            relative_path=".",
            error_code="repo_not_found",
            error_message="document repository path does not exist",
            details_json={"repo_path": str(repo_path)},
        )
        return _summary([], [error], ignored_count=0)

    registered = []
    errors = []
    ignored_count = 0
    for path in sorted(repo_path.rglob("*.md")):
        relative_path = _relative_path(repo_path, path)
        if _top_level_directory(relative_path) not in CONTROLLED_DIRECTORIES:
            ignored_count += 1
            continue
        try:
            front_matter = _read_front_matter(path)
            validated = validate_front_matter(front_matter)
            registered.append(_persist_document(conn, binding, relative_path, validated))
        except DocumentValidationError as exc:
            errors.append(
                document_scan_error_repository.create(
                    conn,
                    doc_binding_id=doc_binding_id,
                    relative_path=relative_path,
                    error_code="invalid_front_matter",
                    error_message=exc.message,
                    details_json=exc.details,
                )
            )
        except ValueError as exc:
            errors.append(
                document_scan_error_repository.create(
                    conn,
                    doc_binding_id=doc_binding_id,
                    relative_path=relative_path,
                    error_code="invalid_front_matter",
                    error_message=str(exc),
                    details_json={},
                )
            )

    return _summary(registered, errors, ignored_count)


def _persist_document(conn, binding: dict, relative_path: str, front_matter: dict) -> dict:
    return document_repository.upsert(
        conn,
        doc_binding_id=binding["id"],
        doc_id=front_matter["doc_id"],
        relative_path=relative_path,
        doc_type=front_matter["doc_type"],
        front_matter_json=front_matter,
        relations_json=front_matter["relations"],
        status=front_matter["status"],
        last_scanned_at=datetime.now(timezone.utc),
        title=front_matter["title"],
    )


def _read_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("document must start with YAML front matter")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("document front matter must be closed with ---")
    front_matter_text = "\n".join(lines[1:end])
    try:
        parsed = yaml.safe_load(front_matter_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML front matter: {exc}") from exc
    return parsed


def _relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _top_level_directory(relative_path: str) -> str:
    return relative_path.split("/", 1)[0]


def _summary(registered: list[dict], errors: list[dict], ignored_count: int) -> dict:
    return {
        "registered_count": len(registered),
        "error_count": len(errors),
        "ignored_count": ignored_count,
        "documents": registered,
        "errors": errors,
    }
