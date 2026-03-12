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
CREATE UNIQUE INDEX idx_agent_conv_unique_ctx
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
