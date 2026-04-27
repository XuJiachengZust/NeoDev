---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-FEATURES-F001-PRODUCT-BINDING-AND-DOCCHANGE-REGISTRATION
title: "F001 产品绑定、版本分支绑定与文档变更登记 PRD"
aliases:
  - "F001 产品绑定、版本分支绑定与文档变更登记 PRD"
tags:
  - neodev/docs
  - neodev/prd
  - neodev/requirements
created: 2026-04-27
updated: 2026-04-27
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
  - "[[01-master-prd]]"
---
# F001 产品绑定、版本分支绑定与文档变更登记 PRD

## 1. 基本信息

| 项 | 值 |
| --- | --- |
| 功能 ID | F001 |
| 优先级 | P0 |
| 对应总 PRD | [../01-master-prd.md](../01-master-prd.md) |
| 关键来源 | SRC-U-001, SRC-U-002, SRC-U-004, SRC-U-008, SRC-U-012, SRC-U-013, SRC-U-014, SRC-C-001, SRC-C-002, SRC-C-003, SRC-C-005, SRC-C-006, SRC-C-007, SRC-C-008 |

## 2. 功能目标

F001 负责把产品、产品版本、代码仓库、文档仓库以及文档变更登记为可追踪事实，并补齐“传入仓库地址后自动触发图谱构建”的入口能力。

该功能解决 4 件事：

1. 创建产品并绑定多个代码仓库分支
2. 创建产品版本并绑定项目分支映射
3. 扫描文档仓库并登记 `DocChange`
4. 传入项目仓库地址后自动触发远程图谱构建，并记录结果和去重动作

## 3. 范围

### 3.1 范围内

- Product / CodeBinding / DocBinding / ProductVersion 持久化
- 文档目录扫描与 front matter 校验
- `DocChange ID` 生成
- 仓库地址接入
- 仓库登记后自动触发图谱构建
- 图谱构建结果查询
- 同代码跨分支复用图谱结果

### 3.2 范围外

- 修改方案生成本身
- Git 推送前校验
- 文档 UI

## 4. 用户故事

| ID | 用户故事 |
| --- | --- |
| US-F001-01 | 研发负责人可以创建产品，并绑定多个代码仓库分支和一个文档仓库 |
| US-F001-02 | 研发负责人可以创建产品版本，并把不同项目仓库分支映射到该版本 |
| US-F001-03 | 方案作者提交文档后，系统可以扫描并生成 `DocChange ID` |
| US-F001-04 | 研发负责人或开发者可以传入仓库地址并自动触发远程图谱构建 |
| US-F001-05 | 研发负责人可以查看仓库项目和图谱构建结果 |
| US-F001-06 | 当多个分支代码相同，系统可以复用已有分析结果而不是重复跑一遍 |

## 5. CLI 能力

| 命令 | 说明 |
| --- | --- |
| `product create` | 创建产品并初始化基础绑定 |
| `product update` | 更新产品元数据 |
| `product show` | 查看产品详情 |
| `product version create` | 创建产品版本 |
| `product version bind-branch` | 绑定 `project_id/project_name -> branch` 映射 |
| `product version show` | 查看产品版本及其分支映射 |
| `doc scan` | 扫描文档仓库，解析受控文档与 front matter |
| `doc change register` | 基于文档提交生成 `DocChange ID` |
| `project create --repo-url` | 登记远程仓库并自动触发图谱构建 |
| `project show` | 查看项目仓库和图谱构建结果 |
| `product version bind-branch` | 按需把项目分支纳入产品版本范围 |

## 6. 业务规则

| ID | 规则 | 验收 |
| --- | --- | --- |
| BR-F001-01 | 一个 Product 可绑定多个 `CodeBinding`，每个绑定至少包含 `repo_url + branch` | AC-F001-01 |
| BR-F001-02 | 一个 Product 只能绑定一个 `DocBinding` | AC-F001-01 |
| BR-F001-03 | 文档扫描仅纳入 `prd/`、`prototype/`、`tech-design/` | AC-F001-02 |
| BR-F001-04 | 文档必须使用 YAML front matter，并至少包含 `doc_id/title/doc_type/product_key/status/relations` | AC-F001-02 |
| BR-F001-05 | 每次受控文档提交生成一个新的 `DocChange ID` | AC-F001-03 |
| BR-F001-06 | `DocChange` 初始状态固定为 `pending_implementation` | AC-F001-03 |
| BR-F001-07 | ProductVersion 必须保存项目分支映射，作为后续检索和分析作用域 | AC-F001-04 |
| BR-F001-08 | 触发自动图谱构建时，输入至少包含 `product_key/product_version_id/project_id(or name)/branch` | AC-F001-05 |
| BR-F001-09 | 同一项目存在运行中分析任务时，新任务必须返回 busy/冲突 | AC-F001-06 |
| BR-F001-10 | 图谱构建任务必须持久化 `status/progress/started_at/finished_at/heartbeat_at` | AC-F001-07 |
| BR-F001-11 | 若目标分支与其他已分析分支 `HEAD` 相同，优先执行 `copy_data` 而不是 `full` | AC-F001-08 |
| BR-F001-12 | 若目标分支存在 `last_parsed_commit` 可衔接，优先执行 `incremental` | AC-F001-09 |
| BR-F001-13 | 若无法复用且不存在增量起点，则执行 `full` | AC-F001-09 |
| BR-F001-14 | 分析完成后必须回写 `last_parsed_commit` 和 `analysis_action` | AC-F001-10 |

