# NeoDev Codex 开发治理外挂 Harness 设计（修正版）

> 日期：2026-04-02  
> 主项目：`D:\PycharmProjects\NeoDev`  
> 参考项：`D:\PycharmProjects\NeoDev\docs\NEODEV_HARNESS_DESIGN_2026-04-02.md`、`C:\Users\AH\IdeaProjects\dsc\harness`  
> 文档性质：设计修正版 / 治理外挂方案 / 非 runtime 内核方案

---

## 0. 先给结论

NeoDev 需要的不是“再造一个 agent runtime”，而是一层**位于 NeoDev 主项目之外、服务于 Codex 开发协作过程的外挂治理层**。

这层 harness 的职责不是替代 NeoDev 的产品能力，不是替代 deepagents / LangGraph / agent_factory / session / checkpointer，也不是把 Codex 变成产品功能本身；它的职责是：

- 在**开发时**约束 Codex 如何理解任务；
- 在**开发时**约束 Codex 如何加载上下文；
- 在**开发时**约束主/子智能体如何分工、如何验收；
- 在**开发时**把任务、产物、评审和沉淀组织起来；
- 让 Codex 从“临场 prompt coding”升级为“可治理、可回溯、可复盘的开发外挂流程”。

一句话：

**这是 NeoDev 项目的 Codex 开发治理外挂层，不是 NeoDev 产品 runtime 内核。**

---

## 1. 设计目标与问题重述

基于已有旧稿与 dsc 的 harness 参考，这次修正版要解决的核心问题不是“NeoDev 如何实现 agent”，而是：

1. **如何把 Codex 的开发协作能力外挂化**，避免深度侵入 NeoDev 产品代码；
2. **如何明确边界**，避免把开发治理层误做成产品运行时的一部分；
3. **如何定义一套最小可落地的治理协议**，包括：
   - bootstrap
   - progressive loading
   - task contract
   - review contract
   - artifact ledger
   - delegation policy
4. **如何给出一个低侵入、可逐步落地的文件结构**；
5. **如何保证不做破坏性修改**，优先产出文档、模板、约束和轻量集成点。

---

## 2. 定位：它到底是什么，不是什么

### 2.1 它是什么

NeoDev Codex Harness 是一层**开发治理外挂层（development governance add-on）**。

它服务的对象是：

- Codex 主智能体
- Codex 子智能体 / delegated worker
- 与 Codex 协作的开发者
- NeoDev 仓库内用于开发协作的文档、任务、审查、产物目录

它主要解决的是**开发阶段的“行为治理”与“协作协议”问题**。

### 2.2 它不是什么

它**不是**以下内容：

1. **不是 NeoDev 产品的 runtime 内核**
   - 不替代 `src/deepagents/`
   - 不替代 `src/service/agent_factory.py`
   - 不替代 session / memory / checkpointer / SSE
   - 不替代产品级 agent profile

2. **不是产品用户可见能力本身**
   - 不把 harness 当作对最终用户暴露的功能模块
   - 不要求前端直接感知 harness 存在

3. **不是新的通用 prompt 仓库**
   - 不应演变成“所有 prompt 都丢进这里”的大杂烩
   - 它只收纳稳定治理规则、模板、协作协议

4. **不是强耦合代码框架**
   - 第一阶段不要求重写 runtime
   - 第一阶段不要求大规模侵入产品代码
   - 第一阶段允许以文档 + 轻量脚本 + 最小 glue code 方式落地

### 2.3 与 NeoDev 主项目的关系

建议明确使用下面这句话作为架构边界定义：

> NeoDev 主项目负责产品 runtime 与业务能力；Codex Harness 负责开发期的智能体治理与协作协议。前者服务产品运行，后者服务开发过程。

即：

- **主项目**：生产能力、产品逻辑、agent runtime、会话与工具执行
- **外挂 harness**：开发规则、任务分派协议、验收机制、产物组织、经验沉淀

这是本设计最重要的边界。

---

## 3. 为什么要外挂化，而不是塞进 NeoDev runtime

### 3.1 因为 NeoDev 现有 runtime 已经不弱

旧稿已经分析得很清楚：NeoDev 现有代码里已经有：

- 会话与消息持久化
- checkpointer
- agent_factory
- backend protocol
- composite backend
- sandbox workspace
- subagent middleware
- skills / memory / prompt middleware

