# Week2 Requirement Doc Workflow Audit

日期：2026-03-27  
任务 ID：W2-RD-01  
范围：仅审计“需求文档工作流主链”的当前真实行为、断点、异常路径，并映射到 W2-RD-02 ~ W2-RD-08。

---

## 1. 审计方法

本次按一轮 **规划 → 执行 → 审查 → 反思** 执行：

1. **规划**：先阅读 `docs/WEEK2_REQUIREMENT_DOC_TASK_PACK_2026-03-26.md`，确认主链边界与验收口径。
2. **执行**：只读检查以下主链文件：
   - `web/src/pages/RequirementDocPage.tsx`
   - `web/src/api/client.ts`
   - `src/service/routers/requirement_docs.py`
   - `src/service/services/requirement_doc_service.py`
   - `src/service/repositories/product_requirement_repository.py`
   - `src/service/repositories/requirement_doc_repository.py`
   - `src/service/workflows/requirement_doc_workflow.py`
   - 辅助组件：`MarkdownDiffReviewer.tsx`、`SplitSuggestionsModal.tsx`
3. **审查**：按“进入页面、空文档、生成中、生成失败、已有文档、diff、save、子文档生成”逐段核对前后端语义是否闭环。
4. **反思**：将问题压缩成可执行的 P0/P1 问题单，并映射到 W2-RD-02~08，避免泛泛而谈。

---

## 2. 主链真实行为总览（当前实现）

当前主链已经具备一个“能跑起来”的基础闭环，但还没有收敛成稳定、可解释、可恢复的 Week2 演示链。

### 2.1 当前主链名义流程

1. 从路由进入 `RequirementDocPage`
2. 页面并行加载：
   - 当前需求信息 `getProductRequirement`
   - 当前文档 `getRequirementDoc`
   - 版本列表 `listDocVersions`
   - 需求树 `listProductRequirementsTree`
   - 后台生成状态 `getDocGenerationStatus`
3. 如果是 Story/Task，点击 `AI 生成` 直接走 `/doc/generate` SSE
4. 如果是 Epic，先进入 `/doc/pre-generate-chat` 预生成对话，再进入 `/doc/generate`
5. SSE 流内前端消费：
   - `workflow_step`
   - `token`
   - `split_suggestions`
   - `workflow_done`
6. 工作流后端执行：
   - `collect_context`
   - `code_search`
   - `graph_search`
   - `synthesize`
   - `generate_doc`
   - `save_draft`
   - `generate_split_suggestions`（仅 epic/story）
7. 保存后版本号增长，可进入 diff；Agent 侧改稿时可进入 review
8. 已有父文档时，可从侧边树对 epic/story 触发子文档生成 `/doc/generate-children`

### 2.2 当前真实状态结论

- **有基础能力**：文档读写、版本、diff、SSE 生成、子文档生成、拆分建议都已有实现。
- **缺主状态模型**：页面没有明确告诉用户“现在是什么状态、下一步该做什么”。
- **缺恢复语义**：生成失败、SSE 中断、刷新恢复、子文档门禁失败都只有局部实现，没有统一产品语义。
- **主链断在感知层**：后端很多能力存在，但前端暴露出来的是按钮集合，不是可解释的工作流。

---

## 3. 主链步骤审计

## 3.1 进入页面

### 当前行为

- `RequirementDocPage` 通过 `productId`、`requirementId` 路由参数进入。
- 页面启动后分别加载需求、文档、版本、需求树、generation status。
- 左侧树可显示 `has_doc` 圆点，并支持切换需求。
- 有未保存内容时，切换节点会弹 `confirm("有未保存的更改，确定切换？")`。

### 断点/异常路径

- 页面首屏没有统一状态摘要，只显示需求基本信息和若干按钮。
- `loadDoc()` 对 404 采用静默吞掉并回退为空字符串，用户无法区分：
  - 真的是“尚无文档”
  - 还是接口失败/权限/后端异常被吃掉了
- `loadVersions()` 与 `loadTree()` 异常也基本吞掉，页面会表现成“像没数据”，但没有解释。
- `generation-status` 在 mount 时会查一次，但页面没有把结果映射成明确主状态卡片。

### 审计结论

