-- 010: 新增 repo_url 字段，保存原始远程仓库地址（repo_path 会被克隆后覆盖为本地路径）
ALTER TABLE projects ADD COLUMN IF NOT EXISTS repo_url TEXT;

-- 回填：如果现有 repo_path 是远程地址则复制到 repo_url
UPDATE projects SET repo_url = repo_path
WHERE repo_url IS NULL
  AND (repo_path LIKE 'http://%' OR repo_path LIKE 'https://%' OR repo_path LIKE 'git@%');
