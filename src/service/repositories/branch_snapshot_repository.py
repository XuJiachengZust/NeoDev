"""Branch snapshot repository for code fact visibility."""

from __future__ import annotations

from typing import Any

from psycopg2.extras import RealDictCursor, execute_values


_SNAPSHOT_COLUMNS = "id, project_id, branch_name, head_commit, snapshot_hash, status, created_at"


def create_snapshot(
    conn,
    *,
    project_id: int,
    branch_name: str,
    head_commit: str | None,
    snapshot_hash: str | None,
    status: str = "completed",
) -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO branch_snapshots
                    (project_id, branch_name, head_commit, snapshot_hash, status)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING {_SNAPSHOT_COLUMNS}""",
            (project_id, branch_name, head_commit, snapshot_hash, status),
        )
        return dict(cur.fetchone())


def get_current_snapshot(conn, project_id: int, branch_name: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_SNAPSHOT_COLUMNS}
                FROM branch_snapshots
                WHERE project_id = %s
                  AND branch_name = %s
                  AND status = 'completed'
                ORDER BY id DESC
                LIMIT 1""",
            (project_id, branch_name),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def replace_facts(conn, snapshot_id: int, fact_ids: list[str]) -> int:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM branch_snapshot_facts WHERE snapshot_id = %s", (snapshot_id,))
        if not fact_ids:
            return 0
        values = [(snapshot_id, fact_id) for fact_id in sorted(set(fact_ids))]
        execute_values(
            cur,
            """INSERT INTO branch_snapshot_facts (snapshot_id, fact_id)
               VALUES %s
               ON CONFLICT (snapshot_id, fact_id) DO NOTHING""",
            values,
        )
    return len(values)


def list_fact_ids(conn, snapshot_id: int) -> list[str]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT fact_id
               FROM branch_snapshot_facts
               WHERE snapshot_id = %s
               ORDER BY fact_id""",
            (snapshot_id,),
        )
        return [str(row["fact_id"]) for row in cur.fetchall()]