当前“进入页面”更多是技术装配完成，不是用户可理解的工作流入口。

---

## 3.2 加载空文档

### 当前行为

- 当 `/doc` 返回 404 时，前端直接把 `content` / `savedContent` 设为空，`version` 设为 0。
- 编辑区 placeholder 为“在此编辑 Markdown 文档…”。
- 用户可以：
  - 直接手写后保存
  - 点击 `AI 生成`
  - 对 epic/story 打开“拆分建议”弹窗

### 断点/异常路径

- 页面没有明确文案告诉用户“这是空文档初始态”。
- `version=0` 只是内部状态，没有用户可见意义。
- 空文档状态下仍可点击“变更”，但若版本不足两条，diff 无默认结果，也没有引导。
- epic/story 在没有文档时也能手动打开拆分建议弹窗，这会把“文档已完成后再拆分”的语义打散。

### 审计结论

空文档状态可操作，但缺乏产品层定义，用户看不出“先生成 / 先编辑 / 先补信息”的推荐路径。

---

## 3.3 生成中

### 当前行为

- 点击 `AI 生成`：
  - story/task 直接进 SSE
  - epic 先做预生成对话，再开始 SSE
- 前端流式消费 `workflow_step` 和 `token`，将 token 直接拼接到编辑区。
- 页面显示当前步骤文案：`collect_context / code_search / graph_search / synthesize / generate_doc / save_draft / generate_split_suggestions`。
- 如果刷新时检测到 `generation_status === running`，会显示“文档生成中（后台运行）…”并每 3 秒轮询 `generation-status`。

### 断点/异常路径

- 生成时只禁用了 `AI 生成`，但 **保存、切到 diff、切到 preview、侧边树切换** 没有统一禁用策略。
- 生成 token 直接写入编辑区，用户不知道这是“临时流式稿”还是“已保存草稿”。
- `workflow_step` 其实有 running/done 两种状态，但前端只在 running 时显示当前步骤，done 没有沉淀为步骤列表或时间线。
- `handleStopStream()` 只是中止前端流；后端没有显式取消协议，也没有把这次中止写成可识别状态。
- `parseSSEStream` 读完流会主动补一条 `workflow_done: completed`；如果后端已发过一次 `workflow_done`，存在前端收到两次完成语义的风险。
- `streamGenerateDoc` / `streamGenerateChildrenDocs` 的 `.catch(() => {})` 直接吞错误，前端可能出现“静默失败”。

### 审计结论

“生成中”目前是最接近主链核心价值的部分，但状态反馈仍然偏工程视角，用户恢复动作和动作边界不够清晰。

---

## 3.4 生成失败

### 当前行为

- 后端在 `run_doc_workflow_stream()` 异常时会尝试把 `generation_status` 更新为 `failed`。
- 前端在：
  - `workflow_step.status === failed`
  - `workflow_done.status === failed`
  - `generation-status === failed`
  时会显示错误。

### 断点/异常路径

- 错误提示入口多，但没有统一失败状态模型。
- 页面失败后只剩一条 error banner，没有“重试 / 继续编辑 / 回到上个版本”主动作设计。
- 如果 SSE 请求网络层失败，`client.ts` 基本吞异常，不保证页面进入明确失败态。
- `get_generation_status()` 在后端如果 migration 未应用，会回退成全 null；页面会把它理解成“没有后台状态”，不是“环境未就绪”。
- `handleGenerate()` 启动时会先 `setContent("")`，若生成失败，用户可能丢失当前未保存内容的视觉上下文。

### 审计结论

失败路径已部分落地，但现在更像“报错后结束”，还不是“失败后可恢复”的工作流。

---

## 3.5 已有文档

### 当前行为

- `getRequirementDoc()` 成功时会把内容加载到编辑区，`savedContent` 同步为当前内容。
- 版本列表来自 `/doc/versions`。
- 左侧树 `has_doc` 基于 `product_requirement_repository.list_tree()` 对 `requirement_doc_meta` 的 LEFT JOIN。
- 保存成功后会刷新版本列表；生成完成或子文档完成后也会触发局部 tree reload。

### 断点/异常路径

- “已有文档”没有独立首屏状态，只是 textarea 里有内容。
- `has_doc` 只看 meta 存不存在，不区分：
  - 真有有效文档
  - 只有 `version=0` + `generation_status` 的占位行
