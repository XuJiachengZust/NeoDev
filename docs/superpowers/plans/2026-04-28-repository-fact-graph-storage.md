---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-28-REPOSITORY-FACT-GRAPH-STORAGE
title: "NeoDev 仓库级事实图存储结构实施计划"
aliases:
  - "NeoDev 仓库级事实图存储结构实施计划"
tags:
  - neodev/docs
  - neodev/implementation-plan
  - neodev/superpowers
created: 2026-04-28
updated: 2026-04-28
doc_type: implementation-plan
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-SUPERPOWERS-SPECS-2026-04-28-REPOSITORY-FACT-GRAPH-STORAGE-DESIGN
  related:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-06-GRAPH-STORAGE-STRUCTURE
related:
  - "[[2026-04-28-repository-fact-graph-storage-design]]"
  - "[[06-graph-storage-structure]]"
---

# NeoDev 仓库级事实图存储结构实施计划

日期：2026-04-28

> **给执行 Agent 的要求：** 实施本计划时必须使用 `superpowers:test-driven-development`。如拆分子任务并行执行，必须使用 `superpowers:subagent-driven-development`；如在当前会话串行执行，必须使用 `superpowers:executing-plans`。

## 1. 目标

把 NeoDev 代码图从“按分支复制整图”改为“Neo4j 保存仓库级代码事实，PostgreSQL 保存分支快照可见范围”。查询入口仍接收 `branch`，但分支语义由 `branch_snapshots` 与 `branch_snapshot_entries` 裁剪。

## 2. 架构

- Neo4j 节点身份不再包含 `branch`，节点按仓库级事实 ID 合并。
- 文件事实 ID 由 `repo_id + filePath + file_content_hash` 生成。
- 符号事实 ID 基于所属文件事实、符号签名与文件内容哈希生成。
- `copy_data` 只复制分支快照，不复制 Neo4j 节点或关系。
- `full` 与 `incremental` 写入仓库级事实图，并创建新的分支快照。
- 查询和节点详情先读取当前分支快照，再把 `visible_file_ids` 传给 Neo4j 查询。
- 代码节点不再提供 AI 预处理、AI 描述、embedding 生成或语义刷新能力。

## 3. 文件边界

- `src/gitnexus_parser/neo4j_writer.py`：改为按 `id` 合并节点和关系，移除写入 API 的 `branch` 身份参数。
- `src/gitnexus_parser/ingestion/structure.py`：生成仓库级 File、Folder 事实 ID。
- `src/gitnexus_parser/ingestion/import_resolver.py`：IMPORTS 关系 ID 使用仓库级端点 ID。
- `src/gitnexus_parser/ingestion/pipeline.py`：传入 `repo_id`、文件内容 hash 与 `project_id`，不再在增量流程中删除分支图节点。
- `src/service/services/branch_snapshot_service.py`：分支快照 entry 指向仓库级文件事实 ID。
- `src/service/services/watch_service.py`：`copy_data` 复制快照，`full`/`incremental` 创建快照并向 pipeline 传入 `project_id`。
- `src/service/services/graph_query_service.py`、`node_service.py`：按快照可见文件裁剪 Neo4j 查询。
- `src/service/services/ai_analysis_runner.py`、`ai_preprocessor_service.py`、`graph_refresh_service.py`、`src/service/routers/preprocess.py`：代码节点 AI/语义处理链路已删除。
- `src/gitnexus_parser/backfill_source_code.py`：旧的分支级回填脚本已删除。

## 4. 任务清单

### 4.1 Neo4j writer 仓库级写入

- [x] 增加 writer 失败测试，约束必须使用 `REQUIRE n.id IS UNIQUE`。
- [x] 节点写入改为 `MERGE (n:Label {id: $id})`。
- [x] 关系写入改为通过 `sourceId`、`targetId` 的仓库级事实 ID 匹配端点。
- [x] 移除 `write_graph` 的 `branch` 参数。

### 4.2 Pipeline 生成仓库级事实 ID

- [x] File 事实 ID 包含仓库、路径与内容 hash。
- [x] Folder 事实 ID 包含仓库与路径，避免跨仓库路径碰撞。
- [x] 解析结果中的 File 与符号引用重映射为仓库级事实 ID。
- [x] IMPORTS 关系 ID 使用仓库级端点 ID。
- [x] pipeline 文档说明改为“写事实与快照”，不再描述删除分支图节点。

### 4.3 分支快照 entry 对齐文件事实

- [x] 新增 `branch_snapshots` 与 `branch_snapshot_entries` 迁移。
- [x] 快照服务从当前工作区生成 entry，并保存仓库级 `file_node_id`。
- [x] 同步服务成功后创建当前分支快照。
- [x] `watch_service` 的 `full` 与 `incremental` 也创建快照。

### 4.4 `copy_data` 改为快照复制

- [x] 相同 HEAD 的分支复制只 clone snapshot。
- [x] 不再调用旧的 Neo4j `add_branch_to_nodes`。
- [x] 保留版本状态更新，保证状态查询能读到目标分支当前快照。

### 4.5 查询和节点详情按快照裁剪

- [x] 链路查询使用当前分支快照中的 `visible_file_ids`。
- [x] 实体上下文和节点详情不再按 `n.branch = $branch` 查询 Neo4j。
- [x] 代码节点 AI 预处理、AI 描述生成、embedding 生成与语义刷新入口已移除。

### 4.6 清理旧代码

- [x] 删除 `src/gitnexus_parser/backfill_source_code.py`。
- [x] `src` 中不再保留 `add_branch_to_nodes`、`delete_branch`、`delete_nodes_by_file_paths` 的旧实现路径。
- [x] 关键查询不再使用 Neo4j 节点上的 `branch` 作为身份或过滤条件。

## 5. 验证记录

- `pytest tests/test_watch_service_branch_snapshot.py -v`：通过。
- `pytest tests/test_neo4j_writer_repository_facts.py -v`：通过。
- `pytest tests/test_pipeline_repository_facts.py -v`：通过。
- `pytest tests/test_cli_contract.py::test_graph_refresh_nodes_command_is_removed tests/test_cli_remote_execution.py::test_code_ai_preprocess_routes_are_not_registered tests/test_git_consistency_service_unit.py::test_post_push_refresh_does_not_refresh_code_node_semantics -v`：通过。

## 6. 子智能体复核结论

已使用三个子智能体分别复核 parser/writer、service 查询链路、文档/测试/迁移。复核时发现的主要缺口包括：

- `watch_service` 的 `full` 与 `incremental` 未创建分支快照，且未向 pipeline 传入 `project_id`。
- `write_graph` 仍保留旧的 `branch` 参数。
- Folder 与 IMPORTS 的事实身份仍存在跨仓库或旧路径端点风险。
- 代码节点 AI/语义处理链路超出当前目标，已按最新范围删除。
- 实施计划文档存在英文模板残留。

以上问题均已补测试并修正。

## 7. 剩余风险

- 完整 `pytest` 受本机临时目录权限影响，可能在 pytest 创建临时目录阶段报 `PermissionError`；功能相关的定向测试已通过。
- API 仍保留 `branch` 入参作为分支视图选择条件，这是兼容层，不再表示 Neo4j 节点身份。
