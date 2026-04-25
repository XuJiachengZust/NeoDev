# T004 文档治理、扫描与受控仓库接入 CLI 记录

## 范围

本文件记录 `T004 文档治理、扫描与受控仓库接入` 的第一阶段实现情况。

本阶段目标是先打通可验收的 `doc scan` 主链路：

- 扫描文档绑定对应的本地文档仓库。
- 仅纳入固定受控目录：`prd/`、`prototype/`、`tech-design/`。
- 解析 Markdown 文件的 YAML front matter。
- 校验最小字段：`doc_id`、`title`、`doc_type`、`product_key`、`status`、`relations`。
- 校验 `relations.target` 必须是非空字符串列表。
- 有效文档写入 `documents` 元数据。
- 结构或 front matter 错误写入 `document_scan_errors`，不注册为有效文档。
- 提供 `doc scan` CLI 入口。

## 命令面

已实现命令：

- `doc scan --doc-binding-id <id> --json`

输出包含：

- `registered_count`
- `error_count`
- `ignored_count`
- `documents`
- `errors`

## 实现说明

新增和调整的主要文件：

- `src/service/services/doc_scan_service.py`
- `src/service/services/doc_validation_service.py`
- `src/service/repositories/document_scan_error_repository.py`
- `src/service/repositories/document_repository.py`
- `src/service/repositories/doc_binding_repository.py`
- `src/service/cli/commands/doc.py`
- `src/service/cli/commands/__init__.py`
- `docker/migrations/018_cli_metadata_foundation.sql`
- `tests/test_doc_scan_service.py`
- `tests/test_doc_cli.py`
- `tests/test_metadata_migration.py`

关键设计：

- CLI 只负责参数解析、数据库事务和结构化错误返回。
- 扫描规则集中在 `doc_scan_service`。
- front matter 结构校验集中在 `doc_validation_service`。
- 文档使用 `(doc_binding_id, relative_path)` 幂等 upsert，重复扫描会更新文档元数据。
- 扫描错误单独持久化到 `document_scan_errors`，避免错误文档进入 `documents`。
- `doc_binding_repository.create` 兼容当前公共库中可能存在的历史必填列 `binding_name`，但只检查当前 schema，避免影响隔离迁移测试。

## 边界测试覆盖

已覆盖：

- 受控目录中的有效文档可生成 `Document` 元数据。
- 非受控目录文档会被忽略。
- 缺失或非法 `relations.target` 会生成扫描错误，不生成 `Document`。
- 重复扫描同一路径文档会更新既有记录，不创建重复记录。
- `doc scan` CLI 可返回扫描摘要。
- 缺失 `doc_binding_id` 会返回 `not_found`。
- 迁移会创建 `document_scan_errors` 表、默认值和索引。

## 验证记录

已执行定向验证：

```powershell
pytest tests/test_metadata_migration.py tests/test_doc_scan_service.py tests/test_doc_cli.py -v
```

结果：

```text
13 passed, 1 warning
```

warning 来自 `.pytest_cache` 写入权限，不是用例失败。

## 当前状态

T004 第一阶段已打通文档扫描和错误留痕主链路。后续可继续扩展：

- `doc scan` 支持按产品业务键解析 active doc binding。
- `doc change register` 生成 `DocChange ID`。
- 扫描错误去重或按扫描批次归档。
- 文档仓库远程拉取、分支校验和 commit 绑定。
