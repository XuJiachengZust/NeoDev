# NeoDev Week2 任务包（需求文档工作流主链）

日期：2026-03-26  
适用对象：Codex / 子智能体 / 并行执行任务负责人  
范围边界：仅围绕“需求文档工作流主链”收敛推进，不横向扩线到其他页面、其他业务域、Deep Agent 架构重写、全站 UI 重设。

---

## 0. 本任务包的目标

把 NeoDev 已具备基础能力的“需求文档工作流”进一步收敛为一条可稳定演示、可验收、可按最小提交单元推进的 Week2 主链：

**进入需求文档页 → 判断当前状态 → 触发生成/续生成 → 审阅 diff/review → 保存版本 → 回到需求树看到状态变化 → 按条件生成子文档。**

本任务包强调：
- 每个任务都要能单独 review
- 每个任务都要有明确验证命令
- 每个任务都要有边界，避免一个任务跨太多层
- 默认按推荐顺序串行；仅在依赖允许时并行

---

## 1. 主链范围与非目标

### 1.1 纳入范围
- 需求文档页状态语义收敛
- 文档生成与续生成反馈
- diff / review / save 闭环
- 需求树入口与文档状态回显
- 子文档生成前置条件与执行反馈
- Week2 演示脚本、验收清单、遗留项收口

### 1.2 不纳入范围
- Deep Agent 新架构或会话系统重写
- 非需求文档主链的全站页面优化
- 版本主线、提交主线的大范围改造
- 新的 DSL / 解析语言扩展
- 大型数据库重构

---

## 2. 推荐执行顺序

建议顺序：
1. **W2-RD-01** 主链审计与断点清单固化
2. **W2-RD-02** 文档页状态模型与动作栏收敛
3. **W2-RD-03** 生成流状态反馈与异常恢复
4. **W2-RD-04** diff / review / save 闭环打通
5. **W2-RD-05** 需求树入口、状态回显、跳转一致性
6. **W2-RD-06** 子文档生成门禁与流式反馈
7. **W2-RD-07** 生成/保存/子文档链路测试补齐
8. **W2-RD-08** Week2 演示脚本与验收清单收口

并行建议：
- W2-RD-07 可在 03/04/05/06 基本稳定后启动
- W2-RD-08 可在 05 之后先起草，最终在 06/07 完成后收口

---

## 3. 任务包明细

---

### W2-RD-01｜主链审计与断点清单固化

- **目标**：把“需求文档工作流主链”的当前真实行为、断点、异常路径梳理成一份可执行问题单，而不是停留在泛规划。
- **边界**：只审计需求文档主链；不在本任务内直接重构逻辑。
- **涉及文件**：
  - `web/src/pages/RequirementDocPage.tsx`
  - `web/src/api/client.ts`
  - `src/service/routers/requirement_docs.py`
  - `src/service/services/requirement_doc_service.py`
  - `src/service/repositories/product_requirement_repository.py`
  - 新增：`docs/WEEK2_REQUIREMENT_DOC_AUDIT.md`
- **执行内容**：
  - 梳理主链步骤图
  - 标出页面状态、接口状态、错误提示、回跳逻辑、需求树状态展示的断点
  - 形成 P0 / P1 问题列表，并映射到后续任务 ID
- **验证命令**：
  - `git -C D:\PycharmProjects\NeoDev diff -- docs/WEEK2_REQUIREMENT_DOC_AUDIT.md`
- **验收标准**：
  - 审计文档至少覆盖：进入页面、加载空文档、生成中、生成失败、已有文档、diff、save、子文档生成
  - 每个问题都能映射到本任务包中的后续任务，不出现“泛泛而谈”
- **推荐提交信息**：
  - `docs: audit requirement doc workflow main path`
- **建议执行顺序**：1

---

### W2-RD-02｜文档页状态模型与动作栏收敛

