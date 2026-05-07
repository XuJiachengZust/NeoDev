---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-T008-T010-GRAPH-REFRESH-SEMANTIC-SEARCH-AND-CHAIN-QUERY-TASK-LIST
title: T008-T010 图谱查询、文档语义检索与链路查询任务清单
aliases:
- T008-T010 图谱查询、文档语义检索与链路查询任务清单
tags:
- neodev/docs
- neodev/tech-design
- neodev/requirements
created: 2026-04-27
updated: 2026-04-28
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
- '[[requirements/rd-knowledge-graph-mvp/01-master-prd|研发知识图谱中台 MVP 总 PRD]]'
---

# T008-T010 图谱查询、文档语义检索与链路查询任务清单

## 1. 目标

本清单合并细化以下三项任务：

- `T008 仓库结构图谱事实索引`
- `T009 产品版本下文档语义检索`
- `T010 图谱上下文与链路查询 CLI`

重点解决的问题：

- 代码图谱只保存仓库级结构事实，不再生成代码节点 AI 摘要、embedding 或语义状态。
- `graph semantic-search` 只检索产品版本作用域内的文档分块。
- `graph impact`、`graph entity-context` 和 `graph get-chain` 输出结构化图谱事实，插件 / skill 不直接访问图数据库。
- 分支查询通过 `branch_snapshot` 限定当前可见节点，再进入仓库事实图遍历。

## 2. 现状基础

当前实现应复用以下能力：

- `src/service/services/graph_query_service.py`
- `src/service/services/node_service.py`
- `src/service/services/doc_semantic_search_service.py`
- `src/service/repositories/document_chunk_repository.py`
- `src/service/services/llm_client.py`

已删除或不再作为代码图谱主链路使用的能力：

- 代码节点 AI 预处理
- 代码节点结构化描述生成
- 代码节点 embedding 写回
- `graph refresh-nodes`

## 3. 改造原则

- 图查询能力最终通过 CLI 输出结构化结果，不直接暴露内部 Cypher 给插件 / skill。
- 文档语义检索必须受 `ProductVersion` 约束。
- 代码节点不参与语义检索；代码图谱查询只返回文件、符号、关系、提交和分支快照事实。
- 推送后的图谱更新由 `project refresh-commit-graph` 承接；提交过大或无法定位时才使用 `project refresh-graph` 兜底。
- 分支级刷新必须保留既有文档节点与代码节点关系。

## 4. 标准能力面

这一组任务最终对外收口为以下 CLI：

- `graph impact`
- `graph entity-context`
- `graph semantic-search`
- `graph get-chain`
- `graph node list`
- `graph edge list`
- `project refresh-commit-graph`
- `project refresh-graph`

## 5. 专项任务

### GQ-01 建立统一图谱查询服务

目标：
统一影响分析、实体上下文、链路查询和分支快照裁剪逻辑。

建议源码落点：

- `src/service/services/graph_query_service.py`
- `src/service/services/node_service.py`
- `src/service/cli/commands/graph.py`

验收口径：

- `graph impact` 能按 `DocChange` 输出影响范围。
- `graph entity-context` 能按项目、版本、分支和实体返回上下文。
- `graph get-chain` 能按节点、文件、符号或提交返回链路。
- 查询结果不包含代码节点语义字段。

### GQ-02 文档语义检索服务

目标：
把语义检索限定在文档分块，不触达代码节点。

建议源码落点：

- `src/service/services/graph_semantic_search_service.py`
- `src/service/services/doc_semantic_search_service.py`
- `src/service/repositories/document_chunk_repository.py`

验收口径：

- `graph semantic-search` 返回文档分块结果。
- 返回字段包含 `document_id`、`doc_id`、`chunk_id`、`heading_path`、`snippet`、`score` 和 `semantic_status`。
- 返回字段不包含代码节点 `entity_id`、`entity_type` 或代码 `file_path`。
- embedding 不可用时返回明确降级状态，不影响代码图谱查询。

### GQ-03 提交级图谱刷新入口

目标：
把推送后的默认刷新收口到提交级入口，避免默认整图刷新。

建议源码落点：

- `src/service/services/sync_service.py`
- `src/service/services/project_service.py`
- `src/service/cli/commands/project.py`

验收口径：

- `project refresh-commit-graph` 只刷新当前提交对应的节点和关系。
- 当提交内容过多或提交无法定位时，返回分支级兜底刷新结果。
- `project refresh-graph` 重新拉取项目分支并刷新整图结构事实。
- 兜底刷新不删除既有文档节点与代码节点关系。

### GQ-04 CLI 与服务职责映射

对应关系：

- `graph impact` -> `graph_query_service`
- `graph entity-context` -> `graph_query_service`
- `graph get-chain` -> `graph_query_service`
- `graph semantic-search` -> `doc_semantic_search_service`
- `graph node/edge/type` -> `graph_management_service`
- `project refresh-commit-graph` -> `sync_service.sync_commit_graph_for_version`
- `project refresh-graph` -> `sync_service.sync_commits_for_version`

验收口径：

- 每个命令都有唯一主服务。
- 不形成多入口重复实现。
- 节点类型和关系类型只允许来自项目内登记类型。
- 关系允许跨项目，但关系类型所有者必须是其中一个端点项目。

## 6. 建议执行顺序

1. 收口代码节点 AI 和语义刷新能力。
2. 建立文档分块语义检索服务。
3. 建立图谱查询服务边界。
4. 建立提交级图谱刷新入口。
5. 建立手工节点、关系和类型管理 CLI。
6. 补齐 CLI 契约、插件指引和测试。

## 7. 关键结论

- 代码图谱是结构事实图，不是语义向量索引。
- 文档语义检索保留，但只面向文档分块。
- `ProductVersion` 是文档语义检索和图谱链路查询的正式边界。
- `branch_snapshot` 是多分支查询的可见性边界。
- `project refresh-commit-graph` 是推送后的默认刷新入口。

## 关联文档
- [[requirements/rd-knowledge-graph-mvp/01-master-prd|研发知识图谱中台 MVP 总 PRD]]
