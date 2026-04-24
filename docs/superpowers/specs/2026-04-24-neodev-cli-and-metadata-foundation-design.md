# NeoDev CLI 与元数据基础设计

## 1. 范围

本设计只覆盖研发知识图谱 MVP 的第一批实现切片：

- `T001` CLI 壳层与统一结果契约
- `T002` 轻量元数据模型与迁移

明确不包含在本切片内的内容：

- `T003` 中的产品 / 版本业务工作流
- `T004` 与 `T005` 中的文档扫描与 `DocChange` 生命周期命令
- 分支分析编排、图谱刷新、语义检索、Git 校验、插件与 skill 交付

本切片的目标是先建立稳定的命令执行壳层和可持久化的元数据基础，使后续任务可以在不返工底层契约的前提下继续叠加。

## 2. 设计决策

### 2.1 CLI 形式

CLI 采用 Python 标准库 `argparse`，不引入新的 CLI 框架。

原因：

- 当前仓库并未使用 Typer 或 Click
- `argparse` 不会引入新的依赖和环境变动
- 这一阶段更看重契约稳定性，而不是命令声明语法的美观度

本轮同时支持两种入口形式，并共享同一套实现：

- 内部模块入口：`python -m service.cli.main ...`
- 仓库根级入口：`python neodev.py ...`

根级入口的存在，是为了让后续插件和 skill 可以调用一个稳定的顶层命令，而不需要感知 Python 模块路径。

### 2.2 结果契约

本切片内的所有 CLI 命令都支持 `--json`，并返回统一的顶层结构：

- `ok`
- `command`
- `timestamp`
- `data`
- `errors`

人类可读输出可以保留给本地使用，但 JSON 将作为自动化调用的唯一权威协议。

本切片实现的错误分类包括：

- `invalid_argument`
- `not_found`
- `conflict`
- `not_ready`
- `internal_error`
- `version_mismatch`

每种错误分类都将通过统一的 CLI 错误适配层映射到稳定的进程退出码。

### 2.3 初始命令面

本切片不会假装后续业务能力已经完成。命令组会按受控方式引入：

- `cli version-check` 会真实实现
- 公共 CLI 框架会为 `product`、`doc`、`graph`、`git` 命令组预留扩展能力
- 当前只注册能够证明路由和契约稳定性的最小命令面

如果某个面向未来的命令组提前暴露出来，它必须显式返回结构化 `not_ready`，而不是提供半成品行为。

## 3. 文件布局

新的 CLI 代码放在 `src/service/cli/` 下：

- `main.py`：解析器初始化与顶层分发入口
- `output.py`：成功 / 失败 JSON 结果构造器，以及人类可读渲染辅助
- `errors.py`：CLI 类型化错误、错误分类映射、退出码映射
- `commands/__init__.py`：命令注册入口
- `commands/cli.py`：`cli version-check`
- `commands/product.py`：如有需要，用于先占位产品命令组的解析结构

新增仓库根级入口：

- `neodev.py`

该入口只负责转发到 `service.cli.main`，不承载业务逻辑。

## 4. 元数据边界

当前代码库中已经存在的表和仓储，在本切片中视为基础能力，不重新设计：

- `products`
- `product_versions`
- `product_version_branches`
- `ai_preprocess_status`

本切片新增的元数据对象包括：

- `doc_bindings`
- `documents`
- `doc_changes`
- `code_change_links`
- `dangerous_commit_records`

这些表是支撑后续文档治理、`DocChange` 生命周期、代码提交关联以及危险提交追踪的最小事实源，不需要把这类运营态数据强行塞进图数据库。

`BranchAnalysisTask` 在本轮不新增独立表。现有 `ai_preprocess_status` 继续作为分支分析运行态的临时事实源，后续任务通过适配层使用它，而不是让各处都直接依赖其原始表语义。

## 5. 元数据模型

### 5.1 `doc_bindings`

用途：
将产品与其受控文档仓库及扫描根目录绑定起来。

最小字段：

- `id`
- `product_id`
- `repo_path`
- `repo_url`
- `default_branch`
- `is_active`
- `created_at`
- `updated_at`

约束：

- MVP 阶段每个产品只允许一个激活中的文档绑定
- 外键关联到 `products`

### 5.2 `documents`

用途：
持久化扫描得到的文档元数据，不与图谱增强结果混用。

最小字段：

- `id`
- `doc_binding_id`
- `doc_id`
- `doc_type`
- `relative_path`
- `title`
- `front_matter_json`
- `relations_json`
- `status`
- `last_seen_commit`
- `last_scanned_at`
- `created_at`
- `updated_at`

约束：

- `doc_id` 唯一
- `(doc_binding_id, relative_path)` 唯一

### 5.3 `doc_changes`

用途：
表示由受控文档变更生成、面向实现闭环的变更记录。

最小字段：

