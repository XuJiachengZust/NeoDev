"""PG repository for document-to-code fact links."""

from __future__ import annotations

from typing import Any

from psycopg2.extras import Json, RealDictCursor

_COLUMNS = (
    "id, product_id, product_version_id, doc_id, doc_node_id, code_project_id, "
    "symbol_key, resolved_fact_id, resolved_snapshot_id, relation_type, source, "
    "confidence, resolution_status, metadata_json, status, created_at, updated_at"
)


def create(
    conn,
    *,
    product_id: int,
    product_version_id: int | None,
    doc_id: str,
    doc_node_id: str | None,
    code_project_id: int,
    symbol_key: str,
    relation_type: str,
    source: str = "manual",
    confidence: float | None = None,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            INSERT INTO doc_code_links (
                product_id, product_version_id, doc_id, doc_node_id,
                code_project_id, symbol_key, relation_type, source,
                confidence, metadata_json
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING {_COLUMNS}
            """,
            (
                product_id,
                product_version_id,
                doc_id,
                doc_node_id,
                code_project_id,
                symbol_key,
                relation_type,
                source,
                confidence,
                Json(metadata_json or {}),
            ),
        )
        return dict(cur.fetchone())


def list_by_product_version_doc(conn, product_version_id: int, doc_id: str) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {_COLUMNS}
            FROM doc_code_links
            WHERE product_version_id = %s
              AND doc_id = %s
              AND status = 'active'
            ORDER BY id
            """,
            (product_version_id, doc_id),
        )
        return [dict(row) for row in cur.fetchall()]


def get_product_version_branch(conn, product_version_id: int, project_id: int) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT product_version_id, project_id, branch_name
            FROM product_version_branches
            WHERE product_version_id = %s
              AND project_id = %s
            """,
            (product_version_id, project_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_active_for_branch_snapshot(
    conn,
    *,
    project_id: int,
    product_version_ids: list[int],
) -> list[dict[str, Any]]:
    params: list[Any] = [project_id]
    version_clause = "AND product_version_id IS NULL"
    if product_version_ids:
        version_clause = "AND (product_version_id IS NULL OR product_version_id = ANY(%s))"
        params.append(product_version_ids)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT id, product_id, product_version_id, doc_id, doc_node_id,
                   code_project_id, symbol_key, resolved_fact_id,
                   resolved_snapshot_id, relation_type, source, confidence,
                   resolution_status, metadata_json, status, created_at, updated_at
            FROM doc_code_links
            WHERE code_project_id = %s
              AND status = 'active'
              {version_clause}
            ORDER BY id
            """,
            params,
        )
        return [dict(row) for row in cur.fetchall()]


def set_resolution(
    conn,
    *,
    link_id: int,
    resolved_fact_id: str | None,
    resolved_snapshot_id: int | None,
    resolution_status: str,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE doc_code_links
            SET resolved_fact_id = %s,
                resolved_snapshot_id = %s,
                resolution_status = %s,
                metadata_json = COALESCE(%s, metadata_json),
                updated_at = now()
            WHERE id = %s
            RETURNING id, product_id, product_version_id, doc_id, doc_node_id,
                      code_project_id, symbol_key, resolved_fact_id,
                      resolved_snapshot_id, relation_type, source, confidence,
                      resolution_status, metadata_json, status, created_at, updated_at
            """,
            (resolved_fact_id, resolved_snapshot_id, resolution_status, Json(metadata_json) if metadata_json is not None else None, link_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_product_version_ids_for_project_branch(conn, *, project_id: int, branch_name: str) -> list[int]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT product_version_id
            FROM product_version_branches
            WHERE project_id = %s AND branch_name = %s
            ORDER BY product_version_id
            """,
            (project_id, branch_name),
        )
        return [int(row["product_version_id"]) for row in cur.fetchall()]
