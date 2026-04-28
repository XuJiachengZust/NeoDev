CREATE TABLE IF NOT EXISTS branch_analysis_status (
    id            SERIAL PRIMARY KEY,
    project_id    INTEGER      NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch        VARCHAR(255) NOT NULL DEFAULT 'main',
    status        VARCHAR(20)  NOT NULL DEFAULT 'pending',
    started_at    TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ,
    error_message TEXT,
    extra         JSONB,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (project_id, branch)
);

CREATE INDEX IF NOT EXISTS idx_branch_analysis_status_project_running
    ON branch_analysis_status (project_id) WHERE status = 'running';

COMMENT ON TABLE branch_analysis_status IS 'Branch analysis and project initialization task status';
COMMENT ON COLUMN branch_analysis_status.status IS 'pending|running|completed|failed';
COMMENT ON COLUMN branch_analysis_status.extra IS 'Optional task statistics and progress details';
