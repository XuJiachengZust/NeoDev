"""Resolve document-to-code links against branch snapshots."""

from __future__ import annotations

from service.repositories import code_fact_repository
from service.repositories import doc_code_link_repository as repo


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


def _resolution_metadata(candidates: list[dict]) -> dict:
    return {
        "candidate_fact_ids": [item["fact_id"] for item in candidates[:20]],
        "candidate_count": len(candidates),
    }
