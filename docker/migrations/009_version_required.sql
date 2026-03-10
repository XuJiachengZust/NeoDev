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
