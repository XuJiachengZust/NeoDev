---
doc_id: NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-README
title: CLI 命令简化 PRD 产物索引
aliases:
  - CLI 命令简化 PRD 产物索引
tags:
  - neodev/docs
  - neodev/prd
  - neodev/requirements
  - requirements/cli-command-simplification
created: 2026-06-10
updated: 2026-06-10
related:
  - '[[requirements/cli-command-simplification/00-source-index|CLI 命令简化事实源索引]]'
  - '[[requirements/cli-command-simplification/01-master-prd|CLI 命令简化总 PRD]]'
  - '[[requirements/cli-command-simplification/features/F001-workflow-entrypoints|F001 高层工作流入口 PRD]]'
  - '[[requirements/cli-command-simplification/features/F002-command-visibility-and-compatibility|F002 命令可见性与兼容策略 PRD]]'
  - '[[requirements/cli-command-simplification/features/F003-agent-command-routing|F003 Agent 命令路由收口 PRD]]'
  - '[[requirements/cli-command-simplification/99-open-questions|CLI 命令简化待确认问题]]'
doc_type: prd
product_key: NEODEV
status: draft
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-SOURCE-INDEX
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-MASTER-PRD
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-F001-WORKFLOW-ENTRYPOINTS
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-F002-COMMAND-VISIBILITY-AND-COMPATIBILITY
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-F003-AGENT-COMMAND-ROUTING
    - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-OPEN-QUESTIONS
---

# CLI 命令简化 PRD 产物索引

## 1. 范围

| 项 | 内容 |
| --- | --- |
| 命中项目 | NeoDev 后端单项目仓库与 NeoDev RD Knowledge 插件 |
| 输出路径 | `docs/requirements/cli-command-simplification/` |
| 需求状态 | 草稿，关键命名与入口收口策略已确认 |
| 核心目标 | 在不删除底层原子命令的前提下，新增少量意图型工作流入口，降低用户和 Agent 的命令选择成本 |
| 非目标 | 本需求不直接实现代码，不变更数据库结构，不立即废弃现有命令 |

## 2. 产物清单

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| `00-source-index.md` | 用户输入、现有 CLI、插件 hooks、脚本和工作流事实索引 | 草稿 |
| `01-master-prd.md` | CLI 命令简化总 PRD | 草稿 |
| `features/F001-workflow-entrypoints.md` | 高层工作流入口能力 | 草稿 |
| `features/F002-command-visibility-and-compatibility.md` | 命令可见性与兼容策略 | 草稿 |
| `features/F003-agent-command-routing.md` | Agent 命令路由收口能力 | 草稿 |
| `99-open-questions.md` | 已关闭问题与确认记录 | 草稿 |

## 3. 功能子 PRD

| 功能编号 | 功能名称 | 文件 | 优先级 | 确认状态 |
| --- | --- | --- | --- | --- |
| F001 | 高层工作流入口 | `features/F001-workflow-entrypoints.md` | P0 | 已确认 |
| F002 | 命令可见性与兼容策略 | `features/F002-command-visibility-and-compatibility.md` | P0 | 已确认 |
| F003 | Agent 命令路由收口 | `features/F003-agent-command-routing.md` | P1 | 已确认 |

## 4. 阻塞问题摘要

| 级别 | 数量 | 主要影响 |
| --- | --- | --- |
| 阻塞 | 0 | 当前可先按“新增高层入口、保留底层命令”的方向细化 |
| 非阻塞 | 0 | 顶层命名、全量 help 入口、插件命令说明收口方式均已确认 |

## 5. 评估状态

| 项 | 内容 |
| --- | --- |
| 编排方式 | 主智能体基于用户评估结论、本地 CLI 代码、插件 manifest/hooks/scripts 和既有 PRD 结构编写 |
| 自检清单 | 已按 NeoDev 受控文档格式、事实源追踪、总分结构和开放问题索引做本地自检 |
| 评估器结论 | 未执行独立子智能体评估 |
| 最近更新时间 | 2026-06-10 |
| 主要风险 | 若高层命令语义过宽，可能掩盖失败位置；若隐藏命令过激，可能破坏脚本和高级排障兼容性 |
| 已确认决策 | 顶层命名接受 `doctor/context/setup/docs/change/git/status`；全量 help 使用 `neodev help --all`；插件命令说明收口为四个意图入口：context/docs/change/submit；每个需求点都必须给出具体场景、数据细节、输出示例和验收关注点 |

## 关联文档

- [[requirements/cli-command-simplification/00-source-index|CLI 命令简化事实源索引]]
- [[requirements/cli-command-simplification/01-master-prd|CLI 命令简化总 PRD]]
- [[requirements/cli-command-simplification/features/F001-workflow-entrypoints|F001 高层工作流入口 PRD]]
- [[requirements/cli-command-simplification/features/F002-command-visibility-and-compatibility|F002 命令可见性与兼容策略 PRD]]
- [[requirements/cli-command-simplification/features/F003-agent-command-routing|F003 Agent 命令路由收口 PRD]]
- [[requirements/cli-command-simplification/99-open-questions|CLI 命令简化待确认问题]]
