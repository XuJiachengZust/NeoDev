---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-T002-DATA-MODEL-REFACTOR-TASK-LIST
title: "T002 数据模型改造任务清单"
aliases:
  - "T002 数据模型改造任务清单"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/requirements
created: 2026-04-27
updated: 2026-04-27
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
  - "[[01-master-prd]]"
---
# T002 数据模型改造任务清单

## 1. 目标

本清单用于细化 `T002 轻量元数据库模型与迁移`，重点解决以下问题：

- 为产品、文档、分析任务、危险提交建立稳定的元数据事实源
- 允许通过适度冗余和快照化设计，换取更低的实现复杂度和更好的审计能力
- 明确哪些结构保留在图数据库，哪些结构下沉到轻量元数据库
- 给后续 CLI、插件 / skill、Git 校验和推送后刷新提供稳定依赖

## 2. 设计原则

- 优先稳定和易维护，不优先做最省空间的范式设计
- 运行态和审计态分离，避免一张表既承担当前状态又承担历史回放
- 关键对象保留冗余字段，减少跨表推导
- 允许在元数据库保存图谱和分析的投影信息，但不替代图数据库本身
- 新结构优先通过 service 层接入，避免 CLI 直接依赖 SQL 细节

## 3. 模型边界

图数据库保留：

- 代码节点和关系
- 文档节点和关系
- 节点 AI 描述和 embedding
- 链路和影响范围事实

轻量元数据库新增或强化：

- `products`
- `product_code_bindings`
- `product_doc_bindings`
- `documents`
- `doc_changes`
- `code_change_links`
- `branch_analysis_tasks`
- `branch_analysis_task_events`
- `dangerous_commit_records`
- `dangerous_commit_resolution_logs`

兼容复用：

- `product_versions`
- `product_version_branches`
- `versions.last_parsed_commit`
- `ai_preprocess_status`
- `ai_description_cache`

## 4. 专项任务

### DM-01 产品主模型落库

目标：
补齐 `Product` 主表和产品级绑定关系。

建议表：

- `products`
- `product_code_bindings`
- `product_doc_bindings`

建议冗余字段：

- `product_key`
- `default_doc_branch`
- `doc_root`
- `repo_kind`
- `enabled`

建议源码落点：

- `src/service/repositories/product_repository.py`
- `src/service/repositories/product_code_binding_repository.py`
- `src/service/repositories/product_doc_binding_repository.py`

验收口径：

- 一个产品可绑定多个代码仓库分支
- 一个产品只绑定一个文档仓库
- CLI 查询产品时不需要临时拼复杂 join

### DM-02 文档主模型与扫描投影

目标：
把文档扫描结果存成稳定投影，供后续 `DocChange` 和页面渲染复用。

建议表：

- `documents`
- `document_scan_errors`

建议冗余字段：

- `product_id`
- `doc_id`
- `repo_path`
- `doc_type`
- `title`
- `status`
- `current_commit`
- `semantic_hash`
- `front_matter_json`
- `relations_json`

建议源码落点：

- `src/service/repositories/document_repository.py`
- `src/service/repositories/document_scan_error_repository.py`
- `src/service/services/doc_scan_service.py`

验收口径：

- 文档扫描结果可重复覆盖更新
- 扫描失败记录可单独查询
- 不必重新扫仓库也能快速展示文档元信息

### DM-03 DocChange 状态主表

目标：
把文档变更闭环从“临时计算”变成“稳定事实”。

建议表：

- `doc_changes`
- `doc_change_status_logs`

建议冗余字段：

- `doc_change_id`
- `product_id`
- `document_id`
- `doc_id`
- `doc_path`
- `doc_commit`
- `doc_branch`
- `change_summary`
- `status`
- `created_by`
- `resolved_by`
- `resolved_at`

建议源码落点：

- `src/service/repositories/doc_change_repository.py`
- `src/service/repositories/doc_change_status_log_repository.py`
- `src/service/services/doc_change_service.py`

验收口径：

- `DocChange` 可独立查询和回溯
- 状态流转有历史日志
- Git 校验无需回头重新解析文档提交

### DM-04 代码落地关联表

目标：
把代码提交与文档变更的实现关联单独建模。

建议表：

- `code_change_links`

建议冗余字段：

- `doc_change_id`
- `product_id`
- `project_id`
- `branch`
- `commit_sha`
- `commit_message`
- `matched_by`
- `verification_status`

建议源码落点：

- `src/service/repositories/code_change_link_repository.py`
- `src/service/services/git_consistency_service.py`

