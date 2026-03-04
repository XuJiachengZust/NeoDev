"""Version (Project aggregate): PG CRUD only (Phase 3)."""

from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor


def list_by_project_id(conn, project_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, project_id, branch, version_name, created_at, last_parsed_commit
             FROM versions WHERE project_id = %s ORDER BY id""",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, version_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, project_id, branch, version_name, created_at, last_parsed_commit
             FROM versions WHERE id = %s""",
            (version_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create(
    conn,
    project_id: int,
    branch: str | None,
    version_name: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO versions (project_id, branch, version_name)
             VALUES (%s, %s, %s)
             RETURNING id, project_id, branch, version_name, created_at, last_parsed_commit""",
            (project_id, branch or None, version_name),
        )
        return dict(cur.fetchone())


def delete(conn, version_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM versions WHERE id = %s", (version_id,))
        return cur.rowcount > 0


def update_last_parsed_commit(
    conn, version_id: int, commit_sha: str
) -> dict | None:
    """Update last_parsed_commit for a version (Phase 4). Returns updated row or None."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """UPDATE versions SET last_parsed_commit = %s WHERE id = %s
             RETURNING id, project_id, branch, version_name, created_at, last_parsed_commit""",
            (commit_sha[:40] if commit_sha else None, version_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def project_exists(conn, project_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM projects WHERE id = %s", (project_id,))
        return cur.fetchone() is not None
