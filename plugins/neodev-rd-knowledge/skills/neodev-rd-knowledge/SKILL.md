---
name: neodev-rd-knowledge
description: 面向 NeoDev 研发知识工作流的官方 skill，用于通过本地 neodev CLI 客户端调用远程 NeoDev 服务，完成文档变更、图谱上下文、Git 校验和推送后刷新。
---

# NeoDev 研发知识工作流

本 skill 只负责引导命令顺序、参数补全、风险提示和结果解释。事实读取与状态变更必须通过本地 `neodev` CLI 客户端调用远程 NeoDev 服务完成。

## 环境准备

- 一行安装 Windows 本地 CLI 客户端：
  `powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -UseBasicParsing https://raw.githubusercontent.com/XuJiachengZust/NeoDev/neodev-sp/scripts/install-neodev-client.ps1 -OutFile $env:TEMP\install-neodev-client.ps1; & $env:TEMP\install-neodev-client.ps1 -Server http://10.50.3.149"`
- 如需切换远程服务，运行：`neodev config set-server <remote_api_url>`。
- 查看当前远程配置，运行：`neodev config show`。
- 在写操作或风险敏感流程开始前，先运行：`neodev cli version-check --json`。
- 插件 hook 会运行 `check_neodev_environment.py`，检查本地 CLI 是否可用、远程服务是否已配置、`cli version-check` 是否兼容。

## 工作流来源

以 `workflows/core-workflows.json` 为唯一工作流契约来源。插件、skill、命令说明和 hook 只围绕该契约解释和校验，不绕过 CLI 直接写数据库或图谱。

## 主流程

### 文档变更到实现

1. 执行 `neodev config show`，确认本地客户端已配置远程 NeoDev 服务。
2. 执行 `neodev cli version-check --json`。
3. 运行 `validate_mvp_docs.py` 和 `validate_obsidian_docs.py` 校验文档格式。
4. 执行 `neodev doc scan --doc-binding-id <doc_binding_id> --json`。
5. 执行 `neodev doc change register --document-id <document_id> --json`。
6. 执行 `neodev graph impact --doc-change-id <doc_change_id> --json`。
7. 按需执行 `neodev graph semantic-search`、`neodev graph entity-context`、`neodev graph get-chain` 获取上下文。

### 仓库接入与自动图谱构建

1. 执行 `neodev config show`，确认本地客户端已配置远程 NeoDev 服务。
2. 执行 `neodev cli version-check --json`。
3. 执行 `neodev project create --name <project_name> --repo-url <repo_url> --json`。
4. 远程 NeoDev 服务在仓库登记后自动触发图谱构建，skill 不再引导用户调用旧显式分析入口。
5. 如需纳入产品版本范围，执行 `neodev product version bind-branch --product-code <product_code> --version-name <version_name> --project-id <project_id> --branch <branch> --json`。
6. 按需执行 `neodev graph semantic-search`、`neodev graph entity-context`、`neodev graph get-chain` 获取上下文。

### 推送前校验

1. 执行 `neodev config show`，确认本地客户端已配置远程 NeoDev 服务。
2. 执行 `neodev cli version-check --json`。
3. 确认 commit message 包含正确的 `DocChange-ID`。
4. 执行 `neodev git verify-doc-change --project-id <project_id> --branch <branch> --commit-sha <commit_sha> --commit-message <commit_message> --json`。
5. 执行 `neodev git dangerous-commit list --project-id <project_id> --json`。
6. 若有风险记录，评审后用 `neodev git dangerous-commit resolve --record-id <record_id> --resolved-by <user> --json` 关闭。

### 推送后刷新

1. 执行 `neodev config show`，确认本地客户端已配置远程 NeoDev 服务。
2. 执行 `neodev cli version-check --json`。
3. 执行 `neodev git post-push-refresh --project-id <project_id> --branch <branch> --commit-sha <commit_sha> --json`。
4. 按需执行 `neodev graph refresh-nodes ... --json`。
5. 按需执行 `neodev graph get-chain ... --json` 检查影响链路。

## 结果解释

- `ok=false` 表示命令未完成，不要继续后续写操作。
- `version_mismatch` 表示本地 CLI、插件或 skill 契约不一致，先修复环境。
- `not_ready` 表示远程服务或必要数据尚不可用。
- `semantic_status=degraded` 表示语义检索降级，仍可继续使用结构化图谱上下文。

## 必守边界

- 不要直接写 PostgreSQL。
- 不要直接写 Neo4j。
- 不直接连接 PostgreSQL。
- 不直接连接 Neo4j。
- 不通过脚本绕过 `neodev` CLI 写入状态。
- 不从插件或 skill 自行编造产品、版本、项目、DocChange、图节点或风险记录。
