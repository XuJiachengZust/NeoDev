-- Phase 2: impact analysis tables (docs/数据结构设计-影响面分析.md 2.2, 6.2)
-- Order: projects -> versions -> requirements -> commits -> requirement_commits -> impact_analyses -> impact_analysis_commits

-- projects (Project aggregate root)
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    repo_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    watch_enabled BOOLEAN DEFAULT false,
    neo4j_database VARCHAR(255),
    neo4j_identifier VARCHAR(255)
);

-- versions (Project aggregate)
CREATE TABLE IF NOT EXISTS versions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch VARCHAR(255) NOT NULL,
    version_name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_parsed_commit VARCHAR(40),
    UNIQUE (project_id, branch)
);

CREATE INDEX IF NOT EXISTS idx_versions_project_id ON versions(project_id);

-- requirements (Requirement aggregate root)
CREATE TABLE IF NOT EXISTS requirements (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    external_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_requirements_project_id ON requirements(project_id);

-- commits
CREATE TABLE IF NOT EXISTS commits (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_id INTEGER NOT NULL REFERENCES versions(id) ON DELETE CASCADE,
    commit_sha VARCHAR(40) NOT NULL,
    message TEXT,
    author VARCHAR(255),
    committed_at TIMESTAMPTZ,
    UNIQUE (project_id, commit_sha)
);

CREATE INDEX IF NOT EXISTS idx_commits_project_id ON commits(project_id);
CREATE INDEX IF NOT EXISTS idx_commits_version_id ON commits(version_id);

-- requirement_commits (Requirement aggregate: N-M)
CREATE TABLE IF NOT EXISTS requirement_commits (
    requirement_id INTEGER NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    PRIMARY KEY (requirement_id, commit_id)
);

CREATE INDEX IF NOT EXISTS idx_requirement_commits_commit_id ON requirement_commits(commit_id);

-- impact_analyses (ImpactAnalysis aggregate root)
CREATE TABLE IF NOT EXISTS impact_analyses (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status VARCHAR(64) NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    result_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_impact_analyses_project_id ON impact_analyses(project_id);

-- impact_analysis_commits (ImpactAnalysis aggregate: analysis-commits)
CREATE TABLE IF NOT EXISTS impact_analysis_commits (
    impact_analysis_id INTEGER NOT NULL REFERENCES impact_analyses(id) ON DELETE CASCADE,
    commit_id INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    PRIMARY KEY (impact_analysis_id, commit_id)
);

CREATE INDEX IF NOT EXISTS idx_impact_analysis_commits_commit_id ON impact_analysis_commits(commit_id);
