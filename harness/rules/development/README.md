# Development Rules Index

本目录用于放置 NeoDev 当前仓库共享的开发规范规则。

## 高优先级优先读取

- `agent-loop-rule.md`
  - 仓库级高优先级规则
  - 进入任何非简单只读任务前优先读取
  - 包含创建子智能体时必须显式填写的创建参数要求
- `code-cleanup-rule.md`
  - 代码变更任务的高优先级规则
  - 要求在新实现落地后及时清理旧代码、废弃代码和失效配套描述
- `subagent-delegation-rule.md`
  - 涉及任务拆解、创建子智能体、执行后验收、修复循环时紧接着读取
  - 包含分派模板、边界模板和创建参数模板
- `progressive-loading-rule.md`
  - 用于决定后续还要按需补读哪些规则

## 按主题查找

- 协作与闭环：
  - `agent-loop-rule.md`
  - `subagent-delegation-rule.md`
- 代码清理：
  - `code-cleanup-rule.md`
- 渐进加载：
  - `progressive-loading-rule.md`
- 契约变更：
  - `cross-layer-contract-change-rule.md`
- 元数据与口径归属：
  - `metadata-source-of-truth-rule.md`
- Git 规范：
  - `git-rule.md`
- harness 沉淀：
  - `harness-deposition-rule.md`
- 参考源使用：
  - `reference-source-rule.md`
