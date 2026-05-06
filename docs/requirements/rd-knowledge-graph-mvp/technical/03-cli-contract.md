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

- `doc binding list`
- `doc change show`
- `graph semantic-search`
- `graph entity-context`
- `graph get-chain`
- `project show`
- `cli version-check`

有副作用命令：

- `doc binding create`
- `doc scan`
- `doc import`
- `doc change register`
- `doc change mark-implemented`
- `project create`
- `project refresh-commit-graph`
- `project refresh-graph`
- `graph type node add`
- `graph type node archive`
- `graph type edge add`
- `graph type edge archive`
- `graph node add`
- `graph node update`
- `graph node delete`
- `graph edge add`
- `graph edge update`
- `graph edge delete`
- `git verify-doc-change`
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

- `doc binding create`
- `doc binding list`
- `doc scan`
- `doc import`
- `doc change register`
- `doc change show`
- `doc change mark-implemented`

### 3.3 图谱与检索

- `graph impact`
- `graph entity-context`
- `graph semantic-search`
- `graph get-chain`
- `graph type node add/list/archive`
- `graph type edge add/list/archive`
- `graph node add/update/delete/show/list`
- `graph edge add/update/delete/show/list`

### 3.4 仓库接入与自动图谱构建

- `project create --repo-url`
- `project refresh-commit-graph`
- `project refresh-graph`
- `project show`

兼容说明：旧显式分析命令只保留给历史集成，不再作为插件 / skill 推荐入口，也不应出现在用户主流程中。

### 3.5 Git 一致性

- `git verify-doc-change`
- `git dangerous-commit resolve`

### 3.6 本地客户端配置与版本检查

- `config set-server`
- `config show`
- `cli version-check`

## 4. 核心命令契约

### 4.0 `doc binding create/list`

`doc binding create` 输入：

- `product_code` 或 `product_id`
- 可选 `project_id` 或 `project_name`
- 可选 `repo_url`
- 可选 `repo_path`
- 可选 `branch`

输出：

- `binding.id`
- `binding.product_id`
- `binding.repo_path`
- `binding.repo_url`
- `binding.default_branch`
- `import_command`

规则：

- 产品下只能有一个 active `DocBinding`。
- 可以从已登记文档项目创建绑定；当项目 `repo_path` 是 Git URL 时，写入 `repo_url`，并将 `repo_path` 解析为远端服务可克隆的文档目录。
- `doc import` 前应先通过 `doc binding list` 获取 active `doc_binding_id`；缺失时再调用 `doc binding create`。
- 不允许插件 / skill 绕过 CLI 直接写 `doc_bindings`。

`doc binding list` 输入：

- `product_code` 或 `product_id`

输出：

- `bindings[]`

### 4.0.1 `doc import`

输入：

- `doc_binding_id`
- 可选 `force`

输出：

- `documents[]` 为轻量摘要，不返回 `body_text` 或完整 front matter。
- `documents[].last_seen_commit`
- `documents[].content_hash`
- `documents[].relative_path`

规则：

- 文档仓库必须是 Git checkout。
- 导入前同步 `doc_bindings.default_branch`。
- 导入范围是文档仓库 docs root 下全部 Markdown 文件，跳过 `.git`、`.obsidian` 等隐藏/内部目录；不再限制为顶层 `prd/`、`prototype/`、`tech-design/`。
- 导入时将文档仓库项目投影到图数据库，并建立 `Project -[:HAS_DOCUMENT]-> Document` 归属关系。
- 每篇导入文档必须写入该文件最近一次提交的 40 位 Git commit hash 到 `last_seen_commit`。
- 如果文档文件未提交、存在未提交变更，或无法取得 commit hash，则该文档导入失败，不生成不可靠版本事实。
- `doc change register` 未显式传入 `doc_change_id` 或 `source_commit` 时，默认使用目标文档的 `last_seen_commit`，因此 DocChange-ID 直接等于文档 commit hash。

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

该命令只检索产品版本作用域内的文档分块，不检索代码节点，也不要求代码节点具备 AI 摘要或 embedding。

输入：

- `product_key`
- `product_version_id` 或 `version_name`
- `query`
- 可选 `top_k`

输出：

- `product_version_id`
- `document_id`
- `doc_id`
- `title`
- `doc_type`
- `relative_path`
- `chunk_id`
- `snippet`
- `score`
- `semantic_status`

