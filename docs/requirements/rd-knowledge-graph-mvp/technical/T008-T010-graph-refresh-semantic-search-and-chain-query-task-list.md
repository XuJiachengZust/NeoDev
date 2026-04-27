---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-T008-T010-GRAPH-REFRESH-SEMANTIC-SEARCH-AND-CHAIN-QUERY-TASK-LIST
title: "T008-T010 图谱刷新、语义检索与链路查询任务清单"
aliases:
  - "T008-T010 图谱刷新、语义检索与链路查询任务清单"
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
# T008-T010 图谱刷新、语义检索与链路查询任务清单

## 1. 目标

本清单合并细化以下三项任务：

- `T008 节点 AI 描述刷新与向量化`
- `T009 产品版本下语义检索`
- `T010 节点刷新与链路获取 CLI`

重点解决的问题：

- 把现有节点 AI 分析能力从“全量预处理副产物”升级为“可单独触发、可复用、可观测”的图谱服务能力
- 把语义检索限定在 `ProductVersion` 作用域内，而不是做无边界全局搜索
- 把链路获取、实体上下文、影响分析统一收口到 CLI，不让插件 / skill 直接碰图库
- 允许用快照和内容复用换取更稳定、更可维护的查询行为，但不把查询结果缓存和预聚合作为 MVP 主路径

## 2. 现状基础

当前本地实现已经具备这些关键基础：

- `src/service/services/ai_analysis_runner.py`
  已支持节点 `description` 生成、`embedding` 写回、`content_hash` 缓存复用、向量索引创建。
- `src/service/services/content_hash.py`
  已支持基于节点内容和子节点结构生成稳定哈希。
- `src/service/repositories/ai_description_cache_repository.py`
  已支持按 `content_hash` 缓存描述和向量。
- `src/service/services/node_service.py`
  已支持按项目版本列出图谱节点。
- `src/service/agent_profiles.py`
  已具备图谱搜索、Cypher 查询、链路探索的能力组织方式。
- `src/service/services/llm_client.py`
  已具备 embedding 探活和调用基础。

说明：

- AI 增强和向量化的底层执行已经存在
- 缺的是稳定的产品能力抽象、作用域模型、CLI 封装和缓存策略标准化

## 3. 改造原则

- 图查询能力最终通过 CLI 输出结构化结果，不直接暴露内部 Cypher 给插件 / skill
- 语义检索必须受 `ProductVersion` 约束
- 节点刷新优先做定向刷新，不默认全量重跑
- 允许维护查询快照和必要的复用记录，优先查询稳定性
- AI 刷新和语义检索共享同一套 embedding / cache / status 事实，不允许各自维护一套隐式逻辑

## 4. 标准能力面

这一组任务最终对外收口为 5 个 CLI：

- `graph impact`
- `graph entity-context`
- `graph semantic-search`
- `graph refresh-nodes`
- `graph get-chain`

## 5. 专项任务

### GQ-01 建立统一图谱服务 facade

目标：
新增统一的图谱服务 facade，承接节点刷新、语义检索、链路查询和影响分析。

建议源码落点：

- 新增 `src/service/services/graph_query_service.py`
- 新增 `src/service/services/graph_refresh_service.py`
- 新增 `src/service/services/semantic_search_service.py`
- 新增 `src/service/services/chain_service.py`
- `src/service/cli/commands/graph.py`

允许改造：

- `node_service` 可保留为低层查询工具
- 原本散在 `agent_profiles` 中的图查询逻辑应逐步下沉到 service

验收口径：

- CLI 不直接拼接复杂查询逻辑
- 图相关能力有清晰的服务边界

### GQ-02 节点刷新作用域模型

目标：
把节点刷新从“预处理阶段的隐式行为”升级为显式输入模型。

建议支持的作用域：

- `node_ids`
- `paths`
- `commit_sha`
- `project_id + branch`

建议输出字段：

- `refresh_scope`
- `graph_nodes_updated`
- `ai_descriptions_updated`
- `embeddings_reused`
- `embeddings_regenerated`
- `status`

验收口径：

- 用户或插件可以明确控制刷新范围
- 返回结果能说明到底刷新了什么

### GQ-03 AI 刷新执行层标准化

目标：
把 `ai_analysis_runner` 封装成可被定向调用的执行层。

建议复用：

- `src/service/services/ai_analysis_runner.py`
- `src/service/services/content_hash.py`
- `src/service/repositories/ai_description_cache_repository.py`

建议改造：

- 将“节点选择”和“AI 刷新执行”拆层
- 执行层只负责：
  - 生成 description
  - 生成 embedding
  - 更新缓存
  - 写回 Neo4j

验收口径：

- 可以只刷新指定节点
- 不需要每次都从全图起跑

### GQ-04 `content_hash` 缓存策略标准化

目标：
把当前已有的缓存复用机制变成正式规则。

建议规则：

- `content_hash` 未变化时优先复用描述和 embedding
- 仅当 hash 变化或强制刷新时重算
- cache hit / miss / save / fail 都进入统计

建议保留字段：

- `content_hash`
- `cache_hit`
- `embedding_model`
- `embedding_updated_at`
- `semantic_status`

验收口径：

- 未变化节点不会重复生成 embedding
- 可追踪每次刷新里命中缓存的比例

### GQ-05 向量索引与检索健康状态

目标：
标准化 embedding preflight、索引状态和降级行为。

建议复用：

- `src/service/services/llm_client.py`
- `src/service/services/ai_analysis_runner.py`

