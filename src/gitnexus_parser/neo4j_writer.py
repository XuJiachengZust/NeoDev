"""Neo4j write: ensure constraints, MERGE nodes and relationships in batches."""

from typing import Any

# Labels we create unique constraint on (main structural and code element types)
CONSTRAINT_LABELS = [
    "File", "Folder", "Project", "Package", "Module",
    "Class", "Function", "Method", "Variable", "Interface", "Enum",
    "Struct", "Namespace", "Trait", "Impl", "Community", "Process",
]


def ensure_constraints(driver, database: str | None = None) -> None:
    """Create repository-fact uniqueness constraints for each label."""
    with driver.session(database=database) as session:
        for label in CONSTRAINT_LABELS:
            try:
                session.run(
                    f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                )
            except Exception:
                pass


def _props_for_neo4j(properties: dict[str, Any]) -> dict[str, Any]:
    """Pass through; Neo4j driver accepts list, str, int, float, bool."""
    return {k: v for k, v in properties.items() if v is not None}


def write_graph(
    graph,
    driver,
    project_id: int = 0,
    batch_size: int = 5000,
    rel_batch_size: int = 2000,
    database: str | None = None,
) -> tuple[int, int]:
    """
    MERGE all repository fact nodes by id, set project_id on each node.
    Create relationships only when both endpoints already exist.
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
                    props["project_id"] = project_id
                    tx.run(
                        f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                        id=n["id"],
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
                    result = tx.run(
                        f"""
                        MATCH (a {{id: $sourceId}})
                        MATCH (b {{id: $targetId}})
                        MERGE (a)-[r:{rel_type} {{id: $relId}}]->(b)
                        SET r.confidence = $confidence, r.reason = $reason
                        RETURN 1 AS written
                        """,
                        sourceId=r["sourceId"],
                        targetId=r["targetId"],
                        relId=rid,
                        confidence=r.get("confidence", 1.0),
                        reason=r.get("reason", ""),
                    )
                    if result.single():
                        rels_written += 1

            session.execute_write(work_rel)

    return nodes_written, rels_written
