---
doc_id: NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-README
title: Version Branch Graph Navigation PRD Index
aliases:
  - Version Branch Graph Navigation PRD Index
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
  - "[[00-source-index|Version Branch Graph Navigation Source Index]]"
  - "[[01-master-prd|Version Branch Graph Navigation Master PRD]]"
  - "[[features/F001-version-show-graph-navigation|F001 Version Show Graph Navigation PRD]]"
  - "[[features/F002-query-oriented-graph-node-fields|F002 Query Oriented Graph Node Fields PRD]]"
  - "[[99-open-questions|Version Branch Graph Navigation Open Questions]]"
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-SOURCE-INDEX
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-MASTER-PRD
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-F001
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-F002
    - NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-OPEN-QUESTIONS
---

# Version Branch Graph Navigation PRD Index

## 1. 最终口径

本 PRD 细化最终目标：使用尽可能少的 CLI，从分支找到版本；`product version show` 只返回产品名称、版本名称、项目名称、分支名称等基础定位信息；后续使用这些名称参数直接找到代码图和文档图。

关键约束：

- 用户侧 CLI/API 查询参数使用名称，不使用 ID。
- 名称必须有唯一性校验，避免名称查询产生歧义。
- `product version show` 不返回代码图摘要或文档图摘要。
- 代码图、文档图、代码节点、文档节点都记录版本名称属性。
- 文档图和文档节点归属版本，不归属产品。

## 2. 文档清单

| 文件 | 说明 | 状态 |
| --- | --- | --- |
| `00-source-index.md` | 来源、代码事实和最终口径索引 | draft |
| `01-master-prd.md` | 总 PRD | draft |
| `features/F001-version-show-graph-navigation.md` | `product version show` 名称参数发现 PRD | draft |
| `features/F002-query-oriented-graph-node-fields.md` | 版本名称直绑图和图节点属性 PRD | draft |
| `99-open-questions.md` | 已确认决策和关闭问题记录 | draft |

## 3. 功能拆分

| 功能 | 名称 | 核心目标 | 优先级 |
| --- | --- | --- | --- |
| F001 | `product version show` 名称参数发现 | 返回产品、版本、项目、分支名称；支持按项目名称和分支名称反查版本 | P0 |
| F002 | 版本名称直绑图和节点属性 | 代码图、文档图和图节点写入名称化版本作用域，支持按名称直接查图 | P0 |

## 4. 评审摘要

| 项 | 结果 |
| --- | --- |
| 阻塞问题 | 0 |
| 非阻塞问题 | 0 |
| CLI 数量策略 | 不新增主流程 CLI；复用 `product version show` 和现有 graph/doc 查询命令 |
| 查询参数策略 | 外部查询参数使用 `product_name/version_name/project_name/branch_name` |
| 唯一性策略 | 产品名全局唯一；项目名全局唯一；版本名在产品内唯一；分支名在项目内唯一 |

## 相关文档

- [[00-source-index|Version Branch Graph Navigation Source Index]]
- [[01-master-prd|Version Branch Graph Navigation Master PRD]]
- [[features/F001-version-show-graph-navigation|F001 Version Show Graph Navigation PRD]]
- [[features/F002-query-oriented-graph-node-fields|F002 Query Oriented Graph Node Fields PRD]]
- [[99-open-questions|Version Branch Graph Navigation Open Questions]]
