"""Branch snapshot metadata repository."""

from typing import Any

from psycopg2.extras import RealDictCursor, execute_values


_SNAPSHOT_COLUMNS = (
    "id, project_id, repo_id, branch, head_commit, last_parsed_commit, "
    "base_snapshot_id, created_from_action, status, created_at"
)

_ENTRY_COLUMNS = (
    "id, snapshot_id, project_id, repo_id, file_path, file_node_id, "
    "file_content_hash, visible, created_at"
)


def create_snapshot(
    conn,
    *,
    project_id: int,
    repo_id: int,
    branch: str,
    head_commit: str | None,
    last_parsed_commit: str | None,
    base_snapshot_id: int | None = None,
    created_from_action: str,
    status: str = "completed",
) -> dict[str, Any]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO branch_snapshots
                    (project_id, repo_id, branch, head_commit, last_parsed_commit,
                     base_snapshot_id, created_from_action, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING {_SNAPSHOT_COLUMNS}""",
            (
                project_id,
                repo_id,
                branch,
                head_commit,
                last_parsed_commit,
                base_snapshot_id,
                created_from_action,
                status,
            ),
        )
        return dict(cur.fetchone())


def replace_entries(conn, snapshot_id: int, entries: list[dict[str, Any]]) -> int:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM branch_snapshot_entries WHERE snapshot_id = %s", (snapshot_id,))
        if not entries:
            return 0
        values = [
            (
                snapshot_id,
                entry["project_id"],
                entry["repo_id"],
                entry["file_path"],
                entry["file_node_id"],
                entry["file_content_hash"],
                bool(entry.get("visible", True)),
            )
            for entry in entries
        ]
        execute_values(
            cur,
            """INSERT INTO branch_snapshot_entries
                    (snapshot_id, project_id, repo_id, file_path, file_node_id,
                     file_content_hash, visible)
               VALUES %s
               ON CONFLICT (snapshot_id, file_path) DO UPDATE SET
                    file_node_id = EXCLUDED.file_node_id,
                    file_content_hash = EXCLUDED.file_content_hash,
                    visible = EXCLUDED.visible""",
            values,
        )
        return len(values)


def copy_entries(
    conn,
    source_snapshot_id: int,
    target_snapshot_id: int,
    *,
    project_id: int,
    repo_id: int,
) -> int:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO branch_snapshot_entries
                    (snapshot_id, project_id, repo_id, file_path, file_node_id,
                     file_content_hash, visible)
               SELECT %s, %s, %s, file_path, file_node_id, file_content_hash, visible
               FROM branch_snapshot_entries
               WHERE snapshot_id = %s
               ON CONFLICT (snapshot_id, file_path) DO UPDATE SET
                    file_node_id = EXCLUDED.file_node_id,
                    file_content_hash = EXCLUDED.file_content_hash,
                    visible = EXCLUDED.visible
               RETURNING id""",
            (target_snapshot_id, project_id, repo_id, source_snapshot_id),
        )
        return len(cur.fetchall())


def get_current_snapshot(conn, project_id: int, branch: str) -> dict[str, Any] | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_SNAPSHOT_COLUMNS}
                FROM branch_snapshots
                WHERE project_id = %s AND branch = %s
                ORDER BY id DESC
                LIMIT 1""",
            (project_id, branch),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_entries(conn, snapshot_id: int, *, visible_only: bool = True) -> list[dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if visible_only:
            cur.execute(
                f"""SELECT {_ENTRY_COLUMNS}
                    FROM branch_snapshot_entries
                    WHERE snapshot_id = %s AND visible = true
                    ORDER BY file_path""",
                (snapshot_id,),
            )
        else:
            cur.execute(
                f"""SELECT {_ENTRY_COLUMNS}
                    FROM branch_snapshot_entries
                    WHERE snapshot_id = %s
                    ORDER BY file_path""",
                (snapshot_id,),
            )
        return [dict(row) for row in cur.fetchall()]
