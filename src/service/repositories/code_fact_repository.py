"""PG repository for project-level code facts."""

from __future__ import annotations

from typing import Any

from psycopg2.extras import Json, RealDictCursor, execute_values


_COLUMNS = (
    "id, project_id, fact_id, symbol_key, node_type, file_path, "
    "qualified_name, name, signature_hash, content_hash, structure_hash, "
    "parent_fact_id, start_line, end_line, metadata_json, status, created_at, updated_at"
)


def _columns(alias: str = "cf") -> str:
    return ", ".join(f"{alias}.{column.strip()}" for column in _COLUMNS.split(","))


def upsert_many(conn, facts: list[dict[str, Any]]) -> int:
    if not facts:
        return 0
    values = [
        (
            fact["project_id"],
            fact["fact_id"],
            fact["symbol_key"],
            fact["node_type"],
            fact.get("file_path"),
            fact.get("qualified_name"),
            fact.get("name"),
            fact.get("signature_hash"),
            fact.get("content_hash"),
            fact.get("structure_hash"),
            fact.get("parent_fact_id"),
            fact.get("start_line"),
            fact.get("end_line"),
            Json(fact.get("metadata_json") or {}),
            fact.get("status") or "active",
        )
        for fact in facts
    ]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO code_facts (
                project_id, fact_id, symbol_key, node_type, file_path,
                qualified_name, name, signature_hash, content_hash, structure_hash,
                parent_fact_id, start_line, end_line, metadata_json, status
            )
            VALUES %s
            ON CONFLICT (project_id, fact_id)
            DO UPDATE SET symbol_key = EXCLUDED.symbol_key,
                          node_type = EXCLUDED.node_type,
                          file_path = EXCLUDED.file_path,
                          qualified_name = EXCLUDED.qualified_name,
                          name = EXCLUDED.name,
                          signature_hash = EXCLUDED.signature_hash,
                          content_hash = EXCLUDED.content_hash,
                          structure_hash = EXCLUDED.structure_hash,
                          parent_fact_id = EXCLUDED.parent_fact_id,
                          start_line = EXCLUDED.start_line,
                          end_line = EXCLUDED.end_line,
                          metadata_json = EXCLUDED.metadata_json,
                          status = EXCLUDED.status,
                          updated_at = now()
            """,
            values,
        )
    return len(values)


def list_by_snapshot(conn, snapshot_id: int, *, node_types: list[str] | None = None) -> list[dict[str, Any]]:
    params: list[Any] = [snapshot_id]
    type_filter = ""
    if node_types:
        type_filter = "AND cf.node_type = ANY(%s)"
        params.append(node_types)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {_columns("cf")}
            FROM branch_snapshot_facts bsf
            JOIN branch_snapshots bs ON bs.id = bsf.snapshot_id
            JOIN code_facts cf ON cf.project_id = bs.project_id AND cf.fact_id = bsf.fact_id
            WHERE bsf.snapshot_id = %s
              {type_filter}
            ORDER BY cf.file_path, cf.start_line NULLS LAST, cf.name
            """,
            params,
        )
        return [dict(row) for row in cur.fetchall()]


def list_visible_by_symbol(conn, *, snapshot_id: int, project_id: int, symbol_key: str) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {_columns("cf")}
            FROM branch_snapshot_facts bsf
            JOIN code_facts cf ON cf.fact_id = bsf.fact_id
            WHERE bsf.snapshot_id = %s
              AND cf.project_id = %s
              AND cf.symbol_key = %s
              AND cf.status = 'active'
            ORDER BY cf.id DESC
            """,
            (snapshot_id, project_id, symbol_key),
        )
        return [dict(row) for row in cur.fetchall()]


def list_by_product_version(
    conn,
    product_version_id: int,
    node_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    params: list[Any] = [product_version_id]
    type_filter = ""
    if node_types:
        type_filter = "AND cf.node_type = ANY(%s)"
        params.append(node_types)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {_columns("cf")},
                   pvb.branch_name,
                   latest_snapshot.id AS snapshot_id,
                   latest_snapshot.head_commit
            FROM product_version_branches pvb
            JOIN LATERAL (
                SELECT id, project_id, branch_name, head_commit
                FROM branch_snapshots
                WHERE project_id = pvb.project_id
                  AND branch_name = pvb.branch_name
                  AND status = 'completed'
                ORDER BY id DESC
                LIMIT 1
            ) latest_snapshot ON TRUE
            JOIN branch_snapshot_facts bsf ON bsf.snapshot_id = latest_snapshot.id
            JOIN code_facts cf
              ON cf.project_id = pvb.project_id
             AND cf.fact_id = bsf.fact_id
            WHERE pvb.product_version_id = %s
              AND cf.status = 'active'
              {type_filter}
            ORDER BY pvb.project_id, cf.file_path, cf.start_line NULLS LAST, cf.name
            """,
            params,
        )
        return [dict(row) for row in cur.fetchall()]
