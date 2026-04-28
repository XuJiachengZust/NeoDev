-- Branch snapshot metadata for repository-level graph storage MVP.

CREATE TABLE IF NOT EXISTS branch_snapshots (
    id                  SERIAL PRIMARY KEY,
    project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    repo_id             INTEGER NOT NULL,
    branch              VARCHAR(255) NOT NULL,
    head_commit         VARCHAR(40),
    last_parsed_commit  VARCHAR(40),
    base_snapshot_id    INTEGER REFERENCES branch_snapshots(id) ON DELETE SET NULL,
    created_from_action VARCHAR(32) NOT NULL,
    status              VARCHAR(32) NOT NULL DEFAULT 'completed',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_branch_snapshots_project_branch
    ON branch_snapshots(project_id, branch, id DESC);

CREATE INDEX IF NOT EXISTS idx_branch_snapshots_head
    ON branch_snapshots(project_id, branch, head_commit);

CREATE TABLE IF NOT EXISTS branch_snapshot_entries (
    id                  SERIAL PRIMARY KEY,
    snapshot_id          INTEGER NOT NULL REFERENCES branch_snapshots(id) ON DELETE CASCADE,
    project_id           INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    repo_id              INTEGER NOT NULL,
    file_path            TEXT NOT NULL,
    file_node_id         TEXT NOT NULL,
    file_content_hash    TEXT NOT NULL,
    visible              BOOLEAN NOT NULL DEFAULT true,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (snapshot_id, file_path)
);

CREATE INDEX IF NOT EXISTS idx_branch_snapshot_entries_snapshot
    ON branch_snapshot_entries(snapshot_id);

CREATE INDEX IF NOT EXISTS idx_branch_snapshot_entries_file
    ON branch_snapshot_entries(project_id, repo_id, file_path);
