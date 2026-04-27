"""Validate NeoDev MVP controlled document front matter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml


CONTROLLED_DIRECTORIES = {"prd", "prototype", "tech-design"}
REQUIRED_FIELDS = {
    "doc_id",
    "title",
    "doc_type",
    "product_key",
    "status",
    "relations",
}
VALID_DOC_TYPES = {"prd", "prototype", "tech-design"}
VALID_STATUSES = {"draft", "active", "deprecated"}


def validate_paths(paths: list[Path]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    checked_count = 0
    for path in _iter_markdown_files(paths):
        checked_count += 1
        errors.extend(_validate_file(path))
    return {"ok": not errors, "checked_count": checked_count, "errors": errors}


def _iter_markdown_files(paths: list[Path]):
    roots = paths or [Path("prd"), Path("prototype"), Path("tech-design")]
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


def _validate_file(path: Path) -> list[dict[str, Any]]:
    try:
        front_matter = _read_front_matter(path)
    except ValueError as exc:
        return [_error(path, "front_matter", str(exc))]

    errors: list[dict[str, Any]] = []
    if not isinstance(front_matter, dict):
        return [_error(path, "front_matter", "front matter must be a mapping")]

    for field in sorted(REQUIRED_FIELDS):
        if not front_matter.get(field):
            errors.append(_error(path, field, f"{field} is required"))

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

    return errors


def _read_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("document must start with YAML front matter")
    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError("document front matter must be closed with ---")
    try:
        return yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML front matter: {exc}") from exc


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
