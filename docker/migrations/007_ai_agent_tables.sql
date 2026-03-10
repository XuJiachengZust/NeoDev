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
