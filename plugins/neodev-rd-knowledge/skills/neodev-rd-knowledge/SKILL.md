---
name: neodev-rd-knowledge
description: 使用 NeoDev 远程服务管理研发知识图谱、文档导入、文档关系、Obsidian 可视化链接、DocChange、NeoSuperpower 工作流和代码分支图谱。
---

# NeoDev 研发知识图谱

只通过本地 `neodev` CLI 访问远程 NeoDev 服务；除排障外，不直接连接 PostgreSQL 或 Neo4j。

共享工作流契约位于 `plugins/neodev-rd-knowledge/workflows/core-workflows.json`，插件、skill 和 CLI 引导必须以该文件为准。

NeoDev 插件内的流程纪律统一称为 `neosuperpower`。新建或维护 NeoDev 受控文档时，目录、标签和工作流名称都应使用 `neosuperpower`。

## 启动检查

```bash
scripts/install-neodev-client.cmd -Server <remote_api_url>
# 或在允许当前进程绕过执行策略时：
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/install-neodev-client.ps1 -Server <remote_api_url>
neodev config set-server <remote_api_url>
neodev config show --json
neodev cli version-check --json
```

## 文档目录结构

所有受控 Markdown 文档必须位于同一个 `<docs_root>` 下。需要 Obsidian 图谱时，打开 `<docs_root>` 作为 vault，不要打开它的子目录。

标准目录：

- `<docs_root>/prd/`: 产品 PRD。
- `<docs_root>/prototype/`: 原型和交互对齐文档。
- `<docs_root>/tech-design/`: 技术设计文档。
- `<docs_root>/neosuperpower/`: NeoDev 工作流、计划、校验和 skill 文档。
- `<docs_root>/<domain>/`: 产品域证据、报告、抽取源文档和专题笔记。

`neosuperpower` 子目录：

- `neosuperpower/plans/`: 执行计划和任务计划。
- `neosuperpower/specs/`: 设计规格和决策记录。
- `neosuperpower/skills/<skill_name>/`: skill 指令、模板和局部指南。
- `neosuperpower/reports/`: 验证报告和运行摘要。
- `neosuperpower/templates/`: 可复用文档模板。

禁止：

- 新增 `docs/superpowers/`。
- 把嵌套 Obsidian vault 当成源目录。
- 在 `<docs_root>` 外生成受控文档。

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
3. 创建文档仓库绑定：`neodev doc binding create --product-code <product_code> --project-id <doc_project_id> --branch <branch> --json`
4. 查询文档仓库绑定：`neodev doc binding list --product-code <product_code> --json`
5. 导入文档：`neodev doc import --doc-binding-id <id> --force --json`
6. 登记文档变更：`neodev doc change register --document-id <document_id> --json`
7. 查询文档影响：`neodev graph impact --doc-change-id <doc_change_id> --json`
8. 重建代码分支图谱：`neodev project refresh-graph --project-id <project_id> --branch <branch> --json`

## 边界

- 文档关系写入先维护源文件，再通过 CLI import 验证并写入文档 Git commit。
- `doc import` 返回轻量文档摘要，并由服务投影 `Project -[:HAS_DOCUMENT]-> Document` 归属关系。
- 导入文档前先通过 `doc binding list` 获取 `doc_binding_id`；若产品没有 active 文档绑定，使用 `doc binding create` 创建，不要直接写数据库。
- DocChange-ID 默认使用文档 Git commit hash；提交代码时 `DocChange-ID` trailer 也应填写该 40 位 commit hash。
- 代码图谱刷新只使用 `project refresh-graph --branch`。
- 远程数据库直连只用于定位 CLI/API 与存储层不一致的问题。
