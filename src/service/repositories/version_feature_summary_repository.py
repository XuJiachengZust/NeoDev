"""版本功能总结仓储：CRUD 与状态管理。"""

from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor


def upsert_running(conn, product_version_id: int, project_id: int, branch: str) -> dict:
    """创建或重置为 running 状态，返回含 id 的记录。"""
    now = datetime.now(timezone.utc)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO version_feature_summaries
                   (product_version_id, project_id, branch, status, triggered_at, summary, error_message, finished_at)
               VALUES (%s, %s, %s, 'running', %s, NULL, NULL, NULL)
               ON CONFLICT (product_version_id, project_id) DO UPDATE SET
                   branch = EXCLUDED.branch,
                   status = 'running',
                   triggered_at = EXCLUDED.triggered_at,
                   summary = NULL,
                   error_message = NULL,
                   finished_at = NULL
               RETURNING id, product_version_id, project_id, branch, status, triggered_at""",
            (product_version_id, project_id, branch, now),
        )
        return dict(cur.fetchone())


def set_completed(conn, summary_id: int, summary_text: str) -> None:
    """设置为 completed，写入 summary 和 finished_at。"""
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE version_feature_summaries
               SET status = 'completed', summary = %s, finished_at = %s
               WHERE id = %s""",
            (summary_text, now, summary_id),
        )


def set_failed(conn, summary_id: int, error_message: str) -> None:
    """设置为 failed，写入 error_message 和 finished_at。"""
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE version_feature_summaries
               SET status = 'failed', error_message = %s, finished_at = %s
               WHERE id = %s""",
            (error_message, now, summary_id),
        )


def list_by_version(conn, product_version_id: int) -> list[dict]:
    """列出某产品版本下所有功能总结，JOIN projects 获取项目名。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT vfs.id, vfs.product_version_id, vfs.project_id, vfs.branch,
                      vfs.status, vfs.summary, vfs.error_message,
                      vfs.triggered_at, vfs.finished_at,
                      p.name AS project_name
               FROM version_feature_summaries vfs
               JOIN projects p ON p.id = vfs.project_id
               WHERE vfs.product_version_id = %s
               ORDER BY vfs.project_id""",
            (product_version_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, summary_id: int) -> dict | None:
    """获取单条总结详情。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT vfs.id, vfs.product_version_id, vfs.project_id, vfs.branch,
                      vfs.status, vfs.summary, vfs.error_message,
                      vfs.triggered_at, vfs.finished_at,
                      p.name AS project_name
               FROM version_feature_summaries vfs
               JOIN projects p ON p.id = vfs.project_id
               WHERE vfs.id = %s""",
            (summary_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def find_versions_for_project_branch(conn, project_id: int, branch: str) -> list[dict]:
    """通过 product_version_branches 反查关联的产品版本列表。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT pvb.product_version_id, pvb.branch
               FROM product_version_branches pvb
               WHERE pvb.project_id = %s AND pvb.branch = %s""",
            (project_id, branch),
        )
        return [dict(row) for row in cur.fetchall()]
