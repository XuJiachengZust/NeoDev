---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-25-NEODEV-PRODUCT-VERSION-BRANCH-CLI-T003
title: "T003 产品 / 产品版本 / 分支绑定 CLI 记录"
aliases:
  - "T003 产品 / 产品版本 / 分支绑定 CLI 记录"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/plan
created: 2026-04-25
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
# T003 产品 / 产品版本 / 分支绑定 CLI 记录

## 范围

本文记录 `T003 产品 / 产品版本 / 分支绑定 CLI` 的实现情况。

本任务基于 `T001` 的 CLI 基础壳层和 `T002` 的元数据 / repository 基础，补齐产品作用域下的 CLI 能力：

- 创建、更新、查看产品。
- 创建、查看产品版本。
- 将产品版本绑定到项目分支。
- 同时支持数字 ID 和稳定业务键作为命令定位方式。

## 命令面

已实现命令：

- `product create`
- `product update`
- `product show`
- `product version create`
- `product version show`
- `product version bind-branch`

## 定位规则

产品支持以下任一定位方式：

- `--product-id`
- `--product-code`

产品版本支持以下任一定位方式：

- `--version-id`
- `--product-id` 或 `--product-code` 搭配 `--version-name`

项目支持以下任一定位方式：

- `--project-id`
- `--project-name`

定位约束：

- 同一实体同时传 ID 和业务键时返回 `invalid_argument`。
- 产品、版本或项目不存在时返回 `not_found`。
- 项目名称不唯一时返回 `conflict`。
- 数据库唯一约束冲突返回 `conflict`，例如重复产品编码、同一产品下重复版本名。
- 项目已经绑定到其他产品时，跨产品绑定返回 `conflict`。

## 实现说明

本次新增或修改的文件：

- `src/service/cli/commands/product.py`
- `src/service/cli/commands/__init__.py`
- `src/service/cli/output.py`
- `src/service/repositories/product_repository.py`
- `src/service/repositories/product_version_repository.py`
- `src/service/repositories/project_repository.py`
- `src/service/services/product_service.py`
- `src/service/services/product_version_service.py`
- `src/service/services/project_service.py`
- `tests/test_product_cli.py`

设计取舍：

- CLI 层保持薄封装，只负责参数解析、实体定位、调用 service、格式化输出。
- 复用现有 `product_service`、`product_version_service`、`project_service`。
- repository 只补聚焦的查询辅助方法，不在 repository 中塞编排逻辑。
- CLI JSON 输出已支持 `datetime` 和 `date` 序列化，数据库行可以稳定返回为 JSON payload。
- `product version bind-branch` 复用 `product_version_service.set_branch`，绑定产品版本分支时会同步确保项目级 `versions` 分支记录存在。

## 边界测试覆盖

`tests/test_product_cli.py` 当前覆盖：

- 通过 `--product-code` 创建和查看产品。
- 通过 `--product-id` 查看产品。
- 通过产品 ID 或产品 code 创建产品版本。
- 通过 `--version-id` 查看产品版本。
- 通过 `--product-code + --version-name` 查看产品版本。
- 通过数字 ID 绑定项目分支。
- 通过业务键绑定项目分支。
- 更新产品并修改产品 code。
- 产品不存在时返回 `not_found`。
- 产品 code 重复时返回 `conflict`。
- 同一产品下版本名重复时返回 `conflict`。
- 同时传 `--product-id` 和 `--product-code` 时返回 `invalid_argument`。
- 只传 `--version-name` 但缺少产品作用域时返回 `invalid_argument`。
- 分支绑定时项目不存在返回 `not_found`。
- `--project-name` 命中多个项目时返回 `conflict`。
- 项目已经绑定其他产品时拒绝跨产品绑定。
- 同一产品版本和项目重复绑定时更新 branch。

## 验证记录

本轮验证命令：

```powershell
pytest tests/test_cli_contract.py tests/test_metadata_migration.py tests/test_metadata_repositories.py tests/test_product_cli.py -v
```

观察结果：

```text
47 passed, 1 warning
```

其中 warning 来自当前工作区无法写入 `.pytest_cache`，不影响测试结果。

## 当前状态

`T003` 已完成实现并有自动化测试覆盖。产品、产品版本、项目分支绑定 CLI 已同时支持数字 ID 和业务键两种调用方式。