- **目标**：统一 RequirementDocPage 中用户可见状态与主动作，避免“有功能但下一步不清楚”。
- **边界**：只收敛页面状态模型、动作区和文案；不在本任务内处理复杂子文档流。
- **涉及文件**：
  - `web/src/pages/RequirementDocPage.tsx`
  - 如有需要：`web/src/App.css`
- **执行内容**：
  - 明确页面主状态：无文档、已有草稿、生成中、待审阅、可保存、保存完成、生成失败
  - 统一顶部动作栏：编辑 / 预览 / diff / review / 保存 / 生成 / 续生成
  - 清理互相冲突或重复的提示文案
  - 让“当前状态 + 下一步动作”在首屏可读
- **验证命令**：
  - `cd D:\PycharmProjects\NeoDev\web; npm run test:run`
  - `cd D:\PycharmProjects\NeoDev\web; npm run build`
- **验收标准**：
  - 首屏能明确告诉用户当前文档状态
  - 不同状态下的主动作不冲突
  - 没有需要靠读代码才能理解的隐式流程切换
- **推荐提交信息**：
  - `feat(web): unify requirement doc page state model`
- **建议执行顺序**：2

---

### W2-RD-03｜生成流状态反馈与异常恢复

- **目标**：把“AI 生成”从黑盒操作变成可理解流程，至少让用户知道进行到哪一步、失败在哪、如何恢复。
- **边界**：只处理当前文档生成链路；不在本任务内扩展新的工作流能力。
- **涉及文件**：
  - `web/src/pages/RequirementDocPage.tsx`
  - `web/src/api/client.ts`
  - `src/service/routers/requirement_docs.py`
  - `src/service/workflows/requirement_doc_workflow.py`
  - 如有需要：`src/service/repositories/requirement_doc_repository.py`
- **执行内容**：
  - 前端统一消费 `workflow_step` / `token` / `workflow_done` / `error`
  - 对 `generation-status` 做页面恢复或轮询兜底，避免刷新后丢失语义
  - 补齐失败提示、取消/重试/继续编辑的恢复动作
  - 明确“生成中禁止哪些动作，允许哪些动作”
- **验证命令**：
  - `cd D:\PycharmProjects\NeoDev; pytest tests/test_requirement_doc_storage.py`
  - `cd D:\PycharmProjects\NeoDev\web; npm run test:run`
  - `cd D:\PycharmProjects\NeoDev\web; npm run build`
- **验收标准**：
  - 用户能看到至少 3 个清晰步骤状态
  - 生成失败后页面不会卡死，能继续重试或回到编辑
  - 刷新页面后，生成状态不会完全失忆
- **推荐提交信息**：
  - `feat(doc): surface generation progress and recovery`
- **建议执行顺序**：3

---

### W2-RD-04｜diff / review / save 闭环打通

- **目标**：把“生成结果 → 审阅差异 → 接受修改 → 保存版本”做成完整闭环。
- **边界**：只围绕 diff/review/save；不在本任务内新增更多 AI 交互玩法。
- **涉及文件**：
  - `web/src/pages/RequirementDocPage.tsx`
  - `web/src/components/MarkdownDiffRenderer.tsx`
  - `web/src/components/MarkdownDiffReviewer.tsx`
  - `web/src/api/client.ts`
  - `src/service/routers/requirement_docs.py`
  - `src/service/services/requirement_doc_service.py`
- **执行内容**：
  - 统一 diff 模式与 review 模式的进入/退出条件
  - 让 review 结果可以明确写回编辑区并保存
  - 保存成功后刷新版本列表与当前版本引用
  - 默认给出“当前稿 vs 上一版本”的最短审阅路径
- **验证命令**：
  - `cd D:\PycharmProjects\NeoDev\web; npm run test:run`
  - `cd D:\PycharmProjects\NeoDev\web; npm run build`
- **验收标准**：
  - 用户可从生成结果直接进入 review/diff
  - 保存后版本列表可见新增版本
  - 至少有一条“上一版本 vs 当前稿”的稳定 diff 展示路径
