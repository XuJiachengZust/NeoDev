"""需求文档元数据 Repository：操作 requirement_doc_meta 表。"""

from psycopg2.extras import RealDictCursor

_COLUMNS = "id, requirement_id, version, generated_by, file_path, created_at, updated_at"


def find_meta(conn, requirement_id: int) -> dict | None:
    """获取指定需求的文档元数据；不存在则返回 None。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM requirement_doc_meta WHERE requirement_id = %s",
            (requirement_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def upsert_meta(
    conn,
    requirement_id: int,
    version: int,
    generated_by: str | None = None,
    file_path: str | None = None,
) -> dict:
    """
    插入或更新元数据。若 requirement_id 已存在则更新，否则插入。
    返回最新行（dict）。
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO requirement_doc_meta (requirement_id, version, generated_by, file_path)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (requirement_id) DO UPDATE SET
                version = EXCLUDED.version,
                generated_by = COALESCE(EXCLUDED.generated_by, requirement_doc_meta.generated_by),
                file_path = COALESCE(EXCLUDED.file_path, requirement_doc_meta.file_path),
                updated_at = now()
            RETURNING """ + _COLUMNS,
            (requirement_id, version, generated_by, file_path),
        )
        return dict(cur.fetchone())


def delete_meta(conn, requirement_id: int) -> bool:
    """删除指定需求的文档元数据；返回是否删除了行。"""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM requirement_doc_meta WHERE requirement_id = %s",
            (requirement_id,),
        )
        return cur.rowcount > 0


def batch_has_doc(conn, requirement_ids: list[int]) -> dict[int, bool]:
    """
    批量检查需求是否有关联文档（存在元数据记录）。
    返回 requirement_id -> True/False；未传入的 id 不出现在结果中。
    """
    if not requirement_ids:
        return {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT requirement_id FROM requirement_doc_meta WHERE requirement_id = ANY(%s)",
            (requirement_ids,),
        )
        has_set = {row["requirement_id"] for row in cur.fetchall()}
    return {rid: (rid in has_set) for rid in requirement_ids}


def check_children_have_docs(conn, requirement_id: int) -> bool:
    """
    检查该需求的所有子需求是否都有文档。
    若无子需求则返回 True；有子需求则当且仅当全部有文档时返回 True。
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id FROM product_requirements WHERE parent_id = %s",
            (requirement_id,),
        )
        children = [row["id"] for row in cur.fetchall()]
    if not children:
        return True
    has_map = batch_has_doc(conn, children)
    return all(has_map.get(cid, False) for cid in children)
