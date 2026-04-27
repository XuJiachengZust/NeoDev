---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-README
title: "研发知识中台 MVP 文档索引"
aliases:
  - "研发知识中台 MVP 文档索引"
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
# 研发知识中台 MVP 文档索引

这组文档描述一个以 `Product` 和 `ProductVersion` 为组织单元、以 `CLI` 为唯一执行接口、与官方插件和官方 skill 协同工作的研发知识中台 MVP。

核心范围：

- 产品绑定多个代码仓库分支和一个文档仓库
- 文档变更登记为 `DocChange`
- 产品版本下的分支分析、AI 语义增强和语义检索
- 图谱链路查询、节点刷新、推送前校验和推送后刷新
- 插件 / skill 负责引导，CLI 负责执行和事实写入

## 文档索引

- [00-source-index.md](./00-source-index.md)
  需求来源和本地源码依据索引。
- [01-master-prd.md](./01-master-prd.md)
  总 PRD，定义核心对象、规则、能力边界和验收口径。
- [technical/README.md](./technical/README.md)
  技术实现类文档索引。
- [99-open-questions.md](./99-open-questions.md)
  当前开放问题及已确认结论。

## 子 PRD

- [features/F001-product-binding-and-docchange-registration.md](./features/F001-product-binding-and-docchange-registration.md)
  产品绑定、文档治理、文档扫描和 `DocChange` 登记。
- [features/F002-graph-query-and-change-context.md](./features/F002-graph-query-and-change-context.md)
  图谱查询、语义检索、节点刷新和链路获取。
- [features/F003-git-consistency-and-risk-control.md](./features/F003-git-consistency-and-risk-control.md)
  Git 一致性校验、危险提交登记与推送后刷新。

## 当前结论

- 对外执行接口统一为 `CLI`
- 不再提供 `MCP`
- 产品默认与官方插件 / 官方 skill 配合使用
- 插件 / skill 负责引导和编排，CLI 负责执行和事实写入
- 不做独立向量索引层
- 图数据库承载关系、节点、链路和 embedding
- 图数据库按仓库级事实图存储，多分支通过分支快照引用限定可见范围
- 轻量元数据库承载产品、版本、DocChange、分析任务、危险提交等元数据
- 允许牺牲部分存储空间，换取更稳定的数据结构、更清晰的审计记录和更低的实现复杂度
- 危险提交允许二次确认后放行，但必须登记并支持后续关闭

## 推荐阅读顺序

1. 阅读 [01-master-prd.md](./01-master-prd.md)
2. 阅读 [technical/README.md](./technical/README.md)
3. 阅读 3 份子 PRD
4. 阅读 [technical/04-implementation-checklist.md](./technical/04-implementation-checklist.md)
5. 阅读 [technical/05-development-task-list.md](./technical/05-development-task-list.md) 做开发排期和任务分配
