---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-GRAPH-QUERY-CLI-F002-CONTEXT-CHAIN
title: NeoDev F002 图谱查询 CLI 留痕：entity-context / get-chain
aliases:
- NeoDev F002 图谱查询 CLI 留痕：entity-context / get-chain
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

# NeoDev F002 图谱查询 CLI 留痕：entity-context / get-chain

## 背景

继续补 F002「图谱查询、版本语义检索与上下文供给」。上一轮已实现 `graph semantic-search` 的 ProductVersion 作用域检索。本轮补两个查询类入口：

- `graph entity-context`
- `graph get-chain`

这两个入口都只读图谱事实，不执行刷新或 AI 更新。

## 本次切片

本次实现最小可验收闭环：

- `graph entity-context`
  - 输入：ProductVersion 定位、project 定位、`--branch`、`--entity-id`、`--depth`
  - 校验：project 必须绑定在该 ProductVersion 下，branch 必须匹配绑定分支
  - 输出：实体、邻接节点、边、上下文摘要、降级原因
- `graph get-chain`
  - 输入：ProductVersion 定位、project 定位、`--branch`
  - 起点定位：`--start-node`、`--file-path`、`--symbol`、`--commit-sha` 四选一
  - 校验：起点定位必须且只能提供一个
  - 输出：`start_node/snapshot_id/branch/head_commit/depth/nodes/edges/path_summary/affected_commits`
- Neo4j 未配置时，返回空结构和 `degraded_reasons`，不让 CLI 崩溃。
- Neo4j 查询返回节点/边时，服务层统一格式化为插件和 skill 可消费的结构化 JSON。

## 代码变更

- `src/service/cli/commands/graph.py`
  - 注册 `entity-context`
  - 注册 `get-chain`
  - 新增 project 定位参数与解析
  - 接入 `GraphQueryError -> CliError`
- `src/service/services/graph_query_service.py`
  - 新增 ProductVersion/project/branch 作用域校验
  - 新增 `entity_context`
  - 新增 `get_chain`
  - 新增 depth、起点定位边界校验
  - 新增节点/边规范化与路径摘要生成
- `tests/test_cli_contract.py`
  - 覆盖两个新命令的 help 注册和关键参数
- `tests/test_graph_query_service_unit.py`
  - 覆盖实体上下文、链路查询、起点定位边界、分支越界
- `tests/test_graph_cli.py`
  - 覆盖 PG-backed CLI 边界：分支越界、多起点定位

## 红灯记录

先写测试后实现：

```text
pytest tests/test_cli_contract.py::test_graph_entity_context_command_is_registered tests/test_cli_contract.py::test_graph_get_chain_command_is_registered tests/test_graph_query_service_unit.py -q
```

初始结果：

```text
6 failed
- invalid choice: 'entity-context'
- invalid choice: 'get-chain'
- ImportError: cannot import name 'graph_query_service'
```

含义：

- CLI 尚未注册 `entity-context/get-chain`。
- 服务层尚未提供图谱查询服务。

实现后遇到一次真实测试失败：

```text
UnboundLocalError / NameError: cannot access local variable 'source'
```

根因：Python f-string 将 Cypher map 字面量 `{source: ...}` 当成插值表达式。修复为转义 Cypher map 花括号。

## 验证

新增查询单元测试：

```text
pytest tests/test_graph_query_service_unit.py -q
```

结果：

```text
4 passed, 1 warning
```

远程 PG graph 相关测试：

```text
TEST_DATABASE_URL=<remote-pg> pytest tests/test_graph_cli.py tests/test_graph_query_service_unit.py tests/test_graph_semantic_search_service_unit.py tests/test_cli_contract.py -q
```

结果：

```text
31 passed, 1 warning
```

远程 PG T001 到当前 F002 覆盖集：

```text
TEST_DATABASE_URL=<remote-pg> pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py tests/test_doc_scan_service.py tests/test_doc_cli.py tests/test_doc_change_service_unit.py tests/test_branch_analysis_service_unit.py tests/test_branch_analysis_service.py tests/test_graph_semantic_search_service_unit.py tests/test_graph_query_service_unit.py tests/test_graph_cli.py -q
```

结果：

```text
80 passed, 1 warning
```

warning 仍是 `.pytest_cache` 写入权限问题，不影响功能验证。

## 当前 F002 状态

已实现：

- `graph semantic-search`
- `graph entity-context`
- `graph get-chain`

仍待补：

- `graph impact`
- `graph refresh-nodes`

其中 `graph refresh-nodes` 会触达节点刷新、AI 描述和 embedding 复用/重算，建议作为下一个独立切片处理。

## 关联文档
- [[neosuperpower/specs/2026-04-24-neodev-cli-and-metadata-foundation-design|NeoDev CLI 与元数据基础设计]]
