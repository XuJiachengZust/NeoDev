---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-README
title: "技术设计索引"
aliases:
  - "技术设计索引"
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
# 技术设计索引

这个目录存放研发知识中台 MVP 的技术实现类文档，和总 PRD、子 PRD 分开管理。

当前内容：

- [02-plugin-skill-guidance.md](./02-plugin-skill-guidance.md)
  插件 / skill 与 CLI 的职责边界和交互规范。
- [03-cli-contract.md](./03-cli-contract.md)
  CLI 命令契约、输出协议、错误码和版本检查策略。
- [04-implementation-checklist.md](./04-implementation-checklist.md)
  技术实施清单和阶段化交付顺序。
- [05-development-task-list.md](./05-development-task-list.md)
  结合源码拆分的开发任务列表。
- [06-graph-storage-structure.md](./06-graph-storage-structure.md)
  仓库级事实图与分支快照引用的存储结构设计，含 Mermaid 图示，重点解决同仓库多分支重复存图问题。
- [T002-data-model-refactor-task-list.md](./T002-data-model-refactor-task-list.md)
  数据模型和底层结构改造专项任务列表。
- [T006-branch-analysis-orchestration-task-list.md](./T006-branch-analysis-orchestration-task-list.md)
  分支分析编排、状态模型、复用策略和兼容改造专项任务列表。
- [T011-git-consistency-and-post-push-refresh-task-list.md](./T011-git-consistency-and-post-push-refresh-task-list.md)
  Git 校验、危险提交、推送后节点刷新与链路更新专项任务列表。
- [T008-T010-graph-refresh-semantic-search-and-chain-query-task-list.md](./T008-T010-graph-refresh-semantic-search-and-chain-query-task-list.md)
  图谱节点刷新、AI 语义增强、产品版本语义检索和链路查询专项任务列表。
