# NeoDev Codex Harness

这是 NeoDev 项目的 **Codex 开发治理外挂层**。

它的职责不是成为 NeoDev 的产品 runtime，也不是对最终用户暴露的功能模块；它服务于开发阶段，用来约束 Codex / 子智能体如何理解任务、如何加载上下文、如何分派、如何审查与如何沉淀产物。

## 定位

- **主项目负责**：NeoDev 产品 runtime、业务逻辑、API、前端、deepagents 等产品能力
- **codex-harness 负责**：开发期 bootstrap、渐进加载、任务 contract、委派 contract、review contract、artifact ledger、经验沉淀

一句话：

> 这是治理 Codex 的开发外挂，不是 NeoDev 产品能力。

## 推荐使用顺序

1. 先读 `BOOTSTRAP.md`
2. 再读 `system/master-prompt.md`
3. 按任务类型读取 `rules/`（命名与 ledger 收敛建议见 `rules/naming-and-ledger-conventions.md`）
4. 需要启动任务时先复制 `contracts/task-contract.template.md`
5. 委派子任务时使用 `contracts/delegation-contract.template.md`
6. 交付前使用 `contracts/review-contract.template.md`
7. 所有重要任务都要在 `ledger/LEDGER.json` 中留痕

## 目录

- `BOOTSTRAP.md`：Codex 启动时先读的强入口
- `system/master-prompt.md`：仓库级治理原则
- `rules/`：渐进加载、主循环、委派、沉淀等规则
- `contracts/`：任务、委派、审查模板
- `tasks/`：具体任务工作区
- `artifacts/`：报告、审查、可交付物
- `ledger/`：执行账本
- `memory/`：沉淀的稳定经验
- `templates/`：后续可扩展模板

## 现成样例

先看 `tasks/README.md`，再进入具体样例目录。

- `tasks/TASK-2026-04-08-HARNESS-CLOSED-LOOP-EXAMPLE/`：单任务闭环样例（task contract → review → ledger）
- `tasks/TASK-2026-04-08-HARNESS-DELEGATION-EXAMPLE/`：delegation 协作样例（父任务 → delegation contract → 子任务回收 → 最终 review → ledger）
- `tasks/TASK-2026-04-08-HARNESS-DUAL-DELEGATION-EXAMPLE/`：更强的双子任务样例（父任务 → 两个不同子任务 contract → 父任务回收/对账/验收 → 最终 review → ledger）

## 约束

- 默认 **不提交** 这套外挂层，除非老大明确要求
- 只沉淀长期稳定的规则与经验，不堆积一次性对话垃圾
- 所有非极小任务默认要有 contract 和 review

## ledger 引用校验（最小脚本）

用于快速检查 `ledger/LEDGER.json` 里声明的 `artifacts` / `review` 路径是否真实存在。

运行方式：

```bash
python scripts/validate_ledger_paths.py
```

说明：

- 脚本只做**存在性校验**，不改 ledger，不碰 NeoDev 主产品 runtime
- 相对路径按 NeoDev 仓库根目录解析，因此既支持 `codex-harness/...`，也支持 `web/...` 这类主仓库路径
- 返回码约定：
  - `0`：全部存在
  - `1`：存在缺失引用
  - `2`：ledger 文件缺失或 JSON 结构非法

最小示例：

- `artifacts`: `"codex-harness/tasks/TASK-2026-04-06-REQ-DOC-REDESIGN.md"`
- `review`: `"codex-harness/artifacts/reviews/TASK-2026-04-06-REQ-DOC-REDESIGN-review.md"`
