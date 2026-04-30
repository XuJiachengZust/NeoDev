-- 023: audit manual graph mutations that are projected into branch facts.

CREATE TABLE IF NOT EXISTS graph_operation_logs (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_name TEXT,
    snapshot_id INTEGER REFERENCES branch_snapshots(id) ON DELETE SET NULL,
    object_kind VARCHAR(32) NOT NULL,
    object_id   TEXT NOT NULL,
    operation   VARCHAR(32) NOT NULL,
    before_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    after_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor       TEXT,
    source      VARCHAR(32) NOT NULL DEFAULT 'manual',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_graph_operation_logs_object_kind
        CHECK (object_kind IN ('node', 'edge', 'node_type', 'edge_type')),
    CONSTRAINT chk_graph_operation_logs_operation
        CHECK (operation IN ('upsert', 'update', 'archive', 'delete'))
);

CREATE INDEX IF NOT EXISTS idx_graph_operation_logs_scope
    ON graph_operation_logs(project_id, branch_name, snapshot_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_graph_operation_logs_object
    ON graph_operation_logs(project_id, object_kind, object_id, created_at DESC);