也就是说，NeoDev 缺的不是“会执行”，而是“如何治理执行”。

### 3.2 因为 dsc 给出的价值主要是治理，不是 runtime

dsc 的 `harness/` 参考项真正有价值的是：

- `BOOTSTRAP.md`：强入口
- `master-prompt.md`：仓库级治理原则
- `agent-loop-rule.md`：主从闭环
- `subagent-delegation-rule.md`：任务分派协议
- `progressive-loading-rule.md`：渐进加载
- `harness-deposition-rule.md`：经验沉淀

这些东西，本质上都是**治理协议**，不是 runtime 引擎。

### 3.3 外挂化的直接收益

外挂化有四个现实收益：

1. **低侵入**：先不动 NeoDev 核心架构；
2. **可试错**：治理规则可以快速迭代，不影响产品主流程；
3. **可替换**：以后即便不是 Codex，也可迁移同一治理层；
4. **可审计**：文档、模板、ledger、review 都能单独演化。

---

## 4. 设计原则

本修正版建议明确以下 8 条原则。

### 4.1 外挂优先，侵入最小

默认把 harness 放在 NeoDev 项目外层或 docs/devtools 邻接层，以**文档、模板、工作区目录、轻量 glue code**为主，不直接改写产品核心。

### 4.2 治理优先，不重复造 runtime

harness 只处理：

- 加载什么
- 怎么分派
- 怎么验收
- 产物怎么落
- 经验怎么沉淀

不处理：

- 模型底层调用链
- 工具执行底座
- conversation 持久化主链路

### 4.3 文档先行，代码后补

第一阶段先把规则、模板、目录结构和流程定义清楚，再决定哪些点值得代码化。

### 4.4 Progressive Loading，不全量灌 prompt

harness 不是“更多规则 = 更强”。应只按当前任务命中范围加载最小必要规则。

### 4.5 Contract First

所有多步骤任务默认要有 contract，至少包括：

- 任务目标
- 边界
- 禁止事项
- 预期产物
- 验收标准

### 4.6 Review 不是可选项

“执行完成”不等于“任务完成”。所有非极小任务都需要 review contract 支撑的验收结论。

### 4.7 Artifact 可回溯

必须能回答：

- 谁做了什么
- 基于什么 contract 做的
- 产物在哪
- 谁验收的
- 最终结论是什么

### 4.8 沉淀稳定经验，拒绝一次性噪音

只沉淀长期稳定的规则、模板、协作约束；不把临时对话垃圾写进 harness。

---

## 5. 参考 dsc 后，NeoDev 该吸收什么，不该照搬什么

### 5.1 应吸收的部分

来自 dsc 的高价值部分：

1. **Bootstrap 强入口**
2. **Master Prompt 总治理原则**
3. **Agent Loop 闭环**
4. **Subagent Delegation 分派模板**
5. **Progressive Loading**
6. **Harness Deposition 沉淀机制**

### 5.2 不应照搬的部分

不建议把 dsc 的目录和规则原样拷贝进 NeoDev，原因：

- dsc 是聚合仓库治理语境；
- NeoDev 是单一主项目 + 产品代码仓库语境；
- NeoDev 当前问题更偏“Codex 开发治理外挂”，不是多业务域聚合导航。

因此，NeoDev 只需要借鉴 dsc 的治理思想，不应机械复刻其业务分层和目录命名。

---

## 6. 推荐架构：双层结构，而不是一层糊在产品里

建议采用**双层结构**。

### 6.1 第一层：外挂 Harness Workspace（主治理层）

建议作为 NeoDev 邻接的开发治理空间存在，例如：

```text
D:\PycharmProjects\NeoDev\codex-harness\
```

或保守一些，若必须放在主仓库内，则建议：

```text
D:\PycharmProjects\NeoDev\devtools\codex-harness\
```

这一层放：

- bootstrap
- rules
- templates
- examples
- scripts
- task ledgers
- working artifacts
- review reports

### 6.2 第二层：NeoDev 主项目最小接入点（可选 glue）

NeoDev 主仓库仅保留极少数接入点，例如：

- 可选的 `harness_loader.py`
- 少量 adapter / helper
- docs 内的设计说明与接入说明

也就是说：

