---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
title: "研发知识图谱中台 MVP 总 PRD"
aliases:
  - "研发知识图谱中台 MVP 总 PRD"
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
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-00-SOURCE-INDEX
related:
  - "[[00-source-index]]"

---

# 研发知识图谱中台 MVP 总 PRD

## 1. 文档信息


| 项    | 值                                          |
| ---- | ------------------------------------------ |
| 需求编号 | R-001                                      |
| 版本   | v0.6                                       |
| 更新时间 | 2026-04-24                                 |
| 范围   | MVP                                        |
| 来源索引 | [00-source-index.md](./00-source-index.md) |


## 2. 产品定位

这是一个面向企业研发的知识图谱中台 MVP。系统以 `Product` 为组织单元，统一管理：

- 多个项目代码仓库的指定分支
- 一个独立的文档仓库
- 产品版本与项目分支映射
- 代码图谱、文档图谱和语义索引

本产品不是让用户裸用 CLI 的工具箱，而是默认与 `插件 / skill` 配合使用：

- `插件 / skill` 负责指导、编排、解释和参数补全
- 本地 `neodev` CLI 客户端负责调用统一远程 NeoDev 服务
- 远程 NeoDev 服务负责执行、校验、持久化、返回结构化事实

一期不做 UI，不做重工作流。开发者电脑只安装 CLI 客户端、官方 skill 和官方插件；服务端、数据库、图谱、分析执行和状态管理集中部署在统一远程 NeoDev 环境。

## 3. MVP 目标

1. 让研发负责人以“产品 + 产品版本”视角组织代码、文档和知识关系。
2. 让文档变更成为代码实现闭环的起点。
3. 让本地智能工具在插件/skill 引导下调用本地 CLI 客户端，由客户端请求统一远程 NeoDev 服务并获取稳定事实和结构化图谱结果。
4. 让产品下任一项目仓库分支都可通过本地 CLI 显式触发远程分析，并可追踪状态与进度。
5. 在多分支共用相同代码时，避免重复跑同一份图谱分析和语义向量化。
6. 让代码推送后的提交可以驱动链路上的代码节点和 AI 描述更新，并向 CLI 暴露节点刷新与链路获取能力。

## 4. 非目标

- 不做文档 UI
- 不做复杂审批流
- 不做任务管理、人力管理、项目管理
- 不做平台内自动提交代码补丁
- 不把插件/skill 做成新的事实源

## 5. 主要用户


| 用户    | 角色定位                                    |
| ----- | --------------------------------------- |
| U-001 | 研发负责人，主用户，负责产品、版本、仓库、文档、分析闭环管理          |
| U-002 | 开发者，通过插件/skill 引导调用 CLI，查询上下文、生成方案、提交代码 |
| U-003 | 产品/技术方案作者，维护 PRD / 原型 / 技术设计文档          |


岗位边界默认弱化，允许一人兼任多个角色。

## 6. 核心对象模型


| ID     | 对象                    | 说明                    | 关键字段                                                                                                                                           |
| ------ | --------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| BO-001 | Product               | 业务级知识容器               | `product_id`, `product_key`, `name`, `status`                                                                                                  |
| BO-002 | CodeBinding           | 产品绑定的代码仓库分支           | `binding_id`, `repo_url`, `branch`, `path_scope`, `enabled`                                                                                    |
| BO-003 | DocBinding            | 产品绑定的唯一文档仓库           | `doc_binding_id`, `repo_url`, `branch`, `doc_root`, `enabled`                                                                                  |
| BO-004 | Document              | 文档仓库中的单篇文档            | `document_id`, `doc_id`, `repo_path`, `doc_type`, `status`, `current_commit`                                                                   |
| BO-005 | DocChange             | 一次文档提交对应的一次实现跟踪单元     | `doc_change_id`, `document_id`, `doc_commit`, `status`, `created_at`                                                                           |
| BO-006 | CodeChangeLink        | 代码提交与 DocChange 的关联事实 | `link_id`, `doc_change_id`, `commit_sha`, `verification_status`                                                                                |
| BO-007 | DangerousCommitRecord | 危险提交登记记录              | `dangerous_commit_id`, `resolved_by`, `resolved_at`, `status`                                                                                  |
| BO-008 | ProductVersion        | 产品版本，承载版本级分支映射与检索范围   | `product_version_id`, `version_name`, `branch_mappings`, `status`                                                                              |
| BO-009 | BranchAnalysisTask    | 某个产品下某个项目仓库分支的一次分析任务  | `analysis_task_id`, `product_id`, `project_id`, `branch`, `status`, `progress`, `started_at`, `finished_at`, `heartbeat_at`, `analysis_action` |


## 7. 核心能力