验收口径：

- 一个 `DocChange` 可关联多个 commit
- 查询某次提交实现了哪个 `DocChange` 不依赖重新解析 git log

### DM-05 分支分析任务主表

目标：
把当前运行态分析任务和历史态分析结果分离。

建议表：

- `branch_analysis_tasks`
- `branch_analysis_task_events`

建议冗余字段：

- `analysis_task_id`
- `product_id`
- `product_version_id`
- `project_id`
- `branch`
- `head_commit`
- `analysis_action`
- `status`
- `progress_json`
- `triggered_by`
- `trigger_source`
- `error_message`

兼容策略：

- 保留 `ai_preprocess_status` 作为旧接口兼容层
- 新任务以 `branch_analysis_tasks` 为主

建议源码落点：

- `src/service/repositories/branch_analysis_task_repository.py`
- `src/service/repositories/branch_analysis_task_event_repository.py`
- `src/service/services/branch_analysis_service.py`

验收口径：

- 当前任务状态和历史事件可分开查询
- `watch-status` 能直接消费任务快照
- 并发冲突判断不需要扫历史日志

### DM-06 危险提交审计结构

目标：
把危险提交的待处理态和关闭流水分离。

建议表：

- `dangerous_commit_records`
- `dangerous_commit_resolution_logs`

建议冗余字段：

- `dangerous_commit_id`
- `doc_change_id`
- `project_id`
- `branch`
- `commit_sha`
- `risk_reason`
- `status`
- `resolved_by`
- `resolved_at`

建议源码落点：

- `src/service/repositories/dangerous_commit_repository.py`
- `src/service/repositories/dangerous_commit_resolution_log_repository.py`
- `src/service/services/git_consistency_service.py`

验收口径：

- 待处理清单查询不需要扫描历史状态
- 关闭动作有独立审计记录

### DM-07 推送后刷新批次记录

目标：
为 `git post-push-refresh` 保留可追踪批次记录，避免后续排错时只能看日志。

建议表：

- `post_push_refresh_runs`

建议冗余字段：

- `run_id`
- `project_id`
- `branch`
- `head_commit`
- `affected_nodes_json`
- `refresh_scope_json`
- `graph_refresh_status`
- `ai_refresh_status`
- `started_at`
- `finished_at`

建议源码落点：

- `src/service/repositories/post_push_refresh_run_repository.py`
- `src/service/services/post_push_refresh_service.py`

验收口径：

- 每次推送后刷新都有独立批次记录
- 节点刷新失败时可以精确定位到批次和影响范围

## 5. 建议执行顺序

1. DM-01 产品主模型落库
2. DM-02 文档主模型与扫描投影
3. DM-03 DocChange 状态主表
4. DM-04 代码落地关联表
5. DM-05 分支分析任务主表
6. DM-06 危险提交审计结构
7. DM-07 推送后刷新批次记录

## 6. 关键决策

- 可以接受多张表和冗余字段，只要换来更清晰的职责边界
- 运行态、历史态、审计态分开建模
- 图数据库负责知识关系，元数据库负责业务状态和执行记录
- 兼容现有能力时优先加 service facade，不直接把旧结构暴露给 CLI

### DM-08 仓库主图与分支快照存储结构

目标：
把“一个仓库一个分支一套完整图”的隐式结构，改为“仓库级事实图 + 分支快照引用”。

建议新增或强化：

- `branch_snapshots`
- `branch_snapshot_entries`

建议字段：

- `branch_snapshots`
  - `snapshot_id`
  - `repo_id`
  - `branch`
  - `head_commit`
  - `last_parsed_commit`
  - `base_snapshot_id`
  - `created_from_action`
  - `status`
- `branch_snapshot_entries`
  - `snapshot_id`
  - `repo_id`
  - `file_path`
  - `file_node_id`
  - `file_content_hash`
  - `visible`

设计约束：

- 图数据库中的代码事实节点不再按 `branch` 复制整套数据
- 分支快照先以文件级 membership 为主
- 符号级可见性通过文件包含关系推导，不额外维护一套分支级 symbol membership

建议源码落点：

- `src/service/repositories/branch_snapshot_repository.py`
- `src/service/repositories/branch_snapshot_entry_repository.py`
- `src/service/services/branch_snapshot_service.py`

验收口径：

- 同一仓库多分支共享相同文件内容时，不重复存整套图节点
- `copy_data` 语义变成复制快照引用，而不是复制整图
- 删除分支时只需要删除快照和引用，不需要删除仓库级事实图
