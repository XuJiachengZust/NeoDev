"""Document aggregate: PG CRUD."""

from datetime import datetime

from psycopg2.extras import Json
from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, doc_binding_id, doc_id, relative_path, doc_type, front_matter_json, "
    "relations_json, status, last_seen_commit, last_scanned_at, title, created_at, updated_at"
)


def create(
    conn,
    doc_binding_id: int,
    doc_id: str,
    relative_path: str,
    doc_type: str = "markdown",
    front_matter_json: dict | None = None,
    relations_json: dict | None = None,
    status: str = "active",
    last_seen_commit: str | None = None,
    last_scanned_at: datetime | None = None,
    title: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO documents (
                 doc_binding_id, doc_id, relative_path, doc_type, front_matter_json,
                 relations_json, status, last_seen_commit, last_scanned_at, title
             )
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (
                doc_binding_id,
                doc_id,
                relative_path,
                doc_type,
                Json(front_matter_json or {}),
                Json(relations_json or {}),
                status,
                last_seen_commit,
                last_scanned_at,
                title,
            ),
        )
        return dict(cur.fetchone())


def upsert(
    conn,
    doc_binding_id: int,
    doc_id: str,
    relative_path: str,
    doc_type: str = "markdown",
    front_matter_json: dict | None = None,
    relations_json: dict | None = None,
    status: str = "active",
    last_seen_commit: str | None = None,
    last_scanned_at: datetime | None = None,
    title: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO documents (
                 doc_binding_id, doc_id, relative_path, doc_type, front_matter_json,
                 relations_json, status, last_seen_commit, last_scanned_at, title
             )
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
             ON CONFLICT (doc_binding_id, relative_path)
             DO UPDATE SET
                 doc_id = EXCLUDED.doc_id,
                 doc_type = EXCLUDED.doc_type,
                 front_matter_json = EXCLUDED.front_matter_json,
                 relations_json = EXCLUDED.relations_json,
                 status = EXCLUDED.status,
                 last_seen_commit = EXCLUDED.last_seen_commit,
                 last_scanned_at = EXCLUDED.last_scanned_at,
                 title = EXCLUDED.title,
                 updated_at = now()
             RETURNING {_COLUMNS}""",
            (
                doc_binding_id,
                doc_id,
                relative_path,
                doc_type,
                Json(front_matter_json or {}),
                Json(relations_json or {}),
                status,
                last_seen_commit,
                last_scanned_at,
                title,
            ),
        )
        return dict(cur.fetchone())


def find_by_id(conn, document_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM documents WHERE id = %s",
            (document_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def find_by_doc_id(conn, doc_id: str) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM documents WHERE doc_id = %s",
            (doc_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_by_binding(conn, doc_binding_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_COLUMNS}
             FROM documents
             WHERE doc_binding_id = %s
             ORDER BY id DESC""",
            (doc_binding_id,),
        )
        return [dict(row) for row in cur.fetchall()]
