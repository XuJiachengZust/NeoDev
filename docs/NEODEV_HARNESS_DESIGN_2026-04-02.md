# NeoDev Harness 方案设计（参考 dsc / 结合现状）

> 产出时间：2026-04-02  
> 主项目：`D:\PycharmProjects\NeoDev`  
> 参考项目：`C:\Users\AH\IdeaProjects\dsc`

---

## 1. 本次分析目标

围绕 NeoDev 当前的 agent / deepagents / sandbox / session 体系，参考 dsc 项目里 `harness/` 的规则化设计，给出一版**可落地、可分阶段推进**的 NeoDev harness 方案。

本设计不泛泛谈“做一个 prompt 管理系统”，而是尽量贴 NeoDev 现有代码结构，回答下面几个问题：

1. dsc 的 harness 到底沉淀了什么能力；
2. NeoDev 当前已经具备哪些 runtime / orchestration 基础；
3. NeoDev 还缺哪些 harness 层能力；
4. 最小可落地版本（MVP）应该落在哪些目录、哪些模块、哪些表意文件；
5. 后续如何从“可用”走向“可维护、可审计、可复用”。

---

## 2. dsc 中与 harness / runtime / agent orchestration 相关的盘点

### 2.1 dsc 的总体判断

dsc 当前看到的 `harness/` 更像一个**规则层 / 协作协议层**，而不是代码里的 agent runtime 实现。

它的核心价值不在“执行工具”，而在：

- 约束 agent 如何加载上下文；
- 约束主从智能体如何分工；
- 约束分派任务时必须明确边界、产物、验收；
- 约束经验如何沉淀回 harness；
- 让多轮开发协作从“临场 prompt”变成“可复用治理资产”。

换句话说：

- **NeoDev 现在偏 runtime 强**；
- **dsc 的 harness 偏治理强**；
- 最合理的方向不是照搬 dsc，而是把 dsc 的“治理层”嵌到 NeoDev 现有 runtime 上面。

---

### 2.2 dsc 关键目录

#### 根目录：`C:\Users\AH\IdeaProjects\dsc\harness`

关键结构：

- `BOOTSTRAP.md`
- `README.md`
- `system/master-prompt.md`
- `rules/development/agent-loop-rule.md`
- `rules/development/subagent-delegation-rule.md`
- `rules/development/progressive-loading-rule.md`
- `rules/development/harness-deposition-rule.md`
- `examples/subagent-delegation-examples.md`
- `context/`
- `tools/`

---

### 2.3 dsc 关键文件与作用

#### 1）`harness/BOOTSTRAP.md`

作用：**强入口**。

它要求：

- 不能跳过 bootstrap 直接乱读规则；
- 不能一次性全量加载全部规则；
- 先读 master prompt、agent loop、subagent delegation、progressive loading；
- 再根据任务是否命中业务域、开发域、环境域继续补读。

这实际上解决的是：

- agent 上下文容易失控；
- 规则越来越多后，模型不知道先读什么；
- 团队成员写了很多规范，但每次调用时缺少统一入口。

#### 2）`harness/system/master-prompt.md`

作用：定义仓库级总原则。

核心点：

- 先识别命中的子项目；
- 根级 harness 只放跨项目稳定规则；
- 业务背景与开发规范分离；
- 使用渐进式加载；
- 完成后考虑是否把稳定经验沉淀回 harness。

#### 3）`rules/development/agent-loop-rule.md`

作用：定义**主智能体—执行器—评估器**的闭环协作模型。

关键点：

- 主智能体负责理解、规划、拆解、汇总；
- 执行器子智能体负责执行，不得擅自扩边界；
- 执行完成 ≠ 完成任务；必须有评估；
- 评估结论需要明确为“通过 / 不通过 / 有风险待修复”。

这份规则很适合 NeoDev，因为 NeoDev 现在已有 subagent 能力，但“何时调度、如何验收、是否允许越界”还主要埋在 prompt 和工程习惯里。

#### 4）`rules/development/subagent-delegation-rule.md`

作用：把子智能体分派协议模板化。

要求每次分派至少说明：

- 任务目标；
- 当前角色；
- 上下文范围；
- 修改边界；
- 禁止事项；
- 预期产出；
- 验证标准。

这是 dsc 中最值得 NeoDev 吸收的一层，因为 NeoDev 当前 `task` 子智能体能力虽强，但更偏“通用能力”，缺少**产品级强约束 delegation contract**。

