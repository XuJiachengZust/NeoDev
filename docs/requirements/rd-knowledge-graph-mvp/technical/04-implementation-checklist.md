---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-04-IMPLEMENTATION-CHECKLIST
title: "MVP 实现清单"
aliases:
  - "MVP 实现清单"
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
# MVP 实现清单

## 1. 目标

本清单用于把当前 PRD、插件 / skill 引导规范、CLI 契约转换为可执行的实现任务。

清单只覆盖 `MVP/P0` 范围：

- 产品、产品版本、仓库绑定
- 文档仓库接入与 `DocChange` 闭环
- 仓库地址接入后的自动图谱构建、结构化索引与语义检索
- 图谱查询、语义检索、节点刷新、链路获取
- Git 一致性校验、危险提交登记、推送后刷新
- 官方插件与官方 skill 实现

## 2. 实现原则

- 本地 `neodev` CLI 客户端是开发者电脑上的唯一执行入口。
- 统一远程 NeoDev 服务是唯一事实落盘、图谱刷新、分析执行和状态管理入口。
- 插件 / skill 只负责参数补全、流程引导、风险提示和结果解释，不承担本地事实源或本地执行层。
- 平台只负责结构化事实和图谱上下文输出，不负责自主规划和自动改代码。
- `MVP` 不引入独立向量索引层，只增加一个轻量元数据库。
- 图数据库承载代码/文档关系、图谱节点、链路以及 embedding。
- 轻量元数据库承载产品、版本、项目仓库、文档变更、图谱构建状态、危险提交和版本检查等必要元数据。
- 所有命令返回统一结构化结果，至少包含 `ok`、`command`、`timestamp`、`data`、`errors`。
- 能复用服务端现有实现的能力，不在 MVP 内重复造轮子；开发者本地只保留 CLI/skill/插件客户端。
- 优先做可串成闭环的命令，再做增强型体验。
- 文档治理采用轻量规则，不引入重审批流。

## 3. 工作流拆解

### 3.1 W001 CLI 壳层与统一结果契约

目标：

- 建立统一 CLI 入口
- 建立命令分组
- 固化统一 JSON 输出与错误码

核心任务：

- 定义 CLI 根命令与子命令分组
- 定义统一输出结构与错误码枚举
- 约束所有写操作命令支持幂等和可追踪日志
- 增加 `--json` 作为标准输出模式
- 增加 `config set-server`、`config show` 和 `cli version-check`，支持本地 CLI 客户端配置并校验远程 NeoDev 服务

交付物：

- CLI 命令入口
- 通用结果封装器
- 通用异常映射器
- CLI 使用说明

完成标准：

- `03-cli-contract.md` 中列出的命令组可被统一路由
- 成功与失败输出结构一致
- 插件 / skill 可通过 `neodev config show` 检查远程服务配置，并通过 `neodev cli version-check --json` 做版本检查和自动拉齐

### 3.2 W002 产品 / 产品版本 / 仓库绑定

目标：

- 支持产品与产品版本建模
- 支持产品下多个项目仓库分支与一个文档仓库绑定

核心任务：

- 实现 `Product`、`ProductVersion`、`CodeBinding`、`DocBinding` 的持久化接口
- 实现 `product create/update/show`
- 实现 `product version create/show`
- 实现 `product version bind-branch`
- 建立产品版本和项目分支的作用域关系

依赖现有能力：

- 现有版本仓储与版本对象

完成标准：

- 能以 `product_key + product_version_id` 唯一定位工作作用域
- 语义检索、图谱查询、代码分析均能复用该作用域

### 3.3 W003 文档仓库接入与 DocChange 闭环

目标：

- 建立文档仓库固定目录和 front matter 解析
- 形成 `Document` 与 `DocChange` 的最小闭环

核心任务：

- 扫描 `prd/`、`prototype/`、`tech-design/`
- 解析 YAML front matter
- 自动生成或校验 `doc_id`
- 建立文档节点及文档间关系
- 为每次受控文档提交生成 `DocChange ID`
- 实现 `doc scan`、`doc change register`、`doc change show`
- 实现 `doc change mark-implemented`
- 实现轻量文档治理校验

轻治理范围：

- 固定目录校验
- front matter 必填字段校验
- 文档类型校验
- `relations.target` 校验
- 扫描失败或校验失败记录

完成标准：

