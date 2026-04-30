---
doc_id: NEODEV-DOC-SUPERPOWERS-SPECS-2026-04-30-PROJECT-BRANCH-GRAPH-DESIGN
title: "NeoDev 项目分支图谱与产品版本绑定设计"
aliases:
  - "项目分支图谱设计"
  - "产品版本绑定分支图谱设计"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/spec
created: 2026-04-30
updated: 2026-04-30
doc_type: tech-design
product_key: NEODEV
status: active
---

# NeoDev 项目分支图谱与产品版本绑定设计

## 1. 背景与目标

NeoDev 的代码图谱存储从“PG 保存解析后的代码节点/边，再投影到 Neo4j”调整为“PG 只保存元数据和人工绑定关系，Neo4j 保存当前分支代码图”。

目标：

- 一个项目分支对应一张当前图谱。
- PostgreSQL 不再保存解析出来的代码节点、代码边、代码事实快照。
- Parser 只负责基础代码解析，输出内存图。
- Neo4j 保存可查询的代码图谱。
- 产品版本只绑定 `project_id + branch_name`，不复制图。
- 文档节点和代码节点的绑定关系保存到 PG，刷新分支图谱时按 active 绑定重建 Neo4j 关系。
- CLI 不兼容旧参数，删除 `--symbol-key` 等旧模型入口。

## 2. 总体模型

### 2.1 图谱边界

Neo4j 中显式创建项目和分支图边界：

```text
(:Project {project_id})
  -[:HAS_BRANCH_GRAPH {graph_id, project_id, branch_name, branch}]->
(:BranchGraph {graph_id, project_id, branch_name, branch, head_commit})
  -[:CONTAINS {graph_id, project_id, branch_name, branch}]->
(:Folder)
```

`Project` 和 `BranchGraph` 是图谱边界层：

- `Project` 表示代码项目。
- `BranchGraph` 表示某个项目分支的一张当前图。
- 顶层 `Folder` 从 `BranchGraph -[:CONTAINS]-> ...` 接入；`File/Class/Method` 等代码节点通过 Folder/File 内部关系进入图。
- 分支图刷新只替换对应 `BranchGraph` 下的代码图。

### 2.2 标签策略

不使用旧的 `GraphNode` 技术性公共标签：

```text
GraphNode
```

结构节点只使用结构标签，代码符号节点使用统一索引标签 `CodeNode` 加真实语义标签：

```text
(:Folder)
(:File)
(:CodeNode:Class)
(:CodeNode:Interface)
(:CodeNode:Enum)
(:CodeNode:Method)
(:CodeNode:Function)
(:CodeNode:Constructor)
(:CodeNode:Module)
(:CodeNode:Package)
```

原因：

- `GraphNode` 不再使用，避免多一层无业务含义的图节点抽象。
- `CodeNode` 只用于代码符号节点，不用于 `Folder`、`File` 等结构节点。
- `Folder/File` 保留为结构节点，用于表达仓库目录和文件层级。
- `CodeNode` 用于文档代码关联和通用代码符号查询。
- 真实类型标签仍然保留，用于表达语义并支撑关系写入时按端点真实标签匹配。
- Project/BranchGraph 表达图边界，`BranchGraph` 只直接关联顶层 `Folder`。

### 2.3 分支字段

所有分支图相关节点和关系都写入：

```text
project_id
branch_name
branch
graph_id
```

`branch_name` 是数据库绑定字段，`branch` 是图查询和展示友好的分支字段。两者当前值相同。

代码节点额外写入：

```text
id
node_id
fact_id
head_commit
label
```

## 3. PostgreSQL 数据模型

### 3.1 `branch_graphs`

保存项目分支当前图谱的元数据。

```text
branch_graphs
- id
- project_id
- branch_name
- head_commit
- graph_hash
- status
- node_count
- edge_count
- refreshed_at
- created_at
- updated_at
unique(project_id, branch_name)
```

语义：

- `id` 是分支图元数据 ID，同时作为 Neo4j `BranchGraph.graph_id`。
- `project_id + branch_name` 唯一定位当前分支图。
- `head_commit` 表示 Neo4j 当前图对应的 Git commit。
- `status` 可取 `running`、`ready`、`failed`。

