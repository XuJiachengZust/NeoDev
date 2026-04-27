---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-27-NEODEV-BRANCH-ANALYSIS-CLI-T006
title: "NeoDev T006 分支分析 CLI 最小切片留痕"
aliases:
  - "NeoDev T006 分支分析 CLI 最小切片留痕"
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
# NeoDev T006 分支分析 CLI 最小切片留痕

日期：2026-04-27

## 背景

在 T003 产品/版本/分支绑定、T004 文档扫描能力之后，开始推进 T006 分支分析编排。当前目标先完成可执行的最小切片：让产品版本作用域下可以通过 CLI 触发分析和查看状态，并复用既有 `preprocess` 执行链路。

## 已实现范围

- 新增 `branch_analysis_service`，作为产品版本分支分析的服务入口。
- `product version analyze`：
  - 校验 `product_version_id + project_id + branch` 是否存在于产品版本分支绑定中。
  - 校验通过后调用既有 `ai_preprocessor_service.run_preprocess`。
  - 返回统一 `analysis_task` 状态结构。
- `product version analyze-status`：
  - 复用同一作用域校验。
  - 从 `ai_preprocess_status` 读取当前状态。
  - 无状态记录时返回 `not_started`。
- 新增 `invalid_scope` CLI 错误类别，用于区分对象存在但不属于该产品版本分支映射。

## 输出结构

`analysis_task` 当前包含：

- `analysis_task_id`
- `product_version_id`
- `project_id`
- `branch`
- `status`
- `analysis_action`
- `progress`
- `started_at`
- `finished_at`
- `heartbeat_at`
- `error_message`

## 测试情况

新增/调整测试：

- `tests/test_branch_analysis_service_unit.py`
- `tests/test_branch_analysis_service.py`
- `tests/test_cli_contract.py`

本地已执行：

```text
pytest tests/test_cli_contract.py tests/test_branch_analysis_service_unit.py -v
20 passed, 1 warning
```

说明：本机 PostgreSQL 当前未启动，`tests/test_branch_analysis_service.py` 属于 PG 集成测试，单独运行时会按现有 fixture 跳过。

## 远程冒烟

已将本切片热更新到远程 `neodev-api` 容器，并基于新建的产品版本分支绑定执行 CLI 冒烟：

- 产品：`NEODEV-T006-1777253800`
- 产品版本 ID：`3`
- 项目 ID：`3`
- 分支：`neodev-sp`
- `product version analyze-status` 初始返回 `not_started`
- `product version analyze --force` 返回 `completed`
- 再次 `product version analyze-status` 返回 `completed`

说明：该远程冒烟使用临时项目路径 `/tmp/neodev-t006-project-1777253800`，不是有效 Git 仓库；底层 `preprocess` 日志记录了图谱同步阶段的无效仓库路径，但 CLI 编排、作用域校验、状态写入与状态查询链路已完成验证。

## 后续范围

本切片暂未实现 T006 的完整任务主表和事件流，后续继续推进：

- BA-03：`branch_analysis_tasks` 与 `branch_analysis_task_events`
- BA-04：按产品版本/项目/分支维度收口并发控制
- BA-05：正式输出 `copy_data / incremental / full` 分析策略
- BA-06 / BA-07：图谱刷新阶段与 AI 分析阶段标准化
- BA-09：让旧 HTTP `preprocess` 入口代理到新服务层
