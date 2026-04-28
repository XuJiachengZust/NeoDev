CREATE TABLE IF NOT EXISTS graph_node_types (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type_key VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_graph_node_types_status CHECK (status IN ('active', 'archived'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_graph_node_types_project_key
    ON graph_node_types (project_id, type_key);

CREATE TABLE IF NOT EXISTS graph_relation_types (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type_key VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    allowed_from_types JSONB NOT NULL DEFAULT '[]'::jsonb,
    allowed_to_types JSONB NOT NULL DEFAULT '[]'::jsonb,
    cross_project_allowed BOOLEAN NOT NULL DEFAULT true,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_graph_relation_types_status CHECK (status IN ('active', 'archived'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_graph_relation_types_project_key
    ON graph_relation_types (project_id, type_key);

CREATE TABLE IF NOT EXISTS graph_nodes (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL,
    type_key VARCHAR(128) NOT NULL,
    name TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    source VARCHAR(32) NOT NULL DEFAULT 'manual',
    repo_id INTEGER,
    file_path TEXT,
    content_hash VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_graph_nodes_status CHECK (status IN ('active', 'archived'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_graph_nodes_project_node_id
    ON graph_nodes (project_id, node_id);

CREATE INDEX IF NOT EXISTS idx_graph_nodes_project_type
    ON graph_nodes (project_id, type_key);

CREATE TABLE IF NOT EXISTS graph_edges (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    edge_id VARCHAR(255) NOT NULL,
    from_node_id VARCHAR(255) NOT NULL,
    to_node_id VARCHAR(255) NOT NULL,
    from_project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    to_project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type_key VARCHAR(128) NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_graph_edges_status CHECK (status IN ('active', 'archived')),
    CONSTRAINT chk_graph_edges_relation_owner CHECK (
        project_id = from_project_id OR project_id = to_project_id
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_graph_edges_project_edge_id
    ON graph_edges (project_id, edge_id);

CREATE INDEX IF NOT EXISTS idx_graph_edges_from_node
    ON graph_edges (from_project_id, from_node_id);

CREATE INDEX IF NOT EXISTS idx_graph_edges_to_node
    ON graph_edges (to_project_id, to_node_id);

CREATE INDEX IF NOT EXISTS idx_graph_edges_project_type
    ON graph_edges (project_id, type_key);
