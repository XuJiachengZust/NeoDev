# NeoDev Week1 执行 Backlog

## 目标

本 Backlog 用于 Week1 的首批执行任务排程，默认由 Codex 主力开发，强调以下原则：

- 只做最小可用单元，每个单元有明确产出、验收标准、验证命令。
- 每个最小单元必须独立提交 1 个 git commit，不混入顺手修改。
- 优先处理已被代码现状直接证明存在的最小缺口，再处理中等范围的链路优化。
- 若某任务已被当前工作区中的未提交改动覆盖，先核对现状，再决定跳过、缩小或重拆该任务。

## 基于当前仓库状态的前置判断

- 后端与测试主线已具备继续推进 Week1 的基础：`src/service` 与 `tests/` 已覆盖项目、版本、提交、同步、预处理、影响面分析等核心域。
- `docs/TODO-backend-branch-view.md` 指向的分支视图主链路缺口仍然成立，尤其是：
  - `src/service/routers/requirements.py` 已存在，但 `src/service/routers/api.py` 尚未挂载项目级需求路由。
  - `ProductProjectDetailPage` 仍在前端兜底自动创建项目级 version，说明 `W1-03` 尚未下沉到后端。
  - 提交查询仍依赖 `version_id`，`project_id + branch` 的后端直查接口尚未提供。
- 当前 `git status --short` 的噪音主要由本地生成物和执行机制文档构成，例如 `web/node_modules/`、`web/dist/`、`__pycache__/`、`.cursor/plans/`、`docker/images/*.tar`、`bash.exe.stackdump`，以及本轮新增的执行文档。
- 但当前脏状态并不只包含可忽略内容，还包含至少一个已暂存大文件 `docker/images/neodev-all-images.tar`，以及明显属于作者产出的未跟踪测试/脚本/文档文件。仅做 `.gitignore` 并不能让当前工作区立刻变干净。
- 因此，`W1-01` 仍然必要，但不再应视为“首个阻塞任务”。它的定位应调整为“尽快执行的仓库卫生任务”，目标是降低后续提交噪音，而不是阻塞第一个功能修复。
- `W1-01` 的范围必须收敛到“只忽略确定属于本地生成物的路径”，不能为了追求清爽状态去隐藏作者产出的测试、脚本或机制文档。

## 当前建议执行顺序

1. 先执行 `W1-02`，因为它是已被现状直接证明的最小功能缺口，只需极小改动即可闭环验证。
2. 再执行 `W1-01`，把确定属于本地生成物的噪音从 `git status` 中移除，但不把作者产出隐藏掉。
3. 然后推进分支视图后端主链路：`W1-03` -> `W1-05` -> `W1-04` -> `W1-06` -> `W1-07`。
4. 最后处理可见性增强：`W1-08` -> `W1-09`。

## Week1 任务清单

