"""Product Version aggregate: PG CRUD."""

from psycopg2.extras import RealDictCursor


_COLUMNS = "id, product_id, version_name, description, status, release_date, created_at, updated_at"


def list_by_product(conn, product_id: int, status: str | None = None) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if status:
            cur.execute(
                f"SELECT {_COLUMNS} FROM product_versions WHERE product_id = %s AND status = %s ORDER BY id DESC",
                (product_id, status),
            )
        else:
            cur.execute(
                f"SELECT {_COLUMNS} FROM product_versions WHERE product_id = %s ORDER BY id DESC",
                (product_id,),
            )
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, version_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM product_versions WHERE id = %s",
            (version_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create(
    conn,
    product_id: int,
    version_name: str,
    description: str | None = None,
    status: str = "planning",
    release_date: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO product_versions (product_id, version_name, description, status, release_date)
             VALUES (%s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (product_id, version_name, description, status, release_date),
        )
        return dict(cur.fetchone())


_ALLOWED_UPDATE_KEYS = frozenset({"version_name", "description", "status", "release_date"})


def update(conn, version_id: int, **kwargs) -> dict | None:
    existing = find_by_id(conn, version_id)
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
    args.append(version_id)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE product_versions SET {", ".join(updates)} WHERE id = %s
             RETURNING {_COLUMNS}""",
            args,
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete(conn, version_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM product_versions WHERE id = %s", (version_id,))
        return cur.rowcount > 0


# ── 分支映射 ──

def list_branches(conn, version_id: int) -> list[dict]:
    """列出产品版本关联的项目分支。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT pvb.id, pvb.product_version_id, pvb.project_id, pvb.branch,
                      p.name AS project_name
               FROM product_version_branches pvb
               JOIN projects p ON p.id = pvb.project_id
               WHERE pvb.product_version_id = %s
               ORDER BY pvb.project_id""",
            (version_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def set_branch(conn, version_id: int, project_id: int, branch: str) -> dict:
    """设置或更新产品版本对应项目的分支。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO product_version_branches (product_version_id, project_id, branch)
             VALUES (%s, %s, %s)
             ON CONFLICT (product_version_id, project_id) DO UPDATE SET branch = EXCLUDED.branch
             RETURNING id, product_version_id, project_id, branch""",
            (version_id, project_id, branch),
        )
        return dict(cur.fetchone())


def remove_branch(conn, version_id: int, project_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM product_version_branches WHERE product_version_id = %s AND project_id = %s",
            (version_id, project_id),
        )
        return cur.rowcount > 0
