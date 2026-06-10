---
doc_id: NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-SOURCE-INDEX
title: Version Branch Graph Navigation Source Index
aliases:
  - Version Branch Graph Navigation Source Index
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
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-MASTER-PRD
---

# 来源索引

## 1. 用户输入

| ID        | 来源       | 内容                                                                                    | 结论                                                       |
| --------- | -------- | ------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| SRC-U-001 | 用户原始需求   | 支持使用 CLI，从分支找到版本，可以从版本直接找到代码图和文档图。                                                    | 需要分支反查版本，以及版本到图的直接定位能力。                                  |
| SRC-U-002 | 用户约束     | CLI 数量需要尽可能精简，优先看能不能改之前已有的。                                                           | 不新增主流程 CLI，优先复用 `product version show` 和现有 graph/doc 命令。 |
| SRC-U-003 | 用户数据结构要求 | 数据结构需要适合查询，询问是否需要在图节点中加字段。                                                            | 图节点需要标准版本作用域字段。                                          |
| SRC-U-004 | 用户修正     | 文档节点应该和版本绑定，而不是产品。                                                                    | 文档图和文档节点归属版本。                                            |
| SRC-U-005 | 用户最终目标   | `product version show` 只要返回版本、分支、产品名称等信息；后续用这些参数直接找到代码图和文档图；文档图和代码图直接绑定版本；图节点有属性记录版本。 | show 只做参数发现；图与节点直接记录版本作用域。                               |
| SRC-U-006 | 用户最终补充   | 现在都是以 ID 为参数查询，后续都应该是名称，名称需要做唯一性校验。                                                   | 外部查询参数必须改为名称，并定义唯一性约束。                                   |
| SRC-U-007 | 用户开放问题回复 | Q1 选择 A；Q2 重建历史图；Q3 一个文档不能被多个版本使用，文档也用 Git 管理，版本隔离。                                   | 开放问题全部关闭；历史图通过重建补齐；文档按 Git 分支/版本隔离，不跨版本复用。               |

## 2. 既有文档事实

| ID | 文件 | 事实 | 影响 |
| --- | --- | --- | --- |
| SRC-D-001 | `docs/requirements/rd-knowledge-graph-mvp/technical/03-cli-contract.md` | 已有 `product version show`、`graph entity-context`、`graph get-chain` 等 CLI 边界。 | 本需求优先扩展既有命令，不新增主流程 CLI。 |
| SRC-D-002 | `docs/requirements/rd-knowledge-graph-mvp/features/F001-product-binding-and-docchange-registration.md` | 已定义产品、版本、分支绑定和文档变更登记能力。 | 版本分支绑定是分支反查版本的事实来源。 |
| SRC-D-003 | `docs/requirements/rd-knowledge-graph-mvp/features/F002-graph-query-and-change-context.md` | 已定义图查询和变更上下文能力。 | 后续图查询不应塞进 `product version show`。 |

## 3. 代码事实

| ID | 文件 | 事实 | 差距 |
| --- | --- | --- | --- |
| SRC-C-001 | `src/service/cli/commands/product.py` | 现有 `product version show` 返回 `product/version/branches`。 | 可作为名称参数发现入口。 |
| SRC-C-002 | `src/service/repositories/product_version_repository.py` | 版本分支绑定在 `product_version_branches`，现有唯一约束偏向 ID 组合。 | 需要补名称唯一性校验和名称反查能力。 |
| SRC-C-003 | `src/service/services/branch_graph_neo4j_service.py` | 当前代码图节点写入 `project_id/branch_name/graph_id/head_commit` 等属性。 | 需要新增 `product_name/version_name/project_name` 等名称化版本作用域字段。 |
| SRC-C-004 | `src/service/services/doc_graph_service.py` | 当前文档节点含 `product_id/document_id/doc_binding_id` 等字段，且存在项目到文档关系。 | 需要从产品级文档归属改为版本级文档归属，节点写入名称化版本作用域字段。 |
| SRC-C-005 | `src/service/cli/commands/graph.py` | 现有图查询命令已承担实体上下文和链路查询。 | 应增强为可使用名称参数直接定位代码图、文档图。 |

## 4. 测试线索

| ID | 文件 | 覆盖方向 |
| --- | --- | --- |
| SRC-T-001 | `tests/test_product_cli.py` | 名称定位、分支反查版本、输出不含图摘要。 |
| SRC-T-002 | `tests/test_graph_cli.py`、`tests/test_graph_query_service_unit.py` | 名称参数驱动的代码图、文档图查询。 |
| SRC-T-003 | `tests/test_branch_graph_neo4j_service.py`、`tests/test_doc_graph_service.py` | 图节点写入名称化版本作用域字段。 |

## 相关文档

- [[01-master-prd|Version Branch Graph Navigation Master PRD]]
