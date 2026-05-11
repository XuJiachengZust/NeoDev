---
doc_id: NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-README
title: Git 危险提交守卫 PRD 产物索引
aliases:
- Git 危险提交守卫 PRD 产物索引
tags:
- neodev/docs
- neodev/prd
- neodev/requirements
- requirements/git-dangerous-commit-guard
created: 2026-05-11
updated: 2026-05-11
related:
- '[[00-source-index|Git 危险提交守卫事实源索引]]'
- '[[01-master-prd|Git 危险提交守卫总 PRD]]'
- '[[features/F001-auto-git-guard-setup|F001 自动配置 Git 守卫 PRD]]'
- '[[features/F002-commit-message-guard|F002 提交消息守卫 PRD]]'
- '[[features/F003-pre-push-dangerous-commit-guard|F003 推送前危险提交守卫 PRD]]'
- '[[99-open-questions|Git 危险提交守卫待确认问题]]'
doc_type: prd
product_key: NEODEV
status: draft
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-SOURCE-INDEX
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-MASTER-PRD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F001-AUTO-GIT-GUARD-SETUP
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F002-COMMIT-MESSAGE-GUARD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-F003-PRE-PUSH-DANGEROUS-COMMIT-GUARD
  - NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-OPEN-QUESTIONS
---

# Git 危险提交守卫 PRD 产物索引

## 1. 范围

| 项 | 内容 |
| --- | --- |
| 命中项目 | NeoDev 后端单项目仓库与 NeoDev RD Knowledge 插件 |
| 输出路径 | `docs/requirements/git-dangerous-commit-guard/` |
| 需求状态 | 草稿，核心方向已由用户确认 |
| 核心结论 | 不内嵌 Git；插件安装后在仓库首次使用时自动配置仓库级 Git 守卫 |

## 2. 产物清单

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| `00-source-index.md` | 用户输入、现有 PRD、代码、插件 hook 和本机检查事实索引 | 草稿 |
| `01-master-prd.md` | Git 危险提交守卫总 PRD | 草稿 |
| `features/F001-auto-git-guard-setup.md` | 插件自动配置 Git 守卫能力 | 草稿 |
| `features/F002-commit-message-guard.md` | 提交消息守卫能力 | 草稿 |
| `features/F003-pre-push-dangerous-commit-guard.md` | 推送前危险提交守卫能力 | 草稿 |
| `99-open-questions.md` | 待确认问题和已确认决策记录 | 草稿 |

## 3. 功能子 PRD

| 功能编号 | 功能名称 | 优先级 | 确认状态 |
| --- | --- | --- | --- |
| F001 | 自动配置 Git 守卫 | P0 | 已确认 |
| F002 | 提交消息守卫 | P0 | 已确认 |
| F003 | 推送前危险提交守卫 | P0 | 已确认 |

## 4. 阻塞问题摘要

| 级别 | 数量 | 主要影响 |
| --- | --- | --- |
| 阻塞 | 0 | 无 |
| 非阻塞 | 0 | 无 |

## 5. 评估状态

| 项 | 内容 |
| --- | --- |
| 编排方式 | 主智能体本地编排；用户未要求创建子智能体，未分派独立执行器或评估器 |
| 自检范围 | front matter、relations、事实追踪、总分一致性、验收闭环 |
| 主要风险 | 实现阶段需同时修复插件 hook 生效问题和服务端危险提交登记问题 |

## 关联文档
- [[00-source-index|Git 危险提交守卫事实源索引]]
- [[01-master-prd|Git 危险提交守卫总 PRD]]
- [[features/F001-auto-git-guard-setup|F001 自动配置 Git 守卫 PRD]]
- [[features/F002-commit-message-guard|F002 提交消息守卫 PRD]]
- [[features/F003-pre-push-dangerous-commit-guard|F003 推送前危险提交守卫 PRD]]
- [[99-open-questions|Git 危险提交守卫待确认问题]]
