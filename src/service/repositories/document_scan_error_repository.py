"""Document scan error aggregate: PG CRUD."""

from psycopg2.extras import Json
from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, doc_binding_id, relative_path, error_code, error_message, details_json, created_at"
)


def create(
    conn,
    doc_binding_id: int,
    relative_path: str,
    error_code: str,
    error_message: str,
    details_json: dict | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO document_scan_errors (
                 doc_binding_id, relative_path, error_code, error_message, details_json
             )
             VALUES (%s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (
                doc_binding_id,
                relative_path,
                error_code,
                error_message,
                Json(details_json or {}),
            ),
        )
        return dict(cur.fetchone())


def list_by_binding(conn, doc_binding_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_COLUMNS}
             FROM document_scan_errors
             WHERE doc_binding_id = %s
             ORDER BY id DESC""",
            (doc_binding_id,),
        )
        return [dict(row) for row in cur.fetchall()]
