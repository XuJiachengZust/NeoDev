---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-T012-T014-PLUGIN-SKILL-E2E
title: "NeoDev T012-T014 插件 / Skill / 端到端留痕"
aliases:
  - "NeoDev T012-T014 插件 / Skill / 端到端留痕"
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
# NeoDev T012-T014 插件 / Skill / 端到端留痕

日期：2026-04-27

## 背景

T001-T011 已经把 CLI、元数据、文档变更、图谱查询、Git 校验和推送后刷新打成最小闭环。本轮继续完成使用层交付：

- T012 官方插件实现
- T013 官方 skill 实现
- T014 联调验收与最小示例工程

## 设计取舍

插件和 skill 只作为引导层、编排层和解释层，不直接写业务状态。

真实执行边界继续保持在 CLI：

- 状态写入走 `doc change register`、`git verify-doc-change` 等 CLI。
- 图谱上下文走 `graph impact`、`graph semantic-search`、`graph entity-context`、`graph get-chain`。
- 推送后刷新走 `git post-push-refresh` 或 `graph refresh-nodes`。
- 插件和 skill 不直接写 PostgreSQL，不直接写 Neo4j。

## 本轮交付

### T012 官方插件

新增：

- `plugins/neodev-rd-knowledge/.codex-plugin/plugin.json`
- `.agents/plugins/marketplace.json`
- `plugins/neodev-rd-knowledge/workflows/core-workflows.json`

覆盖工作流：

- 会话启动版本检查
- 文档变更到实现上下文
- 分支分析触发和状态查看
- 推送前 `DocChange-ID` 校验
- 危险提交列表和关闭
- 推送后刷新

### T013 官方 skill

新增：

- `plugins/neodev-rd-knowledge/skills/neodev-rd-knowledge/SKILL.md`

skill 明确：

- 使用 `workflows/core-workflows.json` 作为共享命令顺序来源。
- 高风险或写操作前先执行 `cli version-check`。
- 所有真实动作使用 `python neodev.py ... --json`。
- 不直接写 PostgreSQL。
- 不直接写 Neo4j。

### T014 最小示例工程

新增：

- `examples/neodev-rd-knowledge/manifest.json`
- `examples/neodev-rd-knowledge/README.md`
- `examples/neodev-rd-knowledge/doc-repo/prd/NEODEV-DEMO-V1.md`
- `examples/neodev-rd-knowledge/doc-repo/prototype/.gitkeep`
- `examples/neodev-rd-knowledge/doc-repo/tech-design/NEODEV-DEMO-TECH.md`
- `examples/neodev-rd-knowledge/project-repo/src/demo_service.py`

示例覆盖：

- 一个产品：`NEODEV-DEMO`
- 一个版本：`V1.0`
- 一个文档仓库
- 两个分支场景：`main` 与 `feature/docchange-demo`
- 一条从版本检查、产品/版本/分支绑定、文档扫描、DocChange 登记、影响分析、提交校验到推送后刷新的演示链路

## CLI 版本契约补齐

更新：

- `src/service/cli/commands/cli.py`

`cli version-check` 现在从官方插件 manifest 和共享 workflow 文件读取：

- `plugin_version`
- `skill_version`
- `compatible`
- `target_version`

## 远程 PG 测试连接稳定性

更新：

- `tests/conftest.py`

原因：

- 长覆盖集在远程 PostgreSQL 上运行时，session 级 `pg_conn` 可能被服务端关闭。
- 旧实现把同一个 session 连接复用于多个测试，连接关闭后会导致后续 PG 测试连锁失败。

处理：

- 保留 session 级 `db_connection` 用于迁移初始化。
- `pg_conn` 改为每个测试创建短连接，用例结束后 rollback 并关闭。
- 这样与 CLI 命令的短连接模式保持一致，也避免长套件空闲连接被关闭。

## TDD 记录

红灯：

```powershell
pytest tests/test_official_plugin_skill.py -q
```

结果：失败，插件 manifest、workflow JSON、skill 文件不存在。

红灯：

```powershell
pytest tests/test_cli_contract.py::test_root_entrypoint_returns_version_check_json -q
```

结果：失败，`plugin_version` 仍为 `None`。

红灯：

```powershell
pytest tests/test_minimal_e2e_example.py -q
```

结果：失败，最小示例 manifest 与示例目录不存在。

绿灯：

```powershell
pytest tests/test_official_plugin_skill.py tests/test_cli_contract.py::test_root_entrypoint_returns_version_check_json -q
pytest tests/test_minimal_e2e_example.py -q
```

结果：

- `4 passed`
- `2 passed`

warning 为 `.pytest_cache` 写入权限问题，不影响功能验证。

最终远程 PG 覆盖集：

```powershell
pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py tests/test_doc_scan_service.py tests/test_doc_cli.py tests/test_doc_change_service_unit.py tests/test_branch_analysis_service_unit.py tests/test_branch_analysis_service.py tests/test_graph_semantic_search_service_unit.py tests/test_graph_impact_service_unit.py tests/test_graph_refresh_service_unit.py tests/test_graph_query_service_unit.py tests/test_graph_cli.py tests/test_commit_message_parser_unit.py tests/test_git_consistency_service_unit.py tests/test_git_cli.py tests/test_official_plugin_skill.py tests/test_minimal_e2e_example.py -q
```

结果：`118 passed, 1 warning`。

## 剩余增强

- T014 当前是可复现文档和示例骨架，尚未自动创建独立 Git 仓库并执行真实端到端提交/推送。
- `git verify-doc-change` 的危险分支自动创建 `DangerousCommitRecord` 仍是 T011 增强项。
- `git post-push-refresh` 的真实 commit 同步统计和链路刷新统计仍是后续增强项。
