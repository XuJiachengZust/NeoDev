---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-FEATURES-F002-GRAPH-QUERY-AND-CHANGE-CONTEXT
title: "F002 图谱查询、版本语义检索与上下文供给 PRD"
aliases:
  - "F002 图谱查询、版本语义检索与上下文供给 PRD"
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
# F002 图谱查询、版本语义检索与上下文供给 PRD

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
- 产品版本作用域下的语义检索
- 仓库图谱节点的 结构化摘要与向量化结果
- 节点刷新与链路获取

这部分能力默认由插件/skill 引导用户使用 CLI，但真正执行、校验和结果输出都落在 CLI。

## 3. 范围

### 3.1 范围内

- `graph impact`
- `graph entity-context`
- `graph semantic-search`
- `graph refresh-nodes`
- `graph get-chain`
- 结构化摘要和 embedding 状态输出
- 版本级检索范围控制

### 3.2 范围外

- 直接生成代码补丁
- 文档登记
- Git 推送校验

## 4. 分层规则

### 4.1 插件 / Skill 负责

- 识别用户当前处于“查影响 / 查链路 / 刷节点 / 查语义”哪个阶段
- 自动推荐正确 CLI
- 自动补全 `product_key/version/project/branch` 参数
- 解释 CLI 输出给用户
- 把多个 CLI 编排成一步式工作流

### 4.2 CLI 负责

- 查询图谱事实
- 刷新节点和 结构化描述
- 获取链路
- 返回结构化结果
- 做最终参数和作用域校验

## 5. 用户故事

| ID | 用户故事 |
| --- | --- |
| US-F002-01 | 开发者可以基于 `DocChange` 查询受影响仓库、模块、文件和符号 |
| US-F002-02 | 研发负责人可以在某个产品版本下执行语义检索，而不是跨全库无边界搜索 |
| US-F002-03 | 本地智能工具可以读取图谱实体上下文和关系证据，用于生成修改方案 |
| US-F002-04 | 代码推送后，研发负责人或开发者可以手动刷新受影响节点和 结构化描述 |
| US-F002-05 | 本地智能工具可以按节点、文件、符号或 commit 获取链路，用于分析调用链、依赖链和影响面 |

## 6. CLI 能力

| 命令 | 说明 |
| --- | --- |
| `doc change show` | 查看 DocChange 元数据、状态、摘要 |
| `graph impact` | 返回 DocChange 的候选影响范围 |
| `graph entity-context` | 返回图谱实体邻接上下文 |
| `graph semantic-search` | 在产品版本作用域内执行语义检索 |
| `graph refresh-nodes` | 按节点、路径、commit 或分支范围刷新代码节点及 结构化描述 |
| `graph get-chain` | 获取节点、文件、符号或 commit 的关系链路 |

## 7. 业务规则

| ID | 规则 | 验收 |
| --- | --- | --- |
| BR-F002-01 | `graph impact` 输出必须包含 `affected_repositories/affected_modules/affected_files/affected_symbols/evidence/confidence/risk_points/suggested_steps` | AC-F002-01 |
| BR-F002-02 | 文档关系以 front matter `relations` 为主，正文显式引用为补充 | AC-F002-02 |
| BR-F002-03 | 所有 CLI 查询结果都必须是结构化输出，便于插件/skill 和本地 Agent 消费 | AC-F002-03 |
| BR-F002-04 | 语义检索必须限制在 `ProductVersion` 映射的项目分支内 | AC-F002-04 |
| BR-F002-05 | 检索结果必须尽量返回项目、分支、文件、实体和分数，而不是只返回一段文本 | AC-F002-04 |
| BR-F002-06 | 仓库图谱节点 图谱语义索引结果至少包含 `description/embedding_model/embedding_updated_at/semantic_status` | AC-F002-05 |
| BR-F002-07 | embedding preflight 或 embedding 生成失败时，系统仍可退化返回 description 或普通图谱结果，并显式标记 `semantic_status` | AC-F002-05 |
| BR-F002-08 | 当节点 `content_hash` 未变化时，语义增强应复用已有 description / embedding，不重复向量化 | AC-F002-06 |
| BR-F002-09 | `graph refresh-nodes` 必须支持按 `project/version/branch/node_id/path/commit` 作为刷新范围输入 | AC-F002-07 |
| BR-F002-10 | 节点刷新应同时覆盖代码节点关系和 结构化描述刷新结果 | AC-F002-07 |
| BR-F002-11 | `graph get-chain` 必须支持直接邻接和 N 跳链路查询 | AC-F002-08 |
| BR-F002-12 | 链路结果必须返回节点、边、方向和简要路径摘要，而不是只返回文本描述 | AC-F002-08 |

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

