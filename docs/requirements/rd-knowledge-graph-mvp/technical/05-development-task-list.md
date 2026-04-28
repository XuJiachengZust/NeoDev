---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-05-DEVELOPMENT-TASK-LIST
title: "研发知识中台 MVP 开发任务列表"
aliases:
  - "研发知识中台 MVP 开发任务列表"
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
# 研发知识中台 MVP 开发任务列表

## 1. 目标

本文档把 PRD 和现有源码能力映射成可执行的开发任务列表，目标是：

- 明确哪些能力可以直接复用现有实现
- 明确哪些能力需要新增元数据、CLI 封装和插件/skill 协同
- 明确哪些地方允许做适度源码改造，而不是被现有结构绑死
- 给出推荐开发顺序、依赖关系、源码落点和验收口径

本文档是 [04-implementation-checklist.md](./04-implementation-checklist.md) 的落地拆分版，重点面向开发排期和任务分配。

## 2. 拆分原则

- 优先复用已有 `service/repository/service/router` 能力，不重复造轮子
- 允许围绕现有边界做适度源码改造，包括抽取公共逻辑、拆分过重服务、补中间服务层
- 底层数据结构允许适度冗余、快照化和反范式，优先稳定性、可维护性和可追踪性，而不是最省存储
- 先打通 `本地 CLI 客户端 + 远程服务 + 元数据 + 图谱事实`，再补插件/skill 引导层
- 先交付主链路，再补增强链路
- 任何状态机、校验、事实写入都落在远程 NeoDev 服务；本地 CLI 只负责调用远程服务，不放在插件/skill
- 任何自然语言引导、风险提示、命令编排都落在插件/skill

## 3. 推荐里程碑

### M1 基础壳层

- T001 CLI 壳层与统一结果协议
- T002 轻量元数据库模型与迁移
- T003 产品 / 产品版本 / 分支绑定 CLI

### M2 文档与分析主链路

- T004 文档治理、扫描与受控仓库接入
- T005 DocChange 登记与状态流转
- T006 仓库接入与自动图谱构建
- T007 图谱复用策略接入

### M3 图谱查询与推送闭环

- T008 节点结构化索引与向量化
- T009 产品版本下语义检索
- T010 节点刷新与链路获取 CLI
- T011 Git 校验、危险提交与推送后刷新

### M4 使用层交付

- T012 官方插件实现
- T013 官方 skill 实现
- T014 联调验收与最小示例工程

## 4. 任务列表

### T001 CLI 壳层与统一结果协议

目标：
建立统一本地 CLI 客户端入口、远程服务调用协议、命令分组、错误码和 `--json` 输出格式，作为后续所有能力的开发者入口。

依赖：
无。

优先复用：
- [03-cli-contract.md](./03-cli-contract.md)

建议源码落点：
- 新增 `src/service/cli/`
- 新增 `src/service/cli/main.py`
- 新增 `src/service/cli/commands/`
- 新增 `src/service/cli/output.py`
- 新增 `src/service/cli/errors.py`

允许改造：
- 如果现有 router/service 输出格式不稳定，可新增 CLI 专用 adapter，不强行复用 HTTP 返回结构

交付内容：
- 支持 `product`、`doc`、`graph`、`git`、`cli` 一级命令分组
- 支持统一顶层字段 `ok`、`command`、`timestamp`、`data`、`errors`
- 支持 `cli version-check`
- 支持插件/skill 可稳定调用的退出码

验收口径：
- 任一命令支持人类可读输出和 `--json`
- 参数错误、资源不存在、冲突、版本不匹配都有稳定错误码
- 插件/skill 不需要自己解析随意文本

### T002 轻量元数据库模型与迁移

目标：
补齐 MVP 缺失的元数据事实源，避免把 `Product`、`DocChange`、`DangerousCommitRecord` 等运营态信息硬塞进图数据库。

依赖：
- T001

