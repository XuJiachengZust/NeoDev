"""Branch analysis task status repository."""

from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor


TABLE_NAME = "branch_analysis_status"


def has_running(conn, project_id: int, stale_minutes: int = 10) -> bool:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT id, project_id, branch, updated_at FROM {TABLE_NAME}
             WHERE project_id = %s AND status = 'running'""",
            (project_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return False

        now = datetime.now(timezone.utc)
        for row in rows:
            updated_at = row.get("updated_at")
            if updated_at:
                elapsed = (now - updated_at).total_seconds() / 60
                if elapsed > stale_minutes:
                    branch = row.get("branch", "unknown")
                    set_failed(
                        conn,
                        project_id,
                        branch,
                        f"analysis task timed out after {stale_minutes} minutes",
                    )
                    conn.commit()
                    return False

        return True


def set_running(conn, project_id: int, branch: str) -> bool:
    if has_running(conn, project_id):
        return False
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            f"""INSERT INTO {TABLE_NAME} (project_id, branch, status, started_at, updated_at)
             VALUES (%s, %s, 'running', %s, %s)
             ON CONFLICT (project_id, branch) DO UPDATE SET
               status = 'running', started_at = EXCLUDED.started_at,
               finished_at = NULL, error_message = NULL, extra = NULL,
               updated_at = EXCLUDED.updated_at""",
            (project_id, branch, now, now),
        )
    return True


def set_completed(conn, project_id: int, branch: str, extra: dict | None = None) -> None:
    from psycopg2.extras import Json

    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            f"""UPDATE {TABLE_NAME}
             SET status = 'completed', finished_at = %s, extra = %s, updated_at = %s
             WHERE project_id = %s AND branch = %s""",
            (now, Json(extra) if extra else None, now, project_id, branch),
        )


def set_failed(
    conn, project_id: int, branch: str, error_message: str, extra: dict | None = None
) -> None:
    from psycopg2.extras import Json

    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        if extra is not None:
            cur.execute(
                f"""UPDATE {TABLE_NAME}
                 SET status = 'failed', finished_at = %s, error_message = %s, extra = %s, updated_at = %s
                 WHERE project_id = %s AND branch = %s""",
                (now, error_message, Json(extra), now, project_id, branch),
            )
        else:
            cur.execute(
                f"""UPDATE {TABLE_NAME}
                 SET status = 'failed', finished_at = %s, error_message = %s, updated_at = %s
                 WHERE project_id = %s AND branch = %s""",
                (now, error_message, now, project_id, branch),
            )


def get_status(conn, project_id: int, branch: str | None = None) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if branch is not None:
            cur.execute(
                f"""SELECT id, project_id, branch, status, started_at, finished_at,
                          error_message, extra, created_at, updated_at
                   FROM {TABLE_NAME}
                   WHERE project_id = %s AND branch = %s""",
                (project_id, branch),
            )
        else:
            cur.execute(
                f"""SELECT id, project_id, branch, status, started_at, finished_at,
                          error_message, extra, created_at, updated_at
                   FROM {TABLE_NAME}
                   WHERE project_id = %s
                   ORDER BY branch""",
                (project_id,),
            )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def update_progress(conn, project_id: int, branch: str, progress: dict) -> None:
    from psycopg2.extras import Json

    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            f"""UPDATE {TABLE_NAME}
             SET extra = %s, updated_at = %s
             WHERE project_id = %s AND branch = %s""",
            (Json({"progress": progress}), now, project_id, branch),
        )


def update_heartbeat(conn, project_id: int, branch: str) -> None:
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            f"""UPDATE {TABLE_NAME}
             SET updated_at = %s
             WHERE project_id = %s AND branch = %s AND status = 'running'""",
            (now, project_id, branch),
        )