| ID    | 能力                                         | 说明                             |
| ----- | ------------------------------------------ | ------------------------------ |
| T-004 | Code Change Proposal Context               | 输出模块/文件/符号级修改建议上下文             |
| T-006 | Document Relation                          | 文档间关系建模与解析                     |
| T-007 | Product Version Semantic Retrieval         | 在产品版本范围内做语义检索                  |
| T-008 | Repository AI Semantic Enrichment          | 对仓库图谱节点做 AI 摘要、embedding 与向量索引 |
| T-009 | Branch Analysis Orchestration              | 触发项目仓库分支分析、查看状态/进度、避免重复分析      |
| T-010 | Post-Push Node Refresh And Chain Retrieval | 推送后刷新链路代码节点、AI 描述并输出链路         |


## 8. 分层原则

### 8.1 插件 / Skill 职责

插件 / skill 是引导层和编排层，负责：

- 指导用户选择正确 CLI
- 解释当前阶段应该先查什么、再改什么、最后推什么
- 自动补全参数和拼装命令
- 提示风险并做人机交互确认
- 解释 CLI 结果并转成可读建议
- 把多个 CLI 串成稳定工作流

### 8.2 CLI 职责

CLI 是执行层和事实层，负责：

- 执行业务动作
- 做最终校验
- 持久化状态与结果
- 更新图谱、节点、链路和 AI 描述
- 返回结构化输出

### 8.3 必须放在 CLI 的规则

- 文档与代码状态机
- `DocChange-ID` 合法性校验
- 危险提交登记与关闭
- `copy_data / incremental / full` 判定
- `last_parsed_commit`、`content_hash`、embedding 复用
- 节点刷新、链路获取、语义检索、影响分析
- 推送后图谱与 AI 描述刷新

### 8.4 适合放在插件 / Skill 的规则

- 工作流引导
- 参数建议与默认值
- 风险说明与继续确认
- 结果解读与下一步建议
- 多条 CLI 串联的自动编排

## 9. 全局业务规则


| ID      | 规则                           | 内容                                                                                      |
| ------- | ---------------------------- | --------------------------------------------------------------------------------------- |
| BR-G-01 | Git 为代码事实源                   | 代码只通过 Git 仓库和分支识别                                                                       |
| BR-G-02 | 文档独立管理                       | 一个产品绑定一个独立文档仓库                                                                          |
| BR-G-03 | 文档提交生成 DocChange             | 每次受控文档提交都生成一个 `DocChange ID`                                                            |
| BR-G-04 | DocChange 默认待实现              | 新生成的 DocChange 默认进入 `pending_implementation`                                            |
| BR-G-05 | 默认通过插件/skill 使用 CLI          | 用户不直接面向底层服务，默认通过插件/skill 引导调用 CLI                                                       |
| BR-G-06 | CLI 是执行与事实唯一入口               | 所有状态变更、图谱更新、节点刷新、链路获取都必须通过 CLI                                                          |
| BR-G-07 | 插件/skill 不持久化业务事实            | 插件/skill 不能成为状态机、校验结果和图谱结果的事实源                                                          |
| BR-G-08 | 代码提交必须引用 DocChange           | Git 提交使用 trailer `DocChange-ID: <doc_change_id>`                                        |
| BR-G-09 | implemented 只能人工确认           | 校验通过后先进入 `in_implementation`，`implemented` 仅人工确认                                        |
| BR-G-10 | 危险提交二次确认后放行                  | 放行时必须登记 `DangerousCommitRecord`，后续记录 `resolved_by` 和 `resolved_at`                      |
| BR-G-11 | 文档仓库结构固定                     | 受控文档仅纳入 `prd/`、`prototype/`、`tech-design/`                                              |
| BR-G-12 | 文档元数据使用 YAML front matter    | 最小字段包含 `doc_id/title/doc_type/product_key/status/relations`                             |
| BR-G-13 | 版本语义检索按 ProductVersion 作用域执行 | 检索范围由 `product_version_branches` 决定                                                     |
| BR-G-14 | 图谱更新沿用既有三段策略                 | 代码图更新优先 `copy_data`，其次 `incremental`，最后 `full`，并维护 `last_parsed_commit`                 |
| BR-G-15 | 仓库图谱节点必须支持 AI 语义增强           | 节点支持 `description/embedding/embedding_model/embedding_updated_at`，并使用 `content_hash` 缓存 |
| BR-G-16 | 产品下项目仓库分支必须支持显式触发分析          | 可按产品版本或项目分支发起代码分析任务                                                                     |
| BR-G-17 | 分支分析必须可见状态和进度                | 至少支持 `running/completed/failed` 状态，以及 `progress/started_at/finished_at/heartbeat_at`    |
| BR-G-18 | 同代码跨分支不得重复分析                 | 当多个分支 `HEAD` 相同或内容哈希命中时，优先复用已有图谱和语义结果                                                   |
| BR-G-19 | 同一项目不可并发跑多个分析任务              | 已有运行中任务时，新任务应返回 busy/冲突                                                                 |
| BR-G-20 | 代码推送后必须支持刷新受影响链路上的代码节点       | 代码提交同步后，系统支持按提交或分支范围刷新受影响节点及其关系链路                                                       |
| BR-G-21 | 代码推送后必须支持刷新受影响节点的 AI 描述      | 图谱刷新后，应支持重新生成或复用 `description/embedding`                                                |
| BR-G-22 | CLI 必须开放节点更新能力               | 支持按 `project/version/branch/node_id/path/commit` 触发节点刷新                                 |
| BR-G-23 | CLI 必须开放链路获取能力               | 支持按节点、文件、符号或 commit 获取直接关系和 N 跳链路                                                       |