- **治理资产在外挂层**
- **产品 glue 在主项目中可选接入**

这才符合“外挂 harness”定位。

---

## 7. 推荐目录结构

### 7.1 首选方案：外挂目录独立

```text
D:\PycharmProjects\NeoDev\codex-harness\
  README.md
  BOOTSTRAP.md
  system\
    master-prompt.md
    loading-policy.md
    glossary.md
  rules\
    development\
      progressive-loading-rule.md
      agent-loop-rule.md
      subagent-delegation-rule.md
      review-and-acceptance-rule.md
      artifact-ledger-rule.md
      delegation-policy-rule.md
      harness-deposition-rule.md
    project\
      neodev-project-boundary-rule.md
      requirement-doc-rule.md
      code-change-rule.md
      docs-edit-rule.md
  contracts\
    task-contract.template.md
    review-contract.template.md
    delegation-contract.template.md
    artifact-record.template.json
  examples\
    task-contract.example.md
    review-contract.example.md
    delegation.example.md
  scripts\
    bootstrap-loader.py
    ledger-init.py
    review-summary.py
  workspace\
    active\
      ACTIVE_TASK.md
      TASK_QUEUE.md
      LEDGER.json
    artifacts\
    contracts\
    reports\
    reviews\
    snapshots\
  docs\
    adoption-guide.md
    integration-notes.md
```

### 7.2 次选方案：若必须留在 NeoDev 仓库内

```text
D:\PycharmProjects\NeoDev\devtools\codex-harness\
  ... 同上 ...
```

### 7.3 为什么不建议直接叫 `NeoDev/harness/`

因为那样很容易让后续维护者误判：

- 这是产品 runtime 的一部分；
- 这是 agent 内核配置中心；
- 这是线上逻辑的一部分。

而本方案强调的是：

**它是 Codex 开发治理外挂层。**

所以命名上最好就与产品主运行层拉开距离。

如果出于现有仓库习惯，短期必须放在 `NeoDev/harness/`，则必须在 README 和 BOOTSTRAP 中强写边界声明。

---

## 8. Bootstrap 设计

### 8.1 Bootstrap 的职责

`BOOTSTRAP.md` 是整个外挂 harness 的唯一强入口。

它必须解决三件事：

1. 告诉 Codex：先读什么；
2. 告诉 Codex：不要全量乱读；
3. 告诉 Codex：这是开发治理外挂，不是产品 runtime 指令中心。

### 8.2 Bootstrap 最低应包含的内容

建议包含以下结构：

```md
# NeoDev Codex Harness Bootstrap

## 定位
- 本 harness 是 NeoDev 项目的开发治理外挂层
- 仅用于开发期 Codex 协作治理
- 不是 NeoDev 产品 runtime 内核

## 强制规则
- 禁止跳过本文件直接全量读取规则
- 禁止把本 harness 误解为产品功能说明
- 禁止一次性加载全部开发规则与项目规则

## 首批必读
1. system/master-prompt.md
2. rules/development/progressive-loading-rule.md
3. 若任务涉及多智能体执行或验收，再读 agent-loop-rule.md 与 subagent-delegation-rule.md

## 后续按需补读
- 文档任务 → docs-edit-rule.md
- 需求文档任务 → requirement-doc-rule.md
- 代码修改任务 → code-change-rule.md
- 需要评审 → review-and-acceptance-rule.md
- 需要沉淀规则 → harness-deposition-rule.md
```

### 8.3 Bootstrap 的关键语义

这份 bootstrap 的核心不是“导航目录”，而是给 Codex 明确一个行为模式：

- 先识别任务类型；
- 再识别是否涉及执行/验收；
- 再按需补读；
- 永不默认全量加载全部规则。

---

## 9. Progressive Loading 设计

### 9.1 问题来源

Codex 在仓库里做事时，最容易失控的事情之一就是：

- 看见很多规则就全读；
- 上下文越堆越长；
- 最终真正有效的约束反而被稀释。

### 9.2 设计目标

progressive loading 要保证：

- 任务只读取真正需要的治理规则；
- 多智能体任务一定加载 delegation / review 约束；
- 普通小任务不强行引入过重流程。

### 9.3 建议的加载层次

按层次加载：

#### Layer 0：Bootstrap 层
- `BOOTSTRAP.md`
- `system/master-prompt.md`

