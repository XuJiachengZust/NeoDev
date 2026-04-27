# NeoDev F003 Dangerous Commit CLI 留痕

## 背景

继续补 F003「Git 一致性、危险提交与推送后刷新」。上一轮已经完成：

- `git verify-doc-change`
- `DocChange-ID` trailer 解析
- `CodeChangeLink` 创建
- `DocChange -> in_implementation`

本轮补危险提交待处理与关闭入口：

- `git dangerous-commit list`
- `git dangerous-commit resolve`

## 目标

把危险提交从一次性提示变成可查询、可关闭、可审计的 CLI 能力。

本轮实现：

- 查询 open 状态危险提交。
- 支持按 `project_id` 过滤。
- 关闭危险提交记录。
- 记录 `resolved_by` 和 `resolved_at`。
- 未找到记录时返回 `not_found`。

## TDD 记录

红灯：

```powershell
pytest tests/test_cli_contract.py::test_git_dangerous_commit_commands_are_registered tests/test_git_consistency_service_unit.py::test_list_dangerous_commits_returns_open_records tests/test_git_consistency_service_unit.py::test_resolve_dangerous_commit_returns_resolved_record tests/test_git_consistency_service_unit.py::test_resolve_dangerous_commit_rejects_unknown_record tests/test_git_cli.py::test_git_dangerous_commit_resolve_rejects_unknown_record -q
```

失败点：

- `git dangerous-commit` 子命令未注册。
- `git_consistency_service` 未暴露 dangerous commit repository / list / resolve 能力。

实现文件：

- `src/service/services/git_consistency_service.py`
- `src/service/cli/commands/git.py`

测试文件：

- `tests/test_cli_contract.py`
- `tests/test_git_consistency_service_unit.py`
- `tests/test_git_cli.py`

## 调试记录

完整远程 PG 覆盖集第一次跑到末尾 `test_git_cli` 时，session 级 `pg_conn` 被服务端关闭：

- `server closed the connection unexpectedly`
- 后续表现为同一个 `pg_conn` `connection already closed`

小范围复跑 git CLI 测试可以通过，说明不是业务代码稳定失败，而是长套件末尾复用 session 连接时触发远程 PG 空闲连接关闭。

修正：

- `tests/test_git_cli.py` 的成功路径改为测试内短连接。
- `pg_conn` 仍用于触发 pytest 的 PG 可用性检查和迁移准备。
- 具体落库/查询用 `_connect_fresh()`，避免长时间复用空闲连接。

## 验证

远程 PG dangerous commit 相关：

```powershell
pytest tests/test_git_consistency_service_unit.py tests/test_git_cli.py::test_git_dangerous_commit_list_and_resolve tests/test_git_cli.py::test_git_dangerous_commit_resolve_rejects_unknown_record -q
```

结果：

- `8 passed`

远程 PG git CLI：

```powershell
pytest tests/test_git_cli.py -q
```

结果：

- `4 passed`

远程 PG T001 到当前 F003 覆盖集：

```powershell
pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py tests/test_doc_scan_service.py tests/test_doc_cli.py tests/test_doc_change_service_unit.py tests/test_branch_analysis_service_unit.py tests/test_branch_analysis_service.py tests/test_graph_semantic_search_service_unit.py tests/test_graph_impact_service_unit.py tests/test_graph_refresh_service_unit.py tests/test_graph_query_service_unit.py tests/test_graph_cli.py tests/test_commit_message_parser_unit.py tests/test_git_consistency_service_unit.py tests/test_git_cli.py -q
```

结果：

- `109 passed`

## 当前 F003 状态

已完成：

- `git verify-doc-change`
- `git dangerous-commit list`
- `git dangerous-commit resolve`

待补：

- 危险提交登记入口或从 verify 风险路径自动创建 `DangerousCommitRecord`
- `git post-push-refresh`
- 推送后按 commit 范围触发 `graph refresh-nodes`

