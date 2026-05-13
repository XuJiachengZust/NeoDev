-- NeoDev PostgreSQL initialization SQL
-- Consolidated database initialization for new deployments.


-- ============================================================
-- Source: docker\init-pgvector.sql
-- ============================================================
-- 首次启动时自动启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- Section: 001_impact_analysis_tables.sql
-- ============================================================
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
DROP INDEX IF EXISTS uq_projects_name;

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

-- ============================================================
-- Section: 002_versions_branch_nullable.sql
-- ============================================================
-- Allow version without bound branch: create version with optional branch (Phase 3+).
ALTER TABLE versions ALTER COLUMN branch DROP NOT NULL;

-- ============================================================
-- Section: 003_git_branches.sql
-- ============================================================
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

-- ============================================================
-- Section: 004_project_repo_auth.sql
-- ============================================================
-- Persist remote repository authentication on project for re-use.
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS repo_username VARCHAR(255),
    ADD COLUMN IF NOT EXISTS repo_password TEXT;

-- ============================================================
-- Section: 006_branch_analysis_status.sql
-- ============================================================
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

-- ============================================================
-- Section: 007_ai_agent_tables.sql
-- ============================================================
-- AI Agent 智能体会话与消息表
-- 5 张表: sessions, conversations, messages, context_snapshots, sandboxes

-- 1. 会话（浏览器级，由前端 localStorage UUID 标识）
CREATE TABLE IF NOT EXISTS ai_agent_sessions (
    id          VARCHAR(64) PRIMARY KEY,
    user_id     VARCHAR(128) NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);


COMMENT ON TABLE ai_agent_sessions IS '浏览器级 Agent 会话，前端 localStorage 持久化 UUID';

