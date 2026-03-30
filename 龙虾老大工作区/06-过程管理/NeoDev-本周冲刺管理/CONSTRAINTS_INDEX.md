# CONSTRAINTS_INDEX

说明：这是当前约束体系的总索引。目标不是一次性加载全部规则，而是按层级和动作场景做渐进式加载。

---

## Layer 0：基础常驻层（始终生效）

作用：定义身份、长期边界、协作对象与基础风格。

来源文件：
- `C:\Users\AH\.openclaw\workspace\SOUL.md`
- `C:\Users\AH\.openclaw\workspace\USER.md`
- `C:\Users\AH\.openclaw\workspace\MEMORY.md`
- `C:\Users\AH\.openclaw\workspace\memory\2026-03-26.md`

---

## Layer 1：通用执行层（任何任务默认加载）

作用：约束所有任务都必须遵守的最小规则。

核心规则：
- 必须先定义目标与边界
- 必须进入状态机
- 汇报必须带证据
- 最小可用单元提交
- 先审核，再交付

来源文件：
- `03-审核与问题/REPORTING_RULES.md`
- `03-审核与问题/STATE_TRANSITIONS.md`
- `03-审核与问题/PRE_COMMIT_RULES.md`
- `03-审核与问题/Definition of Done.md`

---

## Layer 2：项目过程层（仅在 NeoDev 项目推进时加载）

作用：约束当前项目、本周目标、任务优先级、审核与执行节奏。

来源文件：
- `01-目标与里程碑/本周目标与里程碑.md`
- `01-目标与里程碑/Week1任务拆解.md`
- `02-任务与执行/本周任务执行表.md`
- `02-任务与执行/TASK_STATE_BOARD.md`
- `02-任务与执行/EXECUTION_HEARTBEAT.md`
- `03-审核与问题/审核清单.md`
- `D:\PycharmProjects\neodev\docs\WEEK1_EXECUTION_BACKLOG.md`
- `D:\PycharmProjects\neodev\docs\CODEX_WORKFLOW.md`
- `D:\PycharmProjects\neodev\docs\REVIEW_GATE.md`

---

## Layer 3：动作门禁层（按动作激活）

作用：在具体动作发生前才加载，用作门禁。

### 开始任务前加载
- `scripts/start-task.ps1`
- `02-任务与执行/TASK_STATE_BOARD.md`
- `02-任务与执行/EXECUTION_HEARTBEAT.md`

### 汇报前加载
- `scripts/report-task.ps1`
- `scripts/check-reporting.ps1`
- `03-审核与问题/REPORTING_RULES.md`

### 提交前加载
- `scripts/commit-task.ps1`
- `scripts/check-state.ps1`
- `scripts/check-heartbeat.ps1`
- `03-审核与问题/PRE_COMMIT_RULES.md`
- `D:\PycharmProjects\neodev\docs\REVIEW_GATE.md`

---

## 当前原则

以后不再把全部规则平铺加载，而是：
- 先常驻基础层
- 默认加载通用执行层
- 做 NeoDev 项目时加载项目过程层
- 在具体动作前按需激活动作门禁层
