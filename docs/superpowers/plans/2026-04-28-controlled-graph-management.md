# 受控图管理实现计划

> **给智能体执行者：** 必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐项执行。任务使用复选框语法跟踪。

**目标：** 增加项目整图刷新和受控的图类型、节点、关系 CLI 管理能力，同时删除废弃的 `git post-push-refresh` 命令。

**架构：** PostgreSQL 保存项目内图类型白名单、可编辑节点元数据和可编辑关系元数据。服务层负责校验类型白名单、身份字段不可变、跨项目关系归属和关系类型跨项目限制。`project refresh-graph` 复用现有同步链路，重新拉取项目分支并重建分支快照。

**技术栈：** Python、FastAPI CLI 命令处理、psycopg2 仓储、PostgreSQL 迁移、pytest。

---

### 任务 1：CLI 契约测试

**文件：**
- 修改：`tests/test_cli_contract.py`
- 修改：`tests/test_git_consistency_service_unit.py`

- [ ] **步骤 1：编写失败测试**

增加测试，确认 `git post-push-refresh` 已删除，`project refresh-graph` 已注册，`graph type/node/edge` 命令族已注册。

- [ ] **步骤 2：验证红灯**

运行：`pytest tests/test_cli_contract.py::test_git_post_push_refresh_command_is_removed tests/test_cli_contract.py::test_project_refresh_graph_command_is_registered tests/test_cli_contract.py::test_graph_management_commands_are_registered -v`

预期：测试失败，因为命令尚未调整。

- [ ] **步骤 3：实现 CLI 命令注册**

从 `src/service/cli/commands/git.py` 删除 `post-push-refresh`；在 `src/service/cli/commands/project.py` 增加 `project refresh-graph`；在 `src/service/cli/commands/graph.py` 增加 `graph type/node/edge` 命令注册。

- [ ] **步骤 4：验证绿灯**

再次运行同一个聚焦测试命令，确认通过。

### 任务 2：图管理元数据迁移

**文件：**
- 新建：`docker/migrations/020_graph_manual_management.sql`
- 修改：`docker/Dockerfile.postgres`
- 新建：`tests/test_graph_manual_management_migration.py`

- [ ] **步骤 1：编写失败迁移测试**

断言 `graph_node_types`、`graph_relation_types`、`graph_nodes`、`graph_edges` 存在，并包含项目内唯一约束和状态检查约束。

- [ ] **步骤 2：验证红灯**

运行：`pytest tests/test_graph_manual_management_migration.py -v`

预期：测试失败，因为迁移文件和表尚不存在。

- [ ] **步骤 3：增加迁移**

创建四张表，包含项目归属、JSONB 属性、归档状态、关系端点项目字段和必要索引。

- [ ] **步骤 4：验证绿灯**

再次运行迁移测试，确认通过。

### 任务 3：仓储层和服务层

**文件：**
- 新建：`src/service/repositories/graph_management_repository.py`
- 新建：`src/service/services/graph_management_service.py`
- 新建：`tests/test_graph_management_service_unit.py`

- [ ] **步骤 1：编写失败服务测试**

覆盖节点类型白名单拒绝、节点更新身份字段拒绝、跨项目关系归属校验、`cross_project_allowed=false` 拒绝跨项目关系。

- [ ] **步骤 2：验证红灯**

运行：`pytest tests/test_graph_management_service_unit.py -v`

预期：导入失败或行为失败。

- [ ] **步骤 3：实现仓储和服务**

增加 CLI 所需的最小增删改查和校验函数。

- [ ] **步骤 4：验证绿灯**

再次运行服务测试，确认通过。

### 任务 4：CLI 处理器

**文件：**
- 修改：`src/service/cli/commands/graph.py`
- 修改：`src/service/cli/commands/project.py`
- 新建：`tests/test_graph_management_cli_unit.py`

- [ ] **步骤 1：编写失败 CLI 处理器测试**

通过 monkeypatch 替换服务调用，验证参数映射和返回结构，不依赖真实数据库。

- [ ] **步骤 2：验证红灯**

运行：`pytest tests/test_graph_management_cli_unit.py -v`

预期：处理器尚未调用服务，测试失败。

- [ ] **步骤 3：实现处理器**

将图类型、节点、关系处理器接到 `graph_management_service`；将项目整图刷新处理器接到现有同步服务，并使用整图刷新语义。

- [ ] **步骤 4：验证绿灯**

再次运行 CLI 单元测试，确认通过。

### 任务 5：回归验证

**文件：**
- 现有 CLI、服务、存储相关测试。

- [ ] **步骤 1：运行聚焦套件**

运行：`pytest tests/test_cli_contract.py tests/test_git_consistency_service_unit.py tests/test_graph_management_service_unit.py tests/test_graph_management_cli_unit.py tests/test_graph_manual_management_migration.py -v`

- [ ] **步骤 2：运行存储结构回归**

运行：`pytest tests/test_branch_snapshot_service.py tests/test_sync_service_branch_snapshot.py tests/test_graph_query_service_unit.py tests/test_node_service_repository_facts.py tests/test_neo4j_writer_repository_facts.py tests/test_pipeline_repository_facts.py -v`

- [ ] **步骤 3：运行全量测试**

运行：`pytest`

已知环境限制：当前机器可能因无法创建 `C:\Users\AH\AppData\Local\Temp\pytest-of-AH` 导致 `tmp_path` 夹具失败；如果再次出现，必须如实记录。