### 3.2 `graph_refresh_runs`

保存每次刷新过程。

```text
graph_refresh_runs
- id
- graph_id
- project_id
- branch_name
- started_at
- finished_at
- status
- head_commit_before
- head_commit_after
- node_count
- edge_count
- error_message
- metadata_json
```

`metadata_json` 保存刷新阶段耗时和 Neo4j 写入结果。

### 3.3 `product_version_branches`

保存产品版本到项目分支的绑定关系。

```text
product_version_branches
- id
- product_version_id
- project_id
- branch_name
- created_at
- updated_at
unique(product_version_id, project_id, branch_name)
```

语义：

- 只保存绑定关系。
- 不复制代码图。
- 不创建版本专属图。
- 查询产品版本代码上下文时，通过绑定关系定位 `branch_graphs(project_id, branch_name)`。

### 3.4 `doc_code_links`

保存文档节点和代码节点的绑定关系。

```text
doc_code_links
- id
- product_version_id
- project_id
- branch_name
- doc_id
- doc_node_id
- relation_type
- code_locator_json
- code_locator_hash
- resolved_graph_id
- resolved_node_id
- resolution_status
- status
- created_at
- updated_at
- deleted_at
unique active(product_version_id, project_id, branch_name, doc_node_id, relation_type, code_locator_hash)
```

推荐 `code_locator_json` 优先保存 `code_node_id`：

```json
{
  "code_node_id": "Function:src/app.py:main",
  "file_path": "src/app.py",
  "qualified_name": "main",
  "node_type": "Function",
  "name": "main"
}
```

解绑不删除历史记录，只将 active 记录置为 inactive 并设置 `deleted_at`。

## 4. Neo4j 数据模型

### 4.1 Project

```text
(:Project {
  id: "project:1",
  project_id: 1,
  name: "project:1"
})
```

`Project` 可复用。刷新分支图不会删除 `Project`。

### 4.2 BranchGraph

```text
(:BranchGraph {
  graph_id: 3,
  project_id: 1,
  branch_name: "release/V2.0R26C01",
  branch: "release/V2.0R26C01",
  head_commit: "..."
})
```

`Project` 到 `BranchGraph`：

```text
(:Project)-[:HAS_BRANCH_GRAPH {
  graph_id,
  project_id,
  branch_name,
  branch
}]->(:BranchGraph)
```

### 4.3 代码节点

代码节点使用 scoped id，避免不同项目/分支冲突：

```text
project:{project_id}:branch:{branch_name}:node:{parser_node_id}
```

示例：

```text
(:File {
  id: "project:1:branch:release/V2.0R26C01:node:File:src/App.java",
  node_id: "File:src/App.java",
  fact_id: "File:src/App.java",
  project_id: 1,
  branch_name: "release/V2.0R26C01",
  branch: "release/V2.0R26C01",
  graph_id: 3,
  head_commit: "...",
  label: "File",
  filePath: "src/App.java",
  name: "App.java"
})
```

### 4.4 代码关系

代码关系直接连接真实标签节点，不加公共标签：

```text
(:Folder)-[:CONTAINS]->(:File)
(:File)-[:DEFINES]->(:Class)
(:File)-[:IMPORTS]->(:File)
(:Method)-[:CALLS]->(:Method)
```

关系属性：

```text
id
relationship_id
project_id
branch_name
branch
graph_id
confidence
reason
type
```

### 4.5 文档到代码关系

文档节点和代码节点关系：

```text
(:Document {doc_id})
  -[:LINKS_TO_CODE {
      id,
      project_id,
      branch_name,
      branch,
      graph_id,
      doc_node_id,
      code_node_id,
      relation_type,
      source,
      confidence
    }]->
(:CodeNode)
```

Neo4j 的 `LINKS_TO_CODE` 是 PG `doc_code_links` active 记录的投影。刷新分支图时会先删除该分支旧投影，再按 active 记录重建。

## 5. 分支图刷新流程

命令：

```bash
neodev project refresh-graph --project-id <id> --branch <branch> --json
```

内部逻辑：

