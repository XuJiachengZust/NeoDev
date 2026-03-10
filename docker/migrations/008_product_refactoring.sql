-- 产品化重构：引入 Product 层，产品级版本、三级需求（Epic/Story/Task）、Bug 管理
-- 兼容策略：旧表（projects, versions, requirements）完全保留，新增表和列

-- ============================================================
-- 1. 产品表
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    code        VARCHAR(64) UNIQUE,              -- 产品编码，可选
    description TEXT,
    owner       VARCHAR(128),
    status      VARCHAR(32) NOT NULL DEFAULT 'active',  -- active | archived
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE products IS '产品（顶层实体），包含多个项目';
COMMENT ON COLUMN products.code IS '产品唯一编码，如 NEODEV';
COMMENT ON COLUMN products.status IS 'active|archived';

-- ============================================================
-- 2. 产品-项目关联（Product 1:N Project）
-- ============================================================
ALTER TABLE projects ADD COLUMN IF NOT EXISTS product_id INTEGER REFERENCES products(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_projects_product_id ON projects(product_id);

COMMENT ON COLUMN projects.product_id IS '所属产品 ID，NULL 表示未归属任何产品';

-- ============================================================
-- 3. 产品级版本
-- ============================================================
CREATE TABLE IF NOT EXISTS product_versions (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    version_name    VARCHAR(255) NOT NULL,
    description     TEXT,
    status          VARCHAR(32) NOT NULL DEFAULT 'planning',  -- planning | developing | testing | released
    release_date    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_id, version_name)
);

CREATE INDEX IF NOT EXISTS idx_product_versions_product_id ON product_versions(product_id);

COMMENT ON TABLE product_versions IS '产品级版本，关联各项目的特定分支';
COMMENT ON COLUMN product_versions.status IS 'planning|developing|testing|released';

-- 产品版本-项目分支映射（一个产品版本关联各项目的分支）
CREATE TABLE IF NOT EXISTS product_version_branches (
    id                  SERIAL PRIMARY KEY,
    product_version_id  INTEGER NOT NULL REFERENCES product_versions(id) ON DELETE CASCADE,
    project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch              VARCHAR(255) NOT NULL,
    UNIQUE (product_version_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_pvb_version_id ON product_version_branches(product_version_id);
CREATE INDEX IF NOT EXISTS idx_pvb_project_id ON product_version_branches(project_id);

COMMENT ON TABLE product_version_branches IS '产品版本与各项目分支的映射';

-- ============================================================
-- 4. 产品级需求（三级：Epic → Story → Task）
-- ============================================================
CREATE TABLE IF NOT EXISTS product_requirements (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    parent_id       INTEGER REFERENCES product_requirements(id) ON DELETE CASCADE,
    level           VARCHAR(16) NOT NULL DEFAULT 'story',  -- epic | story | task
    title           VARCHAR(512) NOT NULL,
    description     TEXT,
    external_id     VARCHAR(255),
    status          VARCHAR(32) NOT NULL DEFAULT 'open',   -- open | in_progress | done | closed
    priority        VARCHAR(16) NOT NULL DEFAULT 'medium', -- low | medium | high | critical
    assignee        VARCHAR(128),
    version_id      INTEGER REFERENCES product_versions(id) ON DELETE SET NULL,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_req_product_id ON product_requirements(product_id);
CREATE INDEX IF NOT EXISTS idx_product_req_parent_id ON product_requirements(parent_id);
CREATE INDEX IF NOT EXISTS idx_product_req_version_id ON product_requirements(version_id);
CREATE INDEX IF NOT EXISTS idx_product_req_level ON product_requirements(level);

COMMENT ON TABLE product_requirements IS '产品级需求，支持三级结构: Epic → Story → Task';
COMMENT ON COLUMN product_requirements.level IS 'epic|story|task';
COMMENT ON COLUMN product_requirements.status IS 'open|in_progress|done|closed';
COMMENT ON COLUMN product_requirements.priority IS 'low|medium|high|critical';

-- 需求-提交关联（跨项目绑定）
CREATE TABLE IF NOT EXISTS product_requirement_commits (
    requirement_id  INTEGER NOT NULL REFERENCES product_requirements(id) ON DELETE CASCADE,
    commit_id       INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    PRIMARY KEY (requirement_id, commit_id)
);

CREATE INDEX IF NOT EXISTS idx_prc_commit_id ON product_requirement_commits(commit_id);

COMMENT ON TABLE product_requirement_commits IS '产品需求与提交的跨项目关联';

-- ============================================================
-- 5. Bug 管理
-- ============================================================
CREATE TABLE IF NOT EXISTS product_bugs (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    title           VARCHAR(512) NOT NULL,
    description     TEXT,
    external_id     VARCHAR(255),
    severity        VARCHAR(16) NOT NULL DEFAULT 'minor',    -- blocker | critical | major | minor | trivial
    status          VARCHAR(32) NOT NULL DEFAULT 'open',     -- open | confirmed | fixing | resolved | closed
    priority        VARCHAR(16) NOT NULL DEFAULT 'medium',   -- low | medium | high | critical
    assignee        VARCHAR(128),
    reporter        VARCHAR(128),
    version_id      INTEGER REFERENCES product_versions(id) ON DELETE SET NULL,
    fix_version_id  INTEGER REFERENCES product_versions(id) ON DELETE SET NULL,
    requirement_id  INTEGER REFERENCES product_requirements(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_product_bugs_product_id ON product_bugs(product_id);
CREATE INDEX IF NOT EXISTS idx_product_bugs_version_id ON product_bugs(version_id);
CREATE INDEX IF NOT EXISTS idx_product_bugs_status ON product_bugs(status);

COMMENT ON TABLE product_bugs IS '产品级 Bug，独立管理';
COMMENT ON COLUMN product_bugs.severity IS 'blocker|critical|major|minor|trivial';
COMMENT ON COLUMN product_bugs.status IS 'open|confirmed|fixing|resolved|closed';

-- Bug-提交关联
CREATE TABLE IF NOT EXISTS product_bug_commits (
    bug_id      INTEGER NOT NULL REFERENCES product_bugs(id) ON DELETE CASCADE,
    commit_id   INTEGER NOT NULL REFERENCES commits(id) ON DELETE CASCADE,
    PRIMARY KEY (bug_id, commit_id)
);

CREATE INDEX IF NOT EXISTS idx_pbc_commit_id ON product_bug_commits(commit_id);

COMMENT ON TABLE product_bug_commits IS 'Bug 修复提交关联';

-- ============================================================
-- 6. Agent 会话扩展：支持产品级上下文
-- ============================================================
ALTER TABLE ai_agent_conversations ADD COLUMN IF NOT EXISTS product_id INTEGER REFERENCES products(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_agent_conv_product ON ai_agent_conversations(product_id);

COMMENT ON COLUMN ai_agent_conversations.product_id IS '产品级 Agent 会话的产品 ID';
