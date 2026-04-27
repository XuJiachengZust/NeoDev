# Harness Engineering

根入口：`harness/BOOTSTRAP.md`

## 目录

- `system/`：仓库级默认原则
- `rules/development/`：跨项目开发规范
- `context/`：环境、联调、部署上下文
- `examples/`：规则与分派示例

## 快速定位

- 默认协作方式：`system/master-prompt.md`
- 多智能体闭环与创建参数：`rules/development/agent-loop-rule.md`
- 子智能体分派与边界模板：`rules/development/subagent-delegation-rule.md`
- 渐进加载：`rules/development/progressive-loading-rule.md`
- 跨层契约变更：`rules/development/cross-layer-contract-change-rule.md`
- 元数据事实来源：`rules/development/metadata-source-of-truth-rule.md`
- 证据优先分析：`rules/development/reference-source-rule.md`
- 环境与部署：`context/README.md`
- 示例入口：`examples/README.md`

调用 `spawn_agent` 前，先回看多智能体两份规则，显式确定 `agent_type`、`model`、`reasoning_effort`、`fork_context` 和分派边界。
