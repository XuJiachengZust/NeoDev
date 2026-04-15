# BOOTSTRAP.md

你正在 NeoDev 项目中工作，但你当前加载的是 **codex-harness** —— 这是一个开发期治理外挂层，不是 NeoDev 产品 runtime。

在开始执行前，先确认以下事实：

1. 你的目标是帮助 NeoDev 开发，而不是发明新的产品方向。
2. 你应优先遵守仓库根目录 `AGENTS.md` 的约束。
3. 这套 harness 负责治理：
   - 任务理解
   - 渐进加载
   - 子任务分派
   - 审查验收
   - 产物沉淀
4. 这套 harness 默认是 **本地开发资产**，不自动进入正式提交。
5. 非极小任务默认必须补齐：
   - task contract
   - review contract
   - ledger 记录

## 启动步骤

1. 读取仓库根 `AGENTS.md`
2. 读取 `codex-harness/system/master-prompt.md`
3. 根据当前任务选择性读取 `codex-harness/rules/*.md`
4. 若任务超过一次性小修，先创建/填写 task contract
5. 若需要委派，先写 delegation contract 再发子任务
6. 产出完成后，写 review contract 并更新 ledger

## 关键边界

- 不要把 codex-harness 当成 NeoDev 产品功能
- 不要把一次性聊天垃圾写进 harness
- 不要跳过验收直接宣称完成
- 不要在未获允许时把外挂层内容提交进仓库