#### 5）`rules/development/progressive-loading-rule.md`

作用：控制规则与上下文的读取顺序。

重点是：

- 只加载当前任务真正需要的上下文；
- 不要为了“可能有用”一次性全读；
- 多智能体任务时不能遗漏 agent loop / delegation rule。

这对 NeoDev 也非常重要，因为 NeoDev 的 prompt 已经开始变长，尤其产品级 agent + requirement doc editor + nexus 子智能体组合后，后续极容易失控。

#### 6）`rules/development/harness-deposition-rule.md`

作用：把一次性问题处理中的稳定经验沉淀到 harness 资产。

核心思想：

- 每次改动完成后都要问：有没有可以沉淀为长期规则的东西；
- 跨项目的放根 harness；
- 单项目的放子项目 harness；
- 临时决策不要沉淀。

这解决的是 NeoDev 后续很可能面临的问题：需求文档 agent、图谱 agent、提交分析 agent 逐渐演化后，经验散落在提交和聊天里，而不是回到工程内。

---

## 3. NeoDev 现状盘点：已经具备的 runtime / execution 基础

下面是按“会话 → agent 编译 → backend → tool → subagent → SSE → 沙箱”的链路梳理 NeoDev 当前实现。

---

### 3.1 会话与消息持久化：已有完整骨架

关键文件：

- `src/service/routers/agent.py`
- `src/service/repositories/agent_repository.py`
- `src/service/checkpointer.py`

#### 已有能力

1. **Session / Conversation 映射**
   - `resolve_session()` 负责 session 解析、conversation 复用或创建；
   - 产品模式下按 `(session_id, product_id, is_active=true)` 找当前对话；
   - 非产品模式按 route + project 维度路由。

2. **消息持久化**
   - `ai_agent_messages` 存用户消息、assistant 消息、token、latency、model；
   - 支持历史分页拉取。

3. **上下文快照**
   - `ai_agent_context_snapshots` 已有 repository API；
   - 但目前更像“可手动保存的摘要”，还不是 harness 自动沉淀链路的一部分。

4. **LangGraph Checkpointer**
   - `src/service/checkpointer.py` 使用 PostgreSQL `AsyncPostgresSaver`；
   - 通过 `thread_id` 实现请求间对话恢复；
   - 若不可用，在 `agent_factory.py` 中退化到 `MemorySaver`。

#### 结论

NeoDev 在**runtime persistence** 层已经比 dsc 的 harness 更强，它不是缺持久化，而是缺：

- 如何控制哪些上下文应该进入 prompt；
- 如何把“会话状态”和“执行协议”绑定起来；
- 如何让不同 agent profile 的行为更可治理。

---

### 3.2 Agent 编译与运行：核心都在 `src/service/agent_factory.py`

这是 NeoDev 当前 harness/runtime 的中心。

#### 已有关键设计

##### 1）agent 缓存

- `_agent_cache`: `thread_id + response_mode` 级别缓存 agent；
- `_workspace_cache`: thread 对应 workspace backend；
- `_retrieval_cache_store`: thread 级 retrieval cache。

说明 NeoDev 已经把“一个会话一个长寿命 agent 运行态”建立起来了。

##### 2）动态 prompt 注入

`system_prompt` 不在编译期固化，而是：

- `create_deep_agent(... system_prompt="placeholder")`
- 实际 prompt 在调用前通过 `configurable.system_prompt_override` 注入
- 由 `DynamicPromptMiddleware` 动态替换。

这非常关键，因为它天然适合承载 harness bootstrap / rule stack。

##### 3）产品级与普通 agent 双体系

- `get_or_create_agent()`：单项目 / route profile 体系；
- `get_or_create_product_agent()`：多项目产品级体系。

产品级 agent 已经具备：

- 多项目只读挂载；
- 可写 workspace；
- 可选 branch mapping；
- 可选 nexus 子智能体；
- requirement doc 编辑模式；
- retrieval cache 共享。

##### 4）统一流式事件处理

`_process_stream_events()` 已经统一处理：

- token 流；
- tool start / end；
- task 子智能体深度识别；
- recursion limit；
- token 统计。

这意味着 NeoDev 已经有一个不错的**运行时事件总线视图**，只差把它升级为 harness 级审计与验收支撑。

---

### 3.3 Backend 路由体系：NeoDev 非常接近“可编排 execution fabric”

