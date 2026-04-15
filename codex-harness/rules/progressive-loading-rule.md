# Progressive Loading Rule

## 目标

避免把整个 harness 全量灌入上下文，只加载当前任务真正需要的部分。

## 默认加载顺序

1. 仓库根 `AGENTS.md`
2. `codex-harness/BOOTSTRAP.md`
3. `codex-harness/system/master-prompt.md`
4. 当前任务命中的规则文件
5. 当前任务的 contract / review / ledger 相关文件

## 选择规则

- 纯实现小任务：只需 bootstrap + master prompt + 任务相关 contract
- 需要委派：额外加载 delegation rule
- 需要沉淀经验：额外加载 deposition rule
- 需要正式验收：额外加载 review rule

## 禁止事项

- 不要无差别加载全部规则
- 不要把历史任务垃圾一并塞进当前上下文
- 不要因为“怕漏掉”而全量灌 prompt