### 4.3 `graph get-chain`

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

### 4.6 `project refresh-commit-graph`

输入：

- `project_id`
- `branch`
- `commit_sha`
- `product_version_id` 或 `version_id`
- 可选 `max_changed_files`

输出：

- `project_id`
- `branch`
- `commit_sha`
- `head_commit`
- `graph_action=commit_incremental`
- `fallback`
- `fallback_reason`
- `changed_paths`
- `changed_file_count`
- `current_snapshot_id`
- `snapshot_entry_count`
- `graph_errors`

规则：

- 推送成功后默认调用该命令。
- 只解析 `commit_sha` 相对父提交变更的受支持代码文件，更新对应代码节点和关系。
- 如果提交不是分支 HEAD、找不到父提交、变更文件数超过阈值或范围无法可靠定位，服务端可回退到 `project refresh-graph`。
- 回退到分支图刷新时，必须保留文档节点与代码节点之间已有关系。
- 不生成代码节点 AI 摘要、embedding 或语义状态。

### 4.7 `project refresh-graph`

输入：

- `project_id`
- `branch`
- `product_version_id` 或 `version_id`

输出：

- `project_id`
- `branch`
- `product_version_id`
- `head_commit`
- `graph_action=full`
- `current_snapshot_id`
- `snapshot_entry_count`
- `graph_errors`

规则：

- 这是分支级兜底刷新入口，不作为推送后的默认刷新命令。
- 重新拉取项目仓库指定分支。
- 重新解析当前分支完整结构图。
- 写入仓库级事实节点和关系。
- 生成新的分支快照。
- 必须保留文档节点与代码节点之间已有关系。
- 不生成代码节点 AI 摘要、embedding 或语义状态。

### 4.8 `project show`

输出：

- `project`
- `repository`
- `watch`
- `last_parsed_commit`
- `init_result`

### 4.8 `graph type node add/list/archive`

输入：

- `project_id`
- `key`
- `name`
- 可选 `description`
- 可选 `status`

输出：

- `project_id`
- `key`
- `name`
- `status`

规则：

- 节点类型只在所属项目内有效。
- CLI 不允许创建未登记类型的节点。

### 4.9 `graph type edge add/list/archive`

输入：

- `project_id`
- `key`
- `name`
- 可选 `allowed_from_types`
- 可选 `allowed_to_types`
- 可选 `cross_project_allowed`
- 可选 `status`

输出：

- `project_id`
- `key`
- `name`
- `cross_project_allowed`
- `status`

规则：

- 关系类型只在关系归属项目内有效。
- CLI 不允许创建未登记类型的关系。

### 4.10 `graph node add/update/delete/show/list`

输入：

- `project_id`
- `node_id`
- `type`
- `name`
- 可选 `properties`
- 可选 `status`

输出：

- `node_id`
- `project_id`
- `type`
- `name`
- `properties`
- `status`

规则：

- 所有节点都允许手动修改。
- 节点类型必须来自节点所属项目的节点类型白名单。
- `id/project_id/repo_id/file_path/content_hash` 等身份字段不可通过 CLI 改写。

### 4.11 `graph edge add/update/delete/show/list`

输入：

- `project_id`
- `edge_id`
- `from_node_id`
- `to_node_id`
- `type`
- 可选 `properties`
- 可选 `status`

输出：

- `edge_id`
- `project_id`
- `from_node_id`
- `to_node_id`
- `from_project_id`
- `to_project_id`
- `type`
- `cross_project`
- `properties`
- `status`

规则：

- 关系类型必须来自关系归属项目的关系类型白名单。
- 关系允许跨项目连接节点。
- 跨项目关系的归属项目必须是起点或终点节点所属项目之一。
- 当关系类型 `cross_project_allowed=false` 时，起点和终点节点必须属于同一项目。

### 4.12 `git verify-doc-change`

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

### 4.13 `cli version-check`

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

该状态只用于文档语义检索结果，不用于代码图谱节点。

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
- 产品版本范围内的文档语义检索可用
- 仓库地址接入后会自动触发远程图谱构建
- `DocChange-ID` 校验与整图刷新可用
- 链路获取和上下文查询可用
- 节点、关系、节点类型和关系类型的受控管理可用
- 插件 / skill 可通过 `cli version-check` 与 CLI 保持一致
