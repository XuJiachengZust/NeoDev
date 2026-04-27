"""Generate a NeoDev MVP controlled document and validate it immediately."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from validate_mvp_docs import validate_paths


TEMPLATE_PATH = Path(__file__).resolve().parent / "assets" / "templates" / "mvp-doc.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doc-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--doc-type", choices=["prd", "prototype", "tech-design"], required=True)
    parser.add_argument("--product-key", required=True)
    parser.add_argument("--status", default="draft", choices=["draft", "active", "deprecated"])
    parser.add_argument("--target", action="append", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    rendered = _render_template(
        doc_id=args.doc_id,
        title=args.title,
        doc_type=args.doc_type,
        product_key=args.product_key,
        status=args.status,
        targets=args.target,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")

    payload = validate_paths([args.output])
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


def _render_template(
    *,
    doc_id: str,
    title: str,
    doc_type: str,
    product_key: str,
    status: str,
    targets: list[str],
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    target_lines = "\n".join(f"    - {target}" for target in targets)
    related_lines = "\n".join(f'  - "[[{target}]]"' for target in targets)
    today = date.today().isoformat()
    return template.format(
        doc_id=doc_id,
        title=title,
        doc_type=doc_type,
        product_key=product_key,
        status=status,
        targets=target_lines,
        related=related_lines,
        created=today,
        updated=today,
    )


if __name__ == "__main__":
    raise SystemExit(main())