### 8.3 `graph refresh-nodes`

输入：

- `product_key`
- `product_version_id`
- `project_id`
- `branch`
- 可选 `node_ids`
- 可选 `paths`
- 可选 `commit_sha`

输出：

- `project_id`
- `branch`
- `refresh_scope`
- `graph_nodes_updated`
- `index_descriptions_updated`
- `embeddings_reused`
- `embeddings_regenerated`
- `status`

### 8.4 `graph get-chain`

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

## 9. 异常处理

| ID | 场景 | 处理 |
| --- | --- | --- |
| EX-F002-01 | `DocChange` 不存在 | 返回明确错误 |
| EX-F002-02 | 产品版本不存在 | 返回明确错误 |
| EX-F002-03 | 检索命中为空 | 返回空列表和作用域信息，不报错 |
| EX-F002-04 | embedding 不可用 | 返回 `semantic_status=degraded/not_vectorized` |
| EX-F002-05 | 指定节点或路径不存在 | 返回明确错误 |
| EX-F002-06 | 链路为空 | 返回空链路结构而非失败 |

## 10. 验收标准

| ID | 前置条件 | 操作 | 预期结果 |
| --- | --- | --- | --- |
| AC-F002-01 | 某 `DocChange` 已登记 | 执行 `graph impact` | 返回模块/文件/符号级候选影响范围和证据 |
| AC-F002-02 | 文档 front matter 中存在 `relations` | 查询 DocChange 上下文 | 返回文档间关系与关联证据 |
| AC-F002-03 | 插件/skill 或本地智能工具调用 CLI | 查询图谱上下文 | 返回结构化 JSON/表结构输出，而非不可解析文本 |
| AC-F002-04 | 产品版本已绑定项目分支 | 执行 `graph semantic-search` | 检索结果仅来自该版本作用域内的分支 |
| AC-F002-05 | 仓库图谱节点已完成 图谱语义索引 | 执行语义检索 | 返回 description、score、semantic_status 等字段 |
| AC-F002-06 | 节点 `content_hash` 未变化 | 再次触发语义增强并检索 | 复用已有向量结果，不重复生成 |
| AC-F002-07 | 用户指定项目/版本/分支以及节点、路径或 commit 范围 | 执行 `graph refresh-nodes` | 受影响代码节点和 结构化描述被刷新，并返回更新摘要 |
| AC-F002-08 | 用户指定节点、文件、符号或 commit | 执行 `graph get-chain` | 返回节点、边、方向和路径摘要 |

## 11. 测试场景

| ID | 优先级 | 场景 |
| --- | --- | --- |
| TC-F002-01 | P0 | 基于 `DocChange` 查询影响范围 |
| TC-F002-02 | P0 | 输出文档关系证据 |
| TC-F002-03 | P0 | 在产品版本作用域内执行语义检索 |
| TC-F002-04 | P0 | 检索结果返回项目、分支、文件和分数 |
| TC-F002-05 | P0 | 按 commit 范围刷新受影响节点和 结构化描述 |
| TC-F002-06 | P0 | 按节点或文件获取直接关系和 N 跳链路 |
| TC-F002-07 | P1 | embedding 退化场景返回 `semantic_status=degraded` |
| TC-F002-08 | P1 | `content_hash` 命中后复用已有语义结果 |
