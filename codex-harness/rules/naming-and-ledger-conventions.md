# Naming and Ledger Conventions

这份说明只解决一个最小问题：让 `codex-harness` 里的任务目录、review 文件、ledger 条目命名尽量收敛，避免样例继续发散。

它是**轻量约束**，不是新框架；优先服务现有样例库，不额外引入脚本、注册表或复杂 schema。

## 1. 任务命名建议

### 推荐格式

```text
TASK-YYYY-MM-DD-SHORT-SCOPE[-OPTIONAL-SUFFIX]
```

例如：

- `TASK-2026-04-08-HARNESS-CLOSED-LOOP-EXAMPLE`
- `TASK-2026-04-08-HARNESS-DELEGATION-EXAMPLE`
- `TASK-2026-04-06-REQ-DOC-REDESIGN`

### 命名原则

- 前缀固定用 `TASK-`，方便目录、review、ledger 统一检索。
- 日期使用 `YYYY-MM-DD`，先给出时间锚点，再给语义段。
- 中间语义段优先写**边界/范围**，如 `HARNESS`、`REQ-DOC`。
- 末尾语义段优先写**动作或目标**，如 `REDESIGN`、`DELEGATION-EXAMPLE`。
- 全部使用大写连字符风格，避免空格、下划线、中文混排导致的映射分裂。

### 不建议

- `task1`、`example-new` 这类无日期、无边界、无动作语义的名字
- 同一个任务在目录、review、ledger 中使用不同 taskId
- 把实现细节写进 taskId（例如模型名、CLI 参数、临时分支名）

## 2. review 文件命名映射建议

### 最小映射规则

review 文件名应当**直接从 taskId 派生**：

```text
{taskId}-review.md
```

例如：

- taskId: `TASK-2026-04-08-HARNESS-CLOSED-LOOP-EXAMPLE`
- review: `TASK-2026-04-08-HARNESS-CLOSED-LOOP-EXAMPLE-review.md`

### 推荐落点

```text
artifacts/reviews/{taskId}-review.md
```

### 为什么这样最稳

- 不需要额外查表
- 人眼一看就知道 review 属于哪个任务
- ledger 的 `taskId`、`review`、`artifacts[]` 可以形成稳定的三点映射

如果未来出现多轮 review，优先在文件内写清楚轮次；不要过早把文件命名扩成复杂版本体系。只有当同一 task 确实需要并存多个 review 文件时，再考虑：

```text
{taskId}-review-v2.md
```

## 3. ledger `type/status` 最小枚举建议

现有 `LEDGER.json` 已经出现了 `example`、`implementation`、`governance-example`、`governance-delegation-example` 等写法。为了继续扩展时不失控，建议先收敛到**最小可用枚举**。

### `type` 最小建议枚举

```json
[
  "implementation",
  "governance",
  "review",
  "example",
  "template"
]
```

#### 使用建议

- `implementation`：真实实现类任务，产物主要落在 NeoDev 主项目或明确的交付文件中
- `governance`：只涉及 harness 规则、contract、流程、样例组织等外挂层治理工作
- `review`：以审查、验收、盘点、差距识别为主的任务
- `example`：用于教学、演示、样板库建设的示例任务
- `template`：占位、模板、尚未实例化的样板条目

### `status` 最小建议枚举

```json
[
  "template",
  "planned",
  "in_progress",
  "blocked",
  "review_pending",
  "completed",
  "archived"
]
```

#### 使用建议

- `template`：样板占位，还不代表真实任务
- `planned`：任务已登记，但尚未开始执行
- `in_progress`：正在执行，已有真实推进
- `blocked`：存在明确阻塞，不能假装继续推进
- `review_pending`：主要产物已出，等待正式 review / acceptance
- `completed`：已完成并有 review 或等价验收证据
- `archived`：历史保留，不再作为活跃参考

### 收敛建议

- 新增条目时，优先只从上述枚举中选值。
- 现有更细的 `type`（如 `governance-delegation-example`）**不要求立刻回收**；但后续新增最好避免继续发明更长的新类别。
- 如果确实需要更细分类，优先写进 `notes`，不要先把 `type` 膨胀成层级树。

## 4. 保持外挂层边界

`codex-harness` 是 **Codex 开发治理外挂层**，不是 NeoDev 产品 runtime。

这条边界在命名和 ledger 上都要体现：

- taskId 中可以出现 `HARNESS` 这类边界词，帮助识别治理任务
- harness 内文档只描述：任务 framing、委派边界、review、ledger、经验沉淀
- 不要把产品 runtime 的模块命名规范、接口 schema、业务状态机直接塞进这份文档
- 不要为了“统一”而让 harness 反向接管主项目的产品命名体系

一句话：

> harness 负责治理开发过程，不负责定义产品本体。

## 5. 当前最小执行建议

如果现在要继续新增样例或任务，先遵循下面四条就够了：

1. 任务目录名直接使用 `taskId`
2. review 文件名固定使用 `{taskId}-review.md`
3. ledger 新条目的 `type/status` 尽量只从最小枚举里取值
4. 所有 harness 说明文档都显式保持“外挂层，不碰产品 runtime”边界

这已经足够支撑当前样例库继续增长，而不会引入过度设计。