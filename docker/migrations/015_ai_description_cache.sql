-- 内容寻址的 AI 描述缓存：同样源码 + 同样模型 = 同样描述，跨分支自动复用
CREATE TABLE IF NOT EXISTS ai_description_cache (
    content_hash    TEXT PRIMARY KEY,
    label           TEXT NOT NULL,
    description     TEXT NOT NULL,
    embedding       real[] NOT NULL,
    embedding_dim   INTEGER NOT NULL,
    chat_model      TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_desc_cache_created ON ai_description_cache (created_at);
