"""拆分建议存储：requirement_split_suggestions 表 CRUD。"""

import json
from psycopg2.extras import RealDictCursor


def find_by_requirement(conn, requirement_id: int) -> dict | None:
    """查询单条拆分建议记录。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, requirement_id, suggestions, generated_by, created_at, updated_at "
            "FROM requirement_split_suggestions WHERE requirement_id = %s",
            (requirement_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        result = dict(row)
        # 确保 suggestions 是 list（psycopg2 自动解析 JSONB，但防御性处理）
        if isinstance(result.get("suggestions"), str):
            result["suggestions"] = json.loads(result["suggestions"])
        return result


def upsert(conn, requirement_id: int, suggestions: list[dict], generated_by: str | None = None) -> dict:
    """插入或更新拆分建议（基于 requirement_id 唯一约束）。"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """INSERT INTO requirement_split_suggestions (requirement_id, suggestions, generated_by)
               VALUES (%s, %s::jsonb, %s)
               ON CONFLICT (requirement_id)
               DO UPDATE SET suggestions = EXCLUDED.suggestions,
                             generated_by = EXCLUDED.generated_by,
                             updated_at = now()
               RETURNING id, requirement_id, suggestions, generated_by, created_at, updated_at""",
            (requirement_id, json.dumps(suggestions, ensure_ascii=False), generated_by),
        )
        return dict(cur.fetchone())


def delete_by_requirement(conn, requirement_id: int) -> bool:
    """删除拆分建议，返回是否有删除。"""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM requirement_split_suggestions WHERE requirement_id = %s",
            (requirement_id,),
        )
        return cur.rowcount > 0
