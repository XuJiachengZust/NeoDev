"""Neo4j write: ensure constraints, MERGE nodes and relationships in batches."""

from typing import Any
from typing import get_args

from gitnexus_parser.graph.types import NodeLabel


# Labels we create unique constraints on. Keep this tied to the declared graph
# schema so newly supported parser labels cannot silently miss id uniqueness.
CODE_FACT_LABELS = {
    "File",
    "Class",
    "Interface",
    "Enum",
    "Annotation",
    "Method",
    "Function",
    "Constructor",
}

CONSTRAINT_LABELS = [*list(get_args(NodeLabel)), "CodeFact", "GraphNode"]


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
            for label, label_batch in _group_by(batch, "label").items():
                rows = []
                for n in label_batch:
                    props = _props_for_neo4j(n.get("properties", {}))
                    props["id"] = n["id"]
                    props["fact_id"] = n["id"]
                    props["project_id"] = project_id
                    rows.append({"id": n["id"], "props": props})

                def work(tx, *, node_label=label, node_rows=rows):
                    nonlocal nodes_written
                    labels = _labels_for_merge(node_label)
                    tx.run(
                        f"""
                        UNWIND $nodes AS row
                        MERGE (n:{labels} {{id: row.id}})
                        SET n += row.props
                        SET n:GraphNode
                        """,
                        nodes=node_rows,
                    )
                    nodes_written += len(node_rows)

                session.execute_write(work)

        relationships = list(graph.iterRelationships())
        for i in range(0, len(relationships), rel_batch_size):
            batch = relationships[i : i + rel_batch_size]
            for rel_type, rel_batch in _group_by(batch, "type").items():
                rows = [
                    {
                        "id": r.get("id") or f"{r['sourceId']}-{r['targetId']}",
                        "sourceId": r["sourceId"],
                        "targetId": r["targetId"],
                        "confidence": r.get("confidence", 1.0),
                        "reason": r.get("reason", ""),
                    }
                    for r in rel_batch
                ]

                def work_rel(tx, *, relationship_type=rel_type, rel_rows=rows):
                    nonlocal rels_written
                    result = tx.run(
                        f"""
                        UNWIND $rels AS rel
                        MATCH (a:GraphNode {{id: rel.sourceId}})
                        MATCH (b:GraphNode {{id: rel.targetId}})
                        MERGE (a)-[r:{relationship_type} {{id: rel.id}}]->(b)
                        SET r.confidence = rel.confidence,
                            r.reason = rel.reason
                        RETURN count(r) AS written
                        """,
                        rels=rel_rows,
                    )
                    row = result.single()
                    rels_written += int(row["written"] if row else 0)

                session.execute_write(work_rel)

    return nodes_written, rels_written


def _group_by(items: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(str(item[key]), []).append(item)
    return groups


def _labels_for_merge(primary_label: str) -> str:
    if primary_label in CODE_FACT_LABELS:
        return f"{primary_label}:CodeFact"
    return primary_label