关键文件：

- `src/deepagents/backends/protocol.py`
- `src/deepagents/backends/composite.py`
- `src/deepagents/backends/local_shell.py`
- `src/service/sandbox_manager.py`

#### 已有能力

##### 1）统一 Backend Protocol

`BackendProtocol` / `SandboxBackendProtocol` 已经抽象出：

- ls/read/grep/glob
- write/edit
- upload/download
- execute

这其实就是 NeoDev runtime 的“工具执行底座”。

##### 2）CompositeBackend

支持按路径前缀路由到不同 backend：

- `/workspace/project/`
- `/workspace/tmp/`
- `/workspace/projects/{name}/`
- `/workspace/sandbox/`

这是 NeoDev 比很多 agent 工程更成熟的地方：

- runtime 已经把“逻辑空间”与“物理后端”解耦；
- 非常适合在上面再加 harness 规则层。

##### 3）LocalShellBackend

当前 `LocalShellBackend` 是**本地 shell + filesystem**，能力强但风险也高：

- `shell=True`
- 无隔离执行
- 主要依赖根目录和人为约束

##### 4）会话级沙箱目录

`src/service/sandbox_manager.py` 提供：

- `ensure_sandbox(session_id)`
- `get_sandbox_path(session_id)`
- `recycle_sandbox(session_id)`

本质是每个会话一个目录，当前实现更像“隔离工作目录”，不是强安全沙箱。

#### 结论

NeoDev 已有：

- 文件空间隔离；
- 工作区与项目路径映射；
- shell 执行入口；

但还缺少：

- agent 级风险分层；
- 工具调用审批策略；
- tool contract / task contract / audit trail。

---

### 3.4 DeepAgent 组装层：NeoDev 已具备 harness 的宿主能力

关键文件：

- `src/deepagents/graph.py`
- `src/deepagents/middleware/subagents.py`
- `src/deepagents/middleware/workspace.py`

#### `create_deep_agent()` 当前已具备的核心结构

主智能体 middleware 栈大致为：

- `DynamicPromptMiddleware`
- `TodoListMiddleware`
- `ToolFilterMiddleware`
- `MemoryMiddleware`（可选）
- `SkillsMiddleware`（可选）
- `FilesystemMiddleware`
- `SubAgentMiddleware`
- `SummarizationMiddleware`
- `AnthropicPromptCachingMiddleware`
- `PatchToolCallsMiddleware`
- `SandboxWorkspaceMiddleware`（若启用 workspace）

子智能体 middleware 栈大致为：

- `SandboxWorkspaceMiddleware(role="subagent")`（若启用 workspace）
- `TodoListMiddleware`（可选）
- `SkillsMiddleware`（可选）
- `FilesystemMiddleware`
- `RetrievalCacheMiddleware`（可选）
- `SummarizationMiddleware`
- `AnthropicPromptCachingMiddleware`
- `ParallelToolCallsMiddleware`
- `PatchToolCallsMiddleware`

#### 说明

NeoDev 已经不是“一个 prompt + 一组 tools”的简单 agent 了，而是一个：

- 有 middleware pipeline；
- 有 subagent runtime；
- 有 workspace protocol；
- 有 route-based backend fabric；
- 有 memory/checkpointer；
- 有 profile system。

所以 NeoDev 的 harness 方案不应另起炉灶，而应把 **harness 作为 prompt governance + execution contract + review protocol** 植入现有 middleware / profile / route 层。

---

### 3.5 子智能体设计：已能用，但离“工程化 delegation contract”还有距离

关键文件：

- `src/deepagents/middleware/subagents.py`
- `src/service/agent_profiles.py`

#### 已有优点

1. `task` 工具能力完整；
2. 支持 general-purpose + custom subagent；
3. 子智能体 prompt 已有相对明确的描述；
4. `SandboxWorkspaceMiddleware` 已要求子智能体把详细结果写 workspace 报告，再返回摘要 + 路径；
5. 产品级 agent prompt 已明确：
   - 编排者负责调度；
   - project-retriever / commit-analyzer / nexus 职责不重叠；
   - 要做动态规划。

#### 主要问题

1. **delegation contract 还主要靠 prompt 大段文字约束**；
2. **不同子智能体返回结构没有统一 schema**；
3. **没有显式“执行结果 / 验收结论 / 风险等级”结构**；
4. **没有单独的 reviewer / evaluator 子智能体类型**；
5. **没有 harness 级任务记录（task id / parent task / status / artifact path）**。

