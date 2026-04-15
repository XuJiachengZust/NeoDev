# NeoDev Week1 下一批直接执行任务

## 排序原则

- 只选“当前代码现状已证明存在缺口”的任务。
- 只选能够在单个 commit 内闭环验证的最小单元。
- 避开会立刻触发 repo/fetch/graph 环境复杂度的任务，优先做边界更清晰的修复。

## 任务 1：W1-02 挂载项目级需求路由

- 目标：把已经存在的 `requirements` 路由正式接入 `/api/projects/...` 聚合路由，消除“代码已存在但入口未暴露”的缺口。
- 涉及文件：`src/service/routers/api.py`、必要时复核 `src/service/routers/requirements.py`、`tests/test_api_requirements.py`
- 验证命令：`pytest tests/test_api_requirements.py -q`
- 推荐 commit message：`fix: register project requirement routes`
- 为什么现在做：这是当前最小、最确定、最容易形成独立提交的功能缺口；改动面极小，验证链路现成，完成后能立刻消除一类 404/不可访问问题。

## 任务 2：W1-01 只忽略确定的本地生成物

- 目标：收敛 `.gitignore`，只忽略明确属于本地生成物和工作区噪音的路径，降低后续 `git status` 与提交筛选成本。
- 涉及文件：`.gitignore`
- 验证命令：`git status --short`
- 推荐 commit message：`chore: ignore generated workspace artifacts`
- 为什么现在做：当前脏状态里生成物噪音很大，但又夹杂作者产出；此时做一个“只忽略安全项”的小提交性价比最高。它不该排在 `W1-02` 前面，因为它无法解决已暂存大文件和作者产出带来的全部脏状态，但它能显著改善后续执行视野。

## 任务 3：W1-03 分支映射时自动补建项目级 version

- 目标：把“缺少项目级 version 时自动创建”的逻辑从前端下沉到后端 `set_branch()`，消除 `ProductProjectDetailPage` 的职责外兜底。
- 涉及文件：`src/service/services/product_version_service.py`、`src/service/repositories/version_repository.py`、相关测试文件
- 验证命令：`pytest tests/test_version_repository.py tests/test_api_versions.py -q`
- 推荐 commit message：`feat: auto create project version on branch mapping`
- 为什么现在做：当前前端已经在为这个缺口补锅，说明问题真实存在且影响主链路；同时这个任务边界清晰，只涉及分支映射和 version 查补，不必立刻进入 sync/graph 的高环境复杂度区域。

## 暂不进入前三的任务

- `W1-05` 虽然边界清晰，但在收益上排在 `W1-03` 之后；先把 branch -> version 的后端一致性补上，再新增按 branch 直查提交接口更顺。
- `W1-04` 会触达 `sync_service`、本地 repo、fetch、graph 等路径，环境不确定性更高，不适合作为当前第三个最小单元。