- `id`
- `doc_change_id`
- `document_id`
- `status`
- `source_commit`
- `summary`
- `details_json`
- `created_by`
- `implemented_at`
- `created_at`
- `updated_at`

约束：

- `doc_change_id` 唯一
- 状态限定为 MVP 阶段的以下枚举：
  - `pending_implementation`
  - `in_implementation`
  - `implemented`

### 5.4 `code_change_links`

用途：
持久化“某次代码提交引用了某个 `DocChange`”这一事实。

最小字段：

- `id`
- `doc_change_id`
- `project_id`
- `branch`
- `commit_sha`
- `commit_message`
- `created_at`

约束：

- 外键关联到 `doc_changes`
- 对 `(project_id, branch, commit_sha)` 建索引

### 5.5 `dangerous_commit_records`

用途：
追踪那些被显式放行、但仍需要后续处理和关闭的高风险提交。

最小字段：

- `id`
- `project_id`
- `branch`
- `commit_sha`
- `risk_level`
- `reason`
- `status`
- `resolved_by`
- `resolved_at`
- `extra_json`
- `created_at`
- `updated_at`

约束：

- 对 `(project_id, status, created_at)` 建索引
- 状态至少支持 `open` 与 `resolved`

## 6. 实现方式

### 6.1 CLI 架构

CLI 采用薄命令层包裹仓储与服务能力：

- 解析层只负责解析参数
- 命令处理器负责调用 service / repository
- 输出层负责结果格式化
- 错误层负责把异常翻译成错误分类与退出码

这样可以避免 CLI 返回结构和 FastAPI HTTP 返回结构耦合在一起，也能让后续 HTTP 与 CLI 各自演进。

### 6.2 迁移策略

数据库迁移沿用当前 `docker/migrations/*.sql` 机制，通过新增增量 SQL 文件落地。

迁移必须满足幂等和增量原则：

- 创建缺失表
- 增加所需索引与约束
- 用户已确认 metadata 旧数据无需迁移，允许直接彻底删除；因此本切片允许为收敛到最终 schema 进行必要的破坏性清理，包括 `DROP COLUMN change_summary`

这样可以兼容当前 `service.migrate.run_migrations()` 的启动迁移方式。

### 6.3 仓储策略

针对新增元数据表，在 `src/service/repositories/` 下增加对应 repository 模块。

本切片的 repository 规则：

- 直接写 SQL 是可接受的，且与现有仓库风格一致
- 返回值继续使用 plain `dict`，保持与当前仓储风格一致
- 写操作保持小而明确
- 不提前把编排逻辑塞进 repository

除非某个命令确实需要跨多个仓储做编排，否则本轮不主动新增新的 service 层抽象，以避免过早设计。

## 7. 测试策略

### 7.1 CLI 测试

`T001` 的测试重点包括：

- `python neodev.py ... --json` 返回包含约定顶层字段
- `python -m service.cli.main ... --json` 与根级入口行为一致
- `cli version-check --json` 成功并返回稳定结构
- 非法参数被映射为结构化错误结果和稳定的非零退出码
- 若暴露了未完成命令面，则它们必须显式返回 `not_ready`

### 7.2 元数据测试

`T002` 的测试重点包括：

- 迁移可成功创建新增表
- repository 的 create / get / list / update 行为正确
- `doc_change_id`、`doc_id` 和文档路径范围约束生效
- 危险提交关闭时能正确回写 `resolved_by` 和 `resolved_at`
- 审计时间字段存在且可用

### 7.3 验收证据

在宣称本切片完成前，必须具备以下证据：

- CLI 契约与元数据 repository 的自动化测试通过
- 至少有一条真实命令执行成功，具体为：
  - `python neodev.py cli version-check --json`

## 8. 风险与护栏

风险：
CLI 可能逐渐演变成第二套应用表面，并开始复制业务逻辑。

护栏：
保持 CLI 足够薄，只有在确实需要复用时，才把逻辑下沉到 repository 或聚焦明确的 service。

风险：
元数据模型可能过早绑定后续工作流语义，导致后面难以调整。

护栏：
本切片只增加持久化结构和稳定标识，不提前固化后续工作流规则。

风险：
后续任务可能直接依赖 `ai_preprocess_status` 的表结构。

护栏：
后续分支分析能力必须通过适配层读取运行态任务状态，从而保留未来引入独立任务模型的空间。

## 9. 本切片完成判定

当以下条件全部满足时，可以认为本切片完成：

- `neodev.py` 作为稳定的仓库根级 CLI 入口可用
- `src/service/cli/` 提供共享的解析、输出和错误基础设施
- `cli version-check` 已实现，并返回约定结果契约
- 新增元数据表通过迁移落地
- 新增元数据对象具备 repository 访问能力
- 自动化测试覆盖 CLI 契约与元数据持久化
- 至少执行过一次真实 CLI 命令作为最终验证
