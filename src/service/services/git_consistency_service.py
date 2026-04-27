from dataclasses import dataclass, field
from typing import Any

from service.repositories import code_change_link_repository
from service.repositories import doc_change_repository
from service.services import commit_message_parser


@dataclass(slots=True)
class GitConsistencyError(Exception):
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def verify_doc_change(
    conn,
    *,
    project_id: int,
    branch: str,
    commit_sha: str,
    commit_message: str,
) -> dict[str, Any]:
    normalized_branch = _required_text(branch, "branch")
    normalized_sha = _required_text(commit_sha, "commit_sha")
    if len(normalized_sha) > 40:
        raise GitConsistencyError(
            category="invalid_argument",
            message="commit_sha must be at most 40 characters",
            details={"commit_sha": normalized_sha},
        )

    try:
        parsed = commit_message_parser.parse_doc_change_id(commit_message)
    except commit_message_parser.CommitMessageParseError as exc:
        raise GitConsistencyError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc

    change = doc_change_repository.find_by_doc_change_id(conn, parsed["doc_change_id"])
    if not change:
        raise GitConsistencyError(
            category="not_found",
            message="doc change not found",
            details={"doc_change_id": parsed["doc_change_id"]},
        )
    if change.get("status") == "implemented":
        raise GitConsistencyError(
            category="conflict",
            message="doc change is already implemented",
            details={"doc_change_id": parsed["doc_change_id"], "status": "implemented"},
        )

    link = code_change_link_repository.create(
        conn,
        doc_change_id=change["id"],
        project_id=project_id,
        branch=normalized_branch,
        commit_sha=normalized_sha,
        commit_message=commit_message,
    )
    updated_change = doc_change_repository.mark_in_implementation(conn, change["id"])
    status = (updated_change or change).get("status")
    return {
        "status": "verified",
        "doc_change_id": parsed["doc_change_id"],
        "doc_change_pk": change["id"],
        "verification_status": "verified",
        "doc_change_status": status,
        "risk_level": "none",
        "next_status": "in_implementation",
        "dangerous_commit_required": False,
        "reason": None,
        "next_actions": ["continue implementation and keep DocChange-ID trailer in related commits"],
        "matched_by": parsed["matched_by"],
        "code_change_link": link,
    }


def _required_text(value: str | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise GitConsistencyError(
            category="invalid_argument",
            message=f"{field_name} is required",
            details={"field": field_name},
        )
    return text
