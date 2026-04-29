---
name: neodev-rd-knowledge
description: 使用 NeoDev 远程服务管理研发知识图谱、文档变更和代码分支图谱。
---

# NeoDev 研发知识图谱

本 skill 只通过本地 `neodev` CLI 客户端访问远程 NeoDev 服务，不直接连接 PostgreSQL 或 Neo4j。

## 启动检查

```bash
neodev config set-server <remote_api_url>
neodev config show
neodev cli version-check --json
```

如需安装 Windows 客户端：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -UseBasicParsing https://raw.githubusercontent.com/XuJiachengZust/NeoDev/neodev-sp/scripts/install-neodev-client.ps1 -OutFile $env:TEMP\install-neodev-client.ps1; & $env:TEMP\install-neodev-client.ps1 -Server http://10.50.3.149"
```

## 工作流来源

工作流以 `workflows/core-workflows.json` 为准。

## 常用流程

1. 登记仓库：`neodev project create --name <project_name> --repo-url <repo_url> --json`
2. 绑定产品版本分支：`neodev product version bind-branch --product-code <product_code> --version-name <version_name> --project-id <project_id> --branch <branch> --json`
3. 重建分支图谱：`neodev project refresh-graph --project-id <project_id> --branch <branch> --json`
4. 查询文档影响：`neodev graph impact --doc-change-id <doc_change_id> --json`
5. 查询代码上下文：`neodev graph entity-context ... --json` 或 `neodev graph get-chain ... --json`

代码图谱不再提供语义搜索入口，推送后也不再使用提交级增量刷新入口。

## 边界

- 不直接访问 PostgreSQL。
- 不直接访问 Neo4j。
- 不调用代码语义搜索或 AI 预处理。
- 分支图谱刷新只使用 `project refresh-graph --branch`。