- 文档提交后能生成 `DocChange`
- `DocChange` 状态至少支持 `pending_implementation`、`in_implementation`、`implemented`
- 文档状态与 `DocChange` 状态分离
- 不合法文档不生成 `DocChange`
- 失败原因可被记录和查询

### 3.4 W004 仓库接入与自动图谱构建

目标：

- 支持通过一条 `project create --repo-url` 接入远程仓库
- 仓库登记后由远程 NeoDev 自动触发图谱构建
- 防止相同代码重复构建

核心任务：

- 实现 `project create --repo-url`
- 实现 `project show`
- 接入现有 `copy_data / incremental / full` 决策逻辑
- 接入 `last_parsed_commit` 和 busy protection
- 对同 HEAD 或同内容分支优先复用已有图谱结果
- 将旧显式分析命令保留为兼容入口，但不进入帮助和插件/skill 主流程

依赖现有能力：

- `project_service.py`
- `sync_service.py`
- `watch_service.py`
- `ai_preprocess_status_repository.py`

完成标准：

- 用户传入仓库地址即可完成项目登记和图谱构建触发
- 插件 / skill 不展示旧显式分析入口
- 相同代码不会被重复全量构建

### 3.5 W005 仓库图谱节点的结构化索引与语义检索

目标：

- 在代码解析结果基础上补齐可检索索引与向量化
- 支持产品版本范围内的语义检索

核心任务：

- 为图谱节点落地 `description`、`embedding`、`embedding_model`、`embedding_updated_at`
- 在节点变更后触发 结构化描述与 embedding 刷新
- 复用内容哈希，避免对未变化节点重复生成描述和向量
- 实现 `graph semantic-search`
- 明确 `semantic_status` 的返回语义

依赖现有能力：

- `ai_analysis_runner.py`
- `agent_profiles.py`
- `ai_description_cache_repository.py`
- `llm_client.py`

完成标准：

- 产品版本下可做语义检索
- 检索命中结果可返回实体、描述、分数、所属项目分支
- 未变化节点优先复用已有 embedding

### 3.6 W006 图谱查询、节点刷新与链路获取

目标：

- 面向本地 agent 提供结构化图谱查询能力
- 支持推送后更新受影响节点和链路

核心任务：

- 实现 `graph impact`
- 实现 `graph entity-context`
- 实现 `graph refresh-nodes`
- 实现 `graph get-chain`
- 为 `graph refresh-nodes` 支持 `project/version/branch/node/path/commit` 范围
- 为 `graph get-chain` 支持直接邻接与 N 跳链路
- 输出节点、边、方向、摘要、受影响提交

依赖现有能力：

- `node_service.py`
- `agent_profiles.py`

完成标准：

- 可按节点、文件、符号、commit 获取链路
- 推送后能只刷新受影响节点，而不是默认全量刷新

### 3.7 W007 Git 一致性校验、危险提交与推送后刷新

目标：

- 让文档变更和代码提交形成最小一致性闭环
- 允许危险提交受控放行并登记
- 支持代码推送后刷新图谱节点和 结构化描述

核心任务：

- 实现 `git verify-doc-change`
- 解析 `DocChange-ID: <id>` trailer
- 建立 `CodeChangeLink`
- 回写 `DocChange` 状态为 `in_implementation`
- 实现 `DangerousCommitRecord` 持久化
- 实现危险提交待处理清单查询
- 实现 `git dangerous-commit resolve`
- 实现 `git post-push-refresh`
- 推送后按 commit 或分支范围同步提交、刷新节点、刷新链路、刷新 结构化描述

依赖现有能力：

- `sync_service.py`
- `watch_service.py`

完成标准：

- 推送前能识别合法 / 非法 / 危险提交
- 危险提交必须二次确认并留痕
- 危险提交放行后进入待处理清单
- CLI 支持查询待处理风险记录
- 风险记录可回写 `resolved_by`、`resolved_at`
- 推送后可增量刷新受影响节点和 结构化描述
- 不引入多级审批、自动升级或定时催办

### 3.8 W008 官方插件与官方 Skill 实现

目标：

- 交付可直接使用的官方插件与官方 skill
- 让插件 / skill 稳定调用 CLI
- 把引导逻辑从 CLI 中解耦出来

核心任务：

