-- Record Git branches per project for version-branch association UI.
CREATE TABLE IF NOT EXISTS git_branches (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, branch_name)
);

CREATE INDEX IF NOT EXISTS idx_git_branches_project_id ON git_branches(project_id);

-- Backfill from existing bound branches in versions table.
INSERT INTO git_branches (project_id, branch_name)
SELECT DISTINCT v.project_id, v.branch
FROM versions v
WHERE v.branch IS NOT NULL AND btrim(v.branch) <> ''
ON CONFLICT (project_id, branch_name) DO NOTHING;
