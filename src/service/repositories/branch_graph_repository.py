"""PostgreSQL metadata for current project branch graphs."""

from __future__ import annotations

from typing import Any

from psycopg2.extras import Json, RealDictCursor


_GRAPH_COLUMNS = (
    "id, project_id, branch_name, head_commit, graph_hash, status, "
    "node_count, edge_count, error_message, refreshed_at, created_at, updated_at"
)


def get_by_project_branch(conn, project_id: int, branch_name: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT {_GRAPH_COLUMNS}
            FROM branch_graphs
            WHERE project_id = %s AND branch_name = %s
            """,
            (project_id, branch_name),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def upsert(conn, *, project_id: int, branch_name: str, status: str = "running") -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            INSERT INTO branch_graphs (project_id, branch_name, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (project_id, branch_name)
            DO UPDATE SET status = EXCLUDED.status,
                          error_message = NULL,
                          updated_at = now()
            RETURNING {_GRAPH_COLUMNS}
            """,
            (project_id, branch_name, status),
        )
        return dict(cur.fetchone())


def mark_ready(
    conn,
    *,
    graph_id: int,
    head_commit: str | None,
    graph_hash: str | None,
    node_count: int,
    edge_count: int,
) -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            UPDATE branch_graphs
            SET head_commit = %s,
                graph_hash = %s,
                status = 'ready',
                node_count = %s,
                edge_count = %s,
                error_message = NULL,
                refreshed_at = now(),
                updated_at = now()
            WHERE id = %s
            RETURNING {_GRAPH_COLUMNS}
            """,
            (head_commit, graph_hash, node_count, edge_count, graph_id),
        )
        return dict(cur.fetchone())


def mark_failed(conn, *, graph_id: int, error_message: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            UPDATE branch_graphs
            SET status = 'failed',
                error_message = %s,
                updated_at = now()
            WHERE id = %s
            RETURNING {_GRAPH_COLUMNS}
            """,
            (error_message, graph_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def start_refresh_run(
    conn,
    *,
    graph_id: int,
    project_id: int,
    branch_name: str,
    head_commit_before: str | None,
) -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO graph_refresh_runs (
                graph_id, project_id, branch_name, status, head_commit_before
            )
            VALUES (%s, %s, %s, 'running', %s)
            RETURNING id, graph_id, project_id, branch_name, started_at,
                      finished_at, status, head_commit_before, head_commit_after,
                      node_count, edge_count, error_message, metadata_json
            """,
            (graph_id, project_id, branch_name, head_commit_before),
        )
        return dict(cur.fetchone())


def complete_refresh_run(
    conn,
    *,
    run_id: int,
    head_commit_after: str | None,
    node_count: int,
    edge_count: int,
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE graph_refresh_runs
            SET status = 'completed',
                finished_at = now(),
                head_commit_after = %s,
                node_count = %s,
                edge_count = %s,
                metadata_json = %s
            WHERE id = %s
            RETURNING id, graph_id, project_id, branch_name, started_at,
                      finished_at, status, head_commit_before, head_commit_after,
                      node_count, edge_count, error_message, metadata_json
            """,
            (head_commit_after, node_count, edge_count, Json(metadata_json or {}), run_id),
        )
        return dict(cur.fetchone())


def fail_refresh_run(conn, *, run_id: int, error_message: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE graph_refresh_runs
            SET status = 'failed',
                finished_at = now(),
                error_message = %s
            WHERE id = %s
            RETURNING id, graph_id, project_id, branch_name, started_at,
                      finished_at, status, head_commit_before, head_commit_after,
                      node_count, edge_count, error_message, metadata_json
            """,
            (error_message, run_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
