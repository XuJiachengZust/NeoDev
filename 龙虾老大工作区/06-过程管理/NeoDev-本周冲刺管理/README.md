# NeoDev 本周冲刺管理（目标导向 + 渐进式加载版）

目标期限：下周一前完成本周任务。  
管理方式：高度遵循软件工程。  
固定路线：**里程碑驱动 → 持续执行 → 节点审核 → 老大校验 / 决策**
约束方式：**分层约束，渐进式加载，按动作触发门禁**

## 核心原则

### 0. 渐进式加载
不再一次性平铺全部规则，而是按层级加载：
- Layer 0：基础常驻层
- Layer 1：通用执行层
- Layer 2：项目过程层
- Layer 3：动作门禁层

详细见：
- `CONSTRAINTS_INDEX.md`
- `LOAD_ORDER.md`

### 1. 目标导向
所有文档、任务、执行记录都必须服务于明确目标，而不是为了留档而留档。

### 2. 里程碑驱动
执行必须在里程碑指导下推进，不允许脱离里程碑随意扩散。

### 3. 持续执行
不是只做计划。进入执行后，应持续推进，并把产出、状态、问题及时落在文档中。

### 4. 节点审核
达到关键节点后先进入审核，确认质量、范围、风险，再决定是否提交给老大。

### 5. 老大校验
当进入需要你审的阶段，我会在当前 Discord 这里主动通知你。

## 目录说明

- `01-目标与里程碑/`
  - 放目标、范围、阶段里程碑、优先级、验收目标
- `02-任务与执行/`
  - 放任务拆解、执行进度、状态表、阶段产出
- `03-审核与问题/`
  - 放审核记录、问题清单、风险、返工项
- `04-待老大决策与校验/`
  - 放需要老大确认、审批、拍板、最终校验的内容
- `archive/`
  - 放归档材料

## 运行机制

### 我负责
- 在里程碑指导下持续执行
- 按目标推进任务
- 记录过程状态和问题
- 在需要老大审核时主动在这里通知
- 在汇报前先运行状态/心跳/汇报检查脚本
- 在提交前遵守 `PRE_COMMIT_RULES.md`

### 老大负责
- 对关键节点进行审核 / 决策 / 最终校验

## 最小自动约束（B 方案）

已落地脚本：
- `scripts/check-state.ps1`
- `scripts/check-heartbeat.ps1`
- `scripts/check-reporting.ps1`
- `scripts/start-task.ps1`
- `scripts/report-task.ps1`
- `scripts/commit-task.ps1`

已落地规则：
- `03-审核与问题/REPORTING_RULES.md`
- `03-审核与问题/STATE_TRANSITIONS.md`
- `03-审核与问题/PRE_COMMIT_RULES.md`

以后默认要求：
1. 开始任务前优先通过 `start-task.ps1`
2. 任务执行前看状态板
3. 执行中写心跳
4. 汇报前跑 `report-task.ps1`
5. 提交前先检查 staged 文件，并优先通过 `commit-task.ps1`
6. 提交前仍需遵守 `PRE_COMMIT_RULES.md`

## 状态建议

- `target_defined`：目标已定义
- `planned`：已规划
- `executing`：执行中
- `review_pending`：待审核
- `rework`：返工中
- `boss_check_pending`：待老大校验
- `done`：已完成

## 当前要求
本周所有行动都必须围绕里程碑推进，并在需要老大审核时主动发起通知。

## 当前推荐入口
- 约束索引：`CONSTRAINTS_INDEX.md`
- 加载顺序：`LOAD_ORDER.md`
- 开始任务：`scripts/start-task.ps1`
- 汇报前检查：`scripts/report-task.ps1`
- 提交前检查：`scripts/commit-task.ps1`
