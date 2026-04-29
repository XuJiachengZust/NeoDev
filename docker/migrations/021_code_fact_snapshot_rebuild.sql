-- 021: rebuild graph storage around project-level code facts.
-- This migration intentionally drops the old file-level branch snapshot storage.

DROP TABLE IF EXISTS branch_snapshot_facts CASCADE;
DROP TABLE IF EXISTS branch_snapshot_entries CASCADE;
DROP TABLE IF EXISTS branch_snapshots CASCADE;
DROP TABLE IF EXISTS doc_code_links CASCADE;
DROP TABLE IF EXISTS code_facts CASCADE;
DROP TABLE IF EXISTS product_version_branches CASCADE;
DROP TABLE IF EXISTS graph_edges CASCADE;
DROP TABLE IF EXISTS graph_nodes CASCADE;
DROP TABLE IF EXISTS graph_relation_types CASCADE;
DROP TABLE IF EXISTS graph_node_types CASCADE;

CREATE TABLE graph_node_types (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type_key VARCHAR(128) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_graph_node_types_status CHECK (status IN ('active', 'archived')),
    CONSTRAINT uq_graph_node_types_project_key UNIQUE (project_id, type_key)
);

CREATE TABLE graph_relation_types (
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
    CONSTRAINT chk_graph_relation_types_status CHECK (status IN ('active', 'archived')),
    CONSTRAINT uq_graph_relation_types_project_key UNIQUE (project_id, type_key)
);

CREATE TABLE graph_nodes (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    node_id VARCHAR(255) NOT NULL,
    type_key VARCHAR(128) NOT NULL,
    name TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    source VARCHAR(32) NOT NULL DEFAULT 'manual',
    file_path TEXT,
    content_hash VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_graph_nodes_status CHECK (status IN ('active', 'archived')),
    CONSTRAINT uq_graph_nodes_project_node_id UNIQUE (project_id, node_id)
);

CREATE INDEX idx_graph_nodes_project_type
    ON graph_nodes(project_id, type_key);

CREATE TABLE graph_edges (
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
    ),
    CONSTRAINT uq_graph_edges_project_edge_id UNIQUE (project_id, edge_id)
);

CREATE INDEX idx_graph_edges_from_node
    ON graph_edges(from_project_id, from_node_id);

CREATE INDEX idx_graph_edges_to_node
    ON graph_edges(to_project_id, to_node_id);

CREATE INDEX idx_graph_edges_project_type
    ON graph_edges(project_id, type_key);

CREATE TABLE product_version_branches (
    id                 SERIAL PRIMARY KEY,
    product_version_id INTEGER NOT NULL REFERENCES product_versions(id) ON DELETE CASCADE,
    project_id         INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_name        TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_product_version_branches_version_project
        UNIQUE (product_version_id, project_id)
);

CREATE INDEX idx_product_version_branches_project_branch
    ON product_version_branches(project_id, branch_name);

CREATE TABLE branch_snapshots (
    id            SERIAL PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_name   TEXT NOT NULL,
    head_commit   VARCHAR(64),
    snapshot_hash VARCHAR(128),
    status        VARCHAR(32) NOT NULL DEFAULT 'completed',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_branch_snapshots_status
        CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE INDEX idx_branch_snapshots_project_branch
    ON branch_snapshots(project_id, branch_name, id DESC);

CREATE INDEX idx_branch_snapshots_project_branch_status
    ON branch_snapshots(project_id, branch_name, status);

CREATE TABLE code_facts (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    fact_id         VARCHAR(255) NOT NULL,
    symbol_key      VARCHAR(255) NOT NULL,
    node_type       VARCHAR(64) NOT NULL,
    file_path       TEXT,
    qualified_name  TEXT,
    name            TEXT,
    signature_hash  VARCHAR(128),
    content_hash    VARCHAR(128),
    structure_hash  VARCHAR(128),
    parent_fact_id  VARCHAR(255),
    start_line      INTEGER,
    end_line        INTEGER,
    metadata_json   JSONB NOT NULL DEFAULT '{}'::jsonb,
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_code_facts_project_fact UNIQUE (project_id, fact_id),
    CONSTRAINT chk_code_facts_node_type
        CHECK (node_type IN ('File', 'Class', 'Interface', 'Enum', 'Annotation', 'Method', 'Function', 'Constructor')),
    CONSTRAINT chk_code_facts_status CHECK (status IN ('active', 'archived'))
);

CREATE INDEX idx_code_facts_project_symbol
    ON code_facts(project_id, symbol_key);

CREATE INDEX idx_code_facts_project_type
    ON code_facts(project_id, node_type);

CREATE TABLE branch_snapshot_facts (
    id          SERIAL PRIMARY KEY,
    snapshot_id INTEGER NOT NULL REFERENCES branch_snapshots(id) ON DELETE CASCADE,
    fact_id     VARCHAR(255) NOT NULL,
    CONSTRAINT uq_branch_snapshot_facts_snapshot_fact UNIQUE (snapshot_id, fact_id)
);

CREATE INDEX idx_branch_snapshot_facts_snapshot
    ON branch_snapshot_facts(snapshot_id);

CREATE INDEX idx_branch_snapshot_facts_fact
    ON branch_snapshot_facts(fact_id);

CREATE TABLE doc_code_links (
    id                   SERIAL PRIMARY KEY,
    product_id           INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_version_id   INTEGER REFERENCES product_versions(id) ON DELETE CASCADE,
    doc_id               TEXT NOT NULL,
    doc_node_id          TEXT,
    code_project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    symbol_key           VARCHAR(255) NOT NULL,
    resolved_fact_id     VARCHAR(255),
    resolved_snapshot_id INTEGER REFERENCES branch_snapshots(id) ON DELETE SET NULL,
    relation_type        VARCHAR(64) NOT NULL,
    source               VARCHAR(64) NOT NULL DEFAULT 'manual',
    confidence           DOUBLE PRECISION,
    resolution_status    VARCHAR(32) NOT NULL DEFAULT 'unresolved',
    metadata_json        JSONB NOT NULL DEFAULT '{}'::jsonb,
    status               VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_doc_code_links_relation_type
        CHECK (relation_type IN ('describes', 'implements', 'verifies', 'references', 'depends_on', 'tests')),
    CONSTRAINT chk_doc_code_links_resolution_status
        CHECK (resolution_status IN ('resolved', 'unresolved', 'stale', 'ambiguous')),
    CONSTRAINT chk_doc_code_links_status
        CHECK (status IN ('active', 'archived'))
);

CREATE INDEX idx_doc_code_links_product_doc
    ON doc_code_links(product_id, doc_id);

CREATE INDEX idx_doc_code_links_project_symbol
    ON doc_code_links(code_project_id, symbol_key);
