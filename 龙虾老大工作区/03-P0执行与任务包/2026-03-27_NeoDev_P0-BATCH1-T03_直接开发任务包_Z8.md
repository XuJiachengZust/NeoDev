# NeoDev P0-BATCH1-T03 直接开发任务包（Z8）

日期：2026-03-27  
作者：子智能体 Z8  
任务 ID：P0-BATCH1-T03  
范围：Plan 对象 + 计划审批页 + 审批栅栏（M2）  
上游依据：
- `2026-03-27_NeoDev_P0统一对象字典_状态机_三道栅栏规格基线_Z6.md`
- `2026-03-27_NeoDev_P0第一批执行任务包_Z5.md`
- `2026-03-27_NeoDev_P0_PRD草稿_人机协作研发闭环层.md`
- `2026-03-27_NeoDev_P0页面信息架构与对象模型状态机草稿_Z2.md`

---

## 1. 任务定位

T03 的目标不是把“执行”做完，而是把 **执行前必须经过的计划批准节点** 做成系统强约束。

一句话收口：

> 让一个已经到 `plan_ready` 的 Work Item，能够生成一版 Plan，进入计划审批页，被明确批准/退回/阻塞；在 `plan_state=approved` 前，任何正式执行入口都必须被审批栅栏拦住。

这条线是 NeoDev P0 与普通 AI 生成器的分水岭。审批不是备注，不是评论，也不是弱提醒，而是进入执行前的主流程节点。

---

## 2. 目标与边界

### 2.1 目标
1. 落实 Plan 对象最小字段、版本规则、状态机。
2. 落实计划审批页的最小模块、动作、回退路径。
3. 落实审批栅栏的系统阻断逻辑：**未审批不得进入正式执行。**
4. 让任务列表/详情摘要能看见“待审批 / 已批准 / 阻塞 / 已失效计划”。
5. 产出可直接进入前后端开发的拆分顺序与验收口径。

### 2.2 边界
**本任务只到进入执行前，不进入 M3/M4。**

明确包含：
- Plan 对象建模
- Plan 生成输入/输出口径
- Plan 版本替代规则（`superseded`）
- 计划审批页 UI/交互/动作
- Work Item 与 Plan 的联动状态流转
- 审批栅栏后端拦截逻辑
- M2 样例与回归验收

明确不包含：
- 真实执行编排
- Artifact / Evidence / Acceptance 落地
- 多级审批与复杂权限体系
- 智能负责人推荐、复杂优先级算法
- 复杂评论系统

---

## 3. 直接开发拆分总览

建议把 T03 切成 5 个顺序明确、边界清晰的开发子任务，按 **对象基线 → 状态与拦截 → 页面交互 → 联调验收 → 列表摘要补强** 的顺序推进。

### T03-D1：Plan 对象与版本规则落地
### T03-D2：审批状态流转与审批栅栏落地
### T03-D3：计划审批页最小交互落地
### T03-D4：Plan 生成样例、回归样例与联调验收
### T03-D5：列表/详情摘要中的计划状态可视化补齐

其中 D1-D3 是主路径，D4 是收口，D5 是提升可操作性的低风险补位。

---

## 4. 开发子任务明细

## T03-D1：Plan 对象与版本规则落地

### 任务顺序
第 1 个，必须最先做。

### 目标
把 Z6 中的 Plan 对象基线真正落成开发可用的数据契约，避免前端页面和后端状态各写一套。

### 边界
只解决 Plan 的数据结构、字段来源、版本规则、合法性校验；不做审批页 UI。

### 涉及页面 / 对象
- 页面：可执行对象页（生成 Plan 入口）、计划审批页（读取/编辑 Plan）
- 对象：`Plan`、`Work Item`、`Task`、`Risk`

### 必须落地的字段
以 Z6 为准，最小必有：
- `plan_id`
- `work_item_id`
- `version`
- `based_on_goal`
- `based_on_boundary`
- `based_on_context_refs`
- `task_breakdown`
- `dependencies`
- `execution_order`
- `key_risks`
- `approval_comment`
- `approval_constraints`
- `approval_by`
- `approval_at`
- `plan_state`
- `superseded_by`
- `created_at`
- `updated_at`

### 核心规则
1. 生成 Plan 时必须冻结 `goal / boundary / context_refs` 快照。
2. 同一 Work Item 同时只能有一个当前有效 Plan。
3. 若 Goal / Boundary / 关键 Success Criteria 变化，旧 Plan 必须转 `superseded`。
4. `plan_state=approved` 前，Work Item 不得进入 `executing`。
5. `Task` 是 Plan 的执行单元，不得反向替代 Work Item 主语义。

### 状态变化
- Plan：`draft -> generated -> pending_approval`
- Work Item：`plan_ready -> plan_pending_approval`

