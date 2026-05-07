---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-T002-DATA-MODEL-REFACTOR-TASK-LIST
title: T002 数据模型重构任务清单
aliases:
- T002 数据模型重构任务清单
tags:
- neodev/docs
- neodev/tech-design
- neodev/requirements
created: 2026-04-27
updated: 2026-04-29
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
- '[[requirements/rd-knowledge-graph-mvp/01-master-prd|研发知识图谱中台 MVP 总 PRD]]'
---

# T002 数据模型重构任务清单

## 1. 目标

本任务用于重构研发知识图谱 MVP 的数据模型。新的模型以产品版本、项目分支快照、代码事实节点和文档到代码关系为核心，目标是精简、高效、可复用，并支撑后续从产品文档定位到方法、函数等最小功能单位。

核心目标：

- 一个产品可以包含多个项目。
- 一个项目只能对应一个代码仓库。
- `project_id` 同时作为项目身份和仓库身份，不再引入 `repo_id`。
- 分支名称只存在于产品版本绑定和分支快照层，不进入代码事实节点身份。
- 删除 commit 增量同步能力，统一使用分支图谱刷新。
- 分支快照直接关联方法、函数、类、文件等代码事实节点，不再只关联文件节点。
- PG 作为事实源，Neo4j 作为查询投影，可从 PG 重建。
- PG 和 Neo4j 都不存储实际源码，只存 hash、路径、符号和必要元数据。
- 文档到代码关系长期绑定稳定功能锚点，并在刷新图谱后自动检测和重建失效关系。

## 2. 总体设计

新的核心链路如下：

```text
product_version
-> product_version_branches
-> project_id + branch_name
-> latest branch_snapshot
-> branch_snapshot_facts
-> code_facts
```

文档到代码链路如下：

```text
document
-> doc_code_links.symbol_key
-> 当前 product_version 可见的 code_facts
```

其中：

- `product_version` 是业务版本。
- `product_version_branches` 表示一个产品版本由哪些项目分支组成。
- `branch_snapshot` 表示某个项目分支在一次刷新后的可见代码事实集合。
- `code_fact` 表示文件、类、方法、函数、构造器等代码节点的某个具体内容版本。
- `symbol_key` 表示稳定功能锚点，不包含代码内容 hash。
- `fact_id` 表示具体代码事实，包含代码内容 hash。

## 3. 保留、删除和新增

### 3.1 保留

- `projects`
- `products`
- `product_versions`
- `product_version_branches`
- `graph_node_types`
- `graph_relation_types`
- `graph_nodes`
- `graph_edges`

说明：

- `graph_*` 表只用于手工补充图，不与代码事实表混用。
- 代码事实固定使用系统枚举类型，不走手工节点类型表。

### 3.2 删除或废弃

- `repo_id`
- 项目级 `versions` 核心链路
- `sync_commit_graph_for_version`
- commit 增量图谱同步逻辑
- `incremental`
- `commit_incremental`
- `base_snapshot_id`
- 旧的文件级 `branch_snapshot_entries`
- 代码节点语义搜索
- 代码节点 AI 处理
- `code_fact_edges`

说明：

- 代码节点之间的结构关系不作为 PG 事实源存储。
- `CONTAINS`、`DEFINES`、`CALLS` 等关系由刷新图谱时重新解析并投影到 Neo4j。
- 如果后续需要纯 PG 影响分析，再单独评估是否恢复代码关系表。

### 3.3 新增或重建

- `code_facts`
- `branch_snapshot_facts`
- `doc_code_links`

## 4. 存储结构

### 4.1 projects

项目即仓库。

```text
projects
- id
- name
- repo_url
- repo_path
- created_at
- updated_at
```

约束：

- 一个项目只能有一个仓库。
- `project_id` 即代码仓库身份。

### 4.2 product_versions

产品业务版本。

```text
product_versions
- id
- product_id
- version_name
- description
- status
- created_at
- updated_at
```

### 4.3 product_version_branches

产品版本绑定项目分支。

