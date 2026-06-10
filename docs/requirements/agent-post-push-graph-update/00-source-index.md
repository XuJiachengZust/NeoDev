---
doc_id: NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-SOURCE-INDEX
title: Agent Push 后图谱更新事实源索引
aliases:
  - Agent Push 后图谱更新事实源索引
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/requirements
  - requirements/agent-post-push-graph-update
created: 2026-05-13
updated: 2026-05-13
related:
  - '[[README|Agent Push 后图谱更新 PRD 产物索引]]'
  - '[[01-master-prd|Agent Push 后图谱更新总 PRD]]'
  - '[[features/F004-skill-behavior-protocol|F004 Skill 行为协议 PRD]]'
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-README
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-MASTER-PRD
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F004-SKILL-BEHAVIOR-PROTOCOL
---

# Agent Push 后图谱更新事实源索引

> 本文只记录事实源和推断限制，不定义最终业务规则。代码事实只代表当前仓库状态，不等同于已确认产品口径。

## 1. 用户输入

| 编号 | 来源 | 内容摘要 | 可用性 | 可追踪到 | 备注 |
| --- | --- | --- | --- | --- | --- |
| SRC-U-001 | 用户消息，2026-05-13 | 代码提交后的后置操作需要自动更新图谱和相关数据。 | 已确认 | R-001, F001, AC-G-01 | 最终触发点已进一步确认是 push 成功后 |
| SRC-U-002 | 用户消息，2026-05-13 | 后置操作需要区分文档和代码。 | 已确认 | R-002, F002, BR-G-02 | 需要复用或扩展现有 scope 分类能力 |
| SRC-U-003 | 用户消息，2026-05-13 | 带有文档变更 id 时，需要自动关联文档和代码。 | 已确认 | R-003, F003, BR-G-03 | 文档变更 id 在现有口径中对应 `DocChange-ID` |
| SRC-U-004 | 用户确认，2026-05-13 | 触发点为 push 成功之后。 | 已确认 | R-001, F001, BR-G-01 | 不以 commit 成功后作为本期触发点 |
| SRC-U-005 | 用户确认，2026-05-13 | 只在 Agent 插件层面做。 | 已确认 | R-004, F001, NFR-001 | 不覆盖普通终端或 IDE 的原生 Git push |
| SRC-U-006 | 用户确认，2026-05-13 | 整个需求更适合封装为 skill；hook 中提示 Agent 执行该 skill；固定流程行为封装成脚本调用 CLI，以提高稳定性。 | 已确认 | R-006, F001, F004, BR-G-07 | 明确 hook、脚本、CLI、skill 的分层方向 |
| SRC-U-007 | 用户确认，2026-05-13 | Q101：Agent 自己获取；Q102：需要持久化，追加覆盖；Q103：不做权限；Q104：参数只能选择本地可以直接获取的；Q105：选择 C；Q106：失败需要全部回滚保持原子性；Q107：选择 B。 | 已确认 | R-007, R-008, F001, F002, F003, F004, BR-G-08, BR-G-09, BR-G-10 | 关闭全部待确认问题 |

## 2. 本地需求与技能设计文档

| 编号 | 路径 | 内容摘要 | 适用范围 | 可信度 | 可追踪到 |
| --- | --- | --- | --- | --- | --- |
| SRC-D-001 | `docs/requirements/rd-knowledge-graph-mvp/features/F003-git-consistency-and-risk-control.md` | 既有 F003 描述 Git 一致性、危险提交与 push 后刷新；插件/Skill 负责编排，CLI 负责校验、状态回写、风险登记和刷新。 | Git 一致性与 push 后刷新背景 | 高 | R-001, R-003, F001, F003 |
| SRC-D-002 | `docs/requirements/git-dangerous-commit-guard/01-master-prd.md` | 危险提交守卫 PRD 记录插件内聚、仓库级 Git 守卫、`DocChange-ID` 和 dangerous commit 的既有产品背景。 | 术语和守卫边界复用 | 高 | R-002, R-003, BR-G-02 |
| SRC-D-003 | `docs/requirements/git-dangerous-commit-guard/features/F002-commit-message-guard.md` | 代码提交必须包含唯一合法 `DocChange-ID`，document-only 可跳过代码 trailer 校验，mixed 提交需拆分。 | DocChange-ID 与提交范围规则背景 | 高 | R-002, R-003, F002, F003 |
| SRC-D-004 | `docs/requirements/git-dangerous-commit-guard/features/F003-pre-push-dangerous-commit-guard.md` | pre-push 会读取 push commit range，对代码提交调用 `neodev git verify-doc-change`。 | push 范围与校验前置事实 | 高 | F002, F003 |
| SRC-D-005 | `docs/neosuperpower/plans/2026-04-28-controlled-graph-management.md` | 旧 `git post-push-refresh` 已删除，当前通过 `project refresh-graph` 做分支图谱刷新。 | 当前刷新入口历史决策 | 高 | R-001, F001 |
| SRC-D-006 | `C:\Users\AH\.codex\skills\.system\skill-creator\SKILL.md` | Skill 适合承载专门工作流和工具集成；需要确定性可靠的重复动作宜放入 scripts；SKILL.md 应保持精简。 | 后置处理 Skill 设计原则 | 高 | R-006, F004, NFR-005 |

