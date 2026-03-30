# LOAD_ORDER

说明：这是当前约束体系的渐进式加载顺序。

---

## 默认加载顺序

### Step 1：常驻加载 Layer 0
始终生效：
- 身份
- 老大边界
- 长期偏好
- 诚实、严谨、规划导向

### Step 2：任务开始前加载 Layer 1
任何任务都默认加载：
- 目标/边界优先
- 状态机基础规则
- 汇报带证据
- 最小可用单元提交
- 先审核再交付

### Step 3：进入 NeoDev 主线时加载 Layer 2
只在当前项目推进时加载：
- 本周目标
- backlog
- 审核清单
- DoD
- 状态板与心跳
- Codex 工作流
- Review Gate

### Step 4：按动作激活 Layer 3

#### 动作 A：开始任务
必须先：
- 明确目标
- 明确边界
- 使用 `start-task.ps1` 或至少同步状态板与心跳

#### 动作 B：汇报状态
必须先：
- 运行 `report-task.ps1`
- 若结果不是 `REPORTING_ALLOWED_USE_EVIDENCE_TEMPLATE`，则不应汇报推进状态

#### 动作 C：提交 git
必须先：
- 检查 staged 文件范围
- 运行 `commit-task.ps1` 或遵守同等检查流程
- 对照 `PRE_COMMIT_RULES.md` 与 `REVIEW_GATE.md`

---

## 升级规则

如果后续约束越来越多，优先把新增约束放进已有层级，而不是平铺新增文件。

### 新增规则放置原则
- 身份/长期偏好 → Layer 0
- 所有任务都适用 → Layer 1
- 仅 NeoDev 项目适用 → Layer 2
- 仅某个动作前使用 → Layer 3

---

## 当前目标
通过渐进式加载，减少规则过载，并提升规则与场景的匹配度。
