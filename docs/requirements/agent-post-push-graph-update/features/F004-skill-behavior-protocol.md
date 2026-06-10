---
doc_id: NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F004-SKILL-BEHAVIOR-PROTOCOL
title: F004 Skill 行为协议 PRD
aliases:
  - F004 Skill 行为协议 PRD
tags:
  - neodev/docs
  - neodev/prd
  - neodev/requirements
  - requirements/agent-post-push-graph-update
created: 2026-05-13
updated: 2026-05-13
related:
  - '[[01-master-prd|Agent Push 后图谱更新总 PRD]]'
  - '[[00-source-index|Agent Push 后图谱更新事实源索引]]'
  - '[[F001-post-push-orchestration|F001 Push 后编排 Hook PRD]]'
  - '[[F002-commit-scope-routing|F002 提交范围分类路由 PRD]]'
  - '[[F003-docchange-code-linking|F003 DocChange 与代码关联 PRD]]'
  - '[[99-open-questions|Agent Push 后图谱更新待确认问题]]'
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-MASTER-PRD
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-SOURCE-INDEX
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F001-POST-PUSH-ORCHESTRATION
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F002-COMMIT-SCOPE-ROUTING
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F003-DOCCHANGE-CODE-LINKING
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-OPEN-QUESTIONS
---

# F004 Skill 行为协议 PRD

## 1. 功能信息

| 项 | 内容 |
| --- | --- |
| 功能编号 | F004 |
| 功能名称 | Skill 行为协议 |
| 优先级 | P0 |
| 状态 | 已定稿，Q107 已关闭 |
| 所属总 PRD | `../01-master-prd.md` |
| 主要事实源 | SRC-U-006, SRC-U-007, SRC-D-006, SRC-C-001, SRC-A-005 |

## 2. 引用业务口径

| 类型 | 编号 | 名称 | 来源章节 | 来源编号 |
| --- | --- | --- | --- | --- |
| 业务对象 | BO-007 | AgentPostPushSkill | 总 PRD 4 | SRC-U-006, SRC-U-007 |
| 业务对象 | BO-008 | PostPushRunRecord | 总 PRD 4 | SRC-U-007 |
| 术语 | T-005 | 后置处理 Skill | 总 PRD 4 | SRC-U-006, SRC-U-007 |
| 术语 | T-006 | 追加覆盖 | 总 PRD 4 | SRC-U-007 |
| 跨功能规则 | BR-G-07 | 固定流程脚本化，skill 只做收口 | 总 PRD 6 | SRC-U-006, SRC-D-006 |
| 跨功能规则 | BR-G-08 | 持久化追加覆盖 | 总 PRD 6 | SRC-U-007 |
| 跨功能规则 | BR-G-10 | 原子性与失败回滚 | 总 PRD 6 | SRC-U-007 |

## 3. 功能目标

F004 定义扩展现有 `neodev-rd-knowledge` skill 的 Agent 行为协议。该 skill 不是核心执行器，不直接写库、不直接刷新图谱、不自行重组复杂 CLI 命令；它指导 Agent 读取后置脚本 JSON，判断成功、失败、回滚、持久化和待补救状态，并用稳定口径向用户汇报。（SRC-U-006, SRC-U-007, SRC-D-006）

固定流程由 F001 的插件脚本调用 NeoDev CLI 完成。Skill 的价值在于把 Agent 在 push 后的固定解释、复核、补救和汇报行为封装起来，降低 Agent 临场发挥导致的误操作风险。（SRC-U-006, SRC-D-006）

## 4. 用户故事与场景

| 场景编号 | 用户角色 | 场景描述 | 业务价值 | 来源编号 |
| --- | --- | --- | --- | --- |
| US-F004-01 | U-001 Agent 插件使用者 | push 后脚本输出 JSON，Agent 自动使用 `neodev-rd-knowledge` skill 解读并汇报 | 用户无需阅读原始 JSON 即可了解后置状态 | SRC-U-006, SRC-U-007 |
| US-F004-02 | U-002 研发负责人 | 关联、文档导入或图谱刷新失败时，Agent 给出明确失败阶段、回滚结果和重试命令 | 失败可定位，可复现，可补救 | SRC-A-005, SRC-U-007 |
| US-F004-03 | U-001 Agent 插件使用者 | 脚本输出 document-only 或 mixed 结果时，Agent 按规则提示下一步 | 避免错误创建文档-代码关联或保留部分成功状态 | SRC-U-002, SRC-U-007 |

