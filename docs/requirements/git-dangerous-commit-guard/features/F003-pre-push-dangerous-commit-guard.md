---
doc_id: NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F003-PRE-PUSH-DANGEROUS-COMMIT-GUARD
title: F003 推送前危险提交守卫 PRD
aliases:
- F003 推送前危险提交守卫 PRD
tags:
- neodev/docs
- neodev/prd
- neodev/requirements
- requirements/git-dangerous-commit-guard
created: 2026-05-11
updated: 2026-05-11
related:
- '[[01-master-prd|Git 危险提交守卫总 PRD]]'
- '[[00-source-index|Git 危险提交守卫事实源索引]]'
- '[[features/F001-auto-git-guard-setup|F001 自动配置 Git 守卫 PRD]]'
- '[[features/F002-commit-message-guard|F002 提交消息守卫 PRD]]'
- '[[99-open-questions|Git 危险提交守卫待确认问题]]'
doc_type: prd
product_key: NEODEV
status: draft
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-MASTER-PRD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-SOURCE-INDEX
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F001-AUTO-GIT-GUARD-SETUP
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F002-COMMIT-MESSAGE-GUARD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-OPEN-QUESTIONS
---

# F003 推送前危险提交守卫 PRD

## 1. 功能信息

| 项 | 内容 |
| --- | --- |
| 功能编号 | F003 |
| 功能名称 | 推送前危险提交守卫 |
| 优先级 | P0 |
| 状态 | 草稿，核心口径已确认 |
| 所属总 PRD | `../01-master-prd.md` |

## 2. 引用业务口径

| 类型 | 编号 | 名称 | 来源章节 |
| --- | --- | --- | --- |
| 业务对象 | BO-003 | RepositoryHook | 总 PRD 4.1 |
| 业务对象 | BO-005 | DangerousCommitRecord | 总 PRD 4.1 |
| 术语 | T-004 | 危险提交漏报 | 总 PRD 4.3 |
| 规则 | BR-G-06 | `verify-doc-change` 失败路径必须创建危险提交记录 | 总 PRD 6 |

## 3. 功能目标

F003 在 Git `pre-push` 阶段读取本次推送的 commit range，对范围内代码提交逐一执行 `neodev git verify-doc-change`。校验失败时必须阻止 push，并确保服务端登记 open 状态危险提交记录，使 `neodev git dangerous-commit list` 能查询到该提交。（SRC-U-001, SRC-D-003, SRC-C-001, SRC-C-002, SRC-A-001）

## 4. 用户故事

| 场景编号 | 用户角色 | 场景描述 | 业务价值 | 来源编号 |
| --- | --- | --- | --- | --- |
| US-F003-01 | U-001 开发者 | 本地已有缺少 `DocChange-ID` 的提交 | push 前被扫描并阻止 | SRC-U-001 |
| US-F003-02 | U-003 研发负责人 | 查询危险提交列表 | 能看到 open 状态记录 | SRC-D-003 |
| US-F003-03 | U-002 插件使用者 | Agent 执行 `git push` | 工具层 hook 先确保守卫安装，仓库级 hook 执行真实校验 | SRC-A-003 |

## 5. 入口与交互

| 入口编号 | 入口 | 输入 | 成功反馈 | 失败反馈 |
| --- | --- | --- | --- | --- |
| EN-F003-01 | `.git/hooks/pre-push` | Git 通过 stdin 传入的 local/remote refs | 允许 push 继续 | 输出失败 commit、原因和 dangerous record 信息并返回非 0 |
| EN-F003-02 | `neodev git verify-doc-change` | project id、branch、commit sha、commit message | 返回 verified | 返回错误并登记危险提交 |
| EN-F003-03 | `neodev git dangerous-commit list` | project id | 返回 open 危险提交 | 无记录时 count 为 0 |

## 6. 业务规则

| 规则编号 | 规则内容 | 关联 AC | 来源编号 |
| --- | --- | --- | --- |
| BR-F003-01 | `pre-push` 必须按 Git stdin 计算本次推送 commit range，不能只检查 HEAD。 | AC-F003-01 | SRC-A-001 |
| BR-F003-02 | 每个代码提交必须调用服务端 `git verify-doc-change` 做最终事实校验。 | AC-F003-02 | SRC-D-002 |
| BR-F003-03 | 缺失、重复、非法、未知或已 implemented 的 `DocChange-ID` 都必须阻止 push。 | AC-F003-03 | SRC-U-001, SRC-C-001 |
| BR-F003-04 | `verify-doc-change` 失败路径必须创建或复用 open 状态危险提交记录。 | AC-F003-04 | SRC-C-001, SRC-C-002 |
| BR-F003-05 | 危险提交记录创建必须幂等，重复 push 不应生成多条同一 project/branch/commit 的 open 记录。 | AC-F003-05 | SRC-D-003 |

## 7. 验收标准

| AC 编号 | Given | When | Then | 覆盖规则 |
| --- | --- | --- | --- | --- |
| AC-F003-01 | 分支有多个待推送提交 | 执行 push | `pre-push` 检查完整 commit range | BR-F003-01 |
| AC-F003-02 | 提交带合法 `DocChange-ID` 且 DocChange 存在 | 执行 push | `verify-doc-change` 通过，push 可继续 | BR-F003-02 |
| AC-F003-03 | 提交缺少 `DocChange-ID` | 执行 push | push 被阻止 | BR-F003-03 |
| AC-F003-04 | `verify-doc-change` 失败 | 查询 dangerous commit list | 可看到 open 状态危险提交记录 | BR-F003-04 |
| AC-F003-05 | 同一坏提交重复 push | 查询 dangerous commit list | 不重复生成 open 记录 | BR-F003-05 |

## 8. 测试场景建议

| 测试编号 | 优先级 | 场景 | 预期结果 |
| --- | --- | --- | --- |
| TC-F003-01 | P0 | pre-push 解析单分支推送范围 | 检查范围内提交 |
| TC-F003-02 | P0 | pre-push 解析多 ref 推送范围 | 每个 ref 范围都被检查 |
| TC-F003-03 | P0 | 缺少 `DocChange-ID` 的提交 | 阻止 push 并登记危险提交 |
| TC-F003-04 | P0 | 未知 DocChange | 阻止 push 并登记危险提交 |
| TC-F003-05 | P0 | 重复 push 同一坏提交 | dangerous record 幂等 |

## 关联文档
- [[01-master-prd|Git 危险提交守卫总 PRD]]
- [[00-source-index|Git 危险提交守卫事实源索引]]
- [[features/F001-auto-git-guard-setup|F001 自动配置 Git 守卫 PRD]]
- [[features/F002-commit-message-guard|F002 提交消息守卫 PRD]]
- [[99-open-questions|Git 危险提交守卫待确认问题]]