-- 2. 会话内的对话（每个 route_context_key + project 组合一个）
CREATE TABLE IF NOT EXISTS ai_agent_conversations (
    id                  SERIAL PRIMARY KEY,
    session_id          VARCHAR(64) NOT NULL REFERENCES ai_agent_sessions(id) ON DELETE CASCADE,
    route_context_key   VARCHAR(64) NOT NULL,
    project_id          INT NULL,
    agent_profile       VARCHAR(64) NOT NULL DEFAULT 'default',
    thread_id           VARCHAR(128) NOT NULL,
    title               VARCHAR(256) NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
    -- 唯一性通过下方索引保证
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_conv_unique_ctx
    ON ai_agent_conversations (session_id, route_context_key, COALESCE(project_id, -1));

CREATE INDEX IF NOT EXISTS idx_agent_conv_session
    ON ai_agent_conversations (session_id);

CREATE INDEX IF NOT EXISTS idx_agent_conv_thread
    ON ai_agent_conversations (thread_id);

COMMENT ON TABLE ai_agent_conversations IS '路由驱动的对话，同一 session + route + project 复用同一对话';
COMMENT ON COLUMN ai_agent_conversations.thread_id IS 'LangGraph checkpointer 使用的线程 ID';

-- 3. 对话消息
CREATE TABLE IF NOT EXISTS ai_agent_messages (
    id                  SERIAL PRIMARY KEY,
    conversation_id     INT NOT NULL REFERENCES ai_agent_conversations(id) ON DELETE CASCADE,
    role                VARCHAR(32) NOT NULL,
    content             TEXT NOT NULL DEFAULT '',
    tool_calls          JSONB NULL,
    tool_call_id        VARCHAR(128) NULL,
    token_in            INT NULL,
    token_out           INT NULL,
    latency_ms          INT NULL,
    model               VARCHAR(128) NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_msg_conv
    ON ai_agent_messages (conversation_id, created_at);

COMMENT ON TABLE ai_agent_messages IS 'Agent 对话消息（user/assistant/tool/system）';
COMMENT ON COLUMN ai_agent_messages.role IS 'user|assistant|tool|system';
COMMENT ON COLUMN ai_agent_messages.tool_calls IS 'assistant 消息中的工具调用列表';
COMMENT ON COLUMN ai_agent_messages.tool_call_id IS 'tool 消息对应的 tool_call_id';

-- 4. 上下文快照（用于长对话恢复）
CREATE TABLE IF NOT EXISTS ai_agent_context_snapshots (
    id                  SERIAL PRIMARY KEY,
    conversation_id     INT NOT NULL REFERENCES ai_agent_conversations(id) ON DELETE CASCADE,
    summary             TEXT NOT NULL,
    state_json          JSONB NULL,
    last_message_id     INT NULL REFERENCES ai_agent_messages(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_snapshot_conv
    ON ai_agent_context_snapshots (conversation_id, created_at DESC);

COMMENT ON TABLE ai_agent_context_snapshots IS '对话上下文快照，用于长对话恢复和摘要';

-- 5. 沙箱（会话级）
CREATE TABLE IF NOT EXISTS ai_agent_sandboxes (
    id                  SERIAL PRIMARY KEY,
    session_id          VARCHAR(64) NOT NULL REFERENCES ai_agent_sessions(id) ON DELETE CASCADE,
    sandbox_id          VARCHAR(128) NOT NULL,
    provider            VARCHAR(64) NOT NULL DEFAULT 'local',
    status              VARCHAR(32) NOT NULL DEFAULT 'active',
    workspace_path      TEXT NULL,
    mounted_project_id  INT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (session_id, sandbox_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_sandbox_session
    ON ai_agent_sandboxes (session_id) WHERE status = 'active';

COMMENT ON TABLE ai_agent_sandboxes IS '会话级沙箱，用于代码执行和文件操作';
COMMENT ON COLUMN ai_agent_sandboxes.status IS 'active|recycled|error';

-- ============================================================
-- Section: 008_product_refactoring.sql
-- ============================================================
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
CREATE UNIQUE INDEX IF NOT EXISTS uq_products_name ON products(name);

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
    branch_name         VARCHAR(255) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_version_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_pvb_version_id ON product_version_branches(product_version_id);
CREATE INDEX IF NOT EXISTS idx_pvb_project_id ON product_version_branches(project_id);
DROP INDEX IF EXISTS uq_pvb_project_branch;
CREATE INDEX IF NOT EXISTS idx_product_version_branches_project_branch
    ON product_version_branches(project_id, branch_name);

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

-- ============================================================
-- Section: 009_version_required.sql
-- ============================================================
-- 版本必填：需求和 Bug 的 version_id 改为 NOT NULL
-- 将已有无 version_id 的需求/Bug 迁移到 Backlog 版本

DO $$
DECLARE r RECORD; backlog_id INT;
BEGIN
  FOR r IN SELECT DISTINCT product_id FROM product_requirements WHERE version_id IS NULL
  LOOP
    INSERT INTO product_versions(product_id, version_name, status)
    VALUES (r.product_id, 'Backlog', 'planning')
    ON CONFLICT (product_id, version_name) DO NOTHING
    RETURNING id INTO backlog_id;
    IF backlog_id IS NULL THEN
      SELECT id INTO backlog_id FROM product_versions
      WHERE product_id = r.product_id AND version_name = 'Backlog';
    END IF;
    UPDATE product_requirements SET version_id = backlog_id
    WHERE product_id = r.product_id AND version_id IS NULL;
  END LOOP;

  FOR r IN SELECT DISTINCT product_id FROM product_bugs WHERE version_id IS NULL
  LOOP
    INSERT INTO product_versions(product_id, version_name, status)
    VALUES (r.product_id, 'Backlog', 'planning')
    ON CONFLICT (product_id, version_name) DO NOTHING
    RETURNING id INTO backlog_id;
    IF backlog_id IS NULL THEN
      SELECT id INTO backlog_id FROM product_versions
      WHERE product_id = r.product_id AND version_name = 'Backlog';
    END IF;
    UPDATE product_bugs SET version_id = backlog_id
    WHERE product_id = r.product_id AND version_id IS NULL;
  END LOOP;
END $$;

ALTER TABLE product_requirements ALTER COLUMN version_id SET NOT NULL;
ALTER TABLE product_bugs ALTER COLUMN version_id SET NOT NULL;

-- 将 ON DELETE SET NULL 改为 ON DELETE RESTRICT（与 NOT NULL 兼容）
ALTER TABLE product_requirements
  DROP CONSTRAINT product_requirements_version_id_fkey,
  ADD CONSTRAINT product_requirements_version_id_fkey
    FOREIGN KEY (version_id) REFERENCES product_versions(id) ON DELETE RESTRICT;

ALTER TABLE product_bugs
  DROP CONSTRAINT product_bugs_version_id_fkey,
  ADD CONSTRAINT product_bugs_version_id_fkey
    FOREIGN KEY (version_id) REFERENCES product_versions(id) ON DELETE RESTRICT;

-- ============================================================
-- Section: 010_project_repo_url.sql
-- ============================================================
-- 010: 新增 repo_url 字段，保存原始远程仓库地址（repo_path 会被克隆后覆盖为本地路径）
ALTER TABLE projects ADD COLUMN IF NOT EXISTS repo_url TEXT;

-- 回填：如果现有 repo_path 是远程地址则复制到 repo_url
UPDATE projects SET repo_url = repo_path
WHERE repo_url IS NULL
  AND (repo_path LIKE 'http://%' OR repo_path LIKE 'https://%' OR repo_path LIKE 'git@%');

-- ============================================================
-- Section: 011_agent_conversation_enhancements.sql
-- ============================================================
-- Agent 对话增强：版本感知 + 对话管理
-- 新增 version_id（关联版本）和 is_active（激活标记）

-- 1. 新增字段
ALTER TABLE ai_agent_conversations
  ADD COLUMN IF NOT EXISTS version_id INTEGER REFERENCES product_versions(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

-- 2. 处理历史数据：旧的同 session+product 多条对话只保留最新一条为 active
WITH ranked AS (
  SELECT id,
         ROW_NUMBER() OVER (PARTITION BY session_id, product_id ORDER BY updated_at DESC) AS rn
  FROM ai_agent_conversations
  WHERE product_id IS NOT NULL AND is_active = true
)
UPDATE ai_agent_conversations
SET is_active = false
WHERE id IN (SELECT id FROM ranked WHERE rn > 1);

-- 3. 替换旧唯一索引：旧索引按 (session, route, project) 约束所有行，
--    但产品模式下同一对话的 route_context_key 会随页面切换动态更新，
--    所以旧索引只应约束非产品对话（product_id IS NULL）。
DROP INDEX IF EXISTS idx_agent_conv_unique_ctx;
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_conv_unique_ctx
    ON ai_agent_conversations (session_id, route_context_key, COALESCE(project_id, -1))
    WHERE product_id IS NULL;

-- 4. 唯一索引：同一 session + product 只有一个激活对话
CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_conv_active_product
  ON ai_agent_conversations (session_id, product_id)
  WHERE is_active = true AND product_id IS NOT NULL;

-- 5. 索引: 按 session+product 查历史对话列表
CREATE INDEX IF NOT EXISTS idx_agent_conv_session_product
  ON ai_agent_conversations (session_id, product_id, updated_at DESC)
  WHERE product_id IS NOT NULL;

COMMENT ON COLUMN ai_agent_conversations.version_id IS '当前关联的产品版本 ID（随页面切换更新）';
COMMENT ON COLUMN ai_agent_conversations.is_active IS '是否为该 session+product 下的激活对话';

-- ============================================================
-- Section: 012_impact_analysis_enhancements.sql
-- ============================================================
-- 012: impact_analyses 增加 title 和 version_id 列
ALTER TABLE impact_analyses ADD COLUMN IF NOT EXISTS title VARCHAR(100);
ALTER TABLE impact_analyses ADD COLUMN IF NOT EXISTS version_id INTEGER REFERENCES versions(id);
CREATE INDEX IF NOT EXISTS idx_impact_analyses_version ON impact_analyses(version_id);

-- ============================================================
-- Section: 013_version_feature_summaries.sql
-- ============================================================
-- 版本功能总结：AI 预处理完成后自动生成的项目功能概述
CREATE TABLE IF NOT EXISTS version_feature_summaries (
    id                 SERIAL PRIMARY KEY,
    product_version_id INTEGER      NOT NULL REFERENCES product_versions(id) ON DELETE CASCADE,
    project_id         INTEGER      NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch             VARCHAR(255) NOT NULL,
    status             VARCHAR(20)  NOT NULL DEFAULT 'pending',   -- pending/running/completed/failed
    summary            TEXT,
    error_message      TEXT,
    triggered_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    finished_at        TIMESTAMPTZ,
    UNIQUE (product_version_id, project_id)
);

-- ============================================================
-- Section: 014_requirement_doc_meta.sql
-- ============================================================
-- 需求文档轻量元数据：版本号、生成方式、文件路径（内容在文件系统）
CREATE TABLE IF NOT EXISTS requirement_doc_meta (
    id              SERIAL PRIMARY KEY,
    requirement_id   INTEGER NOT NULL UNIQUE REFERENCES product_requirements(id) ON DELETE CASCADE,
    version         INTEGER NOT NULL DEFAULT 1,
    generated_by    VARCHAR(32),   -- 'manual' | 'agent' | 'workflow'
    file_path       VARCHAR(512),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_req_doc_meta_req_id ON requirement_doc_meta(requirement_id);

COMMENT ON TABLE requirement_doc_meta IS '需求文档元数据，正文存于文件系统 /data/requirement_docs/{product_id}/{requirement_id}/doc.md';

-- ============================================================
-- Section: 016_doc_generation_status.sql
-- ============================================================
-- 016: 需求文档生成状态持久化
ALTER TABLE requirement_doc_meta
  ADD COLUMN IF NOT EXISTS generation_status VARCHAR(32) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS generation_started_at TIMESTAMPTZ DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS generation_error TEXT DEFAULT NULL;

-- ============================================================
-- Section: 017_split_suggestions.sql
-- ============================================================
-- 拆分建议结构化存储（从文档内嵌文本迁移到独立表）
CREATE TABLE IF NOT EXISTS requirement_split_suggestions (
    id              SERIAL PRIMARY KEY,
    requirement_id  INTEGER NOT NULL REFERENCES product_requirements(id) ON DELETE CASCADE,
    suggestions     JSONB NOT NULL DEFAULT '[]'::jsonb,
    generated_by    VARCHAR(32),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_split_suggestions_req UNIQUE (requirement_id)
);

-- ============================================================
-- Section: 018_cli_metadata_foundation.sql
-- ============================================================
-- 018: CLI metadata foundation tables
-- No backfill for legacy rows is required; this migration only defines new schema objects.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS doc_bindings (
    id                  SERIAL PRIMARY KEY,
    product_id          INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_version_id  INTEGER NOT NULL REFERENCES product_versions(id) ON DELETE CASCADE,
    repo_path           TEXT NOT NULL DEFAULT '',
    repo_url            TEXT NOT NULL DEFAULT '',
    git_source_key      TEXT NOT NULL DEFAULT '',
    default_branch      VARCHAR(255) NOT NULL DEFAULT 'main',
    is_active           BOOLEAN NOT NULL DEFAULT true,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE doc_bindings
    ADD COLUMN IF NOT EXISTS product_version_id INTEGER REFERENCES product_versions(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS repo_path TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS repo_url TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS git_source_key TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS default_branch VARCHAR(255) NOT NULL DEFAULT 'main',
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

ALTER TABLE doc_bindings
    ALTER COLUMN product_version_id SET NOT NULL,
    ALTER COLUMN repo_path SET DEFAULT '',
    ALTER COLUMN repo_url SET DEFAULT '',
    ALTER COLUMN default_branch SET DEFAULT 'main',
    ALTER COLUMN is_active SET DEFAULT true;

CREATE INDEX IF NOT EXISTS idx_doc_bindings_product_id
    ON doc_bindings(product_id);

DROP INDEX IF EXISTS uq_doc_bindings_active_product;

CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_bindings_active_version
    ON doc_bindings(product_version_id)
    WHERE is_active = true;

UPDATE doc_bindings
   SET git_source_key = COALESCE(
       NULLIF(
           CASE
               WHEN btrim(repo_url) <> '' THEN
                   regexp_replace(
                       regexp_replace(
                           regexp_replace(
                               lower(split_part(btrim(repo_url), '://', 1)) || '://' ||
                               lower(split_part(split_part(btrim(repo_url), '://', 2), '/', 1)) ||
                               CASE
                                   WHEN position('/' in split_part(btrim(repo_url), '://', 2)) > 0
                                   THEN substring(
                                       split_part(btrim(repo_url), '://', 2)
                                       FROM position('/' in split_part(btrim(repo_url), '://', 2))
                                   )
                                   ELSE ''
                               END,
                               '\.git$',
                               '',
                               'i'
                           ),
                           '/+$',
                           ''
                       ),
                       '\\',
                       '/',
                       'g'
                   )
               ELSE ''
           END,
           ''
       ),
       NULLIF(
           regexp_replace(
               regexp_replace(
                   regexp_replace(btrim(replace(repo_path, '\', '/')), '\.git$', '', 'i'),
                   '/+$',
                   ''
               ),
               '\\',
               '/',
               'g'
           ),
           ''
       ),
       ''
   )
 WHERE git_source_key = '';

DROP INDEX IF EXISTS uq_doc_bindings_active_repo_url_source;
DROP INDEX IF EXISTS uq_doc_bindings_active_repo_path_source;

CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_bindings_active_git_source_key
    ON doc_bindings(git_source_key, default_branch)
    WHERE is_active = true
      AND git_source_key <> '';


CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL PRIMARY KEY,
    doc_binding_id  INTEGER NOT NULL REFERENCES doc_bindings(id) ON DELETE CASCADE,
    product_version_id INTEGER REFERENCES product_versions(id) ON DELETE CASCADE,
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
    ADD COLUMN IF NOT EXISTS product_version_id INTEGER REFERENCES product_versions(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS doc_type VARCHAR(64) NOT NULL DEFAULT 'markdown',
    ADD COLUMN IF NOT EXISTS front_matter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS relations_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS last_seen_commit VARCHAR(40),
    ADD COLUMN IF NOT EXISTS last_scanned_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS title VARCHAR(512),
    ADD COLUMN IF NOT EXISTS body_text TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS content_hash TEXT,
    ADD COLUMN IF NOT EXISTS graph_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS chunk_status VARCHAR(32) NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE documents
    ALTER COLUMN doc_type SET DEFAULT 'markdown',
    ALTER COLUMN front_matter_json SET DEFAULT '{}'::jsonb,
    ALTER COLUMN relations_json SET DEFAULT '{}'::jsonb,
    ALTER COLUMN status SET DEFAULT 'active',
    ALTER COLUMN body_text SET DEFAULT '',
    ALTER COLUMN graph_status SET DEFAULT 'pending',
    ALTER COLUMN chunk_status SET DEFAULT 'pending';

DROP INDEX IF EXISTS uq_documents_doc_id;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_doc_version
    ON documents(doc_id, product_version_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_doc_id_legacy
    ON documents(doc_id)
    WHERE product_version_id IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_documents_binding_path
    ON documents(doc_binding_id, relative_path);

CREATE INDEX IF NOT EXISTS idx_documents_binding_deleted
    ON documents(doc_binding_id, deleted_at);


CREATE TABLE IF NOT EXISTS document_chunks (
    id                  SERIAL PRIMARY KEY,
    document_id          INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index          INTEGER NOT NULL,
    heading_path         TEXT NOT NULL DEFAULT '',
    chunk_text           TEXT NOT NULL,
    token_count          INTEGER NOT NULL DEFAULT 0,
    content_hash         TEXT NOT NULL,
    split_strategy       VARCHAR(32) NOT NULL DEFAULT 'structural',
    status               VARCHAR(32) NOT NULL DEFAULT 'active',
    embedding            vector,
    embedding_model      TEXT,
    embedding_dim        INTEGER,
    embedding_updated_at TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS heading_path TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS token_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS content_hash TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS split_strategy VARCHAR(32) NOT NULL DEFAULT 'structural',
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS embedding vector,
    ADD COLUMN IF NOT EXISTS embedding_model TEXT,
    ADD COLUMN IF NOT EXISTS embedding_dim INTEGER,
    ADD COLUMN IF NOT EXISTS embedding_updated_at TIMESTAMPTZ;

CREATE UNIQUE INDEX IF NOT EXISTS uq_document_chunks_document_index
    ON document_chunks(document_id, chunk_index);

CREATE INDEX IF NOT EXISTS idx_document_chunks_document_status
    ON document_chunks(document_id, status);


CREATE TABLE IF NOT EXISTS document_scan_errors (
    id              SERIAL PRIMARY KEY,
    doc_binding_id  INTEGER NOT NULL REFERENCES doc_bindings(id) ON DELETE CASCADE,
    relative_path   TEXT NOT NULL,
    error_code      VARCHAR(64) NOT NULL,
    error_message   TEXT NOT NULL,
    details_json    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE document_scan_errors
    ADD COLUMN IF NOT EXISTS details_json JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE document_scan_errors
    ALTER COLUMN details_json SET DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_document_scan_errors_binding_created
    ON document_scan_errors(doc_binding_id, created_at);


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

-- ============================================================
-- Section: 020_graph_manual_management.sql
-- ============================================================
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

-- ============================================================
-- Section: 023_manual_graph_fact_unification.sql
-- ============================================================
-- 023: audit manual graph mutations that are projected into branch facts.

CREATE TABLE IF NOT EXISTS graph_operation_logs (
    id          SERIAL PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_name TEXT,
    graph_id    INTEGER,
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
    ON graph_operation_logs(project_id, branch_name, graph_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_graph_operation_logs_object
    ON graph_operation_logs(project_id, object_kind, object_id, created_at DESC);

-- ============================================================
-- Project branch graph metadata. PostgreSQL keeps graph metadata
-- and doc-code binding indexes only; parsed code nodes/edges live in Neo4j.
-- ============================================================
CREATE TABLE IF NOT EXISTS branch_graphs (
    id            SERIAL PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_name   VARCHAR(255) NOT NULL,
    head_commit   VARCHAR(64),
    graph_hash    TEXT,
    status        VARCHAR(32) NOT NULL DEFAULT 'pending',
    node_count    INTEGER NOT NULL DEFAULT 0,
    edge_count    INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    refreshed_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_branch_graphs_project_branch UNIQUE (project_id, branch_name),
    CONSTRAINT chk_branch_graphs_status CHECK (status IN ('pending', 'running', 'ready', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_branch_graphs_project_status
    ON branch_graphs(project_id, status);

CREATE TABLE IF NOT EXISTS graph_refresh_runs (
    id                 SERIAL PRIMARY KEY,
    graph_id           INTEGER REFERENCES branch_graphs(id) ON DELETE SET NULL,
    project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_name         VARCHAR(255) NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at         TIMESTAMPTZ,
    status              VARCHAR(32) NOT NULL DEFAULT 'running',
    head_commit_before  VARCHAR(64),
    head_commit_after   VARCHAR(64),
    node_count          INTEGER NOT NULL DEFAULT 0,
    edge_count          INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    metadata_json       JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT chk_graph_refresh_runs_status CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_graph_refresh_runs_scope
    ON graph_refresh_runs(project_id, branch_name, started_at DESC);

CREATE TABLE IF NOT EXISTS doc_code_links (
    id                  SERIAL PRIMARY KEY,
    product_version_id  INTEGER NOT NULL REFERENCES product_versions(id) ON DELETE CASCADE,
    project_id          INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_name         VARCHAR(255) NOT NULL,
    doc_id              VARCHAR(128) NOT NULL,
    doc_node_id         TEXT,
    relation_type       VARCHAR(128) NOT NULL,
    code_locator_json   JSONB NOT NULL DEFAULT '{}'::jsonb,
    code_locator_hash   TEXT NOT NULL,
    resolved_graph_id   INTEGER REFERENCES branch_graphs(id) ON DELETE SET NULL,
    resolved_node_id    TEXT,
    resolution_status   VARCHAR(32) NOT NULL DEFAULT 'pending',
    status              VARCHAR(32) NOT NULL DEFAULT 'active',
    source              VARCHAR(32) NOT NULL DEFAULT 'manual',
    confidence          DOUBLE PRECISION,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    CONSTRAINT chk_doc_code_links_resolution_status
        CHECK (resolution_status IN ('pending', 'resolved', 'stale', 'ambiguous', 'failed')),
    CONSTRAINT chk_doc_code_links_status
        CHECK (status IN ('active', 'inactive'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_doc_code_links_active_locator
    ON doc_code_links(product_version_id, project_id, branch_name, doc_node_id, relation_type, code_locator_hash)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_doc_code_links_branch_active
    ON doc_code_links(project_id, branch_name, status);

CREATE INDEX IF NOT EXISTS idx_doc_code_links_doc
    ON doc_code_links(product_version_id, doc_id);