这部分正是 dsc 的 `agent-loop-rule + subagent-delegation-rule` 可以补上的地方。

---

## 4. NeoDev 当前问题归纳

结合代码结构，NeoDev 现在不是“没有 harness”，而是“runtime 有了，但 harness 治理还没显式成型”。

### 4.1 主要缺口

#### 缺口 A：缺统一的 harness 入口

现在 prompt 规则主要散落在：

- `agent_profiles.py`
- 各子智能体 prompt builder
- `workspace.py` 中间件
- 某些 route-specific 约束

问题：

- 没有像 dsc `BOOTSTRAP.md` 那样的统一加载入口；
- 不同场景 prompt 演化时容易重复、冲突、漂移；
- 新增 agent profile 时没有统一接入规范。

#### 缺口 B：缺显式任务协作协议

虽然有 subagent，但没有独立的 harness contract 文件体系来定义：

- 任务目标；
- 边界；
- 禁止事项；
- 期望产物；
- 验证标准；
- reviewer 判断条件。

#### 缺口 C：缺 execution audit / review layer

SSE 事件流能看到执行过程，但没有工程内结构化沉淀：

- tool 调用摘要；
- subagent 报告索引；
- 关键决策依据；
- 最终结论是通过/不通过/待修复。

#### 缺口 D：workspace 已有，但还不是完整 artifact workspace

现在 workspace 更偏“共享磁盘目录”，但对 artifact 类型缺少规范：

- 报告放哪；
- 中间代码片段放哪；
- 验收结果放哪；
- 计划与动态调整放哪。

#### 缺口 E：安全等级与工具策略还不够分层

尤其 `LocalShellBackend` 当前太强，虽然实用，但对于：

- requirement doc agent
n- product agent
- 未来 code modification agent

需要更明确的 profile-based execution policy。

---

## 5. NeoDev Harness 的目标与边界

---

### 5.1 目标

NeoDev Harness 不应重新实现 LangGraph / deepagents，而应作为其上层治理框架，实现以下目标：

1. **统一入口**：定义 agent 在不同任务下如何加载规则与上下文；
2. **统一分派协议**：让 orchestrator 到 subagent 的任务下发具备稳定 contract；
3. **统一产物规范**：让报告、计划、验收、快照有固定落点；
4. **统一验收协议**：把“执行结果”和“完成结论”区分开；
5. **统一沉淀机制**：让有效经验能回写到 harness 规则；
6. **最小侵入接入**：尽量复用现有 `agent_factory.py`、`agent_profiles.py`、middleware 栈、workspace backend。

---

### 5.2 边界

NeoDev Harness **不负责**：

- 替代现有 `deepagents` runtime；
- 重写 LangGraph checkpointer；
- 重新设计所有 agent profile；
- 一次性做完 HITL / 审批 / 强安全沙箱；
- 替代数据库中的 conversation/message 记录。

NeoDev Harness **负责**：

- 规则加载与约束；
- 分派协议；
- 任务产物组织；
- 审计与验收结构；
- runtime 之上的治理层。

---

## 6. 建议的 NeoDev Harness 架构

建议新增目录：

```text
D:\PycharmProjects\NeoDev\harness\
  BOOTSTRAP.md
  README.md
  system\
    master-prompt.md
    response-contract.md
  rules\
    development\
      progressive-loading-rule.md
      agent-loop-rule.md
      subagent-delegation-rule.md
      workspace-artifact-rule.md
      tool-execution-policy-rule.md
      review-and-acceptance-rule.md
      harness-deposition-rule.md
    product\
      requirement-doc-rule.md
      code-analysis-rule.md
      impact-analysis-rule.md
  templates\
    task-contract.md
    review-template.md
    report-template.md
  examples\
    delegation-example.md
    review-example.md
```

说明：

- 结构上不要照抄 dsc 的 business/development 二分法；
- NeoDev 更适合 `system / rules / templates / examples`；
- `product/` 规则单独放，因为 NeoDev 当前很多 agent 都是产品场景驱动。

---

## 7. 核心组件设计

### 7.1 HarnessBootstrapLoader（新增，建议 Python 模块）

建议新增：

- `src/service/harness_loader.py`

职责：

