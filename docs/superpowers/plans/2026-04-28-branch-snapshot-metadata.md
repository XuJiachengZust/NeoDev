---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-28-BRANCH-SNAPSHOT-METADATA
title: "NeoDev 分支快照元数据实现计划"
aliases:
  - "NeoDev 分支快照元数据实现计划"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/plan
created: 2026-04-28
updated: 2026-04-28
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-SUPERPOWERS-SPECS-2026-04-28-BRANCH-SNAPSHOT-METADATA-DESIGN
related:
  - "[[2026-04-28-branch-snapshot-metadata-design]]"
---
# NeoDev 分支快照元数据实现计划

日期：2026-04-28

> **给执行 Agent 的要求：** 实施本计划时必须使用 `superpowers:test-driven-development`。如拆分子任务并行执行，必须使用 `superpowers:subagent-driven-development`；如在当前会话串行执行，必须使用 `superpowers:executing-plans`。

## 1. 目标

新增分支快照元数据能力，使图谱同步完成后可以持久化当前分支的文件级可见视图，并让状态查询和链路查询返回真实 `snapshot_id`。

## 2. 总体架构

本轮不改 Neo4j 的分支级写入方式，先在 PostgreSQL 中新增快照头和快照条目。同步流程成功后调用快照服务生成新快照；查询和状态服务通过快照服务读取当前快照，替代当前固定 `snapshot_id = None` 的占位行为。

## 3. 文件边界

新增文件：

- `docker/migrations/019_branch_snapshots.sql`
- `src/service/repositories/branch_snapshot_repository.py`
- `src/service/services/branch_snapshot_service.py`
- `tests/test_branch_snapshot_service.py`
- `tests/test_sync_service_branch_snapshot.py`

修改文件：

- `src/service/services/sync_service.py`
- `src/service/services/branch_analysis_service.py`
- `src/service/services/graph_query_service.py`
- `tests/test_branch_analysis_service_unit.py`
- `tests/test_graph_query_service_unit.py`

## 4. 任务拆分

### 4.1 任务一：新增快照迁移与仓储

目标：提供 `branch_snapshots` 和 `branch_snapshot_entries` 的最小持久化能力。

步骤：

1. 先写失败测试，覆盖创建快照、批量写 entry、读取当前快照、复制 entry。
2. 执行：

   ```text
   pytest tests/test_branch_snapshot_service.py -v
   ```

   预期失败原因：快照服务或仓储尚不存在。

3. 新增 `docker/migrations/019_branch_snapshots.sql`。
4. 新增 `branch_snapshot_repository.py`，提供：

   - `create_snapshot`
   - `replace_entries`
   - `copy_entries`
   - `get_current_snapshot`
   - `list_entries`

5. 再次执行同一测试，预期通过。

### 4.2 任务二：新增快照服务

目标：把文件扫描、内容哈希和仓储写入封装到服务层。

步骤：

1. 先写失败测试，使用临时目录模拟仓库文件。
2. 覆盖 `create_snapshot_from_repo`：

   - 能扫描支持的代码文件。
   - 能生成 `file_node_id`。
   - 能生成 `file_content_hash`。
   - 能写入 `created_from_action`。

3. 覆盖 `clone_snapshot`：

   - 能从源快照复制 entry。
   - 新快照的 `created_from_action` 为 `copy_data`。

4. 实现 `branch_snapshot_service.py`。
5. 执行：

   ```text
   pytest tests/test_branch_snapshot_service.py -v
   ```

   预期通过。

### 4.3 任务三：同步流程生成快照

目标：`sync_commits_for_version` 在图谱同步成功后生成当前快照。

步骤：

1. 先写失败测试，注入假的 pipeline 和假的快照服务调用点。
2. 覆盖成功同步后返回：

   - `graph_action`
   - `current_snapshot_id`
   - `head_commit`

3. 修改 `sync_service.py`，在 `run_pipeline` 成功并回写 `last_parsed_commit` 后创建快照。
4. 执行：

   ```text
   pytest tests/test_sync_service_branch_snapshot.py -v
   ```

   预期通过。

### 4.4 任务四：状态和查询返回快照

目标：让分支分析状态和链路查询不再返回空快照。

步骤：

1. 修改 `tests/test_branch_analysis_service_unit.py`，先写失败断言：

   - `analysis_task.current_snapshot_id` 等于当前快照 ID。
   - `analysis_task.created_from_action` 来自当前快照。

2. 修改 `tests/test_graph_query_service_unit.py`，先写失败断言：

   - `get_chain().snapshot_id` 等于当前快照 ID。
   - `get_chain().head_commit` 优先来自当前快照。

3. 修改 `branch_analysis_service.py` 和 `graph_query_service.py`，读取当前快照。
4. 执行：

   ```text
   pytest tests/test_branch_analysis_service_unit.py tests/test_graph_query_service_unit.py -v
   ```

   预期通过。

### 4.5 任务五：回归验证

目标：确认本轮变更没有破坏既有最小闭环。

执行：

```text
pytest tests/test_branch_snapshot_service.py tests/test_sync_service_branch_snapshot.py tests/test_branch_analysis_service_unit.py tests/test_graph_query_service_unit.py
```

如环境允许，再执行：

```text
pytest tests/test_metadata_migration.py
```

验收记录必须说明：

- 通过的测试数量。
- 跳过的测试数量及原因。
- 仍未实现的范围：Neo4j 仍是分支级存储，仓库级事实图迁移留到下一轮。

## 5. 验收标准

满足以下条件时，本计划完成：

- `branch_snapshots` 和 `branch_snapshot_entries` 有迁移文件。
- 快照服务能从仓库文件生成快照条目。
- 快照服务能复制已有快照条目支持 `copy_data` 语义。
- 图谱同步成功后会创建当前分支快照。
- 分支分析状态返回真实 `current_snapshot_id`。
- 链路查询返回真实 `snapshot_id`。
- 相关单元测试通过。
