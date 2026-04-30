from dataclasses import dataclass, field
from typing import Any

from service.services import product_service
from service.services import product_version_service
from service.services import project_service


@dataclass(slots=True)
class GraphQueryError(Exception):
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def entity_context(
    conn,
    *,
    product_version_id: int,
    project_id: int,
    branch: str,
    entity_id: str,
    depth: int = 1,
) -> dict[str, Any]:
    entity_id = (entity_id or "").strip()
    if not entity_id:
        raise GraphQueryError(category="invalid_argument", message="entity_id is required")
    depth = _validate_depth(depth, max_depth=3)
    context = _validate_scope(conn, product_version_id, project_id, branch)
    return {
        "product_version_id": product_version_id,
        "project_id": project_id,
        "project_name": context["project"].get("name"),
        "branch": context["branch"],
        "depth": depth,
        "entity": None,
        "neighbors": [],
        "edges": [],
        "context_summary": [],
        "degraded_reasons": [_code_storage_removed_reason(project_id, context["branch"])],
    }


def get_chain(
    conn,
    *,
    product_version_id: int,
    project_id: int,
    branch: str,
    start_node: str | None = None,
    file_path: str | None = None,
    symbol: str | None = None,
    commit_sha: str | None = None,
    depth: int = 1,
) -> dict[str, Any]:
    depth = _validate_depth(depth, max_depth=5)
    locator = _validate_chain_locator(
        start_node=start_node,
        file_path=file_path,
        symbol=symbol,
        commit_sha=commit_sha,
    )
    context = _validate_scope(conn, product_version_id, project_id, branch)
    return _empty_chain(
        branch=context["branch"],
        depth=depth,
        snapshot_id=None,
        head_commit=None,
        degraded_reason=_code_storage_removed_reason(project_id, context["branch"]),
    )


def _validate_scope(conn, product_version_id: int, project_id: int, branch: str) -> dict[str, Any]:
    normalized_branch = (branch or "").strip()
    if not normalized_branch:
        raise GraphQueryError(category="invalid_argument", message="branch is required")

    version = product_version_service.get_version(conn, product_version_id)
    if not version:
        raise GraphQueryError(
            category="not_found",
            message="product version not found",
            details={"product_version_id": product_version_id},
        )
    product = product_service.get_product(conn, version["product_id"])
    if not product:
        raise GraphQueryError(
            category="not_found",
            message="product not found",
            details={"product_id": version["product_id"]},
        )

    project = project_service.get_project(conn, project_id)
    if not project:
        raise GraphQueryError(
            category="not_found",
            message="project not found",
            details={"project_id": project_id},
        )

    branches = product_version_service.list_branches(conn, product_version_id)
    mapping = next((row for row in branches if row["project_id"] == project_id), None)
    if not mapping:
        raise GraphQueryError(
            category="invalid_scope",
            message="project is not bound to this product version",
            details={"product_version_id": product_version_id, "project_id": project_id},
        )
    expected_branch = mapping.get("branch_name") or mapping.get("branch")
    if expected_branch != normalized_branch:
        raise GraphQueryError(
            category="invalid_scope",
            message="branch is not bound to this product version project mapping",
            details={
                "product_version_id": product_version_id,
                "project_id": project_id,
                "expected_branch": expected_branch,
                "actual_branch": normalized_branch,
            },
        )
    return {
        "product": product,
        "version": version,
        "project": project,
        "branch_mapping": mapping,
        "branch": normalized_branch,
    }


def _validate_depth(depth: int, *, max_depth: int) -> int:
    try:
        value = int(depth)
    except (TypeError, ValueError) as exc:
        raise GraphQueryError(
            category="invalid_argument",
            message="depth must be an integer",
            details={"depth": depth},
        ) from exc
    if value < 1 or value > max_depth:
        raise GraphQueryError(
            category="invalid_argument",
            message=f"depth must be between 1 and {max_depth}",
            details={"depth": depth},
        )
    return value


def _validate_chain_locator(
    *,
    start_node: str | None,
    file_path: str | None,
    symbol: str | None,
    commit_sha: str | None,
) -> dict[str, str]:
    candidates = {
        "start_node": (start_node or "").strip(),
        "file_path": (file_path or "").strip(),
        "symbol": (symbol or "").strip(),
        "commit_sha": (commit_sha or "").strip(),
    }
    provided = {key: value for key, value in candidates.items() if value}
    if len(provided) != 1:
        raise GraphQueryError(
            category="invalid_argument",
            message="provide exactly one chain start locator",
            details={"provided": sorted(provided)},
        )
    key, value = next(iter(provided.items()))
    return {"type": key, "value": value}


def _code_storage_removed_reason(project_id: int, branch: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "branch": branch,
        "reason": "code_node_storage_removed",
    }


def _empty_chain(
    *,
    branch: str,
    depth: int,
    snapshot_id: int | None,
    head_commit: str | None,
    degraded_reason: dict[str, Any],
) -> dict[str, Any]:
    return {
        "start_node": None,
        "snapshot_id": snapshot_id,
        "branch": branch,
        "head_commit": head_commit,
        "depth": depth,
        "nodes": [],
        "edges": [],
        "path_summary": [],
        "affected_commits": [],
        "degraded_reasons": [degraded_reason],
    }
