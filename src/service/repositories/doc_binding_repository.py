"""Doc binding aggregate: PG CRUD."""

from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, product_id, repo_path, repo_url, default_branch, is_active, created_at, updated_at"
)


def create(
    conn,
    product_id: int,
    repo_path: str = "",
    repo_url: str = "",
    default_branch: str = "main",
    is_active: bool = True,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO doc_bindings (product_id, repo_path, repo_url, default_branch, is_active)
             VALUES (%s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (product_id, repo_path, repo_url, default_branch, is_active),
        )
        return dict(cur.fetchone())


def find_by_id(conn, binding_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM doc_bindings WHERE id = %s",
            (binding_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_active_by_product(conn, product_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT {_COLUMNS}
             FROM doc_bindings
             WHERE product_id = %s AND is_active = true
             ORDER BY id DESC""",
            (product_id,),
        )
        return [dict(row) for row in cur.fetchall()]