## 3. 代码事实

| 编号 | 路径 | 事实摘要 | 推断限制 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-C-001 | `plugins/neodev-rd-knowledge/hooks/hooks.json` | 当前 `PostToolUse` 中存在 `Bash(git push *)` matcher，但命令仅 `echo` 提醒手动运行 `neodev project refresh-graph`。 | 说明已有 Agent 层入口，但自动执行尚未实现。 | R-001, F001 |
| SRC-C-002 | `plugins/neodev-rd-knowledge/hooks/hooks.json` | 当前 `PreToolUse` 对 `neodev`、`git commit`、`git push` 调用 `ensure_git_guard.py` 和 `check_neodev_environment.py`。 | 这是执行前检查，不是 push 成功后的数据更新。 | F001 |
| SRC-C-003 | `plugins/neodev-rd-knowledge/check_git_commit_scope.py` | 可按路径把变更分类为 `document`、`code`、`mixed`、`empty`；code 的提示 workflow 已包含 `project refresh-graph after push`。 | 现有函数面向 staged paths，push 后 commit range 复用方式需设计。 | R-002, F002 |
| SRC-C-004 | `plugins/neodev-rd-knowledge/git_guard_pre_push.py` | `check_pre_push` 能解析 refs、计算 commit range、跳过 document/empty、拒绝 mixed、对 code 调用 `git verify-doc-change`。 | 发生在 pre-push 阶段，不负责 push 成功后的刷新。 | F002, F003 |
| SRC-C-005 | `src/service/services/commit_message_parser.py` | `parse_doc_change_id` 要求提交消息中唯一 `DocChange-ID` trailer，值为 40 位十六进制文档 commit hash。 | 只解析提交消息，不刷新图谱。 | F003 |
| SRC-C-006 | `src/service/services/git_consistency_service.py` | `verify_doc_change` 成功时创建 `CodeChangeLink` 并把 DocChange 标记为 `in_implementation`。 | 这是文档与代码关联的现有服务能力，可被后置脚本通过 CLI 复用。 | R-003, F003 |
| SRC-C-007 | `src/service/services/sync_service.py` | `refresh_graph_for_branch` 会 fetch/checkout 项目仓库、运行 parser pipeline、写入 Neo4j 分支图谱并记录刷新运行。 | 当前是分支级 full replace 或 skipped，不是 commit 增量刷新。 | R-001, F001 |
| SRC-C-008 | `src/service/cli/commands/project.py` | CLI 注册 `project refresh-graph`，支持 `--project-id` 或 `--project-name` 与 `--branch`。 | 可作为 Agent 后置脚本的刷新入口。 | F001 |
| SRC-C-009 | `src/service/cli/commands/git.py` | CLI 注册 `git verify-doc-change`，参数包含 project、branch、commit sha、commit message。 | 需要调用方提供 commit range 和 commit message。 | F003 |
| SRC-C-010 | `src/service/services/doc_import_service.py` | 文档导入会同步文档仓库、保存文档 `last_seen_commit`，并更新文档图谱、分块和向量。 | 用户已确认 document-only push 后自动触发文档导入并登记 DocChange。 | F002 |
| SRC-C-011 | `src/service/services/doc_change_service.py` | `register_doc_change` 要求 `DocChange-ID` 和 `source_commit` 为同一个 40 位文档 commit hash，初始状态为 `pending_implementation`。 | 不说明 push 后是否自动登记新 DocChange。 | F003 |
| SRC-C-012 | `tests/test_git_consistency_service_unit.py` | 测试断言 `git_consistency_service` 没有 `post_push_refresh` 入口。 | 说明当前没有服务层 post-push 专用入口。 | F001 |
| SRC-C-013 | `src/service/cli/commands/doc.py` | CLI 已注册 `neodev doc import --doc-binding-id ... --json` 与 `neodev doc change register --document-id ... --doc-change-id ... --source-commit ... --json`。 | 后置脚本仍需从本地上下文解析 doc binding、document id 和文档 commit。 | F002, F004 |