#### Layer 1：通用开发治理层
- `rules/development/progressive-loading-rule.md`

#### Layer 2：协作闭环层（按需）
- `agent-loop-rule.md`
- `subagent-delegation-rule.md`
- `review-and-acceptance-rule.md`

#### Layer 3：任务域规则层（按需）
- `docs-edit-rule.md`
- `requirement-doc-rule.md`
- `code-change-rule.md`

#### Layer 4：沉淀层（收尾按需）
- `harness-deposition-rule.md`

### 9.4 触发条件建议

| 任务类型 | 需要加载 |
|---|---|
| 只读调研 | Bootstrap + master + progressive |
| 文档重写 | 再加 docs-edit-rule |
| 多智能体拆解 | 再加 agent-loop + subagent-delegation |
| 需要验收 | 再加 review-and-acceptance |
| 需要规则沉淀 | 最后加 harness-deposition |

如果担心 markdown 表格在某些环境不友好，也可在实际文件里改成 bullet list。

---

## 10. Task Contract 设计

### 10.1 为什么要有 task contract

没有 task contract，Codex 很容易出现以下问题：

- 目标漂移；
- 越界扩写；
- 把建议当结论；
- 输出内容与真正任务不匹配；
- 无法复盘当时到底让它做了什么。

### 10.2 Task Contract 最小字段

建议至少包含：

- `task_id`
- `title`
- `goal`
- `in_scope`
- `out_of_scope`
- `inputs`
- `expected_outputs`
- `acceptance_criteria`
- `owner_role`
- `status`

### 10.3 Markdown 模板建议

```md
# Task Contract
- task_id:
- title:
- owner_role:
- goal:
- in_scope:
- out_of_scope:
- inputs:
- expected_outputs:
- acceptance_criteria:
- status:
```

### 10.4 适用于本次 NeoDev 文档任务的示例语义

像本次任务，就可以表达为：

- goal：重写 NeoDev Codex 外挂 harness 设计文档
- in_scope：定位、边界、外挂目录结构、bootstrap、progressive loading、task/review contract、artifact ledger、delegation policy、最小落地方案
- out_of_scope：不修改 NeoDev runtime 主链路，不大规模改代码，不落地线上产品功能
- expected_outputs：详细设计文档一份
- acceptance_criteria：能清楚回答“它是什么、不是什麽、怎么落地、最小怎么做、文件怎么摆”

---

## 11. Delegation Policy 与 Delegation Contract 设计

### 11.1 Delegation Policy：宏观规则

delegation policy 负责回答：

- 什么时候该派子智能体；
- 子智能体能做什么；
- 子智能体不能做什么；
- 父智能体如何收口；
- 什么情况下必须回到主智能体决策。

建议政策性规则如下：

1. 主智能体负责：规划、拆解、收口、验收判定；
2. 子智能体负责：执行、分析、整理、提出风险；
3. 子智能体不得：
   - 擅自改目标
   - 擅自扩大边界
   - 以主智能体身份做最终收口
4. 非极小任务默认要求独立 review；
5. 一旦发现范围变化、目标冲突、重大风险，必须回退主智能体重新分派。

### 11.2 Delegation Contract：单次分派协议

建议每次分派都用固定模板。

最小字段：

- `task_id`
- `role`（executor / reviewer / researcher）
- `goal`
- `context_scope`
- `allowed_paths`
- `forbidden_actions`
- `deliverables`
- `validation_criteria`
- `artifact_path`

模板示例：

```md
# Delegation Contract
- task_id:
- role:
- goal:
- context_scope:
- allowed_paths:
- forbidden_actions:
- deliverables:
- validation_criteria:
- artifact_path:
```

### 11.3 建议的角色分类

建议至少分三类：

- `researcher`：只读调研
- `executor`：执行产出
- `reviewer`：独立验收

不要让所有子智能体都被模糊叫做 “subagent”；角色明确后，输出风格和验收逻辑都会更稳定。

---

## 12. Review Contract 设计

### 12.1 为什么 Review Contract 必须单列

很多系统会有 task contract，却没有单独的 review contract。结果是：

- 执行者自己说“做完了”；
- 但没人知道“做得对不对”；
- 也没人知道“按什么标准判定”。

所以 review contract 必须独立。

