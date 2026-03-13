"""ImpactAnalysis aggregate: impact_analyses + impact_analysis_commits (Phase 3)."""

from psycopg2.extras import RealDictCursor

_COLUMNS = "id, project_id, version_id, status, title, triggered_at, result_summary"


def create(conn, project_id: int, status: str = "pending", version_id: int | None = None) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO impact_analyses (project_id, status, version_id)
             VALUES (%s, %s, %s)
             RETURNING {_COLUMNS}""",
            (project_id, status, version_id),
        )
        return dict(cur.fetchone())


def add_commits(conn, impact_analysis_id: int, commit_ids: list[int]) -> None:
    with conn.cursor() as cur:
        for cid in commit_ids:
            cur.execute(
                "INSERT INTO impact_analysis_commits (impact_analysis_id, commit_id) VALUES (%s, %s)",
                (impact_analysis_id, cid),
            )


def update_result(
    conn,
    analysis_id: int,
    status: str,
    title: str | None = None,
    result_summary: str | None = None,
) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE impact_analyses
               SET status = %s, title = %s, result_summary = %s
               WHERE id = %s
               RETURNING {_COLUMNS}""",
            (status, title, result_summary, analysis_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_by_project_id(conn, project_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_COLUMNS}
             FROM impact_analyses WHERE project_id = %s ORDER BY id DESC""",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def list_by_product(conn, product_id: int) -> list[dict]:
    """查询产品下所有项目的影响面分析报告。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT ia.id, ia.project_id, ia.version_id, ia.status, ia.title,
                       ia.triggered_at, ia.result_summary,
                       p.name AS project_name,
                       v.version_name AS version_name,
                       (SELECT count(*) FROM impact_analysis_commits iac
                        WHERE iac.impact_analysis_id = ia.id) AS commit_count
                FROM impact_analyses ia
                JOIN projects p ON p.id = ia.project_id
                LEFT JOIN versions v ON v.id = ia.version_id
                WHERE p.product_id = %s
                ORDER BY ia.id DESC""",
            (product_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, analysis_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_COLUMNS}
             FROM impact_analyses WHERE id = %s""",
            (analysis_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_commit_ids(conn, impact_analysis_id: int) -> list[int]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT commit_id FROM impact_analysis_commits WHERE impact_analysis_id = %s",
            (impact_analysis_id,),
        )
        return [row[0] for row in cur.fetchall()]