| ID | 当前顺位 | 优先级 | 最小可用产出 | 预计涉及文件 | 完成标准 | 验证命令 | 推荐提交信息 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W1-02 | 1 | P0 | 校验并补齐项目级需求路由挂载，保证现有接口测试可通过 | `src/service/routers/api.py`、`src/service/routers/requirements.py`、`tests/test_api_requirements.py` | `/api/projects/{project_id}/requirements` 全套 CRUD 与 commit 绑定接口可访问；若现有代码已覆盖，则仅补测试或关闭任务 | `pytest tests/test_api_requirements.py -q` | `fix: register project requirement routes` |
| W1-01 | 2 | P0 | 只忽略确定属于本地生成物的 git 噪音 | `.gitignore` | `git status --short` 不再被 `web/node_modules`、`web/dist`、`__pycache__`、`.cursor/plans`、`.claude`、`docker/images/*.tar`、`bash.exe.stackdump` 等淹没；作者产出的测试、脚本、文档仍保持可见 | `git status --short` | `chore: ignore generated workspace artifacts` |
| W1-03 | 3 | P1 | 产品版本设置分支映射时，自动补建项目级 version | `src/service/services/product_version_service.py`、`src/service/repositories/version_repository.py`、相关测试文件 | `set_branch()` 写入映射后，若 `project_id + branch` 对应 version 不存在则自动创建；重复执行不产生脏数据 | `pytest tests/test_version_repository.py tests/test_api_versions.py -q` | `feat: auto create project version on branch mapping` |
| W1-05 | 4 | P1 | 新增按 `project_id + branch` 直接查询提交列表的后端接口 | `src/service/routers/commits.py`、`src/service/services/commit_service.py`、`src/service/repositories/commit_repository.py`、`tests/test_api_commits.py` | 提供 `GET /api/projects/{project_id}/commits-by-branch?branch=xxx`；找不到项目返回 404；找不到 version 返回空列表或明确定义的返回值并有测试约束 | `pytest tests/test_api_commits.py -q` | `feat: add commits by branch api` |
| W1-04 | 5 | P1 | 项目同步提交时，针对已映射分支自动补建项目级 version | `src/service/services/sync_service.py`、`tests/test_sync_service.py`、`tests/test_api_sync_placeholder.py` | `sync_commits_for_project()` 对存在产品分支映射但缺失项目 version 的情况自动补齐，避免同步结果为空 | `pytest tests/test_sync_service.py tests/test_api_sync_placeholder.py -q` | `feat: auto create version before project sync` |
| W1-06 | 6 | P1 | 提交列表接口支持分页 | `src/service/routers/commits.py`、`src/service/repositories/commit_repository.py`、`web/src/api/client.ts`、相关测试 | `listCommitsByVersion` 支持 `offset`、`limit`；默认值明确；返回结果与旧参数兼容；超大提交量下前端不必一次性拉全量 | `pytest tests/test_api_commits.py -q` | `feat: paginate version commits api` |
| W1-07 | 7 | P1 | 前端分支视图消费分页与按分支查询接口 | `web/src/api/client.ts`、`web/src/pages/product/ProductProjectDetailPage.tsx`、相关前端测试 | 产品项目详情页首屏只拉第一页，可继续加载；无需先手工查 version ID 才能按 branch 拉提交 | `cd web; npm run test:run` 和 `cd web; npm run build` | `feat: use paginated branch commit queries in product detail` |
| W1-08 | 8 | P2 | 影响面分析详情接口返回结构化结果 | `src/service/routers/impact.py`、`src/service/services/impact_analysis_service.py`、`src/service/repositories/impact_analysis_repository.py`、`tests/test_api_impact_analyses.py` | 提供详情查询入口，至少能返回分析元数据、关联 commit 信息、结构化影响对象占位或真实结果字段；返回契约固定下来 | `pytest tests/test_api_impact_analyses.py -q` | `feat: add impact analysis detail payload` |
| W1-09 | 9 | P2 | 需求关联提交反查结果补充 `project_name`，支持前端展开查看来源 | `src/service/repositories/product_requirement_repository.py`、`src/service/routers/product_requirements.py`、`web/src/pages/product/ProductRequirementsPage.tsx`、相关测试 | 需求绑定提交列表在跨项目场景可区分提交来源；前端可从“只看数量”升级为“可下钻看提交” | `pytest tests/test_api_requirements.py -q` 和 `cd web; npm run test:run` | `feat: show project source in requirement commits` |

## 每个任务的统一 Definition of Done

- 只解决 1 个最小问题，不顺手重构邻近模块。
- 只改完成该任务必需的文件；若必须跨层修改，必须在提交说明中写清楚链路。
- 至少补 1 个与改动直接对应的验证点：测试、构建或手工接口验证。
- 通过 [`CODEX_WORKFLOW.md`](./CODEX_WORKFLOW.md) 的工作流自检。
- 满足 [`REVIEW_GATE.md`](./REVIEW_GATE.md) 的提交前门槛。

## 建议节奏

- Day 1: `W1-02` -> `W1-01` -> `W1-03`
- Day 2 到 Day 3: `W1-05` -> `W1-04` -> `W1-06`
- Day 4: `W1-07`
- Day 5: `W1-08` -> `W1-09`

## Week1 明确不做

- 不做 `src/deepagents` 的架构重写。
- 不做新的解析语言扩展。
- 不做全站 UI 重设计。
- 不做与当前任务无关的数据库重构或大范围命名整理。
