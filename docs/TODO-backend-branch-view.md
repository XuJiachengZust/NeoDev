# 后端 TODO：分支视图增强

> 当前前端已完成的功能需要后端配合优化的事项。

## 1. 版本-分支映射时自动创建项目级 Version

**现状：** 在 `ProductVersionOverviewPage` 设置分支映射（`setVersionBranch`）后，`product_version_branches` 表中有记录，但 `versions` 表中不一定有对应的项目级 Version 记录。当前前端在 `ProductProjectDetailPage` 中做了兜底：发现缺失时自动调用 `createVersion` API。

**优化：** 将自动创建逻辑下沉到后端 `product_version_service.set_branch()` 中。在写入 `product_version_branches` 后，检查 `versions` 表是否有该 `project_id + branch` 的记录，没有则自动创建。

**涉及文件：**
- `src/service/services/product_version_service.py` — `set_branch()` 方法
- `src/service/repositories/version_repository.py` — 需要 `find_by_project_and_branch()` 查询

## 2. 同步提交时自动创建项目级 Version

**现状：** `sync_service.sync_commits_for_version()` 要求项目级 Version 已存在，否则返回 None。

**优化：** 可考虑在 `sync_commits_for_project()` 中，对于有分支映射但无项目级 Version 的情况自动创建。

**涉及文件：**
- `src/service/services/sync_service.py`

## 3. 需求完成情况接口性能优化

**现状：** `list_tree_with_commit_counts` 使用 `LEFT JOIN + GROUP BY` 一次性返回需求及其提交数，当前够用。

**未来优化：**
- 如果需求数或提交绑定数很大，可考虑添加索引 `product_requirement_commits(requirement_id)`
- 考虑增加缓存或物化视图

**涉及文件：**
- `src/service/repositories/product_requirement_repository.py` — `list_tree_with_commit_counts()`
- `docker/migrations/` — 可能需要新增索引迁移

## 4. 提交列表按分支直接查询

**现状：** 查询提交必须先找到项目级 Version ID，再通过 `listCommitsByVersion` 查询。没有按 `project_id + branch` 直接查询提交的接口。

**优化：** 新增 `GET /api/projects/{project_id}/commits-by-branch?branch=xxx` 端点，内部自动查找 Version 再查提交，简化前端逻辑。

**涉及文件：**
- `src/service/routers/commits.py`
- `src/service/services/commit_service.py`
- `src/service/repositories/commit_repository.py`

## 5. 提交列表服务端分页

**现状：** `listCommitsByVersion` 一次性返回分支下所有提交，前端用虚拟滚动渲染。当提交数达万级时全量拉取仍有性能问题。

**优化：** 新增 `offset` + `limit` 分页参数，默认 `limit=500`；前端首屏加载首页，滚动到底部时加载下一页（无限滚动）。

**涉及文件：**
- `src/service/routers/commits.py` — 添加 `offset`、`limit` Query 参数
- `src/service/repositories/commit_repository.py` — SQL 添加 `LIMIT %s OFFSET %s`
- `web/src/api/client.ts` — `ListCommitsByVersionParams` 增加分页字段

## 6. 影响面分析结果查询接口

**现状：** `createImpactAnalysis` 只触发分析任务，前端没有展示分析结果的入口。需要能查询某组提交的影响面分析结果详情（影响的文件、函数、模块）。

**优化：**
- `GET /api/projects/{project_id}/impact-analyses/{id}/details` — 返回影响的符号列表、文件变更图谱
- 或在现有 `getImpactAnalysis` 返回值中嵌入结构化结果

**涉及文件：**
- `src/service/routers/impact.py`
- `src/service/repositories/impact_repository.py`

## 7. 需求绑定反查：按需求查关联提交列表

**现状：** `list_commits(requirement_id)` 已存在，但前端需求完成情况卡片目前只展示提交数，无法展开查看具体关联了哪些提交。

**优化：** 前端需求树行点击后展开关联提交列表，后端接口已有（`GET /{product_id}/requirements/{requirement_id}/commits`），无需新增端点，但建议增加返回字段 `project_name` 以便跨项目场景下区分来源。

**涉及文件：**
- `src/service/repositories/product_requirement_repository.py` — `list_commits()` JOIN projects 表补充 `project_name`
