-- 022: allow repository-derived code identifiers to exceed 255 characters.

ALTER TABLE IF EXISTS code_facts ALTER COLUMN fact_id TYPE TEXT;
ALTER TABLE IF EXISTS code_facts ALTER COLUMN symbol_key TYPE TEXT;
ALTER TABLE IF EXISTS code_facts ALTER COLUMN parent_fact_id TYPE TEXT;

ALTER TABLE IF EXISTS branch_snapshot_facts ALTER COLUMN fact_id TYPE TEXT;

ALTER TABLE IF EXISTS doc_code_links ALTER COLUMN symbol_key TYPE TEXT;
ALTER TABLE IF EXISTS doc_code_links ALTER COLUMN resolved_fact_id TYPE TEXT;
