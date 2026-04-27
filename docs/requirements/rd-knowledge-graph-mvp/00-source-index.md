---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-00-SOURCE-INDEX
title: "研发知识图谱中台 MVP 来源索引"
aliases:
  - "研发知识图谱中台 MVP 来源索引"
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
| SRC-U-010 | 对话确认 | 产品版本下需要支持语义检索 | ProductVersion Semantic Retrieval |
| SRC-U-011 | 对话确认 | 仓库图谱节点需要支持 图谱语义索引与向量化 | Repository AI Semantic Enrichment |
| SRC-U-012 | 对话确认 | 需要支持触发产品下项目仓库分支的代码分析 | Branch Analysis Trigger |
| SRC-U-013 | 对话确认 | 需要支持查看分析状态和记录分析进度 | Branch Analysis Status / Progress |
| SRC-U-014 | 对话确认 | 需要防止多分支之间相同代码被重复构建 | Cross-Branch Deduplication |
| SRC-U-015 | 对话确认 | 代码推送后需要支持更新链路上的代码节点和 结构化描述 | Post-Push Graph Refresh |
| SRC-U-016 | 对话确认 | 需要提供 CLI 开放节点更新能力和链路获取能力 | CLI Node Refresh / Chain Retrieval |
| SRC-U-017 | 对话确认 | 产品需要和插件或 skill 配合使用，默认在它们指导下使用 CLI | Plugin/Skill Guided CLI |
| SRC-U-018 | 对话确认 | 需要判断哪些规则放在插件/skill 中，哪些规则必须落在 CLI 中 | Rule Layering |

## 2. 本地代码来源

| ID | 文件 | 本地事实摘要 | 关联内容 |
| --- | --- | --- | --- |
| SRC-C-001 | `src/service/repositories/product_version_repository.py` | 已有 `product_versions` 和 `product_version_branches` 数据模型，支持产品版本与项目分支映射 | ProductVersion |
| SRC-C-002 | `src/service/services/sync_service.py` | 已支持 `sync_commits_for_version/project`，可在代码同步后刷新图谱并更新 `last_parsed_commit` | Post-Push Graph Refresh |
| SRC-C-003 | `src/service/services/watch_service.py` | Watch 流程已实现 `copy_data / incremental / full` 三段策略；当新分支与其他分支 `HEAD` 相同时可复用已解析图数据 | Cross-Branch Deduplication |
| SRC-C-004 | `src/service/services/ai_analysis_runner.py` | 图谱节点已支持写回 `description/embedding/embeddingModel/embeddingUpdatedAt` | Node AI Refresh |
| SRC-C-005 | `src/service/services/ai_preprocessor_service.py` | 分支 AI 预处理已具备 LLM preflight、图谱 freshness 校验、进度回调、完成/失败回写 | Branch Analysis Trigger / Progress |
| SRC-C-006 | `src/service/repositories/ai_preprocess_status_repository.py` | 已有分析状态表，支持 `set_running/get_status/update_progress/update_heartbeat/set_completed/set_failed/has_running` | AnalysisTask 状态模型 |
| SRC-C-007 | `src/service/routers/preprocess.py` | 已有按 `project_id + branch` 触发图谱构建和查询状态的接口 | CLI / 服务接口映射 |
| SRC-C-008 | `src/service/routers/sync.py` | 已有 `watch-status` 接口，可查看项目 watch 状态和各版本 `last_parsed_commit` | 准备度 / 去重可见性 |
| SRC-C-009 | `src/service/agent_profiles.py` | 已存在 `nexus_search` 等检索能力，可作为 CLI 检索输出依据 | 版本语义检索 |
| SRC-C-010 | `src/service/workflows/requirement_doc_workflow.py` | 工作流已消费 `version_name / branch_map / project_id_map` | ProductVersion |
| SRC-C-011 | `src/service/services/llm_client.py` | 已有 chat / embedding probe 与 embedding 调用能力 | 图谱语义索引 |
| SRC-C-012 | `src/service/repositories/ai_description_cache_repository.py` | 已有 `content_hash` 缓存及 description / embedding / model 存储 | 向量化缓存与复用 |
| SRC-C-013 | `src/service/services/content_hash.py` | 已有内容哈希策略 | 向量化去重 |
| SRC-C-014 | `src/service/services/node_service.py` | 已支持按版本列出图谱节点 | Node Refresh 能力基础 |
| SRC-C-015 | `src/service/agent_profiles.py` | 已明确 `nexus_explore / nexus_impact / nexus_cypher` 用于关系、影响和链路追踪 | Chain Retrieval |

## 3. 结论

- 这版 PRD 不是抽象设想，而是围绕现有产品版本、图谱同步、AI 预处理、状态跟踪、去重和节点增强能力回写形成。
- 产品默认通过插件/skill 引导用户，再调用 CLI 完成执行；CLI 是业务执行、状态持久化和结构化结果输出的唯一事实层。
