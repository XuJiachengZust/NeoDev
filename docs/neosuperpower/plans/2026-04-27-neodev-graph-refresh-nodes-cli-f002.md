---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-GRAPH-REFRESH-NODES-CLI-F002
title: NeoDev F002 图谱节点刷新 CLI 留痕
aliases:
- NeoDev F002 图谱节点刷新 CLI 留痕
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
- '[[neosuperpower/specs/2026-04-24-neodev-cli-and-metadata-foundation-design|NeoDev
  CLI 与元数据基础设计]]'
---

# NeoDev F002 图谱节点刷新 CLI 留痕

## 背景

继续补 F002 最后一个 CLI 入口：

- `graph refresh-nodes`

至此 F002 的 5 个图谱命令均进入 CLI：

- `graph impact`
- `graph entity-context`
- `graph semantic-search`
- `graph refresh-nodes`
- `graph get-chain`

## 目标

为插件、skill 和本地 Agent 提供一个可控的节点刷新入口，支持按以下范围定位：

- `ProductVersion`
- `project`
- `branch`
- `node_id`
- `path`
- `commit_sha`

输出字段对齐 F002 PRD 和 CLI 契约：

- `refresh_scope`
- `graph_nodes_updated`
- `ai_descriptions_updated`
- `embeddings_reused`
- `embeddings_regenerated`
- `status`

本轮额外返回：

- `semantic_status`
- `degraded_reasons`

用于明确 Neo4j 或语义刷新不可用时的降级状态。

## 设计取舍

`graph refresh-nodes` 是有副作用命令。当前已有 `ai_analysis_runner` 支持整分支 AI description / embedding 生成，但它不是稳定的局部刷新 API。为了避免 CLI 默认触发不可控全量 AI 重跑，本轮采用最小可控闭环：

- 复用现有 ProductVersion -> project/branch 作用域校验。
- 参数先校验，再访问数据库，保证空 path/node_id 等输入返回 `invalid_argument`。
- 未配置 Neo4j 时返回 `status=degraded`、`semantic_status=not_refreshed`。
- 配置 Neo4j 时，只对命中节点标记 `semanticStatus=refresh_requested` 和 `refreshRequestedAt`，并返回 `graph_nodes_updated`。
- `ai_descriptions_updated/embeddings_reused/embeddings_regenerated` 暂为 0，后续在局部 AI 刷新执行层稳定后接入真实统计。

这个实现让 CLI 合约、作用域控制、降级语义和节点刷新意图先稳定下来，避免把全量预处理能力误暴露成局部刷新能力。

## TDD 记录

红灯：

```powershell
pytest tests/test_cli_contract.py::test_graph_refresh_nodes_command_is_registered tests/test_graph_refresh_service_unit.py tests/test_graph_cli.py::test_graph_refresh_nodes_rejects_branch_outside_product_version -q
```

失败点：

- `graph refresh-nodes` 未注册。
- `service.services.graph_refresh_service` 不存在。

实现：

- 新增 `src/service/services/graph_refresh_service.py`
- 更新 `src/service/cli/commands/graph.py`
- 更新 `tests/test_cli_contract.py`
- 新增 `tests/test_graph_refresh_service_unit.py`
- 更新 `tests/test_graph_cli.py`

调试记录：

- 初次实现先做 DB 作用域校验，再校验 path，导致空 path 测试触发 fake connection 的 `AttributeError`。
- 修正为先规范化 `node_ids/paths/commit_sha`，再校验 ProductVersion 作用域。

## 验证

本地：

```powershell
pytest tests/test_graph_refresh_service_unit.py tests/test_cli_contract.py::test_graph_refresh_nodes_command_is_registered -q
```

结果：

- `4 passed`
- `.pytest_cache` 权限 warning 不影响结果。

远程 PG refresh-nodes 相关：

```powershell
pytest tests/test_graph_refresh_service_unit.py tests/test_graph_cli.py::test_graph_refresh_nodes_rejects_branch_outside_product_version tests/test_graph_cli.py::test_graph_refresh_nodes_returns_degraded_without_neo4j -q
```

结果：

- `5 passed`

远程 PG T001 到完整 F002 覆盖集：

```powershell
pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py tests/test_doc_scan_service.py tests/test_doc_cli.py tests/test_doc_change_service_unit.py tests/test_branch_analysis_service_unit.py tests/test_branch_analysis_service.py tests/test_graph_semantic_search_service_unit.py tests/test_graph_impact_service_unit.py tests/test_graph_refresh_service_unit.py tests/test_graph_query_service_unit.py tests/test_graph_cli.py -q
```

结果：

- `93 passed`

## 当前 F002 状态

已完成：

- `graph impact`
- `graph entity-context`
- `graph semantic-search`
- `graph refresh-nodes`
- `graph get-chain`

后续增强建议：

- 把 `ai_analysis_runner` 拆出局部节点刷新执行层。
- 将 `refresh_requested` 节点接入真实 description / embedding 生成。
- 将 `embeddings_reused` 和 `embeddings_regenerated` 与 `content_hash` 缓存统计打通。

## 关联文档
- [[neosuperpower/specs/2026-04-24-neodev-cli-and-metadata-foundation-design|NeoDev CLI 与元数据基础设计]]
