-- 018: CLI metadata foundation tables
-- No backfill for legacy rows is required; this migration only defines new schema objects.

CREATE TABLE IF NOT EXISTS doc_bindings (
    id                  SERIAL PRIMARY KEY,
    product_id          INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    repo_path           TEXT NOT NULL DEFAULT '',
    repo_url            TEXT NOT NULL DEFAULT '',
    default_branch      VARCHAR(255) NOT NULL DEFAULT 'main',
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE doc_bindings
    ADD COLUMN IF NOT EXISTS repo_path TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS repo_url TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS default_branch VARCHAR(255) NOT NULL DEFAULT 'main',
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE doc_bindings
    ALTER COLUMN repo_path SET DEFAULT '',
    ALTER COLUMN repo_url SET DEFAULT '',
    ALTER COLUMN default_branch SET DEFAULT 'main',
    ALTER COLUMN is_active SET DEFAULT true;

CREATE INDEX IF NOT EXISTS idx_doc_bindings_product_id
    ON doc_bindings(product_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_bindings_active_product
    ON doc_bindings(product_id)
    WHERE is_active = true;


CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    doc_binding_id  INTEGER NOT NULL REFERENCES doc_bindings(id) ON DELETE CASCADE,
    doc_id          VARCHAR(128) NOT NULL,
    relative_path   TEXT NOT NULL,
    doc_type        VARCHAR(64) NOT NULL DEFAULT 'markdown',
    front_matter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    relations_json  JSONB NOT NULL DEFAULT '{}'::jsonb,
    status          VARCHAR(32) NOT NULL DEFAULT 'active',
    last_seen_commit VARCHAR(40),
    last_scanned_at TIMESTAMPTZ,
    title           VARCHAR(512),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS doc_type VARCHAR(64) NOT NULL DEFAULT 'markdown',
    ADD COLUMN IF NOT EXISTS front_matter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS relations_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS last_seen_commit VARCHAR(40),
    ADD COLUMN IF NOT EXISTS last_scanned_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS title VARCHAR(512);

ALTER TABLE documents
    ALTER COLUMN doc_type SET DEFAULT 'markdown',
    ALTER COLUMN front_matter_json SET DEFAULT '{}'::jsonb,
    ALTER COLUMN relations_json SET DEFAULT '{}'::jsonb,
    ALTER COLUMN status SET DEFAULT 'active';

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_doc_id
    ON documents(doc_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_binding_path
    ON documents(doc_binding_id, relative_path);


CREATE TABLE IF NOT EXISTS doc_changes (
    id              SERIAL PRIMARY KEY,
    document_id     INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    doc_change_id   VARCHAR(128) NOT NULL,
    source_commit   VARCHAR(40),
    summary         TEXT,
    details_json    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by      VARCHAR(255),
    implemented_at  TIMESTAMPTZ,
    status          VARCHAR(32) NOT NULL DEFAULT 'pending_implementation',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_doc_changes_status
        CHECK (
            status IN (
                'pending_implementation',
                'in_implementation',
                'implemented'
            )
        )
);

ALTER TABLE doc_changes
    ADD COLUMN IF NOT EXISTS source_commit VARCHAR(40),
    ADD COLUMN IF NOT EXISTS summary TEXT,
    ADD COLUMN IF NOT EXISTS details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS created_by VARCHAR(255),
    ADD COLUMN IF NOT EXISTS implemented_at TIMESTAMPTZ;

ALTER TABLE doc_changes
    DROP COLUMN IF EXISTS change_summary;

ALTER TABLE doc_changes
    ALTER COLUMN status SET DEFAULT 'pending_implementation';

ALTER TABLE doc_changes
    ALTER COLUMN details_json SET DEFAULT '{}'::jsonb;

ALTER TABLE doc_changes
    DROP CONSTRAINT IF EXISTS chk_doc_changes_status;

ALTER TABLE doc_changes
    ADD CONSTRAINT chk_doc_changes_status
    CHECK (
        status IN (
            'pending_implementation',
            'in_implementation',
            'implemented'
        )
    );

CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_changes_doc_change_id
    ON doc_changes(doc_change_id);

CREATE INDEX IF NOT EXISTS idx_doc_changes_document_id
    ON doc_changes(document_id);


CREATE TABLE IF NOT EXISTS code_change_links (
    id              SERIAL PRIMARY KEY,
    doc_change_id   INTEGER NOT NULL REFERENCES doc_changes(id) ON DELETE CASCADE,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch          VARCHAR(255) NOT NULL,
    commit_sha      VARCHAR(40) NOT NULL,
    commit_message  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE code_change_links
    ADD COLUMN IF NOT EXISTS commit_message TEXT;

CREATE INDEX IF NOT EXISTS idx_code_change_links_project_branch_sha
    ON code_change_links(project_id, branch, commit_sha);

CREATE INDEX IF NOT EXISTS idx_code_change_links_doc_change_id
    ON code_change_links(doc_change_id);


CREATE TABLE IF NOT EXISTS dangerous_commit_records (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch          VARCHAR(255) NOT NULL,
    commit_sha      VARCHAR(40) NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'open',
    risk_level      VARCHAR(32) NOT NULL DEFAULT 'medium',
    resolved_by     VARCHAR(255),
    resolved_at     TIMESTAMPTZ,
    extra_json      JSONB NOT NULL DEFAULT '{}'::jsonb,
    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_dangerous_commit_records_status
        CHECK (status IN ('open', 'resolved'))
);

ALTER TABLE dangerous_commit_records
    ADD COLUMN IF NOT EXISTS risk_level VARCHAR(32) NOT NULL DEFAULT 'medium',
    ADD COLUMN IF NOT EXISTS reason TEXT,
    ADD COLUMN IF NOT EXISTS resolved_by VARCHAR(255),
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS extra_json JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE dangerous_commit_records
    ALTER COLUMN status SET DEFAULT 'open';

ALTER TABLE dangerous_commit_records
    ALTER COLUMN risk_level SET DEFAULT 'medium',
    ALTER COLUMN extra_json SET DEFAULT '{}'::jsonb;

ALTER TABLE dangerous_commit_records
    DROP CONSTRAINT IF EXISTS chk_dangerous_commit_records_status;

ALTER TABLE dangerous_commit_records
    ADD CONSTRAINT chk_dangerous_commit_records_status
    CHECK (status IN ('open', 'resolved'));

CREATE INDEX IF NOT EXISTS idx_dangerous_commit_records_project_status_created
    ON dangerous_commit_records(project_id, status, created_at);

CREATE INDEX IF NOT EXISTS idx_dangerous_commit_records_commit_sha
    ON dangerous_commit_records(commit_sha);