### 验收标准
- 后端/数据契约能表达完整 Plan 最小字段。
- 生成出来的 Plan 包含任务拆解、依赖、顺序、风险、依据快照。
- 可区分 `rejected` 与 `superseded`，且两者回退语义不同。
- 能证明同一 Work Item 不会并存两个 active approved Plan。

### 风险
- 把 Plan 做成普通 checklist，丢失“依据快照”和“版本替代”语义。
- 继续偷用 Work Item 字段代替 Plan 字段，导致对象边界再次混乱。

### 推荐提交信息
- `feat(plan): add plan object schema and versioning rules`
- `feat(plan): persist plan basis snapshots and supersede semantics`

---

## T03-D2：审批状态流转与审批栅栏落地

### 任务顺序
第 2 个，紧跟 D1。

### 目标
把“未审批不得执行”从文档规则变成系统约束，落成后端/服务层/状态机拦截。

### 边界
只做状态流转、动作校验、阻断返回；不追求复杂权限体系。

### 涉及页面 / 对象
- 页面：计划审批页、可执行对象页、执行入口、任务列表/首页
- 对象：`Work Item`、`Plan`

### 必须支持的动作
- `generate_plan`
- `submit_for_approval`
- `approve_plan`
- `reject_plan`
- `block_plan`
- `start_execution`
- `supersede_plan`

### 审批栅栏规则
触发时机：
- 在计划审批页点击批准
- 在计划审批页点击启动正式执行
- 任何试图把 Work Item 从 `plan_pending_approval` 推进到 `approved/executing` 的动作

阻断条件：
1. 不存在已生成的 Plan。
2. Plan 缺少任务拆解 / 依赖 / 执行顺序。
3. Plan 未引用 Goal / Boundary / Context 快照。
4. 存在高风险越界项且未被审批意见接纳。
5. 尚未发生明确审批动作。
6. Work Item 的 Goal / Boundary 已变化，当前 Plan 失效。

放行条件：
1. 已存在当前有效 Plan。
2. Plan 包含拆解、顺序、依赖、关键风险。
3. 审批人做出正式批准动作。
4. 无未处理高风险越界项。
5. Plan 与当前 Goal / Boundary 一致。

### 状态变化
- Plan：`generated -> pending_approval -> approved / rejected / superseded`
- Work Item：`plan_ready -> plan_pending_approval -> approved / blocked / clarifying`
- 启动执行动作：`approved -> executing`

### 回退语义
- `rejected`：计划内容不足或审批不通过，回到 `clarifying` 或 `plan_ready`
- `superseded`：目标/边界变化，旧计划失效，由新版本替代
- `blocked`：外部依赖阻断，不是计划内容修订

### 验收标准
- 没有 approved Plan 时，任何正式执行入口都返回 block。
- `plan_pending_approval` 不能直接跳到 `executing`。
- `rejected` 和 `superseded` 的返回值、状态结果、前端文案可区分。
- 所有状态变更都附带动作、时间、人、原因。

### 风险
- 把审批只做成前端按钮禁用，后端未真正拦截。
- 把 rejected / blocked / superseded 混成一个退回态，后续无法判定该补计划、补边界还是等外部依赖。

### 推荐提交信息
- `feat(approval-gate): enforce approval before execution`
- `feat(workitem): add plan approval transitions and block rules`

---

## T03-D3：计划审批页最小交互落地

### 任务顺序
第 3 个，在 D1/D2 基础上进行。

### 目标
把计划审批页做成一个最小但完整的正式决策页面，而不是只展示 AI 输出。

### 边界
只做 M2 最小页：一屏完成审阅依据、查看计划、输入审批意见、执行批准/退回/阻塞。

### 涉及页面 / 对象
- 页面：计划审批页
- 对象：`Plan`、`Work Item`、`Task`、`Risk`

### 页面最小模块
1. **计划总览区**
   - Plan 摘要
   - 任务拆解
   - 执行顺序
   - 依赖关系
   - 关键风险
2. **计划依据区**
   - Goal 快照
   - Boundary 快照
   - Context 引用摘要
   - 当前是否存在边界漂移提示
3. **审批意见区**
   - 审批意见输入
   - 附加限制条件输入
   - 当前栅栏检查结果
4. **审批动作区**
   - 批准
   - 退回补充
   - 标记阻塞
   - （仅在已批准后展示）启动执行

### 关键交互要求
- 页面进入时必须能看见“这版计划依据什么生成”。
- 退回时必须选择回退方向：`clarifying` 或 `plan_ready`。
- 阻塞时必须填写结构化 `block_reason`。
- 若页面检测到 Goal / Boundary 已变化，应提示该 Plan 即将或已经 `superseded`。
- 已批准后才出现或放开“启动执行”动作。