### 12.2 Review Contract 最小字段

建议至少包含：

- `review_id`
- `task_id`
- `reviewer_role`
- `review_scope`
- `required_inputs`
- `checkpoints`
- `verdict_schema`
- `pass_criteria`
- `risk_reporting_rule`

### 12.3 Verdict 标准化

建议强制三值结论：

- `PASS`
- `FAIL`
- `RISK`

其中：

- `PASS`：目标达成，风险可接受；
- `FAIL`：未达成目标或明显偏离；
- `RISK`：基本达成但存在未清风险或边界问题，不能直接宣称完成。

### 12.4 Review 输出模板建议

```md
# Review Result
- review_id:
- task_id:
- verdict: PASS | FAIL | RISK
- summary:
- checklist:
- risks:
- missing_items:
- recommendation:
```

---

## 13. Artifact Ledger 设计

### 13.1 它解决什么问题

artifact ledger 用来回答：

- 这次任务产生了哪些文件；
- 哪些是 contract；
- 哪些是报告；
- 哪些是 review；
- 当前状态是什么。

没有 ledger，产物再多，也只是散落文件。

### 13.2 Ledger 最小记录模型

建议第一阶段直接用 JSON 文件即可，不必先上库。

最小结构示例：

```json
{
  "task_id": "TASK-2026-04-02-001",
  "title": "Rewrite NeoDev Codex harness design",
  "status": "artifact_ready",
  "contracts": [
    "workspace/contracts/TASK-2026-04-02-001.md"
  ],
  "reports": [
    "workspace/reports/TASK-2026-04-02-001.md"
  ],
  "reviews": [
    "workspace/reviews/TASK-2026-04-02-001.md"
  ],
  "artifacts": [
    "docs/NEODEV_CODEX_HARNESS_ADDON_DESIGN_2026-04-02_REVISED.md"
  ]
}
```

### 13.3 状态建议

建议状态尽量收敛，不要一开始过度复杂。第一阶段可先用：

- `planned`
- `executing`
- `artifact_ready`
- `review_pending`
- `done`
- `blocked`

如果后续与更严格控制层对齐，再扩展也不迟。

---

## 14. 推荐文件与工作区结构

建议在外挂层 workspace 中固定以下结构：

```text
workspace\
  active\
    ACTIVE_TASK.md
    TASK_QUEUE.md
    LEDGER.json
  contracts\
  reports\
  reviews\
  artifacts\
  snapshots\
```

### 14.1 各目录职责

- `active/ACTIVE_TASK.md`：当前主任务
- `active/TASK_QUEUE.md`：待办队列
- `active/LEDGER.json`：结构化索引
- `contracts/`：task / delegation / review contract
- `reports/`：执行报告
- `reviews/`：评审报告
- `artifacts/`：中间产物
- `snapshots/`：关键上下文快照

### 14.2 为什么这套结构适合外挂层

因为它不要求 NeoDev runtime 改数据库结构，也不要求改产品接口，只是把开发协作过程组织起来。

---

## 15. 最小落地方案（MVP）

本修正版建议的 MVP 不追求“功能很全”，而追求“外挂定位清晰、最小闭环成立”。

### 15.1 MVP 必做项

#### 1）建立外挂目录

至少建立：

- `README.md`
- `BOOTSTRAP.md`
- `system/master-prompt.md`
- `rules/development/progressive-loading-rule.md`
- `rules/development/agent-loop-rule.md`
- `rules/development/subagent-delegation-rule.md`
- `rules/development/review-and-acceptance-rule.md`
- `rules/development/artifact-ledger-rule.md`
- `rules/development/delegation-policy-rule.md`
- `rules/development/harness-deposition-rule.md`

#### 2）建立 contracts 模板

至少建立：

- `task-contract.template.md`
- `delegation-contract.template.md`
- `review-contract.template.md`
- `artifact-record.template.json`

#### 3）建立 workspace 目录

至少建立：

- `active/`
- `contracts/`
- `reports/`
- `reviews/`
- `artifacts/`

#### 4）产出 adoption guide

明确告诉维护者：

- 这是开发治理外挂层；
- 如何 bootstrap；
- 如何建 task contract；
- 如何做 review；
- 如何记录 ledger。

### 15.2 MVP 可选项