```text
product_version_branches
- id
- product_version_id
- project_id
- branch_name
- created_at
- updated_at
```

约束：

```text
unique(product_version_id, project_id)
```

含义：

- 一个产品版本下，一个项目只能绑定一个分支。
- 一个产品版本可以绑定多个项目。
- 同一项目的不同产品版本可以绑定不同分支。

### 4.4 branch_snapshots

项目分支刷新后的快照。

```text
branch_snapshots
- id
- project_id
- branch_name
- head_commit
- snapshot_hash
- status
- created_at
```

索引：

```text
(project_id, branch_name, id desc)
(project_id, branch_name, status)
```

状态枚举：

```text
running
completed
failed
```

说明：

- 分支快照只表示当前分支可见代码事实集合。
- 不再维护增量快照链。
- `snapshot_hash` 由当前快照可见事实集合计算。

### 4.5 code_facts

代码事实节点。

```text
code_facts
- id
- project_id
- fact_id
- symbol_key
- node_type
- file_path
- qualified_name
- name
- signature_hash
- content_hash
- structure_hash
- parent_fact_id
- start_line
- end_line
- metadata_json
- status
- created_at
- updated_at
```

唯一约束：

```text
unique(project_id, fact_id)
```

推荐节点类型：

```text
File
Class
Interface
Enum
Annotation
Method
Function
Constructor
```

身份规则：

```text
symbol_key = hash(project_id + node_type + file_path + qualified_name)
fact_id = hash(project_id + node_type + file_path + qualified_name + content_hash)
```

说明：

- `symbol_key` 是稳定功能锚点。
- `fact_id` 是具体内容版本。
- 方法实现变化后，`content_hash` 和 `fact_id` 会变化，但 `symbol_key` 保持稳定。

### 4.6 branch_snapshot_facts

快照到代码事实的关联。

```text
branch_snapshot_facts
- id
- snapshot_id
- fact_id
```

唯一约束：

```text
unique(snapshot_id, fact_id)
```

说明：

- 逻辑上只需要 `snapshot_id + fact_id`。
- 如查询性能不足，可以冗余 `project_id`、`node_type`、`symbol_key`，但首版不作为必要字段。

### 4.7 doc_code_links

文档节点到代码节点的关系。

```text
doc_code_links
- id
- product_id
- product_version_id nullable
- doc_id
- doc_node_id
- code_project_id
- symbol_key
- resolved_fact_id nullable
- resolved_snapshot_id nullable
- relation_type
- source
- confidence
- resolution_status
- metadata_json
- status
- created_at
- updated_at
```

推荐关系类型：

```text
DESCRIBES
REQUIRES
IMPLEMENTS
VALIDATES
TESTS
DEPENDS_ON
```

解析状态：

```text
resolved
unresolved
stale
ambiguous
```

说明：

- `symbol_key` 是长期稳定关系。
- `resolved_fact_id` 是当前产品版本或当前分支快照下解析到的实际代码事实。
- 刷新图谱后，如果 `resolved_fact_id` 不再属于当前快照，必须按 `symbol_key` 重新解析。

## 5. Hash 计算规则

系统不存储源码，但 hash 必须基于源码内容计算。

```text
signature_hash = hash(名称 + 参数 + 返回值 + 修饰符 + 注解)
content_hash = hash(规范化后的代码内容)
structure_hash = hash(node_type + signature_hash + content_hash + sorted(child.structure_hash))
```

计算顺序：

```text
自底向上计算 hash
自顶向下判断复用
```

复用规则：

- 文件 `structure_hash` 一致时，文件下整棵子树复用。
- 类 `structure_hash` 一致时，类下方法整体复用。
- 方法或函数 `content_hash` 一致时，最小功能节点复用。
- hash 一致只复用元数据和图节点，不复用源码。

## 6. 业务操作逻辑

### 6.1 创建项目

命令示例：

```bash
neodev project create --name dsc-web-server --repo-url git@example.com:group/dsc-web-server.git
```

逻辑：

