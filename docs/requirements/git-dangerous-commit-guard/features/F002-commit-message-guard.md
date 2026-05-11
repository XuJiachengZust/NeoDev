---
doc_id: NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F002-COMMIT-MESSAGE-GUARD
title: F002 提交消息守卫 PRD
aliases:
- F002 提交消息守卫 PRD
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
- '[[features/F003-pre-push-dangerous-commit-guard|F003 推送前危险提交守卫 PRD]]'
- '[[99-open-questions|Git 危险提交守卫待确认问题]]'
doc_type: prd
product_key: NEODEV
status: draft
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-MASTER-PRD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-SOURCE-INDEX
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F001-AUTO-GIT-GUARD-SETUP
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F003-PRE-PUSH-DANGEROUS-COMMIT-GUARD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-OPEN-QUESTIONS
---

# F002 提交消息守卫 PRD

## 1. 功能信息


| 项       | 内容                    |
| ------- | --------------------- |
| 功能编号    | F002                  |
| 功能名称    | 提交消息守卫                |
| 优先级     | P0                    |
| 状态      | 草稿，核心口径已确认            |
| 所属总 PRD | `../01-master-prd.md` |


## 2. 引用业务口径


| 类型   | 编号      | 名称                                    | 来源章节      |
| ---- | ------- | ------------------------------------- | --------- |
| 业务对象 | BO-003  | RepositoryHook                        | 总 PRD 4.1 |
| 业务对象 | BO-004  | CommitMessage                         | 总 PRD 4.1 |
| 术语   | T-002   | 仓库级 Git 守卫                            | 总 PRD 4.3 |
| 规则   | BR-G-01 | 代码提交必须有且只有一个合法 `DocChange-ID` trailer | 总 PRD 6   |


## 3. 功能目标

F002 在 Git `commit-msg` 阶段校验最终提交消息。对于代码提交，提交消息必须包含且只包含一个合法 `DocChange-ID: <40-char document commit hash>` trailer；文档-only 提交可按现有文档流程跳过；混合提交必须阻止并提示拆分。（SRC-D-001, SRC-C-004, SRC-C-005）

## 4. 用户故事


| 场景编号       | 用户角色        | 场景描述                        | 业务价值                              | 来源编号      |
| ---------- | ----------- | --------------------------- | --------------------------------- | --------- |
| US-F002-01 | U-001 开发者   | 代码提交忘记写 `DocChange-ID`      | 在 commit 完成前被阻止                   | SRC-U-001 |
| US-F002-02 | U-001 开发者   | 代码提交写了两个 `DocChange-ID`     | 在 commit 完成前被阻止                   | SRC-C-005 |
| US-F002-03 | U-002 插件使用者 | Agent 通过 `git commit -m` 提交 | 校验最终消息，不依赖旧 `.git/COMMIT_EDITMSG` | SRC-C-005 |


## 5. 入口与交互


| 入口编号       | 入口                      | 输入              | 成功反馈                    | 失败反馈                        |
| ---------- | ----------------------- | --------------- | ----------------------- | --------------------------- |
| EN-F002-01 | `.git/hooks/commit-msg` | Git 传入的提交消息文件路径 | 允许 commit 继续            | 输出缺失、重复或非法 trailer 原因并返回非 0 |
| EN-F002-02 | 插件工具层 commit hook       | 当前 staged scope | 发现未安装仓库级 hook 时先触发 F001 | 输出安装或冲突提示                   |


## 6. 业务规则


| 规则编号       | 规则内容                                                                 | 关联 AC      | 来源编号                 |
| ---------- | -------------------------------------------------------------------- | ---------- | -------------------- |
| BR-F002-01 | `commit-msg` 必须读取 Git 传入的消息文件参数，不能读取旧的 `.git/COMMIT_EDITMSG` 作为最终消息。 | AC-F002-01 | SRC-C-005, SRC-A-001 |
| BR-F002-02 | 代码提交必须包含一个且只有一个 `DocChange-ID`。                                      | AC-F002-02 | SRC-D-001            |
| BR-F002-03 | `DocChange-ID` 必须是 40 字符文档 Git commit hash。                          | AC-F002-03 | SRC-C-005            |
| BR-F002-04 | staged scope 为 mixed 时必须阻止提交并提示拆分。                                   | AC-F002-04 | SRC-C-004            |
| BR-F002-05 | document-only 提交可跳过代码 `DocChange-ID` 校验，但仍应由文档导入和 DocChange 登记流程接管。  | AC-F002-05 | SRC-C-004, SRC-D-001 |


## 7. 验收标准


| AC 编号      | Given                                             | When                 | Then               | 覆盖规则       |
| ---------- | ------------------------------------------------- | -------------------- | ------------------ | ---------- |
| AC-F002-01 | 用户执行 `git commit -m`                              | `commit-msg` hook 运行 | 校验的是 Git 传入的最终消息文件 | BR-F002-01 |
| AC-F002-02 | staged scope 为 code 且消息缺少 `DocChange-ID`          | 提交                   | commit 被阻止         | BR-F002-02 |
| AC-F002-03 | staged scope 为 code 且 `DocChange-ID` 非 40 字符 hash | 提交                   | commit 被阻止         | BR-F002-03 |
| AC-F002-04 | staged scope 为 mixed                              | 提交                   | commit 被阻止并提示拆分    | BR-F002-04 |
| AC-F002-05 | staged scope 为 document                           | 提交                   | 跳过代码 trailer 校验    | BR-F002-05 |


## 8. 测试场景建议


| 测试编号       | 优先级 | 场景                    | 预期结果        |
| ---------- | --- | --------------------- | ----------- |
| TC-F002-01 | P0  | 代码提交缺失 `DocChange-ID` | hook 返回非 0  |
| TC-F002-02 | P0  | 代码提交重复 `DocChange-ID` | hook 返回非 0  |
| TC-F002-03 | P0  | 代码提交合法 `DocChange-ID` | hook 返回 0   |
| TC-F002-04 | P0  | 混合提交                  | hook 返回非 0  |
| TC-F002-05 | P1  | 文档-only 提交            | hook 跳过代码校验 |

## 关联文档
- [[01-master-prd|Git 危险提交守卫总 PRD]]
- [[00-source-index|Git 危险提交守卫事实源索引]]
- [[features/F001-auto-git-guard-setup|F001 自动配置 Git 守卫 PRD]]
- [[features/F003-pre-push-dangerous-commit-guard|F003 推送前危险提交守卫 PRD]]
- [[99-open-questions|Git 危险提交守卫待确认问题]]
