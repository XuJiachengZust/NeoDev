-- 012: impact_analyses 增加 title 和 version_id 列
ALTER TABLE impact_analyses ADD COLUMN IF NOT EXISTS title VARCHAR(100);
ALTER TABLE impact_analyses ADD COLUMN IF NOT EXISTS version_id INTEGER REFERENCES versions(id);
CREATE INDEX IF NOT EXISTS idx_impact_analyses_version ON impact_analyses(version_id);
