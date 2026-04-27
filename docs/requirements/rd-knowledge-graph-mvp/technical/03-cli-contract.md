---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-03-CLI-CONTRACT
title: "CLI 命令契约"
aliases:
  - "CLI 命令契约"
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
# CLI 命令契约

## 1. 目标

MVP 对外只暴露本地 `neodev` CLI 客户端能力。CLI 客户端是远程 API 客户端，不是本地服务端；所有真实执行、状态写入、图谱刷新和分析任务都必须请求统一远程 NeoDev 服务完成。

本地 CLI 客户端负责：

- 读取本地配置中的远程服务地址
- 将命令、参数和本地项目路径上下文发送到远程 NeoDev 服务
- 返回远程服务的结构化结果

远程 NeoDev 服务负责：

- 执行业务动作
- 持久化业务事实
- 更新图谱与状态
- 运行分析任务

插件 / skill 负责：

- 引导用户选择正确命令
- 编排多步工作流
- 补全参数
- 解释结果
- 提示风险

本版采用强一致版本策略：

- 不引入 `schema_version`
- CLI 与插件 / skill 视为同一套运行时契约
- 通过版本检查和自动更新保持兼容

## 2. 全局要求

### 2.1 输出结构

所有命令默认支持结构化 JSON 输出，顶层字段至少包括：

- `ok`
- `command`
- `timestamp`
- `data`
- `errors`

补充规则：

- 不增加 `schema_version`
- 插件 / skill 不负责兼容多套结果协议
- 若本地 CLI 未配置远程服务，应先执行 `neodev config set-server <url>`
- 若版本不兼容，应先执行 `neodev cli version-check --json`，再决定是否继续

### 2.2 错误码

统一错误类别：

- `invalid_argument`
- `not_found`
- `conflict`
- `not_ready`
- `verification_failed`
- `risky_operation`
- `internal_error`
- `version_mismatch`

### 2.3 幂等与副作用

默认无副作用命令：

- `doc change show`
- `graph semantic-search`
- `graph entity-context`
- `graph get-chain`
- `project show`
- `cli version-check`

有副作用命令：

- `doc scan`
- `doc change register`
- `doc change mark-implemented`
- `graph refresh-nodes`
- `project create`
- `git verify-doc-change`
- `git post-push-refresh`
- `git dangerous-commit resolve`

## 3. 命令分组

### 3.1 产品、版本与项目

- `product create`
- `product update`
- `product show`
- `product version create`
- `product version bind-branch`
- `product version show`
- `project create`
- `project show`

### 3.2 文档与变更

- `doc scan`
- `doc change register`
- `doc change show`
- `doc change mark-implemented`

### 3.3 图谱与检索

- `graph impact`
- `graph entity-context`
- `graph semantic-search`
- `graph refresh-nodes`
- `graph get-chain`

### 3.4 仓库接入与自动图谱构建

- `project create --repo-url`
- `project show`

兼容说明：旧显式分析命令只保留给历史集成，不再作为插件 / skill 推荐入口，也不应出现在用户主流程中。

### 3.5 Git 一致性

- `git verify-doc-change`
- `git post-push-refresh`
- `git dangerous-commit resolve`

### 3.6 本地客户端配置与版本检查

- `config set-server`
- `config show`
- `cli version-check`

## 4. 核心命令契约

### 4.1 `graph impact`

输入：

- `doc_change_id`

输出：

- `affected_repositories`
- `affected_modules`
- `affected_files`
- `affected_symbols`
- `evidence`
- `confidence`
- `risk_points`
- `suggested_steps`

### 4.2 `graph semantic-search`

输入：

- `product_key`
- `product_version_id` 或 `version_name`
- `query`
- 可选 `top_k`

输出：

- `product_version_id`
- `project_name`
- `branch`
- `entity_type`
- `entity_id`
- `file_path`
- `description`
- `score`
- `semantic_status`

### 4.3 `graph refresh-nodes`

输入：

- `product_key`
- `product_version_id`
- `project_id`
- `branch`
- 可选 `node_ids`
- 可选 `paths`
- 可选 `commit_sha`

输出：

