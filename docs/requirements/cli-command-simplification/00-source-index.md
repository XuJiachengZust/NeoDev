---
doc_id: NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-SOURCE-INDEX
title: CLI 命令简化事实源索引
aliases:
  - CLI 命令简化事实源索引
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/requirements
  - requirements/cli-command-simplification
created: 2026-06-10
updated: 2026-06-10
related:
  - '[[requirements/cli-command-simplification/README|CLI 命令简化 PRD 产物索引]]'
  - '[[requirements/cli-command-simplification/01-master-prd|CLI 命令简化总 PRD]]'
  - '[[requirements/cli-command-simplification/99-open-questions|CLI 命令简化待确认问题]]'
doc_type: tech-design
product_key: NEODEV
status: draft
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-README
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-MASTER-PRD
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-OPEN-QUESTIONS
---

# CLI 命令简化事实源索引

## 1. 用户输入

| 编号 | 来源 | 内容摘要 | 可用性 | 可追踪到 | 备注 |
| --- | --- | --- | --- | --- | --- |
| SRC-U-001 | 用户消息，2026-06-10 | 询问“现在命令太多是否还有简化和压缩的空间”。 | 已确认 | R-001, R-002, F001, F002 | 触发命令体系评估。 |
| SRC-U-002 | 用户消息，2026-06-10 | 明确“本次只要评估”。 | 已确认 | R-001, NFR-001 | 约束本轮不做实现。 |
| SRC-U-003 | 用户消息，2026-06-10 | 要求“写一个需求，简化命令”。 | 已确认 | R-001, R-003, F001, F002, F003 | 本 PRD 直接来源。 |
| SRC-U-004 | 会话评估结论，2026-06-10 | 建议保留底层原子命令，新增少量 workflow 命令并隐藏高级/内部命令。 | 候选 | R-001, R-002, BR-G-01, BR-G-02 | 需产品负责人确认最终命名。 |
| SRC-U-005 | 用户消息，2026-06-10 | 确认 Q-101 接受顶层命名；Q-102 采用 `neodev help --all`；Q-103 插件命令说明收口为 context/docs/change/submit 四个意图入口。 | 已确认 | F001, F002, F003, D-003, D-004, D-005 | 关闭原非阻塞待确认项。 |
| SRC-U-006 | 用户消息，2026-06-10 | 补充要求注意各命令的操作和数据是否可以形成闭环。 | 已确认 | BR-G-06, AC-G-06, F001, F003, D-006 | 约束高层命令必须说明输入、读写数据、输出证据、下一步动作和失败恢复。 |
| SRC-U-007 | 用户消息，2026-06-10 | 补充要求这些命令之间在业务上也需要闭环。 | 已确认 | BR-G-07, AC-G-07, F001, F003, D-007 | 约束命令集合必须形成端到端业务生命周期，而不是孤立命令清单。 |
| SRC-U-008 | 用户消息，2026-06-10 | 补充要求需求文档更加具体，闭环需要说明闭环中的具体细节。 | 已确认 | BR-G-08, AC-G-08, F001, F003, D-008 | 约束业务闭环必须用典型场景说明触发条件、命令顺序、数据读写、输出证据和下一步。 |
| SRC-U-009 | 用户消息，2026-06-10 | 澄清不是做抽象编号拆分，而是要具体说明细节，并给出一些场景例子。 | 已确认 | BR-G-08, AC-G-08, F001, F002, F003, D-009 | 约束每个需求点都要补具体场景、示例输入输出和验收关注点。 |

## 2. 本地需求文档

| 编号 | 路径 | 内容摘要 | 适用范围 | 可信度 | 可追踪到 |
| --- | --- | --- | --- | --- | --- |
| SRC-D-001 | `README.md` | NeoDev SP 定位为 AI 软件工程一人团队工作台，提供后端服务、CLI、图谱解析器、插件和部署资产。 | 产品定位与 CLI/插件关系 | 高 | R-001, R-003 |
| SRC-D-002 | `plugins/neodev-rd-knowledge/workflows/core-workflows.json` | 已定义 session check、version navigation、repository auto graph、document import、DocChange、commit routing、pre-push、graph refresh、browser acceptance 等工作流。 | 工作流聚合依据 | 高 | F001, F003 |
| SRC-D-003 | `plugins/neodev-rd-knowledge/skills/neodev-rd-knowledge/SKILL.md` | 要求本地 `neodev` CLI 是事实读写边界，状态变更前先检查 config 和 version-check，post-push 自动更新由原子命令处理。 | CLI 边界与 Agent 行为约束 | 高 | R-002, F002, F003 |
| SRC-D-004 | `docs/requirements/agent-post-push-graph-update/01-master-prd.md` | post-push 流程已把多个原子动作收口成一个服务端原子写命令。 | 命令聚合先例 | 高 | F001, F003 |

## 3. 代码事实

