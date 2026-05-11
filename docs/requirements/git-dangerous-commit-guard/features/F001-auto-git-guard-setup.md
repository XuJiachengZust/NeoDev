---
doc_id: NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F001-AUTO-GIT-GUARD-SETUP
title: F001 自动配置 Git 守卫 PRD
aliases:
- F001 自动配置 Git 守卫 PRD
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
- '[[features/F002-commit-message-guard|F002 提交消息守卫 PRD]]'
- '[[features/F003-pre-push-dangerous-commit-guard|F003 推送前危险提交守卫 PRD]]'
- '[[99-open-questions|Git 危险提交守卫待确认问题]]'
doc_type: prd
product_key: NEODEV
status: draft
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-MASTER-PRD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-SOURCE-INDEX
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F002-COMMIT-MESSAGE-GUARD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F003-PRE-PUSH-DANGEROUS-COMMIT-GUARD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-OPEN-QUESTIONS
---

# F001 自动配置 Git 守卫 PRD

## 1. 功能信息


| 项       | 内容                    |
| ------- | --------------------- |
| 功能编号    | F001                  |
| 功能名称    | 自动配置 Git 守卫           |
| 优先级     | P0                    |
| 状态      | 草稿，核心口径已确认            |
| 所属总 PRD | `../01-master-prd.md` |


## 2. 引用业务口径


| 类型   | 编号     | 名称             | 来源章节      |
| ---- | ------ | -------------- | --------- |
| 业务对象 | BO-001 | NeoDevPlugin   | 总 PRD 4.1 |
| 业务对象 | BO-002 | GitGuard       | 总 PRD 4.1 |
| 业务对象 | BO-003 | RepositoryHook | 总 PRD 4.1 |
| 术语   | T-001  | 插件内聚守卫         | 总 PRD 4.3 |
| 术语   | T-002  | 仓库级 Git 守卫     | 总 PRD 4.3 |


## 3. 功能目标

F001 让 NeoDev RD Knowledge 插件在安装后具备自动配置能力：当用户首次在某个 Git 仓库内触发 NeoDev 工作流、`git commit`、`git push` 或 `neodev` 相关命令时，插件自动检查当前仓库是否已安装 NeoDev Git 守卫；未安装或版本过旧时自动完成幂等配置。（SRC-U-004, SRC-U-005, SRC-L-003）

## 4. 用户故事


| 场景编号       | 用户角色        | 场景描述                                        | 业务价值                 | 来源编号                 |
| ---------- | ----------- | ------------------------------------------- | -------------------- | -------------------- |
| US-F001-01 | U-001 开发者   | 开发者安装插件后进入仓库执行 NeoDev 工作流，守卫自动安装            | 不需要手工创建 `.git/hooks` | SRC-U-004            |
| US-F001-02 | U-002 插件使用者 | 通过 Agent 执行 `git commit` 前，插件先确保仓库级 hook 存在 | 工具层和 Git 层形成双防线      | SRC-L-002, SRC-A-003 |
| US-F001-03 | U-001 开发者   | 仓库已有自定义 hook，NeoDev 不静默覆盖                   | 避免破坏用户已有工作流          | SRC-U-003            |


## 5. 前置条件

- 当前目录位于 Git 工作树内。（SRC-A-001）
- NeoDev RD Knowledge 插件已安装且 shared scripts 可访问。（SRC-L-001）
- 本机 NeoDev CLI 可执行并配置远程服务。（SRC-A-002）

## 6. 入口与触发


| 入口编号       | 入口              | 触发方式                                              | 结果              | 来源编号      |
| ---------- | --------------- | ------------------------------------------------- | --------------- | --------- |
| EN-F001-01 | 插件 `PreToolUse` | Agent 执行 `git commit *`、`git push *` 或 `neodev *` | 调用守卫确保脚本        | SRC-L-002 |
| EN-F001-02 | 显式安装命令          | `neodev git guard install` 或插件脚本入口                | 安装或升级仓库级 hook   | SRC-U-005 |
| EN-F001-03 | 仓库级 hook 自检     | 已安装 hook 执行时                                      | 发现缺少插件脚本时输出修复提示 | SRC-U-003 |


## 7. 业务规则


| 规则编号       | 规则内容                                          | 关联 AC      | 来源编号                 |
| ---------- | --------------------------------------------- | ---------- | -------------------- |
| BR-F001-01 | 自动配置只针对当前 Git 仓库，不扫描或修改其他仓库。                  | AC-F001-01 | SRC-U-005            |
| BR-F001-02 | NeoDev 管理的 hook 必须包含可识别版本和管理标记。               | AC-F001-02 | SRC-U-003            |
| BR-F001-03 | 多次执行自动配置必须幂等。                                 | AC-F001-03 | SRC-U-005            |
| BR-F001-04 | 已有用户 hook 时不得静默覆盖，必须采用可保留原 hook 的组合方式或返回冲突提示。 | AC-F001-04 | SRC-U-003            |
| BR-F001-05 | 环境检查必须使用 JSON 输出或兼容文本输出，不能因解析默认文本误报未配置。       | AC-F001-05 | SRC-L-006, SRC-A-002 |


## 8. 验收标准


| AC 编号      | Given                             | When              | Then                              | 覆盖规则       |
| ---------- | --------------------------------- | ----------------- | --------------------------------- | ---------- |
| AC-F001-01 | 当前目录是 Git 仓库且未安装 NeoDev hook      | 首次触发 NeoDev 插件工作流 | 自动安装 `commit-msg` 与 `pre-push` 守卫 | BR-F001-01 |
| AC-F001-02 | 仓库已安装 NeoDev hook                 | 再次触发自动配置          | 能识别已安装版本                          | BR-F001-02 |
| AC-F001-03 | 连续执行两次安装                          | 检查 hook 文件        | 内容不重复追加                           | BR-F001-03 |
| AC-F001-04 | 仓库已有用户自定义 hook                    | 执行自动配置            | 不静默覆盖用户 hook                      | BR-F001-04 |
| AC-F001-05 | 本机 `neodev config show --json` 可用 | 执行环境检查            | 返回 ok，不误报未配置                      | BR-F001-05 |


## 9. 测试场景建议


| 测试编号       | 优先级 | 场景                  | 预期结果                         |
| ---------- | --- | ------------------- | ---------------------------- |
| TC-F001-01 | P0  | 空 Git hook 仓库首次自动配置 | 生成 `commit-msg` 和 `pre-push` |
| TC-F001-02 | P0  | 重复执行自动配置            | hook 内容保持单份                  |
| TC-F001-03 | P0  | 用户已有 hook           | 用户 hook 不被静默覆盖               |
| TC-F001-04 | P0  | 环境检查使用已配置 CLI       | 返回 ok                        |

## 关联文档
- [[01-master-prd|Git 危险提交守卫总 PRD]]
- [[00-source-index|Git 危险提交守卫事实源索引]]
- [[features/F002-commit-message-guard|F002 提交消息守卫 PRD]]
- [[features/F003-pre-push-dangerous-commit-guard|F003 推送前危险提交守卫 PRD]]
- [[99-open-questions|Git 危险提交守卫待确认问题]]