- 实现官方插件
- 实现官方 skill
- 固化插件 / skill 推荐命令映射
- 固化典型工作流提示词或命令编排模板
- 统一参数补全、风险提示、结果解释逻辑
- 明确插件 / skill 不允许直接写业务状态
- 为插件和 skill 提供统一版本检查与自动更新入口

依赖文档：

- `02-plugin-skill-guidance.md`
- `03-cli-contract.md`

完成标准：

- 官方插件和官方 skill 都能完整引导以下场景：
- 文档变更到实现方案
- 仓库接入与自动图谱构建
- 推送前校验
- 推送后节点与链路刷新
- 两者对同一场景给出的 CLI 调用序列保持一致

## 4. 推荐交付顺序

### Phase 1 基础命令与模型

- W001 CLI 壳层与统一结果契约
- W002 产品 / 产品版本 / 仓库绑定
- W003 文档仓库接入与 `DocChange` 闭环

产出：

- 产品、版本、文档、`DocChange` 可持久化
- 基础 CLI 骨架可用

### Phase 2 分析与检索闭环

- W004 仓库接入与自动图谱构建
- W005 仓库图谱节点的结构化索引与语义检索
- W006 图谱查询、节点刷新与链路获取

产出：

- 传入仓库地址即可自动触发远程图谱构建
- 可查询项目和图谱上下文
- 可做产品版本范围语义检索
- 可获取链路与刷新节点

### Phase 3 Git 一致性与插件落地

- W007 Git 一致性校验、危险提交与推送后刷新
- W008 官方插件与官方 Skill 实现

产出：

- 文档变更与代码提交闭环
- 危险提交留痕
- 推送后增量刷新
- 官方插件与官方 skill 可稳定引导使用 CLI

## 5. 命令到实现责任映射

| 命令 | CLI 责任 | 插件 / skill 责任 |
| --- | --- | --- |
| `doc change register` | 生成 `DocChange`、落库、返回状态 | 判断何时触发、补全文档上下文 |
| `project create --repo-url` | 登记项目仓库并自动触发图谱构建 | 引导用户提供仓库地址和项目名称 |
| `graph semantic-search` | 在产品版本作用域内返回检索结果 | 组织 query、解释命中结果 |
| `graph refresh-nodes` | 刷新节点、结构化描述、embedding | 推荐刷新范围、解释刷新必要性 |
| `graph get-chain` | 返回链路事实 | 解释链路意义、推荐后续动作 |
| `git verify-doc-change` | 校验 trailer、写回状态、输出风险 | 提示是否继续、补全说明文本 |
| `git post-push-refresh` | 同步提交并刷新图谱 / 结构化描述 | 在推送成功后提醒或自动编排调用 |
| `cli version-check` | 检查 CLI/插件/skill 兼容状态并执行拉齐 | 会话启动时调用并决定是否继续后续流程 |

## 6. 最小测试清单

- 产品创建后可绑定多个代码仓库分支和一个文档仓库
- 文档扫描后可生成 `Document` 节点和文档关系
- 文档提交后可生成唯一 `DocChange ID`
- 不合法文档会被阻止登记 `DocChange`，并留下错误记录
- 相同 HEAD 分支触发图谱构建时优先复用已有结果
- 分析任务运行中再次触发同项目分析会返回冲突
- 节点未变化时 embedding 被复用而不是重复生成
- `graph get-chain` 可返回节点、边、方向和摘要
- `graph refresh-nodes` 可按 commit 范围刷新受影响节点
- `git verify-doc-change` 能识别合法 trailer 与非法 trailer
- 危险提交二次确认后可被登记
- 危险提交可进入待处理清单并被手工关闭
- `git post-push-refresh` 可在推送后刷新受影响节点和 结构化描述
- 插件 / skill 可通过 `cli version-check` 保持与 CLI 一致

## 7. 完成判定

满足以下条件即可认为 MVP 具备实现就绪性：

- 总 PRD、子 PRD、插件 / skill 规范、CLI 契约、实现清单彼此一致
- 每个核心 CLI 命令都有明确输入、输出、状态、副作用和责任边界
- 每条核心能力都能映射到现有代码基础或明确的新实现任务
- 插件 / skill 和 CLI 的职责边界不再模糊
- 官方插件与官方 skill 都达到可用状态，而不是停留在规范文档
- 可以直接据此拆成开发任务、测试任务和集成任务
