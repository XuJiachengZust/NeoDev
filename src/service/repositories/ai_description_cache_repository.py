"""AI 描述缓存仓储：按内容哈希存取描述与向量，跨分支复用。"""

from psycopg2.extras import RealDictCursor, execute_values


def batch_get(conn, hashes: list[str]) -> dict[str, dict]:
    """批量查询缓存，返回 {content_hash: {description, embedding, embedding_dim}}。"""
    if not hashes:
        return {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT content_hash, description, embedding, embedding_dim "
            "FROM ai_description_cache WHERE content_hash = ANY(%s)",
            (hashes,),
        )
        return {row["content_hash"]: dict(row) for row in cur.fetchall()}


def batch_upsert(conn, entries: list[dict]) -> int:
    """批量写入缓存条目，冲突时更新。"""
    if not entries:
        return 0
    with conn.cursor() as cur:
        execute_values(
            cur,
            """INSERT INTO ai_description_cache
                 (content_hash, label, description, embedding, embedding_dim, chat_model, embedding_model)
               VALUES %s
               ON CONFLICT (content_hash) DO UPDATE SET
                 description = EXCLUDED.description,
                 embedding = EXCLUDED.embedding,
                 embedding_dim = EXCLUDED.embedding_dim,
                 created_at = now()""",
            [
                (
                    e["content_hash"],
                    e["label"],
                    e["description"],
                    e["embedding"],
                    e["embedding_dim"],
                    e["chat_model"],
                    e["embedding_model"],
                )
                for e in entries
            ],
        )
        return cur.rowcount