优先复用：
- [src/service/repositories/product_version_repository.py](/D:/PycharmProjects/NeoDev/src/service/repositories/product_version_repository.py)
- [src/service/repositories/version_repository.py](/D:/PycharmProjects/NeoDev/src/service/repositories/version_repository.py)
- [src/service/repositories/ai_preprocess_status_repository.py](/D:/PycharmProjects/NeoDev/src/service/repositories/ai_preprocess_status_repository.py)

建议源码落点：
- 新增 `src/service/repositories/product_repository.py`
- 新增 `src/service/repositories/doc_binding_repository.py`
- 新增 `src/service/repositories/document_repository.py`
- 新增 `src/service/repositories/doc_change_repository.py`
- 新增 `src/service/repositories/dangerous_commit_repository.py`
- 新增迁移脚本或初始化 SQL

允许改造：
- 可将现有 `ai_preprocess_status` 扩展为通用分析任务表，或新增 `branch_analysis_tasks` 后保留兼容层
- 允许为稳定性增加冗余字段和快照字段，例如保存 `branch`、`head_commit`、`analysis_action`、`progress_json` 的历史快照

交付内容：
- `Product`
- `CodeBinding`
- `DocBinding`
- `Document`
- `DocChange`
- `CodeChangeLink`
- `DangerousCommitRecord`
- `BranchAnalysisTask` 或复用现有预处理状态表的兼容方案
- 必要时增加查询优化和审计友好的冗余列，不强求极致范式

验收口径：
- 关键对象都有唯一主键和必要索引
- `DocChange ID` 唯一
- 任务状态、危险提交状态、解决人、解决时间可持久化

### T003 产品 / 产品版本 / 分支绑定 CLI

目标：
把产品、产品版本和项目分支映射关系从现有仓库能力整理成正式 CLI 能力。

依赖：
- T001
- T002

优先复用：
- [src/service/repositories/product_version_repository.py](/D:/PycharmProjects/NeoDev/src/service/repositories/product_version_repository.py)
- [src/service/services/sync_service.py](/D:/PycharmProjects/NeoDev/src/service/services/sync_service.py)

建议源码落点：
- `src/service/cli/commands/product.py`
- 新增 `src/service/services/product_service.py`
- 适度复用现有 repository，不重复写 SQL

允许改造：
- 如现有 `product_version_repository` 与产品主模型边界不清，可新增 service 层统一封装，不直接在 CLI 拼 repository 调用

交付内容：
- `product create/update/show`
- `product version create/show`
- `product version bind-branch`
- 产品版本和项目分支的稳定查询能力

验收口径：
- 可以创建产品并绑定多个项目仓库分支
- 可以为产品版本设置每个项目的目标分支
- 可为后续语义检索和图谱构建提供稳定作用域

### T004 文档治理、扫描与受控仓库接入

目标：
实现文档仓库接入、固定目录校验、front matter 解析和扫描错误记录。

依赖：
- T001
- T002
- T003

优先复用：
- 现有代码中无直接等价能力，需新建

建议源码落点：
- 新增 `src/service/services/doc_scan_service.py`
- 新增 `src/service/services/doc_validation_service.py`
- 新增 `src/service/cli/commands/doc.py`

允许改造：
- 若后续页面渲染也要复用 front matter 解析，可抽成通用 `document_metadata` 模块

交付内容：
- 固定目录 `prd/`、`prototype/`、`tech-design/`
- YAML front matter 最小字段校验
- `relations.target` 校验
- 扫描错误记录保留，不通过不登记 `DocChange`
- `doc scan`

验收口径：
- 文档扫描可生成 `Document` 元数据
- 结构错误文档会留下错误记录
- 文档关系可解析成结构化数据

### T005 DocChange 登记与状态流转

目标：
把“文档提交 -> DocChange -> 待实现”变成稳定闭环。

依赖：
- T002
- T004

优先复用：
- [01-master-prd.md](./01-master-prd.md)
- [features/F001-product-binding-and-docchange-registration.md](./features/F001-product-binding-and-docchange-registration.md)

建议源码落点：
- 新增 `src/service/services/doc_change_service.py`
- `src/service/cli/commands/doc.py`

允许改造：
- 如文档扫描与变更登记耦合过重，可将“扫描事实”和“变更登记”拆成两个独立 service

