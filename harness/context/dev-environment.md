# 研发环境信息

## 目的

本文件用于统一沉淀 NeoDev 当前仓库的研发环境、远程服务器和部署约定。
本地配置事实优先来自仓库中的公开配置文件；远程登录信息仅在明确需要联调或部署时使用。

## 来源

当前信息来源包括：

- `.env.example`
- `environment.yml`
- `docker-compose.yml`
- `Dockerfile`
- `pytest.ini`
- `src/config.example.json`
- 用户于 `2026-04-23` 直接提供的远程开发环境信息
- `2026-05-12` 远端部署验证：远端源码目录、Docker Compose 状态、离线 API 镜像构建与健康检查

## 使用规则

- 只有在任务涉及远程服务器、Docker 联调、数据库校验、远端部署时，才按需读取本文件。
- 本文件是研发协作口径和环境索引，不自动替代远端实时现状。
- 若后续确认环境发生变化，应同步更新本文件，并注明新的来源。

## 当前本地开发环境

- Conda 环境名：`NeoDev`
- Python 版本：`3.11`
- 本地 API 启动命令：`PYTHONPATH=src python -m uvicorn service.main:app --reload`
- Pytest 默认配置：`pytest.ini` 中声明 `pythonpath = src`，测试目录预期为 `tests/`

## 当前本地默认服务配置

- PostgreSQL：`postgresql://postgres:postgres@localhost:5432/neodev`
- Neo4j Bolt：`bolt://localhost:7687`
- Neo4j 用户：`neo4j`
- Neo4j 默认密码：`password123`
- OpenAI 配置入口：`.env` / `.env.example` 中的 `OPENAI_API_KEY`、`OPENAI_BASE`、`OPENAI_MODEL_CHAT`、`OPENAI_MODEL_EMBEDDING`
- 本地示例图数据库配置也可参考 `src/config.example.json`

## 当前 Docker 运行约定

- 入口文件：`docker-compose.yml`
- 主要容器名：`neodev-postgres`、`neodev-neo4j`、`neodev-api`、`neodev-web`
- API 容器内应用目录：`/app`
- API 默认暴露端口：容器内 `8000`
- 数据卷用途：
  - `repo_data` 对应仓库克隆目录
  - `sandbox_data` 对应 agent sandbox 目录
  - `doc_data` 对应需求文档目录

## 当前远程开发环境

- SSH 主机：`10.50.3.149`
- SSH 端口：`22`
- SSH 用户：`root`
- SSH 密码：`nKP422W[5f#{PPs#0e*r@RDG`
- 远程开发环境也是 Docker 部署，不按裸机 Python 进程方式维护
- 远端源码目录：`/root/neodev`
- 远端 `/root/neodev` 不保证是 Git 工作树，宿主机也不保证安装 `git`；不要依赖 `git pull` 或远端 Git 状态作为部署入口
- 涉及远端联调或排障时，优先使用 `docker ps`、`docker logs`、`docker exec`、`docker compose ps` 等方式核对运行状态
- 远端部署、重启或配置校验前，先确认容器名、Compose 项目名、挂载目录和环境变量来源，再执行变更
- 远端可能无法访问 Docker Hub；构建 API 镜像时若 `python:3.11-slim` 元数据拉取超时，应使用已有 `neodev-api-base:latest` 与离线运行时 Dockerfile 重建 `neodev-api:latest`
- 离线 API 构建只需要复制 `src/` 与 `docker/init.sql` 到 `/app`，示例基础 Dockerfile 可参考本地 `.deploy/Dockerfile.api.runtime`
- 远端发布应保留 `/root/neodev/.env` 与 Docker 数据卷，只替换源码目录并重建/重启 `api` 容器；PostgreSQL、Neo4j 和 Web 容器通常不需要重建

## 当前验证约定

- 若任务可以通过本地配置和源码完成，不要无关连接远端服务器。
- 若需要数据库校验，先确认使用的是本地 Compose 环境还是远端环境。
- 若需要远端部署，先核对远端 Docker / Compose 编排方式，再执行替换、重建或重启动作。
- 若需要查看远端 API、PostgreSQL 或 Neo4j 状态，优先从容器视角确认，而不是先假设宿主机直接暴露了进程。
- 远端 API 部署后至少验证：`docker compose ps`、`docker exec neodev-api python -m service.cli.main --json cli version-check`、`curl -fsS http://127.0.0.1/health`
- 涉及数据库迁移修复时，除健康检查外，还应从容器内检查已部署的 `/app/docker/init.sql` 和 PostgreSQL 实际 schema/index 状态
