---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-FEATURES-F002-GRAPH-QUERY-AND-CHANGE-CONTEXT
title: "F002 图谱查询、文档语义检索与上下文供给 PRD"
aliases:
  - "F002 图谱查询、文档语义检索与上下文供给 PRD"
tags:
  - neodev/docs
  - neodev/prd
  - neodev/requirements
created: 2026-04-27
updated: 2026-04-27
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
  - "[[01-master-prd]]"
---
# F002 图谱查询、文档语义检索与上下文供给 PRD

## 1. 基本信息

| 项 | 值 |
| --- | --- |
| 功能 ID | F002 |
| 优先级 | P0 |
| 对应总 PRD | [../01-master-prd.md](../01-master-prd.md) |
| 关键来源 | SRC-U-010, SRC-U-011, SRC-U-015, SRC-U-016, SRC-U-017, SRC-U-018, SRC-C-002, SRC-C-004, SRC-C-009, SRC-C-012, SRC-C-014, SRC-C-015 |

## 2. 功能目标

F002 负责向本地智能工具输出“可消费的事实和关系”，包括：

- DocChange 影响范围查询
- 图谱实体上下文查询
- 产品版本作用域下的文档语义检索
- 仓库代码图谱节点的结构事实查询
- 链路获取
- 节点、关系、节点类型和关系类型的 CLI 管理

这部分能力默认由插件/skill 引导用户使用 CLI，但真正执行、校验和结果输出都落在 CLI。

## 3. 范围

### 3.1 范围内

- `graph impact`
- `graph entity-context`
- `graph semantic-search`
- `graph get-chain`
- `graph type node add/list/archive`
- `graph type edge add/list/archive`
- `graph node add/update/delete/show/list`
- `graph edge add/update/delete/show/list`
- 代码结构事实输出
- 文档版本级检索范围控制
- 项目内节点类型和关系类型白名单控制
- 跨项目关系管理

### 3.2 范围外

- 直接生成代码补丁
- 文档登记
- Git 推送校验

## 4. 分层规则

### 4.1 插件 / Skill 负责

- 识别用户当前处于“查影响 / 查链路 / 查上下文 / 查文档语义”哪个阶段
- 自动推荐正确 CLI
- 自动补全 `product_key/version/project/branch` 参数
- 解释 CLI 输出给用户
- 把多个 CLI 编排成一步式工作流

### 4.2 CLI 负责

- 查询图谱事实
- 查询代码结构事实
- 管理节点、关系、节点类型和关系类型
- 获取链路
- 返回结构化结果
- 做最终参数和作用域校验

## 5. 用户故事

| ID | 用户故事 |
| --- | --- |
| US-F002-01 | 开发者可以基于 `DocChange` 查询受影响仓库、模块、文件和符号 |
| US-F002-02 | 研发负责人可以在某个产品版本下执行文档语义检索，而不是跨全库无边界搜索 |
| US-F002-03 | 本地智能工具可以读取图谱实体上下文和关系证据，用于生成修改方案 |
| US-F002-04 | 代码推送后，研发负责人或开发者可以查询更新后的结构事实和链路 |
| US-F002-05 | 本地智能工具可以按节点、文件、符号或 commit 获取链路，用于分析调用链、依赖链和影响面 |
| US-F002-06 | 研发负责人可以通过 CLI 修正或补充任意图节点的信息 |
| US-F002-07 | 研发负责人可以通过 CLI 建立项目内或跨项目的受控关系 |

## 6. CLI 能力

| 命令 | 说明 |
| --- | --- |
| `doc change show` | 查看 DocChange 元数据、状态、摘要 |
| `graph impact` | 返回 DocChange 的候选影响范围 |
| `graph entity-context` | 返回图谱实体邻接上下文 |
| `graph semantic-search` | 在产品版本作用域内执行文档语义检索 |
| `graph get-chain` | 获取节点、文件、符号或 commit 的关系链路 |
| `graph type node add/list/archive` | 管理项目内允许的节点类型 |
| `graph type edge add/list/archive` | 管理项目内允许的关系类型 |
| `graph node add/update/delete/show/list` | 管理项目内节点，所有节点都允许手动修改 |
| `graph edge add/update/delete/show/list` | 管理关系，允许跨项目连接节点 |

