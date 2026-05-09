"""Doc binding aggregate: PG CRUD."""

from urllib.parse import urlsplit, urlunsplit

import psycopg2
from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, product_id, product_version_id, repo_path, repo_url, default_branch, is_active, created_at, updated_at"
)


def create(
    conn,
    product_id: int,
    product_version_id: int,
    repo_path: str = "",
    repo_url: str = "",
    default_branch: str = "main",
    is_active: bool = True,
) -> dict:
    if product_version_id is None:
        raise ValueError("doc binding must be scoped to a product version")
    normalized_default_branch = _normalized_default_branch(default_branch)
    git_source_key = _normalized_git_source_key(repo_url=repo_url, repo_path=repo_path)
    if is_active:
        _raise_if_git_source_bound_to_other_version(
            conn,
            product_version_id=product_version_id,
            git_source_key=git_source_key,
            default_branch=normalized_default_branch,
        )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if _has_column(conn, "doc_bindings", "binding_name"):
            cur.execute(
                f"""INSERT INTO doc_bindings (
                     product_id, product_version_id, binding_name, repo_path, repo_url, default_branch, is_active, git_source_key
                 )
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                 RETURNING {_COLUMNS}""",
                (
                    product_id,
                    product_version_id,
                    f"product-{product_id}-docs",
                    repo_path,
                    repo_url,
                    normalized_default_branch,
                    is_active,
                    git_source_key,
                ),
            )
        else:
            cur.execute(
                f"""INSERT INTO doc_bindings (product_id, product_version_id, repo_path, repo_url, default_branch, is_active, git_source_key)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)
                 RETURNING {_COLUMNS}""",
                (
                    product_id,
                    product_version_id,
                    repo_path,
                    repo_url,
                    normalized_default_branch,
                    is_active,
                    git_source_key,
                ),
            )
        return dict(cur.fetchone())


def _raise_if_git_source_bound_to_other_version(
    conn,
    *,
    product_version_id: int,
    git_source_key: str,
    default_branch: str,
) -> None:
    if not git_source_key:
        return
    params: list = [product_version_id, default_branch, git_source_key]
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, product_version_id, repo_path, repo_url, default_branch
             FROM doc_bindings
             WHERE is_active = true
               AND product_version_id <> %s
               AND default_branch = %s
               AND git_source_key = %s
             LIMIT 1
            """,
            tuple(params),
        )
        conflict = cur.fetchone()
    if conflict:
        raise psycopg2.IntegrityError(
            "doc binding git source is already bound to another product version"
        )


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


def _normalized_default_branch(value: str) -> str:
    return (value or "").strip() or "main"


def _normalized_git_source_key(*, repo_url: str, repo_path: str) -> str:
    for candidate in (repo_url, repo_path):
        normalized = _normalized_git_source_value(candidate)
        if normalized:
            return normalized
    return ""


def _normalized_git_source_value(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    text = _trim_git_suffix(_trim_trailing_separators(text.replace("\\", "/")))
    url = urlsplit(text)
    if url.scheme and url.netloc:
        netloc = _normalized_netloc(url.netloc)
        return urlunsplit(
            (
                url.scheme.lower(),
                netloc,
                _trim_git_suffix(_trim_trailing_separators(url.path.replace("\\", "/"))),
                url.query,
                url.fragment,
            )
        )
    if _looks_like_scp_git_source(text):
        user_host, path = text.split(":", 1)
        user, host = user_host.split("@", 1)
        return f"{user}@{host.lower()}:{_trim_git_suffix(_trim_trailing_separators(path))}"
    return text


def _normalized_netloc(value: str) -> str:
    if "@" in value:
        user_info, host = value.rsplit("@", 1)
        return f"{user_info}@{host.lower()}"
    return value.lower()


def _looks_like_scp_git_source(value: str) -> bool:
    return "@" in value and ":" in value and "://" not in value and "/" in value.split(":", 1)[1]


def _trim_trailing_separators(value: str) -> str:
    return value.rstrip("/")


def _trim_git_suffix(value: str) -> str:
    return value[:-4] if value.lower().endswith(".git") else value
