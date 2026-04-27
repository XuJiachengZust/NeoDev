# 渐进加载 Rule

目标：只加载当前任务真正需要的上下文。

## 补读触发

- 单项目实现：优先锁定当前命中的代码域，再决定是否继续补读规则
- 命中 `src/service/routers`、`src/service/services`、`src/service/repositories` 之间的接口、字段、状态流转变化：读 `cross-layer-contract-change-rule.md`
- 命中根目录配置、`.env*`、`docker-compose.yml`、`Dockerfile`、`src/config.example.json` 的来源归属：读 `metadata-source-of-truth-rule.md`
- 字段新增、删除、改名、schema 调整、接口契约收口：读 `cross-layer-contract-change-rule.md`
- 资源类型名称、字段展示、过滤口径、资格约束或别名归属判断：读 `metadata-source-of-truth-rule.md`
- Git、沉淀、参考源、最小证据集判断：再读 `git-rule.md`、`harness-deposition-rule.md`、`reference-source-rule.md`
- 远程环境、数据库校验、联调验证、远端部署：读 `context/dev-environment.md`

## 禁止事项

- 不因“可能有用”全量读取全部规则
- 不跳过 `BOOTSTRAP.md`
- 不在多智能体执行/验收任务中遗漏 `agent-loop-rule.md` 或 `subagent-delegation-rule.md`