1. 创建或更新 `projects`。
2. 保存 `repo_url` 和本地 `repo_path`。
3. 不创建 `repo_id`。
4. 可选触发默认分支图谱刷新。
5. 图谱刷新完成后生成 `branch_snapshots`、`code_facts`、`branch_snapshot_facts`。

### 6.2 创建产品版本

命令示例：

```bash
neodev product version create --product dsc --name V2.0R26C01
```

逻辑：

1. 创建 `product_versions`。
2. 不自动绑定项目。
3. 不自动刷新图谱。

### 6.3 绑定项目分支到产品版本

命令示例：

```bash
neodev product version bind-project \
  --version-id 1 \
  --project-id 1 \
  --branch release/V2.0R26C01
```

逻辑：

1. 校验产品版本存在。
2. 校验项目存在。
3. 写入或更新 `product_version_branches`。
4. 检查 `project_id + branch_name` 是否已有 `completed` 快照。
5. 如果没有快照，返回提示，需要执行 `project refresh-graph`。
6. 不自动刷新其他项目。

### 6.4 刷新分支图谱

命令示例：

```bash
neodev project refresh-graph --project-id 1 --branch release/V2.0R26C01
```

逻辑：

1. 拉取项目仓库。
2. checkout 指定分支。
3. 获取 `head_commit`。
4. 扫描代码文件。
5. 解析 AST，生成文件、类、方法、函数等代码树。
6. 自底向上计算 `signature_hash`、`content_hash`、`structure_hash`。
7. 按 `fact_id` 查找 `code_facts`。
8. 命中则复用，未命中则新增。
9. 计算 `snapshot_hash`。
10. 如果最新快照的 `snapshot_hash` 相同，返回 `no_change`。
11. 如果不同，创建新的 `branch_snapshots`。
12. 批量写入 `branch_snapshot_facts`。
13. 投影当前快照相关节点和关系到 Neo4j。
14. 重建受影响的 `doc_code_links` 解析结果。

说明：

- 刷新是全分支刷新，不是 commit 增量同步。
- 全分支刷新不等于全量重建，复用由 hash 决定。
- 旧 `sync_commit_graph_for_version` 逻辑废弃。

### 6.5 重建文档到代码关系

触发时机：

- 刷新分支图谱后自动触发。
- 手动执行文档关系重建命令时触发。

逻辑：

1. 找到绑定了当前 `project_id + branch_name` 的产品版本。
2. 找到这些产品版本下 `code_project_id = project_id` 的 `doc_code_links`。
3. 检查 `resolved_fact_id` 是否仍在当前 `branch_snapshot_facts` 中。
4. 如果仍在，保持 `resolution_status = resolved`。
5. 如果不在，按 `symbol_key` 在当前快照可见 `code_facts` 中重新查找。
6. 找到唯一候选，更新 `resolved_fact_id`、`resolved_snapshot_id`，设置 `resolution_status = resolved`。
7. 找不到候选，设置 `resolution_status = unresolved`。
8. 找到多个候选，设置 `resolution_status = ambiguous`，等待人工确认。

### 6.6 查询产品版本功能节点

输入：

```text
product_version_id
```

逻辑：

1. 查询 `product_version_branches`。
2. 对每个 `project_id + branch_name` 找最新 `completed` 快照。
3. 读取 `branch_snapshot_facts`。
4. join `code_facts`。
5. 过滤 `node_type in Method, Function, Constructor, Class, Interface`。
6. 返回当前产品版本可见功能节点。

### 6.7 查询文档对应功能节点

输入：

```text
product_version_id + doc_id
```

逻辑：

1. 查询 `doc_code_links`。
2. 根据 `product_version_branches` 找目标项目在该产品版本下绑定的分支。
3. 获取该分支最新 `completed` 快照。
4. 优先校验 `resolved_fact_id` 是否仍属于该快照。
5. 如果有效，返回对应 `code_facts`。
6. 如果无效，按 `symbol_key` 即时解析并更新 `doc_code_links`。
7. 返回解析后的实际方法、函数、类或接口节点。