## 7. 业务规则

| ID | 规则 | 验收 |
| --- | --- | --- |
| BR-F002-01 | `graph impact` 输出必须包含 `affected_repositories/affected_modules/affected_files/affected_symbols/evidence/confidence/risk_points/suggested_steps` | AC-F002-01 |
| BR-F002-02 | 文档关系以 front matter `relations` 为主，正文显式引用为补充 | AC-F002-02 |
| BR-F002-03 | 所有 CLI 查询结果都必须是结构化输出，便于插件/skill 和本地 Agent 消费 | AC-F002-03 |
| BR-F002-04 | 文档语义检索必须限制在 `ProductVersion` 作用域内 | AC-F002-04 |
| BR-F002-05 | 文档检索结果必须返回文档、分块、片段和分数，而不是只返回一段不可追踪文本 | AC-F002-04 |
| BR-F002-06 | 仓库代码图谱节点不得依赖 AI 摘要、embedding 或代码语义搜索 | AC-F002-05 |
| BR-F002-07 | 文档 embedding 不可用时，系统仍可退化返回明确状态，不影响代码结构图谱查询 | AC-F002-05 |
| BR-F002-08 | 当代码节点 `content_hash` 未变化时，应复用已有仓库级结构事实，不重复构建 | AC-F002-06 |
| BR-F002-09 | `graph refresh-nodes` 不属于 MVP 命令面 | AC-F002-07 |
| BR-F002-10 | 代码推送后只更新仓库级结构事实和分支快照，不生成代码语义字段 | AC-F002-07 |
| BR-F002-11 | `graph get-chain` 必须支持直接邻接和 N 跳链路查询 | AC-F002-08 |
| BR-F002-12 | 链路结果必须返回节点、边、方向和简要路径摘要，而不是只返回文本描述 | AC-F002-08 |
| BR-F002-13 | 节点类型必须来自节点所属项目的 `graph_node_types` 白名单 | AC-F002-09 |
| BR-F002-14 | 关系类型必须来自关系归属项目的 `graph_relation_types` 白名单 | AC-F002-10 |
| BR-F002-15 | 所有节点都允许通过 CLI 手动修改，但 `id/project_id/repo_id/file_path/content_hash` 等身份字段不可改写 | AC-F002-11 |
| BR-F002-16 | 关系允许跨项目，但关系自身必须有归属项目 `project_id` | AC-F002-12 |
| BR-F002-17 | 跨项目关系的归属项目必须是起点或终点节点所属项目之一 | AC-F002-13 |
| BR-F002-18 | 关系类型可声明 `cross_project_allowed=false`，此时起点和终点节点必须属于同一项目 | AC-F002-14 |

## 8. 输入输出

### 8.1 `graph impact`

输入：

- `doc_change_id`

输出：

- `doc_change_id`
- `document_summary`
- `affected_repositories`
- `affected_modules`
- `affected_files`
- `affected_symbols`
- `evidence`
- `confidence`
- `risk_points`
- `suggested_steps`

### 8.2 `graph semantic-search`

该命令只面向文档分块语义检索，不面向代码节点。

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

### 8.3 `graph get-chain`

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

### 8.4 `graph type node add/list/archive`

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

### 8.5 `graph type edge add/list/archive`

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

### 8.6 `graph node add/update/delete/show/list`

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

### 8.7 `graph edge add/update/delete/show/list`

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

## 9. 异常处理

