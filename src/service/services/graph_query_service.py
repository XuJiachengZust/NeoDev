from dataclasses import dataclass, field
from typing import Any

from service.repositories import version_repository as version_repo
from service.services import product_service
from service.services import product_version_service
from service.services import project_service
from service.services.neo4j_config_service import load_neo4j_config


@dataclass(slots=True)
class GraphQueryError(Exception):
    category: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        Exception.__init__(self, self.message)


def _branch_snapshot_service():
    patched = globals().get("branch_snapshot_service")
    if patched is not None:
        return patched
    from service.services import branch_snapshot_service as service

    return service


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
    current_snapshot, visible_file_ids = _load_visible_file_ids(conn, project_id, context["branch"])
    if not visible_file_ids:
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
            "degraded_reasons": [
                {
                    "project_id": project_id,
                    "branch": context["branch"],
                    "reason": "branch_snapshot_not_available",
                }
            ],
        }
    driver, database, degraded_reason = _open_driver(context)
    if degraded_reason:
        return {
            "product_version_id": product_version_id,
            "project_id": project_id,
            "project_name": context["project"].get("name"),
            "branch": context["branch"],
            "snapshot_id": current_snapshot.get("id") if current_snapshot else None,
            "depth": depth,
            "entity": None,
            "neighbors": [],
            "edges": [],
            "context_summary": [],
            "degraded_reasons": [degraded_reason],
        }

    try:
        source, neighbors, edges = _load_entity_context(
            driver,
            database,
            project_id=project_id,
            branch=context["branch"],
            entity_id=entity_id,
            depth=depth,
            visible_file_ids=visible_file_ids,
        )
    finally:
        driver.close()

    if source is None:
        raise GraphQueryError(
            category="not_found",
            message="entity not found",
            details={"entity_id": entity_id, "project_id": project_id, "branch": context["branch"]},
        )
    return {
        "product_version_id": product_version_id,
        "project_id": project_id,
        "project_name": context["project"].get("name"),
        "branch": context["branch"],
        "depth": depth,
        "entity": source,
        "neighbors": neighbors,
        "edges": edges,
        "context_summary": _summarize_edges(edges),
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
    current_snapshot, visible_file_ids = _load_visible_file_ids(conn, project_id, context["branch"])
    current_snapshot = current_snapshot or {}
    version = version_repo.find_by_project_and_branch(conn, project_id, context["branch"])
    head_commit = current_snapshot.get("head_commit") or (version or {}).get("last_parsed_commit")
    if not visible_file_ids:
        return _empty_chain(
            branch=context["branch"],
            depth=depth,
            snapshot_id=current_snapshot.get("id"),
            head_commit=head_commit,
            degraded_reason={
                "project_id": project_id,
                "branch": context["branch"],
                "reason": "branch_snapshot_not_available",
            },
        )
    driver, database, degraded_reason = _open_driver(context)
    if degraded_reason:
        return _empty_chain(
            branch=context["branch"],
            depth=depth,
            snapshot_id=current_snapshot.get("id"),
            head_commit=head_commit,
            degraded_reason=degraded_reason,
        )

    try:
        chain = _load_chain(
            driver,
            database,
            project_id=project_id,
            branch=context["branch"],
            locator=locator,
            depth=depth,
            visible_file_ids=visible_file_ids,
        )
    finally:
        driver.close()

    if chain["start_node"] is None:
        raise GraphQueryError(
            category="not_found",
            message="start node not found",
            details={"project_id": project_id, "branch": context["branch"], "locator": locator},
        )
    return {
        "start_node": chain["start_node"],
        "snapshot_id": current_snapshot.get("id"),
        "branch": context["branch"],
        "head_commit": head_commit,
        "depth": depth,
        "nodes": chain["nodes"],
        "edges": chain["edges"],
        "path_summary": _summarize_edges(chain["edges"]),
        "affected_commits": chain["affected_commits"],
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
    if mapping["branch"] != normalized_branch:
        raise GraphQueryError(
            category="invalid_scope",
            message="branch is not bound to this product version project mapping",
            details={
                "product_version_id": product_version_id,
                "project_id": project_id,
                "expected_branch": mapping["branch"],
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


def _open_driver(context: dict[str, Any]):
    neo4j_config, database = load_neo4j_config(context["project"])
    if not neo4j_config or not neo4j_config.get("neo4j_uri"):
        return None, None, {
            "project_id": context["project"]["id"],
            "branch": context["branch"],
            "reason": "neo4j_not_configured",
        }
    return _create_neo4j_driver(neo4j_config), database, None


def _load_visible_file_ids(conn, project_id: int, branch: str) -> tuple[dict[str, Any] | None, list[str]]:
    current_snapshot = _branch_snapshot_service().get_current_snapshot(conn, project_id, branch)
    if not current_snapshot:
        return None, []
    entries = _branch_snapshot_service().list_entries(conn, current_snapshot["id"])
    return current_snapshot, [
        entry["file_node_id"]
        for entry in entries
        if entry.get("file_node_id")
    ]


def _create_neo4j_driver(neo4j_config: dict):
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        neo4j_config["neo4j_uri"],
        auth=(
            neo4j_config.get("neo4j_user") or "neo4j",
            neo4j_config.get("neo4j_password") or "",
        ),
    )


def _load_entity_context(
    driver,
    database: str | None,
    *,
    project_id: int,
    branch: str,
    entity_id: str,
    depth: int,
    visible_file_ids: list[str],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
    query = f"""
    MATCH (source {{id: $entity_id, project_id: $project_id}})
    WHERE source.id IN $visible_file_ids
       OR EXISTS {{
            MATCH (visible_file)-[:CONTAINS|DEFINES*1..4]->(source)
            WHERE visible_file.id IN $visible_file_ids
       }}
    OPTIONAL MATCH path = (source)-[*1..{depth}]-(neighbor)
    WHERE all(scoped_node IN nodes(path)
        WHERE scoped_node.project_id = $project_id
          AND (
            scoped_node.id IN $visible_file_ids
            OR EXISTS {{
                MATCH (visible_file)-[:CONTAINS|DEFINES*1..4]->(scoped_node)
                WHERE visible_file.id IN $visible_file_ids
            }}
          )
    )
    WITH source, collect(DISTINCT neighbor) AS neighbors, collect(path) AS paths
    WITH source, neighbors, [p IN paths WHERE p IS NOT NULL] AS valid_paths
    WITH source, neighbors,
         reduce(es = [], p IN valid_paths |
           es + [rel IN relationships(p) | {{
             source: startNode(rel).id,
             target: endNode(rel).id,
             type: type(rel),
             direction: CASE WHEN startNode(rel).id = source.id THEN 'outbound' ELSE 'inbound' END
           }}]
         ) AS edges
    RETURN source {{
        .id, .name, .description,
        file_path: coalesce(source.file_path, source.filePath, source.path, source.relative_path),
        label: labels(source)[0]
    }} AS source_node,
    [n IN neighbors WHERE n IS NOT NULL | n {{
        .id, .name, .description,
        file_path: coalesce(n.file_path, n.filePath, n.path, n.relative_path),
        label: labels(n)[0]
    }}] AS neighbors,
    edges AS edges
    """
    with driver.session(database=database) as session:
        records = list(session.run(
            query,
            entity_id=entity_id,
            branch=branch,
            project_id=project_id,
            visible_file_ids=visible_file_ids,
        ))
    if not records:
        return None, [], []
    record = records[0]
    source = _format_node(record.get("source_node"))
    neighbors = _dedupe_nodes(_format_node(node) for node in (record.get("neighbors") or []))
    edges = _normalize_edge_records(record.get("edges") or record.get("path_edges") or [])
    return source, neighbors, edges


def _load_chain(
    driver,
    database: str | None,
    *,
    project_id: int,
    branch: str,
    locator: dict[str, str],
    depth: int,
    visible_file_ids: list[str],
) -> dict[str, Any]:
    query = _chain_query(locator["type"], depth)
    params = {
        "project_id": project_id,
        "branch": branch,
        "start_node": locator["value"] if locator["type"] == "start_node" else None,
        "file_path": locator["value"] if locator["type"] == "file_path" else None,
        "symbol": locator["value"] if locator["type"] == "symbol" else None,
        "commit_sha": locator["value"] if locator["type"] == "commit_sha" else None,
        "visible_file_ids": visible_file_ids,
    }
    with driver.session(database=database) as session:
        records = list(session.run(query, **params))
    if not records:
        return {"start_node": None, "nodes": [], "edges": [], "affected_commits": []}

    start_node = None
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    affected_commits: list[str] = []
    for record in records:
        if start_node is None:
            start_node = _format_node(record.get("start_node"))
        nodes.extend(_format_node(node) for node in (record.get("nodes") or []))
        edges.extend(_normalize_edge_records(record.get("edges") or record.get("path_edges") or []))
        affected_commits.extend(str(value) for value in (record.get("affected_commits") or []) if value)

    return {
        "start_node": start_node,
        "nodes": _dedupe_nodes(nodes),
        "edges": _dedupe_edges(edges),
        "affected_commits": sorted(set(affected_commits)),
    }


def _chain_query(locator_type: str, depth: int) -> str:
    if locator_type == "start_node":
        start_predicate = "start.id = $start_node"
    elif locator_type == "file_path":
        start_predicate = "coalesce(start.file_path, start.filePath, start.path, start.relative_path) = $file_path"
    elif locator_type == "symbol":
        start_predicate = "start.name = $symbol"
    elif locator_type == "commit_sha":
        start_predicate = "coalesce(start.commit_sha, start.commitSha, start.last_commit, start.lastCommit) = $commit_sha"
    else:
        raise GraphQueryError(
            category="invalid_argument",
            message="unsupported chain locator",
            details={"locator_type": locator_type},
        )
    return f"""
    MATCH (start)
    WHERE start.project_id = $project_id
      AND {start_predicate}
      AND (
        start.id IN $visible_file_ids
        OR EXISTS {{
            MATCH (visible_file)-[:CONTAINS|DEFINES*1..4]->(start)
            WHERE visible_file.id IN $visible_file_ids
        }}
      )
    OPTIONAL MATCH path = (start)-[*1..{depth}]-(end)
    WHERE all(scoped_node IN nodes(path)
        WHERE scoped_node.project_id = $project_id
          AND (
            scoped_node.id IN $visible_file_ids
            OR EXISTS {{
                MATCH (visible_file)-[:CONTAINS|DEFINES*1..4]->(scoped_node)
                WHERE visible_file.id IN $visible_file_ids
            }}
          )
    )
    WITH start, collect(path) AS paths
    WITH start, [p IN paths WHERE p IS NOT NULL] AS valid_paths
    WITH start,
         reduce(ns = [], p IN valid_paths | ns + nodes(p)) AS raw_nodes,
         reduce(es = [], p IN valid_paths |
           es + [rel IN relationships(p) | {{
             source: startNode(rel).id,
             target: endNode(rel).id,
             type: type(rel),
             direction: CASE WHEN startNode(rel).id = start.id THEN 'outbound' ELSE 'inbound' END
           }}]
         ) AS edges
    RETURN start {{
        .id, .name, .description,
        file_path: coalesce(start.file_path, start.filePath, start.path, start.relative_path),
        label: labels(start)[0]
    }} AS start_node,
    [n IN raw_nodes | n {{
        .id, .name, .description,
        file_path: coalesce(n.file_path, n.filePath, n.path, n.relative_path),
        label: labels(n)[0]
    }}] AS nodes,
    edges AS edges,
    [] AS affected_commits
    LIMIT 100
    """


def _format_node(raw_node) -> dict[str, Any] | None:
    if raw_node is None:
        return None
    node = dict(raw_node)
    return {
        "entity_id": node.get("id") or node.get("entity_id"),
        "entity_type": node.get("label") or node.get("entity_type"),
        "name": node.get("name"),
        "file_path": node.get("file_path") or node.get("filePath") or node.get("path") or node.get("relative_path"),
        "description": node.get("description") or "",
    }


def _dedupe_nodes(nodes) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not node:
            continue
        key = str(node.get("entity_id") or "")
        if key and key not in deduped:
            deduped[key] = node
    return list(deduped.values())


def _normalize_edge_records(raw_edges) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for item in raw_edges:
        if isinstance(item, list):
            edges.extend(_normalize_edge_records(item))
            continue
        if item is None:
            continue
        edge = dict(item)
        source = edge.get("source") or edge.get("start") or edge.get("from")
        target = edge.get("target") or edge.get("end") or edge.get("to")
        rel_type = edge.get("type") or edge.get("label") or edge.get("relationship")
        if not source or not target or not rel_type:
            continue
        edges.append(
            {
                "source": source,
                "target": target,
                "type": rel_type,
                "direction": edge.get("direction") or "outbound",
            }
        )
    return _dedupe_edges(edges)


def _dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for edge in edges:
        key = (
            str(edge.get("source") or ""),
            str(edge.get("target") or ""),
            str(edge.get("type") or ""),
            str(edge.get("direction") or ""),
        )
        if key not in deduped:
            deduped[key] = edge
    return list(deduped.values())


def _summarize_edges(edges: list[dict[str, Any]]) -> list[str]:
    return [
        f"{edge['source']} -[{edge['type']}]-> {edge['target']}"
        for edge in edges
        if edge.get("source") and edge.get("target") and edge.get("type")
    ]


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
