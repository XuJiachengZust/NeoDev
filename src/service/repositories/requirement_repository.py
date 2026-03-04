"""Requirement aggregate: PG CRUD + requirement_commits (Phase 3)."""

from psycopg2.extras import RealDictCursor


def list_by_project_id(conn, project_id: int) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, project_id, title, description, external_id, created_at
             FROM requirements WHERE project_id = %s ORDER BY id""",
            (project_id,),
        )
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, requirement_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, project_id, title, description, external_id, created_at
             FROM requirements WHERE id = %s""",
            (requirement_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create(
    conn,
    project_id: int,
    title: str,
    description: str | None = None,
    external_id: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO requirements (project_id, title, description, external_id)
             VALUES (%s, %s, %s, %s)
             RETURNING id, project_id, title, description, external_id, created_at""",
            (project_id, title, description, external_id),
        )
        return dict(cur.fetchone())


def update(
    conn,
    requirement_id: int,
    title: str | None = None,
    description: str | None = None,
    external_id: str | None = None,
) -> dict | None:
    existing = find_by_id(conn, requirement_id)
    if not existing:
        return None
    updates = []
    args = []
    if title is not None:
        updates.append("title = %s")
        args.append(title)
    if description is not None:
        updates.append("description = %s")
        args.append(description)
    if external_id is not None:
        updates.append("external_id = %s")
        args.append(external_id)
    if not updates:
        return existing
    args.append(requirement_id)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE requirements SET {", ".join(updates)} WHERE id = %s
             RETURNING id, project_id, title, description, external_id, created_at""",
            args,
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete(conn, requirement_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM requirements WHERE id = %s", (requirement_id,))
        return cur.rowcount > 0


def get_commit_ids(conn, requirement_id: int) -> list[int]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT commit_id FROM requirement_commits WHERE requirement_id = %s",
            (requirement_id,),
        )
        return [row[0] for row in cur.fetchall()]


def bind_commits(conn, requirement_id: int, commit_ids: list[int]) -> None:
    with conn.cursor() as cur:
        for cid in commit_ids:
            cur.execute(
                "INSERT INTO requirement_commits (requirement_id, commit_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (requirement_id, cid),
            )


def unbind_commits(conn, requirement_id: int, commit_ids: list[int]) -> None:
    with conn.cursor() as cur:
        for cid in commit_ids:
            cur.execute(
                "DELETE FROM requirement_commits WHERE requirement_id = %s AND commit_id = %s",
                (requirement_id, cid),
            )
