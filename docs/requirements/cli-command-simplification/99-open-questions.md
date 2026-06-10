---

doc_id: NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-OPEN-QUESTIONS
title: CLI 命令简化待确认问题
aliases:

- CLI 命令简化待确认问题
tags:
- neodev/docs
- neodev/tech-design
- neodev/requirements
- requirements/cli-command-simplification
created: 2026-06-10
updated: 2026-06-10
related:
- '[[requirements/cli-command-simplification/README|CLI 命令简化 PRD 产物索引]]'
- '[[requirements/cli-command-simplification/01-master-prd|CLI 命令简化总 PRD]]'
- '[[requirements/cli-command-simplification/00-source-index|CLI 命令简化事实源索引]]'
doc_type: tech-design
product_key: NEODEV
status: draft
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-README
  - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-MASTER-PRD
  - NEODEV-DOC-REQUIREMENTS-CLI-COMMAND-SIMPLIFICATION-SOURCE-INDEX

---

# CLI 命令简化待确认问题

## 1. 阻塞问题


| 问题编号 | 当前已知事实                     | 问题  | 需要确认的选项/开放点 | 类型  | 影响章节/范围 | 阻塞原因 | 建议确认人 | 状态  |
| ---- | -------------------------- | --- | ----------- | --- | ------- | ---- | ----- | --- |
| 无    | 当前需求可按“新增高层入口、保留底层兼容”继续细化。 | 无   | 无           | 无   | 无       | 无    | 无     | 无   |


## 2. 非阻塞问题


| 问题编号  | 当前已知事实                                                     | 问题                | 需要确认的选项/开放点                                      | 类型  | 影响章节/范围        | 默认处理方式                      | 建议确认人         | 状态  |
| ----- | ---------------------------------------------------------- | ----------------- | ------------------------------------------------ | --- | -------------- | --------------------------- | ------------- | --- |
| 无 | 原 Q-101、Q-102、Q-103 均已确认。 | 无 | 无 | 无 | 无 | 无 | 已关闭 |


## 3. 已确认问题记录


| 问题编号  | 确认结论                           | 确认人/来源                    | 确认时间       | 已更新文档位置             |
| ----- | ------------------------------ | ------------------------- | ---------- | ------------------- |
| D-001 | 本次只做需求编写，不做实现。                 | 用户消息 SRC-U-002, SRC-U-003 | 2026-06-10 | README、总 PRD 非目标    |
| D-002 | 简化方向不是删除底层命令，而是新增高层入口并降低默认可见面。 | 会话评估结论 SRC-U-004          | 2026-06-10 | 总 PRD 2、7；F001；F002 |
| D-003 | Q-101 接受 `doctor/context/setup/docs/change/git/status` 这组顶层命名。 | 用户消息 SRC-U-005 | 2026-06-10 | 总 PRD 5、6；F001 |
| D-004 | Q-102 全量 help 入口采用 `neodev help --all`。 | 用户消息 SRC-U-005 | 2026-06-10 | F002 |
| D-005 | Q-103 插件命令说明收口为 context/docs/change/submit 四个意图入口。 | 用户消息 SRC-U-005 | 2026-06-10 | F003 |
| D-006 | 每个高层命令必须形成操作与数据闭环，说明输入、读写事实、输出证据、下一步动作和失败恢复。 | 用户消息 SRC-U-006 | 2026-06-10 | 总 PRD 7、12；F001；F003 |
| D-007 | 高层命令之间必须形成业务闭环，覆盖上下文确认、仓库接入、文档同步、变更启动、影响分析、提交检查和状态回看。 | 用户消息 SRC-U-007 | 2026-06-10 | 总 PRD 7、12；F001；F003 |
| D-008 | 业务闭环必须用具体场景说明触发条件、命令顺序、数据读写、输出证据、下一步动作和验收关注点。 | 用户消息 SRC-U-008 | 2026-06-10 | 总 PRD 5、7、8、12；F001；F003 |
| D-009 | 不采用纯抽象编号拆分；其他需求点也要按具体场景、示例输入输出和验收关注点补充细节。 | 用户消息 SRC-U-009 | 2026-06-10 | 总 PRD 7、12；F001；F002；F003 |


## 关联文档

- [[requirements/cli-command-simplification/README|CLI 命令简化 PRD 产物索引]]
- [[requirements/cli-command-simplification/01-master-prd|CLI 命令简化总 PRD]]
- [[requirements/cli-command-simplification/00-source-index|CLI 命令简化事实源索引]]