| ID | 场景 | 处理 |
| --- | --- | --- |
| EX-F002-01 | `DocChange` 不存在 | 返回明确错误 |
| EX-F002-02 | 产品版本不存在 | 返回明确错误 |
| EX-F002-03 | 检索命中为空 | 返回空列表和作用域信息，不报错 |
| EX-F002-04 | 文档 embedding 不可用 | 返回 `semantic_status=degraded/not_vectorized`，代码图谱查询不受影响 |
| EX-F002-05 | 指定节点或路径不存在 | 返回明确错误 |
| EX-F002-06 | 链路为空 | 返回空链路结构而非失败 |
| EX-F002-07 | 节点类型未登记 | 返回 `invalid_type`，不创建或更新节点 |
| EX-F002-08 | 关系类型未登记 | 返回 `invalid_type`，不创建或更新关系 |
| EX-F002-09 | 跨项目关系归属项目不合法 | 返回 `invalid_scope`，不创建关系 |
| EX-F002-10 | 尝试修改节点身份字段 | 返回 `invalid_argument`，不更新节点 |

## 10. 验收标准

| ID | 前置条件 | 操作 | 预期结果 |
| --- | --- | --- | --- |
| AC-F002-01 | 某 `DocChange` 已登记 | 执行 `graph impact` | 返回模块/文件/符号级候选影响范围和证据 |
| AC-F002-02 | 文档 front matter 中存在 `relations` | 查询 DocChange 上下文 | 返回文档间关系与关联证据 |
| AC-F002-03 | 插件/skill 或本地智能工具调用 CLI | 查询图谱上下文 | 返回结构化 JSON/表结构输出，而非不可解析文本 |
| AC-F002-04 | 产品版本已绑定文档范围 | 执行 `graph semantic-search` | 检索结果仅来自该版本作用域内的文档分块 |
| AC-F002-05 | 仓库图谱节点已完成结构事实写入 | 执行代码图谱查询 | 返回文件、符号和关系，不返回代码节点语义字段 |
| AC-F002-06 | 节点 `content_hash` 未变化 | 再次触发图谱构建 | 复用已有仓库级结构事实，不重复生成 |
| AC-F002-07 | 用户尝试执行代码节点刷新 | 执行 `graph refresh-nodes` | CLI 拒绝该命令或不注册该命令 |
| AC-F002-08 | 用户指定节点、文件、符号或 commit | 执行 `graph get-chain` | 返回节点、边、方向和路径摘要 |
| AC-F002-09 | 项目未登记节点类型 `SERVICE` | 执行 `graph node add --type SERVICE` | 返回类型错误，不创建节点 |
| AC-F002-10 | 项目已登记关系类型 `DEPENDS_ON` | 执行 `graph edge add --type DEPENDS_ON` | 创建关系并返回归属项目、起止节点和跨项目标记 |
| AC-F002-11 | 已存在代码解析生成节点 | 执行 `graph node update` | 可更新名称、类型和属性，不允许改写身份字段 |
| AC-F002-12 | A 项目节点连接 B 项目节点，关系归属 A | 执行 `graph edge add --project-id A` | 成功创建跨项目关系 |
| AC-F002-13 | A 项目节点连接 B 项目节点，关系归属 C | 执行 `graph edge add --project-id C` | 返回作用域错误 |
| AC-F002-14 | 关系类型禁止跨项目 | 用该类型连接不同项目节点 | 返回作用域错误 |

## 11. 测试场景

| ID | 优先级 | 场景 |
| --- | --- | --- |
| TC-F002-01 | P0 | 基于 `DocChange` 查询影响范围 |
| TC-F002-02 | P0 | 输出文档关系证据 |
| TC-F002-03 | P0 | 在产品版本作用域内执行文档语义检索 |
| TC-F002-04 | P0 | 文档检索结果返回文档、分块、片段和分数 |
| TC-F002-05 | P0 | 推送后更新仓库级结构事实和分支快照 |
| TC-F002-06 | P0 | 按节点或文件获取直接关系和 N 跳链路 |
| TC-F002-07 | P1 | embedding 退化场景返回 `semantic_status=degraded` |
| TC-F002-08 | P1 | `content_hash` 命中后复用已有结构事实 |
| TC-F002-09 | P0 | 节点类型白名单限制节点新增和更新 |
| TC-F002-10 | P0 | 关系类型白名单限制关系新增和更新 |
| TC-F002-11 | P0 | 所有节点允许手动更新非身份字段 |
| TC-F002-12 | P0 | 跨项目关系按关系归属项目校验 |
