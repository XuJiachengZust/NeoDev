"""Neo4j write: ensure constraints, MERGE nodes and relationships in batches."""

from typing import Any

# Labels we create unique constraint on (main structural and code element types)
CONSTRAINT_LABELS = [
    "File", "Folder", "Project", "Package", "Module",
    "Class", "Function", "Method", "Variable", "Interface", "Enum",
    "Struct", "Namespace", "Trait", "Impl", "Community", "Process",
]


def ensure_constraints(driver, database: str | None = None) -> None:
    """Create composite uniqueness constraint (n.id, n.branch) for each label (idempotent)."""
    with driver.session(database=database) as session:
        for label in CONSTRAINT_LABELS:
            try:
                session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE (n.id, n.branch) IS NODE KEY"
                )
            except Exception:
                try:
                    session.run(
                        f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE (n.id, n.branch) IS UNIQUE"
                    )
                except Exception:
                    pass


def _props_for_neo4j(properties: dict[str, Any]) -> dict[str, Any]:
    """Pass through; Neo4j driver accepts list, str, int, float, bool."""
    return {k: v for k, v in properties.items() if v is not None}


def delete_branch(driver, branch: str, database: str | None = None) -> None:
    """Remove all nodes and relationships for the given branch (full branch subgraph replace)."""
    with driver.session(database=database) as session:
        session.run("MATCH (n) WHERE n.branch = $branch DETACH DELETE n", branch=branch)


def delete_nodes_by_file_paths(
    driver,
    branch: str,
    file_paths: list[str],
    database: str | None = None,
) -> None:
    """
    Remove nodes (and their relationships) for the given branch whose filePath is in file_paths.
    Used for incremental update: only re-scanned paths are removed then rewritten.
    """
    if not file_paths:
        return
    with driver.session(database=database) as session:
        session.run(
            "MATCH (n) WHERE n.branch = $branch AND n.filePath IN $paths DETACH DELETE n",
            branch=branch,
            paths=file_paths,
        )


def write_graph(
    graph,
    driver,
    branch: str,
    batch_size: int = 5000,
    rel_batch_size: int = 2000,
    database: str | None = None,
) -> tuple[int, int]:
    """
    MERGE all nodes by (id, branch), then MERGE all relationships (endpoints matched by id+branch).
    Returns (nodes_written, relationships_written).
    """
    nodes_written = 0
    rels_written = 0

    with driver.session(database=database) as session:
        nodes = list(graph.iterNodes())
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i : i + batch_size]
            def work(tx):
                nonlocal nodes_written
                for n in batch:
                    label = n["label"]
                    props = _props_for_neo4j(n.get("properties", {}))
                    props["id"] = n["id"]
                    props["branch"] = branch
                    tx.run(
                        f"MERGE (n:{label} {{id: $id, branch: $branch}}) SET n += $props",
                        id=n["id"],
                        branch=branch,
                        props=props,
                    )
                    nodes_written += 1

            session.execute_write(work)

        relationships = list(graph.iterRelationships())
        for i in range(0, len(relationships), rel_batch_size):
            batch = relationships[i : i + rel_batch_size]
            def work_rel(tx):
                nonlocal rels_written
                for r in batch:
                    rel_type = r["type"]
                    rid = r.get("id") or f"{r['sourceId']}-{r['targetId']}"
                    tx.run(
                        f"""
                        MERGE (a {{id: $sourceId, branch: $branch}})
                        MERGE (b {{id: $targetId, branch: $branch}})
                        MERGE (a)-[r:{rel_type} {{id: $relId}}]->(b)
                        SET r.confidence = $confidence, r.reason = $reason
                        """,
                        sourceId=r["sourceId"],
                        targetId=r["targetId"],
                        branch=branch,
                        relId=rid,
                        confidence=r.get("confidence", 1.0),
                        reason=r.get("reason", ""),
                    )
                    rels_written += 1

            session.execute_write(work_rel)

    return nodes_written, rels_written
