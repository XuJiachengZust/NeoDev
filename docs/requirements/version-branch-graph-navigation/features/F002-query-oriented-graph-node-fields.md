---
doc_id: NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-F002
title: F002 Query Oriented Graph Node Fields PRD
aliases:
  - F002 Query Oriented Graph Node Fields PRD
tags:
  - neodev/docs
  - neodev/requirements
  - neodev/requirements/version-branch-graph-navigation
  - neosuperpower/generated
created: 2026-05-07
updated: 2026-05-07
doc_type: prd
product_key: NEODEV
status: draft
related:
  - "[[01-master-prd|Version Branch Graph Navigation Master PRD]]"
  - "[[requirements/version-branch-graph-navigation/features/F001-version-show-graph-navigation|F001 Version Show Graph Navigation PRD]]"
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-MASTER-PRD
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-F001
---

# F002 版本名称直绑图和图节点属性 PRD

## 1. 目标

代码图和文档图都必须直接绑定产品版本。用户侧查询使用名称参数，因此图、节点和关键关系必须写入名称化版本作用域字段，使后续查询可以从 `product_name + version_name` 直接进入代码图或文档图。

ID 可作为内部追踪字段保留，但不能成为用户侧唯一查询入口。

## 2. 版本作用域字段

| 对象 | 必填名称字段 | 可选内部字段 |
| --- | --- | --- |
| CodeGraph | `product_name/version_name/project_name/branch_name` | `product_version_id/project_id/graph_id` |
| DocumentGraph | `product_name/version_name` | `product_version_id/doc_binding_id` |
| CodeNode | `product_name/version_name/project_name/branch_name` | `product_version_id/project_id/node_id/fact_id` |
| DocumentNode | `product_name/version_name` | `product_version_id/document_id/doc_binding_id/doc_id` |
| GraphRelationship | `product_name/version_name` | relation ID |

## 3. 代码图字段

| 字段 | 对象 | 说明 |
| --- | --- | --- |
| `product_name` | CodeGraph/CodeNode/GraphRelationship | 产品名称，必填且全局唯一。 |
| `version_name` | CodeGraph/CodeNode/GraphRelationship | 版本名称，必填，与 `product_name` 组成唯一版本。 |
| `project_name` | CodeGraph/CodeNode | 项目名称，必填且全局唯一。 |
| `branch_name` | CodeGraph/CodeNode | 分支名，必填，与 `project_name` 组成唯一分支。 |
| `head_commit` | CodeGraph/CodeNode | 图对应提交，建议保留。 |
| `file_path` | CodeNode | 文件路径查询字段。 |
| `name` / `qualified_name` | CodeNode | 符号查询字段。 |

## 4. 文档图字段

| 字段 | 对象 | 说明 |
| --- | --- | --- |
| `product_name` | DocumentGraph/DocumentNode/GraphRelationship | 产品名称，必填。 |
| `version_name` | DocumentGraph/DocumentNode/GraphRelationship | 版本名称，必填。 |
| `doc_name` | DocumentNode | 文档名称，建议在版本内唯一。 |
| `relative_path` | DocumentNode | 文档路径，建议在版本内唯一。 |
| `doc_type` | DocumentNode | 文档类型。 |
| `content_hash` | DocumentNode | 内容哈希。 |
| `product_id` | DocumentNode | 可选派生展示字段，不能作为查询归属。 |

## 5. 查询规则

| ID | 规则 |
| --- | --- |
| BR-F002-01 | 后续代码图查询使用 F001 输出的 `product_name/version_name/project_name/branch_name`。 |
| BR-F002-02 | 后续文档图查询使用 `product_name/version_name`。 |
| BR-F002-03 | 图节点缺少名称化版本作用域字段时，不应作为有效版本图节点返回。 |
| BR-F002-04 | 名称查询命中多个实体时必须返回 `ambiguous_name`，不能暗选。 |
| BR-F002-05 | 旧的产品级代码图和文档图必须重建，重建后写入名称化版本作用域字段。 |
| BR-F002-06 | 文档由 Git 管理并按版本隔离，一个文档不能被多个版本使用。 |
| BR-F002-07 | 同一文档尝试绑定到多个版本时必须返回冲突错误。 |

## 6. 验收标准

| ID | Given | When | Then |
| --- | --- | --- | --- |
| AC-F002-01 | 刷新某版本绑定分支的代码图 | 检查 CodeGraph | CodeGraph 含 `product_name/version_name/project_name/branch_name`。 |
| AC-F002-02 | 刷新某版本绑定分支的代码图 | 检查 CodeNode | CodeNode 含 `product_name/version_name/project_name/branch_name`。 |
| AC-F002-03 | 导入某版本作用域文档 | 检查 DocumentGraph | DocumentGraph 含 `product_name/version_name`。 |
| AC-F002-04 | 导入某版本作用域文档 | 检查 DocumentNode | DocumentNode 含 `product_name/version_name`，且不只依赖 `product_id`。 |
| AC-F002-05 | 使用 F001 输出的名称化 `query_params` | 调用后续图查询 | 能直接定位该版本的代码图和文档图。 |
| AC-F002-06 | 同一产品两个版本有不同文档集合 | 分别按版本名称查询 | 结果按 `product_name/version_name` 隔离。 |
| AC-F002-07 | 历史图缺少名称化版本作用域字段 | 执行历史图重建 | 重建后的图、节点和关系包含名称化版本作用域字段。 |
| AC-F002-08 | 同一文档已绑定版本 A | 尝试绑定版本 B | 返回文档跨版本复用冲突。 |

## 7. 测试用例

| ID | 优先级 | 场景 | 断言 |
| --- | --- | --- | --- |
| TC-F002-01 | P0 | 代码图刷新 | CodeGraph 和 CodeNode 都写入名称化版本作用域。 |
| TC-F002-02 | P0 | 文档导入 | DocumentGraph 和 DocumentNode 都写入名称化版本作用域。 |
| TC-F002-03 | P0 | 版本代码图查询 | 使用 `product_name/version_name/project_name/branch_name` 命中正确代码图。 |
| TC-F002-04 | P0 | 版本文档图查询 | 使用 `product_name/version_name` 命中正确文档图。 |
| TC-F002-05 | P1 | 历史图重建 | 重建后节点包含名称化版本作用域字段。 |
| TC-F002-06 | P0 | 文档跨版本复用 | 同一 Git 文档来源不能绑定到多个版本。 |

## 8. 实现影响

- `branch_graph_neo4j_service.py` 需要在代码图投影时获取并写入 `product_name/version_name/project_name/branch_name`。
- `doc_graph_service.py` 需要从产品级归属调整为版本级归属，并写入 `product_name/version_name`。
- 历史代码图和文档图需要重建，避免缺名称化版本作用域的节点参与新查询。
- 文档绑定需要校验 Git 文档来源和版本作用域，禁止同一文档跨多个版本复用。
- graph 查询服务需要接受并优先使用名称参数过滤。
- 需要为 Neo4j 的 `product_name/version_name/project_name/branch_name` 建立适合查询的索引。
- repository 层需要补产品名、项目名、产品内版本名的唯一性校验。

## 相关文档

- [[01-master-prd|Version Branch Graph Navigation Master PRD]]
- [[requirements/version-branch-graph-navigation/features/F001-version-show-graph-navigation|F001 Version Show Graph Navigation PRD]]
