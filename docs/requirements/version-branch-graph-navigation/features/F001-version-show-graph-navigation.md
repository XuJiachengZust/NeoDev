---
doc_id: NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-F001
title: F001 Version Show Graph Navigation PRD
aliases:
  - F001 Version Show Graph Navigation PRD
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
  - "[[requirements/version-branch-graph-navigation/features/F002-query-oriented-graph-node-fields|F002 Query Oriented Graph Node Fields PRD]]"
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-MASTER-PRD
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-F002
---

# F001 `product version show` 名称参数发现 PRD

## 1. 目标

`product version show` 是版本导航的轻量入口，只负责返回产品名称、版本名称、项目名称、分支名称和后续查询所需名称参数。它不读取、不聚合、不展示代码图或文档图内容。

## 2. 入口

| ID | CLI | 入参 | 输出 |
| --- | --- | --- | --- |
| EN-F001-01 | `product version show` | `--product-name --version-name` | `product/version/branches/query_params` |
| EN-F001-02 | `product version show` | `--project-name --branch-name`，可选 `--product-name` 缩小范围 | `project/branch_name/resolved_versions[]` |

不再作为用户侧查询入口：

- `--version-id`
- `--project-id`
- `product_version_id`
- `project_id`

## 3. 输出字段

| 字段 | 说明 | 必填 |
| --- | --- | --- |
| `product.name` | 产品名称 | 是 |
| `version.name` | 版本名称 | 是 |
| `branches[].project_name` | 绑定项目名称 | 是 |
| `branches[].branch_name` | 绑定分支名 | 是 |
| `query_params[]` | 后续代码图、文档图查询可直接使用的名称参数集合 | 是 |
| `resolved_versions[]` | 分支反查命中的版本列表 | 仅分支反查模式 |

`query_params[]` 结构：

```json
{
  "product_name": "NeoDev",
  "version_name": "v1.0",
  "project_name": "NeoDev",
  "branch_name": "main"
}
```

禁止输出字段：

- `code_graphs`
- `document_graph`
- `node_count`
- `edge_count`
- `graph_status`
- `documents_sample`

## 4. 名称唯一性校验

| ID | 规则 |
| --- | --- |
| BR-F001-01 | `product_name` 必须全局唯一。 |
| BR-F001-02 | `project_name` 必须全局唯一。 |
| BR-F001-03 | `version_name` 必须在同一 `product_name` 下唯一。 |
| BR-F001-04 | `branch_name` 必须在同一 `project_name` 下唯一。 |
| BR-F001-05 | `product_name + version_name + project_name` 下最多绑定一个 `branch_name`。 |

## 5. 业务规则

| ID | 规则 |
| --- | --- |
| BR-F001-06 | 不新增主流程 CLI，复用 `product version show`。 |
| BR-F001-07 | `product version show` 是只读命令，不触发图刷新、文档导入或 Neo4j 查询。 |
| BR-F001-08 | 版本定位模式补充名称化 `query_params[]`。 |
| BR-F001-09 | 分支反查模式返回所有命中的版本，不能暗选一个版本。 |
| BR-F001-10 | 图是否存在、图是否 ready、节点数量等由后续 graph/doc 查询返回。 |
| BR-F001-11 | 分支反查无命中时返回空 `resolved_versions[]` 且 `ok=true`，不返回 `not_found`。 |

## 6. 验收标准

| ID | Given | When | Then |
| --- | --- | --- | --- |
| AC-F001-01 | 已存在产品版本 | 执行 `product version show --product-name <name> --version-name <name> --json` | 返回产品名、版本名、分支名、`query_params`。 |
| AC-F001-02 | 已存在项目分支绑定 | 执行 `product version show --project-name <name> --branch-name <name> --json` | 返回 `resolved_versions[]`。 |
| AC-F001-03 | 同一分支绑定多个版本 | 执行分支反查 | 返回多个版本，不暗选。 |
| AC-F001-04 | 任意 show 调用 | 查看 JSON | 不存在 `code_graphs` 和 `document_graph`。 |
| AC-F001-05 | 输出包含 `query_params` | 调用后续图查询 | 参数均为名称字段。 |
| AC-F001-06 | 创建或改名造成名称冲突 | 执行创建或更新 | 返回 `name_conflict`。 |
| AC-F001-07 | 项目分支没有绑定任何版本 | 执行分支反查 | 返回 `resolved_versions: []` 且 `ok=true`。 |

## 7. 测试用例

| ID | 优先级 | 场景 | 断言 |
| --- | --- | --- | --- |
| TC-F001-01 | P0 | 产品名+版本名定位 | 输出包含 `product/version/branches/query_params`。 |
| TC-F001-02 | P0 | 项目名+分支名反查单命中 | 输出包含一个 `resolved_versions`。 |
| TC-F001-03 | P0 | 项目名+分支名反查多命中 | 输出包含多个 `resolved_versions`。 |
| TC-F001-04 | P0 | 输出瘦身 | 不输出图摘要字段。 |
| TC-F001-05 | P0 | 名称唯一性 | 重复产品名、项目名、同产品版本名返回冲突。 |
| TC-F001-06 | P1 | 分支无命中 | 返回空 `resolved_versions[]` 且 `ok=true`。 |

## 相关文档

- [[01-master-prd|Version Branch Graph Navigation Master PRD]]
- [[requirements/version-branch-graph-navigation/features/F002-query-oriented-graph-node-fields|F002 Query Oriented Graph Node Fields PRD]]
