---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-POST-PUSH-REFRESH-CLI-F003
title: "NeoDev F003 推送后刷新 CLI 留痕"
aliases:
  - "NeoDev F003 推送后刷新 CLI 留痕"
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
# NeoDev F003 推送后刷新 CLI 留痕

## 背景

继续补 F003「Git 一致性、危险提交与推送后刷新」。此前已经完成：

- `git verify-doc-change`
- `git dangerous-commit list`
- `git dangerous-commit resolve`

本轮补推送后刷新入口：

- `git post-push-refresh`

## 目标

为插件、skill 和本地 Agent 提供推送成功后的统一刷新入口。MVP 最小闭环是：

- 输入 `project_id + branch`
- 可选输入 `product_version_id`
- 可选输入 `commit_sha`
- 自动解析绑定到该 project/branch 的 ProductVersion
- 调用 `graph_refresh_service.refresh_nodes`
- 输出结构化刷新统计

## 设计取舍

当前已有 `sync_service.sync_commits_for_version`，但该能力会触发 Git 同步和图谱 pipeline，范围较重。F003 的 `post-push-refresh` 应优先面向“推送后局部刷新”，因此本轮不默认触发全量同步。

本轮行为：

- 未传 `--version-id` 时，根据 `product_version_branches(project_id, branch)` 自动定位唯一 ProductVersion。
- 未找到绑定返回 `not_found`。
- 多个 ProductVersion 绑定同一 project/branch 时返回 `conflict`。
- 传 `--version-id` 时校验该版本确实绑定了 project/branch。
- `commit_sha` 透传给 `graph refresh-nodes`，作为局部刷新范围。
- 输出 `commits_synced=0` 和 `chains_updated=0`，保留字段契约，后续接入真实 sync/chain 更新统计。

## TDD 记录

红灯：

```powershell
pytest tests/test_cli_contract.py::test_git_post_push_refresh_command_is_registered tests/test_git_consistency_service_unit.py::test_post_push_refresh_delegates_to_graph_refresh tests/test_git_consistency_service_unit.py::test_post_push_refresh_rejects_unbound_project_branch tests/test_git_cli.py::test_git_post_push_refresh_returns_degraded_without_neo4j -q
```

失败点：

- `git post-push-refresh` 未注册。
- `post_push_refresh` service 方法不存在。
- ProductVersion 绑定解析方法不存在。

实现文件：

- `src/service/services/git_consistency_service.py`
- `src/service/cli/commands/git.py`

测试文件：

- `tests/test_cli_contract.py`
- `tests/test_git_consistency_service_unit.py`
- `tests/test_git_cli.py`

## 验证

本地最小集：

```powershell
pytest tests/test_cli_contract.py::test_git_post_push_refresh_command_is_registered tests/test_git_consistency_service_unit.py::test_post_push_refresh_delegates_to_graph_refresh tests/test_git_consistency_service_unit.py::test_post_push_refresh_rejects_unbound_project_branch tests/test_git_cli.py::test_git_post_push_refresh_returns_degraded_without_neo4j -q
```

结果：

- `3 passed, 1 skipped`
- 本地 PG 不可用时 PG CLI 用例跳过。

远程 PG git 相关：

```powershell
pytest tests/test_git_consistency_service_unit.py tests/test_git_cli.py -q
```

结果：

- `13 passed`

远程 PG T001 到当前 F003 覆盖集：

```powershell
pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py tests/test_doc_scan_service.py tests/test_doc_cli.py tests/test_doc_change_service_unit.py tests/test_branch_analysis_service_unit.py tests/test_branch_analysis_service.py tests/test_graph_semantic_search_service_unit.py tests/test_graph_impact_service_unit.py tests/test_graph_refresh_service_unit.py tests/test_graph_query_service_unit.py tests/test_graph_cli.py tests/test_commit_message_parser_unit.py tests/test_git_consistency_service_unit.py tests/test_git_cli.py -q
```

结果：

- `113 passed`

## 当前 F003 状态

已完成：

- `git verify-doc-change`
- `git dangerous-commit list`
- `git dangerous-commit resolve`
- `git post-push-refresh`

待增强：

- 从 `verify-doc-change` 的风险分支自动创建 `DangerousCommitRecord`
- 将 `post-push-refresh` 接入真实 commit 同步统计
- 将 `chains_updated` 与后续链路刷新/缓存失效能力打通
- 将 AI 局部刷新统计接入 `graph_refresh_service`

