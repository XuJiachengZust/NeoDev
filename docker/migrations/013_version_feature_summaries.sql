-- 版本功能总结：AI 预处理完成后自动生成的项目功能概述
CREATE TABLE IF NOT EXISTS version_feature_summaries (
    id                 SERIAL PRIMARY KEY,
    product_version_id INTEGER      NOT NULL REFERENCES product_versions(id) ON DELETE CASCADE,
    project_id         INTEGER      NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch             VARCHAR(255) NOT NULL,
    status             VARCHAR(20)  NOT NULL DEFAULT 'pending',   -- pending/running/completed/failed
    summary            TEXT,
    error_message      TEXT,
    triggered_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    finished_at        TIMESTAMPTZ,
    UNIQUE (product_version_id, project_id)
);