1. 根据当前 profile / route / doc mode / product mode 决定要加载哪些 harness 文件；
2. 先加载 `harness/BOOTSTRAP.md`；
3. 再按规则做渐进加载；
4. 把加载后的 rule bundle 拼成 `system_prompt_override` 前缀；
5. 可选地把加载结果记录到日志或 state 中。

### 设计建议

可提供接口：

```python
def build_harness_prompt_bundle(
    *,
    profile_name: str,
    route_context_key: str | None,
    is_product: bool,
    has_doc_context: bool,
    response_mode: str | None,
) -> str:
    ...
```

集成点：

- `agent_factory.run_agent_stream()`
- `agent_factory.run_agent_invoke()`
- `agent_factory.run_product_agent_stream()`

拼接顺序建议：

1. harness bootstrap / master prompt
2. 按条件加载 development rules
3. 按 profile 加载 product rules
4. 再拼接 `agent_profiles.py` 里原有的 profile system prompt
5. 再拼接 response mode suffix

这样能保证：

- harness 是上位规则；
- 具体 profile prompt 是场景化指令；
- response mode 只是表达风格附加层。

---

### 7.2 DelegationContract（新增结构化协议）

建议不要只靠 prompt 文字，至少在 orchestrator 内部形成一个结构体。

建议新增：

- `src/service/harness_contracts.py`

定义示例：

```python
from pydantic import BaseModel
from typing import Literal

class DelegationContract(BaseModel):
    task_id: str
    role: Literal["executor", "reviewer", "researcher"]
    goal: str
    scope: list[str]
    allowed_paths: list[str] = []
    forbidden_actions: list[str] = []
    expected_output: list[str]
    validation_criteria: list[str]
    artifact_path: str | None = None
```

用途：

- 给子智能体生成 description 前先形成结构；
- 再将结构渲染成 markdown/prompt；
- 后续 reviewer 也能读取同一 contract 做验收。

这样就把 dsc 的“分派模板”从文档层推进到了代码层。

---

### 7.3 Task Ledger / Artifact Index（新增）

建议新增：

- `src/service/harness_ledger.py`

职责：

- 为每次子任务生成 task id；
- 记录 parent/child 关系；
- 记录 artifact 路径；
- 记录状态：planned / running / done / review_pending / failed；
- 可选写入 workspace + 数据库快照。

#### MVP 版不一定要上库

第一阶段完全可以只写到 workspace：

```text
/workspace/sandbox/
  plan.md
  ledger.json
  reports/
  reviews/
  artifacts/
```

其中：

- `plan.md`：orchestrator 当前计划
- `ledger.json`：子任务结构化记录
- `reports/*.md`：执行器详细报告
- `reviews/*.md`：评估器/验收报告
- `artifacts/*`：中间产物

这会把现有 workspace 从“能写文件”升级成“有组织的任务空间”。

---

### 7.4 Reviewer 子智能体（新增类型）

目前 NeoDev 现有子智能体偏：

- project-retriever
- commit-analyzer
- nexus

建议增加一类 reviewer 子智能体，不一定第一阶段就能改代码，但应该尽快纳入 profile。

建议类型：

- `execution-reviewer`
- 或拆成 `doc-reviewer` / `analysis-reviewer`

职责：

- 读取执行器产出的报告与关键 artifact；
- 对照 delegation contract 检查是否完成；
- 输出明确结论：`PASS / FAIL / RISK`；
- 写 `reviews/{task_id}.md`。

这就是把 dsc 的 `agent-loop-rule` 真正落到 NeoDev runtime 上。

---

### 7.5 Workspace Artifact Rule（新增规则 + 中间件增强）

当前 `SandboxWorkspaceMiddleware` 已经有不错的提示词，但还可以继续工程化。

建议增强点：

#### 当前优点

- orchestrator / subagent 角色提示分离；
- 子智能体被要求输出摘要 + 报告路径；
- orchestrator 被要求动态规划。

#### 建议增强

1. 明确固定目录：
   - `/workspace/sandbox/reports/`
   - `/workspace/sandbox/reviews/`
   - `/workspace/sandbox/artifacts/`
   - `/workspace/sandbox/contracts/`
   - `/workspace/sandbox/plan.md`
   - `/workspace/sandbox/ledger.json`

2. 报告文件名加入 task id：
   - `reports/TASK-001-project-retriever.md`

3. reviewer 必须输出 machine-readable verdict block，例如：

