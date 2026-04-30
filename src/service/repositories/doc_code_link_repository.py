"""PG repository for document-to-code binding indexes."""

from __future__ import annotations

from typing import Any

from psycopg2.extras import Json, RealDictCursor


_COLUMNS = (
    "id, product_version_id, project_id, branch_name, doc_id, doc_node_id, "
    "relation_type, code_locator_json, code_locator_hash, resolved_graph_id, "
    "resolved_node_id, resolution_status, status, source, confidence, "
    "created_at, updated_at, deleted_at"
)


def upsert_active(
    conn,
    *,
    product_version_id: int,
    project_id: int,
    branch_name: str,
    doc_id: str,
    doc_node_id: str | None,
    relation_type: str,
    code_locator_json: dict[str, Any],
    code_locator_hash: str,
    resolved_graph_id: int | None = None,
    resolved_node_id: str | None = None,
    resolution_status: str = "pending",
    source: str = "manual",
    confidence: float | None = None,
) -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            INSERT INTO doc_code_links (
                product_version_id, project_id, branch_name, doc_id, doc_node_id,
                relation_type, code_locator_json, code_locator_hash,
                resolved_graph_id, resolved_node_id, resolution_status,
                status, source, confidence
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'active', %s, %s)
            ON CONFLICT (
                product_version_id, project_id, branch_name, doc_node_id, relation_type, code_locator_hash
            )
            WHERE status = 'active'
            DO UPDATE SET doc_id = EXCLUDED.doc_id,
                          code_locator_json = EXCLUDED.code_locator_json,
                          resolved_graph_id = EXCLUDED.resolved_graph_id,
                          resolved_node_id = EXCLUDED.resolved_node_id,
                          resolution_status = EXCLUDED.resolution_status,
                          source = EXCLUDED.source,
                          confidence = EXCLUDED.confidence,
                          updated_at = now()
            RETURNING {_COLUMNS}
            """,
            (
                product_version_id,
                project_id,
                branch_name,
                doc_id,
                doc_node_id,
                relation_type,
                Json(code_locator_json),
                code_locator_hash,
                resolved_graph_id,
                resolved_node_id,
                resolution_status,
                source,
                confidence,
            ),
        )
        return dict(cur.fetchone())


def mark_inactive(conn, *, link_id: int) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            UPDATE doc_code_links
            SET status = 'inactive',
                deleted_at = COALESCE(deleted_at, now()),
                updated_at = now()
            WHERE id = %s AND status = 'active'
            RETURNING {_COLUMNS}
            """,
            (link_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_active_for_branch(conn, *, project_id: int, branch_name: str) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {_COLUMNS}
            FROM doc_code_links
            WHERE project_id = %s
              AND branch_name = %s
              AND status = 'active'
            ORDER BY id
            """,
            (project_id, branch_name),
        )
        return [dict(row) for row in cur.fetchall()]
