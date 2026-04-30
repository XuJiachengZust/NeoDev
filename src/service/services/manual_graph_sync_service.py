"""Neo4j synchronization for manual graph facts."""

from __future__ import annotations

import re
from typing import Any

from service.services import project_service
from service.services.neo4j_config_service import load_neo4j_config


def sync_node(conn, *, project_id: int, node: dict, fact: dict) -> None:
    driver, database = _open_driver(conn, project_id)
    if driver is None:
        return
    try:
        props = {
            "id": fact["fact_id"],
            "fact_id": fact["fact_id"],
            "project_id": project_id,
            "name": node.get("name"),
            "node_type": fact.get("node_type"),
            "source": "manual",
            "manual_node_id": node.get("node_id"),
            "type_key": node.get("type_key"),
            "status": node.get("status") or "active",
        }
        props.update((fact.get("metadata_json") or {}).get("properties") or {})
        with driver.session(database=database) as session:
            session.run(
                """
                MERGE (n:GraphNode:CodeFact {id: $fact_id})
                SET n += $props
                """,
                fact_id=fact["fact_id"],
                props=_clean_props(props),
            )
    finally:
        driver.close()


def archive_node(conn, *, project_id: int, node: dict, fact_id: str) -> None:
    driver, database = _open_driver(conn, project_id)
    if driver is None:
        return
    try:
        with driver.session(database=database) as session:
            session.run(
                """
                MATCH (n:GraphNode {id: $fact_id, project_id: $project_id})
                SET n.status = 'archived'
                """,
                fact_id=fact_id,
                project_id=project_id,
            )
    finally:
        driver.close()


def sync_edge(
    conn,
    *,
    project_id: int,
    branch: str,
    snapshot_id: int,
    edge: dict,
) -> None:
    driver, database = _open_driver(conn, project_id)
    if driver is None:
        return
    relationship_type = normalize_relationship_type(str(edge.get("type_key") or "RELATED_TO"))
    source_fact_id = _manual_node_fact_id(project_id, edge["from_node_id"])
    target_fact_id = _manual_node_fact_id(project_id, edge["to_node_id"])
    props = {
        "id": edge["edge_id"],
        "project_id": project_id,
        "type_key": edge.get("type_key"),
        "source": "manual",
        "status": edge.get("status") or "active",
        "branch_name": branch,
        "snapshot_id": snapshot_id,
    }
    props.update(edge.get("properties") or {})
    try:
        with driver.session(database=database) as session:
            session.run(
                f"""
                MATCH (a:GraphNode {{id: $source_fact_id, project_id: $project_id}})
                MATCH (b:GraphNode {{id: $target_fact_id, project_id: $project_id}})
                MERGE (a)-[r:{relationship_type} {{id: $edge_id}}]->(b)
                SET r += $props
                """,
                source_fact_id=source_fact_id,
                target_fact_id=target_fact_id,
                edge_id=edge["edge_id"],
                project_id=project_id,
                props=_clean_props(props),
            )
    finally:
        driver.close()


def archive_edge(conn, *, project_id: int, edge: dict) -> None:
    driver, database = _open_driver(conn, project_id)
    if driver is None:
        return
    try:
        with driver.session(database=database) as session:
            session.run(
                """
                MATCH ()-[r {id: $edge_id, project_id: $project_id}]-()
                SET r.status = 'archived'
                """,
                edge_id=edge["edge_id"],
                project_id=project_id,
            )
    finally:
        driver.close()


def clear_project_graph(conn, *, project_id: int) -> None:
    driver, database = _open_driver(conn, project_id)
    if driver is None:
        return
    try:
        with driver.session(database=database) as session:
            session.run(
                """
                MATCH (n:GraphNode {project_id: $project_id})
                DETACH DELETE n
                """,
                project_id=project_id,
            )
    finally:
        driver.close()


def normalize_relationship_type(type_key: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", type_key.strip()).upper().strip("_")
    return normalized or "RELATED_TO"


def _open_driver(conn, project_id: int):
    project = project_service.get_project(conn, project_id)
    if not project:
        return None, None
    config, database = load_neo4j_config(project)
    if not config or not config.get("neo4j_uri"):
        return None, None
    return _create_driver(config), database


def _create_driver(config: dict):
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        config["neo4j_uri"],
        auth=(config.get("neo4j_user") or "neo4j", config.get("neo4j_password") or ""),
    )


def _manual_node_fact_id(project_id: int, node_id: str) -> str:
    return f"manual:{project_id}:node:{node_id}"


def _clean_props(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