### 6.8 删除产品版本

逻辑：

1. 删除 `product_versions`。
2. 删除关联的 `product_version_branches`。
3. 不删除 `branch_snapshots`。
4. 不删除 `code_facts`。
5. 不删除仍可被其他产品版本复用的文档到代码关系。

### 6.9 删除项目

逻辑：

1. 删除 `projects`。
2. 级联删除项目相关 `branch_snapshots`、`branch_snapshot_facts`、`code_facts`。
3. 将相关 `doc_code_links` 置为失效或删除。
4. 清理或重建 Neo4j 投影。

### 6.10 垃圾回收

建议命令：

```bash
neodev graph gc
```

逻辑：

1. 找到没有任何 `branch_snapshot_facts` 引用的 `code_facts`。
2. 根据保留周期归档或删除。
3. 找到失效且长期未恢复的 `doc_code_links`。
4. 根据策略归档或保留人工处理。
5. 清理 Neo4j 中无事实源引用的投影节点。

## 7. Neo4j 投影规则

Neo4j 不作为唯一事实源。

投影节点：

```text
CodeFact
Document
```

投影关系：

```text
CONTAINS
DEFINES
CALLS
EXTENDS
IMPLEMENTS
IMPORTS
DOC_RELATES_TO_CODE
```

说明：

- Neo4j 节点不存 `branch_name`。
- Neo4j 节点不存源码。
- 查询前由 PG 算出 `visible_fact_ids`。
- Neo4j 查询使用 `fact_id in visible_fact_ids` 做版本范围过滤。

示例：

```cypher
MATCH (n:CodeFact)
WHERE n.fact_id IN $visible_fact_ids
RETURN n
```

## 8. CLI 调整

保留：

```text
project create
project show
project refresh-graph
product version create
product version bind-project
graph node/edge 手工管理命令
```

废弃或删除：

```text
project refresh-commit-graph
git post-push-refresh
sync-commits 驱动图谱更新的行为
项目级 version 作为图谱核心参数
```

`project refresh-graph` 必须支持：

```text
--project-id
--project-name
--branch
```

不再要求：

```text
--version-id
```

产品版本相关查询通过 `product_version_id` 解析绑定项目和分支。

## 9. 实施任务

### DM-01 重构数据库迁移

任务：

- 新增 `code_facts`。
- 新增 `branch_snapshot_facts`。
- 新增 `doc_code_links`。
- 重建或迁移 `branch_snapshots`。
- 废弃 `repo_id`。
- 废弃旧 `branch_snapshot_entries` 文件级结构。
- 废弃项目级 `versions` 在图谱核心链路中的作用。

验收：

- 新表能通过迁移创建。
- 唯一约束和索引完整。
- 旧数据可清空后重建。

### DM-02 重构代码事实生成

任务：

- 修改解析流水线，生成 `code_facts`。
- 使用 `project_id` 替代 `repo_id`。
- 生成 `symbol_key` 和 `fact_id`。
- 计算 `signature_hash`、`content_hash`、`structure_hash`。
- 保证不保存源码正文。

验收：

- 同一项目同一方法内容一致时复用同一 `fact_id`。
- 方法内容变化时生成新的 `fact_id`。
- `symbol_key` 在方法内容变化时保持稳定。

### DM-03 重构分支图谱刷新

任务：

- 删除 commit 增量同步路径。
- 将 `project refresh-graph` 改为分支全刷新。
- 使用 hash 复用已有 `code_facts`。
- 写入 `branch_snapshots` 和 `branch_snapshot_facts`。
- `snapshot_hash` 一致时返回 `no_change`。

验收：

- 刷新指定项目分支可生成方法级快照。
- 快照能直接查到当前分支可见方法和函数。
- 不依赖 `version_id`。

### DM-04 重构产品版本绑定

任务：

- `product_version_branches` 使用 `branch_name`。
- 一个产品版本下一个项目只能绑定一个分支。
- 绑定后检查是否存在分支快照。

验收：

