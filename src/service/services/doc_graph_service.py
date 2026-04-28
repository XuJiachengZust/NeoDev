"""Document graph writer for Neo4j document-level facts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def upsert_document_graph(conn, *, binding: dict, document: dict) -> dict[str, Any]:
    config, database = _load_config()
    if not config or not config.get("neo4j_uri"):
        return {"status": "not_configured"}
    driver = _create_driver(config)
    try:
        with driver.session(database=database) as session:
            session.run(
                """
                MERGE (d:Document {doc_id: $doc_id, product_id: $product_id})
                SET d.document_id = $document_id,
                    d.doc_binding_id = $doc_binding_id,
                    d.title = $title,
                    d.doc_type = $doc_type,
                    d.relative_path = $relative_path,
                    d.status = $status,
                    d.content_hash = $content_hash,
                    d.updated_at = $updated_at
                """,
                document_id=document["id"],
                doc_binding_id=binding["id"],
                product_id=binding["product_id"],
                doc_id=document["doc_id"],
                title=document.get("title") or "",
                doc_type=document.get("doc_type") or "",
                relative_path=document.get("relative_path") or "",
                status=document.get("status") or "active",
                content_hash=document.get("content_hash") or "",
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            targets = ((document.get("relations_json") or {}).get("target") or [])
            for target in targets:
                session.run(
                    """
                    MATCH (source:Document {doc_id: $source_doc_id, product_id: $product_id})
                    MATCH (target:Document {doc_id: $target_doc_id, product_id: $product_id})
                    MERGE (source)-[:RELATES_TO]->(target)
                    """,
                    source_doc_id=document["doc_id"],
                    target_doc_id=target,
                    product_id=binding["product_id"],
                )
    finally:
        driver.close()
    return {"status": "updated"}


def _load_config() -> tuple[dict | None, str | None]:
    try:
        from gitnexus_parser import load_config

        config = load_config()
    except Exception:
        return None, None
    database = (config.get("neo4j_database") or "").strip() or None
    return config, database


def _create_driver(config: dict):
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        config["neo4j_uri"],
        auth=(config.get("neo4j_user") or "neo4j", config.get("neo4j_password") or ""),
    )
