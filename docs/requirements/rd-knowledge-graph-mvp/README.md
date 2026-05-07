---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-README
title: 研发知识中台 MVP 文档索引
aliases:
- 研发知识中台 MVP 文档索引
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
- '[[requirements/rd-knowledge-graph-mvp/01-master-prd|研发知识图谱中台 MVP 总 PRD]]'
---

# 研发知识中台 MVP 文档索引

这组文档描述一个以 `Product` 和 `ProductVersion` 为组织单元、以本地 `neodev` CLI 客户端为唯一执行入口、与官方插件和官方 skill 协同工作的研发知识中台 MVP。

产品最终形态是：开发者电脑只安装轻量 CLI 客户端、官方 skill 和官方插件；NeoDev 服务、数据库、图谱、分析执行和状态管理集中部署在统一远程环境。本地 CLI 只负责把命令、参数和本地项目路径上下文发送到远程 NeoDev 服务，所有事实读取、状态写入、图谱刷新和分析任务都由远程服务完成。

核心范围：

- 产品绑定多个代码仓库分支和一个文档仓库
- 文档变更登记为 `DocChange`
- 传入仓库地址后由远程 NeoDev 自动触发图谱构建，并支持产品版本范围语义检索
- 图谱链路查询、节点刷新、推送前校验和推送后刷新
- 插件 / skill 负责引导，本地 CLI 客户端负责调用远程 NeoDev 服务，远程服务负责执行和事实写入

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

- 对外执行接口统一为本地 `neodev` CLI 客户端
- 不再提供 `MCP`
- 产品默认与官方插件 / 官方 skill 配合使用
- 插件 / skill 负责引导和编排，本地 CLI 客户端调用统一远程 NeoDev 服务完成执行和事实写入
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

## 关联文档
- [[requirements/rd-knowledge-graph-mvp/01-master-prd|研发知识图谱中台 MVP 总 PRD]]