1. 查询 project。
2. 解析 repo 路径或远程仓库 URL。
3. 如果是远程仓库，确保本地缓存仓库存在。
4. `git fetch`。
5. checkout 到目标分支。
6. 获取目标分支 `head_commit`。
7. 加载 Neo4j 配置。
8. 查询 `branch_graphs(project_id, branch_name)`。
9. 如果 PG 已 ready、head_commit 未变化，并且 Neo4j 存在 `Project -[:HAS_BRANCH_GRAPH]-> BranchGraph`，返回 `skipped_unchanged`。
10. upsert `branch_graphs` 为 `running`。
11. 创建 `graph_refresh_runs(status=running)`。
12. 执行 parser pipeline。
13. 删除当前分支旧图节点：
    ```cypher
    MATCH (n {project_id: $project_id, branch_name: $branch_name})
    WHERE NOT n:Project
    DETACH DELETE n
    ```
14. 删除当前分支旧文档代码投影：
    ```cypher
    MATCH (:Document)-[r:LINKS_TO_CODE {project_id: $project_id, branch_name: $branch_name}]->()
    DELETE r
    ```
15. MERGE `Project`。
16. MERGE `BranchGraph`。
17. MERGE `Project -[:HAS_BRANCH_GRAPH]-> BranchGraph`。
18. 批量写入结构节点和代码符号节点；代码符号节点使用 `CodeNode + 真实类型标签`。
19. 批量写入代码关系。
20. 建立 `BranchGraph -[:CONTAINS]-> 顶层 Folder`。
21. 查询 PG active `doc_code_links`，重建 `Document -[:LINKS_TO_CODE]-> CodeNode`。
22. 计算 `graph_hash`。
23. 更新 `branch_graphs(status=ready, head_commit, node_count, edge_count, refreshed_at)`。
24. 更新 `graph_refresh_runs(status=completed, metadata_json)`。
25. commit PG。
26. 恢复刷新前分支。

## 6. Parser Pipeline 性能设计

pipeline 输出内存图，不直接写 PG 或 Neo4j。

阶段：

```text
walk_repository_paths
process_structure
read_files
parse_files_ast
materialize_ast_to_graph
process_import_relationships
process_call_relationships
process_heritage_relationships
```

Import resolver 使用预构建索引：

```text
exact
exact_lower
suffix
suffix_lower
```

复杂度从：

```text
O(I * (F log F + P * E * F))
```

降为：

```text
O(F * D + I * P * E)
```

## 7. CLI 设计

### 7.1 `project refresh-graph`

职责：

- 重新构建 `project_id + branch_name` 对应的当前 Neo4j 代码图。
- 更新 `branch_graphs` 和 `graph_refresh_runs`。
- 重建 active 文档代码关系投影。

输出包含：

```text
project_id
branch
graph_id
run_id
head_commit
graph_action
node_count
edge_count
file_count
graph_hash
neo4j_write
timings
graph_errors
refresh_mode
```

### 7.2 `product version bind-branch`

职责：

- 保存产品版本到 `project_id + branch_name` 的绑定关系。
- 不复制图。
- 如果分支没有解析或图未 ready，则触发自动解析。

内部逻辑：

1. 解析 product。
2. 解析 product version。
3. 解析 project。
4. normalize branch name。
5. upsert `product_version_branches(product_version_id, project_id, branch_name)`。
6. 查询 `branch_graphs(project_id, branch_name)`。
7. 如果不存在、不是 ready、或 Neo4j 不存在对应 `BranchGraph`，调用 `project refresh-graph`。
8. 返回绑定结果和图状态。

### 7.3 `product version unbind-branch`

职责：

- 删除或停用产品版本到分支的绑定关系。
- 不删除 `branch_graphs`。
- 不删除 Neo4j 代码图。

### 7.4 `product version link-code`

职责：

- 在 PG 保存文档节点到代码节点的绑定关系。
- 可立即投影到 Neo4j。
- 刷新分支图时重建 active 绑定关系。
- 支持绑定和解绑。

绑定命令：

```bash
neodev product version link-code \
  --product-code <product> \
  --version-name <version> \
  --project-name <project> \
  --branch <branch> \
  --doc-id <doc_id> \
  --doc-node-id <doc_node_id> \
  --relation-type <relation_type> \
  --code-node-id <parser_node_id> \
  --json
```

