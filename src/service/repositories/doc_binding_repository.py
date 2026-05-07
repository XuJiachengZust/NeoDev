"""Doc binding aggregate: PG CRUD."""

from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, product_id, product_version_id, repo_path, repo_url, default_branch, is_active, created_at, updated_at"
)


def create(
    conn,
    product_id: int,
    product_version_id: int | None = None,
    repo_path: str = "",
    repo_url: str = "",
    default_branch: str = "main",
    is_active: bool = True,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        has_product_version_id = _has_column(conn, "doc_bindings", "product_version_id")
        version_column = ", product_version_id" if has_product_version_id else ""
        version_value = ", %s" if has_product_version_id else ""
        if _has_column(conn, "doc_bindings", "binding_name"):
            cur.execute(
                f"""INSERT INTO doc_bindings (
                     product_id{version_column}, binding_name, repo_path, repo_url, default_branch, is_active
                 )
                 VALUES (%s{version_value}, %s, %s, %s, %s, %s)
                 RETURNING {_COLUMNS}""",
                _insert_params(
                    product_id,
                    product_version_id,
                    has_product_version_id,
                    f"product-{product_id}-docs",
                    repo_path,
                    repo_url,
                    default_branch,
                    is_active,
                ),
            )
        else:
            cur.execute(
                f"""INSERT INTO doc_bindings (product_id{version_column}, repo_path, repo_url, default_branch, is_active)
                 VALUES (%s{version_value}, %s, %s, %s, %s)
                 RETURNING {_COLUMNS}""",
                _insert_params(
                    product_id,
                    product_version_id,
                    has_product_version_id,
                    repo_path,
                    repo_url,
                    default_branch,
                    is_active,
                ),
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


def _has_column(conn, table_name: str, column_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = %s
                  AND column_name = %s
            )
            """,
            (table_name, column_name),
        )
        return bool(cur.fetchone()[0])


def _insert_params(
    product_id: int,
    product_version_id: int | None,
    has_product_version_id: bool,
    *tail,
) -> tuple:
    head = (product_id, product_version_id) if has_product_version_id else (product_id,)
    return (*head, *tail)