### 状态变化
- 点击“生成 Plan”：Work Item `plan_ready -> plan_pending_approval`；Plan `draft/generated -> pending_approval`
- 点击“批准”：Plan `pending_approval -> approved`；Work Item `plan_pending_approval -> approved`
- 点击“退回”：Plan `pending_approval -> rejected`；Work Item `-> clarifying` 或 `plan_ready`
- 点击“阻塞”：Work Item `-> blocked`
- 点击“启动执行”：Work Item `approved -> executing`

### 验收标准
- 页面至少覆盖计划总览、计划依据、审批意见、审批动作四大模块。
- 批准前无法触发正式执行。
- 审批意见、限制条件、审批人、审批时间可落库或形成状态记录。
- 页面能展示当前 block 原因与回退方向。

### 风险
- 页面只显示“结果”，不显示“依据”，会让审批退化成拍脑袋确认。
- 页面写太重，塞入执行页/验收页语义，破坏 P0 的对象边界。

### 推荐提交信息
- `feat(plan-page): build plan approval page for M2`
- `feat(plan-page): add approval actions and basis panels`

---

## T03-D4：Plan 生成样例、回归样例与联调验收

### 任务顺序
第 4 个，用来收口主路径。

### 目标
确保 T03 不是“状态机看起来对”，而是真的能被演示、回归、派工。

### 边界
只做 M2 样例与联调，不进入 Artifact/Acceptance。

### 涉及页面 / 对象
- 页面：可执行对象页、计划审批页、任务列表/首页
- 对象：`Work Item`、`Plan`

### 至少准备的样例
1. 正常批准路径样例
2. 退回补充路径样例
3. 边界变化导致 `superseded` 的样例
4. 未审批直接执行被拦截的反例

### 验收演示步骤
1. 从一个 `plan_ready` 的 Work Item 生成 Plan。
2. 查看任务拆解、依赖、顺序、风险与依据。
3. 执行批准动作，进入 `approved`。
4. 尝试从未批准版本直接执行，验证系统 block。
5. 修改 Boundary，验证旧 Plan 转 `superseded`，并要求重生成。

### 验收标准
- 至少 2 条正反向回归流程可跑通。
- 演示中可清楚证明“审批是主流程节点，不是备注”。
- 列表页或详情摘要能看见待审批、已批准、阻塞、已失效计划。

### 风险
- 只做 happy path，没覆盖边界变化和误操作直进执行。
- 联调时页面状态与后端状态名不一致。

### 推荐提交信息
- `test(plan-flow): add approval and supersede regression cases`
- `docs(m2): add plan approval demo fixtures and acceptance checklist`

---

## T03-D5：列表/详情摘要中的计划状态可视化补齐

### 任务顺序
第 5 个，可与 D4 局部并行，但不要先于 D1/D2。

### 目标
让负责人不进详情也能识别哪些 Work Item 正卡在审批、哪些已批准、哪些已阻塞、哪些计划已失效。

### 边界
只补最小摘要，不做复杂仪表盘。

### 涉及页面 / 对象
- 页面：任务列表/首页、Work Item 详情摘要区
- 对象：`Work Item`、`Plan`

### 最小展示项
- Work Item 标题
- Work Item 主状态
- 当前 Plan 版本号
- 当前 Plan 状态
- 当前阻断原因 / block_reason
- 当前待处理动作（待审批 / 待补计划 / 已批准可执行 / 已阻塞）
- 最近更新时间

### 验收标准
- `plan_pending_approval` 的任务可从列表直接识别。
- `blocked` 与 `clarifying` 不混淆。
- 已 `superseded` 的旧计划不会被误显示为当前有效计划。

### 风险
- 列表仍只展示 Work Item 状态，不展示 Plan 摘要，导致负责人看不出审批积压。

### 推荐提交信息
- `feat(list): surface current plan status and pending actions`
- `feat(detail): add work item plan summary card`

---

## 5. 推荐开发顺序

### 推荐顺序
1. **T03-D1 Plan 对象与版本规则落地**
2. **T03-D2 审批状态流转与审批栅栏落地**
3. **T03-D3 计划审批页最小交互落地**
4. **T03-D4 样例/回归/联调验收**
5. **T03-D5 列表与摘要补齐**

### 为什么这样排
- 没有 D1，页面和后端会各自发明 Plan。
- 没有 D2，审批依然只是 UI 演戏。
- 没有 D3，负责人没有真正可用的正式决策界面。
- D4 是证据，D5 是可操作性补强。

---

## 6. 页面与对象读写边界

### 6.1 可执行对象页
- 主对象：`Work Item`
- 本页对 T03 的唯一关键动作：发起“生成 Plan / 进入计划”
- 不应在这里深度编辑 `task_breakdown`、`dependencies`、`approval_comment`