## 10. 状态机

### 10.1 Document 状态

- `draft`
- `active`
- `deprecated`

### 10.2 DocChange 状态

- `draft`
- `pending_implementation`
- `in_implementation`
- `implemented`
- `closed_no_code`

### 10.3 BranchAnalysisTask 状态

- `queued`
- `running`
- `completed`
- `failed`

## 11. CLI 能力面

### 11.1 产品与版本管理

- `product create`
- `product update`
- `product show`
- `product version create`
- `product version bind-branch`
- `product version show`

### 11.2 文档闭环

- `doc scan`
- `doc change register`
- `doc change show`
- `doc change mark-implemented`

### 11.3 图谱与检索

- `graph impact`
- `graph entity-context`
- `graph semantic-search`
- `graph refresh-nodes`
- `graph get-chain`

### 11.4 分支分析

- `product version analyze`
- `product version analyze-status`
- `product version watch-status`

### 11.5 Git 一致性与推送后刷新

- `git verify-doc-change`
- `git post-push-refresh`
- `git dangerous-commit resolve`

## 12. 核心流程

### 12.1 文档变更到代码修改方案

1. 用户提交文档仓库变更。
2. 系统扫描并生成 `DocChange ID`。
3. DocChange 状态进入 `pending_implementation`。
4. 插件/skill 引导本地智能工具通过 CLI 获取 DocChange、图谱关系和候选影响范围。
5. 智能工具输出模块/类/函数级代码修改方案。
6. 开发实现代码并在 commit trailer 中写入 `DocChange-ID`。
7. 推送前校验通过后回写 `in_implementation`。
8. 人工确认后更新为 `implemented`。

### 12.2 产品下项目仓库分支分析

1. 研发负责人选择 `product + product_version + project + branch`。
2. 插件/skill 引导执行 `product version analyze`。
3. CLI 先检查是否已有运行中任务。
4. CLI 检查该分支是否可直接复用：
  - 若与其他已分析分支 `HEAD` 相同，优先 `copy_data`
  - 若 `last_parsed_commit` 可衔接，执行 `incremental`
  - 否则执行 `full`
5. 分析过程中持续写入状态、进度和 heartbeat。
6. 分析完成后更新图谱、`last_parsed_commit`、语义摘要与 embedding。
7. 用户通过 `product version analyze-status` 或 `product version watch-status` 查看状态。

### 12.3 代码推送后的节点与链路刷新

1. 代码推送后，插件/skill 可引导执行 `git post-push-refresh`。
2. CLI 同步对应分支 commits 和代码图谱。
3. CLI 识别受影响的文件、符号或图谱节点。
4. CLI 按受影响范围刷新链路上的代码节点及关系。
5. CLI 对受影响节点执行 AI 描述刷新：
  - 若 `content_hash` 未变化，复用已有 `description/embedding`
  - 若内容变化，重新生成 AI 描述和 embedding
6. 插件/skill 可继续引导调用：
  - `graph refresh-nodes`
  - `graph get-chain`

## 13. 关键数据要求

### 13.1 文档 Front Matter

```yaml
---
doc_id: PRD-NEODEV-001
title: 研发知识图谱中台 MVP
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - PRD-NEODEV-000
---
```

### 13.2 分支分析状态输出

- `analysis_task_id`
- `product_id`
- `product_version_id`
- `project_id`
- `branch`
- `status`
- `progress`
- `analysis_action`
- `current_snapshot_id`
- `head_commit`
- `last_parsed_commit`
- `created_from_action`
- `started_at`
- `finished_at`
- `heartbeat_at`
- `error_message`
- `extra`

### 13.3 语义检索结果

- `product_version_id`
- `project_name`
- `branch`
- `entity_type`
- `entity_id`
- `file_path`
- `description`
- `score`
- `semantic_status`

### 13.4 链路获取结果

