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


| 问题编号 | 当前已知事实                             | 问题    | 需要确认的选项/开放点 | 类型  | 影响章节/范围 | 阻塞原因 | 建议确认人 | 状态  |
| ---- | ---------------------------------- | ----- | ----------- | --- | ------- | ---- | ----- | --- |
| 无    | Q-001、Q-101、Q-102、Q-103、Q-104 均已确认 | 无阻塞问题 | 不适用         | 不适用 | 不适用     | 无    | 不适用   | 已关闭 |


## 2. 非阻塞问题


| 问题编号 | 当前已知事实                 | 问题     | 需要确认的选项/开放点 | 类型  | 影响章节/范围 | 默认处理方式 | 建议确认人 | 状态  |
| ---- | ---------------------- | ------ | ----------- | --- | ------- | ------ | ----- | --- |
| 无    | 用户已确认权限、命令、清理范围和自动导入策略 | 无非阻塞问题 | 不适用         | 不适用 | 不适用     | 不适用    | 不适用   | 已关闭 |


## 3. 已确认问题记录


| 问题编号  | 确认结论                                                              | 确认人/来源                                   | 确认时间       | 已更新文档位置                                                                                |
| ----- | ----------------------------------------------------------------- | ---------------------------------------- | ---------- | -------------------------------------------------------------------------------------- |
| Q-001 | 切换绑定采用删除旧绑定并创建目标绑定的语义，不采用软删除、复制绑定或覆盖更新                            | 用户消息：旧绑定需要删除；用户选择方案 1                    | 2026-05-11 | `01-master-prd.md` 2、5、7；`features/F001-doc-binding-switch.md` 3、8、14                  |
| Q-101 | 本期不做权限模型，沿用现有 CLI/API 访问边界                                        | 用户消息：我们不做权限                              | 2026-05-11 | `01-master-prd.md` 3、4、7、11、12；`features/F001-doc-binding-switch.md` 12、17             |
| Q-102 | 切换命令采用 `doc binding switch`                                       | 用户授权实现方选择合适命令；实现方选择 `doc binding switch` | 2026-05-11 | `01-master-prd.md` 2、9；`features/F001-doc-binding-switch.md` 5、6、11、12、15              |
| Q-103 | 删除旧绑定时只清理绑定数据字段，不额外清理旧 documents、chunks、scan errors 或 Neo4j 文档图关系 | 用户消息：清理绑定数据字段即可                          | 2026-05-11 | `01-master-prd.md` 2、3、5、7、12；`features/F001-doc-binding-switch.md` 8、12、14、15         |
| Q-104 | 切换命令不自动 scan/import，只返回目标绑定和后续显式 scan/import 指令                   | 用户消息：不做自动导入                              | 2026-05-11 | `01-master-prd.md` 2、3、7、8、9、12；`features/F001-doc-binding-switch.md` 8、10、11、12、14、15 |


## 关联文档

- [[requirements/doc-binding-switch/README|文档绑定切换 PRD 产物索引]]
- [[requirements/doc-binding-switch/01-master-prd|文档绑定切换总 PRD]]
