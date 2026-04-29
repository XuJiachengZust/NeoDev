# 手工图与事实图统一设计

## 背景

NeoDev 当前存在两条图写入路径：

- 扫描链路写入 `code_facts`、`branch_snapshot_facts`，并同步 Neo4j 的 `GraphNode` / `CodeFact` 节点。
- 手工图命令写入 `graph_node_types`、`graph_relation_types`、`graph_nodes`、`graph_edges`。

`neodev graph node/edge/type ...` 这组命令不能再表现为另一套独立图。手工创建的节点和边，最终必须进入和扫描产物一致的分支可见事实图。查询命令不应该需要区分节点来自扫描还是手工录入。

## 设计决定

手工图写入直接修改目标项目分支的当前 latest completed snapshot。

手工节点和边写入后，按普通事实图处理：

- 手工节点写入 `code_facts`。
- 手工节点的快照归属写入目标 latest completed snapshot 的 `branch_snapshot_facts`。
- 手工节点同步到 Neo4j，使用扫描节点同样的通用标签。
- 手工边写入后，也进入同一套可查询图结构。
- 来源差异只通过元数据和操作日志记录，不影响查询语义。

当分支重新扫描时，扫描链路先清理该 `project_id + branch_name` 下之前的分支图数据，然后基于本次扫描结果重新创建 snapshot 和事实图。扫描流程不会继承之前的手工补丁。因此，如果手工节点或边没有被新的扫描结果重新产生，它们会从该分支最新查询中消失。操作日志继续保留用于审计。

## CLI 范围

会影响事实图的手工命令必须带分支上下文：

- `graph node add/update/delete`
- `graph edge add/update/delete`

定位方式遵循现有项目和产品版本命令风格：

- `--project-id` 或 `--project-name`
- `--branch`
- 可选支持 `--product-version-id`，或 `--product-code` + `--version-name`

服务层解析目标范围：

```text
project_id + branch_name -> latest completed branch_snapshot
```

如果目标分支没有 completed snapshot，命令返回明确的 `invalid_scope` 类错误。

类型管理命令仍然是项目级元数据操作：

- `graph type node add/list/archive`
- `graph type edge add/list/archive`

类型管理命令本身不修改快照。

## 数据模型

### 现有手工表

现有 `graph_*` 表继续保留，作为手工管理和审计友好的源记录：

- `graph_node_types`
- `graph_relation_types`
- `graph_nodes`
- `graph_edges`

这些表继续保存标签、类型 key、展示名称、自定义属性和状态。

### 事实表

手工节点写入时，同时 upsert `code_facts`。

推荐的手工节点事实字段：

```text
fact_id        = 基于 graph node id 生成的稳定手工 fact id
symbol_key     = 基于 project/type/name 或 node id 生成的稳定 symbol key
node_type      = 现有事实查询支持的节点类型
file_path      = null 或合成的手工路径
qualified_name = 手工 qualified name
name           = 展示名称
metadata_json  = source、manual_node_id、type_key、properties、operation_id
status         = active 或 archived
```

当前 `code_facts.node_type` 有类似枚举的 check 约束。第一版实现不建议直接放开 schema 风险，而是把手工图类型映射到现有支持的事实节点类型，并把原始图类型保存在 `metadata_json.type_key`。

`branch_snapshot_facts` 直接修改目标 latest completed snapshot。新增或更新时加入 fact id。删除或归档时，按照现有状态语义移除可见性或归档事实；最新快照查询不能再看到被删除的手工事实。

分支重新扫描前，服务必须先清理该分支旧图数据：

- 删除或归档该 `project_id + branch_name` 对应的旧 `branch_snapshots`。
- 删除旧 snapshot 下的 `branch_snapshot_facts`。
- 清理该分支旧 snapshot 产生的 Neo4j 可见图数据，避免旧手工节点或旧扫描节点继续参与查询。
- 对不再被任何 snapshot 引用的 `code_facts`，可以在清理流程中归档或交给后续 GC 处理。
- `graph_operation_logs` 不参与清理，作为审计记录保留。

### 操作日志

新增手工图操作日志：

```text
graph_operation_logs
- id
- project_id
- branch_name
- snapshot_id
- object_kind
- object_id
- operation
- before_json
- after_json
- actor
- source
- created_at
```

操作日志是手工变更与扫描变更的持久区别。查询行为不能依赖操作日志。

## Neo4j 行为

手工节点同步为普通可查询图节点：

```text
(:GraphNode:CodeFact { project_id, fact_id, id, name, ... })
```

手工相关信息作为属性保存，不作为核心遍历必须依赖的标签：

```text
source = "manual"
manual_node_id = ...
type_key = ...
```

手工边同步为 `:GraphNode` 端点之间的 Neo4j 关系。关系类型 key 在进入 Cypher 关系类型前必须校验或规范化。原始 type key 保存在关系属性里。

遍历查询继续从 PG 快照归属推导分支可见性。分支重新扫描时先清理旧分支数据，再创建新的 latest snapshot；旧手工事实不再参与最新分支遍历。

## 错误处理

手工事实写入需要事务化：

1. 校验 project、branch、snapshot、节点类型和关系类型。
2. 写入或更新 `graph_*` 管理行。
3. upsert 或归档事实表数据。
4. 写入操作日志。
5. 提交 PG 事务。
6. 同步 Neo4j。

如果 PG 写入失败，不执行 Neo4j 同步。

如果 PG 已提交但 Neo4j 同步失败，命令返回失败，并包含已提交的 operation id 和足够的重试上下文。PG 操作日志仍是恢复时的事实来源。

## 测试

需要补充有针对性的测试：

- `graph node add` 会创建或更新 `graph_nodes`、`code_facts`、`branch_snapshot_facts` 和操作日志。
- `graph node delete/archive` 会移除 latest snapshot 可见性。
- 分支重新扫描会创建新 snapshot，并且不会继承手工 snapshot membership。
- `graph entity-context` 和 `graph get-chain` 只能在 fact id 属于 latest snapshot 时看到手工节点。
- 手工 type key 即使映射到现有 `code_facts.node_type`，也会保存在 metadata。
- PG 事务回滚能避免手工事实部分写入。

## 不在本次范围

- 重新扫描后仍永久保留的手工 overlay。
- 手工图节点的独立查询语义。
- 手工图编辑 UI。
- 完整的历史差异可视化。

## 自检

本文档没有占位章节。分支覆盖语义已经明确：手工写入修改当前 latest completed snapshot；重新扫描会先清理该分支旧图数据，再基于扫描结果创建新的 latest snapshot，不继承手工新增内容。手工节点和扫描节点在查询上等价，来源只通过 metadata 和操作日志保留。
