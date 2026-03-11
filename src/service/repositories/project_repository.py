"""Project aggregate: PG CRUD only (Phase 3)."""

from psycopg2.extras import RealDictCursor


_COLUMNS = "id, name, repo_path, repo_url, created_at, watch_enabled, neo4j_database, neo4j_identifier, repo_username, repo_password"


def list_all(conn) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT {_COLUMNS} FROM projects ORDER BY id")
        return [dict(row) for row in cur.fetchall()]


def find_by_id(conn, project_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM projects WHERE id = %s",
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
    repo_username: str | None = None,
    repo_password: str | None = None,
    repo_url: str | None = None,
) -> dict:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""INSERT INTO projects (name, repo_path, repo_url, watch_enabled, neo4j_database, neo4j_identifier, repo_username, repo_password)
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
             RETURNING {_COLUMNS}""",
            (name, repo_path, repo_url, watch_enabled, neo4j_database, neo4j_identifier, repo_username, repo_password),
        )
        row = cur.fetchone()
        return dict(row)


_ALLOWED_UPDATE_KEYS = frozenset(
    {"name", "repo_path", "repo_url", "watch_enabled", "neo4j_database", "neo4j_identifier", "repo_username", "repo_password"}
)


def update(conn, project_id: int, **kwargs) -> dict | None:
    existing = find_by_id(conn, project_id)
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
    args.append(project_id)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE projects SET {", ".join(updates)} WHERE id = %s
             RETURNING {_COLUMNS}""",
            args,
        )
        row = cur.fetchone()
        return dict(row) if row else None


def delete(conn, project_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
        return cur.rowcount > 0
