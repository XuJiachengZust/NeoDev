# NeoDev 仓库 Codex 工作流

## 适用范围

本流程用于 Codex 在 NeoDev 仓库内执行日常开发任务，目标是让每次改动都具备可控范围、稳定验证和可追踪提交。

## 默认思考强度

- 规划阶段使用高思考。
  适用于需求拆分、跨层影响评估、数据库或接口设计、失败原因不明确的故障排查。
- 开发阶段使用中思考。
  适用于已确认范围后的编码、补测试、补文档、前后端对接。
- 审核阶段默认回到高思考。
  适用于 diff 自查、提交前风险核对、确认是否需要拆 commit。

## 核心规则

- 每个最小可用单元必须独立提交 1 个 git commit。
- 不混入无关改动，不顺手修邻近问题，不做“顺便重构”。
- 只 stage 本任务需要的文件，禁止 `git add .`。
- 当前工作区若已存在用户未提交改动，默认共存，不回滚、不覆盖、不整理。
- API、数据库、前端联动改动可以同一个 commit，但前提是它们共同服务于同一个最小目标。

## 标准执行流程

### 1. 开工前

- 先运行 `git status --short`，识别脏工作区与无关变更。
- 只读取完成当前目标所需的文件，不先做全仓大扫读。
- 用一句话写清当前最小目标。
  例：`为产品版本分支映射自动补建项目 version`

### 2. 规划

- 用高思考确认以下内容后再动手：
  - 目标产出是什么
  - 最少要改哪些文件
  - 验收标准是什么
  - 需要跑哪些验证命令
  - 推荐 commit 标题是什么
- 若目标无法在 1 个 commit 内说清，先继续拆分，直到可以独立提交。

### 3. 开发

- 切到中思考直接实现，不在实现中扩大目标。
- 遵循仓库现有分层：
  - 后端优先按 `router -> service -> repository -> tests`
  - 前端优先按 `api/client -> page/component -> tests`
  - 数据改动优先按 `migration -> repository/service -> tests`
- 没有明确收益时，不移动文件、不改命名、不统一格式。

### 4. 验证

- 后端改动至少跑对应 `pytest` 文件。
- 前端改动至少跑 `cd web && npm run test:run`；涉及构建路径时再跑 `cd web && npm run build`。
- 只改文档时至少跑 `git diff --check`，确认没有意外空白和混入文件。
- 如果环境阻塞导致某项验证无法执行，提交说明里必须写明未执行项与原因。

### 5. 提交

- 用精确路径 stage，例如：
  - `git add src/service/routers/commits.py tests/test_api_commits.py`
  - `git add web/src/api/client.ts web/src/pages/product/ProductProjectDetailPage.tsx`
- 提交信息使用短 Conventional Commit：
  - `feat: ...`
  - `fix: ...`
  - `refactor: ...`
  - `test: ...`
  - `docs: ...`
  - `chore: ...`
- 一个最小单元只允许一个提交主题。

## 最小单元判定标准

满足以下条件，才算可提交的最小单元：

- 能用一句话解释改动目标。
- 改动文件集合稳定，没有“顺带补丁”。
- 有明确验收标准。
- 有最小验证命令。
- 提交后即使后续任务未开始，当前仓库也处于可理解、可回滚、可继续开发状态。

## 禁止事项

- 禁止为赶进度把两个以上业务目标塞进一个 commit。
- 禁止把生成物、缓存、构建产物、密钥、临时计划文件提交进仓库。
- 禁止因工作区脏而使用破坏性 git 命令清理他人改动。
- 禁止仅因“看起来顺手”修改无关测试、样式、注释或格式。

## NeoDev 仓库内的建议命令矩阵

- 后端单文件验证：`pytest tests/test_api_commits.py -q`
- 后端领域回归：`pytest tests/test_sync_service.py tests/test_api_sync_placeholder.py -q`
- 前端测试：`cd web && npm run test:run`
- 前端构建：`cd web && npm run build`
- 文档提交检查：`git diff --check`
- 提交范围检查：`git diff --name-only --cached`

## 提交前自问

- 这次提交只解决了一个问题吗？
- 变更文件里是否出现了与目标无关的文件？
- 测试或构建是否覆盖了本次改动链路？
- 如果 reviewer 只看这一个 commit，能否快速理解其目的和边界？

满足以上问题后，再进入 [`REVIEW_GATE.md`](./REVIEW_GATE.md)。

