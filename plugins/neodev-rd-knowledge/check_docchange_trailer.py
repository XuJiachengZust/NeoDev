"""Validate that a commit message has exactly one valid DocChange-ID trailer."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


DOC_CHANGE_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


def validate_message(message: str) -> dict[str, Any]:
    matches = []
    for line_no, line in enumerate(str(message or "").splitlines(), start=1):
        key, separator, value = line.partition(":")
        if key.strip().lower() != "docchange-id" or not separator:
            continue
        matches.append({"line": line_no, "value": value.strip()})

    errors: list[dict[str, Any]] = []
    if not matches:
        errors.append({"field": "DocChange-ID", "message": "DocChange-ID trailer is required"})
    elif len(matches) > 1:
        errors.append(
            {
                "field": "DocChange-ID",
                "message": "DocChange-ID trailer must be unique",
                "count": len(matches),
            }
        )
    else:
        doc_change_id = matches[0]["value"]
        if not DOC_CHANGE_ID_PATTERN.match(doc_change_id):
            errors.append(
                {
                    "field": "DocChange-ID",
                    "message": "DocChange-ID must be a 40-character document commit hash",
                    "line": matches[0]["line"],
                }
            )

    payload: dict[str, Any] = {"ok": not errors, "checked_count": 1, "errors": errors}
    if not errors:
        payload["doc_change_id"] = matches[0]["value"]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--message")
    source.add_argument("--message-file", type=Path)
    parser.add_argument(
        "--skip-document-only",
        action="store_true",
        help="Skip DocChange-ID validation when staged changes contain only controlled documents.",
    )
    args = parser.parse_args()

    if args.skip_document_only and _staged_scope() == "document":
        print(json.dumps({"ok": True, "checked_count": 0, "skipped": "document-only commit"}, ensure_ascii=False))
        return 0

    message = args.message
    if args.message_file:
        message = args.message_file.read_text(encoding="utf-8")

    payload = validate_message(message)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload["ok"] else 1


def _staged_scope() -> str:
    proc = subprocess.run(
        ["python", "plugins/neodev-rd-knowledge/check_git_commit_scope.py"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode not in (0, 1):
        return "unknown"
    try:
        return json.loads(proc.stdout).get("scope") or "unknown"
    except json.JSONDecodeError:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
