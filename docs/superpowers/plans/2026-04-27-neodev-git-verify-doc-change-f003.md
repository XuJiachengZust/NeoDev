# NeoDev F003 Git Verify DocChange CLI 留痕

## 背景

继续推进研发知识图谱 MVP 的 F003「Git 一致性、危险提交与推送后刷新」。本轮先完成第一条闭环：

- `git verify-doc-change`

目标是把 `DocChange-ID` 从提交消息约定变成 CLI 可验证、可落库、可推进状态机的正式协议。

## 范围

本轮实现：

- 新增 `commit_message_parser`
- 新增 `git_consistency_service`
- 新增 `git verify-doc-change` CLI
- 校验 commit message 中唯一的 `DocChange-ID: <id>` trailer
- 校验 DocChange 是否存在
- 拒绝已经 `implemented` 的 DocChange
- 创建 `CodeChangeLink`
- 将 DocChange 从 `pending_implementation` 推进到 `in_implementation`

暂不实现：

- `git dangerous-commit resolve`
- `git post-push-refresh`
- 危险提交二次确认和待处理列表

## TDD 记录

红灯：

```powershell
pytest tests/test_cli_contract.py::test_git_verify_doc_change_command_is_registered tests/test_commit_message_parser_unit.py tests/test_git_consistency_service_unit.py tests/test_git_cli.py::test_git_verify_doc_change_rejects_missing_trailer -q
```

失败点：

- 顶层 `git` 命令未注册。
- `service.services.commit_message_parser` 不存在。
- `service.services.git_consistency_service` 不存在。

实现文件：

- `src/service/services/commit_message_parser.py`
- `src/service/services/git_consistency_service.py`
- `src/service/cli/commands/git.py`
- `src/service/cli/commands/__init__.py`
- `src/service/repositories/doc_change_repository.py`

测试文件：

- `tests/test_commit_message_parser_unit.py`
- `tests/test_git_consistency_service_unit.py`
- `tests/test_git_cli.py`
- `tests/test_cli_contract.py`

## 行为口径

成功路径输出：

- `status=verified`
- `verification_status=verified`
- `doc_change_status=in_implementation`
- `risk_level=none`
- `next_status=in_implementation`
- `dangerous_commit_required=false`

错误路径：

- 缺少 `DocChange-ID` -> `invalid_argument`
- 重复 `DocChange-ID` -> `invalid_argument`
- 空 trailer 值 -> `invalid_argument`
- DocChange 不存在 -> `not_found`
- DocChange 已 implemented -> `conflict`

## 验证

远程 PG F003 相关：

```powershell
pytest tests/test_commit_message_parser_unit.py tests/test_git_consistency_service_unit.py tests/test_git_cli.py -q
```

结果：

- `9 passed`

第一次完整覆盖集遇到远程 PG 连接被服务端断开的瞬时问题，最早错误为：

- `server closed the connection unexpectedly`

随后复跑最早失败点和新增成功路径：

```powershell
pytest tests/test_product_cli.py::test_product_version_cli_supports_business_keys_for_create_show_and_bind tests/test_git_cli.py::test_git_verify_doc_change_creates_link_and_updates_status -q
```

结果：

- `2 passed`

远程 PG T001 到当前 F003 切片完整覆盖集复跑：

```powershell
pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py tests/test_doc_scan_service.py tests/test_doc_cli.py tests/test_doc_change_service_unit.py tests/test_branch_analysis_service_unit.py tests/test_branch_analysis_service.py tests/test_graph_semantic_search_service_unit.py tests/test_graph_impact_service_unit.py tests/test_graph_refresh_service_unit.py tests/test_graph_query_service_unit.py tests/test_graph_cli.py tests/test_commit_message_parser_unit.py tests/test_git_consistency_service_unit.py tests/test_git_cli.py -q
```

结果：

- `103 passed`

## 当前 F003 状态

已完成：

- `git verify-doc-change`
- `DocChange-ID` trailer 解析
- `CodeChangeLink` 创建
- `DocChange -> in_implementation` 状态推进

待补：

- `git dangerous-commit resolve`
- `git post-push-refresh`
- 危险提交登记 / 查询 / 关闭流水
- 推送后按 commit 范围触发 `graph refresh-nodes`

