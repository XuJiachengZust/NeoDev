"""Project aggregate: PG CRUD only (Phase 3)."""

from psycopg2.extras import RealDictCursor


def list_all(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, name, repo_path, created_at, watch_enabled, neo4j_database, neo4j_identifier FROM projects ORDER BY id"
        )
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, project_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, name, repo_path, created_at, watch_enabled, neo4j_database, neo4j_identifier FROM projects WHERE id = %s",
            (project_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create(
    conn,
    name: str,
    repo_path: str,
    watch_enabled: bool = False,
    neo4j_database: str | None = None,
    neo4j_identifier: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO projects (name, repo_path, watch_enabled, neo4j_database, neo4j_identifier)
             VALUES (%s, %s, %s, %s, %s)
             RETURNING id, name, repo_path, created_at, watch_enabled, neo4j_database, neo4j_identifier""",
            (name, repo_path, watch_enabled, neo4j_database, neo4j_identifier),
        )
        row = cur.fetchone()
        return dict(row)


def update(
    conn,
    project_id: int,
    name: str | None = None,
    repo_path: str | None = None,
    watch_enabled: bool | None = None,
    neo4j_database: str | None = None,
    neo4j_identifier: str | None = None,
) -> dict | None:
    existing = find_by_id(conn, project_id)
    if not existing:
        return None
    updates = []
    args = []
    if name is not None:
        updates.append("name = %s")
        args.append(name)
    if repo_path is not None:
        updates.append("repo_path = %s")
        args.append(repo_path)
    if watch_enabled is not None:
        updates.append("watch_enabled = %s")
        args.append(watch_enabled)
    if neo4j_database is not None:
        updates.append("neo4j_database = %s")
        args.append(neo4j_database)
    if neo4j_identifier is not None:
        updates.append("neo4j_identifier = %s")
        args.append(neo4j_identifier)
    if not updates:
        return existing
    args.append(project_id)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE projects SET {", ".join(updates)} WHERE id = %s
             RETURNING id, name, repo_path, created_at, watch_enabled, neo4j_database, neo4j_identifier""",
            args,
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete(conn, project_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        return cur.rowcount > 0