交付内容：
- `doc change register`
- `doc change show`
- `doc change mark-implemented`
- `DocChange ID` 生成规则
- `pending_implementation` / `in_implementation` / `implemented` 状态机

验收口径：
- 受控文档提交后可登记唯一 `DocChange ID`
- 初始状态正确进入 `pending_implementation`
- 人工确认后才能进入 `implemented`

### T006 仓库接入与自动图谱构建

目标：
支持开发者传入仓库地址后，由远程 NeoDev 自动登记项目并触发图谱构建；插件 / skill 不再展示旧显式分析入口。

依赖：
- T001
- T002
- T003

优先复用：
- [src/service/services/project_service.py](/D:/PycharmProjects/NeoDev/src/service/services/project_service.py)
- [src/service/services/sync_service.py](/D:/PycharmProjects/NeoDev/src/service/services/sync_service.py)
- [src/service/services/watch_service.py](/D:/PycharmProjects/NeoDev/src/service/services/watch_service.py)
- [src/service/repositories/ai_preprocess_status_repository.py](/D:/PycharmProjects/NeoDev/src/service/repositories/ai_preprocess_status_repository.py)

建议源码落点：
- `src/service/cli/commands/project.py`
- 复用 `src/service/services/project_service.py` 的仓库初始化和图谱同步能力
- 旧 `branch_analysis_service` 仅作为兼容层，内部不再调用 AI 预处理

允许改造：
- 将显式分析入口从插件 / skill 主流程移除，保留旧命令兼容已有集成
- 自动图谱构建结果回写到项目初始化结果和可查询状态

交付内容：
- `project create --repo-url`
- `project show`
- 返回 `auto_graph_analysis=true` 和 `init_result.sync`
- 为任务记录保留 `head_commit`、触发来源、错误快照等冗余信息

验收口径：
- 传入仓库地址即可触发远程图谱构建
- 插件 / skill 不展示旧显式分析入口
- 同一项目存在运行中图谱构建时可给出冲突提示

### T007 图谱复用策略接入

目标：
复用当前已有的 `copy_data / incremental / full` 策略，避免多分支重复图谱构建。

依赖：
- T006

优先复用：
- [src/service/services/watch_service.py](/D:/PycharmProjects/NeoDev/src/service/services/watch_service.py)
- [src/service/services/sync_service.py](/D:/PycharmProjects/NeoDev/src/service/services/sync_service.py)
- [src/service/repositories/version_repository.py](/D:/PycharmProjects/NeoDev/src/service/repositories/version_repository.py)

建议源码落点：
- `src/service/services/branch_analysis_service.py`
- 可能需要抽取 `watch_service` 的策略判断逻辑为独立 helper

允许改造：
- 可把 `watch_service` 和 `sync_service` 中分散的增量/全量判定统一抽到共享策略模块
- 允许维护分支级复用元数据或缓存映射表，换取更稳定的复用判定

交付内容：
- 同 HEAD 分支优先 `copy_data`
- 存在 `last_parsed_commit` 时走 `incremental`
- 其他场景走 `full`
- CLI 返回图谱构建动作和复用策略

验收口径：
- 相同代码不重复全量构建
- 可解释当前任务为什么选中某种策略
- `last_parsed_commit` 在成功后正确回写

### T008 节点结构化索引与向量化

目标：
正式暴露仓库图谱节点结构化索引与 embedding 刷新能力。

依赖：
- T006
- T007

优先复用：
- [src/service/services/doc_semantic_search_service.py](/D:/PycharmProjects/NeoDev/src/service/services/doc_semantic_search_service.py)
- [src/service/repositories/document_chunk_repository.py](/D:/PycharmProjects/NeoDev/src/service/repositories/document_chunk_repository.py)
- [src/service/services/llm_client.py](/D:/PycharmProjects/NeoDev/src/service/services/llm_client.py)

建议源码落点：
- `src/service/cli/commands/graph.py`
- 扩展 `src/service/services/sync_service.py`
- 扩展 `src/service/services/project_service.py`

