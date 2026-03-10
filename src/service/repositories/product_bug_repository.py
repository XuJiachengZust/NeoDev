"""Product Bug aggregate: PG CRUD."""

from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, product_id, title, description, external_id, severity, status, priority, "
    "assignee, reporter, version_id, fix_version_id, requirement_id, created_at, updated_at"
)


def list_by_product(
    conn,
    product_id: int,
    status: str | None = None,
    severity: str | None = None,
    version_id: int | None = None,
) -> list[dict]:
    conditions = ["product_id = %s"]
    args: list = [product_id]
    if status:
        conditions.append("status = %s")
        args.append(status)
    if severity:
        conditions.append("severity = %s")
        args.append(severity)
    if version_id is not None:
        conditions.append("(version_id = %s OR fix_version_id = %s)")
        args.extend([version_id, version_id])

    where = " AND ".join(conditions)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM product_bugs WHERE {where} ORDER BY id DESC",
            args,
        )
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, bug_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM product_bugs WHERE id = %s",
            (bug_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create(
    conn,
    product_id: int,
    title: str,
    description: str | None = None,
    external_id: str | None = None,
    severity: str = "minor",
    status: str = "open",
    priority: str = "medium",
    assignee: str | None = None,
    reporter: str | None = None,
    version_id: int | None = None,
    fix_version_id: int | None = None,
    requirement_id: int | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO product_bugs
               (product_id, title, description, external_id, severity, status, priority,
                assignee, reporter, version_id, fix_version_id, requirement_id)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (
                product_id, title, description, external_id, severity, status, priority,
                assignee, reporter, version_id, fix_version_id, requirement_id,
            ),
        )
        return dict(cur.fetchone())


_ALLOWED_UPDATE_KEYS = frozenset({
    "title", "description", "external_id", "severity", "status", "priority",
    "assignee", "reporter", "version_id", "fix_version_id", "requirement_id",
})


def update(conn, bug_id: int, **kwargs) -> dict | None:
    existing = find_by_id(conn, bug_id)
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
    args.append(bug_id)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE product_bugs SET {", ".join(updates)} WHERE id = %s
             RETURNING {_COLUMNS}""",
            args,
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete(conn, bug_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM product_bugs WHERE id = %s", (bug_id,))
        return cur.rowcount > 0


# ── Bug-提交关联 ──

def bind_commits(conn, bug_id: int, commit_ids: list[int]) -> int:
    count = 0
    with conn.cursor() as cur:
        for cid in commit_ids:
            cur.execute(
                """INSERT INTO product_bug_commits (bug_id, commit_id)
                 VALUES (%s, %s)
                 ON CONFLICT DO NOTHING""",
                (bug_id, cid),
            )
            count += cur.rowcount
    return count


def unbind_commits(conn, bug_id: int, commit_ids: list[int]) -> int:
    count = 0
    with conn.cursor() as cur:
        for cid in commit_ids:
            cur.execute(
                "DELETE FROM product_bug_commits WHERE bug_id = %s AND commit_id = %s",
                (bug_id, cid),
            )
            count += cur.rowcount
    return count


def list_commits(conn, bug_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT c.id, c.project_id, c.version_id, c.commit_sha, c.message, c.author, c.committed_at
               FROM product_bug_commits pbc
               JOIN commits c ON c.id = pbc.commit_id
               WHERE pbc.bug_id = %s
               ORDER BY c.committed_at DESC""",
            (bug_id,),
        )
        return [dict(row) for row in cur.fetchall()]
