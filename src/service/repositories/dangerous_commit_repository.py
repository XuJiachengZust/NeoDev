"""Dangerous commit aggregate: PG CRUD."""

from psycopg2.extras import Json
from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, project_id, branch, commit_sha, status, risk_level, resolved_by, "
    "resolved_at, extra_json, reason, created_at, updated_at"
)


def create(
    conn,
    project_id: int,
    branch: str,
    commit_sha: str,
    status: str = "open",
    risk_level: str = "medium",
    reason: str | None = None,
    extra_json: dict | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO dangerous_commit_records (
                 project_id, branch, commit_sha, status, risk_level, reason, extra_json
             )
             VALUES (%s, %s, %s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (project_id, branch, commit_sha, status, risk_level, reason, Json(extra_json or {})),
        )
        return dict(cur.fetchone())


def find_by_id(conn, record_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM dangerous_commit_records WHERE id = %s",
            (record_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def find_open_by_identity(conn, project_id: int, branch: str, commit_sha: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_COLUMNS}
             FROM dangerous_commit_records
             WHERE status = 'open'
               AND project_id = %s
               AND branch = %s
               AND commit_sha = %s
             ORDER BY created_at DESC, id DESC
             LIMIT 1""",
            (project_id, branch, commit_sha),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_open(conn, project_id: int | None = None) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if project_id is not None:
            cur.execute(
                f"""SELECT {_COLUMNS}
                 FROM dangerous_commit_records
                 WHERE status = 'open' AND project_id = %s
                 ORDER BY created_at DESC, id DESC""",
                (project_id,),
            )
        else:
            cur.execute(
                f"""SELECT {_COLUMNS}
                 FROM dangerous_commit_records
                 WHERE status = 'open'
                 ORDER BY created_at DESC, id DESC"""
            )
        return [dict(row) for row in cur.fetchall()]


def resolve(conn, record_id: int, resolved_by: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE dangerous_commit_records
             SET status = 'resolved', resolved_by = %s, resolved_at = now(), updated_at = now()
             WHERE id = %s AND status = 'open'
             RETURNING {_COLUMNS}""",
            (resolved_by, record_id),
        )
        row = cur.fetchone()
        if row:
            return dict(row)
    return find_by_id(conn, record_id)
