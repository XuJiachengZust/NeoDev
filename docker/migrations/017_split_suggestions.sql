-- 拆分建议结构化存储（从文档内嵌文本迁移到独立表）
CREATE TABLE IF NOT EXISTS requirement_split_suggestions (
    id              SERIAL PRIMARY KEY,
    requirement_id  INTEGER NOT NULL REFERENCES product_requirements(id) ON DELETE CASCADE,
    suggestions     JSONB NOT NULL DEFAULT '[]'::jsonb,
    generated_by    VARCHAR(32),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_split_suggestions_req UNIQUE (requirement_id)
);