### 6.2 计划审批页
- 主对象：`Plan`
- 次对象：`Work Item`、`Task`、`Risk`
- 主写内容：
  - `task_breakdown`
  - `dependencies`
  - `execution_order`
  - `key_risks`
  - `approval_comment`
  - `approval_constraints`
  - 审批动作
- 不应主写：
  - `raw_input`
  - Work Item 原始来源字段
  - Artifact / Acceptance 字段

### 6.3 任务列表/首页
- 主对象：`Work Item`
- 次对象：Plan 摘要
- 只做状态可视化与导航，不做审批主写

---

## 7. T03 关键状态口径

## 7.1 Work Item
- `plan_ready`：满足清晰度栅栏，可以生成计划
- `plan_pending_approval`：已有待审计划，不能执行
- `approved`：计划已获批准，可以启动正式执行
- `blocked`：因外部依赖或明确阻断停住
- `clarifying`：计划被退回，需要补边界/目标/信息

## 7.2 Plan
- `draft`：尚未形成完整计划对象
- `generated`：已生成计划初稿
- `pending_approval`：待正式审批
- `approved`：已通过审批
- `rejected`：被退回补充
- `superseded`：因新版本/边界变化被替代

### `rejected` 与 `superseded` 的强区分
- `rejected` = 审批不通过，需要补计划或补信息
- `superseded` = 计划曾经有效，但因新的 Goal/Boundary/关键标准变化而失效

---

## 8. 最小验收清单

只要有任意一条不满足，T03 就不算完成：

1. 能从 `plan_ready` 生成一版 Plan。
2. Plan 至少包含：任务拆解、执行顺序、依赖关系、关键风险、依据快照。
3. 计划审批页至少包含：计划总览、计划依据、审批意见、审批动作。
4. `plan_pending_approval` 的 Work Item 无法直接进入 `executing`。
5. 批准后，Plan 与 Work Item 状态同步进入可执行状态。
6. 退回后，能明确回到 `clarifying` 或 `plan_ready`。
7. Goal / Boundary 变化后，旧 Plan 必须被标记为 `superseded`。
8. 列表或摘要能看出“待审批 / 已批准 / 阻塞 / 已失效计划”。

---

## 9. 主要风险与控制

### 风险 1：审批流变成表面按钮
- 表现：前端看起来有批准按钮，但后端仍允许直接执行
- 控制：执行入口必须经过统一审批栅栏校验

### 风险 2：Plan 退化成普通 checklist
- 表现：只有子任务列表，没有依据快照、依赖和顺序
- 控制：Plan 必须同时具备拆解、顺序、依赖、关键风险、依据快照

### 风险 3：对象边界再次混乱
- 表现：审批页开始改 raw_input、结果页字段或 Acceptance 字段
- 控制：坚持“计划页主写 Plan，对象页主写 Work Item”

### 风险 4：`rejected` / `blocked` / `superseded` 混淆
- 表现：所有失败都叫“退回”
- 控制：把回退原因结构化，并在状态、页面文案、后端返回中统一区分

### 风险 5：审批负担被感知为额外流程成本
- 表现：负责人不愿用
- 控制：页面必须显式展示依据、风险、边界和责任记录，让审批动作体现“降低背锅风险”而不是纯流程负担

---

## 10. 适合直接派工给研发的任务描述模板

> 基于 NeoDev P0 Z6 规格基线与 T03 任务包，实现 M2 计划生成与审批闭环：围绕 Plan 对象、计划审批页、审批状态流转、审批栅栏、Plan 版本替代规则开展开发。必须满足“未审批不得进入正式执行”，并能区分 rejected / blocked / superseded 的不同回退语义；边界仅到进入执行前，不进入 Artifact / Acceptance。

---

## 11. 最适合先开工的前 3 个开发子任务

### 1) T03-D1：Plan 对象与版本规则落地
最先做。因为这是所有页面、接口、状态和回归口径的共同母版。

### 2) T03-D2：审批状态流转与审批栅栏落地
第二个做。因为 NeoDev 的关键差异不是“能生成计划”，而是“未批准不能执行”。

### 3) T03-D3：计划审批页最小交互落地
第三个做。因为负责人真正感知产品价值的，就是能在一页中看见依据、风险、计划并做正式决策。

---

## 12. 最终收口

T03 最小可执行拆分的核心不是多做几个页面，而是把以下三件事连成一根硬链路：

1. `plan_ready` 的 Work Item 能生成有依据快照的 Plan；
2. Plan 必须在计划审批页经历正式批准/退回/阻塞；
3. 在审批栅栏放行前，系统必须阻止任何正式执行入口。

做到这里，NeoDev P0 的“先计划后执行”才算从概念进入工程现实。