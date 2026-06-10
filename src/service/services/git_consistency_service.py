from dataclasses import dataclass, field
from typing import Any

from service.repositories import code_change_link_repository
from service.repositories import dangerous_commit_repository
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
        _raise_dangerous_commit(
            conn,
            project_id=project_id,
            branch=normalized_branch,
            commit_sha=normalized_sha,
            category=exc.category,
            message=exc.message,
            details=exc.details,
            commit_message=commit_message,
        )

    change = doc_change_repository.find_by_doc_change_id(conn, parsed["doc_change_id"])
    if not change:
        _raise_dangerous_commit(
            conn,
            project_id=project_id,
            branch=normalized_branch,
            commit_sha=normalized_sha,
            category="not_found",
            message="doc change not found",
            details={"doc_change_id": parsed["doc_change_id"]},
            commit_message=commit_message,
        )
    if change.get("status") == "implemented":
        _raise_dangerous_commit(
            conn,
            project_id=project_id,
            branch=normalized_branch,
            commit_sha=normalized_sha,
            category="conflict",
            message="doc change is already implemented",
            details={"doc_change_id": parsed["doc_change_id"], "status": "implemented"},
            commit_message=commit_message,
        )

    link = _ensure_code_change_link(
        conn,
        doc_change_id=int(change["id"]),
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


def _ensure_code_change_link(
    conn,
    *,
    doc_change_id: int,
    project_id: int,
    branch: str,
    commit_sha: str,
    commit_message: str,
) -> dict:
    existing_links = code_change_link_repository.list_by_commit(
        conn,
        project_id=project_id,
        branch=branch,
        commit_sha=commit_sha,
    )
    for link in existing_links:
        if int(link.get("doc_change_id") or 0) == doc_change_id:
            return link
    if existing_links:
        raise GitConsistencyError(
            category="conflict",
            message="commit is already linked to another doc change",
            details={
                "project_id": project_id,
                "branch": branch,
                "commit_sha": commit_sha,
                "existing_doc_change_id": existing_links[0].get("doc_change_id"),
                "doc_change_id": doc_change_id,
            },
        )
    return code_change_link_repository.create(
        conn,
        doc_change_id=doc_change_id,
        project_id=project_id,
        branch=branch,
        commit_sha=commit_sha,
        commit_message=commit_message,
    )


def list_dangerous_commits(conn, *, project_id: int | None = None) -> dict[str, Any]:
    rows = dangerous_commit_repository.list_open(conn, project_id=project_id)
    return {"dangerous_commits": rows, "count": len(rows)}


def resolve_dangerous_commit(
    conn,
    *,
    record_id: int,
    resolved_by: str,
) -> dict[str, Any]:
    resolver = _required_text(resolved_by, "resolved_by")
    resolved = dangerous_commit_repository.resolve(
        conn,
        record_id=record_id,
        resolved_by=resolver,
    )
    if not resolved:
        raise GitConsistencyError(
            category="not_found",
            message="dangerous commit record not found",
            details={"record_id": record_id},
        )
    return {"dangerous_commit": resolved}


def _required_text(value: str | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise GitConsistencyError(
            category="invalid_argument",
            message=f"{field_name} is required",
            details={"field": field_name},
        )
    return text


def _raise_dangerous_commit(
    conn,
    *,
    project_id: int,
    branch: str,
    commit_sha: str,
    category: str,
    message: str,
    details: dict[str, Any],
    commit_message: str,
) -> None:
    dangerous = _ensure_dangerous_commit(
        conn,
        project_id=project_id,
        branch=branch,
        commit_sha=commit_sha,
        reason=message,
        category=category,
        details=details,
        commit_message=commit_message,
    )
    raise GitConsistencyError(
        category=category,
        message=message,
        details={
            **details,
            "dangerous_commit": dangerous,
            "dangerous_commit_required": True,
            "risk_level": "high",
        },
    )


def _ensure_dangerous_commit(
    conn,
    *,
    project_id: int,
    branch: str,
    commit_sha: str,
    reason: str,
    category: str,
    details: dict[str, Any],
    commit_message: str,
) -> dict:
    existing = dangerous_commit_repository.find_open_by_identity(
        conn,
        project_id=project_id,
        branch=branch,
        commit_sha=commit_sha,
    )
    if existing:
        return existing
    return dangerous_commit_repository.create(
        conn,
        project_id=project_id,
        branch=branch,
        commit_sha=commit_sha,
        risk_level="high",
        reason=reason,
        extra_json={
            "category": category,
            "details": details,
            "commit_message": commit_message,
        },
    )