- 因为 `update_generation_status(running)` 会在生成前插入 meta(version=0)，树上可能提前显示“有文档”，但实际内容文件尚不存在。
- 页面没有展示“最后更新时间 / 当前版本 / 生成来源（manual/agent/workflow）”等有助于审阅的关键信息。

### 审计结论

“已有文档”在存储层有数据，在体验层没有被定义为明确状态，且 `has_doc` 语义已被 generation placeholder 污染。

---

## 3.6 diff

### 当前行为

- `变更`按钮进入 diff 模式。
- 若版本数 >= 2 且用户尚未选择版本，默认比较最新两版。
- `/doc/diff` 返回两个版本原文，前端用 `MarkdownDiffRenderer` 渲染。

### 断点/异常路径

- 当版本少于两版时，进入 diff 没有空态提示，不知道为什么看不到结果。
- diff 只基于“已保存版本”，**当前编辑中的未保存草稿** 不在最短审阅路径内。
- `loadDiff()` 出错时只把 `diffContent` 设 null，没有错误提示。
- 页面没有默认强调“当前稿 vs 上一版本”的最短路径文案，只是自动代选。

### 审计结论

diff 能用，但仍偏底层功能，不足以支撑“生成后立刻审阅”的主链。

---

## 3.7 save

### 当前行为

- `保存`触发 `PUT /doc`，`generated_by=manual`。
- Review 应用变更时保存 `generated_by=agent`。
- 工作流保存草稿时后端写 `generated_by=workflow`。
- 保存后版本号递增，版本列表刷新，`savedContent` 更新，dirty 消失。

### 断点/异常路径

- 手动保存成功后没有成功反馈，只是按钮状态恢复。
- 页面没有展示当前版本，因此用户难以感知“刚才保存生成了一个新版本”。
- 保存后需求树是否立即反映状态，依赖 meta 已存在；没有统一的“保存成功→树刷新→状态同步”动作。
- 当前页面的 review/save 闭环只覆盖 Agent 改稿，不覆盖“生成结果先 diff/review 再保存”的 Week2 目标路径。

### 审计结论

save 的底层能力存在，但还没成为一个对用户可见的版本化闭环。

---

## 3.8 子文档生成

### 当前行为

- 左树对 epic/story 节点显示 ⚡ 按钮。
- 点击后先调用 `/doc/can-generate-children`，当前规则仅检查父需求是否存在 doc meta。
- 通过后调用 `/doc/generate-children` SSE。
- 前端消费：
  - `decompose_done`
  - `child_start`
  - `child_done`
  - `workflow_done`
- 树上能显示子项 pending/running/completed/failed 状态。

### 断点/异常路径

- 门禁只看“有 meta”，不看：
  - 父文档内容是否真实存在
  - 文档是否完成到可拆分质量
  - 拆分建议是否存在
  - 当前层级是否真的允许生成子级
- 门禁失败文案固定为“请先完成当前需求文档后再生成子级文档”，但后端并没有返回失败原因，因此前端无法说清真实原因。
- 前端没消费 `child_progress`，只能看到开始/完成，看不到子项内部步骤。
- `streamGenerateChildrenDocs` 同样吞网络错误，失败时容易静默。
- 任务包要求“完成后刷新树与当前页状态”，当前只做了 tree reload，没有针对当前页状态的统一刷新。
- 如果父节点处于 `running` 时已插入 meta(version=0)，理论上可能提前放开子文档生成门禁。

### 审计结论

子文档生成已有雏形，但门禁语义偏弱、反馈粒度不足，是 Week2 主链里最容易“看起来能点、实际上不稳”的部分。

---

## 4. 关键断点汇总（主链视角）

### 4.1 页面状态语义断点

- 页面没有统一主状态：无文档 / 生成中 / 生成失败 / 待审阅 / 可保存 / 保存完成。
- 当前页面更像“编辑器 + 按钮面板”，不是工作流页面。

### 4.2 后端状态语义断点

- `requirement_doc_meta` 同时承担：
  - 文档存在性
  - 当前版本元数据
  - generation status 占位
- `version=0 + generation_status=running/pending` 会污染“是否已有文档”的判断。

