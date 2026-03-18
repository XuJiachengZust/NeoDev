-- 016: 需求文档生成状态持久化
ALTER TABLE requirement_doc_meta
  ADD COLUMN IF NOT EXISTS generation_status VARCHAR(32) DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS generation_started_at TIMESTAMPTZ DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS generation_error TEXT DEFAULT NULL;
