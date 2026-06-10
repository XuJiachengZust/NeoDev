---

doc_id: NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-OPEN-QUESTIONS
title: Agent Push 后图谱更新待确认问题
aliases:

- Agent Push 后图谱更新待确认问题
tags:
- neodev/docs
- neodev/prd
- neodev/requirements
- requirements/agent-post-push-graph-update
created: 2026-05-13
updated: 2026-05-13
related:
- '[[README|Agent Push 后图谱更新 PRD 产物索引]]'
- '[[00-source-index|Agent Push 后图谱更新事实源索引]]'
- '[[01-master-prd|Agent Push 后图谱更新总 PRD]]'
- '[[features/F001-post-push-orchestration|F001 Push 后编排 Hook PRD]]'
- '[[features/F002-commit-scope-routing|F002 提交范围分类路由 PRD]]'
- '[[features/F003-docchange-code-linking|F003 DocChange 与代码关联 PRD]]'
- '[[features/F004-skill-behavior-protocol|F004 Skill 行为协议 PRD]]'
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-README
  - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-SOURCE-INDEX
  - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-MASTER-PRD
  - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F001-POST-PUSH-ORCHESTRATION
  - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F002-COMMIT-SCOPE-ROUTING
  - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F003-DOCCHANGE-CODE-LINKING
  - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F004-SKILL-BEHAVIOR-PROTOCOL

---

# Agent Push 后图谱更新待确认问题

## 1. 阻塞问题


| 问题编号 | 当前已知事实                 | 问题                  | 需要确认的选项/开放点 | 类型  | 影响章节/范围 | 阻塞原因 | 建议确认人 | 状态  |
| ---- | ---------------------- | ------------------- | ----------- | --- | ------- | ---- | ----- | --- |
| 无    | 用户已确认 Q101-Q107 的处理策略。 | 当前没有阻塞 PRD 继续细化的问题。 | 不适用         | 范围  | 不适用     | 不适用  | 不适用   | 不适用 |


## 2. 非阻塞问题


| 问题编号 | 当前已知事实                          | 问题               | 需要确认的选项/开放点 | 类型  | 影响章节/范围 | 默认处理方式 | 建议确认人 | 状态  |
| ---- | ------------------------------- | ---------------- | ----------- | --- | ------- | ------ | ----- | --- |
| 无    | Q101-Q107 均已由用户在 2026-05-13 确认。 | 当前没有保留的非阻塞待确认问题。 | 不适用         | 不适用 | 不适用     | 不适用    | 不适用   | 不适用 |


## 3. 已确认问题记录


| 问题编号  | 确认结论                                                                           | 确认人/来源                     | 确认时间       | 已更新文档位置                                         |
| ----- | ------------------------------------------------------------------------------ | -------------------------- | ---------- | ----------------------------------------------- |
| D-001 | 后置操作触发点为 push 成功之后，不是本地 commit 成功之后。                                           | 用户消息                       | 2026-05-13 | `01-master-prd.md` 2、6；F001                     |
| D-002 | 本期只在 Agent 插件层面做，不覆盖普通终端或 IDE 原生 Git push。                                     | 用户消息                       | 2026-05-13 | `01-master-prd.md` 2、3、6；F001                   |
| D-003 | 可以改造现有 `PostToolUse` 的 `Bash(git push *)` hook；当前只做提醒，需升级为自动执行。                | 用户消息 + SRC-C-001           | 2026-05-13 | `01-master-prd.md` 2；F001                       |
| D-004 | 采用“hook 调用确定性脚本、脚本调用 NeoDev CLI、skill 规范 Agent 结果解读与补救”的分层方案；Skill 不承担核心写入和刷新。 | 用户消息 + SRC-D-006           | 2026-05-13 | `01-master-prd.md` 2、6；F001；F004                |
| D-005 | Q101：Agent/脚本自己从本地获取 push 范围、project、branch 等上下文。                              | 用户消息 SRC-U-007             | 2026-05-13 | `01-master-prd.md` 3、6、11；F001；F002             |
| D-006 | Q102：需要持久化；运行历史追加记录，同一业务键的最新有效状态覆盖更新。                                          | 用户消息 SRC-U-007             | 2026-05-13 | `01-master-prd.md` 2、4、6、10；F001；F003；F004      |
| D-007 | Q103：不做额外权限。                                                                   | 用户消息 SRC-U-007             | 2026-05-13 | `01-master-prd.md` 3、9；F004                     |
| D-008 | Q104：脚本参数只能选择本地可以直接获取或控制执行形态的值；Hook 不传远端业务参数。                                  | 用户消息 SRC-U-007             | 2026-05-13 | `01-master-prd.md` 3、6、11；F001                  |
| D-009 | Q105：选择 C，document-only push 自动执行 `doc import` 后登记 DocChange。                  | 用户消息 SRC-U-007 + SRC-C-013 | 2026-05-13 | `01-master-prd.md` 2、3、6、10；F002                |
| D-010 | Q106：失败需要全部回滚，保持原子性。                                                           | 用户消息 SRC-U-007             | 2026-05-13 | `01-master-prd.md` 2、3、6、10；F001；F002；F003；F004 |
| D-011 | Q107：选择 B，扩展现有 `neodev-rd-knowledge` skill。                                    | 用户消息 SRC-U-007             | 2026-05-13 | `01-master-prd.md` 2、3、6；F001；F004              |


## 4. 关闭问题对照


| 原问题编号 | 原问题摘要                                     | 关闭状态 | 决策编号  |
| ----- | ----------------------------------------- | ---- | ----- |
| Q-101 | push 成功后如何稳定取得本次 push 范围、project 和 branch | 已关闭  | D-005 |
| Q-102 | 是否需要持久化运行记录，以及重复触发如何去重                    | 已关闭  | D-006 |
| Q-103 | 是否需要额外权限或数据可见性规则                          | 已关闭  | D-007 |
| Q-104 | 后置脚本标准文件名和调用参数是什么                         | 已关闭  | D-008 |
| Q-105 | document-only push 后是否自动导入和登记 DocChange   | 已关闭  | D-009 |
| Q-106 | 关联失败和图谱刷新失败之间的继续策略                        | 已关闭  | D-010 |
| Q-107 | 后置处理 skill 的标准名称、触发描述和安装位置                | 已关闭  | D-011 |
