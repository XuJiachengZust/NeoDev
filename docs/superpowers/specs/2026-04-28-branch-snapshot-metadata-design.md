---
doc_id: NEODEV-DOC-SUPERPOWERS-SPECS-2026-04-28-BRANCH-SNAPSHOT-METADATA-DESIGN
title: "NeoDev 分支快照元数据设计"
aliases:
  - "NeoDev 分支快照元数据设计"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/spec
created: 2026-04-28
updated: 2026-04-28
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-06-GRAPH-STORAGE-STRUCTURE
related:
  - "[[06-graph-storage-structure]]"
---
# NeoDev 分支快照元数据设计

## 1. 目标

本设计实现 `06-graph-storage-structure.md` 的第一个 MVP 切片：先落地分支快照元数据和文件级快照条目，并把当前快照暴露到分支分析状态与链路查询结果中。

本切片不直接重写 Neo4j 的图事实存储。当前 Neo4j 写入仍可继续使用分支级节点，PostgreSQL 先保存分支视图元数据，为后续“仓库级事实图 + 分支快照裁剪”提供稳定边界。

## 2. 范围

本切片包含：

- 新增 `branch_snapshots` 和 `branch_snapshot_entries`。
- 新增快照仓储和服务，支持创建当前分支快照、复制快照条目、读取当前快照。
- 图谱同步成功后生成新的分支快照。
- `analysis_task` 和 `graph get-chain` 返回真实的 `snapshot_id`、`head_commit` 和 `created_from_action`。

本切片不包含：

- 将 Neo4j 节点唯一性从 `(id, branch)` 改为仓库级事实身份。
- 将链路查询改造成通过 `branch_snapshot_entries` 裁剪后再遍历仓库级事实图。
- 新增代码节点向量检索主流程。

## 3. 数据模型

### 3.1 `branch_snapshots`

用途：记录某个项目分支在某次分析动作后的当前可见视图头信息。

建议字段：

- `id`
- `project_id`
- `repo_id`
- `branch`
- `head_commit`
- `last_parsed_commit`
- `base_snapshot_id`
- `created_from_action`
- `status`
- `created_at`

说明：

- `repo_id` 在本切片中使用 `project_id`，后续如引入独立仓库表，可平滑迁移。
- `created_from_action` 取值为 `copy_data`、`incremental`、`full`。
- 每次成功同步生成一条新快照，不原地改写旧快照。

### 3.2 `branch_snapshot_entries`

用途：记录某个快照当前可见的文件级事实引用。

建议字段：

- `id`
- `snapshot_id`
- `project_id`
- `repo_id`
- `file_path`
- `file_node_id`
- `file_content_hash`
- `visible`
- `created_at`

说明：

- MVP 先精确到文件级，不单独保存符号级 membership。
- `file_node_id` 暂时兼容当前 Neo4j 文件节点 ID，使用 `generate_id("File", file_path)`。
- `file_content_hash` 使用当前检出的文件内容计算 SHA-256。

## 4. 核心流程

### 4.1 `full`

`full` 在本切片中的语义是：

1. 当前分支图谱同步成功。
2. 扫描当前分支工作区文件。
3. 为每个文件生成 `file_content_hash` 与 `file_node_id`。
4. 创建新的 `branch_snapshots` 记录。
5. 批量写入该快照的 `branch_snapshot_entries`。

### 4.2 `incremental`

`incremental` 在本切片中的语义是：

1. 找到该分支上一条当前快照作为 `base_snapshot_id`。
2. 当前 Neo4j 增量写入仍按现有逻辑执行。
3. 成功后生成新的快照头和文件级条目。

说明：本切片可以先重新生成完整 entry 集合，暂不强制做“未变文件 entry 复用”。字段和服务边界保留 `base_snapshot_id`，后续可在不改外部契约的前提下优化为局部替换。

### 4.3 `copy_data`

`copy_data` 在本切片中的语义是：

1. 找到可复用的源快照。
2. 创建目标分支的新快照头。
3. 将源快照的 entry 集合复制到目标快照。
4. 不复制 Neo4j 整图。

当前同步主路径可以先不自动选择 `copy_data`，但服务层必须提供复制快照条目的能力，供后续 watch 或编排层接入。

## 5. 查询影响

### 5.1 分支分析状态

`analysis_task` 需要优先读取当前快照，并返回：

- `current_snapshot_id`
- `head_commit`
- `last_parsed_commit`
- `created_from_action`

若快照尚未生成，则继续兼容旧的 `versions.last_parsed_commit`。

### 5.2 链路查询

`graph get-chain` 当前仍按 `branch` 查询 Neo4j，但返回结构中的 `snapshot_id` 不再固定为 `None`，而是读取当前分支快照。

后续 Neo4j 仓库级事实图落地后，再把链路查询改为：

`ProductVersion -> product_version_branches -> branch_snapshots -> branch_snapshot_entries -> File Fact -> Symbol Fact`

## 6. 测试策略

本切片需要覆盖：

- 从仓库文件生成快照条目。
- 复制已有快照条目形成新的 `copy_data` 快照。
- 分支分析状态返回当前快照。
- 链路查询返回当前快照 ID。

验证命令：

```text
pytest tests/test_branch_snapshot_service.py tests/test_branch_analysis_service_unit.py tests/test_graph_query_service_unit.py
```

如本机 PostgreSQL 不可用，数据库集成测试允许沿用现有 fixture 跳过策略，但纯服务层测试必须可执行。
