"""Node service: list graph nodes by version (Neo4j) with optional name/type filter."""

import logging

from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo
from service.services.ai_preprocessor_service import _load_neo4j_config

logger = logging.getLogger(__name__)


def list_nodes_by_version(
    conn,
    project_id: int,
    version_id: int,
    *,
    name: str | None = None,
    type_filter: str | None = None,
) -> list[dict] | None:
    """
    List Neo4j nodes for a version (branch). Returns None if project/version not found;
    returns [] if Neo4j not configured or no nodes.
    Each item: {id, label, name, properties}.
    """
    project = project_repo.find_by_id(conn, project_id)
    if project is None:
        return None
    ver = version_repo.find_by_id(conn, version_id)
    if ver is None or ver.get("project_id") != project_id:
        return None
    branch = (ver.get("branch") or "").strip()
    if not branch:
        return []

    neo4j_config, database = _load_neo4j_config(project)
    if not neo4j_config or not neo4j_config.get("neo4j_uri"):
        return []

    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        neo4j_config["neo4j_uri"],
        auth=(
            neo4j_config.get("neo4j_user") or "neo4j",
            neo4j_config.get("neo4j_password") or "",
        ),
    )
    try:
        with driver.session(database=database) as session:
            conditions = ["n.branch = $branch", "n.project_id = $project_id"]
            params: dict = {"branch": branch, "project_id": project_id}
            if name is not None and name.strip() != "":
                conditions.append("n.name CONTAINS $name")
                params["name"] = name.strip()
            if type_filter is not None and type_filter.strip() != "":
                conditions.append("labels(n)[0] = $label")
                params["label"] = type_filter.strip()

            q = f"""
            MATCH (n)
            WHERE {" AND ".join(conditions)}
            RETURN n.id AS id, labels(n)[0] AS label, n.name AS name, properties(n) AS properties
            ORDER BY n.name
            """
            result = session.run(q, params)
            return [dict(record) for record in result]
    finally:
        driver.close()