#### 1）轻量 loader 脚本

可以有一个脚本，比如：

- `scripts/bootstrap-loader.py`

作用：

- 根据任务类型拼出建议加载清单；
- 但不是强制依赖它。

#### 2）轻量 glue code

如果确实需要把 harness 接一点到 NeoDev 里，可以加一个**极轻量**的：

- `src/service/harness_loader.py`

职责仅限：

- 读取外挂 harness 中的 bootstrap/rules；
- 拼出 prompt bundle；
- 在开发模式下给 agent 增补治理上下文。

注意：

这一步是**可选增强**，不是 MVP 的前提。

---

## 16. 与 NeoDev 主项目的最小集成建议

### 16.1 原则：可接，不必深接

集成可以分两档。

#### 档 A：完全外挂、零代码侵入

只做：

- 文档
- 模板
- 工作区
- 使用约定

适合先试运行。

#### 档 B：轻量接入主项目

只在少量位置增加 glue：

- `src/service/harness_loader.py`
- 在 `agent_factory.py` 某些开发模式入口里读取 bundle

但依然坚持：

- 不改 NeoDev runtime 核心模型；
- 不把 harness 变成线上必需模块；
- 不让产品功能强依赖它。

### 16.2 不建议第一阶段做的事

以下事情不要在第一阶段做：

- 大改 `agent_factory.py` 主逻辑
- 大改 `deepagents/` middleware 结构
- 把所有 profile prompt 迁移到 harness
- 引入复杂数据库 schema
- 把 artifact ledger 绑定到线上会话持久化
- 做重型 HITL/审批流

这些都属于第二阶段以后才值得评估的事情。

---

## 17. 建议文件清单

### 17.1 文档层

建议至少新增以下文件（外挂目录内）：

```text
README.md
BOOTSTRAP.md
system/master-prompt.md
rules/development/progressive-loading-rule.md
rules/development/agent-loop-rule.md
rules/development/subagent-delegation-rule.md
rules/development/review-and-acceptance-rule.md
rules/development/artifact-ledger-rule.md
rules/development/delegation-policy-rule.md
rules/development/harness-deposition-rule.md
rules/project/neodev-project-boundary-rule.md
rules/project/docs-edit-rule.md
rules/project/requirement-doc-rule.md
rules/project/code-change-rule.md
contracts/task-contract.template.md
contracts/delegation-contract.template.md
contracts/review-contract.template.md
contracts/artifact-record.template.json
docs/adoption-guide.md
docs/integration-notes.md
```

### 17.2 若要给 NeoDev 主仓库加最小说明

建议补一个：

```text
D:\PycharmProjects\NeoDev\docs\CODEX_HARNESS_ADOPTION_NOTES.md
```

用于说明：

- 外挂目录在哪；
- 为什么不用把它并入 runtime；
- 哪些点可选接入。

---

## 18. 分阶段实施建议

### Phase 1：文档与结构立住

目标：先把外挂治理层“定义出来”。

产出：

- 外挂目录
- bootstrap
- core rules
- contract templates
- workspace 目录
- adoption guide

验收：

- 新任务可以基于模板创建 contract；
- 新任务有 review 模板；
- 产物可被 ledger 记录；
- 维护者能清楚理解边界。

### Phase 2：半自动化支持

目标：减少人工拼规则成本。

产出：

- bootstrap-loader.py
- ledger-init.py
- review-summary.py

验收：

- 能自动创建 task skeleton；
- 能自动初始化 ledger；
- 能汇总 review 结论。

### Phase 3：主项目轻量 glue

目标：在开发模式下让 NeoDev agent 可以按需读取 harness bundle。

产出：

- 可选的 `src/service/harness_loader.py`
- 少量接入点说明

验收：

- 不影响产品主逻辑；
- 可在特定开发流程中使用 harness；
- 关闭 glue 后不影响主系统运行。

### Phase 4：再考虑 reviewer agent / 更强治理

目标：有需要时再增强，而不是一开始做过头。

可选方向：

- reviewer 子智能体
- 更严格 delegation schema
- 更精细的 tool execution policy
- 与主项目会话视图做弱关联展示

---

## 19. 风险与防错

### 19.1 最大风险：边界再次混淆

最容易发生的偏差是：

- 把 harness 写着写着又变成产品 runtime 设计；
- 或把它做成超长 prompt 仓库。

