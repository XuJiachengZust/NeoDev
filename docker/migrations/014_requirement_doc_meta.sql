-- 需求文档轻量元数据：版本号、生成方式、文件路径（内容在文件系统）
CREATE TABLE IF NOT EXISTS requirement_doc_meta (
    id              SERIAL PRIMARY KEY,
    requirement_id   INTEGER NOT NULL UNIQUE REFERENCES product_requirements(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL DEFAULT 1,
    generated_by    VARCHAR(32),   -- 'manual' | 'agent' | 'workflow'
    file_path       VARCHAR(512),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_req_doc_meta_req_id ON requirement_doc_meta(requirement_id);

COMMENT ON TABLE requirement_doc_meta IS '需求文档元数据，正文存于文件系统 /data/requirement_docs/{product_id}/{requirement_id}/doc.md';