解绑命令：

```bash
neodev product version link-code \
  --product-code <product> \
  --version-name <version> \
  --unlink \
  --link-id <link_id> \
  --json
```

不支持旧参数：

```text
--symbol-key
```

## 8. 数据初始化 SQL

数据库结构使用单一初始化 SQL：

```text
docker/init.sql
```

要求：

- 包含当前最小可运行 schema。
- 不保留旧 `code_facts`、`branch_snapshot_facts`、`graph_nodes`、`graph_edges` 等解析结果持久化表。
- 初始化脚本可用于清空环境后的重新部署。

## 9. Neo4j 查询约定

分支图是否存在：

```cypher
MATCH (:Project {project_id: $project_id})-[:HAS_BRANCH_GRAPH]->(g:BranchGraph {
  project_id: $project_id,
  branch_name: $branch_name
})
RETURN count(g) AS count
```

删除当前分支图：

```cypher
MATCH (n {project_id: $project_id, branch_name: $branch_name})
WHERE NOT n:Project
DETACH DELETE n
```

写节点：

```cypher
UNWIND $nodes AS row
MERGE (n:<Labels> {id: row.id})
SET n += row.props
```

其中 `Folder/File` 的 `<Labels>` 分别是 `Folder`、`File`；代码符号节点的 `<Labels>` 是 `CodeNode:<RealLabel>`。

写关系：

```cypher
UNWIND $rels AS rel
MATCH (source:<SourceRealLabel> {id: rel.source_id})
MATCH (target:<TargetRealLabel> {id: rel.target_id})
MERGE (source)-[r:<TYPE> {id: rel.id}]->(target)
SET r += rel.props
```

关系写入必须按端点真实标签分组后执行，不能使用无标签 `MATCH (source {id})`。`CodeNode` 作为通用索引标签保留，但核心代码关系仍用真实类型标签匹配，避免无标签全图扫描并保留语义查询能力。

文档代码关系：

```cypher
UNWIND $links AS link
MATCH (code:CodeNode {id: link.scoped_code_node_id})
MERGE (doc:Document {doc_id: link.doc_id})
MERGE (doc)-[r:LINKS_TO_CODE {id: link.id}]->(code)
SET r += link.props
```

## 10. 验收标准

- PG 不保存解析出来的代码节点和边。
- PG 保存 `branch_graphs`、`graph_refresh_runs`、`product_version_branches`、`doc_code_links`。
- Neo4j 不创建 `GraphNode`。
- Neo4j 创建 `CodeNode`，但只标记 `Class/Interface/Enum/Annotation/Method/Function/Constructor` 等代码符号节点。
- Neo4j 的 `Folder/File` 不带 `CodeNode` 标签。
- Neo4j 创建 `Project`。
- Neo4j 创建 `BranchGraph`。
- `Project -[:HAS_BRANCH_GRAPH]-> BranchGraph` 存在。
- `BranchGraph -[:CONTAINS]-> 顶层 Folder` 存在。
- `BranchGraph` 不直接关联 `File/Class/Method` 等非 Folder 代码节点。
- 所有代码节点包含 `branch_name` 和 `branch` 字段。
- `product version bind-branch` 只保存版本到 `project_id + branch_name` 的绑定关系，不复制图。
- 分支未解析时，绑定会触发自动解析。
- `product version link-code` 支持绑定和解绑。
- link-code 绑定记录保存在 PG。
- 刷新分支图后 active link-code 关系会重建到 Neo4j。
- `--symbol-key` 不再存在。
- import 解析使用预构建索引，避免每条 import 扫描全仓库文件。

## 11. 已确认的取舍

- 不做版本图复制，产品版本始终引用项目分支当前图。
- 不做 PG 代码事实存储，避免维护两套结构。
- 不使用 `GraphNode` 公共标签。
- 使用 `CodeNode` 作为代码符号节点的统一索引标签。
- 使用 `Project` 和 `BranchGraph` 作为 Neo4j 图边界。
- 保留 `Folder/File` 结构节点，因为它们是代码图语义的一部分。
