"""Branch snapshot orchestration for code fact visibility."""

from __future__ import annotations

from typing import Any

from service.repositories import branch_snapshot_repository as snapshot_repo
from service.repositories import code_fact_repository as code_fact_repo


def create_snapshot_from_code_facts(
    conn,
    *,
    project_id: int,
    branch: str,
    head_commit: str | None,
    snapshot_hash: str | None,
    code_facts: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_branch = (branch or "").strip()
    normalized_facts = [_with_project_id(fact, project_id) for fact in code_facts]
    code_fact_repo.upsert_many(conn, normalized_facts)
    snapshot = snapshot_repo.create_snapshot(
        conn,
        project_id=project_id,
        branch_name=normalized_branch,
        head_commit=head_commit,
        snapshot_hash=snapshot_hash,
        status="completed",
    )
    entry_count = snapshot_repo.replace_facts(
        conn,
        snapshot["id"],
        [fact["fact_id"] for fact in normalized_facts],
    )
    snapshot["entry_count"] = entry_count
    return snapshot


def get_current_snapshot(conn, project_id: int, branch: str) -> dict[str, Any] | None:
    return snapshot_repo.get_current_snapshot(conn, project_id, (branch or "").strip())


def list_fact_ids(conn, snapshot_id: int) -> list[str]:
    return snapshot_repo.list_fact_ids(conn, snapshot_id)


def list_code_facts(
    conn,
    snapshot_id: int,
    *,
    node_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    return code_fact_repo.list_by_snapshot(conn, snapshot_id, node_types=node_types)


def list_product_version_code_facts(
    conn,
    product_version_id: int,
    *,
    node_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    return code_fact_repo.list_by_product_version(conn, product_version_id, node_types=node_types)


def _with_project_id(fact: dict[str, Any], project_id: int) -> dict[str, Any]:
    row = dict(fact)
    row["project_id"] = project_id
    return row