- `refresh_scope`
- `graph_nodes_updated`
- `graph_nodes_updated`
- `chains_updated`
- `index_reused`
- `index_regenerated`
- `status`

规则：

- 支持按 `project/version/branch/node/path/commit` 刷新
- 默认优先局部刷新
- 不默认执行全库全量刷新

### 4.4 `graph get-chain`

输入：

- `product_key`
- `product_version_id`
- `project_id`
- `branch`
- `start_node` 或 `file_path` 或 `symbol` 或 `commit_sha`
- 可选 `depth`

输出：

- `start_node`
- `snapshot_id`
- `branch`
- `head_commit`
- `depth`
- `nodes`
- `edges`
- `path_summary`
- `affected_commits`

规则：

- 支持直接邻接查询
- 支持 N 跳链路查询
- 返回节点、边、方向和摘要

### 4.5 `project create`

输入：

- `name`
- `repo_url` 或 `repo_path`
- 可选 `watch_enabled`
- 可选 `neo4j_database`
- 可选 `neo4j_identifier`

输出：

- `project`
- `auto_graph_analysis=true`
- `project.init_result.sync`
- `message`

规则：

- 用户传入仓库地址后，远程 NeoDev 服务自动登记项目并触发图谱构建。
- 如果仓库图谱可复用，服务端优先复用已有结果，不暴露旧显式分析入口。
- 插件 / skill 只引导 `project create --repo-url`，不再引导显式分析命令。

### 4.6 `project show`

输出：

- `project`
- `repository`
- `watch`
- `last_parsed_commit`
- `init_result`

### 4.7 `git verify-doc-change`

输入：

- `commit_message`
- `project_id`
- `branch`

输出：

- `doc_change_id`
- `verification_status`
- `doc_change_status`
- `risk_level`
- `next_status`

规则：

- 统一解析 `DocChange-ID: <id>` trailer
- 校验成功后建立 `CodeChangeLink`
- 合法引用时可推进 `DocChange -> in_implementation`

### 4.8 `git post-push-refresh`

输入：

- `project_id`
- `branch`
- 可选 `commit_sha` 或 commit 范围

输出：

- `commits_synced`
- `graph_nodes_updated`
- `chains_updated`
- `index_reused`
- `index_regenerated`

规则：

- 推送后按新增 commit 范围刷新
- 默认不执行全库全量刷新
- 受影响节点需要同步更新图谱关系与必要索引

### 4.9 `cli version-check`

输入：

- 可选 `auto_update`

输出：

- `cli_version`
- `plugin_version`
- `skill_version`
- `compatible`
- `update_available`
- `updated`
- `target_version`
- `message`

规则：

- 用于检查 CLI 与插件 / skill 是否保持强一致
- 当 `auto_update=true` 且存在可用更新时，可自动拉齐版本
- 若返回 `compatible=false`，插件 / skill 不应继续执行高风险写操作

## 5. 状态语义

### 5.1 `DocChange`

- `pending_implementation`
- `in_implementation`
- `implemented`

### 5.2 `RepositoryGraphBuild`

- `queued`
- `running`
- `completed`
- `failed`

### 5.3 `semantic_status`

- `ready`
- `degraded`
- `not_vectorized`

## 6. 与插件 / Skill 的协作要求

插件 / skill 负责：

- 引导命令选择
- 组织工作流
- 提示风险
- 补全参数
- 解释结果
- 在会话开始或关键写操作前执行版本检查

CLI 负责：

- 执行业务命令
- 持久化业务状态
- 返回结构化事实
- 校验 ID 引用
- 推动状态变更

协作约束：

- 不采用多套输出协议并存
- 默认先保证 CLI 与插件 / skill 版本一致
- 若发现不兼容，优先调用 `cli version-check`

## 7. 最小成功标准

MVP 视为契约成立，需要满足：

- 所有核心命令均有明确输入、输出和副作用定义
- 产品版本范围语义检索可用
- 仓库地址接入后会自动触发远程图谱构建
- `DocChange-ID` 校验与推送后刷新可用
- 节点刷新和链路获取可用
- 插件 / skill 可通过 `cli version-check` 与 CLI 保持一致
