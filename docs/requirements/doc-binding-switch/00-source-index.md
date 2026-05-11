---
doc_id: NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-SOURCE-INDEX
title: 文档绑定切换事实源索引
aliases:
- 文档绑定切换事实源索引
tags:
- neodev/docs
- neodev/tech-design
- neodev/requirements
- requirements/doc-binding-switch
created: 2026-05-11
updated: 2026-05-11
related:
- '[[requirements/doc-binding-switch/README|文档绑定切换 PRD 产物索引]]'
- '[[requirements/doc-binding-switch/01-master-prd|文档绑定切换总 PRD]]'
doc_type: tech-design
product_key: NEODEV
status: draft
relations:
  target:
  - NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-README
  - NEODEV-DOC-REQUIREMENTS-DOC-BINDING-SWITCH-MASTER-PRD
---

# 文档绑定切换事实源索引

## 1. 用户输入

| 编号 | 来源 | 内容摘要 | 可用性 | 可追踪到 | 备注 |
| --- | --- | --- | --- | --- | --- |
| SRC-U-001 | 用户消息，2026-05-11 | “文档和产品版本需要有切换绑定的需求” | 已确认 | R-001, F001, BR-G-01, AC-G-01 | 明确需求方向是文档与产品版本的绑定可切换 |
| SRC-U-002 | 用户消息，2026-05-11 | “旧绑定需要删除” | 已确认 | R-002, BR-G-02, BR-F001-02, AC-F001-02, TC-F001-02 | 明确切换不是软删除、复制或覆盖更新，而是删除旧绑定后建立目标绑定 |
| SRC-U-003 | 用户选择，2026-05-11 | 用户选择方案 1：删除后新建 | 已确认 | R-002, F001, AC-G-02 | 确认推荐方案 |
| SRC-U-004 | 用户消息，2026-05-11 | 不做权限；切换命令由实现方选择合适名称；清理绑定数据字段即可；不做自动导入 | 已确认 | R-003, R-006, BR-G-05, BR-G-06, BR-F001-05, BR-F001-06, BR-F001-07, AC-F001-06 | 收口 Q-101 至 Q-104 |

## 2. 本地需求文档

| 编号 | 路径 | 内容摘要 | 适用范围 | 可信度 | 可追踪到 |
| --- | --- | --- | --- | --- | --- |
| SRC-D-001 | `docs/requirements/rd-knowledge-graph-mvp/01-master-prd.md` | NeoDev 以 Product / ProductVersion 组织文档仓库、文档图和语义检索范围 | 总体产品背景 | 高 | R-001, BO-001, BO-002, BO-003 |
| SRC-D-002 | `docs/requirements/rd-knowledge-graph-mvp/features/F001-product-binding-and-docchange-registration.md` | 既有文档绑定、文档扫描、DocChange 登记和版本分支绑定能力 | 现有能力边界 | 高 | BR-G-01, BR-G-03, AC-G-01 |
| SRC-D-003 | `docs/requirements/version-branch-graph-navigation/01-master-prd.md` | 文档图必须绑定产品版本作用域，同一文档不得绑定多个版本 | 版本作用域规则 | 高 | BR-G-04, AC-G-03 |

## 3. 原型、截图与交互材料

| 编号 | 路径 | 内容摘要 | 适用范围 | 待确认点 | 可追踪到 |
| --- | --- | --- | --- | --- | --- |
| SRC-P-001 | 不适用 | 本期未提供 UI 原型，当前需求面向 CLI/API 能力 | 页面入口不纳入本期确定范围 | 本期不做权限模型，不补 UI | SRC-U-004 |

## 4. 代码事实

| 编号 | 路径 | 事实摘要 | 推断限制 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-C-001 | `src/service/repositories/doc_binding_repository.py` | `create` 要求 `product_version_id` 非空，且 active 绑定会校验同一文档 Git 来源不能绑定到其他版本 | 代码事实说明现状，不自动等同最终产品规则 | BO-003, BR-G-04, BR-F001-04 |
| SRC-C-002 | `src/service/cli/commands/doc.py` | 当前 CLI 已有 `doc binding create` 和 `doc binding list`，没有显式切换或删除绑定命令 | 命令命名已按用户授权选择为 `doc binding switch` | R-003, SRC-U-004 |
| SRC-C-003 | `src/service/repositories/document_repository.py` | 文档 upsert 在存在 `product_version_id` 时使用 `(doc_id, product_version_id)` 作为冲突目标 | 只证明文档记录已具备版本隔离基础 | BO-004, BR-G-04 |
| SRC-C-004 | `src/service/services/doc_scan_service.py` | 扫描绑定时根据 binding 的 `product_version_id` 写入 documents | 切换命令不自动扫描；扫描仍由后续命令显式执行 | BR-F001-05, SRC-U-004 |
| SRC-C-005 | `src/service/services/doc_import_service.py` | 导入绑定时根据 binding 的 `product_version_id` upsert 文档、写文档图、替换 chunk | 切换命令不自动导入；导入仍由后续命令显式执行 | BR-F001-06, SRC-U-004 |
| SRC-C-006 | `src/service/services/doc_graph_service.py` | 文档图写入需要 `product_version_id`，文档图摘要按 product/version 名称查询 | 只证明版本文档图查询依赖版本作用域 | AC-G-03, AC-F001-05 |

## 5. 接口与数据事实

| 编号 | 路径/接口/表 | 事实摘要 | 推断限制 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-A-001 | `README.md` | README 公开 CLI 入口包含 `doc binding create/list`、`doc scan`、`doc import`、`doc graph show` | README 可能落后于代码，需要实现时同步校验 | R-003, AC-F001-01 |
| SRC-A-002 | `docker/init.sql` | `doc_bindings.product_version_id` 为产品版本外键，active 绑定存在版本和 Git 来源唯一性约束 | 本需求只要求切换命令清理绑定数据字段，不额外清理文档、chunk 或图谱数据 | BR-F001-04, BR-F001-07, SRC-U-004 |
| SRC-A-003 | `src/service/migrate.py` | 运行时迁移补齐 `doc_bindings.product_version_id`、`documents.product_version_id` 和相关唯一索引 | 迁移事实不等同于切换命令设计 | BR-G-04, AC-G-03 |

## 6. 测试与验收材料

| 编号 | 路径 | 内容摘要 | 适用范围 | 可追踪到 |
| --- | --- | --- | --- | --- |
| SRC-T-001 | `tests/test_doc_cli.py` | 覆盖 doc binding create/list、scan、DocChange CLI 行为 | 新增切换需求应补充同类 CLI 测试 | TC-F001-01, TC-F001-02 |
| SRC-T-002 | `tests/test_cli_contract.py` | 覆盖 CLI 命令注册和帮助契约 | 新命令或参数变更应补充注册测试 | TC-F001-01 |
| SRC-T-003 | `tests/test_doc_scan_service.py` | 覆盖扫描绑定和版本作用域文档登记 | 新需求应补充切换后旧版本不再登记的测试 | TC-F001-03 |
| SRC-T-004 | `tests/test_doc_import_service_unit.py` | 覆盖导入、chunk、version-scoped 文档 upsert | 切换不自动导入；导入侧只需验证目标绑定后续显式 import | TC-F001-05 |

## 关联文档
- [[requirements/doc-binding-switch/README|文档绑定切换 PRD 产物索引]]
- [[requirements/doc-binding-switch/01-master-prd|文档绑定切换总 PRD]]
