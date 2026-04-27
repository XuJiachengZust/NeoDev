from dataclasses import dataclass
from typing import Any

from service.repositories import project_repository as project_repo
from service.services import llm_client
from service.services import product_version_service
from service.services import project_service
from service.services.ai_preprocessor_service import _load_neo4j_config


@dataclass
class GraphSemanticSearchError(Exception):
    category: str
    message: str
    details: dict | None = None


def semantic_search(
    conn,
    *,
    product_version_id: int,
    query: str,
    top_k: int = 5,
) -> dict[str, Any]:
    query = (query or "").strip()
    if not query:
        raise GraphSemanticSearchError(
            category="invalid_argument",
            message="query is required",
        )
    if top_k < 1 or top_k > 50:
        raise GraphSemanticSearchError(
            category="invalid_argument",
            message="top_k must be between 1 and 50",
            details={"top_k": top_k},
        )

    version = product_version_service.get_version(conn, product_version_id)
    if not version:
        raise GraphSemanticSearchError(
            category="not_found",
            message="product version not found",
            details={"product_version_id": product_version_id},
        )

    bindings = product_version_service.list_branches(conn, product_version_id)
    scope = [_scope_item(binding) for binding in bindings]
    if not scope:
        raise GraphSemanticSearchError(
            category="invalid_scope",
            message="product version has no bound branches",
            details={"product_version_id": product_version_id},
        )

    query_embedding, embedding_error = _embed_query(query)
    results: list[dict[str, Any]] = []
    degraded_reasons: list[dict[str, Any]] = []

    for binding in bindings:
        branch = (binding.get("branch") or "").strip()
        project_id = int(binding["project_id"])
        project = project_service.get_project(conn, project_id) or project_repo.find_by_id(conn, project_id)
        if not project or not branch:
            degraded_reasons.append(
                {
                    "project_id": project_id,
                    "branch": branch,
                    "reason": "project_or_branch_missing",
                }
            )
            continue

        neo4j_config, database = _load_neo4j_config(project)
        if not neo4j_config or not neo4j_config.get("neo4j_uri"):
            degraded_reasons.append(
                {
                    "project_id": project_id,
                    "branch": branch,
                    "reason": "neo4j_not_configured",
                }
            )
            continue

        driver = _create_neo4j_driver(neo4j_config)
        try:
            branch_results = _search_branch(
                driver,
                database,
                product_version_id=product_version_id,
                project_id=project_id,
                project_name=str(binding.get("project_name") or project.get("name") or ""),
                branch=branch,
                query=query,
                query_embedding=query_embedding,
                limit=top_k,
            )
            results.extend(branch_results)
        except Exception as exc:  # noqa: BLE001
            degraded_reasons.append(
                {
                    "project_id": project_id,
                    "branch": branch,
                    "reason": "neo4j_query_failed",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
        finally:
            driver.close()

    results.sort(key=lambda row: float(row.get("score") or 0), reverse=True)
    results = results[:top_k]
    semantic_status = _overall_status(
        results=results,
        query_embedding=query_embedding,
        embedding_error=embedding_error,
        degraded_reasons=degraded_reasons,
    )
    return {
        "product_version_id": product_version_id,
        "query": query,
        "top_k": top_k,
        "scope": scope,
        "semantic_status": semantic_status,
        "results": results,
        "degraded_reasons": degraded_reasons,
    }


def _scope_item(binding: dict) -> dict[str, Any]:
    return {
        "project_id": int(binding["project_id"]),
        "project_name": binding.get("project_name"),
        "branch": binding.get("branch"),
    }


def _embed_query(query: str) -> tuple[list[float] | None, str | None]:
    try:
        return llm_client.embedding_completion(query), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _create_neo4j_driver(neo4j_config: dict):
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        neo4j_config["neo4j_uri"],
        auth=(
            neo4j_config.get("neo4j_user") or "neo4j",
            neo4j_config.get("neo4j_password") or "",
        ),
    )


def _search_branch(
    driver,
    database: str | None,
    *,
    product_version_id: int,
    project_id: int,
    project_name: str,
    branch: str,
    query: str,
    query_embedding: list[float] | None,
    limit: int,
) -> list[dict[str, Any]]:
    with driver.session(database=database) as session:
        if query_embedding:
            records = session.run(
                _VECTOR_SEARCH_QUERY,
                project_id=project_id,
                branch=branch,
                embedding=query_embedding,
                limit=limit,
            )
        else:
            records = session.run(
                _TEXT_SEARCH_QUERY,
                project_id=project_id,
                branch=branch,
                needle=query.lower(),
                limit=limit,
            )
        return [
            _format_record(
                record,
                product_version_id=product_version_id,
                project_id=project_id,
                project_name=project_name,
                branch=branch,
            )
            for record in records
        ]


_VECTOR_SEARCH_QUERY = """
MATCH (n)
WHERE n.branch = $branch
  AND n.project_id = $project_id
  AND n.embedding IS NOT NULL
WITH n, vector.similarity.cosine(n.embedding, $embedding) AS score
RETURN n.id AS entity_id,
       labels(n)[0] AS entity_type,
       n.name AS name,
       coalesce(n.file_path, n.filePath, n.path, n.relative_path) AS file_path,
       n.description AS description,
       score AS score,
       CASE
         WHEN n.description IS NULL OR n.description = '' THEN 'not_vectorized'
         ELSE 'vectorized'
       END AS semantic_status
ORDER BY score DESC
LIMIT $limit
"""


_TEXT_SEARCH_QUERY = """
MATCH (n)
WHERE n.branch = $branch
  AND n.project_id = $project_id
  AND (
    toLower(coalesce(n.name, '')) CONTAINS $needle
    OR toLower(coalesce(n.description, '')) CONTAINS $needle
    OR toLower(coalesce(n.file_path, n.filePath, n.path, n.relative_path, '')) CONTAINS $needle
  )
RETURN n.id AS entity_id,
       labels(n)[0] AS entity_type,
       n.name AS name,
       coalesce(n.file_path, n.filePath, n.path, n.relative_path) AS file_path,
       n.description AS description,
       CASE
         WHEN toLower(coalesce(n.name, '')) CONTAINS $needle THEN 0.6
         WHEN toLower(coalesce(n.description, '')) CONTAINS $needle THEN 0.4
         ELSE 0.2
       END AS score,
       CASE
         WHEN n.description IS NULL OR n.description = '' THEN 'not_vectorized'
         ELSE 'degraded'
       END AS semantic_status
ORDER BY score DESC, n.name
LIMIT $limit
"""


def _format_record(
    record,
    *,
    product_version_id: int,
    project_id: int,
    project_name: str,
    branch: str,
) -> dict[str, Any]:
    return {
        "product_version_id": product_version_id,
        "project_id": project_id,
        "project_name": project_name,
        "branch": branch,
        "entity_type": record.get("entity_type"),
        "entity_id": record.get("entity_id"),
        "file_path": record.get("file_path"),
        "description": record.get("description") or "",
        "score": float(record.get("score") or 0),
        "semantic_status": record.get("semantic_status") or "not_vectorized",
    }


def _overall_status(
    *,
    results: list[dict[str, Any]],
    query_embedding: list[float] | None,
    embedding_error: str | None,
    degraded_reasons: list[dict[str, Any]],
) -> str:
    if results:
        statuses = {str(row.get("semantic_status") or "") for row in results}
        if "vectorized" in statuses and query_embedding:
            return "vectorized"
        if "degraded" in statuses:
            return "degraded"
        return "not_vectorized"
    if embedding_error:
        return "not_vectorized"
    if degraded_reasons:
        return "not_configured"
    return "empty"