允许改造：
- 代码节点不再执行 AI 摘要、embedding 或语义刷新
- 推送后默认使用提交级图谱刷新；提交过大或无法定位时才使用分支级兜底刷新

交付内容：
- `project refresh-commit-graph`
- `project refresh-graph`
- 文档分块 embedding 复用
- 分支快照更新

验收口径：
- 可按当前提交刷新代码结构节点和关系
- 分支级兜底刷新不能丢失文档节点与代码节点关系
- 文档分块未变化时优先复用 embedding

### T009 产品版本下语义检索

目标：
基于文档分块 embedding 能力提供产品版本作用域内的文档语义检索。

依赖：
- T003
- T008

优先复用：
- [src/service/services/doc_semantic_search_service.py](/D:/PycharmProjects/NeoDev/src/service/services/doc_semantic_search_service.py)
- [src/service/agent_profiles.py](/D:/PycharmProjects/NeoDev/src/service/agent_profiles.py)

建议源码落点：
- `src/service/cli/commands/graph.py`
- 扩展 `src/service/services/graph_semantic_search_service.py`

允许改造：
- 如果当前文档语义检索逻辑散在 agent profile 里，可下沉到独立 service，再由 agent/profile/CLI 共享
- 允许在元数据库中维护检索作用域快照和必要的复用记录，但不把检索结果缓存作为 MVP 主路径

交付内容：
- `graph semantic-search`
- 作用域限定到 `product_version_id`
- 结果包含文档分块、标题路径、摘要片段、`score`、`semantic_status`

验收口径：
- 查询结果不会跨产品版本串数据
- 结果可被插件/skill 直接消费
- 向量不可用或未就绪时返回明确状态

### T010 节点刷新与链路获取 CLI

目标：
把图谱查询能力收敛成稳定 CLI，而不是让插件/skill 直接碰底层图库。

依赖：
- T008
- T009

优先复用：
- [src/service/services/node_service.py](/D:/PycharmProjects/NeoDev/src/service/services/node_service.py)
- [src/service/agent_profiles.py](/D:/PycharmProjects/NeoDev/src/service/agent_profiles.py)

建议源码落点：
- `src/service/cli/commands/graph.py`
- 新增 `src/service/services/chain_service.py`

允许改造：
- 如果 `node_service` 过于面向现有 API，可抽出图查询 facade，供 CLI 和其他入口共用
- 允许增加节点访问快照或诊断记录，但不把链路查询结果缓存和预聚合作为 MVP 主路径

交付内容：
- `graph impact`
- `graph entity-context`
- `graph get-chain`
- `project refresh-commit-graph`

验收口径：
- 能按 `DocChange` 输出影响范围
- 能按节点或 commit 输出链路
- 插件/skill 不需要自己拼 Cypher 或直接查图数据库

### T011 Git 校验、危险提交与推送后刷新

目标：
把代码提交约束、风险记录和推送后图谱刷新串成闭环。

依赖：
- T005
- T008
- T010

优先复用：
- [src/service/services/sync_service.py](/D:/PycharmProjects/NeoDev/src/service/services/sync_service.py)
- [src/service/services/watch_service.py](/D:/PycharmProjects/NeoDev/src/service/services/watch_service.py)

建议源码落点：
- `src/service/cli/commands/git.py`
- 新增 `src/service/services/git_consistency_service.py`
- 扩展 `src/service/services/project_service.py` 和 `src/service/services/sync_service.py`

允许改造：
- `sync_service` 保留提交同步能力，并新增按提交刷新图谱的受控入口
- 允许单独维护危险提交待处理清单、解决流水和分支快照记录，优先审计清晰

交付内容：
- `git verify-doc-change`
- `git dangerous-commit resolve`
- `project refresh-commit-graph`
- `project refresh-graph`
- `CodeChangeLink`
- `DangerousCommitRecord`

验收口径：
- `DocChange-ID` trailer 校验稳定
- 二次确认后可登记危险提交
- 推送后默认只刷新本次提交对应的节点和关系；提交过大时才使用分支级刷新兜底
- 危险提交支持查询、关闭、记录 `resolved_by` / `resolved_at`

### T012 官方插件实现

