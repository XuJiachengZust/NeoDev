"""Product aggregate: PG CRUD."""

from psycopg2.extras import RealDictCursor


_COLUMNS = "id, name, code, description, owner, status, created_at, updated_at"


def list_all(conn, status: str | None = None) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if status:
            cur.execute(
                f"SELECT {_COLUMNS} FROM products WHERE status = %s ORDER BY id",
                (status,),
            )
        else:
            cur.execute(f"SELECT {_COLUMNS} FROM products ORDER BY id")
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, product_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM products WHERE id = %s",
            (product_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create(
    conn,
    name: str,
    code: str | None = None,
    description: str | None = None,
    owner: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO products (name, code, description, owner)
             VALUES (%s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (name, code, description, owner),
        )
        return dict(cur.fetchone())


_ALLOWED_UPDATE_KEYS = frozenset({"name", "code", "description", "owner", "status"})


def update(conn, product_id: int, **kwargs) -> dict | None:
    existing = find_by_id(conn, product_id)
    if not existing:
        return None
    updates = []
    args = []
    for key, value in kwargs.items():
        if key not in _ALLOWED_UPDATE_KEYS:
            continue
        updates.append(f"{key} = %s")
        args.append(value)
    if not updates:
        return existing
    updates.append("updated_at = now()")
    args.append(product_id)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE products SET {", ".join(updates)} WHERE id = %s
             RETURNING {_COLUMNS}""",
            args,
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete(conn, product_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM products WHERE id = %s", (product_id,))
        return cur.rowcount > 0


def list_projects(conn, product_id: int) -> list[dict]:
    """列出产品下的所有项目。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, name, repo_path, created_at, watch_enabled, product_id
               FROM projects WHERE product_id = %s ORDER BY id""",
            (product_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def create_project(
    conn,
    product_id: int,
    name: str,
    repo_path: str,
    repo_username: str | None = None,
    repo_password: str | None = None,
    repo_url: str | None = None,
) -> dict:
    """在产品下直接创建项目。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO projects (name, repo_path, repo_url, repo_username, repo_password, product_id)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id, name, repo_path, repo_url, created_at, watch_enabled, product_id,
                         repo_username, repo_password""",
            (name, repo_path, repo_url, repo_username, repo_password, product_id),
        )
        return dict(cur.fetchone())


def bind_project(conn, product_id: int, project_id: int) -> bool:
    """将项目关联到产品。"""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE projects SET product_id = %s WHERE id = %s",
            (product_id, project_id),
        )
        return cur.rowcount > 0


def unbind_project(conn, product_id: int, project_id: int) -> bool:
    """解除项目与产品的关联。"""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE projects SET product_id = NULL WHERE id = %s AND product_id = %s",
            (project_id, product_id),
        )
        return cur.rowcount > 0