- 产品版本可绑定多个项目分支。
- 缺少快照时给出明确提示。

### DM-05 实现文档到代码关系

任务：

- 新增 `doc_code_links` repository/service/CLI/API。
- 支持通过 `symbol_key` 创建文档到代码关系。
- 保存当前解析结果 `resolved_fact_id`。
- 支持 `resolved/unresolved/stale/ambiguous` 状态。

验收：

- 文档可以关联到项目下稳定代码符号。
- 产品版本查询时能解析到当前实际代码事实。

### DM-06 刷新后重建文档关系

任务：

- 分支刷新完成后查找受影响产品版本。
- 检查 `doc_code_links.resolved_fact_id` 是否仍在当前快照。
- 失效时按 `symbol_key` 自动重解析。
- 处理找不到和多候选情况。

验收：

- 方法内容变化后，文档关系能自动指向新 `fact_id`。
- 方法删除后，关系状态变为 `unresolved`。
- 多候选时状态变为 `ambiguous`。

### DM-07 重构查询服务

任务：

- 产品版本功能节点查询改为读取 `branch_snapshot_facts + code_facts`。
- 文档对应功能节点查询通过 `doc_code_links` 解析。
- Neo4j 查询由 PG 提供 `visible_fact_ids`。

验收：

- 可以查询某产品版本下所有可见方法、函数、类。
- 可以从文档查到当前产品版本下的实际代码节点。

### DM-08 重构 Neo4j 投影

任务：

- Neo4j 写入 `CodeFact` 节点。
- 不写 `branch_name`。
- 不写源码。
- 图关系由刷新时解析并投影。
- 支持从 PG 重建投影。

验收：

- Neo4j 节点可按 `fact_id` 查询。
- PG 清晰表达事实源。
- Neo4j 可删除后从 PG 重建。

### DM-09 清理旧代码

任务：

- 删除 `sync_commit_graph_for_version`。
- 删除 `git post-push-refresh`。
- 删除代码节点 AI/语义搜索路径。
- 删除 `repo_id` 依赖。
- 删除项目级 `versions` 在图谱刷新中的必填逻辑。

验收：

- 代码中不再要求 `--version-id` 执行分支图谱刷新。
- 图谱刷新不再依赖 commit 增量。
- 代码节点不再触发语义/AI 处理。

### DM-10 测试和远程验证

任务：

- 单元测试覆盖 hash 身份生成。
- 单元测试覆盖分支刷新和快照写入。
- 单元测试覆盖文档关系重建。
- 远程环境清空后使用当前项目仓库重建图谱。
- 验证 PG 结构、Neo4j 投影、产品版本查询和文档关系查询。

验收：

- 本地测试通过。
- 远程 PG 表结构符合本文档。
- 远程 Neo4j 不包含 `branch_name`、源码正文、AI/语义字段。
- 产品版本可以从快照直接查到方法/函数级节点。

## 10. 风险和约束

- 方法移动文件或重命名会改变 `symbol_key`，旧文档关系可能需要人工重绑。
- 同一个 `symbol_key` 在当前快照内匹配多个事实时，必须标记 `ambiguous`。
- 不存 `code_fact_edges` 会降低纯 PG 图遍历能力，但能显著简化事实源。
- Neo4j 投影失败不应破坏 PG 事实源。
- 刷新分支图谱必须保证 Git checkout 和扫描过程互斥，避免同一项目并发刷新造成工作树错乱。

## 11. 完成标准

- 数据模型不再使用 `repo_id`。
- 分支快照关联到最小功能单位。
- `project refresh-graph` 不再要求 `version_id`。
- 增量同步和 post-push 自动刷新被移除。
- 文档到代码关系使用 `symbol_key + resolved_fact_id`。
- 刷新图谱后能自动检测并重建失效文档关系。
- PG 可作为唯一事实源。
- Neo4j 可作为查询投影重建。

## 关联文档
- [[requirements/rd-knowledge-graph-mvp/01-master-prd|研发知识图谱中台 MVP 总 PRD]]
