"""Doc change aggregate: PG CRUD."""

from psycopg2.extras import Json
from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, document_id, doc_change_id, source_commit, summary, details_json, created_by, "
    "implemented_at, status, created_at, updated_at"
)


def create(
    conn,
    document_id: int,
    doc_change_id: str,
    source_commit: str | None = None,
    summary: str | None = None,
    details_json: dict | None = None,
    created_by: str | None = None,
    status: str = "pending_implementation",
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO doc_changes (
                 document_id, doc_change_id, source_commit, summary, details_json, created_by, status
             )
             VALUES (%s, %s, %s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (
                document_id,
                doc_change_id,
                source_commit,
                summary,
                Json(details_json or {}),
                created_by,
                status,
            ),
        )
        return dict(cur.fetchone())


def find_by_id(conn, change_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM doc_changes WHERE id = %s",
            (change_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def find_by_doc_change_id(conn, doc_change_id: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM doc_changes WHERE doc_change_id = %s",
            (doc_change_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_by_document(conn, document_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_COLUMNS}
             FROM doc_changes
             WHERE document_id = %s
             ORDER BY id DESC""",
            (document_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def mark_implemented(conn, change_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE doc_changes
             SET status = 'implemented', implemented_at = now(), updated_at = now()
             WHERE id = %s AND implemented_at IS NULL
             RETURNING {_COLUMNS}""",
            (change_id,),
        )
        row = cur.fetchone()
        if row:
            return dict(row)
    return find_by_id(conn, change_id)
