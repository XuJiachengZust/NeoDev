"""Product Requirement aggregate: PG CRUD for three-level requirements (Epic/Story/Task)."""

from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, product_id, parent_id, level, title, description, external_id, "
    "status, priority, assignee, version_id, sort_order, created_at, updated_at"
)


def list_by_product(
    conn,
    product_id: int,
    level: str | None = None,
    parent_id: int | None = None,
    status: str | None = None,
    version_id: int | None = None,
) -> list[dict]:
    """列出产品需求，可按 level/parent/status/version 过滤。"""
    conditions = ["product_id = %s"]
    args: list = [product_id]
    if level:
        conditions.append("level = %s")
        args.append(level)
    if parent_id is not None:
        conditions.append("parent_id = %s")
        args.append(parent_id)
    if status:
        conditions.append("status = %s")
        args.append(status)
    if version_id is not None:
        conditions.append("version_id = %s")
        args.append(version_id)

    where = " AND ".join(conditions)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM product_requirements WHERE {where} ORDER BY sort_order, id",
            args,
        )
        return [dict(row) for row in cur.fetchall()]


def list_tree(conn, product_id: int, version_id: int | None = None) -> list[dict]:
    """以平铺列表返回产品下所有需求（含 parent_id、has_doc），前端自行构建树。"""
    conditions = ["r.product_id = %s"]
    args: list = [product_id]
    if version_id is not None:
        conditions.append("r.version_id = %s")
        args.append(version_id)
    where = " AND ".join(conditions)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT r.id, r.product_id, r.parent_id, r.level, r.title, r.description,
                       r.external_id, r.status, r.priority, r.assignee, r.version_id,
                       r.sort_order, r.created_at, r.updated_at,
                       (m.id IS NOT NULL) AS has_doc
                FROM product_requirements r
                LEFT JOIN requirement_doc_meta m ON m.requirement_id = r.id
                WHERE {where}
                ORDER BY r.sort_order, r.id""",
            args,
        )
        return [dict(row) for row in cur.fetchall()]


def list_tree_with_commit_counts(conn, product_id: int, version_id: int | None = None) -> list[dict]:
    """返回需求平铺列表，附带每条需求已绑定的提交数（LEFT JOIN 避免 N+1）。"""
    conditions = ["r.product_id = %s"]
    args: list = [product_id]
    if version_id is not None:
        conditions.append("r.version_id = %s")
        args.append(version_id)
    where = " AND ".join(conditions)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT r.id, r.product_id, r.parent_id, r.level, r.title, r.description,
                       r.external_id, r.status, r.priority, r.assignee, r.version_id,
                       r.sort_order, r.created_at, r.updated_at,
                       COUNT(prc.commit_id) AS commit_count
                FROM product_requirements r
                LEFT JOIN product_requirement_commits prc ON prc.requirement_id = r.id
                WHERE {where}
                GROUP BY r.id
                ORDER BY r.sort_order, r.id""",
            args,
        )
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, requirement_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM product_requirements WHERE id = %s",
            (requirement_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create(
    conn,
    product_id: int,
    title: str,
    level: str = "story",
    parent_id: int | None = None,
    description: str | None = None,
    external_id: str | None = None,
    status: str = "open",
    priority: str = "medium",
    assignee: str | None = None,
    version_id: int | None = None,
    sort_order: int = 0,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO product_requirements
               (product_id, parent_id, level, title, description, external_id,
                status, priority, assignee, version_id, sort_order)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (
                product_id, parent_id, level, title, description, external_id,
                status, priority, assignee, version_id, sort_order,
            ),
        )
        return dict(cur.fetchone())


_ALLOWED_UPDATE_KEYS = frozenset({
    "title", "description", "external_id", "status", "priority",
    "assignee", "version_id", "sort_order", "parent_id", "level",
})


def update(conn, requirement_id: int, **kwargs) -> dict | None:
    existing = find_by_id(conn, requirement_id)
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
    args.append(requirement_id)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE product_requirements SET {", ".join(updates)} WHERE id = %s
             RETURNING {_COLUMNS}""",
            args,
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete(conn, requirement_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM product_requirements WHERE id = %s", (requirement_id,))
        return cur.rowcount > 0


# ── 需求-提交关联 ──

def bind_commits(conn, requirement_id: int, commit_ids: list[int]) -> int:
    """绑定提交到需求，返回新增绑定数。"""
    count = 0
    with conn.cursor() as cur:
        for cid in commit_ids:
            cur.execute(
                """INSERT INTO product_requirement_commits (requirement_id, commit_id)
                 VALUES (%s, %s)
                 ON CONFLICT DO NOTHING""",
                (requirement_id, cid),
            )
            count += cur.rowcount
    return count


def unbind_commits(conn, requirement_id: int, commit_ids: list[int]) -> int:
    count = 0
    with conn.cursor() as cur:
        for cid in commit_ids:
            cur.execute(
                "DELETE FROM product_requirement_commits WHERE requirement_id = %s AND commit_id = %s",
                (requirement_id, cid),
            )
            count += cur.rowcount
    return count


def list_commits(conn, requirement_id: int) -> list[dict]:
    """列出需求关联的提交。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT c.id, c.project_id, c.version_id, c.commit_sha, c.message, c.author, c.committed_at
               FROM product_requirement_commits prc
               JOIN commits c ON c.id = prc.commit_id
               WHERE prc.requirement_id = %s
               ORDER BY c.committed_at DESC""",
            (requirement_id,),
        )
        return [dict(row) for row in cur.fetchall()]
