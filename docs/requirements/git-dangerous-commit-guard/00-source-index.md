---
doc_id: NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-SOURCE-INDEX
title: Git 危险提交守卫事实源索引
aliases:
- Git 危险提交守卫事实源索引
tags:
- neodev/docs
- neodev/tech-design
- neodev/requirements
- requirements/git-dangerous-commit-guard
created: 2026-05-11
updated: 2026-05-11
related:
- '[[README|Git 危险提交守卫 PRD 产物索引]]'
- '[[01-master-prd|Git 危险提交守卫总 PRD]]'
doc_type: tech-design
product_key: NEODEV
status: draft
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-README
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-MASTER-PRD
---

# Git 危险提交守卫事实源索引

## 1. 用户输入

| 编号 | 来源 | 内容摘要 | 可用性 | 可追踪到 | 备注 |
| --- | --- | --- | --- | --- | --- |
| SRC-U-001 | 用户消息，2026-05-11 | 代码提交缺少 `DocChange-ID` 应属于危险提交，但未被识别和提醒，不符合 MVP 要求 | 已确认 | R-001, R-004, F003, AC-G-04 | 明确当前缺口是危险提交漏报 |
| SRC-U-002 | 用户消息，2026-05-11 | 询问如何在插件层面解决 | 已确认 | R-002, F001, F002, F003 | 明确插件层需要承担提前拦截能力 |
| SRC-U-003 | 用户消息，2026-05-11 | 希望插件足够内聚 | 已确认 | R-002, BR-G-03 | 规则、脚本、模板和安装入口应归属 NeoDev RD Knowledge 插件 |
| SRC-U-004 | 用户消息，2026-05-11 | 这些配置需要在安装插件时自动完成 | 已确认 | R-003, F001, AC-F001-01 | 自动配置是核心体验要求 |
| SRC-U-005 | 用户确认，2026-05-11 | 接受“插件安装后在仓库首次使用时自动配置 Git 守卫”的方案 | 已确认 | R-003, BR-G-04 | 解决插件安装时不知道具体仓库的问题 |

## 2. 本地需求文档

| 编号 | 路径 | 内容摘要 | 适用范围 | 可信度 | 可追踪到 |
| --- | --- | --- | --- | --- | --- |
| SRC-D-001 | `docs/requirements/rd-knowledge-graph-mvp/01-master-prd.md` | MVP 要求代码提交使用 `DocChange-ID`，推送前校验与危险提交登记属于 P0 范围 | Git 一致性总规则 | 高 | R-001, BR-G-01, AC-G-01 |
| SRC-D-002 | `docs/neosuperpower/plans/2026-04-27-neodev-git-verify-doc-change-f003.md` | 已实现 `git verify-doc-change`，成功时创建 `CodeChangeLink` 并推进 DocChange 状态 | 现有 CLI 能力 | 高 | F003, BR-F003-02 |
| SRC-D-003 | `docs/neosuperpower/plans/2026-04-27-neodev-dangerous-commit-cli-f003.md` | 已实现 `git dangerous-commit list/resolve`，但待补从 verify 风险路径自动创建危险提交记录 | 危险提交缺口 | 高 | R-004, F003, AC-F003-04 |

## 3. 本机检查事实

| 编号 | 检查项 | 事实摘要 | 推断限制 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-L-001 | 插件 manifest | `plugins/neodev-rd-knowledge/.codex-plugin/plugin.json` 声明 `hooks` 与 shared scripts | 只证明插件声明，不证明 Git 仓库 hook 生效 | F001 |
| SRC-L-002 | 插件 hooks | `hooks/hooks.json` 已包含 `Bash(git commit *)` 的工具层拦截 | 只能覆盖 Agent 工具调用，不能覆盖 IDE 或普通终端 Git | F002 |
| SRC-L-003 | 仓库 Git hooks | 当前 `.git/hooks/` 只有 sample 文件，没有真实 `commit-msg`、`pre-push`、`pre-commit` | 说明仓库级 Git hook 未安装 | R-003, F001 |
| SRC-L-004 | Git hooksPath | 当前仓库未配置 `core.hooksPath` | Git 不会从插件目录自动加载 hook | F001 |
| SRC-L-005 | 提交消息脚本 | `check_docchange_trailer.py --message "feat: add doc binding switch"` 能识别缺失 `DocChange-ID` | 脚本可用，但当前没有稳定接入真实 Git hook | F002 |
| SRC-L-006 | 环境检查脚本 | `check_neodev_environment.py` 调用默认 `neodev config show` 并按 JSON 解析，存在误报风险 | 需要修复为 `--json` 或兼容文本输出 | F001 |

## 4. 代码事实

| 编号 | 路径 | 事实摘要 | 推断限制 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-C-001 | `src/service/services/git_consistency_service.py` | `verify_doc_change` 在缺少、重复或非法 `DocChange-ID` 时直接抛错，当前未创建危险提交记录 | 说明服务端仍需补登记闭环 | R-004, F003 |
| SRC-C-002 | `src/service/repositories/dangerous_commit_repository.py` | 已具备创建、查询 open、关闭危险提交记录的 repository 能力 | 未提供幂等 upsert | F003 |
| SRC-C-003 | `src/service/cli/commands/git.py` | 已注册 `git verify-doc-change`、`git dangerous-commit list/resolve` | CLI 异常路径会回滚当前事务，需设计失败登记提交边界 | F003 |
| SRC-C-004 | `plugins/neodev-rd-knowledge/check_git_commit_scope.py` | 可按 staged paths 区分 document、code、mixed、empty | `commit-msg` 阶段 staged 内容可能变化，需按 hook 时机使用 | F002 |
| SRC-C-005 | `plugins/neodev-rd-knowledge/check_docchange_trailer.py` | 可校验提交消息中唯一合法 `DocChange-ID` | 当前 `hooks.json` 使用 `.git/COMMIT_EDITMSG` 作为 PreToolUse 输入，不是最终提交消息的可靠来源 | F002 |

## 5. 接口与平台事实

| 编号 | 路径/接口 | 事实摘要 | 推断限制 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-A-001 | Git 标准 hook | `commit-msg` 接收最终提交消息文件，`pre-push` 接收本次推送 refs 和 commit range | 本需求不内嵌 Git，只安装薄 hook 调用插件脚本 | F001, F002, F003 |
| SRC-A-002 | NeoDev CLI | `neodev config show --json`、`neodev cli version-check --json` 在本机可用 | 插件脚本应显式使用 JSON 输出 | F001 |
| SRC-A-003 | 插件 hook | Agent 工具层 hook 可作为补充提醒 | 不能作为唯一拦截边界 | BR-G-05 |

## 6. 测试与验收材料

| 编号 | 路径 | 内容摘要 | 适用范围 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-T-001 | `tests/test_plugin_platforms.py` | 覆盖插件 manifest 与 hooks 文件结构 | 新增 shared scripts 或 hook 入口应同步测试 | TC-F001-01 |
| SRC-T-002 | `tests/test_git_consistency_service_unit.py` | 覆盖 Git 一致性 service 成功和错误路径 | 新增危险提交登记应补 failure-path 测试 | TC-F003-03 |
| SRC-T-003 | `tests/test_git_cli.py` | 覆盖 `git verify-doc-change` 与 dangerous commit CLI | 新增 pre-push 或 guard 命令应补 CLI 测试 | TC-F003-04 |

## 关联文档
- [[README|Git 危险提交守卫 PRD 产物索引]]
- [[01-master-prd|Git 危险提交守卫总 PRD]]
