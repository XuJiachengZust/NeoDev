---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-GRAPH-SEMANTIC-SEARCH-CLI-T007
title: "NeoDev T007 图谱语义检索 CLI 留痕"
aliases:
  - "NeoDev T007 图谱语义检索 CLI 留痕"
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
# NeoDev T007 图谱语义检索 CLI 留痕

## 背景

本次继续推进研发知识图谱 MVP 的 `T007 Product Version Semantic Retrieval`。

T001-T006 已经提供 CLI 壳层、元数据基础、产品版本绑定、文档扫描、DocChange 生命周期和分支分析编排。T007 的目标是在 ProductVersion 作用域内提供 `graph semantic-search`，让插件、skill 和本地 Agent 可以通过 CLI 获取结构化的版本级语义检索结果。

## 本次切片

本次实现最小可验收闭环：

- 新增 `graph semantic-search` 顶层 CLI。
- 支持通过 `--version-id` 或 `--product-code/--version-name` 定位 ProductVersion。
- 支持 `--query` 和 `--top-k`。
- 检索作用域只来自 `product_version_branches` 绑定的项目分支。
- 返回结构化 JSON：
  - `product_version_id`
  - `query`
  - `top_k`
  - `scope`
  - `semantic_status`
  - `results`
  - `degraded_reasons`
- 当 embedding 不可用时，降级为 Neo4j 文本检索，并将结果标记为 `degraded` 或 `not_vectorized`。
- 当版本没有绑定分支时，返回结构化 `invalid_scope`，避免无边界搜索。

## 代码变更

- `src/service/cli/commands/graph.py`
  - 新增 graph 命令组。
  - 新增 `semantic-search` 子命令。
  - 复用统一 CLI JSON 输出和错误模型。
- `src/service/cli/commands/__init__.py`
  - 注册 graph 命令组。
- `src/service/services/graph_semantic_search_service.py`
  - 新增 ProductVersion 作用域校验。
  - 新增 query/top_k 参数校验。
  - 新增 Neo4j 向量检索与文本降级检索。
  - 新增结构化结果格式化。
- `tests/test_cli_contract.py`
  - 覆盖 `graph semantic-search --help` 注册。
- `tests/test_graph_semantic_search_service_unit.py`
  - 覆盖版本分支作用域、embedding 降级、无绑定分支、参数边界。
- `tests/test_graph_cli.py`
  - 覆盖 PG-backed CLI 边界：ProductVersion 存在但无绑定分支时返回 `invalid_scope`。

## 红灯记录

先写测试后实现：

```text
pytest tests/test_cli_contract.py::test_graph_semantic_search_command_is_registered tests/test_graph_semantic_search_service_unit.py -q
```

初始结果：

```text
4 failed
- invalid choice: 'graph'
- ImportError: cannot import name 'graph_semantic_search_service'
```

含义：

- CLI 尚未注册 `graph` 顶层命令。
- 服务层尚未提供 `graph_semantic_search_service`。

## 边界行为

- `query` 为空：`invalid_argument`
- `top_k < 1` 或 `top_k > 50`：`invalid_argument`
- ProductVersion 不存在：`not_found`
- ProductVersion 未绑定任何项目分支：`invalid_scope`
- embedding 不可用：不让 CLI 失败，降级文本检索并返回 `semantic_status=degraded/not_vectorized`
- Neo4j 未配置或查询失败：返回空结果和 `degraded_reasons`

## 验证

新增测试：

```text
pytest tests/test_cli_contract.py::test_graph_semantic_search_command_is_registered tests/test_graph_semantic_search_service_unit.py -q
```

结果：

```text
4 passed, 1 warning
```

相关命令契约和服务单测：

```text
pytest tests/test_cli_contract.py tests/test_graph_semantic_search_service_unit.py tests/test_branch_analysis_service_unit.py -q
```

结果：

```text
26 passed, 1 warning
```

远程 PG 上新增 graph 相关测试：

```text
TEST_DATABASE_URL=<remote-pg> pytest tests/test_graph_cli.py tests/test_cli_contract.py tests/test_graph_semantic_search_service_unit.py -q
```

结果：

```text
23 passed, 1 warning
```

远程 PG 上 T001-T007 当前覆盖集：

```text
TEST_DATABASE_URL=<remote-pg> pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py tests/test_doc_scan_service.py tests/test_doc_cli.py tests/test_doc_change_service_unit.py tests/test_branch_analysis_service_unit.py tests/test_branch_analysis_service.py tests/test_graph_semantic_search_service_unit.py tests/test_graph_cli.py -q
```

结果：

```text
72 passed, 1 warning
```

warning 仍是 `.pytest_cache` 写入权限问题，不影响功能验证。

## 后续

T007 当前是 CLI 最小闭环：能按 ProductVersion 限定范围，并在语义能力不可用时结构化降级。

后续深化项：

- 将 `graph impact`、`graph entity-context`、`graph refresh-nodes`、`graph get-chain` 纳入 F002 完整闭环。
- 补齐真实 Neo4j 向量索引环境下的端到端语义命中验收。
- 将 T008 的 AI 语义增强和 T007 检索结果质量联动验证。
