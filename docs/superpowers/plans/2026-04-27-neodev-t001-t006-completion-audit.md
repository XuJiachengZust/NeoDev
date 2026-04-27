# NeoDev T001-T006 完整性检查留痕

日期：2026-04-27

## 检查范围

本次按 MVP 任务 `T001` 到 `T006` 做完整性检查，重点核对：

- CLI 命令是否按契约注册
- 统一 JSON 输出和错误码是否稳定
- 元数据迁移和 repository 是否可用
- 产品 / 版本 / 分支绑定是否闭环
- 文档扫描与 DocChange 是否闭环
- 分支分析命令和状态字段是否覆盖契约

## 检查结论

### T001 CLI 壳层与统一结果协议

结论：已覆盖。

已核对：

- `neodev.py`
- `src/service/cli/main.py`
- `src/service/cli/output.py`
- `src/service/cli/errors.py`
- `src/service/cli/commands/cli.py`
- `tests/test_cli_contract.py`

### T002 轻量元数据模型与迁移

结论：已覆盖当前 MVP 1-6 所需元数据基础。

已核对：

- `docker/migrations/018_cli_metadata_foundation.sql`
- `tests/test_metadata_migration.py`
- `tests/test_metadata_repositories.py`
- `product/doc/document/doc_change/code_change_link/dangerous_commit` repository

说明：T006 当前继续复用 `ai_preprocess_status` 作为分支分析任务状态兼容层，不在本次切换到新的 `branch_analysis_tasks` 主表。

### T003 产品 / 版本 / 分支绑定 CLI

结论：已覆盖。

已核对命令：

- `product create`
- `product update`
- `product show`
- `product version create`
- `product version show`
- `product version bind-branch`

测试覆盖：`tests/test_product_cli.py`。

### T004 文档扫描

结论：已覆盖。

已核对命令：

- `doc scan`

已核对能力：

- 受控目录扫描
- front matter 解析
- 文档 upsert
- 扫描错误留痕
- 非法文档不进入有效文档登记

测试覆盖：

- `tests/test_doc_scan_service.py`
- `tests/test_doc_cli.py`

### T005 DocChange 登记与状态流转

结论：已覆盖最小闭环。

已核对命令：

- `doc change register`
- `doc change show`
- `doc change mark-implemented`

已核对能力：

- 自动生成 DocChange ID
- 唯一 DocChange ID
- `pending_implementation`
- 人工标记 `implemented`
- `mark-implemented` 幂等

测试覆盖：

- `tests/test_doc_change_service_unit.py`
- `tests/test_doc_cli.py`

### T006 分支分析编排与状态查看

结论：本次检查发现并补齐两个缺口。

本次补齐：

- 注册 `product version watch-status`
- `analysis_task` 输出补齐契约字段：
  - `current_snapshot_id`
  - `head_commit`
  - `last_parsed_commit`
  - `created_from_action`

已核对命令：

- `product version analyze`
- `product version analyze-status`
- `product version watch-status`

测试覆盖：

- `tests/test_cli_contract.py`
- `tests/test_branch_analysis_service_unit.py`
- `tests/test_branch_analysis_service.py`

说明：`watch-status` 当前是一次性状态读取命令，复用 `get_analysis_status`，不做阻塞式长轮询。这样保持 CLI 可自动化调用，后续如需持续轮询应由插件/skill 或外层脚本控制节奏。

## 验证记录

发现缺口时的红灯：

```powershell
pytest tests/test_cli_contract.py::test_product_version_analysis_commands_are_registered -q
```

结果：失败，`watch-status` 未注册。

状态字段红灯：

```powershell
pytest tests/test_branch_analysis_service_unit.py::test_get_analysis_status_includes_contract_snapshot_fields -q
```

结果：失败，`branch_analysis_service` 尚未输出契约字段。

绿灯：

```powershell
pytest tests/test_branch_analysis_service_unit.py -q
pytest tests/test_cli_contract.py::test_product_version_analysis_commands_are_registered -q
```

结果：通过。

完整目标验证使用远程 PostgreSQL：

```powershell
$env:TEST_DATABASE_URL='postgresql://postgres:postgres@<remote-pg-host>:5432/neodev'
pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py tests/test_doc_scan_service.py tests/test_doc_cli.py tests/test_doc_change_service_unit.py tests/test_branch_analysis_service_unit.py tests/test_branch_analysis_service.py -q
```

结果：`67 passed, 1 warning`。warning 为 `.pytest_cache` 写入权限问题，不影响 T001-T006 功能验证。

## 剩余边界

T001-T006 当前按 CLI 最小 MVP 闭环可用。以下能力属于 T007 之后或更完整的分支分析演进，不作为本次 T001-T006 阻断项：

- 独立 `branch_analysis_tasks` / `branch_analysis_task_events` 主表
- 图谱复用策略 `copy_data / incremental / full` 的独立任务决策表述
- 分支快照表和快照条目表
- HTTP `preprocess` 完全代理到新的产品版本分析入口