| 编号 | 路径 | 事实摘要 | 推断限制 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-C-001 | `src/service/cli/commands/product.py` | 注册 `product create/update/show`、`product version create/show/bind-branch/unbind-branch/link-code/code-facts` 等产品版本命令。 | 代码事实不等同于最终用户入口。 | F001, F002 |
| SRC-C-002 | `src/service/cli/commands/project.py` | 注册 `project create/show/refresh-graph/init-status`。 | `setup repo` 可复用这些命令。 | F001 |
| SRC-C-003 | `src/service/cli/commands/doc.py` | 注册 `doc binding create/list/switch`、`doc scan/import`、`doc graph show`、`doc change register/show/mark-implemented`。 | `docs sync` 与 `change start` 可复用这些命令。 | F001 |
| SRC-C-004 | `src/service/cli/commands/graph.py` | 注册 `graph impact/entity-context/get-chain` 以及手工 graph type/node/edge 管理命令。 | 手工图谱命令偏高级/维护入口。 | F001, F002 |
| SRC-C-005 | `src/service/cli/commands/git.py` | 注册 `git verify-doc-change`、`git post-push-graph-update`、`git dangerous-commit list/resolve`。 | `post-push-graph-update` 更适合作为内部 hook 入口。 | F002, F003 |
| SRC-C-006 | `plugins/neodev-rd-knowledge/hooks/hooks.json` | 配置 SessionStart、PreToolUse 和 PostToolUse hooks；push 成功后自动运行 `post_push_graph_update.py --json`。 | hook 行为需保持可审计。 | F003 |
| SRC-C-007 | `plugins/neodev-rd-knowledge/.codex-plugin/plugin.json` | shared scripts 包含文档校验、DocChange trailer、环境检查、commit scope、post-push update 和 session hint。 | 插件 manifest 是当前可见能力来源。 | F002, F003 |

## 4. 接口与数据事实

| 编号 | 路径/接口/表 | 事实摘要 | 推断限制 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-A-001 | `neodev config show` | 本地配置检查可返回 `server_url` 和 `config_path`。 | 本次运行成功，但不代表所有用户环境均可用。 | F001, F003 |
| SRC-A-002 | `neodev cli version-check --json` | CLI 兼容检查是高风险/状态变更前置检查。 | 本次运行发生超时，需在实现阶段考虑超时提示。 | F001, F003, EX-F001-01 |
| SRC-A-003 | `/api/cli/execute` | 本地 CLI shim 可把命令转发到远程 API 服务执行。 | 高层命令仍应保持 CLI/API 契约一致。 | F001, F002 |

## 5. 测试与验收材料

| 编号 | 路径 | 内容摘要 | 适用范围 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-T-001 | `tests/test_cli_contract.py` | 覆盖 CLI 注册命令契约。 | 新增高层命令需补充注册与输出契约测试。 | TC-F001-01, TC-F002-01 |
| SRC-T-002 | `tests/test_cli_remote_execution.py` | 覆盖远程 CLI execute 契约。 | 高层命令若支持远程执行需补充转发测试。 | TC-F001-02 |
| SRC-T-003 | `tests/test_git_cli.py` | 覆盖 Git DocChange 和 dangerous commit CLI。 | `git check` 聚合入口需复用现有事实。 | TC-F001-04, TC-F003-02 |
| SRC-T-004 | `tests/test_post_push_graph_update.py` | 覆盖 push 后脚本范围解析、分类、原子 CLI 调用和结果持久化。 | Agent 路由收口不应破坏当前 hook。 | TC-F003-03 |

## 6. 事实结论

- 命令数量多来自必要原子能力，而非全部都应作为日常主入口暴露。（SRC-C-001 至 SRC-C-005）
- 已有 workflow 配置和 post-push 原子命令证明“高层入口聚合底层命令”是当前架构可接受方向。（SRC-D-002, SRC-D-004）
- 简化策略应优先新增高层入口、隐藏高级/内部命令、保留底层兼容，而不是删除既有命令；高层入口命名已确认采用 `doctor/context/setup/docs/change/git/status` 这组顶层路径。（SRC-U-004, SRC-U-005, SRC-D-003）
- Agent 插件默认命令说明和 prompts 也应同步收口，否则即使 CLI 简化，Agent 仍可能直接选择原子命令；插件命令说明已确认收口为 context/docs/change/submit 四个意图入口。（SRC-U-005, SRC-C-006, SRC-C-007）
- 每个高层命令都必须能说明操作与数据闭环：输入从哪里来、读写哪些 NeoDev 事实、输出哪些证据、下一步进入哪个命令，以及失败后如何恢复。（SRC-U-006）
- 高层命令集合必须形成业务闭环：从环境与上下文确认开始，经仓库接入、文档同步、变更启动、影响分析、提交检查、push 后状态回看，再回到上下文/状态确认。（SRC-U-007）
- 业务闭环和其他需求点都必须用具体场景说明，至少包含触发条件、命令顺序、数据读写、输出证据、下一步动作和验收关注点。（SRC-U-008, SRC-U-009）

## 关联文档

- [[requirements/cli-command-simplification/README|CLI 命令简化 PRD 产物索引]]
- [[requirements/cli-command-simplification/01-master-prd|CLI 命令简化总 PRD]]
- [[requirements/cli-command-simplification/99-open-questions|CLI 命令简化待确认问题]]