目标：
交付一套完整可用的官方插件，把 CLI 能力包装成面向 Codex / Claude Code 的引导式入口。

依赖：
- T001 到 T011

优先复用：
- [02-plugin-skill-guidance.md](./02-plugin-skill-guidance.md)
- [03-cli-contract.md](./03-cli-contract.md)

建议源码落点：
- 仓库内新增官方插件目录
- 如有插件市场索引，同步补充元数据

交付内容：
- 版本检查
- 常用工作流编排
- 风险提示
- 参数补全
- 结果解释

验收口径：
- 插件不绕过 CLI 直接写状态
- 插件能稳定串起常见主链路
- 版本不匹配时可触发 `cli version-check`

### T013 官方 skill 实现

目标：
交付一套完整可用的官方 skill，指导本地智能工具正确使用 CLI。

依赖：
- T001 到 T011

优先复用：
- [02-plugin-skill-guidance.md](./02-plugin-skill-guidance.md)

建议源码落点：
- 仓库内新增官方 skill 目录和说明

交付内容：
- 文档变更闭环使用指引
- 语义检索与链路查询使用指引
- 提交前校验与危险提交处理指引
- 推送后刷新指引

验收口径：
- skill 只负责编排和提示，不承载事实写入
- skill 能稳定指导 agent 选对命令顺序

### T014 联调验收与最小示例工程

目标：
提供一套可以反复跑通的最小示例，避免功能做完但无法从用户视角串起来。

依赖：
- T001 到 T013

优先复用：
- 现有仓库中的测试风格和最小工程组织方式

建议源码落点：
- 新增示例文档仓库样例
- 新增最小项目仓库样例
- 新增联调说明文档

交付内容：
- 一套最小产品
- 一个文档仓库
- 两个项目分支场景
- 一次文档变更到推送后刷新的端到端演示

验收口径：
- 新人按文档可复现主链路
- 插件/skill 和 CLI 可以一起跑通

## 5. 关键依赖关系

- `T001` 是所有 CLI 任务的基础
- `T002` 是文档闭环、风险记录、分析任务状态的基础
- `T003` 是产品版本作用域内分析和检索的基础
- `T004 + T005` 构成文档闭环
- `T006 + T007` 构成自动图谱构建和去重主链路
- `T008 + T009 + T010` 构成图谱查询和文档语义能力主链路
- `T011` 把文档闭环和代码落地闭环接起来
- `T012 + T013` 是最终用户可用性的交付层

## 6. 建议分工方式

如果按 2 到 3 个并行实现面拆分，建议这样切：

- A 线：CLI 壳层、元数据库、产品/文档模型
  对应 `T001` 到 `T005`
- B 线：自动图谱构建、图谱复用、结构化事实与文档语义检索
  对应 `T006` 到 `T010`
- C 线：Git 闭环、插件、skill、联调
  对应 `T011` 到 `T014`

其中 `T001` 和 `T002` 必须先完成基础骨架，再开始大规模并行。

## 7. 最小首批开发包

如果先只做第一批可演示能力，建议收敛为：

- T001 CLI 壳层与统一结果协议
- T002 轻量元数据库模型与迁移
- T003 产品 / 产品版本 / 分支绑定 CLI
- T004 文档治理、扫描与受控仓库接入
- T005 DocChange 登记与状态流转
- T006 仓库接入与自动图谱构建
- T007 图谱复用策略接入
- T008 仓库结构图谱事实索引
- T009 产品版本下文档语义检索

这批做完后，已经可以支撑：

- 绑定产品和产品版本
- 接入文档仓库和项目分支
- 触发自动图谱构建并查看状态
- 做产品版本下的文档语义检索
- 登记文档变更并生成 `DocChange ID`

## 8. 后续建议

- 下一步可把本文件继续拆成 Jira/禅道级别的子任务
- 如果要直接进入实现，可以先从 `T001 + T002` 开始建立骨架
- 如果要让多名 agent 并行工作，可以按第 6 节拆线
- 如果后续你决定正式改底层表结构，我建议先把 `T002` 单独再细拆一版“数据模型改造任务清单”
