"""ImpactAnalysis aggregate: impact_analyses + impact_analysis_commits (Phase 3)."""

from psycopg2.extras import RealDictCursor


def create(conn, project_id: int, status: str = "pending") -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO impact_analyses (project_id, status)
             VALUES (%s, %s)
             RETURNING id, project_id, status, triggered_at, result_summary""",
            (project_id, status),
        )
        return dict(cur.fetchone())


def add_commits(conn, impact_analysis_id: int, commit_ids: list[int]) -> None:
    with conn.cursor() as cur:
        for cid in commit_ids:
            cur.execute(
                "INSERT INTO impact_analysis_commits (impact_analysis_id, commit_id) VALUES (%s, %s)",
                (impact_analysis_id, cid),
            )


def list_by_project_id(conn, project_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, project_id, status, triggered_at, result_summary
             FROM impact_analyses WHERE project_id = %s ORDER BY id DESC""",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, analysis_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, project_id, status, triggered_at, result_summary
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
