from dataclasses import dataclass, field
from typing import Any

from service.repositories import branch_graph_repository
from service.services import branch_graph_neo4j_service
from service.services import neo4j_config_service
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
    graph = _require_ready_graph(conn, project_id, context["branch"])
    neo4j_config, neo4j_database = _load_neo4j_config(context["project"])
    neo4j_result = branch_graph_neo4j_service.entity_context(
        config=neo4j_config,
        database=neo4j_database,
        project_id=project_id,
        product_name=_product_name(context["product"]),
        version_name=context["version"].get("version_name") or context["version"].get("name"),
        project_name=context["project"].get("name"),
        branch_name=context["branch"],
        entity_id=entity_id,
        depth=depth,
    )
    return {
        "product_version_id": product_version_id,
        "project_id": project_id,
        "project_name": context["project"].get("name"),
        "branch": context["branch"],
        "snapshot_id": graph["id"],
        "head_commit": graph.get("head_commit"),
        "depth": depth,
        "entity": neo4j_result.get("entity"),
        "neighbors": neo4j_result.get("neighbors") or [],
        "edges": neo4j_result.get("edges") or [],
        "context_summary": neo4j_result.get("context_summary") or [],
        "degraded_reasons": [],
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
    graph = _require_ready_graph(conn, project_id, context["branch"])
    neo4j_config, neo4j_database = _load_neo4j_config(context["project"])
    neo4j_result = branch_graph_neo4j_service.get_chain(
        config=neo4j_config,
        database=neo4j_database,
        project_id=project_id,
        product_name=_product_name(context["product"]),
        version_name=context["version"].get("version_name") or context["version"].get("name"),
        project_name=context["project"].get("name"),
        branch_name=context["branch"],
        locator=locator,
        depth=depth,
    )
    return {
        "start_node": neo4j_result.get("start_node"),
        "snapshot_id": graph["id"],
        "branch": context["branch"],
        "head_commit": graph.get("head_commit"),
        "depth": depth,
        "nodes": neo4j_result.get("nodes") or [],
        "edges": neo4j_result.get("edges") or [],
        "path_summary": neo4j_result.get("path_summary") or [],
        "affected_commits": [],
        "degraded_reasons": [],
    }


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


def _require_ready_graph(conn, project_id: int, branch: str) -> dict[str, Any]:
    graph = branch_graph_repository.get_by_project_branch(conn, project_id, branch)
    if not graph:
        raise GraphQueryError(
            category="not_found",
            message="branch graph not found",
            details={"project_id": project_id, "branch": branch},
        )
    if graph.get("status") != "ready":
        raise GraphQueryError(
            category="not_ready",
            message="branch graph is not ready",
            details={"project_id": project_id, "branch": branch, "status": graph.get("status")},
        )
    return graph


def _load_neo4j_config(project: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    neo4j_config, neo4j_database = neo4j_config_service.load_neo4j_config(project)
    if not neo4j_config:
        raise GraphQueryError(
            category="invalid_config",
            message="Neo4j is not configured",
            details={"project_id": project.get("id")},
        )
    return neo4j_config, neo4j_database


def _product_name(product: dict[str, Any]) -> str | None:
    return product.get("name") or product.get("code")
