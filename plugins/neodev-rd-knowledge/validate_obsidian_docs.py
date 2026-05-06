"""Validate repository Markdown docs for NeoDev and Obsidian compatibility."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml


REQUIRED_FIELDS = {
    "aliases",
    "created",
    "doc_id",
    "doc_type",
    "product_key",
    "related",
    "relations",
    "status",
    "tags",
    "title",
    "updated",
}
VALID_DOC_TYPES = {"prd", "prototype", "tech-design"}
VALID_STATUSES = {"draft", "active", "deprecated"}
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
WIKI_LINK_PATTERN = re.compile(r"\[\[([^\]|#]+)")


@dataclass(frozen=True)
class ParsedDoc:
    path: Path
    front_matter: dict[str, Any]


def validate_paths(paths: list[Path]) -> dict[str, Any]:
    docs: list[ParsedDoc] = []
    errors: list[dict[str, str]] = []
    for path in _iter_markdown_files(paths):
        try:
            front_matter = _read_front_matter(path)
        except ValueError as exc:
            errors.append(_error(path, "front_matter", str(exc)))
            continue
        docs.append(ParsedDoc(path=path, front_matter=front_matter))
        errors.extend(_validate_front_matter(path, front_matter))

    doc_ids = _doc_id_index(docs)
    wiki_targets = _wiki_target_index(docs, paths)
    for doc in docs:
        errors.extend(_validate_relation_targets(doc, doc_ids))
        errors.extend(_validate_related_links(doc, wiki_targets))

    return {"ok": not errors, "checked_count": len(docs) + _front_matter_error_count(errors), "errors": errors}


def _iter_markdown_files(paths: list[Path]):
    roots = paths or [Path("docs")]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        candidates = [root] if root.is_file() else sorted(root.rglob("*.md"))
        for candidate in candidates:
            if candidate.suffix.lower() != ".md":
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield candidate


def _read_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].lstrip("\ufeff") != "---":
        raise ValueError("document must start with YAML front matter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("document front matter must be closed with ---") from exc
    try:
        parsed = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML front matter: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("front matter must be a mapping")
    return parsed


def _validate_front_matter(path: Path, front_matter: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for field in sorted(REQUIRED_FIELDS):
        if not front_matter.get(field):
            errors.append(_error(path, field, f"{field} is required"))

    errors.extend(_validate_string_list(path, front_matter.get("aliases"), "aliases"))
    errors.extend(
        _validate_string_list(
            path,
            front_matter.get("tags"),
            "tags",
            reject_hash_prefix=True,
        )
    )
    errors.extend(_validate_string_list(path, front_matter.get("related"), "related"))
    errors.extend(_validate_date(path, front_matter.get("created"), "created"))
    errors.extend(_validate_date(path, front_matter.get("updated"), "updated"))

    doc_type = front_matter.get("doc_type")
    if doc_type and doc_type not in VALID_DOC_TYPES:
        errors.append(_error(path, "doc_type", "doc_type must be one of: prd, prototype, tech-design"))

    status = front_matter.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(_error(path, "status", "status must be one of: draft, active, deprecated"))

    relations = front_matter.get("relations")
    if relations and not isinstance(relations, dict):
        errors.append(_error(path, "relations", "relations must be a mapping"))
    elif isinstance(relations, dict):
        target = relations.get("target")
        if not isinstance(target, list) or not target:
            errors.append(_error(path, "relations.target", "relations.target must be a non-empty list"))
        elif any(not isinstance(item, str) or not item.strip() for item in target):
            errors.append(_error(path, "relations.target", "relations.target must contain non-empty strings"))

    return errors


def _validate_string_list(
    path: Path,
    value: Any,
    field: str,
    *,
    reject_hash_prefix: bool = False,
) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list) or not value:
        return [_error(path, field, f"{field} must be a non-empty list")]
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return [_error(path, field, f"{field} must contain non-empty strings")]
    if reject_hash_prefix and any(item.strip().startswith("#") for item in value):
        return [_error(path, field, f"{field} entries must omit the leading #")]
    return []


def _validate_date(path: Path, value: Any, field: str) -> list[dict[str, str]]:
    if value is None:
        return []
    if isinstance(value, date):
        return []
    if isinstance(value, str) and DATE_PATTERN.fullmatch(value):
        return []
    return [_error(path, field, f"{field} must use YYYY-MM-DD")]


def _doc_id_index(docs: list[ParsedDoc]) -> dict[str, Path]:
    return {
        str(doc.front_matter["doc_id"]): doc.path
        for doc in docs
        if isinstance(doc.front_matter.get("doc_id"), str)
    }


def _wiki_target_index(docs: list[ParsedDoc], paths: list[Path]) -> set[str]:
    roots = _wiki_roots(paths)
    targets: set[str] = set()
    for doc in docs:
        targets.add(doc.path.stem)
        for root in roots:
            try:
                relative = doc.path.resolve().relative_to(root.resolve()).as_posix()
            except ValueError:
                continue
            if relative.endswith(".md"):
                targets.add(relative[:-3])
    return targets


def _wiki_roots(paths: list[Path]) -> list[Path]:
    roots = paths or [Path("docs")]
    result: list[Path] = []
    for root in roots:
        if root.is_file():
            result.append(root.parent)
        else:
            result.append(root)
    return result


def _validate_relation_targets(doc: ParsedDoc, doc_ids: dict[str, Path]) -> list[dict[str, str]]:
    relations = doc.front_matter.get("relations")
    if not isinstance(relations, dict) or not isinstance(relations.get("target"), list):
        return []
    errors: list[dict[str, str]] = []
    for target in relations["target"]:
        if isinstance(target, str) and target not in doc_ids:
            errors.append(_error(doc.path, "relations.target", f"unknown doc_id: {target}"))
    return errors


def _validate_related_links(doc: ParsedDoc, wiki_targets: set[str]) -> list[dict[str, str]]:
    related = doc.front_matter.get("related")
    if not isinstance(related, list):
        return []
    errors: list[dict[str, str]] = []
    for item in related:
        if not isinstance(item, str):
            continue
        matches = WIKI_LINK_PATTERN.findall(item)
        if not matches:
            errors.append(_error(doc.path, "related", f"related entry must use wiki link syntax: {item}"))
            continue
        for note_name in matches:
            if note_name not in wiki_targets:
                errors.append(_error(doc.path, "related", f"unknown wiki link: [[{note_name}]]"))
    return errors


def _front_matter_error_count(errors: list[dict[str, str]]) -> int:
    return sum(1 for error in errors if error["field"] == "front_matter")


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
