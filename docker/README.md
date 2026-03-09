# PostgreSQL + pgvector 本地 Docker

## 启动

```powershell
cd D:\PycharmProjects\NeoDev
docker compose up -d
```

## 连接信息

| 项     | 值        |
|--------|-----------|
| Host   | localhost |
| Port   | 5432      |
| User   | postgres  |
| Pass   | postgres  |
| DB     | neodev    |

连接串：`postgresql://postgres:postgres@localhost:5432/neodev`

## 向量扩展

首次启动时会自动执行 `docker/init-pgvector.sql`，创建 `vector` 扩展。

若需手动启用：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## 影响面分析表（Phase 2 迁移）

首次**新库**启动时，会按顺序执行以下迁移：
- `docker/migrations/001_impact_analysis_tables.sql`
- `docker/migrations/002_versions_branch_nullable.sql`
- `docker/migrations/003_git_branches.sql`

其中 `003_git_branches.sql` 会创建 `git_branches` 表，并从 `versions.branch` 自动回填已有分支。

若库已存在（例如之前仅启用过 pgvector），需**手动执行**迁移：

```powershell
# 若已安装 psql（或在容器内执行）
psql -h localhost -U postgres -d neodev -f docker/migrations/001_impact_analysis_tables.sql
psql -h localhost -U postgres -d neodev -f docker/migrations/002_versions_branch_nullable.sql
psql -h localhost -U postgres -d neodev -f docker/migrations/003_git_branches.sql
```

或使用 Python 连接后执行该 SQL 文件内容。跑 `tests/test_impact_analysis_schema.py` 时，若检测到无 `projects` 表会自动执行该迁移（需 PG 已启动）。

## 示例：带向量列的表

```sql
CREATE TABLE items (
  id BIGSERIAL PRIMARY KEY,
  embedding vector(3)  -- 3 维向量，按实际维度修改
);

-- 余弦相似度查询示例
SELECT * FROM items
ORDER BY embedding <=> '[1,2,3]'
LIMIT 5;
```

## 停止与清理

```powershell
docker compose down        # 停止并删除容器
docker compose down -v      # 并删除数据卷
```