## 7. 数据字段

| 字段 | 说明 |
| --- | --- |
| `product_key` | 产品短标识 |
| `product_version_id` | 产品版本 ID |
| `branch_mappings` | `[{project_id, project_name, branch}]` |
| `doc_change_id` | 文档变更跟踪 ID |
| `analysis_task_id` | 图谱构建任务 ID |
| `status` | `queued/running/completed/failed` |
| `progress` | 结构化进度，例如已处理节点数、阶段、百分比 |
| `analysis_action` | `copy_data/incremental/full` |
| `last_parsed_commit` | 最近一次成功解析的 commit |
| `heartbeat_at` | 任务心跳时间 |

## 8. 输出要求

### 8.1 `project create --repo-url`

最小返回：

- `project`
- `project.id`
- `project.name`
- `project.repo_url`
- `auto_graph_analysis`
- `project.init_result.sync`
- `message`

### 8.2 `project show`

最小返回：

- `project_id`
- `project_name`
- `repo_url`
- `watch_enabled`
- `last_parsed_commit`
- `init_result`

## 9. 异常处理

| ID | 场景 | 处理 |
| --- | --- | --- |
| EX-F001-01 | 产品不存在 | 返回明确错误 |
| EX-F001-02 | 文档仓库不存在或无法读取 | 扫描失败并保留错误信息 |
| EX-F001-03 | front matter 缺字段或格式错误 | 拒绝登记文档并返回字段级错误 |
| EX-F001-04 | 触发图谱构建时产品版本未绑定该项目分支 | 返回参数错误或未绑定错误 |
| EX-F001-05 | 项目已有运行中分析任务 | 返回 busy/冲突 |
| EX-F001-06 | 分析过程长时间无 heartbeat | 允许按既有策略判定为 stale 并转 failed |

## 10. 验收标准

| ID | 前置条件 | 操作 | 预期结果 |
| --- | --- | --- | --- |
| AC-F001-01 | 用户提供产品信息、代码仓库分支和文档仓库 | 执行产品创建 | 成功持久化 Product / CodeBinding / DocBinding |
| AC-F001-02 | 文档仓库中存在受控目录文档 | 执行 `doc scan` | 成功解析文档并校验 front matter |
| AC-F001-03 | 文档有新提交 | 执行 `doc change register` | 生成 `doc_change_id`，状态为 `pending_implementation` |
| AC-F001-04 | 产品已创建 | 执行 `product version create` 和 `bind-branch` | 成功保存产品版本和项目分支映射 |
| AC-F001-05 | 仓库地址可访问 | 执行 `project create --repo-url` | 创建项目并自动触发远程图谱构建 |
| AC-F001-06 | 同一项目已有运行中图谱构建 | 再次登记或触发构建 | 返回 busy/冲突，不产生第二个运行中任务 |
| AC-F001-07 | 仓库已登记 | 执行 `project show` | 返回项目仓库、图谱构建结果和可查询上下文 |
| AC-F001-08 | 新分支与已分析分支 `HEAD` 相同 | 触发图谱构建 | 使用 `copy_data` 复用已有图谱 |
| AC-F001-09 | 新分支存在增量起点 | 触发图谱构建 | 使用 `incremental` 而非 `full` |
| AC-F001-10 | 分析成功完成 | 查看 watch/status | `last_parsed_commit` 和 `analysis_action` 已回写 |

## 11. 测试场景

| ID | 优先级 | 场景 |
| --- | --- | --- |
| TC-F001-01 | P0 | 创建产品并绑定多个代码仓库分支和一个文档仓库 |
| TC-F001-02 | P0 | 扫描文档仓库并解析 front matter |
| TC-F001-03 | P0 | 文档提交后生成 `DocChange ID` |
| TC-F001-04 | P0 | 创建产品版本并绑定项目分支 |
| TC-F001-05 | P0 | 传入仓库地址后自动触发远程图谱构建 |
| TC-F001-06 | P0 | 查询分析任务状态和进度 |
| TC-F001-07 | P0 | 同项目重复触发图谱构建时返回 busy |
| TC-F001-08 | P0 | 同 HEAD 分支触发时走 `copy_data` |
| TC-F001-09 | P1 | 增量场景走 `incremental` |
| TC-F001-10 | P1 | stale 任务被转 failed 并可重新触发 |
