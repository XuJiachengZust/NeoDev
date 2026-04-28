---
doc_id: NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-F004-GIT-DOC-CHUNK-SEMANTIC-SEARCH
title: "F004 Git 文档导入、分块向量化与文档语义检索 PRD"
aliases:
  - "F004 Git 文档导入、分块向量化与文档语义检索 PRD"
tags:
  - neodev/docs
  - neodev/prd
  - neodev/requirements
created: 2026-04-28
updated: 2026-04-28
doc_type: prd
product_key: NEODEV
status: active
relations:
  target:
    - NEODEV-DOC-REQUIREMENTS-RD-KNOWLEDGE-GRAPH-MVP-01-MASTER-PRD
related:
  - "[[01-master-prd]]"
---

# F004 Git 文档导入、分块向量化与文档语义检索 PRD

## 1. 范围覆盖

本文档在冲突处覆盖早期 MVP 表述。

- 文档只从产品绑定的 Git 文档仓库导入。
- 直接上传文档不属于 MVP 导入路径。
- 受控文档目录为 `prd/`、`prototype/`、`tech-design/` 和 `docs/`。
- Neo4j 只保存文档级图事实。
- PostgreSQL 与 pgvector 保存文档分块和分块 embedding。
- 对外语义检索只返回文档分块，不返回代码图谱节点。

## 2. 文档导入

导入命令在扫描前同步已配置的文档仓库。

必需 CLI：

```bash
neodev.py doc import --doc-binding-id <id> --json
```

预期行为：

- 如果 `doc_bindings.repo_path` 已存在，则从 Git 更新。
- 如果 `repo_path` 缺失且存在 `repo_url`，则把仓库克隆到 `repo_path`。
- 切换到 `doc_bindings.default_branch`。
- 只扫描受控目录下的 Markdown 文件。
- 校验既有 YAML front matter 规则。
- 持久化文档元数据、正文文本和内容哈希。
- 当前 Git checkout 中缺失的文档标记为删除或非活跃。

## 3. 文档图谱

Neo4j 仍然是文档图事实存储。

- 每个受控文档映射为一个 `Document` 节点。
- 文档节点身份基于产品、绑定和 `doc_id`。
- 文档关系从 front matter 派生，尤其是 `relations.target`。
- MVP 中分块不成为图节点。

## 4. 文档分块

分块在文档元数据和图事实更新后执行。

分块策略：

1. 优先按 Markdown 结构分块。
2. 结构分块过长时，再按语义相似度继续切分。
3. 保留原始文档顺序。
4. 存储分块文本、标题路径、序号、token 估算、内容哈希和 embedding 状态。

结构分块必须尊重：

- Markdown 标题
- 段落
- 列表
- 表格
- fenced code block

默认阈值：

- 目标分块大小：800 token
- 触发二次切分的最大结构分块大小：1200 token
- 重叠窗口：120 token

## 5. 向量化

每个文档分块生成一个 embedding。

参与 embedding 的文本包括：

- 文档标题
- `doc_id`
- `doc_type`
- tags
- aliases
- 相关文档
- 关系目标
- 标题路径
- 分块文本

如果分块内容哈希未变化，除非显式强制刷新，否则复用既有 embedding。

## 6. 语义检索

`graph semantic-search` 保留为公开 CLI 命令名，但公开结果只用于文档分块检索。

必需结果字段：

- `product_version_id`
- `document_id`
- `doc_id`
- `title`
- `doc_type`
- `relative_path`
- `chunk_id`
- `chunk_index`
- `heading_path`
- `snippet`
- `score`
- `semantic_status`

该命令不得返回代码图谱节点字段，例如 `entity_id`、`entity_type` 或代码 `file_path`。

## 7. 验收标准

- `docs/` 下的 Markdown 文件会被纳入文档导入。
- 受控目录之外的 Markdown 文件会被忽略。
- Git 仓库导入是唯一文档导入路径。
- Neo4j 包含文档级节点和关系。
- PostgreSQL 包含文档分块和分块 embedding。
- 内容未变化的分块不会重复生成 embedding。
- `graph semantic-search` 返回产品版本作用域内的文档分块结果。
