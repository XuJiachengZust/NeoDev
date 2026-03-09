"""AI 预处理任务状态仓储：并发控制与状态查询。"""

from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor


def has_running(conn, project_id: int) -> bool:
    """存在该 project_id 且 status='running' 则返回 True。"""
    with conn.cursor() as cur:
        cur.execute(
            """SELECT 1 FROM ai_preprocess_status
             WHERE project_id = %s AND status = 'running' LIMIT 1""",
            (project_id,),
        )
        return cur.fetchone() is not None


def set_running(conn, project_id: int, branch: str) -> bool:
    """若 has_running 为 True 则返回 False；否则 upsert (project_id, branch) 为 running，返回 True。"""
    if has_running(conn, project_id):
        return False
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO ai_preprocess_status (project_id, branch, status, started_at, updated_at)
             VALUES (%s, %s, 'running', %s, %s)
             ON CONFLICT (project_id, branch) DO UPDATE SET
               status = 'running', started_at = EXCLUDED.started_at,
               finished_at = NULL, error_message = NULL, extra = NULL,
               updated_at = EXCLUDED.updated_at""",
            (project_id, branch, now, now),
        )
    return True


def set_completed(conn, project_id: int, branch: str, extra: dict | None = None) -> None:
    """更新为 completed、finished_at、extra。"""
    from psycopg2.extras import Json
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE ai_preprocess_status
             SET status = 'completed', finished_at = %s, extra = %s, updated_at = %s
             WHERE project_id = %s AND branch = %s""",
            (now, Json(extra) if extra else None, now, project_id, branch),
        )


def set_failed(
    conn, project_id: int, branch: str, error_message: str, extra: dict | None = None
) -> None:
    """更新为 failed、finished_at、error_message；可选写入 extra（如过程日志）。"""
    from psycopg2.extras import Json
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        if extra is not None:
            cur.execute(
                """UPDATE ai_preprocess_status
                 SET status = 'failed', finished_at = %s, error_message = %s, extra = %s, updated_at = %s
                 WHERE project_id = %s AND branch = %s""",
                (now, error_message, Json(extra), now, project_id, branch),
            )
        else:
            cur.execute(
                """UPDATE ai_preprocess_status
                 SET status = 'failed', finished_at = %s, error_message = %s, updated_at = %s
                 WHERE project_id = %s AND branch = %s""",
                (now, error_message, now, project_id, branch),
            )


def get_status(conn, project_id: int, branch: str | None = None) -> list[dict]:
    """按 project_id 或 (project_id, branch) 查询最近记录。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if branch is not None:
            cur.execute(
                """SELECT id, project_id, branch, status, started_at, finished_at,
                          error_message, extra, created_at, updated_at
                   FROM ai_preprocess_status
                   WHERE project_id = %s AND branch = %s""",
                (project_id, branch),
            )
        else:
            cur.execute(
                """SELECT id, project_id, branch, status, started_at, finished_at,
                          error_message, extra, created_at, updated_at
                   FROM ai_preprocess_status
                   WHERE project_id = %s
                   ORDER BY branch""",
                (project_id,),
            )
        rows = cur.fetchall()
    return [dict(r) for r in rows]
