---
doc_id: NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-README
title: 文档绑定切换 PRD 产物索引
aliases:
- 文档绑定切换 PRD 产物索引
tags:
- neodev/docs
- neodev/prd
- neodev/requirements
- requirements/doc-binding-switch
created: 2026-05-11
updated: 2026-05-11
related:
- '[[requirements/doc-binding-switch/00-source-index|文档绑定切换事实源索引]]'
- '[[requirements/doc-binding-switch/01-master-prd|文档绑定切换总 PRD]]'
- '[[requirements/doc-binding-switch/features/F001-doc-binding-switch|F001 文档绑定切换 PRD]]'
- '[[requirements/doc-binding-switch/99-open-questions|文档绑定切换待确认问题]]'
doc_type: prd
product_key: NEODEV
status: draft
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-SOURCE-INDEX
  - NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-MASTER-PRD
  - NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-F001-DOC-BINDING-SWITCH
  - NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-OPEN-QUESTIONS
---

# 文档绑定切换 PRD 产物索引

## 1. 范围

| 项 | 内容 |
| --- | --- |
| 命中项目 | NeoDev 后端单项目仓库 |
| 输出路径 | `docs/requirements/doc-binding-switch/` |
| 需求状态 | 草稿，核心切换语义已由用户确认 |
| 跨项目原因 | 不适用 |

## 2. 产物清单

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| `00-source-index.md` | 用户输入、现有 PRD、代码、接口、数据和测试事实索引 | 草稿 |
| `01-master-prd.md` | 文档绑定切换总 PRD | 草稿 |
| `features/F001-doc-binding-switch.md` | 删除旧绑定并新建目标绑定的功能 PRD | 草稿 |
| `99-open-questions.md` | 待确认问题与已确认决策记录 | 草稿 |

## 3. 功能子 PRD

| 功能编号 | 功能名称 | 文件 | 优先级 | 确认状态 |
| --- | --- | --- | --- | --- |
| F001 | 文档绑定切换 | `features/F001-doc-binding-switch.md` | P0 | 核心删除语义已确认，清理深度和命令命名待确认 |

## 4. 阻塞问题摘要

| 级别 | 数量 | 主要影响 |
| --- | --- | --- |
| 阻塞 | 0 | 核心业务语义已可进入方案和实现计划 |
| 非阻塞 | 4 | 影响权限边界、命令命名、清理深度和自动导入策略 |

## 5. 评估状态

| 项 | 内容 |
| --- | --- |
| 编排方式 | 主智能体本地编排；因本会话未获得显式子智能体授权，未创建执行器或评估器子智能体 |
| 执行器分工 | 主智能体完成事实收集、总 PRD、子 PRD 和问题清单 |
| 自检清单 | 已按 NeoDev 受控文档格式、事实追踪、总分一致性做本地自检 |
| 评估器结论 | 未执行独立子智能体评估 |
| 最近评估时间 | 2026-05-11 |
| 主要风险 | 旧绑定删除后的关联数据清理深度仍需在实现计划中确认 |

## 关联文档
- [[requirements/doc-binding-switch/00-source-index|文档绑定切换事实源索引]]
- [[requirements/doc-binding-switch/01-master-prd|文档绑定切换总 PRD]]
- [[requirements/doc-binding-switch/features/F001-doc-binding-switch|F001 文档绑定切换 PRD]]
- [[requirements/doc-binding-switch/99-open-questions|文档绑定切换待确认问题]]