- `project_id`
- `product_version_id`
- `branch`
- `snapshot_id`
- `head_commit`
- `start_node`
- `depth`
- `nodes`
- `edges`
- `path_summary`
- `affected_commits`

## 14. 图存储结构简化设计

### 14.1 设计原则

MVP 简化图存储结构的重点不是减少节点类型和关系类型，而是避免同一仓库在多分支下重复存整套图数据。

正式口径：

- 图数据库存仓库级代码事实
- 分支只维护当前引用哪些代码事实的快照
- 不再为每个分支复制一套完整代码图

### 14.2 目标结构

图数据库保留：

- 仓库级代码节点和关系
- 文档节点和关系
- 节点级 `description / embedding / embedding_model / embedding_updated_at`

轻量元数据库新增或强化：

- `branch_snapshots`
- `branch_snapshot_entries`

推荐含义：

- `branch_snapshots` 记录 `repo_id / branch / head_commit / last_parsed_commit / base_snapshot_id / created_from_action`
- `branch_snapshot_entries` 记录某个分支快照当前可见的文件级节点引用

### 14.3 对多分支分析策略的影响

`copy_data / incremental / full` 继续保留，但语义收紧为：

- `copy_data`：复制分支快照引用，不复制整图
- `incremental`：只替换受影响文件对应的快照引用
- `full`：重建该分支的完整快照视图，但仍复用已有仓库级事实节点

### 14.4 对检索和链路查询的影响

- 语义检索先由 `ProductVersion -> branch snapshots` 限定范围，再检索文件和符号节点
- 链路查询先按分支快照裁剪可见节点，再做关系遍历
- 推送后节点刷新只更新受影响文件子图，并切换该分支快照引用

### 14.5 MVP 简化约束

- 不做按分支整图副本
- 不做按 commit 完整图快照
- 分支快照先以文件级 membership 为主
- 符号级可见性优先沿 `File -> Symbol` 包含关系推导

## 15. 验收标准


| ID      | 前置条件                   | 操作                                  | 预期结果                                                                 |
| ------- | ---------------------- | ----------------------------------- | -------------------------------------------------------------------- |
| AC-G-01 | 产品已绑定多个代码仓库分支和一个文档仓库   | 执行产品初始化和扫描                          | 图谱中存在 Product / CodeBinding / DocBinding / Document / ProductVersion |
| AC-G-02 | 受控文档有新提交               | 执行 `doc change register` 或自动登记      | 生成 `DocChange ID`，状态为 `pending_implementation`                       |
| AC-G-03 | 代码提交带合法 `DocChange-ID` | 执行推送前校验                             | 生成 `CodeChangeLink`，DocChange 转为 `in_implementation`                 |
| AC-G-04 | 产品版本已绑定项目分支            | 执行 `graph semantic-search`          | 只在该产品版本映射的分支范围内返回结果                                                  |
| AC-G-05 | 仓库图谱节点已做 AI 语义增强       | 执行语义检索                              | 返回 `description/score/semantic_status` 等字段                           |
| AC-G-06 | 产品下某项目仓库分支可访问          | 执行 `product version analyze`        | 创建或启动 `BranchAnalysisTask`，状态进入 `running`                            |
| AC-G-07 | 分支分析任务运行中              | 执行 `product version analyze-status` | 返回状态、进度、heartbeat、开始时间和当前 action                                     |
| AC-G-08 | 同一项目已有运行中分析任务          | 再次触发新分析                             | 返回 busy/冲突，不启动第二个运行中任务                                               |
| AC-G-09 | 新分支与已分析分支 `HEAD` 相同    | 触发分析                                | 优先复用已有图谱数据，不重复全量分析                                                   |
| AC-G-10 | 图谱节点内容哈希未变化            | 触发 AI 语义增强                          | 复用已有 description / embedding，不重复向量化                                  |
| AC-G-11 | 代码推送后有新增提交             | 执行 `git post-push-refresh`          | 受影响代码节点和链路被更新，必要时 AI 描述被刷新                                           |
| AC-G-12 | 用户指定节点、文件、符号或 commit   | 执行 `graph get-chain`                | 返回可消费的链路节点和边                                                         |
| AC-G-13 | 用户指定项目/版本/分支/节点范围      | 执行 `graph refresh-nodes`            | 完成节点刷新并返回更新摘要                                                        |


## 16. 版本范围

### P0

- 产品、版本、分支绑定
- 文档接入、DocChange 闭环
- 版本级语义检索
- 仓库图谱节点 AI 语义增强与向量化
- 分支分析触发、状态、进度、去重
- 推送前校验与危险提交登记
- 推送后图谱节点刷新、AI 描述刷新、链路获取
- 插件/skill 引导下的 CLI 工作流

### P1

- UI 页面
- 更复杂的自动完成判定
- 更细粒度的任务排队与调度策略
- 更复杂的人工审批流