### 4.3 恢复路径断点

- 生成失败后没有显式重试策略。
- SSE 请求失败可能被静默吞掉。
- 停止生成只是前端中止，不是完整取消协议。

### 4.4 审阅闭环断点

- diff 基于已保存版本；review 基于 Agent 改稿；两条审阅链没有统一成一个主闭环。
- 生成结果没有默认进入 review/diff 的稳定路径。

### 4.5 树入口与状态回显断点

- 左树 `has_doc` 可能被 generation placeholder 提前置真。
- 保存/生成/子文档后虽有局部刷新，但没有统一状态同步规则。

---

## 5. P0 / P1 问题清单与任务映射

## 5.1 P0（Week2 主链必须收敛）

### P0-1 页面缺少统一状态模型，用户不知道当前状态和下一步动作
- **现象**：首屏只有按钮组合，没有“无文档 / 生成中 / 失败 / 待审阅 / 可保存”主状态表达。
- **原因猜测**：页面是在现有功能上叠加生成、diff、review、树等能力，缺少统一状态收敛层。
- **建议归属任务 ID**：`W2-RD-02`

### P0-2 `has_doc` 被 generation placeholder 污染，树状态可能失真
- **现象**：后端在生成开始时就 `update_generation_status(..., running)` 并插入 meta(version=0)；树接口只看 meta 是否存在，因此可能在文档尚未真正生成时显示“有文档”。
- **原因猜测**：`requirement_doc_meta` 同时承载“存在性”和“生成状态”两种语义，但树侧只做了 `(m.id IS NOT NULL)` 的简化判断。
- **建议归属任务 ID**：`W2-RD-05`，必要时联动 `W2-RD-03`

### P0-3 生成失败与网络失败没有统一恢复面
- **现象**：有些失败走 `workflow_done.failed`，有些失败走 polling failed，有些 fetch 层直接吞掉，页面上恢复动作也不统一。
- **原因猜测**：前端只按事件点做补丁式处理，没有“生成失败状态机”。
- **建议归属任务 ID**：`W2-RD-03`

### P0-4 生成结果没有稳定接入 diff/review/save 主闭环
- **现象**：生成完成后通常回到编辑态；diff 只看版本，review 只服务 Agent 改稿，用户缺少“生成完成→审阅→保存版本”的明确最短路径。
- **原因猜测**：diff/review/save 三个能力是并列功能，不是串联动作链。
- **建议归属任务 ID**：`W2-RD-04`

### P0-5 子文档门禁过弱，容易在错误时机放开
- **现象**：`can_generate_children` 只检查 meta 存在；如果父文档还在 running/pending 或只有 version=0，也可能被判定为可生成。
- **原因猜测**：门禁实现是“有文档即可”，但真实 Week2 语义应更接近“父文档已稳定完成且满足拆分前置条件”。
- **建议归属任务 ID**：`W2-RD-06`

### P0-6 子文档流缺少子项内部步骤反馈
- **现象**：前端只显示 `child_start` / `child_done`，后端已有 `child_progress`，但页面未消费，用户看不到子项进行到哪一步。
- **原因猜测**：前端树只做了最小进度面，没有接上更细粒度流事件。
- **建议归属任务 ID**：`W2-RD-06`

## 5.2 P1（不一定阻塞 Week2 首演，但应尽快收敛）

### P1-1 空文档态与接口失败态被混成同一个空编辑器
- **现象**：`loadDoc()` catch 后直接置空，用户看不出是“暂无文档”还是“请求异常”。
- **原因猜测**：前端把 404 业务空态和异常空态统一吞掉了。
- **建议归属任务 ID**：`W2-RD-02`

### P1-2 生成时动作禁用规则不完整
- **现象**：生成中仍可能进行保存、切节点、切 diff 等操作，语义不一致。
- **原因猜测**：页面只在按钮级做局部 disable，没有动作白名单/黑名单设计。
- **建议归属任务 ID**：`W2-RD-03`

### P1-3 手动停止生成不是完整取消协议
- **现象**：`handleStopStream()` 只中止前端流，不保证后端状态同步到“已取消/已停止”。
- **原因猜测**：当前实现把 abort 当作前端本地动作，不是工作流级状态转换。
- **建议归属任务 ID**：`W2-RD-03`

