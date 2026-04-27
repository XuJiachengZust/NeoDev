from dataclasses import dataclass, field
from typing import Any

from service.repositories import code_change_link_repository
from service.repositories import dangerous_commit_repository
from service.repositories import doc_change_repository
from service.repositories import product_version_repository
from service.services import graph_refresh_service
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


def post_push_refresh(
    conn,
    *,
    project_id: int,
    branch: str,
    version_id: int | None = None,
    commit_sha: str | None = None,
) -> dict[str, Any]:
    normalized_branch = _required_text(branch, "branch")
    normalized_commit_sha = _optional_text(commit_sha, "commit_sha")
    if normalized_commit_sha and len(normalized_commit_sha) > 40:
        raise GitConsistencyError(
            category="invalid_argument",
            message="commit_sha must be at most 40 characters",
            details={"commit_sha": normalized_commit_sha},
        )

    product_version_id = _resolve_bound_product_version(
        conn,
        project_id=project_id,
        branch=normalized_branch,
        version_id=version_id,
    )
    refresh = graph_refresh_service.refresh_nodes(
        conn,
        product_version_id=product_version_id,
        project_id=project_id,
        branch=normalized_branch,
        commit_sha=normalized_commit_sha,
    )
    return {
        "project_id": project_id,
        "branch": normalized_branch,
        "product_version_id": product_version_id,
        "commits_synced": 0,
        "graph_nodes_updated": refresh.get("graph_nodes_updated", 0),
        "chains_updated": 0,
        "ai_descriptions_updated": refresh.get("ai_descriptions_updated", 0),
        "embeddings_reused": refresh.get("embeddings_reused", 0),
        "embeddings_regenerated": refresh.get("embeddings_regenerated", 0),
        "refresh_scope": refresh.get("refresh_scope", {}),
        "status": refresh.get("status"),
        "semantic_status": refresh.get("semantic_status"),
        "degraded_reasons": refresh.get("degraded_reasons", []),
    }


def _resolve_bound_product_version(
    conn,
    *,
    project_id: int,
    branch: str,
    version_id: int | None = None,
) -> int:
    if version_id is not None:
        version = product_version_repository.find_by_id(conn, version_id)
        if not version:
            raise GitConsistencyError(
                category="not_found",
                message="product version not found",
                details={"version_id": version_id},
            )
        mappings = product_version_repository.list_branches(conn, version_id)
        match = next(
            (row for row in mappings if row["project_id"] == project_id and row["branch"] == branch),
            None,
        )
        if not match:
            raise GitConsistencyError(
                category="invalid_scope",
                message="project branch is not bound to this product version",
                details={"version_id": version_id, "project_id": project_id, "branch": branch},
            )
        return version_id

    matches = _find_product_version_branches(conn, project_id, branch)
    if not matches:
        raise GitConsistencyError(
            category="not_found",
            message="no product version is bound to this project branch",
            details={"project_id": project_id, "branch": branch},
        )
    if len(matches) > 1:
        raise GitConsistencyError(
            category="conflict",
            message="project branch is bound to multiple product versions",
            details={
                "project_id": project_id,
                "branch": branch,
                "product_version_ids": [row["product_version_id"] for row in matches],
            },
        )
    return int(matches[0]["product_version_id"])


def _find_product_version_branches(conn, project_id: int, branch: str) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT product_version_id, project_id, branch
            FROM product_version_branches
            WHERE project_id = %s AND branch = %s
            ORDER BY product_version_id
            """,
            (project_id, branch),
        )
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]


def _required_text(value: str | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise GitConsistencyError(
            category="invalid_argument",
            message=f"{field_name} is required",
            details={"field": field_name},
        )
    return text


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)
