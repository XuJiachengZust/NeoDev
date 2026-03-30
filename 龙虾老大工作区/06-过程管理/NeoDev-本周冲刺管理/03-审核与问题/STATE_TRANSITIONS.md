# STATE_TRANSITIONS

说明：这是最小强状态机的跃迁规则。所有任务必须先定义目标与边界，再进入状态流转。

## 状态集合
- planned
- ready
- executing
- artifact_ready
- review_pending
- rework
- boss_check_pending
- done
- blocked
- replan_required

## 强规则

### 规则 1：任务不能直接模糊执行
进入 `executing` 前，必须明确：
- 目标
- 边界
- 当前动作
- 预期产物

### 规则 2：planned -> ready
必须已具备：
- 明确目标
- 明确边界
- 明确验收标准

### 规则 3：ready -> executing
必须同步写入：
- TASK_STATE_BOARD
- EXECUTION_HEARTBEAT

### 规则 4：executing 超时
- 30 分钟无心跳：异常
- 60 分钟无产物：必须转 `blocked` 或 `replan_required`

### 规则 5：executing -> artifact_ready
必须已有至少一个可验证产物：
- 文件改动
- 文档
- commit
- 审核材料
- 明确阻塞分析

### 规则 6：artifact_ready -> review_pending
必须明确：
- 审核对象
- 风险
- 验证结果

### 规则 7：review_pending -> boss_check_pending
必须满足：
- 已完成审核
- 有清晰待老大确认点
- 有产物路径

### 规则 8：没有状态变化，不算推进
如果没有状态跃迁、没有心跳、没有证据，则执行无效。
