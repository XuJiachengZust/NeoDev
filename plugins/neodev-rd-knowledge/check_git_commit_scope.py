"""Classify staged Git changes for NeoDev commit workflow routing."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import PurePosixPath


DOC_EXTENSIONS = {".md", ".markdown", ".mdx", ".doc", ".docx"}
DOC_ROOTS = {"docs"}
WORKFLOW_DOC_ROOTS = {"docs/neosuperpower", "docs/requirements", "docs/prd", "docs/prototype", "docs/tech-design"}


def main() -> int:
    paths = _staged_paths()
    classification = classify_paths(paths)
    print(json.dumps(classification, ensure_ascii=False))
    if classification["scope"] == "mixed":
        print(
            "NeoDev commit scope is mixed. Split document and code changes so each commit can run the correct workflow.",
            file=sys.stderr,
        )
        return 1
    return 0


def classify_paths(paths: list[str]) -> dict:
    doc_paths = [path for path in paths if _is_document_path(path)]
    code_paths = [path for path in paths if not _is_document_path(path)]
    if doc_paths and code_paths:
        scope = "mixed"
        required_workflow = "split-commit"
    elif doc_paths:
        scope = "document"
        required_workflow = "doc binding list -> doc import -> doc change register"
    elif code_paths:
        scope = "code"
        required_workflow = "verify DocChange-ID -> git verify-doc-change -> project refresh-graph after push"
    else:
        scope = "empty"
        required_workflow = "no staged changes"
    return {
        "ok": scope != "mixed",
        "scope": scope,
        "required_workflow": required_workflow,
        "documents": doc_paths,
        "code": code_paths,
    }


def _staged_paths() -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        print(proc.stderr, file=sys.stderr)
        sys.exit(proc.returncode)
    return [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]


def _is_document_path(path: str) -> bool:
    normalized = path.strip().replace("\\", "/")
    if not normalized:
        return False
    lower = normalized.lower()
    parts = PurePosixPath(lower).parts
    if parts and parts[0] in DOC_ROOTS and PurePosixPath(lower).suffix in DOC_EXTENSIONS:
        return True
    return any(lower == root or lower.startswith(f"{root}/") for root in WORKFLOW_DOC_ROOTS)


if __name__ == "__main__":
    raise SystemExit(main())