- **推荐提交信息**：
  - `feat(web): close review diff save loop for requirement docs`
- **建议执行顺序**：4

---

### W2-RD-05｜需求树入口、状态回显、跳转一致性

- **目标**：让用户从需求树进入文档页的入口清晰，且能在树上看到文档状态，不再只在文档页内自嗨。
- **边界**：只处理需求树与文档页之间的入口和状态同步；不扩展到其他导航结构。
- **涉及文件**：
  - `src/service/repositories/product_requirement_repository.py`
  - `web/src/api/client.ts`
  - `web/src/pages/RequirementDocPage.tsx`
  - `web/src/App.tsx`（如需路由校正）
- **执行内容**：
  - 确认需求树接口 `has_doc` 行为稳定
  - 在文档页左侧树/相关树视图中统一文档状态显示
  - 明确文档按钮、当前节点高亮、切换节点时未保存拦截
  - 保存后、子文档生成后主动刷新树状态
- **验证命令**：
  - `cd D:\PycharmProjects\NeoDev; pytest tests/test_api_preprocess.py`
  - `cd D:\PycharmProjects\NeoDev\web; npm run test:run`
  - `cd D:\PycharmProjects\NeoDev\web; npm run build`
- **验收标准**：
  - 树上能区分有文档/无文档状态
  - 从树切换不同需求时，路由与页面内容一致
  - 未保存变更有明确阻断或确认
- **推荐提交信息**：
  - `feat(web): align requirement tree entry and doc status`
- **建议执行顺序**：5

---

### W2-RD-06｜子文档生成门禁与流式反馈

- **目标**：把“生成子文档”从隐藏能力点收敛为可理解、可控、可反馈的流程。
- **边界**：仅处理 Epic/Story 向下生成子文档的门禁、入口、进度反馈；不在本任务内改造拆分算法本身。
- **涉及文件**：
  - `web/src/pages/RequirementDocPage.tsx`
  - `web/src/api/client.ts`
  - `src/service/routers/requirement_docs.py`
  - `src/service/services/requirement_doc_service.py`
  - `src/service/workflows/requirement_doc_workflow.py`
- **执行内容**：
  - 明确 can-generate-children 失败原因文案
  - 统一子文档生成入口只出现在允许层级
  - 流式展示 `decompose_done / child_start / child_done / workflow_done`
  - 完成后刷新树与当前页状态
- **验证命令**：
  - `cd D:\PycharmProjects\NeoDev\web; npm run test:run`
  - `cd D:\PycharmProjects\NeoDev\web; npm run build`
- **验收标准**：
  - 用户能理解为什么当前不能生成子文档
  - 子文档批量生成时能看到子项级别进度
  - 生成完成后需求树状态同步更新
- **推荐提交信息**：
  - `feat(doc): harden child doc generation gating and progress`
- **建议执行顺序**：6

---

### W2-RD-07｜主链自动化测试与最小手工验证包

- **目标**：为 Week2 主链补足最低限度的自动化验证与手工验收步骤，保证任务包交付后可持续 review。
- **边界**：只补主链相关测试；不补无关历史测试债。
- **涉及文件**：
  - `tests/test_requirement_doc_storage.py`
  - 如缺失则新增：
    - `web/src/pages/RequirementDocPage.test.tsx`
    - `tests/test_requirement_docs_api.py`
  - 新增：`docs/WEEK2_REQUIREMENT_DOC_MANUAL_CHECKLIST.md`
- **执行内容**：
  - 为文档 CRUD / 版本 / diff / can-generate-children / generation-status 补最小 API 级测试
  - 为文档页补 1~2 条关键前端交互测试
  - 输出手工验收 checklist
- **验证命令**：
  - `cd D:\PycharmProjects\NeoDev; pytest`
  - `cd D:\PycharmProjects\NeoDev\web; npm run test:run`
  - `cd D:\PycharmProjects\NeoDev\web; npm run build`
