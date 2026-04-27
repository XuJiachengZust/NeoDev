---
doc_id: NEODEV-DOC-SUPERPOWERS-PLANS-2026-04-25-NEODEV-REMOTE-DEPLOY-SELF-TEST
title: "NeoDev 远程部署与自测留痕"
aliases:
  - "NeoDev 远程部署与自测留痕"
tags:
  - neodev/docs
  - neodev/tech-design
  - neodev/plan
created: 2026-04-25
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
# NeoDev 远程部署与自测留痕

日期：2026-04-25

## 背景

用户要求将当前 T003/T004 能力部署到远程环境，并允许清空远程环境数据后进行自测。

## 部署情况

- 远程目录：`/root/neodev`
- 远程容器：`neodev-postgres`、`neodev-neo4j`、`neodev-api`、`neodev-web`
- 数据处理：已执行 `docker compose down -v`，远程 Docker volume 被清空后重新创建
- 镜像构建：`docker compose up -d --build` 因远程访问 Docker Hub 超时，未完成重建
- 临时部署方式：使用既有镜像启动容器后，将当前源码与迁移文件复制进 `neodev-api` / `neodev-postgres` 容器，并手动执行 `018_cli_metadata_foundation.sql`

## 远程自测结果

远程 CLI 可见命令：

```text
usage: neodev [-h] [--json] {cli,doc,product} ...
```

容器状态：

```text
neodev-web Up
neodev-api Up
neodev-postgres Up (healthy)
neodev-neo4j Up (healthy)
```

产品/版本/分支绑定自测：

- 新建产品：`NEODEV-REMOTE-1777101578`
- 新建版本：`REMOTE-SMOKE`
- 新建项目：`neodev-remote-project-1777101578`
- 绑定分支：`neodev-sp`
- `product version show --version-id 2 --json` 返回 1 条分支绑定

文档扫描自测：

- 文档绑定 ID：`1`
- 有效文档：`prd/overview.md`
- 错误文档：`tech-design/bad.md`
- 忽略文档：`notes/ignored.md`
- `doc scan --doc-binding-id 1 --json` 返回：
  - `registered_count = 1`
  - `error_count = 1`
  - `ignored_count = 1`
- 数据库复查：
  - `documents` 中该绑定的记录数为 `1`
  - `document_scan_errors` 中该绑定的记录数为 `1`

## 限制与后续

- 当前远程验证证明 T003/T004 的 CLI 链路可以在远程环境运行。
- 当前不是正式镜像级部署，因为远程 Docker Hub 拉取基础镜像超时；若要固化部署，需要解决远程网络拉取问题，或本地构建镜像后通过 `docker save/load` 传入远程。
- 完整项目自动分析命令仍未实现，后续应进入 T006：`product version analyze` / `analyze-status`。
