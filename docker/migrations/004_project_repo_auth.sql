-- Persist remote repository authentication on project for re-use.
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS repo_username VARCHAR(255),
    ADD COLUMN IF NOT EXISTS repo_password TEXT;
