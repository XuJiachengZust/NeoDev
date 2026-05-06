"""Sync NeoDev doc_id relations into Obsidian-readable wiki links."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml


DEFAULT_SECTION_TITLE = "关联文档"


class QuotedString(str):
    pass


def _quoted_string_presenter(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")


yaml.add_representer(QuotedString, _quoted_string_presenter, Dumper=yaml.SafeDumper)


def sync_paths(
    paths: list[Path],
    *,
    section_title: str = DEFAULT_SECTION_TITLE,
    write_body_section: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    records = _read_records(paths)
    by_doc_id = {record["front_matter"]["doc_id"]: record for record in records}
    if len(by_doc_id) != len(records):
        return {
            "ok": False,
            "updated_count": 0,
            "checked_count": len(records),
            "errors": [{"field": "doc_id", "message": "duplicate doc_id found"}],
        }

    errors: list[dict[str, str]] = []
    updated: list[str] = []
    for record in records:
        front_matter = record["front_matter"]
        target_ids = ((front_matter.get("relations") or {}).get("target") or [])
        links: list[str] = []
        for target_id in target_ids:
            target = by_doc_id.get(target_id)
            if not target:
                errors.append(
                    {
                        "path": record["relative_path"],
                        "field": "relations.target",
                        "message": f"unknown doc_id: {target_id}",
                    }
                )
                continue
            links.append(_wiki_link(target))

        unique_links = list(dict.fromkeys(links))
        front_matter["related"] = [QuotedString(link) for link in unique_links]
        body = record["body"]
        if write_body_section:
            body = _replace_related_section(body, unique_links, section_title)

        new_text = _render_document(front_matter, body)
        if new_text != record["text"]:
            updated.append(record["relative_path"])
            if not dry_run:
                record["path"].write_text(new_text, encoding="utf-8")

    return {
        "ok": not errors,
        "checked_count": len(records),
        "updated_count": len(updated),
        "updated": updated,
        "errors": errors,
        "body_section": write_body_section,
        "section_title": section_title,
    }


def _read_records(paths: list[Path]) -> list[dict[str, Any]]:
    roots = paths or [Path("docs")]
    records: list[dict[str, Any]] = []
    for root in roots:
        base = root if root.is_dir() else root.parent
        candidates = [root] if root.is_file() else sorted(root.rglob("*.md"))
        for path in candidates:
            if path.suffix.lower() != ".md":
                continue
            text = path.read_text(encoding="utf-8")
            if not text.startswith("---\n"):
                raise ValueError(f"document must start with YAML front matter: {path}")
            try:
                _, front_matter_text, body = text.split("---", 2)
            except ValueError as exc:
                raise ValueError(f"document front matter must be closed with ---: {path}") from exc
            front_matter = yaml.safe_load(front_matter_text) or {}
            if not isinstance(front_matter, dict):
                raise ValueError(f"front matter must be a mapping: {path}")
            if not isinstance(front_matter.get("doc_id"), str):
                raise ValueError(f"doc_id is required: {path}")
            records.append(
                {
                    "path": path,
                    "relative_path": path.relative_to(base).as_posix(),
                    "front_matter": front_matter,
                    "body": body.lstrip("\n").rstrip() + "\n",
                    "text": text,
                }
            )
    return records


def _wiki_link(record: dict[str, Any]) -> str:
    target = record["relative_path"]
    if target.endswith(".md"):
        target = target[:-3]
    title = str(record["front_matter"].get("title") or Path(target).stem).replace("|", "-")
    return f"[[{target}|{title}]]"


def _replace_related_section(body: str, links: list[str], section_title: str) -> str:
    body = _strip_related_section(body, section_title).rstrip()
    if not links:
        return body + "\n"
    lines = [f"## {section_title}", *[f"- {link}" for link in links]]
    return body + "\n\n" + "\n".join(lines) + "\n"


def _strip_related_section(body: str, section_title: str) -> str:
    marker = f"\n## {section_title}\n"
    body = body.rstrip()
    index = body.rfind(marker)
    if index == -1:
        return body
    tail = body[index + len(marker) :]
    lines = [line for line in tail.splitlines() if line.strip()]
    if lines and all(line.startswith("- [[") and line.endswith("]]") for line in lines):
        return body[:index]
    return body


def _render_document(front_matter: dict[str, Any], body: str) -> str:
    rendered_front_matter = yaml.safe_dump(
        front_matter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    return f"---\n{rendered_front_matter}\n---\n\n{body.rstrip()}\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--section-title", default=DEFAULT_SECTION_TITLE)
    parser.add_argument("--no-body-section", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = sync_paths(
            args.paths,
            section_title=args.section_title,
            write_body_section=not args.no_body_section,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        payload = {"ok": False, "checked_count": 0, "updated_count": 0, "errors": [str(exc)]}
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
