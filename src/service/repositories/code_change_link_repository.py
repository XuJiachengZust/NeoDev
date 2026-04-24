"""Code change link aggregate: PG CRUD."""

from psycopg2.extras import RealDictCursor


_COLUMNS = "id, doc_change_id, project_id, branch, commit_sha, commit_message, created_at"


def create(
    conn,
    doc_change_id: int,
    project_id: int,
    branch: str,
    commit_sha: str,
    commit_message: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO code_change_links (
                 doc_change_id, project_id, branch, commit_sha, commit_message
             )
             VALUES (%s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (doc_change_id, project_id, branch, commit_sha, commit_message),
        )
        return dict(cur.fetchone())


def list_by_doc_change(conn, doc_change_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_COLUMNS}
             FROM code_change_links
             WHERE doc_change_id = %s
             ORDER BY id DESC""",
            (doc_change_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def list_by_commit(conn, project_id: int, branch: str, commit_sha: str) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_COLUMNS}
             FROM code_change_links
             WHERE project_id = %s AND branch = %s AND commit_sha = %s
             ORDER BY id DESC""",
            (project_id, branch, commit_sha),
        )
        return [dict(row) for row in cur.fetchall()]
