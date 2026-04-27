from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from service.services import graph_query_service
from service.services.ai_preprocessor_service import _load_neo4j_config


@dataclass(slots=True)
class GraphRefreshError(Exception):
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def refresh_nodes(
    conn,
    *,
    product_version_id: int,
    project_id: int,
    branch: str,
    node_ids: list[str] | None = None,
    paths: list[str] | None = None,
    commit_sha: str | None = None,
) -> dict[str, Any]:
    normalized_node_ids = _normalize_many(node_ids, "node_id")
    normalized_paths = _normalize_many(paths, "path")
    normalized_commit_sha = _normalize_one(commit_sha, "commit_sha")

    try:
        context = graph_query_service._validate_scope(conn, product_version_id, project_id, branch)
    except graph_query_service.GraphQueryError as exc:
        raise GraphRefreshError(
            category=exc.category,
            message=exc.message,
            details=exc.details,
        ) from exc

    scope = {
        "product_version_id": product_version_id,
        "project_id": project_id,
        "branch": context["branch"],
        "node_ids": normalized_node_ids,
        "paths": normalized_paths,
        "commit_sha": normalized_commit_sha,
    }

    driver, database, degraded_reason = _open_driver(context)
    if degraded_reason:
        return _result(
            project_id=project_id,
            project_name=context["project"].get("name"),
            branch=context["branch"],
            scope=scope,
            updated_count=0,
            status="degraded",
            semantic_status="not_refreshed",
            degraded_reasons=[degraded_reason],
        )

    try:
        updated_count = _mark_refresh_requested(
            driver,
            database,
            project_id=project_id,
            branch=context["branch"],
            scope=scope,
        )
    finally:
        driver.close()

    return _result(
        project_id=project_id,
        project_name=context["project"].get("name"),
        branch=context["branch"],
        scope=scope,
        updated_count=updated_count,
        status="completed",
        semantic_status="refresh_requested",
        degraded_reasons=[],
    )


def _open_driver(context: dict[str, Any]):
    neo4j_config, database = _load_neo4j_config(context["project"])
    if not neo4j_config or not neo4j_config.get("neo4j_uri"):
        return None, None, {
            "project_id": context["project"]["id"],
            "branch": context["branch"],
            "reason": "neo4j_not_configured",
        }
    return _create_neo4j_driver(neo4j_config), database, None


def _create_neo4j_driver(neo4j_config: dict):
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        neo4j_config["neo4j_uri"],
        auth=(
            neo4j_config.get("neo4j_user") or "neo4j",
            neo4j_config.get("neo4j_password") or "",
        ),
    )


def _mark_refresh_requested(
    driver,
    database: str | None,
    *,
    project_id: int,
    branch: str,
    scope: dict[str, Any],
) -> int:
    query = """
    MATCH (n)
    WHERE n.branch = $branch
      AND n.project_id = $project_id
      AND (
        $whole_branch = true
        OR ($has_node_ids = true AND n.id IN $node_ids)
        OR ($has_paths = true AND (n.file_path IN $paths OR n.path IN $paths))
        OR ($has_commit = true AND (
          n.commit_sha = $commit_sha
          OR n.commit = $commit_sha
          OR $commit_sha IN coalesce(n.commits, [])
        ))
      )
    SET n.semanticStatus = 'refresh_requested',
        n.refreshRequestedAt = $refresh_requested_at
    RETURN count(n) AS updated_count
    """
    params = {
        "project_id": project_id,
        "branch": branch,
        "node_ids": scope["node_ids"],
        "paths": scope["paths"],
        "commit_sha": scope["commit_sha"],
        "has_node_ids": bool(scope["node_ids"]),
        "has_paths": bool(scope["paths"]),
        "has_commit": bool(scope["commit_sha"]),
        "whole_branch": not (scope["node_ids"] or scope["paths"] or scope["commit_sha"]),
        "refresh_requested_at": datetime.now(timezone.utc).isoformat(),
    }
    with driver.session(database=database) as session:
        records = list(session.run(query, **params))
    if not records:
        return 0
    return int(records[0].get("updated_count") or 0)


def _result(
    *,
    project_id: int,
    project_name: str | None,
    branch: str,
    scope: dict[str, Any],
    updated_count: int,
    status: str,
    semantic_status: str,
    degraded_reasons: list[dict],
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "project_name": project_name,
        "branch": branch,
        "refresh_scope": scope,
        "graph_nodes_updated": updated_count,
        "ai_descriptions_updated": 0,
        "embeddings_reused": 0,
        "embeddings_regenerated": 0,
        "status": status,
        "semantic_status": semantic_status,
        "degraded_reasons": degraded_reasons,
    }


def _normalize_many(values: list[str] | None, field_name: str) -> list[str]:
    normalized = []
    seen = set()
    for value in values or []:
        text = _normalize_one(value, field_name)
        if text is None:
            continue
        if text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalize_one(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise GraphRefreshError(
            category="invalid_argument",
            message=f"{field_name} must not be blank",
            details={"field": field_name},
        )
    return text
