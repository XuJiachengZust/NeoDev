"""Validate NeoDev MVP controlled document front matter."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml


CONTROLLED_DIRECTORIES = {"prd", "prototype", "tech-design", "docs"}
REQUIRED_FIELDS = {
    "aliases",
    "created",
    "doc_id",
    "title",
    "doc_type",
    "product_key",
    "related",
    "status",
    "tags",
    "updated",
    "relations",
}
VALID_DOC_TYPES = {"prd", "prototype", "tech-design"}
VALID_STATUSES = {"draft", "active", "deprecated"}
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
NEOSUPERPOWER_CHILDREN = {"plans", "specs", "skills", "reports", "templates"}


def validate_paths(paths: list[Path]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    checked_count = 0
    valid_documents: list[tuple[Path, dict[str, Any]]] = []
    for path in _iter_markdown_files(paths):
        checked_count += 1
        file_errors, front_matter = _validate_file(path)
        errors.extend(file_errors)
        if isinstance(front_matter, dict):
            valid_documents.append((path, front_matter))
    doc_ids = {
        str(front_matter["doc_id"])
        for _, front_matter in valid_documents
        if isinstance(front_matter.get("doc_id"), str)
    }
    for path, front_matter in valid_documents:
        errors.extend(_validate_relation_targets(path, front_matter, doc_ids))
    return {"ok": not errors, "checked_count": checked_count, "errors": errors}


def _iter_markdown_files(paths: list[Path]):
    roots = paths or [Path("prd"), Path("prototype"), Path("tech-design"), Path("docs")]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else sorted(root.rglob("*.md"))
        for candidate in candidates:
            if candidate.suffix.lower() != ".md":
                continue
            if not _is_controlled_document(candidate):
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield candidate


def _is_controlled_document(path: Path) -> bool:
    return any(part in CONTROLLED_DIRECTORIES for part in path.parts)


def _validate_file(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    try:
        front_matter = _read_front_matter(path)
    except ValueError as exc:
        return [_error(path, "front_matter", str(exc))], None

    errors: list[dict[str, Any]] = []
    errors.extend(_validate_directory_structure(path))
    if not isinstance(front_matter, dict):
        return [_error(path, "front_matter", "front matter must be a mapping")], None

    for field in sorted(REQUIRED_FIELDS):
        if not front_matter.get(field):
            errors.append(_error(path, field, f"{field} is required"))

    errors.extend(
        _validate_list_field(
            path,
            front_matter.get("aliases"),
            "aliases",
            "aliases must be a non-empty list",
        )
    )
    errors.extend(
        _validate_list_field(
            path,
            front_matter.get("tags"),
            "tags",
            "tags must be a non-empty list without leading #",
            reject_hash_prefix=True,
        )
    )
    errors.extend(
        _validate_list_field(
            path,
            front_matter.get("related"),
            "related",
            "related must be a non-empty list",
        )
    )
    errors.extend(_validate_date_field(path, front_matter.get("created"), "created"))
    errors.extend(_validate_date_field(path, front_matter.get("updated"), "updated"))

    doc_type = front_matter.get("doc_type")
    if doc_type and doc_type not in VALID_DOC_TYPES:
        errors.append(
            _error(
                path,
                "doc_type",
                "doc_type must be one of: prd, prototype, tech-design",
            )
        )

    status = front_matter.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(
            _error(path, "status", "status must be one of: draft, active, deprecated")
        )

    relations = front_matter.get("relations")
    if relations:
        if not isinstance(relations, dict):
            errors.append(_error(path, "relations", "relations must be a mapping"))
        else:
            target = relations.get("target")
            if not isinstance(target, list) or not target:
                errors.append(
                    _error(
                        path,
                        "relations.target",
                        "relations.target must be a non-empty list",
                    )
                )
            elif any(not isinstance(item, str) or not item.strip() for item in target):
                errors.append(
                    _error(
                        path,
                        "relations.target",
                        "relations.target must contain non-empty strings",
                    )
                )

    return errors, front_matter


def _validate_directory_structure(path: Path) -> list[dict[str, str]]:
    parts = path.parts
    if "superpowers" in parts:
        return [_error(path, "path", "use neosuperpower/, not superpowers/")]
    if ".obsidian" in parts:
        return [_error(path, "path", "controlled docs must not live inside .obsidian")]
    if "neosuperpower" in parts:
        index = parts.index("neosuperpower")
        if len(parts) <= index + 2 or parts[index + 1] not in NEOSUPERPOWER_CHILDREN:
            return [
                _error(
                    path,
                    "path",
                    "neosuperpower docs must be under plans/, specs/, skills/<skill_name>/, reports/, or templates/",
                )
            ]
    return []


def _validate_relation_targets(
    path: Path,
    front_matter: dict[str, Any],
    doc_ids: set[str],
) -> list[dict[str, str]]:
    relations = front_matter.get("relations")
    if not isinstance(relations, dict) or not isinstance(relations.get("target"), list):
        return []
    errors: list[dict[str, str]] = []
    for target in relations["target"]:
        if isinstance(target, str) and target not in doc_ids:
            errors.append(_error(path, "relations.target", f"unknown doc_id: {target}"))
    return errors


def _read_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].lstrip("\ufeff") != "---":
        raise ValueError("document must start with YAML front matter")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise ValueError("document front matter must be closed with ---")
    front_matter_text = "\n".join(lines[1:end])
    try:
        return yaml.safe_load(front_matter_text)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML front matter: {exc}") from exc


def _validate_list_field(
    path: Path,
    value: Any,
    field: str,
    message: str,
    *,
    reject_hash_prefix: bool = False,
) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or not value:
        return [_error(path, field, message)]
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return [_error(path, field, f"{field} must contain non-empty strings")]
    if reject_hash_prefix and any(item.strip().startswith("#") for item in value):
        return [_error(path, field, message)]
    return []


def _validate_date_field(path: Path, value: Any, field: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if isinstance(value, date):
        return []
    if isinstance(value, str) and DATE_PATTERN.fullmatch(value):
        return []
    return [_error(path, field, f"{field} must use YYYY-MM-DD")]


def _error(path: Path, field: str, message: str) -> dict[str, str]:
    return {"path": path.as_posix(), "field": field, "message": message}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args(argv)
    payload = validate_paths(args.paths)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
