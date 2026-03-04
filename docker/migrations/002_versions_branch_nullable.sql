-- Allow version without bound branch: create version with optional branch (Phase 3+).
ALTER TABLE versions ALTER COLUMN branch DROP NOT NULL;
