# Week2 Requirement Doc Acceptance

日期：2026-03-27  
任务 ID：W2-RD-08  
适用对象：老大 / 评审 / 交接同学

---

## 1. 本次验收想回答什么

Week2 不回答“功能是不是越来越多”，只回答三件事：

1. 需求文档工作流主链是否已经可演示。  
2. 主链是否已经有最小验证依据。  
3. 哪些问题属于已知环境阻塞，不能被包装成业务功能未完成。

---

## 2. Week2 已完成项（按主链口径）

结合 W2-RD-01 ~ W2-RD-07 当前产出，Week2 已完成以下收敛：

- 已完成需求文档页主状态与主动作收敛。
- 已完成生成流反馈与失败恢复基础能力收敛。
- 已完成 diff / review / save 主闭环打通。
- 已完成需求树入口、文档状态回显、页面跳转一致性补强。
- 已完成子文档生成门禁与进度反馈补强。
- 已完成后端主链相关 API / storage / gate / tree 状态测试补齐。
- 已完成一份面向非开发验收人员的手工 checklist。
- 已完成本次演示脚本、验收清单、遗留项清单结果包。

当前判断：**Week2 主链已经达到“能看、能验、能继续接”的交付线，但不是全绿完美态。**

---

## 3. 本次核验依据

### 文档依据
- `docs/WEEK2_REQUIREMENT_DOC_AUDIT.md`
- `docs/WEEK2_REQUIREMENT_DOC_MANUAL_CHECKLIST.md`
- `docs/WEEK2_REQUIREMENT_DOC_DEMO_SCRIPT.md`
- `docs/WEEK2_REQUIREMENT_DOC_OPEN_ISSUES.md`

### 提交依据
- `3918fc1` docs: audit requirement doc workflow main path
- `27f99d8` feat(web): unify requirement doc page state model
- `5438daa` feat(doc): surface generation progress and recovery
- `08fee17` feat(web): close review diff save loop for requirement docs
- `9bf7e77` feat(web): align requirement tree entry and doc status
- `2df69e0` feat(doc): harden child doc generation gating and progress
- `5bcf3e1` test(doc): cover requirement doc main workflow

### 本次复核结果
- 后端定向测试：`pytest tests/test_requirement_doc_storage.py tests/test_requirement_doc_api.py tests/test_requirement_doc_children_gate.py tests/test_product_requirement_tree_doc_status.py` → **17 passed**
- 前端构建：`npm run build`（`web/`）→ **通过**
- 前端测试：`npm run test:run`（`web/`）→ **未全绿，当前失败 1 条**，失败点位于 `RequirementDocPage.test.tsx` 对“文档生成失败”文案的断言，属于前端测试口径/实现对齐问题，不能算作 Week2 主链完全全绿。

---

## 4. 验收步骤与通过标准

## A. 入口与状态识别

### 步骤
- 从需求树进入 Requirement Doc 页面。
- 分别检查空态、已有态、生成中、生成失败等状态是否能被区分。

### 通过标准
- 用户能看懂当前状态。
- 页面不是只有按钮堆叠，而是能表达下一步动作。

### 未通过时怎么处理
- 记为“状态语义未收敛”，回到页面状态层修正。
- 不允许用口头解释代替产品状态表达。

---

## B. 生成与恢复

### 步骤
- 在空文档节点点击“AI 生成文档”。
- 观察过程反馈；必要时刷新页面，看后台状态能否恢复。
- 若失败，检查是否存在重试或继续编辑路径。

### 通过标准
- 生成过程有清晰反馈。
- 失败后不是卡死，而是能继续处理。

### 未通过时怎么处理
- 记为“生成恢复链未闭环”，回到生成状态与恢复逻辑修正。
- 若问题由模型服务或环境引起，单独记为环境阻塞，不假装前端功能已通过。

---

## C. 审阅、保存、版本

### 步骤
- 对生成结果做最小修改。
- 进入 diff / review。
- 保存为新版本。

### 通过标准
- 差异可见。
- 保存后版本列表刷新。
- 用户能确认新版本已经形成。

### 未通过时怎么处理
- 记为“审阅保存链断裂”，回到 diff/review/save 闭环修正。
- 若只是提示文案或测试断言不一致，也要记录，但不要夸大为主链不可用。

---

## D. 树状态回显与子文档继续生成

### 步骤
- 保存后返回树或观察左侧树状态。
- 在满足条件的 Epic/Story 上触发子文档生成。
- 在不满足条件时验证门禁提示。

### 通过标准
- 树状态与详情页一致。
- 子文档门禁可拦截、可放行、可反馈。

### 未通过时怎么处理
- 记为“树状态回显/子文档门禁未收敛”。
- 若问题只在环境层复现，应进入遗留项，不把业务完成度说成 100%。

---

## 5. 对当前 EPERM 环境阻塞的诚实口径

必须明确：**Week2 结果包不按“全绿”汇报。**

当前前端验收口径里，需要显式保留以下环境风险：

- `vite/esbuild spawn EPERM` 曾作为前端 test/build 的环境阻塞项出现。
- 这类问题的性质是**环境/执行层阻塞**，不是需求文档主链产品语义本身的设计目标。
- 因此，Week2 可以判断为“主链已收敛到可演示、可验收”，但**不能包装成前端环境已经稳定无风险**。
- 本次复核里 `npm run build` 已通过，但这不应直接抹掉 EPERM 风险记录；该项仍应放在遗留问题中持续追踪，直到环境稳定性被单独验证关闭。

换句话说：

- **可以说主链功能基本到位；**
- **不能说前端环境问题已经彻底清零。**

---

## 6. Week2 验收结论

### 结论分级
- **主链完成度**：高，已达到 Week2 结果展示和继续交接的要求。
- **测试完成度**：中高，后端主链测试已补齐；前端测试仍有未全绿项。
- **环境稳定度**：中，仍需诚实保留 `vite/esbuild spawn EPERM` 风险口径。

### 总结判断
**建议将 Week2 判定为“功能主链完成，可进入老板评审/Week3 衔接”，但附带环境与前端测试未完全清零的说明。**

这比“假装全绿”更可靠，也更适合后续继续接手。
