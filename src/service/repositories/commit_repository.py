"""Commit: PG read + find_by_id for requirement/impact services (Phase 3). Phase 4: upsert_commits."""

from typing import Any

from psycopg2.extras import RealDictCursor


def find_by_id(conn, commit_id: int) -> dict | None:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """SELECT id, project_id, version_id, commit_sha, message, author, committed_at
             FROM commits WHERE id = %s""",
            (commit_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_by_project_id(
    conn,
    project_id: int,
    version_id: int | None = None,
    requirement_id: int | None = None,
) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if version_id is not None:
            cur.execute(
                """SELECT id, project_id, version_id, commit_sha, message, author, committed_at
                 FROM commits WHERE project_id = %s AND version_id = %s ORDER BY id""",
                (project_id, version_id),
            )
        elif requirement_id is not None:
            cur.execute(
                """SELECT c.id, c.project_id, c.version_id, c.commit_sha, c.message, c.author, c.committed_at
                 FROM commits c
                 JOIN requirement_commits rc ON rc.commit_id = c.id
                 WHERE rc.requirement_id = %s AND c.project_id = %s ORDER BY c.id""",
                (requirement_id, project_id),
            )
        else:
            cur.execute(
                """SELECT id, project_id, version_id, commit_sha, message, author, committed_at
                 FROM commits WHERE project_id = %s ORDER BY id""",
                (project_id,),
            )
        return [dict(row) for row in cur.fetchall()]


def list_by_version_id(conn, project_id: int, version_id: int) -> list[dict]:
    return list_by_project_id(conn, project_id, version_id=version_id)


def list_by_version_id_filtered(
    conn,
    project_id: int,
    version_id: int,
    *,
    message: str | None = None,
    committed_at_from: str | None = None,
    committed_at_to: str | None = None,
    id: int | None = None,
    sha: str | None = None,
) -> list[dict]:
    """List commits for a version with optional filters (message substring, time range, id, sha prefix)."""
    conditions = ["project_id = %s", "version_id = %s"]
    params: list[Any] = [project_id, version_id]
    if message is not None and message.strip() != "":
        conditions.append("message ILIKE %s")
        params.append(f"%{message.strip()}%")
    if committed_at_from is not None and committed_at_from.strip() != "":
        conditions.append("committed_at >= %s")
        params.append(committed_at_from.strip())
    if committed_at_to is not None and committed_at_to.strip() != "":
        conditions.append("committed_at <= %s")
        params.append(committed_at_to.strip())
    if id is not None:
        conditions.append("id = %s")
        params.append(id)
    if sha is not None and sha.strip() != "":
        conditions.append("commit_sha LIKE %s")
        params.append(sha.strip() + "%")
    where = " AND ".join(conditions)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""SELECT id, project_id, version_id, commit_sha, message, author, committed_at
             FROM commits WHERE {where} ORDER BY id""",
            tuple(params),
        )
        return [dict(row) for row in cur.fetchall()]


def upsert_commits(
    conn,
    project_id: int,
    version_id: int,
    commits: list[dict[str, Any]],
) -> int:
    """
    Insert or update commits for a project/version. Each dict: commit_sha (required),
    message, author, committed_at (optional). Returns number of rows affected (inserted or updated).
    Uses ON CONFLICT (project_id, commit_sha) DO UPDATE to set version_id, message, author, committed_at.
    """
    if not commits:
        return 0
    with conn.cursor() as cur:
        for c in commits:
            sha = (c.get("commit_sha") or "")[:40]
            if not sha:
                continue
            msg = c.get("message")
            author = c.get("author")
            committed_at = c.get("committed_at")
            cur.execute(
                """INSERT INTO commits (project_id, version_id, commit_sha, message, author, committed_at)
                 VALUES (%s, %s, %s, %s, %s, %s)
                 ON CONFLICT (project_id, commit_sha)
                 DO UPDATE SET version_id = EXCLUDED.version_id, message = EXCLUDED.message,
                               author = EXCLUDED.author, committed_at = EXCLUDED.committed_at""",
                (project_id, version_id, sha, msg, author, committed_at),
            )
        return len([c for c in commits if (c.get("commit_sha") or "")[:40]])
