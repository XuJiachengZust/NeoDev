"""Document graph writer for Neo4j document-level facts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from service.repositories import project_repository


def upsert_document_graph(conn, *, binding: dict, document: dict) -> dict[str, Any]:
    config, database = _load_config()
    if not config or not config.get("neo4j_uri"):
        return {"status": "not_configured"}
    project = resolve_document_project(conn, binding)
    driver = _create_driver(config)
    try:
        with driver.session(database=database) as session:
            session.run(
                """
                MERGE (d:Document {doc_id: $doc_id, product_id: $product_id})
                SET d.document_id = $document_id,
                    d.doc_binding_id = $doc_binding_id,
                    d.product_version_id = $product_version_id,
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
                product_version_id=binding.get("product_version_id"),
                doc_id=document["doc_id"],
                title=document.get("title") or "",
                doc_type=document.get("doc_type") or "",
                relative_path=document.get("relative_path") or "",
                status=document.get("status") or "active",
                content_hash=document.get("content_hash") or "",
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            if project:
                session.run(
                    """
                    MATCH (d:Document {doc_id: $doc_id, product_id: $product_id})
                    MERGE (p:Project {project_id: $project_id})
                    SET p.id = coalesce(p.id, $project_node_id),
                        p.name = coalesce(p.name, $project_name, $project_node_id),
                        p.repo_path = coalesce(p.repo_path, $project_repo_path),
                        p.repo_url = coalesce(p.repo_url, $project_repo_url),
                        p.product_id = coalesce(p.product_id, $product_id),
                        d.project_id = $project_id,
                        d.product_version_id = $product_version_id
                    MERGE (p)-[r:HAS_DOCUMENT {
                        doc_binding_id: $doc_binding_id,
                        doc_id: $doc_id
                    }]->(d)
                    SET r.product_id = $product_id,
                        r.project_id = $project_id,
                        r.document_id = $document_id,
                        r.product_version_id = $product_version_id,
                        r.relative_path = $relative_path,
                        r.updated_at = $updated_at
                    """,
                    project_id=project["id"],
                    project_node_id=f"project:{project['id']}",
                    project_name=project.get("name") or f"project:{project['id']}",
                    project_repo_path=project.get("repo_path") or "",
                    project_repo_url=project.get("repo_url") or "",
                    document_id=document["id"],
                    doc_binding_id=binding["id"],
                    product_id=binding["product_id"],
                    product_version_id=binding.get("product_version_id"),
                    doc_id=document["doc_id"],
                    relative_path=document.get("relative_path") or "",
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
    return {"status": "updated", "project_id": project["id"] if project else None}


def resolve_document_project(conn, binding: dict) -> dict | None:
    binding_product_id = binding.get("product_id")
    binding_repo_url = _normalized_text(binding.get("repo_url"))
    binding_repo_path = _normalized_text(binding.get("repo_path"))
    binding_repo_name = _repo_name(binding_repo_path)
    candidates = project_repository.list_all(conn)
    for project in candidates:
        if binding_product_id is not None and project.get("product_id") != binding_product_id:
            continue
        project_repo_url = _normalized_text(project.get("repo_url"))
        project_repo_path = _normalized_text(project.get("repo_path"))
        if binding_repo_url and binding_repo_url in {project_repo_url, project_repo_path}:
            return project
        if binding_repo_path and binding_repo_path in {project_repo_url, project_repo_path}:
            return project
        if binding_repo_name and _normalized_text(project.get("name")) == binding_repo_name:
            return project
    return None


def _normalized_text(value: Any) -> str:
    return str(value or "").strip()


def _repo_name(path_or_url: str) -> str:
    text = _normalized_text(path_or_url).rstrip("/\\")
    if not text:
        return ""
    text = text[:-4] if text.endswith(".git") else text
    posix_name = PurePosixPath(text.replace("\\", "/")).name
    windows_name = PureWindowsPath(text).name
    return (posix_name or windows_name).strip()


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