### P1-4 diff 空态与异常态没有可见反馈
- **现象**：版本不足、接口失败、未选择版本时，页面很容易只剩空白 diff 区。
- **原因猜测**：diff 功能实现优先了“能比”，没有处理“不能比时怎么说”。
- **建议归属任务 ID**：`W2-RD-04`

### P1-5 保存成功缺少版本化反馈
- **现象**：保存后只是 dirty 消失，用户难以感知新增版本与当前版本号。
- **原因猜测**：save 更偏存储动作，没有做用户可见的版本成功提示。
- **建议归属任务 ID**：`W2-RD-04`

### P1-6 树与当前页刷新规则不统一
- **现象**：生成完成、保存、子文档完成时有的刷新 tree，有的只刷新 doc/versions，没有统一同步策略。
- **原因猜测**：各动作后都是局部补刷新，没有定义“哪些事件必须同步哪些视图”。
- **建议归属任务 ID**：`W2-RD-05`

### P1-7 子文档门禁失败原因不可解释
- **现象**：前端只能显示统一文案“请先完成当前需求文档后再生成子级文档”。
- **原因猜测**：后端接口只返回 boolean，不返回 reason code / detail。
- **建议归属任务 ID**：`W2-RD-06`

### P1-8 主链测试断面明显不足
- **现象**：从当前代码形态看，主链涉及的空态、生成失败、diff 空态、children progress 等分支很容易回归，但任务包中仅列了待补测试，当前主链没有看到足够完整的保护网。
- **原因猜测**：能力开发先于主链验收抽象，测试尚未围绕 Week2 主链组织。
- **建议归属任务 ID**：`W2-RD-07`

### P1-9 Week2 演示口径尚未文档化
- **现象**：当前代码可以组合出演示，但没有单一主路径文档来规避现场踩断点。
- **原因猜测**：产品化收口尚未开始。
- **建议归属任务 ID**：`W2-RD-08`

---

## 6. 建议的后续任务切分口径

### W2-RD-02 应承接什么
- 定义 RequirementDocPage 的可见状态模型
- 定义每个状态的首屏文案与主动作
- 区分空文档、接口失败、已有文档、待审阅

### W2-RD-03 应承接什么
- 收敛生成中/失败/恢复/取消语义
- 明确生成中哪些动作禁用，哪些允许
- 统一消费 SSE / polling / network error

### W2-RD-04 应承接什么
- 打通生成结果 → diff/review → save
- 把“当前稿 vs 上一版本”做成最短稳定路径
- 明确保存成功后的版本反馈

### W2-RD-05 应承接什么
- 修正树上文档状态语义，避免 `has_doc` 失真
- 统一页面保存/生成/子文档完成后的树刷新规则
- 固定树入口与文档页跳转一致性

### W2-RD-06 应承接什么
- 强化 `can-generate-children` 语义与失败原因
- 接上 `child_progress`
- 让完成后当前页与树状态同步收敛

### W2-RD-07 应承接什么
- 为 P0 路径补最小 API/UI 保护测试
- 特别覆盖：空态、running、failed、diff、children gating、children progress

### W2-RD-08 应承接什么
- 把以上收敛后的主链整理为演示脚本与验收清单
- 明确哪些是 Week2 已闭环，哪些进入 Week3

---

## 7. 最小结论

当前需求文档工作流**不是从零开始**，而是已经有一条“技术链路基本存在”的主链雏形；真正缺的是：

1. **状态语义收敛**：让用户一眼知道现在处于哪一站
2. **失败恢复收敛**：让失败后不是只看到报错，而是知道怎么办
3. **审阅保存收敛**：让生成结果自然进入 diff/review/save
4. **树状态收敛**：让入口和状态回显不说谎
5. **子文档门禁收敛**：让批量生成不是“能点就点”，而是有条件、有反馈

如果 Week2 只允许优先处理少数关键点，建议优先级仍应保持为：

1. `W2-RD-02` 状态模型
2. `W2-RD-03` 生成反馈与恢复
3. `W2-RD-04` diff/review/save 闭环

这是因为当前最大的风险不在“功能不存在”，而在“功能存在但讲不清、恢复不了、演示时容易断”。
