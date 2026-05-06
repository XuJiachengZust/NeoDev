from dataclasses import dataclass, field
import re
from typing import Any


@dataclass(slots=True)
class CommitMessageParseError(Exception):
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def parse_doc_change_id(commit_message: str) -> dict[str, str]:
    lines = str(commit_message or "").splitlines()
    matches = []
    for line_no, line in enumerate(lines, start=1):
        key, separator, value = line.partition(":")
        if key.strip().lower() != "docchange-id" or not separator:
            continue
        doc_change_id = value.strip()
        if not doc_change_id:
            raise CommitMessageParseError(
                category="invalid_argument",
                message="DocChange-ID trailer value is required",
                details={"line": line_no},
            )
        if not re.fullmatch(r"[0-9a-fA-F]{40}", doc_change_id):
            raise CommitMessageParseError(
                category="invalid_argument",
                message="DocChange-ID must be a 40-character document commit hash",
                details={"line": line_no},
            )
        matches.append({"doc_change_id": doc_change_id, "line": line_no})

    if not matches:
        raise CommitMessageParseError(
            category="invalid_argument",
            message="DocChange-ID trailer is required",
        )
    if len(matches) > 1:
        raise CommitMessageParseError(
            category="invalid_argument",
            message="DocChange-ID trailer must be unique",
            details={"count": len(matches)},
        )
    return {"doc_change_id": matches[0]["doc_change_id"].lower(), "matched_by": "trailer"}
