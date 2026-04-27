---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-FEATURES-F003-GIT-CONSISTENCY-AND-RISK-CONTROL
title: "F003 Git 一致性、危险提交与推送后刷新 PRD"
aliases:
  - "F003 Git 一致性、危险提交与推送后刷新 PRD"
tags:
  - neodev/docs
  - neodev/prd
  - neodev/requirements
created: 2026-04-27
updated: 2026-04-27
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
  - "[[01-master-prd]]"
---
# F003 Git 一致性、危险提交与推送后刷新 PRD

## 1. 基本信息

| 项 | 值 |
| --- | --- |
| 功能 ID | F003 |
| 优先级 | P0 |
| 对应总 PRD | [../01-master-prd.md](../01-master-prd.md) |
| 关键来源 | SRC-U-005, SRC-U-006, SRC-U-007, SRC-U-015, SRC-U-017, SRC-U-018, SRC-C-002, SRC-C-004 |

## 2. 功能目标

F003 负责在 Git 提交和推送环节维持文档与代码的一致性，并定义推送后的最小刷新闭环：

- 推送前校验 `DocChange-ID`
- 回写 `CodeChangeLink` 和 `DocChange` 状态
- 危险提交登记与关闭
- 推送后刷新受影响代码节点、链路和 结构化描述

这部分默认由插件/skill 引导用户执行，但真正的校验、状态回写、风险登记和刷新动作都必须落在 CLI。

## 3. 分层规则

### 3.1 插件 / Skill 负责

- 提醒用户在提交前执行校验
- 对危险提交做风险说明和继续确认
- 在推送成功后提醒或自动编排 `git post-push-refresh`
- 解释推送后刷新结果

### 3.2 CLI 负责

- 校验 `DocChange-ID`
- 创建 `CodeChangeLink`
- 回写 `DocChange` 状态
- 创建或关闭 `DangerousCommitRecord`
- 推送后刷新代码节点、链路和 结构化描述

## 4. 用户故事

| ID | 用户故事 |
| --- | --- |
| US-F003-01 | 开发者在提交代码时可以通过 CLI 校验 `DocChange-ID` |
| US-F003-02 | 研发负责人可以人工确认 `implemented` |
| US-F003-03 | 危险提交发生时系统可以登记风险记录 |
| US-F003-04 | 代码推送完成后，系统可以基于提交范围刷新受影响代码节点和 结构化描述 |

## 5. CLI 能力

| 命令 | 说明 |
| --- | --- |
| `git verify-doc-change` | 供 pre-push / 本地工具调用进行校验 |
| `doc change mark-implemented` | 人工确认 `implemented` |
| `git dangerous-commit resolve` | 关闭危险提交记录 |
| `git post-push-refresh` | 按 commit 或分支触发推送后图谱和 结构化描述刷新 |

## 6. 业务规则

| ID | 规则 | 验收 |
| --- | --- | --- |
| BR-F003-01 | Git 提交统一使用 trailer `DocChange-ID: <doc_change_id>` | AC-F003-01 |
| BR-F003-02 | 推送前校验必须解析并校验 `DocChange-ID` | AC-F003-01 |
| BR-F003-03 | 校验通过后必须创建 `CodeChangeLink`，并将 `DocChange` 置为 `in_implementation` | AC-F003-02 |
| BR-F003-04 | `implemented` 只能通过人工确认进入 | AC-F003-02 |
| BR-F003-05 | 危险提交二次确认放行时必须创建 `DangerousCommitRecord` | AC-F003-03 |
| BR-F003-06 | 危险提交解决时必须记录 `resolved_by` 和 `resolved_at` | AC-F003-03 |
| BR-F003-07 | 推送后必须支持按 commit 或分支触发图谱刷新和 结构化描述刷新 | AC-F003-04 |
| BR-F003-08 | 推送后刷新应优先以受影响 commit、文件和节点为范围，而非默认全库刷新 | AC-F003-04 |

## 7. 核心流程

1. 开发者执行 `git push`。
2. 插件/skill 引导执行 `git verify-doc-change`。
3. CLI 解析 commit message 中的 `DocChange-ID`。
4. CLI 校验 `DocChange-ID` 是否存在且可用。
5. 校验通过后：
   - 创建 `CodeChangeLink`
   - 将 `DocChange` 更新为 `in_implementation`
6. 如遇危险场景：
   - 插件/skill 解释风险并获取二次确认
   - CLI 创建 `DangerousCommitRecord`
7. 推送成功后执行 `git post-push-refresh`：
   - 同步对应分支 commits
   - 更新受影响代码节点和关系链路
   - 刷新受影响节点的 结构化描述与 embedding
8. 后续通过 `doc change mark-implemented` 人工确认 `implemented`。

## 8. 数据字段

| 字段 | 说明 |
| --- | --- |
| `DocChange-ID` | Git trailer 字段 |
| `commit_sha` | 代码提交 SHA |
| `verification_status` | `verified / rejected / risky` |
| `resolved_by` | 危险提交解决人 |
| `resolved_at` | 危险提交解决时间 |
| `refresh_scope` | 推送后刷新范围 |
| `graph_nodes_updated` | 刷新后的节点数量 |
| `index_descriptions_updated` | 刷新的 结构化描述数量 |

## 9. 异常处理

| ID | 场景 | 处理 |
| --- | --- | --- |
| EX-F003-01 | 提交缺少 `DocChange-ID` | 拒绝或按策略提示危险提交 |
| EX-F003-02 | `DocChange-ID` 不存在 | 拒绝推送 |
| EX-F003-03 | `DocChange` 已关闭且不允许关联 | 拒绝推送 |
| EX-F003-04 | 推送后刷新失败 | 记录失败结果并返回可重试信息 |

## 10. 验收标准

| ID | 前置条件 | 操作 | 预期结果 |
| --- | --- | --- | --- |
| AC-F003-01 | 代码提交包含合法 `DocChange-ID` trailer | 执行校验 | 成功解析并校验 `DocChange-ID` |
| AC-F003-02 | 校验通过且存在合法引用 | 执行推送前校验 | 创建 `CodeChangeLink` 并将 `DocChange` 置为 `in_implementation`，后续人工确认 `implemented` |
| AC-F003-03 | 危险提交被二次确认放行 | 继续处理 | 创建 `DangerousCommitRecord` 并在解决时记录 `resolved_by`/`resolved_at` |
| AC-F003-04 | 推送成功且存在新增 commit | 执行 `git post-push-refresh` | 受影响代码节点、关系链路及 结构化描述被刷新 |

## 11. 测试场景

| ID | 优先级 | 场景 |
| --- | --- | --- |
| TC-F003-01 | P0 | 合法 `DocChange-ID` trailer 的校验 |
| TC-F003-02 | P0 | 校验通过后将 DocChange 置为 `in_implementation` |
| TC-F003-03 | P0 | 危险提交登记 |
| TC-F003-04 | P1 | 危险提交解决时记录 `resolved_by` 和 `resolved_at` |
| TC-F003-05 | P0 | 推送成功后按 commit 范围刷新代码节点和 结构化描述 |
