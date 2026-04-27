---
name: neodev-rd-knowledge
description: 用于 NeoDev 研发知识工作流，包括 DocChange 登记、图谱影响面和上下文查询、产品版本分支分析、Git 推送前校验、危险提交处理、推送后刷新；所有真实动作都必须通过 NeoDev CLI 执行。
---

# NeoDev 研发知识

使用本 skill 引导 NeoDev 研发知识图谱和 Git 一致性流程。它只负责编排和解释；所有真实动作都必须通过 `python neodev.py ... --json` 执行。

## 必守边界

- 写操作或风险敏感流程开始前，先执行 `cli version-check`。
- 不解析人类可读输出；必须请求 `--json` 并读取结构化 payload。
- 不在 prompt、脚本或插件中自建额外状态机。
- 不要直接写 PostgreSQL。
- 不要直接写 Neo4j。
- 不要用临时 SQL、图查询或持久化脚本替代 NeoDev CLI。

## 工作流来源

规范命令顺序放在本插件的 `workflows/core-workflows.json`。需要精确步骤名、命令模板或插件/skill 共享流程时，读取该文件。

## 主流程

### 文档变更到实现

1. 执行 `cli version-check`。
2. 用 `doc change register` 登记受控变更。
3. 用 `graph impact` 查询影响面。
4. 需要更多上下文时，再使用 `graph semantic-search`、`graph entity-context` 和 `graph get-chain`。
5. 只基于 CLI 返回的事实规划代码修改；没有证据时不要虚构受影响文件。

### 分支分析

1. 执行 `cli version-check`。
2. 用 `product version analyze` 触发分析。
3. 用 `product version analyze-status` 查看进度。
4. `product version watch-status` 只作为单次状态读取；重复轮询由外层编排控制节奏。

### 推送前校验

1. 检查 commit message 是否只包含一个 `DocChange-ID`。
2. 执行 `git verify-doc-change`。
3. 如果 CLI 返回风险，先解释风险并要求用户明确确认，再继续高风险动作。
4. 用 `git dangerous-commit list` 查看待处理风险项。

### 推送后刷新

1. 推送成功后执行 `git post-push-refresh`。
2. 需要更小或更明确范围时，使用 `graph refresh-nodes`。
3. 需要追踪后续依赖或影响链时，使用 `graph get-chain`。

## 结果解释

- `ok=false` 默认视为阻断，除非用户明确选择安全替代路径。
- `version_mismatch` 是高风险写流程的停止条件。
- `semantic_status=degraded` 表示图谱或 embedding 能力降级，不等同于命令失败。
- 给用户的解释必须绑定 CLI payload 中的具体字段。

## Cross-Client Contract

- Codex, Claude Code, and Cursor entries are adapters over the same shared scripts, template, and workflow contract.
- Validate MVP documents with `validate_mvp_docs.py` before `doc scan` or `doc change register`.
- Validate repository docs with `validate_obsidian_docs.py` when changing `docs/**/*.md`.
- Generate controlled docs with `generate_mvp_doc.py`; the generator writes the file and immediately runs the validator.
- Validate commit messages with `check_docchange_trailer.py` before Git commit verification.

MVP front matter:

```yaml
doc_id: DOC-001
title: Document Title
aliases:
  - Document Title
tags:
  - neodev/docs
created: 2026-04-27
updated: 2026-04-27
doc_type: prd
product_key: PRODUCT
status: draft
relations:
  target:
    - TARGET-DOC-001
related:
  - "[[TARGET-DOC-001]]"
```

Extra fields are allowed. `doc_type` must be `prd`, `prototype`, or `tech-design`; `status` must be `draft`, `active`, or `deprecated`; `relations.target` must be a non-empty list of non-empty strings. Obsidian properties are required for repository docs: `aliases`, `tags`, and `related` are non-empty lists; `created` and `updated` use `YYYY-MM-DD`; `related` should use wiki links.

## Superpowers Workflow

- Requirements or design: `superpowers:brainstorming`.
- Implementation: `superpowers:test-driven-development`.
- Failure investigation: `superpowers:systematic-debugging`.
- Completion, commit, or push: `superpowers:verification-before-completion`.