```md
## Verdict
- status: PASS
- task_id: TASK-001
- risks:
  - none
```

4. orchestrator 优先读 `reviews/`，其次按需读 `reports/`。

---

### 7.6 Tool Execution Policy（新增）

建议增加一层 profile-based tool execution policy，哪怕第一版只是配置与 prompt 约束，也比完全口头约束强。

建议新增：

- `src/service/tool_execution_policy.py`

按 profile 做最小分层：

#### Level 0：只读分析

适用：

- `default`
- `project_repo`
- `project_versions`
- `project_commits`
- `project_requirements`
- `cockpit_*`

策略：

- 禁止 `execute`；
- 只允许 `ls/read/glob/grep`；
- 子智能体只做研究型任务。

#### Level 1：受控工作区写入

适用：

- requirement doc editor
- product doc generation / planning类

策略：

- 允许写 `/workspace/sandbox/`；
- 禁止直接写项目代码路径；
- 禁止 shell 执行或默认关闭。

#### Level 2：代码改动实验态

未来适用：

- 自动修复 agent
- patch 生成 agent

策略：

- 只允许在 session sandbox 中执行 shell；
- 明确 require reviewer；
- 关键工具调用需要 interrupt / 审批。

这层不一定第一期做完整，但建议先把 policy 模型占位出来。

---

## 8. 与 NeoDev 现有代码的落点映射

### 8.1 应改造的第一批落点

#### 落点 1：`src/service/agent_factory.py`

这是 harness 接入的主入口。

建议改动：

- 在 `run_agent_stream()` / `run_agent_invoke()` / `run_product_agent_stream()` 中，统一通过 `harness_loader` 构造 prompt bundle；
- 将 bundle 拼到 `system_prompt_override` 前；
- 可选地把当前加载的 harness rule 名称打日志。

#### 落点 2：`src/service/agent_profiles.py`

建议职责收敛：

- 保留“场景化 profile prompt”与工具白名单；
- 把“工程治理性规则”迁移到 `harness/` 文档；
- 避免这里继续膨胀成超长总 prompt 仓库。

#### 落点 3：`src/deepagents/middleware/workspace.py`

建议增强：

- 更明确固定 artifact 目录；
- 增加 contracts / reviews 约束；
- 可选支持在 `before_agent` 时初始化目录结构与 `ledger.json`。

#### 落点 4：`src/deepagents/middleware/subagents.py`

建议不做大改，但应在 task description 构建前接入 delegation contract 渲染逻辑。

即：

- 当前是直接传 `description`；
- 目标是：上层先生成 contract，再渲染为 description 传入。

#### 落点 5：`src/service/routers/agent.py`

建议后续扩展：

- 增加获取当前 harness artifact 索引的接口（可选）；
- 或支持前端读取当前 plan / latest review / doc artifact。

---

## 9. NeoDev Harness 最小可落地版本（MVP）

目标：**先把规则入口、workspace 产物规范、delegation contract 三件事跑起来**，不追求一次做全。

### MVP 范围

#### 必做 1：新增 `harness/` 目录与最小规则集合

至少包含：

- `harness/BOOTSTRAP.md`
- `harness/system/master-prompt.md`
- `harness/rules/development/progressive-loading-rule.md`
- `harness/rules/development/agent-loop-rule.md`
- `harness/rules/development/subagent-delegation-rule.md`
- `harness/rules/development/workspace-artifact-rule.md`
- `harness/rules/development/review-and-acceptance-rule.md`
- `harness/rules/development/harness-deposition-rule.md`

#### 必做 2：新增 `harness_loader.py`

把上面规则按 profile 场景拼入 prompt。

#### 必做 3：规范 workspace artifact 目录

最少要稳定以下目录：

- `/workspace/sandbox/reports/`
- `/workspace/sandbox/reviews/`
- `/workspace/sandbox/artifacts/`
- `/workspace/sandbox/contracts/`

#### 必做 4：定义 Delegation Contract 渲染模板

哪怕先不做结构化 Pydantic，也至少要有固定 markdown 模版：

```md
# Delegation Contract
- task_id:
- role:
- goal:
- scope:
- allowed_paths:
- forbidden_actions:
- expected_output:
- validation_criteria:
```

#### 必做 5：产品级 agent 使用 reviewer 规则

第一版可以先不新增 reviewer 子智能体，而是要求 orchestrator：

