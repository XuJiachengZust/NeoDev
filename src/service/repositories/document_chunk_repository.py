"""Document chunk aggregate: PG CRUD and vector search."""

from __future__ import annotations

from psycopg2.extras import RealDictCursor


_COLUMNS = (
    "id, document_id, chunk_index, heading_path, chunk_text, token_count, "
    "content_hash, split_strategy, status, embedding, embedding_model, "
    "embedding_dim, embedding_updated_at, created_at, updated_at"
)


def replace_document_chunks(conn, document_id: int, chunks: list[dict]) -> list[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("DELETE FROM document_chunks WHERE document_id = %s", (document_id,))
        rows: list[dict] = []
        for chunk in chunks:
            cur.execute(
                f"""INSERT INTO document_chunks (
                     document_id, chunk_index, heading_path, chunk_text, token_count,
                     content_hash, split_strategy, status
                 )
                 VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
                 RETURNING {_COLUMNS}""",
                (
                    document_id,
                    chunk["chunk_index"],
                    chunk.get("heading_path") or "",
                    chunk["text"],
                    int(chunk.get("token_count") or 0),
                    chunk["content_hash"],
                    chunk.get("split_strategy") or "structural",
                ),
            )
            rows.append(dict(cur.fetchone()))
        return rows


def upsert_embedding(
    conn,
    chunk_id: int,
    *,
    embedding: list[float],
    embedding_model: str,
) -> dict:
    vector_literal = "[" + ",".join(str(float(value)) for value in embedding) + "]"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""UPDATE document_chunks
             SET embedding = %s::vector,
                 embedding_model = %s,
                 embedding_dim = %s,
                 embedding_updated_at = now(),
                 updated_at = now()
             WHERE id = %s
             RETURNING {_COLUMNS}""",
            (vector_literal, embedding_model, len(embedding), chunk_id),
        )
        return dict(cur.fetchone())


def search_chunks(
    conn,
    *,
    product_id: int,
    embedding: list[float],
    top_k: int,
) -> list[dict]:
    vector_literal = "[" + ",".join(str(float(value)) for value in embedding) + "]"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT dc.id AS chunk_id,
                   dc.chunk_index,
                   dc.heading_path,
                   dc.chunk_text,
                   d.id AS document_id,
                   d.doc_id,
                   d.title,
                   d.doc_type,
                   d.relative_path,
                   1 - (dc.embedding <=> %s::vector) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            JOIN doc_bindings db ON db.id = d.doc_binding_id
            WHERE db.product_id = %s
              AND db.is_active = true
              AND d.deleted_at IS NULL
              AND dc.status = 'active'
              AND dc.embedding IS NOT NULL
            ORDER BY dc.embedding <=> %s::vector
            LIMIT %s
            """,
            (vector_literal, product_id, vector_literal, top_k),
        )
        return [dict(row) for row in cur.fetchall()]