- **验收标准**：
  - 至少覆盖：读取文档、保存版本、diff 对比、子文档门禁、生成状态展示
  - 手工 checklist 可供非开发人员按步骤复现主链
- **推荐提交信息**：
  - `test(doc): cover requirement doc main workflow`
- **建议执行顺序**：7

---

### W2-RD-08｜Week2 演示脚本、验收清单、遗留项收口

- **目标**：把 Week2 产出整理成可给老大/评审直接查看的结果包，而不是只有代码提交。
- **边界**：文档收口任务，不在本任务内继续追加功能。
- **当前交付物（2026-03-27）**：
  - `docs/WEEK2_REQUIREMENT_DOC_DEMO_SCRIPT.md`
  - `docs/WEEK2_REQUIREMENT_DOC_ACCEPTANCE.md`
  - `docs/WEEK2_REQUIREMENT_DOC_OPEN_ISSUES.md`
- **涉及文件**：
  - 新增：`docs/WEEK2_REQUIREMENT_DOC_DEMO_SCRIPT.md`
  - 新增：`docs/WEEK2_REQUIREMENT_DOC_ACCEPTANCE.md`
  - 新增：`docs/WEEK2_REQUIREMENT_DOC_OPEN_ISSUES.md`
  - 更新：`docs/WEEK2_REQUIREMENT_DOC_TASK_PACK_2026-03-26.md`
- **执行内容**：
  - 固化 1 条主演示路径
  - 输出阶段验收清单
  - 输出已知遗留项与 Week3 输入
- **验证命令**：
  - `git -C D:\PycharmProjects\NeoDev diff -- docs/WEEK2_REQUIREMENT_DOC_DEMO_SCRIPT.md docs/WEEK2_REQUIREMENT_DOC_ACCEPTANCE.md docs/WEEK2_REQUIREMENT_DOC_OPEN_ISSUES.md`
- **验收标准**：
  - 非开发人员按文档可完成演示
  - 验收清单能逐项勾选，不依赖口头解释
  - 明确区分 Week2 已完成 / 未完成 / Week3 输入
- **推荐提交信息**：
  - `docs: add week2 requirement doc demo and acceptance pack`
- **建议执行顺序**：8

---

## 4. 派工建议（给 Codex / 子智能体）

### 4.1 单任务派工模板
每次只派发 1 个任务 ID，要求执行体输出：
- 改动文件清单
- 关键实现点
- 验证命令与结果
- 未解决问题/风险
- 建议提交信息

### 4.2 禁止事项
- 不允许顺手扩大需求
- 不允许一个任务同时重构前后端大块逻辑
- 不允许跳过验证直接回报“已完成”
- 不允许把“后续再补测试”当成默认策略

### 4.3 推荐派工粒度
- 前端主链：优先 W2-RD-02 / 03 / 04 / 05 / 06
- 后端补口：优先围绕 03 / 06 / 07 做契约稳定
- 文档与验收：最后执行 08，但可提前准备草稿

---

## 5. Week2 Done 判定

Week2 不是“提交够多”就算完成，而是至少满足以下条件：
- 能从需求树进入文档页
- 页面能表达当前文档状态与下一步动作
- 能触发生成，并看到过程反馈/失败恢复
- 能进行 diff / review / save，且版本能回看
- 能理解何时允许生成子文档，并看到子任务级反馈
- 有演示脚本、验收清单、遗留项清单

---

## 6. 最适合的执行策略

如果只允许先开 3 个任务，建议顺序为：
1. **W2-RD-01**：先把断点钉死，防止后面任务边界漂移
2. **W2-RD-02**：先收敛状态模型，后续所有动作才有统一语义
3. **W2-RD-03**：生成流是 Week2 样板价值最高的感知点，应该最早打磨

原因：这三个任务会先把“主链看得见、讲得清、不会失控”建立起来，后面的 diff/save/tree/children 才会更顺。