- 在关键任务后自行产出 review 结论文件；
- 将结论写入 `reviews/{task_id}.md`。

也就是“先用同一个 agent 承担 review”，但结构先立住，后面再替换成独立 reviewer。

---

## 10. 分阶段实施建议

### Phase 1：规则入口与产物规范（1 周内可完成）

目标：让 harness 从“没有”变成“存在且可接入”。

工作项：

1. 新建 `harness/` 目录；
2. 编写 Bootstrap / master prompt / development rules；
3. 新建 `src/service/harness_loader.py`；
4. 在 `agent_factory.py` 中接入 prompt bundle；
5. 在 `workspace.py` 中明确 artifact 目录规范；
6. 验证产品 agent 与 requirement doc agent 不回归。

验收标准：

- 所有主要 agent 调用都可带上 harness bundle；
- workspace 内报告、评审、artifact 路径有统一规范；
- profile prompt 长度可控，没有明显重复提示膨胀。

---

### Phase 2：Delegation Contract + Ledger（1~2 周）

目标：让 subagent 调度有结构化协议，而不是纯自然语言。

工作项：

1. 新建 `src/service/harness_contracts.py`；
2. 新建 `src/service/harness_ledger.py`；
3. orchestrator 派发 task 前生成 task id 与 contract；
4. contract 写到 `/workspace/sandbox/contracts/`；
5. 结果索引写到 `/workspace/sandbox/ledger.json`；
6. 子智能体报告文件名带 task id。

验收标准：

- 每个子任务都有 contract 文件；
- ledger 能追踪 task 状态与 artifact 路径；
- 出问题时可回溯“谁被派去做什么、产出了什么”。

---

### Phase 3：独立 Reviewer 子智能体（2 周左右）

目标：把 dsc 的“执行—评估闭环”真正落地。

工作项：

1. 定义 reviewer 子智能体 profile；
2. 为 product / requirement doc / impact analysis 场景配置 reviewer；
3. reviewer 读取 contract + report 输出 verdict；
4. orchestrator 只根据 verdict 决定是否继续修复。

验收标准：

- 至少一个核心链路（如 requirement doc 编辑）形成 executor + reviewer 闭环；
- review 结论标准化；
- 明确区分“已执行”与“已验收”。

---

### Phase 4：工具策略分层与审计增强（后续）

目标：降低 LocalShellBackend 的风险，把 harness 接到 execution policy 上。

工作项：

1. 梳理各 profile 的工具权限；
2. 禁止不需要 execute 的 profile 获得 execute；
3. 高风险 edit/execute 接入 HITL 或 interrupt_on；
4. 按 tool 维度沉淀执行日志/审计摘要。

---

## 11. 我对 NeoDev harness 的推荐落地路径

如果只给一个最务实方案，我建议这样推进：

### 第一优先级

- **先做文档级 harness + prompt loader**，不要一开始就上复杂 runtime 改造。

原因：

- 现有 runtime 足够强；
- 真正缺的是规则统一入口与治理结构；
- 低风险、收益快、便于验证。

### 第二优先级

- **再做 contract + ledger**。

原因：

- 这是从“有规则”走向“能追踪”的关键一步；
- 也是之后做 reviewer、审计、前端可视化的基础。

### 第三优先级

- **最后再做 reviewer 子智能体与工具审批**。

原因：

- reviewer 是提升质量的关键，但不必卡在第一阶段；
- tool approval 如果过早做，会拖慢当前功能演进。

---

## 12. 一个务实的代码实施草案

### 12.1 第一批新增文件

建议新增：

```text
D:\PycharmProjects\NeoDev\harness\BOOTSTRAP.md
D:\PycharmProjects\NeoDev\harness\README.md
D:\PycharmProjects\NeoDev\harness\system\master-prompt.md
D:\PycharmProjects\NeoDev\harness\rules\development\progressive-loading-rule.md
D:\PycharmProjects\NeoDev\harness\rules\development\agent-loop-rule.md
D:\PycharmProjects\NeoDev\harness\rules\development\subagent-delegation-rule.md
D:\PycharmProjects\NeoDev\harness\rules\development\workspace-artifact-rule.md
D:\PycharmProjects\NeoDev\harness\rules\development\review-and-acceptance-rule.md
D:\PycharmProjects\NeoDev\harness\rules\development\harness-deposition-rule.md
D:\PycharmProjects\NeoDev\src\service\harness_loader.py
```

