"""Generate a NeoDev controlled document and validate graph-ready metadata."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from validate_mvp_docs import validate_paths as validate_mvp_paths
from validate_obsidian_docs import validate_paths as validate_obsidian_paths


TEMPLATE_PATH = Path(__file__).resolve().parent / "assets" / "templates" / "mvp-doc.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--doc-type", choices=["prd", "prototype", "tech-design"], required=True)
    parser.add_argument("--product-key", required=True)
    parser.add_argument("--status", default="draft", choices=["draft", "active", "deprecated"])
    parser.add_argument("--target", action="append", required=True, help="Target document doc_id")
    parser.add_argument("--tag", action="append", default=[], help="Additional tag without leading #")
    parser.add_argument("--docs-root", type=Path, help="Markdown vault/root used to resolve target doc_id values")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    docs_root = (args.docs_root or _infer_docs_root(args.output)).resolve()
    output = args.output.resolve()
    index = _load_doc_index(docs_root)
    index[args.doc_id] = {
        "path": output,
        "relative_path": output.relative_to(docs_root).as_posix(),
        "title": args.title,
    }
    unresolved = [target for target in args.target if target not in index]
    if unresolved:
        payload = {
            "ok": False,
            "checked_count": 0,
            "output": output.as_posix(),
            "errors": [
                {
                    "field": "relations.target",
                    "message": f"unknown doc_id: {target}",
                }
                for target in unresolved
            ],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 1

    rendered = _render_template(
        doc_id=args.doc_id,
        title=args.title,
        doc_type=args.doc_type,
        product_key=args.product_key,
        status=args.status,
        targets=args.target,
        tags=_tags(args.product_key, args.doc_type, args.tag),
        doc_index=index,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")

    mvp_payload = validate_mvp_paths([docs_root])
    obsidian_payload = validate_obsidian_paths([docs_root])
    payload = {
        "ok": bool(mvp_payload["ok"] and obsidian_payload["ok"]),
        "output": output.as_posix(),
        "docs_root": docs_root.as_posix(),
        "mvp": mvp_payload,
        "obsidian": obsidian_payload,
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


def _infer_docs_root(output: Path) -> Path:
    resolved = output.resolve()
    for candidate in [resolved.parent, *resolved.parents]:
        if candidate.name == "docs":
            return candidate
    return resolved.parent


def _load_doc_index(docs_root: Path) -> dict[str, dict[str, str | Path]]:
    index: dict[str, dict[str, str | Path]] = {}
    if not docs_root.exists():
        return index
    for path in sorted(docs_root.rglob("*.md")):
        front_matter = _read_front_matter(path)
        doc_id = front_matter.get("doc_id")
        if not isinstance(doc_id, str) or not doc_id.strip():
            continue
        index[doc_id] = {
            "path": path.resolve(),
            "relative_path": path.resolve().relative_to(docs_root).as_posix(),
            "title": str(front_matter.get("title") or path.stem),
        }
    return index


def _read_front_matter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].lstrip("\ufeff") != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    parsed = yaml.safe_load("\n".join(lines[1:end]))
    return parsed if isinstance(parsed, dict) else {}


def _tags(product_key: str, doc_type: str, extra_tags: list[str]) -> list[str]:
    prefix = product_key.lower()
    tags = [f"{prefix}/docs", f"{prefix}/{doc_type}", "neosuperpower/generated"]
    tags.extend(tag.strip() for tag in extra_tags if tag.strip())
    return list(dict.fromkeys(tags))


def _render_template(
    *,
    doc_id: str,
    title: str,
    doc_type: str,
    product_key: str,
    status: str,
    targets: list[str],
    tags: list[str],
    doc_index: dict[str, dict[str, str | Path]],
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    target_lines = "\n".join(f"    - {target}" for target in targets)
    tag_lines = "\n".join(f"  - {tag}" for tag in tags)
    related_links = [_wiki_link(doc_index[target]) for target in targets]
    related_lines = "\n".join(f"  - '{link}'" for link in related_links)
    body_related = "\n".join(f"- {link}" for link in related_links)
    today = date.today().isoformat()
    return template.format(
        doc_id=doc_id,
        title=title,
        doc_type=doc_type,
        product_key=product_key,
        status=status,
        targets=target_lines,
        tags=tag_lines,
        related=related_lines,
        body_related=body_related,
        created=today,
        updated=today,
    )


def _wiki_link(record: dict[str, str | Path]) -> str:
    target = str(record["relative_path"])
    if target.endswith(".md"):
        target = target[:-3]
    title = str(record["title"]).replace("|", "-")
    return f"[[{target}|{title}]]"


if __name__ == "__main__":
    raise SystemExit(main())