## 5. 前置条件

- F001 后置脚本能够输出 JSON 结果，且至少包含 `hook_status`、`classification_summary`、`doc_import_results`、`docchange_register_results`、`docchange_link_results`、`graph_refresh_result`、`run_record`、`rollback_status`、`errors`、`skill_hint`。（SRC-A-005, SRC-U-007）
- Skill 协议扩展到现有 `neodev-rd-knowledge` skill 中；不新增独立 skill 名称。（SRC-U-007）
- 任何核心写入、关联、文档导入、图谱刷新和持久化均已由脚本通过 NeoDev CLI 完成、回滚或明确失败。（SRC-U-006, SRC-U-007）

## 6. 入口与触发

| 入口编号 | 能力入口 | 触发方式 | 到达结果 | 来源编号 |
| --- | --- | --- | --- | --- |
| EN-F004-01 | 脚本输出 `skill_hint` | F001 脚本返回 JSON 后，Agent 读取 `skill_hint.skill=neodev-rd-knowledge` | Agent 使用本 skill 扩展协议解读结果 | SRC-U-006, SRC-U-007 |
| EN-F004-02 | 用户或 Agent 显式要求处理 post-push 结果 | 用户粘贴或引用后置脚本 JSON | Agent 按本 skill 给出汇报和补救建议 | SRC-U-006 |

## 7. 行为协议

| 协议编号 | 行为 | 规则 | 输入 | 输出 | 来源编号 |
| --- | --- | --- | --- | --- | --- |
| BP-F004-01 | 读取结果 | 优先读取脚本 JSON；不得凭空推断成功 | `hook_status`, `errors` | 后置流程总状态 | SRC-A-005 |
| BP-F004-02 | 分类汇报 | 分别汇报 document/code/mixed/empty 计数和处理动作 | `classification_summary` | 分类摘要 | SRC-U-002 |
| BP-F004-03 | 文档汇报 | 汇报 document-only 的 doc import 和 doc change register 结果 | `doc_import_results`, `docchange_register_results` | 文档后置摘要 | SRC-U-007, SRC-C-013 |
| BP-F004-04 | 关联汇报 | 对每个 code commit 汇报 DocChange 关联成功、回滚或失败 | `docchange_link_results` | 关联摘要 | SRC-U-003, SRC-U-007 |
| BP-F004-05 | 图谱汇报 | 汇报 `project refresh-graph` 的状态、graph_id、head_commit、节点边数量或回滚结果 | `graph_refresh_result` | 图谱刷新摘要 | SRC-A-002, SRC-U-007 |
| BP-F004-06 | 持久化汇报 | 汇报运行历史追加和最新状态覆盖结果 | `run_record` | 持久化摘要 | SRC-U-007 |
| BP-F004-07 | 回滚汇报 | 任一核心步骤失败时，优先汇报 rollback_status；若 rollback_failed，必须提示人工介入风险 | `rollback_status`, `errors` | 回滚摘要 | SRC-U-007 |
| BP-F004-08 | 失败补救 | 只建议执行同一脚本的重试/诊断参数或已存在 NeoDev CLI，不拼接未定义写库命令 | `errors`, `retry_command` | 补救建议 | SRC-U-006, SRC-D-006 |
| BP-F004-09 | 边界保护 | 不直接把 DocChange 标记为 `implemented`，不直接写 PostgreSQL 或 Neo4j，不新增权限假设 | 全量结果 | 边界提示 | SRC-C-011, SRC-U-007 |

## 8. 脚本 JSON 候选结构

```json
{
  "hook_status": "success | failed | rolled_back | skipped | not_ready",
  "project": {
    "project_id": "string",
    "project_name": "string",
    "branch": "string",
    "source": "local"
  },
  "classification_summary": {
    "document": 0,
    "code": 0,
    "mixed": 0,
    "empty": 0
  },
  "doc_import_results": [],
  "docchange_register_results": [],
  "docchange_link_results": [],
  "graph_refresh_result": {
    "status": "completed | rolled_back | failed | skipped",
    "graph_id": "string",
    "head_commit": "string",
    "node_count": 0,
    "edge_count": 0
  },
  "run_record": {
    "persistence_mode": "append_history+overwrite_latest",
    "run_id": "string",
    "latest_status": "completed | rolled_back | failed"
  },
  "rollback_status": "not_needed | rolled_back | rollback_failed",
  "errors": [],
  "skill_hint": {
    "skill": "neodev-rd-knowledge",
    "action": "interpret_post_push_result"
  }
}
```

