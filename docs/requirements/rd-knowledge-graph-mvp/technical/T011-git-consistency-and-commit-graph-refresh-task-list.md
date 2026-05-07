---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-TECHNICAL-T011-GIT-CONSISTENCY-AND-POST-PUSH-REFRESH-TASK-LIST
title: T011 Git 一致性与推送后刷新任务清单
aliases:
- T011 Git 一致性与推送后刷新任务清单
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

# T011 Git 一致性与推送后刷新任务清单

## 1. 目标

本清单用于细化 `T011 Git 校验、危险提交与推送后刷新`，重点解决以下问题：

- 将 `DocChange-ID` 从文档约束变成代码提交闭环中的稳定协议
- 将危险提交从“提示信息”升级为可追踪、可关闭、可审计的正式记录
- 将推送后图谱节点刷新、结构化描述刷新和链路更新标准化
- 让 Git 钩子、CLI、插件 / skill 共享同一套规则和结果模型

## 2. 现状基础

当前本地代码已经具备这些可复用能力：

- `src/service/services/sync_service.py`
  已有按项目版本同步提交、刷新图谱、更新 `last_parsed_commit` 的能力。
- `src/service/services/watch_service.py`
  已有 `copy_data / incremental / full` 的复用策略。
- `src/service/git_ops.py`
  已有 `HEAD`、提交列表、`show_commit`、`diff_commit` 等只读 Git 能力。
- `src/service/repositories/commit_repository.py`
  已有 `commits` 持久化和按版本查询能力。
- `src/service/agent_profiles.py`
  已有围绕 commit 分析的能力组织方式。

当前缺失的核心是：

- `DocChange-ID` trailer 的正式解析和校验
- `CodeChangeLink` 的正式模型
- 危险提交待处理清单和关闭流水
- 推送后“按 commit / 节点 / 文件范围”刷新图谱与 结构化描述的标准服务

## 3. 改造原则

- Git 规则最终解释权在 CLI 和服务端，不放在插件 / skill
- 危险提交允许放行，但必须留下正式审计记录
- 推送后刷新采用“批次记录 + 刷新范围快照”模式，方便排错和重放
- 允许保存冗余字段，如 `commit_message_snapshot`、`refresh_scope_json`、`affected_nodes_json`
- 现有 `sync_service` 可以复用，但推送后的默认入口改为 `project refresh-commit-graph`

## 4. 标准链路

推荐的完整链路：

1. 文档提交生成 `DocChange`
2. 开发提交代码时使用 trailer：`DocChange-ID: <id>`
3. 插件 / skill 在推送前调用 `git verify-doc-change`
4. CLI 解析 trailer、校验 `DocChange`、写入 `CodeChangeLink`
5. 如果规则不满足但用户确认继续，CLI 创建 `DangerousCommitRecord`
6. 推送后插件 / skill 调用 `project refresh-commit-graph`
7. CLI 按当前提交刷新图谱节点和关系；提交过大或无法定位时才调用 `project refresh-graph`
8. 后续人工调用 `doc change mark-implemented` 或等价命令确认完成

## 5. 专项任务

### GC-01 建立统一 Git 一致性服务入口

目标：
新增统一的 `git_consistency_service`，承接提交校验、风险登记和提交关联写入。

建议源码落点：

- 新增 `src/service/services/git_consistency_service.py`
- 新增 `src/service/cli/commands/git.py`

允许改造：

- 不要把这类逻辑继续分散在 hook 脚本、插件 prompt 或独立小脚本里

验收口径：

- 所有 Git 校验结果都从同一服务层返回
- CLI 能统一输出 `verified / rejected / risky`

### GC-02 `DocChange-ID` trailer 解析与协议校验

目标：
将 commit message 中的 `DocChange-ID` 解析固化成正式协议。

建议规则：

- 主格式：`DocChange-ID: <doc_change_id>`
- 支持 trailer 位置解析
- 缺失时返回明确错误
- 重复或格式错误时返回明确错误

建议源码落点：

- `src/service/services/git_consistency_service.py`
- 新增 `src/service/services/commit_message_parser.py`

验收口径：

- 校验逻辑不依赖人工约定理解
- trailer 解析结果结构化返回

### GC-03 `CodeChangeLink` 正式落库

目标：
把 commit 与 `DocChange` 的关联建成正式事实，而不是只靠消息文本。

建议依赖：

- [T002-data-model-refactor-task-list.md](./T002-data-model-refactor-task-list.md) 的 `DM-04`

建议字段：

- `doc_change_id`
- `project_id`
- `branch`
- `commit_sha`
- `commit_message_snapshot`
- `matched_by`
- `verification_status`

验收口径：

- 一个 `DocChange` 可关联多个 commit
- 后续查询不需要重新扫 Git 历史

### GC-04 推送前校验结果模型

目标：
把推送前校验的返回值标准化，供插件 / skill 直接消费。

建议返回字段：

- `status`
- `doc_change_id`
- `verification_status`
- `reason`
- `next_actions`
- `dangerous_commit_required`

