---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-GRAPH-IMPACT-CLI-F002
title: "NeoDev F002 图谱影响面 CLI 留痕"
aliases:
  - "NeoDev F002 图谱影响面 CLI 留痕"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/plan
created: 2026-04-27
updated: 2026-04-27
doc_type: tech-design
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-SUPERPOWERS-SPECS-2026-04-24-NEODEV-CLI-AND-METADATA-FOUNDATION-DESIGN
related:
  - "[[2026-04-24-neodev-cli-and-metadata-foundation-design]]"
---
# NeoDev F002 图谱影响面 CLI 留痕

## 背景

继续补 F002「图谱查询、版本语义检索与上下文供给」。此前已经完成：

- `graph semantic-search`
- `graph entity-context`
- `graph get-chain`

本轮补齐 DocChange 影响范围入口：

- `graph impact`

## 目标

让插件、skill 和本地 Agent 可以基于 `DocChange` 获取结构化候选影响范围，输出字段对齐 F002 PRD 和 CLI 契约：

- `doc_change_id`
- `document_summary`
- `affected_repositories`
- `affected_modules`
- `affected_files`
- `affected_symbols`
- `evidence`
- `confidence`
- `risk_points`
- `suggested_steps`

## 设计取舍

本轮做最小闭环，不把影响范围强行推断为最终事实：

- `details_json` 中的 `affected_*` 作为显式声明。
- `documents.relations_json` 中的 `modules/files/symbols/relations` 作为文档关系证据。
- `documents.front_matter_json` 中的 repository、module、relations 等作为补充证据。
- `component` 只作为 front matter 证据保留，不自动扩大为 `affected_modules`。
- 找不到 DocChange 或 document 时返回明确错误。

## TDD 记录

红灯：

```powershell
pytest tests/test_cli_contract.py::test_graph_impact_command_is_registered tests/test_graph_impact_service_unit.py tests/test_graph_cli.py::test_graph_impact_rejects_unknown_doc_change -q
```

失败点：

- `graph impact` 未注册。
- `service.services.graph_impact_service` 不存在。

实现：

- 新增 `src/service/services/graph_impact_service.py`
- 更新 `src/service/cli/commands/graph.py`
- 更新 `tests/test_cli_contract.py`
- 更新 `tests/test_graph_impact_service_unit.py`
- 更新 `tests/test_graph_cli.py`

调试记录：

- 初次实现把 front matter `component` 当成 `affected_modules`，导致影响范围过宽。
- 修正为只从显式 `affected_modules`、relations `modules`、front matter `module/modules` 生成模块候选。
- `component` 保留在 `document.front_matter` evidence 中。

## 验证

本地非 PG：

```powershell
pytest tests/test_cli_contract.py tests/test_graph_impact_service_unit.py -q
```

结果：

- `26 passed`
- `.pytest_cache` 权限 warning 不影响结果。

远程 PG graph 相关：

```powershell
pytest tests/test_graph_impact_service_unit.py tests/test_graph_cli.py -q
```

结果：

- `9 passed`

远程 PG T001 到当前 F002 覆盖集：

```powershell
pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py tests/test_doc_scan_service.py tests/test_doc_cli.py tests/test_doc_change_service_unit.py tests/test_branch_analysis_service_unit.py tests/test_branch_analysis_service.py tests/test_graph_semantic_search_service_unit.py tests/test_graph_impact_service_unit.py tests/test_graph_query_service_unit.py tests/test_graph_cli.py -q
```

结果：

- `87 passed`

## 当前 F002 状态

已完成：

- `graph semantic-search`
- `graph impact`
- `graph entity-context`
- `graph get-chain`

待补：

- `graph refresh-nodes`

