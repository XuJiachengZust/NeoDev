---
doc_id: NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-OPEN-QUESTIONS
title: 文档绑定切换待确认问题
aliases:
- 文档绑定切换待确认问题
tags:
- neodev/docs
- neodev/tech-design
- neodev/requirements
- requirements/doc-binding-switch
created: 2026-05-11
updated: 2026-05-11
related:
- '[[requirements/doc-binding-switch/README|文档绑定切换 PRD 产物索引]]'
- '[[requirements/doc-binding-switch/01-master-prd|文档绑定切换总 PRD]]'
doc_type: tech-design
product_key: NEODEV
status: draft
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-README
  - NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-MASTER-PRD
---

# 文档绑定切换待确认问题

## 1. 阻塞问题

| 问题编号 | 当前已知事实 | 问题 | 需要确认的选项/开放点 | 类型 | 影响章节/范围 | 阻塞原因 | 建议确认人 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 无 | 用户已确认旧绑定需要删除，并选择删除后新建方案 | 无阻塞问题 | 不适用 | 不适用 | 不适用 | 核心业务语义已确认，可进入实现计划 | 不适用 | 不适用 |

## 2. 非阻塞问题

| 问题编号 | 当前已知事实 | 问题 | 需要确认的选项/开放点 | 类型 | 影响章节/范围 | 默认处理方式 | 建议确认人 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Q-101 | 当前需求未提供权限模型 | 谁可以执行文档绑定切换？ | 所有 CLI 使用者可执行，或限制为产品管理员/研发负责人 | 权限 | 总 PRD 4、11；F001 6、12 | 实现计划先按现有 CLI 鉴权边界处理，不新增权限模型 | 产品负责人 | 待确认 |
| Q-102 | 现有 CLI 只有 `doc binding create/list` | 切换入口命名和参数如何确定？ | `doc binding switch`、`doc binding replace`、或 `doc binding create --replace` | 接口 | 总 PRD 12；F001 6、12、15 | 实现计划优先选择与现有命令族一致的最小新增入口 | 产品负责人/实现负责人 | 待确认 |
| Q-103 | 用户确认旧绑定需要删除，但未确认关联数据清理深度 | 删除旧绑定时，旧 documents、chunks、scan errors、Neo4j 文档图关系如何处理？ | 硬删除、外键级联、标记失效、或按子系统分别处理 | 数据 | 总 PRD 5.5、7；F001 8、13、14 | 实现计划必须列清外键和图谱清理清单后再改代码 | 实现负责人 | 待确认 |
| Q-104 | 现有 scan/import 是独立命令 | 切换命令是否自动执行 scan/import？ | 只返回后续命令；支持可选 `--scan`；支持可选 `--import` | 范围 | 总 PRD 2.3、8、9；F001 8、12、14 | 当前 PRD 不要求自动导入，默认返回后续命令 | 产品负责人 | 待确认 |

## 3. 已确认问题记录

| 问题编号 | 确认结论 | 确认人/来源 | 确认时间 | 已更新文档位置 |
| --- | --- | --- | --- | --- |
| Q-001 | 切换绑定采用删除旧绑定并创建目标绑定的语义，不采用软删除、复制绑定或覆盖更新 | 用户消息：旧绑定需要删除；用户选择方案 1 | 2026-05-11 | `01-master-prd.md` 2、5、7；`features/F001-doc-binding-switch.md` 3、8、14 |

## 关联文档
- [[requirements/doc-binding-switch/README|文档绑定切换 PRD 产物索引]]
- [[requirements/doc-binding-switch/01-master-prd|文档绑定切换总 PRD]]
