---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-00-SOURCE-INDEX
title: 研发知识图谱中台 MVP 来源索引
aliases:
- 研发知识图谱中台 MVP 来源索引
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

# 研发知识图谱中台 MVP 来源索引

## 1. 用户确认来源

| ID | 类型 | 来源摘要 | 关联内容 |
| --- | --- | --- | --- |
| SRC-U-001 | 对话确认 | 产品是按业务组织的知识容器，一个产品绑定多个项目仓库的指定分支 | Product, CodeBinding, ProductVersion |
| SRC-U-002 | 对话确认 | 文档独立于代码仓库，单独存放在一个文档 Git 仓库中 | DocBinding, Document |
| SRC-U-003 | 对话确认 | 一期不做 UI，对外统一通过 CLI 提供能力 | CLI 能力面 |
| SRC-U-004 | 对话确认 | 文档提交生成 `DocChange ID`，默认进入 `pending_implementation` | DocChange |
| SRC-U-005 | 对话确认 | 代码提交必须使用 trailer `DocChange-ID: <doc_change_id>` | Git 一致性 |
| SRC-U-006 | 对话确认 | `implemented` 只能人工确认，提交校验通过后先进入 `in_implementation` | DocChange 状态机 |
| SRC-U-007 | 对话确认 | 危险提交默认二次确认后放行，并记录解决人和时间 | DangerousCommitRecord |
| SRC-U-008 | 对话确认 | 文档目录固定为 `prd/`、`prototype/`、`tech-design/` | 文档仓库结构 |
| SRC-U-009 | 对话确认 | 文档使用 YAML front matter，最小字段包含 `doc_id/title/doc_type/product_key/status/relations` | 文档模型 |
| SRC-U-010 | 对话确认 | 产品版本下需要支持语义检索 | 产品版本语义检索 |
| SRC-U-011 | 对话确认 | 仓库代码图谱节点只保留结构事实，不再做 AI 摘要、embedding 或代码语义搜索 | 仓库结构图 |
| SRC-U-012 | 对话确认 | 需要支持触发产品下项目仓库分支的代码分析 | 分支分析触发 |
| SRC-U-013 | 对话确认 | 需要支持查看分析状态和记录分析进度 | 分支分析状态与进度 |
| SRC-U-014 | 对话确认 | 需要防止多分支之间相同代码被重复构建 | 跨分支去重 |
| SRC-U-015 | 对话确认 | 整图更新直接重新拉取项目分支，重建仓库级事实图和分支快照 | 项目整图刷新 |
| SRC-U-016 | 对话确认 | 需要提供 CLI 链路获取和上下文查询能力；代码节点刷新命令不再对外暴露 | CLI 链路获取 |
| SRC-U-017 | 对话确认 | 产品需要和插件或 skill 配合使用，默认在它们指导下使用 CLI | 插件和 skill 引导的 CLI |
| SRC-U-018 | 对话确认 | 需要判断哪些规则放在插件/skill 中，哪些规则必须落在 CLI 中 | 规则分层 |
| SRC-U-019 | 对话确认 | CLI 需要支持更新、添加、删除节点和关系，所有节点都允许手动修改 | 图手工管理 |
| SRC-U-020 | 对话确认 | 节点类型和关系类型必须受项目内白名单限制，不允许产生项目之外的类型 | 项目图类型注册 |
| SRC-U-021 | 对话确认 | 关系允许跨项目，但关系自身必须有归属项目，并按归属项目的关系类型白名单校验 | 跨项目关系 |

## 2. 本地代码来源

| ID | 文件 | 本地事实摘要 | 关联内容 |
| --- | --- | --- | --- |
| SRC-C-001 | `src/service/repositories/product_version_repository.py` | 已有 `product_versions` 和 `product_version_branches` 数据模型，支持产品版本与项目分支映射 | ProductVersion |
| SRC-C-002 | `src/service/services/sync_service.py` | 已支持 `sync_commits_for_version/project`，可在代码同步后刷新图谱并更新 `last_parsed_commit` | 项目整图刷新 |
| SRC-C-003 | `src/service/services/watch_service.py` | Watch 流程已实现 `copy_data / incremental / full` 三段策略；当新分支与其他分支 `HEAD` 相同时可复用已解析图数据 | 跨分支去重 |
| SRC-C-004 | `src/gitnexus_parser/neo4j_writer.py` | 仓库事实图按 `repo_id + path + content_hash` 写入，节点不再带分支身份 | 仓库事实图 |
| SRC-C-005 | `src/service/services/branch_snapshot_service.py` | 分支快照记录产品版本、项目、分支、HEAD 与可见文件事实引用 | 分支快照 |
| SRC-C-006 | `src/service/repositories/branch_analysis_status_repository.py` | 分支分析状态表支持运行中、进度、心跳、完成和失败记录 | 分析任务状态模型 |
| SRC-C-007 | `src/service/services/branch_analysis_service.py` | 分支分析只编排图谱同步和快照更新，不再触发代码 AI 预处理 | 分支分析触发与进度 |
| SRC-C-008 | `src/service/routers/sync.py` | 已有 `watch-status` 接口，可查看项目 watch 状态和各版本 `last_parsed_commit` | 准备度 / 去重可见性 |
| SRC-C-009 | `src/service/agent_profiles.py` | 已存在 `nexus_search` 等检索能力，可作为 CLI 检索输出依据 | 版本语义检索 |
| SRC-C-010 | `src/service/workflows/requirement_doc_workflow.py` | 工作流已消费 `version_name / branch_map / project_id_map` | 产品版本 |
| SRC-C-011 | `src/service/services/doc_semantic_search_service.py` | 文档分块保留语义检索能力，和代码节点语义搜索解耦 | 文档语义检索 |
| SRC-C-012 | `src/gitnexus_parser/ingestion/facts.py` | 文件事实 ID 基于仓库、路径和内容哈希生成，支持跨分支复用 | 结构事实去重 |
| SRC-C-013 | `src/service/services/graph_query_service.py` | 链路查询通过分支快照裁剪可见文件范围，再访问 Neo4j 结构事实 | 链路获取 |
| SRC-C-014 | `src/service/services/node_service.py` | 已支持按版本和分支快照列出可见图谱节点 | 节点列表 |
| SRC-C-015 | `src/service/agent_profiles.py` | 已明确 `nexus_explore / nexus_impact / nexus_cypher` 用于关系、影响和链路追踪 | 链路获取 |

## 3. 结论

- 这版 PRD 不是抽象设想，而是围绕现有产品版本、图谱同步、分支分析状态、仓库级结构事实、快照裁剪、文档语义检索和 CLI 图管理能力形成。
- 产品默认通过插件/skill 引导用户，再调用 CLI 完成执行；CLI 是业务执行、状态持久化和结构化结果输出的唯一事实层。

## 关联文档
- [[requirements/rd-knowledge-graph-mvp/01-master-prd|研发知识图谱中台 MVP 总 PRD]]
