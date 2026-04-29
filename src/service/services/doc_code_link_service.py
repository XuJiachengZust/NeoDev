"""Resolve document-to-code links against branch snapshots."""

from __future__ import annotations

from service.repositories import code_fact_repository
from service.repositories import doc_code_link_repository as repo
from service.services import branch_snapshot_service

_RELATION_TYPES = {
    "DESCRIBES",
    "REQUIRES",
    "IMPLEMENTS",
    "VALIDATES",
    "TESTS",
    "DEPENDS_ON",
}


def create_link(
    conn,
    *,
    product_id: int,
    product_version_id: int | None,
    doc_id: str,
    doc_node_id: str | None = None,
    code_project_id: int,
    symbol_key: str,
    relation_type: str,
    source: str = "manual",
    confidence: float | None = None,
    metadata_json: dict | None = None,
) -> dict:
    normalized_relation_type = _normalize_relation_type(relation_type)
    link = repo.create(
        conn,
        product_id=product_id,
        product_version_id=product_version_id,
        doc_id=_required_text(doc_id, "doc_id"),
        doc_node_id=doc_node_id,
        code_project_id=code_project_id,
        symbol_key=_required_text(symbol_key, "symbol_key"),
        relation_type=normalized_relation_type,
        source=source,
        confidence=confidence,
        metadata_json=metadata_json,
    )
    if product_version_id is None:
        return link
    return _resolve_link(conn, link) or link


def list_code_facts_for_doc(conn, *, product_version_id: int, doc_id: str) -> dict:
    links = repo.list_by_product_version_doc(conn, product_version_id, _required_text(doc_id, "doc_id"))
    code_facts: list[dict] = []
    resolved = 0
    stale = 0
    ambiguous = 0
    for link in links:
        resolution = _resolve_link(conn, link)
        status = (resolution or link).get("resolution_status")
        if status == "resolved":
            candidates = _visible_candidates_for_link(conn, link)
            if len(candidates) == 1:
                code_facts.append(candidates[0])
                resolved += 1
        elif status == "ambiguous":
            ambiguous += 1
        else:
            stale += 1
    return {
        "product_version_id": product_version_id,
        "doc_id": doc_id,
        "links_checked": len(links),
        "resolved": resolved,
        "stale": stale,
        "ambiguous": ambiguous,
        "code_facts": code_facts,
    }


def rebuild_links_for_branch_snapshot(
    conn,
    *,
    project_id: int,
    branch_name: str,
    snapshot_id: int,
) -> dict:
    """Resolve active doc-code links after a branch graph rebuild."""
    product_version_ids = repo.list_product_version_ids_for_project_branch(
        conn,
        project_id=project_id,
        branch_name=branch_name,
    )
    links = repo.list_active_for_branch_snapshot(
        conn,
        project_id=project_id,
        product_version_ids=product_version_ids,
    )
    resolved = 0
    stale = 0
    ambiguous = 0
    for link in links:
        candidates = code_fact_repository.list_visible_by_symbol(
            conn,
            snapshot_id=snapshot_id,
            project_id=project_id,
            symbol_key=link["symbol_key"],
        )
        if len(candidates) == 1:
            repo.set_resolution(
                conn,
                link_id=link["id"],
                resolved_fact_id=candidates[0]["fact_id"],
                resolved_snapshot_id=snapshot_id,
                resolution_status="resolved",
                metadata_json=_resolution_metadata(candidates),
            )
            resolved += 1
        elif len(candidates) > 1:
            repo.set_resolution(
                conn,
                link_id=link["id"],
                resolved_fact_id=None,
                resolved_snapshot_id=snapshot_id,
                resolution_status="ambiguous",
                metadata_json=_resolution_metadata(candidates),
            )
            ambiguous += 1
        else:
            repo.set_resolution(
                conn,
                link_id=link["id"],
                resolved_fact_id=None,
                resolved_snapshot_id=snapshot_id,
                resolution_status="stale",
                metadata_json={"reason": "symbol_not_visible_in_snapshot"},
            )
            stale += 1
    return {
        "links_checked": len(links),
        "resolved": resolved,
        "stale": stale,
        "ambiguous": ambiguous,
        "product_version_ids": product_version_ids,
    }


def _resolve_link(conn, link: dict) -> dict | None:
    product_version_id = link.get("product_version_id")
    if product_version_id is None:
        return None
    candidates = _visible_candidates_for_link(conn, link)
    snapshot = _current_snapshot_for_link(conn, link)
    snapshot_id = snapshot.get("id") if snapshot else None
    if len(candidates) == 1:
        return repo.set_resolution(
            conn,
            link_id=link["id"],
            resolved_fact_id=candidates[0]["fact_id"],
            resolved_snapshot_id=snapshot_id,
            resolution_status="resolved",
            metadata_json=_resolution_metadata(candidates),
        )
    if len(candidates) > 1:
        return repo.set_resolution(
            conn,
            link_id=link["id"],
            resolved_fact_id=None,
            resolved_snapshot_id=snapshot_id,
            resolution_status="ambiguous",
            metadata_json=_resolution_metadata(candidates),
        )
    return repo.set_resolution(
        conn,
        link_id=link["id"],
        resolved_fact_id=None,
        resolved_snapshot_id=snapshot_id,
        resolution_status="stale",
        metadata_json={"reason": "symbol_not_visible_in_snapshot"},
    )


def _visible_candidates_for_link(conn, link: dict) -> list[dict]:
    snapshot = _current_snapshot_for_link(conn, link)
    if not snapshot:
        return []
    return code_fact_repository.list_visible_by_symbol(
        conn,
        snapshot_id=snapshot["id"],
        project_id=link["code_project_id"],
        symbol_key=link["symbol_key"],
    )


def _current_snapshot_for_link(conn, link: dict) -> dict | None:
    binding = repo.get_product_version_branch(
        conn,
        link["product_version_id"],
        link["code_project_id"],
    )
    if not binding:
        return None
    return branch_snapshot_service.get_current_snapshot(
        conn,
        link["code_project_id"],
        binding["branch_name"],
    )


def _resolution_metadata(candidates: list[dict]) -> dict:
    return {
        "candidate_fact_ids": [item["fact_id"] for item in candidates[:20]],
        "candidate_count": len(candidates),
    }


def _normalize_relation_type(value: str) -> str:
    normalized = _required_text(value, "relation_type").upper()
    if normalized not in _RELATION_TYPES:
        raise ValueError(f"unsupported relation_type: {value}")
    return normalized


def _required_text(value: str | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    return text