对应 CLI：

- `git verify-doc-change`

验收口径：

- 插件 / skill 不需要自己猜测用户下一步该做什么
- 失败、风险、通过三种结果边界清晰

### GC-05 危险提交主表与待处理清单

目标：
把危险提交从瞬时提示升级为待处理事项。

建议依赖：

- [T002-data-model-refactor-task-list.md](./T002-data-model-refactor-task-list.md) 的 `DM-06`

建议行为：

- 二次确认后创建 `DangerousCommitRecord`
- 默认进入 `pending`
- 可通过 CLI 查询待处理清单

建议新增命令：

- `git dangerous-commit list`
- `git dangerous-commit resolve`

验收口径：

- 危险提交可单独查询
- 风险不会因为命令执行结束而丢失

### GC-06 危险提交关闭流水

目标：
保留危险提交关闭时的审计记录。

建议字段：

- `resolved_by`
- `resolved_at`
- `resolution_note`

验收口径：

- 每次关闭动作都有记录
- 可以追溯是谁在什么时间关闭了风险

### GC-07 推送后刷新服务

目标：
复用 `project_service` 与 `sync_service`，承接推送后提交级图谱刷新。

建议源码落点：

- 扩展 `src/service/services/project_service.py`
- 扩展 `src/service/services/sync_service.py`
- `src/service/cli/commands/project.py`

允许改造：

- `sync_service` 保留提交同步能力
- “推送后刷新”通过 `project refresh-commit-graph` 暴露为提交级受控入口

验收口径：

- 推送后刷新可以独立触发
- 不要求强依赖完整全量同步

### GC-08 提交范围识别与刷新范围计算

目标：
根据 commit、文件路径、节点映射识别刷新范围。

建议复用：

- `src/service/git_ops.py`
- `src/service/repositories/commit_repository.py`

建议输出：

- `commit_sha_list`
- `changed_files`
- `candidate_nodes`
- `refresh_scope_json`

验收口径：

- 可根据最近一次推送的 commits 生成明确刷新范围
- 刷新范围可审计和复用

### GC-09 图谱节点和关系刷新对接

目标：
把推送后刷新与提交级图谱刷新能力正式接起来。

建议依赖：

- `T010 节点刷新与链路获取 CLI`

建议行为：

- 优先按受影响节点刷新
- 必要时按文件范围刷新
- 只对受影响代码结构节点和关系执行刷新

验收口径：

- 推送后不会无脑全量重跑
- 节点和关系刷新结果可统计

### GC-10 推送后刷新批次记录

目标：
为每次推送后刷新保留批次级审计。

建议依赖：

- [T002-data-model-refactor-task-list.md](./T002-data-model-refactor-task-list.md) 的 `DM-07`

建议字段：

- `run_id`
- `project_id`
- `branch`
- `head_commit`
- `refresh_scope_json`
- `affected_nodes_json`
- `graph_refresh_status`

验收口径：

- 刷新失败时可以重放和排错
- 不需要只靠控制台日志回溯

### GC-11 链路更新与查询一致性

目标：
在推送后刷新后，保证 `graph get-chain`、`graph impact` 等查询尽快读取到最新结果。

建议行为：

- 明确链路查询读取的是最新图谱状态
- 如存在预聚合或缓存，推送后刷新时同步失效或更新

验收口径：

- 推送后查询结果不会长期滞后
- 链路更新行为可解释

### GC-12 旧能力兼容与迁移策略

目标：
改造过程中不破坏现有 `sync-commits` 和提交查询能力。

建议方案：

- 保留 `sync_service.sync_commits_for_version/project`
- 新增 `project refresh-commit-graph`
- 插件 / skill 从旧命令迁移到 `project refresh-commit-graph`

验收口径：

- 旧同步能力仍可用
- 新能力不形成第二套难以维护的并行实现

## 6. 建议执行顺序

1. GC-01 建立统一 Git 一致性服务入口
2. GC-02 `DocChange-ID` trailer 解析与协议校验
3. GC-03 `CodeChangeLink` 正式落库
4. GC-04 推送前校验结果模型
5. GC-05 危险提交主表与待处理清单
6. GC-06 危险提交关闭流水
7. GC-07 推送后刷新服务
8. GC-08 提交范围识别与刷新范围计算
9. GC-09 图谱节点和关系刷新对接
10. GC-10 推送后刷新批次记录
11. GC-11 链路更新与查询一致性
12. GC-12 旧能力兼容与迁移策略

## 7. 关键结论

- 当前已有“提交同步”和“图谱刷新”基础，但还没有“Git 一致性闭环”的正式模型
- `DocChange-ID`、`CodeChangeLink`、`DangerousCommitRecord` 和分支快照记录是这条链路稳定化的关键
- 推送后刷新不应等价于全量同步，而应转为按 commit 和节点范围执行的定向刷新

## 关联文档
- [[requirements/rd-knowledge-graph-mvp/01-master-prd|研发知识图谱中台 MVP 总 PRD]]
