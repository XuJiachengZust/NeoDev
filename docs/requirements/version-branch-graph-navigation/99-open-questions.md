---
doc_id: NEODEV-DOC-REQUIREMENTS-VERSION-BRANCH-GRAPH-NAVIGATION-OPEN-QUESTIONS
title: Version Branch Graph Navigation Open Questions
aliases:
  - Version Branch Graph Navigation Open Questions
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

# 开放问题

## 1. 已确认决策

| ID | 决策 | 日期 |
| --- | --- | --- |
| C-001 | 不新增主流程 CLI，优先复用 `product version show` 和现有 graph/doc 查询命令。 | 2026-05-07 |
| C-002 | `product version show` 只返回产品、版本、分支等基础定位信息，不返回代码图或文档图摘要。 | 2026-05-07 |
| C-003 | 代码图和文档图都直接绑定产品版本。 | 2026-05-07 |
| C-004 | 用户侧查询参数使用名称，不使用 ID。 | 2026-05-07 |
| C-005 | 名称需要唯一性校验，冲突时不能暗选。 | 2026-05-07 |
| C-006 | 文档节点和文档图以版本为归属，不以产品为唯一归属。 | 2026-05-07 |
| C-007 | 分支反查无命中时采用 Q-101 A：返回空 `resolved_versions[]` 且 `ok=true`。 | 2026-05-07 |
| C-008 | 历史代码图和文档图采用重建策略，重建后补齐名称化版本作用域字段。 | 2026-05-07 |
| C-009 | 一个文档不能被多个版本使用；文档使用 Git 管理，并通过 Git 分支/版本实现隔离。 | 2026-05-07 |

## 2. 已关闭问题

| ID | 问题 | 最终决策 | 状态 |
| --- | --- | --- | --- |
| Q-101 | 分支反查无命中时返回空 `resolved_versions[]` 还是 `not_found`？ | 返回空 `resolved_versions[]` 且 `ok=true`。 | closed |
| Q-102 | 历史代码图节点和文档图节点缺少名称化版本字段时如何处理？ | 重建历史图；重建前缺少名称化版本作用域的历史节点不作为有效版本图查询结果。 | closed |
| Q-103 | 同一文档是否可以被多个版本复用？ | 不可以。文档由 Git 管理并按版本隔离，同一文档来源不能跨多个版本绑定。 | closed |

## 相关文档

- [[01-master-prd|Version Branch Graph Navigation Master PRD]]
