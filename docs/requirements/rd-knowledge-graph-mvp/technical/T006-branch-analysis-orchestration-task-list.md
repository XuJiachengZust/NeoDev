---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-T006-BRANCH-ANALYSIS-ORCHESTRATION-TASK-LIST
title: "T006 仓库接入与自动图谱构建任务清单"
aliases:
  - "T006 仓库接入与自动图谱构建任务清单"
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
# T006 仓库接入与自动图谱构建任务清单

## 1. 目标

本清单用于细化 `T006 仓库接入与自动图谱构建`，重点解决以下问题：

- 开发者传入仓库地址后，远程 NeoDev 自动登记项目并触发图谱构建
- 保留旧分析命令作为兼容层，但不在帮助、插件或 skill 主流程中显式展示
- 统一“仓库登记、图谱构建、并发控制、失败恢复、复用策略”这条链路
- 让 CLI、插件 / skill 和后续推送后刷新都围绕同一远程图谱构建模型工作

## 2. 现状基础

当前本地实现已经提供了这几类可复用能力：

- `src/service/services/project_service.py`
  已有项目仓库登记、初始化和图谱同步触发能力。
- `src/service/repositories/ai_preprocess_status_repository.py`
  已有运行态、进度、心跳、超时失败转移能力。
- `src/service/routers/preprocess.py`
  已有旧触发和查询接口，可作为兼容层保留，不作为用户主流程。
- `src/service/services/watch_service.py`
  已有 `copy_data / incremental / full` 三段复用策略。
- `src/service/services/sync_service.py`
  已有按版本同步提交、刷新图谱、更新 `last_parsed_commit` 的基础逻辑。
- `src/service/repositories/version_repository.py`
  已有 `versions.last_parsed_commit` 的持久化能力。

这说明：

- 核心执行链路不是从零开始
- 主要缺的是“仓库地址接入、自动图谱构建、CLI 封装、兼容改造”

## 3. 改造原则

- 不直接删除旧 `preprocess` / `branch_analysis` 能力，先保留兼容层
- 运行态和历史态分离，避免继续把所有信息塞进 `ai_preprocess_status.extra`
- 复用策略统一收口到仓库图谱构建编排层，不分散在多个入口里
- 项目仓库视角和产品版本视角都保留，但对外主入口统一为 `project create --repo-url`
- 允许保存冗余快照，如 `head_commit`、`analysis_action`、`trigger_source`、`progress_json`

## 4. 编排模型

建议的标准链路：

1. CLI 接收 `project_name + repo_url`
2. 服务层创建或读取项目仓库记录
3. 远程 NeoDev 自动触发图谱构建
4. 执行并发控制和忙碌检查
5. 根据 `HEAD`、`last_parsed_commit` 和图谱现状判定 `copy_data / incremental / full`
6. 执行图谱刷新和必要索引更新
7. 按阶段回写进度、心跳、错误快照
8. 输出项目与图谱构建结果给 CLI
9. 如需产品版本范围，再通过 `product version bind-branch` 建立映射

## 5. 专项任务

### BA-01 建立统一仓库接入入口

目标：
新增 `project create --repo-url`，作为 CLI 用户主入口，并复用项目服务的仓库初始化与图谱同步能力。

建议源码落点：

- 新增 `src/service/cli/commands/project.py`
- 复用 `src/service/services/project_service.py`
- 旧 `src/service/services/branch_analysis_service.py` 作为兼容层保留

允许改造：

- 旧显式分析命令保留为兼容代理，而不是继续承担主入口语义
- 自动图谱构建不再调用 AI 预处理 worker

验收口径：

- CLI 不再直接依赖 HTTP router
- 新入口可以稳定接受产品版本上下文

### BA-02 产品版本作用域校验

目标：
在触发图谱构建前，确认该分支确实属于指定产品版本的项目分支映射。

建议复用：

- `src/service/repositories/product_version_repository.py`
- `src/service/repositories/version_repository.py`

建议新增：

- 在 `branch_analysis_service` 内新增作用域校验函数

验收口径：

- 非产品版本内的项目分支不能被错误触发
- CLI 错误码明确区分 `not_found` 和 `invalid_scope`

### BA-03 任务主表与事件流接入

目标：
将当前 `ai_preprocess_status` 的运行态能力升级成正式任务模型。

建议依赖：

- [T002-data-model-refactor-task-list.md](./T002-data-model-refactor-task-list.md) 的 `DM-05`

建议实现：

- `branch_analysis_tasks` 记录当前任务快照
- `branch_analysis_task_events` 记录阶段事件
- `ai_preprocess_status` 作为兼容层镜像或过渡层

允许改造：

- 初期可双写新表和旧表，后续再逐步收敛

验收口径：

- 当前状态、历史事件、错误快照都可独立查询
- `watch-status` 不再只能依赖 `extra.progress`

### BA-04 并发控制与心跳超时治理

目标：
保留当前忙碌保护能力，并把它从“项目预处理”语义升级为“图谱构建任务”语义。

建议复用：

- `src/service/repositories/ai_preprocess_status_repository.py`

建议改造：

