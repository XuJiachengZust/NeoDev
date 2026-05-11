---
doc_id: NEODEV-DOC-REQUIREMENTS-GIT-DANGEROUS-COMMIT-GUARD-OPEN-QUESTIONS
title: Git 危险提交守卫待确认问题
aliases:
- Git 危险提交守卫待确认问题
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

# Git 危险提交守卫待确认问题

## 1. 阻塞问题


| 问题编号 | 当前已知事实            | 问题    | 需要确认的选项/开放点 | 类型  | 影响章节/范围 | 阻塞原因 | 建议确认人 | 状态  |
| ---- | ----------------- | ----- | ----------- | --- | ------- | ---- | ----- | --- |
| 无    | Q-001 至 Q-004 已确认 | 无阻塞问题 | 不适用         | 不适用 | 不适用     | 无    | 不适用   | 已关闭 |


## 2. 非阻塞问题


| 问题编号 | 当前已知事实           | 问题     | 需要确认的选项/开放点 | 类型  | 影响章节/范围 | 默认处理方式 | 建议确认人 | 状态  |
| ---- | ---------------- | ------ | ----------- | --- | ------- | ------ | ----- | --- |
| 无    | 用户已确认插件内聚和自动配置口径 | 无非阻塞问题 | 不适用         | 不适用 | 不适用     | 不适用    | 不适用   | 已关闭 |


## 3. 已确认问题记录


| 问题编号  | 确认结论                                                             | 确认人/来源                        | 确认时间       | 已更新文档位置                                                                                                           |
| ----- | ---------------------------------------------------------------- | ----------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------- |
| Q-001 | 不内嵌 Git，不做完整 Git 客户端替代；采用插件安装薄 Git hooks 的方案                     | 用户询问和后续确认                     | 2026-05-11 | `01-master-prd.md` 2、6、9                                                                                          |
| Q-002 | 插件需要足够内聚，守卫安装、hook 模板、校验脚本和工具层提醒归属 NeoDev RD Knowledge 插件        | 用户消息：希望插件足够内聚                 | 2026-05-11 | `01-master-prd.md` 2、4、6；`features/F001-auto-git-guard-setup.md`                                                  |
| Q-003 | 插件安装后，在仓库首次使用时自动完成 Git 守卫配置                                      | 用户消息：安装插件时自动配置；用户确认首次使用自动配置方案 | 2026-05-11 | `01-master-prd.md` 2、6；`features/F001-auto-git-guard-setup.md`                                                    |
| Q-004 | 仅添加工具层 hook 不够，必须补仓库级 `commit-msg` 和 `pre-push` hook，并由服务端登记危险提交 | 本机检查与用户确认                     | 2026-05-11 | `01-master-prd.md` 6、9；`features/F002-commit-message-guard.md`；`features/F003-pre-push-dangerous-commit-guard.md` |

## 关联文档
- [[README|Git 危险提交守卫 PRD 产物索引]]
- [[01-master-prd|Git 危险提交守卫总 PRD]]
