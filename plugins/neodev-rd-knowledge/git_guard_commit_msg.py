"""Git commit-msg hook guard for NeoDev DocChange trailers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import check_docchange_trailer
import check_git_commit_scope


def check_commit_message(message_file: Path) -> dict[str, Any]:
    classification = check_git_commit_scope.classify_paths(check_git_commit_scope._staged_paths())
    scope = classification["scope"]
    if scope == "document":
        return {
            "ok": True,
            "scope": scope,
            "checked_count": 0,
            "skipped": "document-only commit",
            "errors": [],
        }
    if scope == "empty":
        return {
            "ok": True,
            "scope": scope,
            "checked_count": 0,
            "skipped": "no staged changes",
            "errors": [],
        }
    if scope == "mixed":
        return {
            "ok": False,
            "scope": scope,
            "checked_count": 0,
            "errors": [
                {
                    "field": "scope",
                    "message": "NeoDev commit scope is mixed. Split document and code changes.",
                }
            ],
            "classification": classification,
        }

    payload = check_docchange_trailer.validate_message(message_file.read_text(encoding="utf-8"))
    payload["scope"] = scope
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("message_file", type=Path)
    args = parser.parse_args(argv)
    payload = check_commit_message(args.message_file)
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