### 12.2 第一批最小代码改动点

1. `src/service/agent_factory.py`
   - 在 `run_agent_stream` / `run_agent_invoke` / `run_product_agent_stream` 拼接 harness prompt bundle。

2. `src/deepagents/middleware/workspace.py`
   - 更新 workspace 协议提示词；
   - 增加 contracts/reviews 目录规范；
   - 可选初始化固定目录结构。

3. `src/service/agent_profiles.py`
   - 适度瘦身，保留场景化信息，减少治理规则重复。

---

## 13. 风险与注意事项

### 风险 1：prompt 重复叠加导致长度膨胀

解决：

- harness 只放稳定治理规则；
- profile prompt 只放场景化指令；
- 不要在 profile prompt 中重复写 harness 已覆盖的内容。

### 风险 2：规则写太多，模型反而不执行

解决：

- 先 MVP；
- development rules 控制在真正必要的 5~7 个文件；
- 尽量把“必须遵守的格式”做成模板，而非长篇口号。

### 风险 3：workspace 规范与现有 requirement_doc 编辑模式冲突

解决：

- requirement doc 继续保留 `/workspace/sandbox/requirement_doc.md`；
- 新增的 reports/reviews/contracts 目录只做补充，不改现有文档路径。

### 风险 4：把所有东西都做成 prompt，缺少程序约束

解决：

- 第一阶段允许 prompt 先行；
- 第二阶段必须引入 contract/ledger 结构化层；
- 否则后面很难审计。

---

## 14. 最终结论

### 一句话结论

**NeoDev 不缺 agent runtime，缺的是一个位于 runtime 之上的 harness 治理层；dsc 可借鉴的重点不是执行实现，而是 Bootstrap、渐进加载、主从闭环、子任务分派协议、经验沉淀这五件事。**

### 最值得落地的 5 个点

1. 建立 `harness/BOOTSTRAP.md` 作为统一入口；
2. 引入 `harness_loader.py`，把规则加载接到 `agent_factory.py`；
3. 规范 workspace artifact 目录；
4. 将 subagent 调度升级为 Delegation Contract；
5. 后续补上 reviewer 子智能体，形成执行—评估闭环。

### 对老代码最小侵入的路线

- 不重写 `deepagents`；
- 不重写 `agent_factory` 结构；
- 只在 prompt 装配点、workspace 协议、task 分派协议上做增强；
- 逐步把“散落在 prompt 里的工程习惯”收敛成显式 harness。

---

## 15. 参考的关键源码与规则文件

### dsc

- `C:\Users\AH\IdeaProjects\dsc\harness\BOOTSTRAP.md`
- `C:\Users\AH\IdeaProjects\dsc\harness\system\master-prompt.md`
- `C:\Users\AH\IdeaProjects\dsc\harness\rules\development\agent-loop-rule.md`
- `C:\Users\AH\IdeaProjects\dsc\harness\rules\development\subagent-delegation-rule.md`
- `C:\Users\AH\IdeaProjects\dsc\harness\rules\development\progressive-loading-rule.md`
- `C:\Users\AH\IdeaProjects\dsc\harness\rules\development\harness-deposition-rule.md`

### NeoDev

- `D:\PycharmProjects\NeoDev\src\service\agent_factory.py`
- `D:\PycharmProjects\NeoDev\src\service\routers\agent.py`
- `D:\PycharmProjects\NeoDev\src\service\repositories\agent_repository.py`
- `D:\PycharmProjects\NeoDev\src\service\checkpointer.py`
- `D:\PycharmProjects\NeoDev\src\service\sandbox_manager.py`
- `D:\PycharmProjects\NeoDev\src\service\agent_profiles.py`
- `D:\PycharmProjects\NeoDev\src\deepagents\graph.py`
- `D:\PycharmProjects\NeoDev\src\deepagents\backends\protocol.py`
- `D:\PycharmProjects\NeoDev\src\deepagents\backends\composite.py`
- `D:\PycharmProjects\NeoDev\src\deepagents\backends\local_shell.py`
- `D:\PycharmProjects\NeoDev\src\deepagents\middleware\subagents.py`
- `D:\PycharmProjects\NeoDev\src\deepagents\middleware\workspace.py`

---

如果继续推进，下一步最合适的是：**直接按本设计创建 NeoDev `harness/` 初版目录和 `src/service/harness_loader.py` 草案。**