建议规则：

- embedding 接口不可用时，允许仅生成 description
- 检索结果标记 `semantic_status=degraded` 或等价状态
- 向量索引创建失败要留下过程记录

验收口径：

- embedding 故障不会让整条链路完全不可用
- 降级状态能被 CLI 明确返回

### GQ-06 产品版本作用域语义检索

目标：
把语义检索限制在产品版本映射下的项目和分支范围内。

建议输入：

- `product_key`
- `product_version_id` 或 `version_name`
- `query`
- `top_k`

建议输出：

- `product_version_id`
- `project_name`
- `branch`
- `entity_type`
- `entity_id`
- `file_path`
- `description`
- `score`
- `semantic_status`

验收口径：

- 搜索不会跨版本串数据
- 搜索结果结构稳定，适合插件 / skill 消费

### GQ-07 检索作用域快照边界

目标：
为语义检索增加稳定性层，避免每次都即席计算所有上下文。

允许设计：

- 作用域快照
- 检索前先解析 `ProductVersion -> branch_snapshot`
- 每条结果都带上 `branch / project / product_version`

前提：

- 不改变图数据库为主事实源的原则
- 不依赖结果缓存也能稳定完成版本作用域检索

验收口径：

- 复杂查询响应更稳定
- 查询故障时更容易排错

### GQ-08 实体上下文查询标准化

目标：
将实体上下文查询从简单节点列表升级为稳定的上下文服务。

对应 CLI：

- `graph entity-context`

建议输出：

- `entity_id`
- `entity_type`
- `file_path`
- `neighbors`
- `relations`
- `semantic_fields`

验收口径：

- 插件 / skill 获取实体上下文不需要再直接调图库

### GQ-09 链路查询服务标准化

目标：
把链路查询从隐式图探索能力升级为正式服务。

对应 CLI：

- `graph get-chain`

建议输入：

- `start_node`
- `file_path`
- `symbol`
- `commit_sha`
- `depth`

建议输出：

- `nodes`
- `edges`
- `path_summary`
- `affected_commits`

验收口径：

- 可以从节点、文件或 commit 出发查询链路
- 结果可直接被智能工具消费

### GQ-10 非目标：链路查询缓存与预聚合

目标：
为高频链路查询提供稳定层。

允许设计：

- `graph get-chain` 先按 `branch_snapshot` 裁剪范围，再按需遍历仓库级事实图
- 节点访问快照
- 不引入链路结果缓存
- 不引入邻接预聚合

验收口径：

- 高阶链路查询不会每次都完全现算
- 后续如需优化，单独立项为 P1 性能专题

### GQ-11 影响分析输出统一

目标：
统一 `graph impact` 的输出，不让不同入口给出不同字段集。

固定输出：

- `affected_repositories`
- `affected_modules`
- `affected_files`
- `affected_symbols`
- `evidence`
- `confidence`
- `risk_points`
- `suggested_steps`

验收口径：

- 影响分析结果结构稳定
- 插件 / skill 可以直接渲染或继续生成方案

### GQ-12 CLI 命令与图服务映射收口

目标：
明确每个 CLI 命令对应的服务职责，避免后面继续散落实现。

对应关系：

- `graph impact` -> `graph_query_service`
- `graph entity-context` -> `graph_query_service`
- `graph semantic-search` -> `semantic_search_service`
- `graph refresh-nodes` -> `graph_refresh_service`
- `graph get-chain` -> `chain_service`

验收口径：

- 每个命令都有唯一主服务
- 不形成多入口重复实现

## 6. 建议执行顺序

1. GQ-01 建立统一图谱服务 facade
2. GQ-02 节点刷新作用域模型
3. GQ-03 AI 刷新执行层标准化
4. GQ-04 `content_hash` 缓存策略标准化
5. GQ-05 向量索引与检索健康状态
6. GQ-06 产品版本作用域语义检索
7. GQ-07 检索作用域快照边界
8. GQ-08 实体上下文查询标准化
9. GQ-09 链路查询服务标准化
10. GQ-10 非目标：链路查询缓存与预聚合
11. GQ-11 影响分析输出统一
12. GQ-12 CLI 命令与图服务映射收口

## 7. 关键结论

- 底层 AI 刷新和 embedding 能力已具备，核心缺口在服务抽象和作用域约束
- `ProductVersion` 是语义检索和链路查询的正式边界
- `content_hash`、缓存和快照不是可选优化，而是稳定性设计的一部分
- 图服务能力必须下沉到 CLI 可消费的统一结构，不能继续依赖隐式 agent 能力

### GQ-13 仓库主图与分支快照查询边界

目标：
统一图刷新、语义检索和链路查询对“多分支存储结构”的理解。

正式口径：

- 图数据库查询的主事实源是仓库级事实图
- 分支只通过 `branch_snapshot` 限定当前可见节点
- 查询先裁剪分支快照范围，再进入事实图遍历

实现约束：

- `graph semantic-search` 不直接对整仓库所有节点做无边界检索
- `graph get-chain` 不假设每个分支都有一份独立整图
- `graph refresh-nodes` 刷新后需要推动当前分支快照切换到新的事实节点

MVP 简化：

- 不把查询结果缓存和预聚合作为主路径
- 先依赖 `branch_snapshot + content_hash` 解决范围裁剪和数据复用
- 若旧文档中存在“查询缓存 / 预聚合”描述，与本节冲突时，以本节为准
