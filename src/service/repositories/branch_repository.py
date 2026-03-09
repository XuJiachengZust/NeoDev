"""Git branch records per project (Phase 5)."""

from psycopg2.extras import RealDictCursor


def list_by_project_id(conn, project_id: int) -> list[str]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT branch_name
               FROM git_branches
               WHERE project_id = %s
               ORDER BY branch_name""",
            (project_id,),
        )
        return [str(row["branch_name"]) for row in cur.fetchall()]


def upsert_many(conn, project_id: int, branch_names: list[str]) -> None:
    cleaned = sorted({b.strip() for b in branch_names if isinstance(b, str) and b.strip()})
    if not cleaned:
        return
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO git_branches (project_id, branch_name, updated_at)
               VALUES (%s, %s, now())
               ON CONFLICT (project_id, branch_name)
               DO UPDATE SET updated_at = now()""",
            [(project_id, b) for b in cleaned],
        )
