---
doc_id: NEODEV-DOC-SUPERPOWERS-SPECS-2026-04-28-REPOSITORY-FACT-GRAPH-STORAGE-DESIGN
title: "NeoDev 仓库级事实图存储结构设计"
aliases:
  - "NeoDev 仓库级事实图存储结构设计"
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
    - NEODEV-DOC-SUPERPOWERS-SPECS-2026-04-28-BRANCH-SNAPSHOT-METADATA-DESIGN
related:
  - "[[06-graph-storage-structure]]"
  - "[[2026-04-28-branch-snapshot-metadata-design]]"
---

# NeoDev 仓库级事实图存储结构设计

## 1. 目标

本设计用于把 `06-graph-storage-structure.md` 从“分支快照元数据层”推进到完整 MVP 新存储结构。目标是让 Neo4j 存仓库级代码事实，PostgreSQL 存分支视图和执行状态。

本次实现后：

- Neo4j 不再按 `(id, branch)` 复制整套分支图。
- `copy_data` 不再复制 Neo4j 节点和关系，只复制分支快照引用。
- 查询入口继续接收 `branch`，但分支语义由 `branch_snapshots` 和 `branch_snapshot_entries` 限定。
- 文件级快照是 MVP 的精确边界，符号可见性通过 `File -> Symbol` 的关系推导。

## 2. 范围

纳入本次实现：

- Neo4j writer 改为仓库级事实写入。
- pipeline 为文件节点和符号节点补充 `repo_id`、`content_hash`、`file_content_hash`、`fact_key`。
- `branch_snapshot_entries.file_node_id` 指向仓库级文件事实节点。
- `full` 与 `incremental` 写入仓库级事实图，并创建新快照。
- `copy_data` 克隆快照 entry，不写 Neo4j。
- `graph get-chain` 和 `entity_context` 按当前快照裁剪可见文件，再遍历事实图。
- `watch_service` 使用快照复制替代旧的 `add_branch_to_nodes`。

暂不纳入本次实现：

- commit 级完整图快照。
- 符号级 membership 表。
- 历史事实垃圾回收。
- 跨分支预聚合查询缓存。

## 3. 数据身份

### 3.1 仓库级文件事实

文件事实节点的稳定身份由仓库、路径和内容共同决定：

```text
File fact key = repo_id + file_path + file_content_hash
```

Neo4j 节点属性：

- `id`: 仓库级文件事实 ID。
- `repo_id`: 仓库标识，MVP 中默认等于 `project_id`。
- `project_id`: 保留项目范围，兼容现有查询和权限边界。
- `filePath`: 文件路径。
- `file_content_hash`: 文件内容 SHA-256。
- `content_hash`: 与 `file_content_hash` 一致，用于通用事实去重。
- `fact_key`: 可读的事实键。
- `branch`: 不再参与身份，可保留为空或兼容写入的最后来源分支。

### 3.2 仓库级符号事实

符号事实节点依附文件内容版本：

```text
Symbol fact key = repo_id + file_path + symbol_signature + file_content_hash
```

MVP 中 `symbol_signature` 使用现有解析结果中的 `label + filePath + name + startLine + endLine` 组合。这样同一文件内容在多个分支上会复用同一组符号事实。

## 4. 写入流程

### 4.1 全量分析

`full` 的流程：

1. checkout 目标分支。
2. 扫描当前仓库文件并计算内容 hash。
3. 构建仓库级事实图。
4. 按事实 ID `MERGE` Neo4j 节点和关系。
5. 创建 `branch_snapshots`。
6. 写入 `branch_snapshot_entries`，每条 entry 指向对应文件事实节点。
7. 更新 `versions.last_parsed_commit`。

全量分析不再删除整个分支图。相同文件内容对应的事实节点会被复用。

### 4.2 增量分析

`incremental` 的流程：

1. 基于上一次 `last_parsed_commit` 找到变更文件。
2. 只解析变更文件对应的事实子图。
3. 写入新的文件事实和符号事实。
4. 基于上一份快照复制未变化文件 entry。
5. 用变更文件的新 entry 覆盖同路径旧 entry。
6. 输出新的快照。

MVP 可以先通过重扫当前文件集生成新 entry 集合，保证正确性；后续再把 entry 生成优化为差量复制。

### 4.3 快照复制

`copy_data` 的流程：

1. 找到相同 HEAD 的来源分支当前快照。
2. 创建目标分支新快照，`base_snapshot_id` 指向来源快照。
3. 复制来源快照 entries 到目标快照。
4. 更新目标 version 的 `last_parsed_commit`。
5. 不调用 Neo4j writer。

## 5. 查询流程

### 5.1 快照裁剪

所有分支级图查询先取得当前快照：

```text
project_id + branch -> current branch_snapshot -> visible branch_snapshot_entries
```

随后把 entry 中的 `file_node_id` 作为可见文件集合传入 Neo4j 查询。

### 5.2 链路查询

`graph get-chain` 的查询步骤：

1. 根据 locator 找到起点。
2. 起点是文件时，要求文件 ID 在快照 entry 集合内。
3. 起点是符号时，要求存在快照可见文件通过 `DEFINES`、`CONTAINS` 或等价关系连接到该符号。
4. 遍历时只保留路径中所有代码节点都归属于可见文件集合的结果。
5. 返回 `snapshot_id`、`branch`、`head_commit`。

### 5.3 实体上下文

`entity_context` 与链路查询使用同一套可见文件集合。它不再用 `n.branch = $branch` 判断节点归属。

## 6. 兼容策略

短期保留以下兼容：

- `branch` 参数仍保留在 API 和 CLI 中。
- Neo4j 节点可继续写入 `project_id`，避免影响现有项目范围判断。
- 查询函数在没有当前快照时返回明确的 degraded reason，避免误查全仓库事实图。
- 老的 `(id, branch)` 约束不强制删除；新的 writer 不依赖它。

## 7. 测试策略

测试按 TDD 推进：

- Neo4j writer 单元测试：约束和 `MERGE` 不再使用 `(id, branch)` 身份。
- pipeline 单元测试：文件事实 ID 随内容 hash 变化，相同内容复用。
- branch snapshot 服务测试：entry 指向仓库级文件事实 ID。
- watch 服务测试：相同 HEAD 分支执行 `copy_data` 时只复制快照，不调用 Neo4j 复制。
- graph query 服务测试：Cypher 使用 `visible_file_ids` 而不是 `branch` 裁剪。
- sync 服务测试：同步结果包含快照与仓库级事实写入信息。

## 8. 自检

- 本设计没有引入符号级 membership，符合 MVP 边界。
- 本设计把分支视图放在 PostgreSQL，把代码事实放在 Neo4j，符合原始技术方案。
- 本设计保留 API 入参兼容，降低上层 CLI 和路由改造范围。
- 本设计明确了无快照时的降级行为，避免查询误返回其他分支事实。