字段缺失时，Skill 必须明确提示 `invalid_result`，不得把未知结果解释成成功。（SRC-U-007）

## 9. 异常与边界场景

| 场景编号 | 场景 | 处理规则 | 用户反馈 | 关联 AC | 来源编号 |
| --- | --- | --- | --- | --- | --- |
| EX-F004-01 | JSON 缺少关键字段 | 标记 invalid_result，不推断成功 | 提示重新运行脚本并附原始错误 | AC-F004-01 | SRC-U-007 |
| EX-F004-02 | 任一核心步骤失败且已回滚 | 汇报失败阶段和 rolled_back，不保留部分成功措辞 | 说明业务写入已回滚 | AC-F004-03 | SRC-U-007 |
| EX-F004-03 | 回滚失败 | 标记 rollback_failed，提示人工介入，不继续自动补救 | 输出高风险摘要 | AC-F004-04 | SRC-U-007 |
| EX-F004-04 | skill_hint 指向非 `neodev-rd-knowledge` | 标记 skill_hint mismatch | 提示实现应扩展现有 skill | AC-F004-05 | SRC-U-007 |

## 10. 验收标准

| AC 编号 | Given | When | Then | 覆盖协议 | 来源编号 |
| --- | --- | --- | --- | --- | --- |
| AC-F004-01 | 脚本输出完整 JSON | Agent 使用本 skill | Agent 汇报总状态、分类、文档导入、关联、图谱刷新、持久化、回滚和错误摘要 | BP-F004-01, BP-F004-02 | SRC-A-005 |
| AC-F004-02 | JSON 中存在 `skill_hint` | Agent 处理结果 | skill_hint 指向现有 `neodev-rd-knowledge` skill | BP-F004-01 | SRC-U-007 |
| AC-F004-03 | 核心步骤失败且回滚成功 | Agent 汇报结果 | 输出失败阶段与 rolled_back，不误报部分成功 | BP-F004-07 | SRC-U-007 |
| AC-F004-04 | 回滚失败 | Agent 汇报结果 | 输出 rollback_failed 和人工介入风险 | BP-F004-07 | SRC-U-007 |
| AC-F004-05 | 需要补救 | Agent 给出下一步 | 补救动作只使用脚本或已存在 NeoDev CLI，不直接写库或新增权限 | BP-F004-08, BP-F004-09 | SRC-U-006, SRC-U-007 |

## 11. 测试场景建议

| 测试编号 | 优先级 | 场景 | 前置条件 | 操作 | 预期结果 | 覆盖 AC |
| --- | --- | --- | --- | --- | --- | --- |
| TC-F004-01 | P0 | 成功 JSON 解读 | 准备包含分类、文档、关联、刷新和持久化成功的 JSON | 使用 skill 解释结果 | 输出成功摘要并列出关键计数 | AC-F004-01 |
| TC-F004-02 | P0 | 失败回滚 JSON 解读 | 准备 graph refresh 失败且 rolled_back 的 JSON | 使用 skill 解释结果 | 输出失败阶段和回滚成功，不保留部分成功措辞 | AC-F004-03 |
| TC-F004-03 | P0 | 回滚失败 JSON 解读 | 准备 rollback_failed JSON | 使用 skill 解释结果 | 输出人工介入风险 | AC-F004-04 |
| TC-F004-04 | P1 | skill_hint 检查 | 准备 skill_hint 指向其他 skill 的 JSON | 使用 skill 解释结果 | 输出 skill_hint mismatch | AC-F004-02 |

## 12. 关联需求与依赖

- 依赖 F001 输出稳定的后置脚本 JSON 和 `skill_hint`。
- 依赖 F002 的分类、文档导入与 DocChange 登记结果。
- 依赖 F003 的 DocChange 关联结果。
- 依赖现有 `neodev-rd-knowledge` skill 作为扩展载体。

## 13. 待确认问题

| 问题编号 | 状态 | 确认结论 | 来源 |
| --- | --- | --- | --- |
| Q-107 | 已关闭 | 选择 B：扩展现有 `neodev-rd-knowledge` skill。 | SRC-U-007 |
