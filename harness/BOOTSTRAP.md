# Harness Bootstrap

`harness` 的唯一强入口。

## 强制规则

- 禁止跳过本文件直接读取零散规则。
- 禁止一次性全量加载全部规则。
- 当前仓库是单项目后端仓库，不要套用多子项目聚合仓库心智。
- 多智能体闭环协作优先于 Git、参考源和环境类规则。

## 首批必读

1. `harness/system/master-prompt.md`
2. `harness/rules/development/agent-loop-rule.md`
3. 若任务涉及代码变更，再读 `harness/rules/development/code-cleanup-rule.md`
4. 若任务涉及创建子智能体、分派、验收或修复循环，再读 `harness/rules/development/subagent-delegation-rule.md`
5. `harness/rules/development/progressive-loading-rule.md`

## 后续按需读取

1. 先判断命中的代码域：`src/service`、`src/deepagents`、`src/gitnexus_parser`、`docker/`、根目录配置文件。
2. 再判断任务类型：开发执行、接口契约、环境/联调/部署、证据核查、Git 收口。
3. 命中字段新增、删除、改名、schema 调整、接口契约收口时，读取 `rules/development/cross-layer-contract-change-rule.md`。
4. 命中配置来源、字段归属、口径一致性时，读取 `rules/development/metadata-source-of-truth-rule.md`。
5. 命中 Git、沉淀、参考源或分析前的最小证据集判断时，读取 `rules/development/` 下对应文件，优先看 `reference-source-rule.md`。
6. 命中远程环境、Docker 联调、数据库校验或远端部署时，读取 `context/dev-environment.md`。
7. 需要导航或示例时，再读 `README.md` 与各目录索引。
8. 若准备调用 `spawn_agent` 创建子智能体，先确认 `agent-loop-rule.md` 与 `subagent-delegation-rule.md` 中关于 `agent_type`、`model`、`reasoning_effort`、`fork_context` 的要求。
