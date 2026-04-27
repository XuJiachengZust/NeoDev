---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-99-OPEN-QUESTIONS
title: "开放问题"
aliases:
  - "开放问题"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/requirements
created: 2026-04-27
updated: 2026-04-27
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
  - "[[01-master-prd]]"
---
# 开放问题

当前这版 MVP 的开放问题已经全部收敛完成。

已关闭：

- `Q-205 CLI 输出版本化`
  结论：不做 `schema_version`。CLI 与插件 / skill 采用强一致版本策略，通过 `cli version-check` 和自动更新保持兼容。

- `Q-206 插件集成形态`
  结论：MVP 需要交付官方插件和官方 skill，而且不是参考实现，而是完整可用实现。

- `Q-204 AI 能力边界`
  结论：平台只负责节点级 AI 描述刷新、向量化、语义检索、影响范围与链路事实输出；插件 / skill 负责基于这些事实生成方案与执行引导；MVP 不做平台侧自主规划和自动改代码。

- `Q-202 向量与索引存储`
  结论：MVP 不做独立向量索引层，只增加一个轻量元数据库。图数据库承载代码/文档关系、节点、链路和 embedding；轻量元数据库承载产品、版本、DocChange、BranchAnalysisTask、DangerousCommitRecord、版本检查状态等必要元数据。

- `Q-201 文档治理`
  结论：MVP 采用轻治理，不做重审批。治理范围包括固定目录校验、front matter 必填字段校验、文档类型校验、`relations.target` 校验；校验失败时不登记 `DocChange`，但保留错误记录。

- `Q-203 风险处理策略`
  结论：危险提交允许二次确认后放行，但必须进入待处理清单；CLI 需要提供查询和关闭能力，并记录 `resolved_by`、`resolved_at`；MVP 不做多级审批、自动升级和定时催办。

当前无未决开放问题。