解决办法：

- 在 `README.md`、`BOOTSTRAP.md`、`master-prompt.md` 三处重复声明定位；
- 明确“治理外挂层”字样；
- 文档和目录命名上也与 runtime 拉开距离。

### 19.2 第二个风险：规则太多，没人用

解决：

- Phase 1 只放真正必要文件；
- 先做 5~10 个高价值规则，不追求齐全；
- 规则要可执行，不要写成空泛口号。

### 19.3 第三个风险：过早代码化

解决：

- 先文档后脚本；
- 先脚本后 glue；
- 先轻量接入后再评估是否深接。

### 19.4 第四个风险：产物很多但无法复盘

解决：

- 强制 task_id；
- 强制 review verdict；
- 强制 ledger 最小记录；
- 强制 contract / report / review 文件命名带 task_id。

---

## 20. 最终建议

### 20.1 推荐落地路线

最务实路线是：

1. **不覆盖旧稿，保留旧稿作为分析参考；**
2. **新增一套“外挂治理层”修正版文档与目录方案；**
3. **先独立建 `codex-harness/` 或 `devtools/codex-harness/`；**
4. **先做文档、模板、ledger、workspace；**
5. **确认实际使用稳定后，再考虑轻量 glue 到 NeoDev 主项目。**

### 20.2 一句话判断

如果要用一句最严格的话来定义这个方案，那就是：

> NeoDev Codex Harness 应被设计为“开发期智能体治理外挂层”，而不是“NeoDev 产品 agent runtime 的一部分”。

### 20.3 本方案相对于旧稿的修正点

本修正版相对旧稿，主要做了以下纠偏：

1. **把“外挂层”定位写死，不再模糊成产品内部 harness；**
2. **把目录结构从仓库内默认 `harness/`，调整为更推荐的外挂独立目录；**
3. **把 bootstrap / progressive loading / contract / review / ledger 放到统一治理语义下；**
4. **强调 MVP 以文档、模板、目录和轻量脚本为主，不做破坏性重构；**
5. **把与 NeoDev 主项目的关系明确成“主项目 runtime + 外挂治理层”的双层结构。**

---

## 21. 附：最小建议文件结构（可直接照着建）

```text
D:\PycharmProjects\NeoDev\codex-harness\
  README.md
  BOOTSTRAP.md
  system\
    master-prompt.md
  rules\
    development\
      progressive-loading-rule.md
      agent-loop-rule.md
      subagent-delegation-rule.md
      review-and-acceptance-rule.md
      artifact-ledger-rule.md
      delegation-policy-rule.md
      harness-deposition-rule.md
    project\
      neodev-project-boundary-rule.md
      docs-edit-rule.md
      requirement-doc-rule.md
      code-change-rule.md
  contracts\
    task-contract.template.md
    delegation-contract.template.md
    review-contract.template.md
    artifact-record.template.json
  workspace\
    active\
      ACTIVE_TASK.md
      TASK_QUEUE.md
      LEDGER.json
    contracts\
    reports\
    reviews\
    artifacts\
    snapshots\
  docs\
    adoption-guide.md
    integration-notes.md
  scripts\
    bootstrap-loader.py
    ledger-init.py
    review-summary.py
```

如果当前必须先留在仓库内，则临时替换为：

```text
D:\PycharmProjects\NeoDev\devtools\codex-harness\
```

而不是优先塞进产品 runtime 主目录。

---

## 22. 本次建议的交付物说明

本次交付建议包括：

- 保留旧稿：`docs/NEODEV_HARNESS_DESIGN_2026-04-02.md`
- 新增修正版：`docs/NEODEV_CODEX_HARNESS_ADDON_DESIGN_2026-04-02_REVISED.md`

这样做的好处是：

- 不破坏原文；
- 新旧方案可对照；
- 后续可再按本修正版继续拆成实际目录和模板文件。

---

如果继续下一步，最合理的动作不是立刻改 NeoDev runtime，而是：

1. 按本文件创建 `codex-harness/` 初始目录；
2. 先落 `BOOTSTRAP.md`、`master-prompt.md`、3 个 contract 模板、`LEDGER.json` 样板；
3. 再决定是否需要一个轻量 `harness_loader.py` 做开发模式接入。