## 4. 接口与数据事实

| 编号 | 路径/接口/表 | 事实摘要 | 推断限制 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-A-001 | Agent hook: `PostToolUse` + `Bash(git push *)` | Agent 插件层已有 push 后工具 hook 配置位置。 | 需要确认 Agent hook 运行时是否只在命令成功后触发。 | F001, Q-101 |
| SRC-A-002 | CLI: `neodev project refresh-graph --project-id/--project-name --branch --json` | 当前分支图谱刷新入口。 | 项目定位参数需由脚本从环境或 `.neodev/project.json` 解析。 | F001 |
| SRC-A-003 | CLI: `neodev git verify-doc-change --project-id --branch --commit-sha --commit-message --json` | 当前 DocChange-ID 校验与 CodeChangeLink 创建入口。 | 需要 push 后脚本提供 commit sha 和 message。 | F003 |
| SRC-A-004 | `docker/init.sql` 表 `code_change_links` | 关联数据包含 `doc_change_id`、`project_id`、`branch`、`commit_sha`、`commit_message`。 | 是否需要防重复写入需另行设计。 | F003, Q-102 |
| SRC-A-005 | `docker/init.sql` 表 `graph_refresh_runs` | 图谱刷新运行记录包含 project、branch、status、head commit before/after、节点边数量。 | 当前记录来自分支刷新，不区分 push 后自动触发来源。 | F001 |

## 5. 测试与验收材料

| 编号 | 路径 | 内容摘要 | 适用范围 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-T-001 | `tests/test_git_guard_scripts.py` | 覆盖 Git guard 安装幂等、保留用户 hook、插件 hook command 从 cache 解析脚本。 | 插件 hook 基础回归 | F001 |
| SRC-T-002 | `tests/test_git_guard_scripts.py` | 覆盖 commit-msg 对 code 缺失 DocChange-ID 失败、document-only 跳过、pre-push 阻断 verify 失败。 | push 前分类与校验回归 | F002, F003 |
| SRC-T-003 | `tests/test_commit_message_parser_unit.py` | 覆盖 DocChange-ID trailer 缺失、重复、空值和非 40 位 hash 的解析失败。 | DocChange-ID 格式回归 | F003 |
| SRC-T-004 | `tests/test_git_consistency_service_unit.py` | 覆盖 `verify_doc_change` 创建 link、推进状态和失败登记 dangerous commit。 | 文档与代码关联回归 | F003 |
| SRC-T-005 | `tests/test_cli_contract.py` | 覆盖 `git post-push-refresh` 已移除，`project refresh-graph` 已注册。 | CLI 合同回归 | F001 |

## 6. 事实收集结论

- 当前最直接可改造点是 Agent 插件层 `PostToolUse` 的 `Bash(git push *)` hook。（SRC-U-005, SRC-C-001）
- 稳定方案应把固定流程放在插件脚本中，由脚本调用 `neodev` CLI；Skill 不承担核心写入和刷新，只规范 Agent 如何解释结果、汇报和执行补救。（SRC-U-006, SRC-D-006）
- 当前图谱刷新应复用 `neodev project refresh-graph`，不恢复旧 `git post-push-refresh`。（SRC-D-005, SRC-C-008, SRC-T-005）
- 带 `DocChange-ID` 的文档与代码关联应复用 `neodev git verify-doc-change` 与现有 `CodeChangeLink` 写入能力。（SRC-U-003, SRC-C-006, SRC-A-003）
- 本次待确认问题已由用户关闭：Agent/脚本本地获取上下文；运行记录持久化并采用追加覆盖；不新增权限；脚本参数只允许本地可直接获取的上下文；document-only 自动导入并登记 DocChange；失败全量回滚保持原子性；扩展现有 `neodev-rd-knowledge` skill。（SRC-U-007）
