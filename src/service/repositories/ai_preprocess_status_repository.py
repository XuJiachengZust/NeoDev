"""AI 预处理任务状态仓储：并发控制与状态查询。"""

from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor


def has_running(conn, project_id: int, stale_minutes: int = 10) -> bool:
    """存在该 project_id 且 status='running' 则返回 True。

    超时保护：如果任务 updated_at 超过 stale_minutes 未更新（心跳超时），自动标记为 failed。
    这样可以区分：
    - git fetch 卡住（无心跳更新）→ 10 分钟后自动清理
    - AI 分析正常运行（定期更新进度）→ 可以运行几小时
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, project_id, branch, updated_at FROM ai_preprocess_status
             WHERE project_id = %s AND status = 'running'""",
            (project_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return False

        # 检查心跳是否超时（基于 updated_at）
        now = datetime.now(timezone.utc)
        for row in rows:
            updated_at = row.get("updated_at")
            if updated_at:
                elapsed = (now - updated_at).total_seconds() / 60
                if elapsed > stale_minutes:
                    # 心跳超时，自动标记为 failed
                    branch = row.get("branch", "unknown")
                    error_msg = f"任务无响应（超过 {stale_minutes} 分钟未更新心跳），已自动清理"
                    set_failed(conn, project_id, branch, error_msg)
                    conn.commit()
                    return False

        return True


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


def update_progress(conn, project_id: int, branch: str, progress: dict) -> None:
    """在任务运行过程中更新进度信息（extra.progress）。同时更新 updated_at 作为心跳。"""
    from psycopg2.extras import Json
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        # 运行中只关心进度信息，extra 最终会在 completed/failed 时被覆盖为完整统计。
        cur.execute(
            """UPDATE ai_preprocess_status
             SET extra = %s, updated_at = %s
             WHERE project_id = %s AND branch = %s""",
            (Json({"progress": progress}), now, project_id, branch),
        )


def update_heartbeat(conn, project_id: int, branch: str) -> None:
    """更新心跳时间戳（updated_at），表示任务仍在运行。"""
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE ai_preprocess_status
             SET updated_at = %s
             WHERE project_id = %s AND branch = %s AND status = 'running'""",
            (now, project_id, branch),
        )
