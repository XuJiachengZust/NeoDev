---
name: neodev-rd-knowledge
description: 使用 NeoDev 远程服务管理研发知识图谱、文档导入、文档关系、Obsidian 可视化链接、DocChange 和代码分支图谱。
---

# NeoDev 研发知识图谱

只通过本地 `neodev` CLI 访问远程 NeoDev 服务；除排障外，不直接连接 PostgreSQL 或 Neo4j。

NeoDev 插件内的流程纪律统一称为 `neosuperpower`。新建或维护 NeoDev 受控文档时，目录、标签和工作流名称都应使用 `neosuperpower`。

## 启动检查

```bash
neodev config set-server <remote_api_url>
neodev config show --json
neodev cli version-check --json
```

Windows 客户端安装示例：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -UseBasicParsing https://raw.githubusercontent.com/XuJiachengZust/NeoDev/neodev-sp/scripts/install-neodev-client.ps1 -OutFile $env:TEMP\install-neodev-client.ps1; & $env:TEMP\install-neodev-client.ps1 -Server http://10.50.3.149"
```

## 文档关系规则

NeoDev 和 Obsidian 使用不同的关系来源，维护文档时必须同时满足：

- NeoDev 图谱关系以 front matter 的 `relations.target` 为准，值必须是真实 `doc_id`，例如 `DSC-DOC-0003`。
- Obsidian 图谱关系以 Markdown wikilink 为准，必须写成真实目标文件链接，例如 `[[neosuperpower/plans/2026-04-14-tag-manage-prototype-alignment|标签管理抽屉原型对齐 Implementation Plan]]`。
- `related` 字段和正文末尾 `## 关联文档` 小节应由 `relations.target` 自动反查生成，不要手工维护两套不一致关系。
- 不要把聚合概念 ID，如 `DSC-TAG-MANAGEMENT`，写入 `relations.target`；这类值不会被 NeoDev graph importer 解析成文档节点关系。

同步 Obsidian 链接：

```bash
python plugins/neodev-rd-knowledge/sync_obsidian_links.py <docs_path>
```

校验文档：

```bash
python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>
python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>
```

## 常用流程

1. 登记仓库：`neodev project create --name <project_name> --repo-url <repo_url> --json`
2. 绑定产品版本分支：`neodev product version bind-branch --product-code <product_code> --version-name <version_name> --project-id <project_id> --branch <branch> --json`
3. 扫描文档：`neodev doc scan --doc-binding-id <id> --json`
4. 导入文档：`neodev doc import --doc-binding-id <id> --force --json`
5. 查询文档影响：`neodev graph impact --doc-change-id <doc_change_id> --json`
6. 重建代码分支图谱：`neodev project refresh-graph --project-id <project_id> --branch <branch> --json`

## 边界

- 文档关系写入先维护源文件，再通过 CLI scan/import 验证。
- 代码图谱刷新只使用 `project refresh-graph --branch`。
- 远程数据库直连只用于定位 CLI/API 与存储层不一致的问题。
