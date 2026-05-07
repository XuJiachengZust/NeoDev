---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-DOCCHANGE-CLI-T005
title: NeoDev T005 DocChange CLI 留痕
aliases:
- NeoDev T005 DocChange CLI 留痕
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

# NeoDev T005 DocChange CLI 留痕

## 背景

本次继续推进研发知识图谱 MVP 的 T005：`DocChange` 登记与状态流转。

T001 到 T004 已经提供 CLI 壳层、元数据表、产品版本绑定和文档扫描能力。T005 的目标是把“已扫描的受控文档 -> DocChange -> 待实现/已实现状态”打成最小闭环，为后续 T011 的 `DocChange-ID` Git 校验和插件/skill 工作流提供稳定入口。

## 本次实现范围

新增服务层：

- `src/service/services/doc_change_service.py`

扩展 CLI：

- `doc change register`
- `doc change show`
- `doc change mark-implemented`

新增/扩展测试：

- `tests/test_doc_change_service_unit.py`
- `tests/test_cli_contract.py`
- `tests/test_doc_cli.py`

## 命令行为

### `doc change register`

输入：

- `--document-id`，必填
- `--doc-change-id`，可选；不传时自动生成 `DC-<DOC_ID>-<8位随机后缀>`
- `--source-commit`，可选
- `--summary`，可选
- `--created-by`，可选

输出：

- `doc_change`
- `document`

初始状态固定为 `pending_implementation`。

### `doc change show`

支持通过以下任一定位方式查询：

- `--change-id`
- `--doc-change-id`

输出：

- `doc_change`
- `document`

### `doc change mark-implemented`

支持通过以下任一定位方式标记完成：

- `--change-id`
- `--doc-change-id`

行为：

- 将 `status` 更新为 `implemented`
- 首次写入 `implemented_at`
- 重复调用保持幂等，不覆盖既有 `implemented_at`

## 边界处理

- 缺少 DocChange 定位参数：返回 `invalid_argument`
- 同时传入 `--change-id` 和 `--doc-change-id`：返回 `invalid_argument`
- `document_id` 不存在：返回 `not_found`
- `doc_change_id` 不存在：返回 `not_found`
- 重复 `doc_change_id`：由数据库唯一约束返回 `conflict`

## 验证记录

红灯：

```powershell
pytest tests/test_cli_contract.py::test_doc_change_commands_are_registered -q
```

结果：失败，`doc change` 尚未注册，错误为 `invalid choice: 'change'`。

服务层红灯：

```powershell
pytest tests/test_doc_change_service_unit.py -q
```

结果：失败，`doc_change_service` 尚不存在。

绿灯：

```powershell
pytest tests/test_doc_change_service_unit.py tests/test_cli_contract.py::test_doc_change_commands_are_registered -q
```

结果：`4 passed, 1 warning`。

远程 PG 集成验证：

```powershell
$env:TEST_DATABASE_URL='postgresql://postgres:postgres@<remote-pg-host>:5432/neodev'
pytest tests/test_doc_cli.py -q
```

结果：`6 passed, 1 warning`。

说明：远程 `neodev-postgres` 容器状态为 healthy，测试真实写入远程 PostgreSQL。测试数据使用随机后缀，未清空远程库。远程环境连接细节以 `harness/context/dev-environment.md` 为准。

## 剩余事项

T005 当前完成最小 CLI 闭环。后续可继续扩展：

- 在 T011 中实现 `git verify-doc-change`，将合法提交推进为 `in_implementation`
- 增加 DocChange 列表查询能力
- 增加更完整的 `details_json` CLI 输入
- 在插件/skill 中把 `doc change register/show/mark-implemented` 包装成研发工作流

## 关联文档
- [[neosuperpower/specs/2026-04-24-neodev-cli-and-metadata-foundation-design|NeoDev CLI 与元数据基础设计]]