- 忙碌判断从“项目有运行中 preprocess”升级为“项目或产品版本下同一分支不可并发分析”
- 心跳超时策略保留
- 失败原因写入任务快照和事件表

验收口径：

- 同一项目的同一分支不会被并发分析
- 僵尸任务可自动转失败
- 冲突信息可被 CLI 明确返回

### BA-05 复用策略统一收口

目标：
把 `copy_data / incremental / full` 判定统一沉到编排层。

建议复用：

- `src/service/services/watch_service.py`
- `src/service/services/sync_service.py`
- `src/service/repositories/version_repository.py`

建议改造：

- 抽出独立的 `analysis_strategy_resolver`
- 输入统一为 `project_id / branch / head_commit / last_parsed_commit / peer_heads`
- 输出统一为 `analysis_action`

验收口径：

- 相同 `HEAD` 优先 `copy_data`
- 存在 `last_parsed_commit` 且 `HEAD` 已变化时走 `incremental`
- 其他场景走 `full`
- 任务状态中始终带 `analysis_action`

### BA-06 图谱刷新阶段标准化

目标：
将图谱刷新从现有“混在 preprocess 内部”升级为可感知阶段。

建议复用：

- `src/service/services/sync_service.py`
- `src/service/services/ai_preprocessor_service.py`

建议阶段拆分：

- `preflight`
- `graph_sync`
- `graph_verify`
- `ai_enrich`
- `completed`

验收口径：

- 状态查看可以知道卡在哪个阶段
- 图谱为空时能自动触发回退策略并留下日志

### BA-07 图谱构建阶段标准化

目标：
把 图谱语义索引阶段的进度、缓存命中和失败信息标准化。

建议复用：

- `src/service/services/ai_analysis_runner.py`
- `src/service/services/ai_preprocessor_service.py`

建议保留的进度字段：

- `stage`
- `done`
- `total`
- `saved`
- `skipped`
- `failed`
- `cache_hit`

允许改造：

- 允许在任务表中存标准化 `progress_json`
- 不要求继续只写到旧 `extra.progress`

验收口径：

- `project show` 和图谱查询命令都能看到稳定项目/图谱结果
- 缓存命中和失败数可追踪

### BA-08 CLI 命令与状态协议对齐

目标：
把技术流程正式映射到 CLI。

对应命令：

- `project create --repo-url`
- `project show`

旧显式分析命令不进入插件 / skill 主流程。

建议输出字段：

- `analysis_task_id`
- `status`
- `analysis_action`
- `progress`
- `started_at`
- `finished_at`
- `heartbeat_at`
- `error_message`

验收口径：

- 插件 / skill 不需要自己从日志中推断阶段
- 用户主流程不展示旧显式分析入口

### BA-09 旧入口兼容策略

目标：
保证现有 HTTP `preprocess` 能力在改造过程中不立即失效。

建议方案：

- 保留 `routers/preprocess.py`
- 内部改为调用 `branch_analysis_service`
- 将返回结构映射到旧接口格式

验收口径：

- 旧接口仍可用
- 新能力优先走 CLI
- 不形成双套主实现

### BA-10 审计与诊断能力

目标：
让分析任务在失败、回退、复用、超时时可定位。

建议保留信息：

- `trigger_source`
- `triggered_by`
- `head_commit`
- `analysis_action`
- `fallback_reason`
- `error_snapshot`

验收口径：

- 出问题时不用只看散乱日志
- 可以还原一次分析任务的完整决策链

## 6. 建议执行顺序

1. BA-01 建立统一仓库接入入口
2. BA-02 产品版本作用域校验
3. BA-03 任务主表与事件流接入
4. BA-04 并发控制与心跳超时治理
5. BA-05 复用策略统一收口
6. BA-06 图谱刷新阶段标准化
7. BA-07 图谱构建阶段标准化
8. BA-08 CLI 命令与状态协议对齐
9. BA-09 旧入口兼容策略
10. BA-10 审计与诊断能力

## 7. 关键结论

- 当前实现已经具备执行基础，重点不是重写，而是编排层收口
- `preprocess` 语义过窄，后续应逐步让位给 `branch_analysis`
- `ai_preprocess_status` 可以继续复用，但不应继续承担全部长期模型职责
- `copy_data / incremental / full` 必须成为正式任务决策的一部分，而不是隐式实现细节

### BA-11 分支快照语义收口

目标：
把自动图谱构建的结果语义从“生成分支级整图”改成“生成或更新分支快照”。

建议规则：

- `copy_data`：复制已有分支快照或复用其 entry 集合
- `incremental`：只替换变更文件对应的快照 entry
- `full`：生成新的完整快照，但尽量复用已有仓库级事实节点

实现含义：

- 分析编排层不再把“复制图”作为主目标
- 编排层的产出对象变为 `branch_snapshot`
- `head_commit`、`last_parsed_commit` 和 `created_from_action` 都要回写到快照

验收口径：

- 同 HEAD 分支触发图谱构建时，不重复生成整套图数据
- 增量分析后可以看到快照 entry 被局部替换
- `project show` 可返回当前快照标识及来源动作
