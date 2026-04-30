"""Neo4j writer for current project-branch code graphs."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

from service.repositories import doc_code_link_repository

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NODE_LABELS = {
    "File",
    "Folder",
    "Class",
    "Interface",
    "Enum",
    "Annotation",
    "Method",
    "Function",
    "Constructor",
    "Module",
    "Package",
}
_CODE_NODE_LABELS = {
    "Annotation",
    "Class",
    "Constructor",
    "Enum",
    "Function",
    "Interface",
    "Method",
}


def branch_has_graph(
    *,
    config: dict[str, Any],
    database: str | None,
    project_id: int,
    branch_name: str,
) -> bool:
    driver = _create_driver(config)
    try:
        with driver.session(database=database) as session:
            row = session.run(
                """
                MATCH (:Project {project_id: $project_id})-[:HAS_BRANCH_GRAPH]->(g:BranchGraph {
                    project_id: $project_id,
                    branch_name: $branch_name
                })
                RETURN count(g) AS count
                """,
                project_id=project_id,
                branch_name=branch_name,
            ).single()
            return bool(row and int(row["count"]) > 0)
    finally:
        driver.close()


def replace_branch_graph(
    *,
    conn,
    config: dict[str, Any],
    database: str | None,
    graph,
    project_id: int,
    branch_name: str,
    graph_id: int,
    head_commit: str | None,
    batch_size: int = 1000,
    rel_batch_size: int = 1000,
) -> dict[str, Any]:
    driver = _create_driver(config)
    try:
        _ensure_constraints(driver, database)
        nodes_written, rels_written = _replace_graph(
            driver,
            database=database,
            graph=graph,
            project_id=project_id,
            branch_name=branch_name,
            graph_id=graph_id,
            head_commit=head_commit,
            batch_size=batch_size,
            rel_batch_size=rel_batch_size,
        )
        doc_links_written = _rebuild_doc_code_links(
            conn,
            driver,
            database=database,
            project_id=project_id,
            branch_name=branch_name,
            graph_id=graph_id,
        )
    finally:
        driver.close()
    return {
        "status": "updated",
        "nodes_written": nodes_written,
        "relationships_written": rels_written,
        "doc_code_links_written": doc_links_written,
    }


def _create_driver(config: dict[str, Any]):
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        config["neo4j_uri"],
        auth=(config.get("neo4j_user") or "neo4j", config.get("neo4j_password") or ""),
    )


def _ensure_constraints(driver, database: str | None) -> None:
    with driver.session(database=database) as session:
        for statement in [
            "CREATE CONSTRAINT project_project_id IF NOT EXISTS FOR (n:Project) REQUIRE n.project_id IS UNIQUE",
            "CREATE CONSTRAINT branch_graph_graph_id IF NOT EXISTS FOR (n:BranchGraph) REQUIRE n.graph_id IS UNIQUE",
            "CREATE INDEX branch_graph_branch IF NOT EXISTS FOR (n:BranchGraph) ON (n.project_id, n.branch_name)",
            "CREATE CONSTRAINT code_node_id IF NOT EXISTS FOR (n:CodeNode) REQUIRE n.id IS UNIQUE",
            "CREATE INDEX code_node_branch IF NOT EXISTS FOR (n:CodeNode) ON (n.project_id, n.branch_name)",
            *[
                f"CREATE CONSTRAINT code_{label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                for label in sorted(_NODE_LABELS)
            ],
            *[
                f"CREATE INDEX code_{label.lower()}_branch IF NOT EXISTS FOR (n:{label}) ON (n.project_id, n.branch_name)"
                for label in sorted(_NODE_LABELS)
            ],
        ]:
            try:
                session.run(statement)
            except Exception:
                pass


def _replace_graph(
    driver,
    *,
    database: str | None,
    graph,
    project_id: int,
    branch_name: str,
    graph_id: int,
    head_commit: str | None,
    batch_size: int,
    rel_batch_size: int,
) -> tuple[int, int]:
    nodes_written = 0
    rels_written = 0
    with driver.session(database=database) as session:
        for label in sorted(_NODE_LABELS):
            session.execute_write(
                _delete_branch_nodes,
                label=label,
                project_id=project_id,
                branch_name=branch_name,
            )
        session.run(
            """
            MATCH (g:BranchGraph {project_id: $project_id, branch_name: $branch_name})
            DETACH DELETE g
            """,
            project_id=project_id,
            branch_name=branch_name,
        )
        session.execute_write(
            _write_branch_graph_root,
            project_id=project_id,
            branch_name=branch_name,
            graph_id=graph_id,
            head_commit=head_commit,
        )
        session.run(
            """
            MATCH (:Document)-[r:LINKS_TO_CODE {project_id: $project_id, branch_name: $branch_name}]->()
            DELETE r
            """,
            project_id=project_id,
            branch_name=branch_name,
        )

        nodes = list(graph.iterNodes())
        for index in range(0, len(nodes), batch_size):
            batch = nodes[index : index + batch_size]
            for label, label_batch in _group_by(batch, "label").items():
                rows = [
                    _node_row(
                        node,
                        project_id=project_id,
                        branch_name=branch_name,
                        graph_id=graph_id,
                        head_commit=head_commit,
                    )
                    for node in label_batch
                ]
                labels = _labels_for_node(label)
                session.execute_write(_write_nodes, labels=labels, rows=rows)
                nodes_written += len(rows)

        nodes_by_id = {str(node["id"]): node for node in nodes}
        root_rows = _root_relationship_rows(
            graph,
            nodes_by_id=nodes_by_id,
            project_id=project_id,
            branch_name=branch_name,
            graph_id=graph_id,
        )
        if root_rows:
            for target_label, root_batch in _group_by(root_rows, "target_label").items():
                written = session.execute_write(
                    _write_branch_graph_root_links,
                    target_label=_safe_identifier(target_label, fallback="CodeElement"),
                    rows=root_batch,
                )
                rels_written += int(written or 0)

        relationships = list(graph.iterRelationships())
        for index in range(0, len(relationships), rel_batch_size):
            batch = relationships[index : index + rel_batch_size]
            rows = [
                _relationship_row(
                    relationship,
                    nodes_by_id=nodes_by_id,
                    project_id=project_id,
                    branch_name=branch_name,
                    graph_id=graph_id,
                )
                for relationship in batch
            ]
            for rel_key, rel_rows in _group_relationship_rows(rows).items():
                relationship_type, source_label, target_label = rel_key
                written = session.execute_write(
                    _write_relationships,
                    relationship_type=relationship_type,
                    source_label=source_label,
                    target_label=target_label,
                    rows=rel_rows,
                )
                rels_written += int(written or 0)
    return nodes_written, rels_written


def _delete_branch_nodes(tx, *, label: str, project_id: int, branch_name: str) -> None:
    tx.run(
        f"""
        MATCH (n:{label} {{project_id: $project_id, branch_name: $branch_name}})
        DETACH DELETE n
        """,
        project_id=project_id,
        branch_name=branch_name,
    )


def _write_nodes(tx, *, labels: str, rows: list[dict[str, Any]]) -> None:
    tx.run(
        f"""
        UNWIND $nodes AS row
        MERGE (n:{labels} {{id: row.id}})
        SET n += row.props
        """,
        nodes=rows,
    )


def _write_branch_graph_root(
    tx,
    *,
    project_id: int,
    branch_name: str,
    graph_id: int,
    head_commit: str | None,
) -> None:
    tx.run(
        """
        MERGE (p:Project {project_id: $project_id})
        SET p.id = 'project:' + toString($project_id),
            p.name = coalesce(p.name, 'project:' + toString($project_id))
        MERGE (g:BranchGraph {graph_id: $graph_id})
        SET g.project_id = $project_id,
            g.branch_name = $branch_name,
            g.branch = $branch_name,
            g.head_commit = $head_commit
        MERGE (p)-[r:HAS_BRANCH_GRAPH {graph_id: $graph_id}]->(g)
        SET r.project_id = $project_id,
            r.branch_name = $branch_name,
            r.branch = $branch_name
        """,
        project_id=project_id,
        branch_name=branch_name,
        graph_id=graph_id,
        head_commit=head_commit or "",
    )


def _write_branch_graph_root_links(tx, *, target_label: str, rows: list[dict[str, Any]]) -> int:
    result = tx.run(
        f"""
        UNWIND $roots AS root
        MATCH (g:BranchGraph {{graph_id: root.props.graph_id}})
        MATCH (target:{target_label} {{id: root.target_id}})
        MERGE (g)-[r:CONTAINS {{id: root.id}}]->(target)
        SET r += root.props
        RETURN count(r) AS written
        """,
        roots=rows,
    )
    row = result.single()
    return int(row["written"] if row else 0)


def _write_relationships(
    tx,
    *,
    relationship_type: str,
    source_label: str,
    target_label: str,
    rows: list[dict[str, Any]],
) -> int:
    result = tx.run(
        f"""
        UNWIND $rels AS rel
        MATCH (source:{source_label} {{id: rel.source_id}})
        MATCH (target:{target_label} {{id: rel.target_id}})
        MERGE (source)-[r:{relationship_type} {{id: rel.id}}]->(target)
        SET r += rel.props
        RETURN count(r) AS written
        """,
        rels=rows,
    )
    row = result.single()
    return int(row["written"] if row else 0)


def _rebuild_doc_code_links(
    conn,
    driver,
    *,
    database: str | None,
    project_id: int,
    branch_name: str,
    graph_id: int,
) -> int:
    links = doc_code_link_repository.list_active_for_branch(
        conn,
        project_id=project_id,
        branch_name=branch_name,
    )
    rows = []
    for link in links:
        locator = link.get("code_locator_json") or {}
        code_node_id = locator.get("code_node_id") or link.get("resolved_node_id")
        if not code_node_id:
            continue
        rows.append(
            {
                "id": f"doc_code_link:{link['id']}",
                "doc_id": link["doc_id"],
                "doc_node_id": link.get("doc_node_id"),
                "code_node_id": code_node_id,
                "scoped_code_node_id": _scoped_id(project_id, branch_name, code_node_id),
                "code_label": _label_from_node_id(code_node_id),
                "project_id": project_id,
                "branch_name": branch_name,
                "graph_id": graph_id,
                "relation_type": link.get("relation_type") or "LINKS_TO_CODE",
                "source": link.get("source") or "manual",
                "confidence": link.get("confidence"),
            }
        )
    if not rows:
        return 0

    written = 0
    with driver.session(database=database) as session:
        for code_label, link_rows in _group_by(rows, "code_label").items():
            result = session.execute_write(
                _write_doc_code_links,
                code_label=_safe_identifier(code_label, fallback="CodeElement"),
                rows=link_rows,
            )
            written += int(result or 0)
    return written


def _write_doc_code_links(tx, *, code_label: str, rows: list[dict[str, Any]]) -> int:
    result = tx.run(
        """
        UNWIND $links AS link
        MATCH (code:CodeNode {id: link.scoped_code_node_id})
        MERGE (doc:Document {doc_id: link.doc_id})
        MERGE (doc)-[r:LINKS_TO_CODE {id: link.id}]->(code)
        SET r.project_id = link.project_id,
            r.branch_name = link.branch_name,
            r.branch = link.branch_name,
            r.graph_id = link.graph_id,
            r.doc_node_id = link.doc_node_id,
            r.code_node_id = link.code_node_id,
            r.relation_type = link.relation_type,
            r.source = link.source,
            r.confidence = link.confidence
        RETURN count(r) AS written
        """,
        links=rows,
    )
    row = result.single()
    return int(row["written"] if row else 0)


def _node_row(
    node: dict[str, Any],
    *,
    project_id: int,
    branch_name: str,
    graph_id: int,
    head_commit: str | None,
) -> dict[str, Any]:
    node_id = str(node["id"])
    props = _props_for_neo4j(node.get("properties") or {})
    props.update(
        {
            "id": _scoped_id(project_id, branch_name, node_id),
            "node_id": node_id,
            "fact_id": node_id,
            "project_id": project_id,
            "branch_name": branch_name,
            "branch": branch_name,
            "graph_id": graph_id,
            "head_commit": head_commit or "",
            "label": str(node.get("label") or ""),
        }
    )
    return {"id": props["id"], "props": props}


def _relationship_row(
    relationship: dict[str, Any],
    *,
    nodes_by_id: dict[str, dict[str, Any]],
    project_id: int,
    branch_name: str,
    graph_id: int,
) -> dict[str, Any]:
    rel_id = str(relationship.get("id") or f"{relationship['sourceId']}->{relationship['targetId']}")
    source_node = nodes_by_id.get(str(relationship["sourceId"])) or {}
    target_node = nodes_by_id.get(str(relationship["targetId"])) or {}
    source_label = _match_label_for_node(str(source_node.get("label") or "CodeElement"))
    target_label = _match_label_for_node(str(target_node.get("label") or "CodeElement"))
    relationship_type = _safe_identifier(str(relationship.get("type") or ""), fallback="RELATED_TO")
    props = _props_for_neo4j(
        {
            "relationship_id": rel_id,
            "project_id": project_id,
            "branch_name": branch_name,
            "branch": branch_name,
            "graph_id": graph_id,
            "confidence": relationship.get("confidence", 1.0),
            "reason": relationship.get("reason") or "",
            "type": relationship.get("type") or "",
        }
    )
    return {
        "id": _scoped_id(project_id, branch_name, rel_id),
        "source_id": _scoped_id(project_id, branch_name, str(relationship["sourceId"])),
        "target_id": _scoped_id(project_id, branch_name, str(relationship["targetId"])),
        "relationship_type": relationship_type,
        "source_label": source_label,
        "target_label": target_label,
        "props": props,
    }


def _props_for_neo4j(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): _value_for_neo4j(value)
        for key, value in properties.items()
        if value is not None
    }


def _value_for_neo4j(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list) and all(isinstance(item, (str, int, float, bool)) for item in value):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _group_by(items: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(str(item.get(key) or ""), []).append(item)
    return groups


def _group_relationship_rows(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str, str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            str(row.get("relationship_type") or "RELATED_TO"),
            str(row.get("source_label") or "CodeElement"),
            str(row.get("target_label") or "CodeElement"),
        )
        groups.setdefault(key, []).append(row)
    return groups


def _labels_for_node(primary_label: str) -> str:
    label = _safe_identifier(primary_label, fallback="CodeElement")
    return f"CodeNode:{label}" if label in _CODE_NODE_LABELS else label


def _match_label_for_node(primary_label: str) -> str:
    return _safe_identifier(primary_label, fallback="CodeElement")


def _root_relationship_rows(
    graph,
    *,
    nodes_by_id: dict[str, dict[str, Any]],
    project_id: int,
    branch_name: str,
    graph_id: int,
) -> list[dict[str, Any]]:
    contained_node_ids = {
        relationship["targetId"]
        for relationship in graph.iterRelationships()
        if relationship.get("type") == "CONTAINS"
    }
    rows = []
    for node in graph.iterNodes():
        node_id = str(node["id"])
        if str(node.get("label") or "") != "Folder":
            continue
        if node_id in contained_node_ids:
            continue
        rows.append(
            {
                "id": f"project:{project_id}:branch:{branch_name}:branch_graph:{graph_id}:contains:{node_id}",
                "target_id": _scoped_id(project_id, branch_name, node_id),
                "target_label": _match_label_for_node(str(node.get("label") or "CodeElement")),
                "props": {
                    "project_id": project_id,
                    "branch_name": branch_name,
                    "branch": branch_name,
                    "graph_id": graph_id,
                    "type": "CONTAINS",
                },
            }
        )
    return rows


def _label_from_node_id(node_id: str) -> str:
    return _safe_identifier(str(node_id).split(":", 1)[0], fallback="CodeElement")


def _safe_identifier(value: str, *, fallback: str) -> str:
    text = str(value or "").strip()
    return text if _IDENTIFIER_RE.match(text) else fallback


def _scoped_id(project_id: int, branch_name: str, item_id: str) -> str:
    return f"project:{project_id}:branch:{branch_name}:node:{item_id}"
