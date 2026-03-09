-- AI 预处理任务状态，用于单项目单任务并发控制与状态查询
CREATE TABLE IF NOT EXISTS ai_preprocess_status (
    id          SERIAL PRIMARY KEY,
    project_id  INT         NOT NULL,
    branch      VARCHAR(255) NOT NULL,
    status      VARCHAR(32)  NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ NULL,
    error_message TEXT NULL,
    extra       JSONB NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, branch)
);

CREATE INDEX IF NOT EXISTS idx_ai_preprocess_status_project_running
    ON ai_preprocess_status (project_id) WHERE status = 'running';

COMMENT ON TABLE ai_preprocess_status IS 'AI 预处理任务状态，用于单项目单任务并发控制与状态查询';
COMMENT ON COLUMN ai_preprocess_status.status IS 'pending|running|completed|failed';
COMMENT ON COLUMN ai_preprocess_status.extra IS '可选统计，如 saved_count, skipped_count, layer_count';
