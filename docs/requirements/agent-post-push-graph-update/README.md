---
doc_id: NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-README
title: Agent Push 后图谱更新 PRD 产物索引
aliases:
  - Agent Push 后图谱更新 PRD 产物索引
tags:
  - neodev/docs
  - neodev/prd
  - neodev/requirements
  - requirements/agent-post-push-graph-update
created: 2026-05-13
updated: 2026-05-13
related:
  - '[[00-source-index|Agent Push 后图谱更新事实源索引]]'
  - '[[01-master-prd|Agent Push 后图谱更新总 PRD]]'
  - '[[features/F001-post-push-orchestration|F001 Push 后编排 Hook PRD]]'
  - '[[features/F002-commit-scope-routing|F002 提交范围分类路由 PRD]]'
  - '[[features/F003-docchange-code-linking|F003 DocChange 与代码关联 PRD]]'
  - '[[features/F004-skill-behavior-protocol|F004 Skill 行为协议 PRD]]'
  - '[[99-open-questions|Agent Push 后图谱更新待确认问题]]'
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-SOURCE-INDEX
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-MASTER-PRD
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F001-POST-PUSH-ORCHESTRATION
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F002-COMMIT-SCOPE-ROUTING
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F003-DOCCHANGE-CODE-LINKING
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-F004-SKILL-BEHAVIOR-PROTOCOL
    - NEODEV-DOC-REQUIREMENTS-AGENT-POST-PUSH-GRAPH-UPDATE-OPEN-QUESTIONS
---

# Agent Push 后图谱更新 PRD 产物索引

## 1. 范围

| 项 | 内容 |
| --- | --- |
| 命中项目 | NeoDev 后端单项目仓库与 NeoDev RD Knowledge 插件 |
| 输出路径 | `docs/requirements/agent-post-push-graph-update/` |
| 需求状态 | 已定稿，核心边界与 Q101-Q107 决策已确认 |
| 核心边界 | 只覆盖 Agent 插件层面的 `git push` 成功后动作，不覆盖普通终端或 IDE 的原生 Git push |
| 分层结论 | Hook 触发确定性脚本；脚本本地获取上下文并调用 NeoDev CLI；扩展现有 `neodev-rd-knowledge` skill 规范 Agent 对 JSON 结果的解读、汇报和补救动作 |

## 2. 产物清单

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| `00-source-index.md` | 用户输入、已有 PRD、代码、CLI、数据、测试与 skill 设计事实索引 | 已定稿 |
| `01-master-prd.md` | Agent Push 后图谱更新总 PRD | 已定稿 |
| `features/F001-post-push-orchestration.md` | Push 后 Agent hook 与稳定脚本编排能力 | 已定稿 |
| `features/F002-commit-scope-routing.md` | Push commit 范围分类与路由能力 | 已定稿 |
| `features/F003-docchange-code-linking.md` | 带 DocChange-ID 的文档与代码关联能力 | 已定稿 |
| `features/F004-skill-behavior-protocol.md` | 后置处理 Skill 的 Agent 行为协议 | 已定稿 |
| `99-open-questions.md` | 待确认问题和已确认决策记录 | 已定稿 |

## 3. 功能子 PRD

| 功能编号 | 功能名称 | 文件 | 优先级 | 确认状态 |
| --- | --- | --- | --- | --- |
| F001 | Push 后编排 Hook | `features/F001-post-push-orchestration.md` | P0 | 已确认 |
| F002 | 提交范围分类路由 | `features/F002-commit-scope-routing.md` | P0 | 已确认 |
| F003 | DocChange 与代码关联 | `features/F003-docchange-code-linking.md` | P0 | 已确认 |
| F004 | Skill 行为协议 | `features/F004-skill-behavior-protocol.md` | P0 | 已确认 |

## 4. 阻塞问题摘要

| 级别 | 数量 | 主要影响 |
| --- | --- | --- |
| 阻塞 | 0 | 当前可按 Agent 插件层 + 脚本 + Skill 分层方案继续细化 |
| 非阻塞 | 0 | Q101-Q107 均已关闭 |

## 5. 评估状态

| 项 | 内容 |
| --- | --- |
| 编排方式 | 主智能体 + 事实收集执行器 + 主智能体分段编写 + 独立评估器子智能体 + 修复循环；本次追加按用户新决策直接修订 |
| 最近更新 | 2026-05-13 |
| 本次调整 | 将 Q101-Q107 转为已确认决策：本地获取上下文、持久化追加覆盖、不新增权限、参数限本地可取、document-only 自动导入登记、失败全量回滚、扩展现有 `neodev-rd-knowledge` skill |
| 主要风险 | 原子性要求跨文档导入、DocChange、CodeChangeLink、图谱刷新和运行记录；实现阶段需验证现有 CLI/服务是否能支持事务或补偿回滚 |
