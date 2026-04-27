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
- 涉及远端联调或排障时，优先使用 `docker ps`、`docker logs`、`docker exec`、`docker compose ps` 等方式核对运行状态
- 远端部署、重启或配置校验前，先确认容器名、Compose 项目名、挂载目录和环境变量来源，再执行变更

## 当前验证约定

- 若任务可以通过本地配置和源码完成，不要无关连接远端服务器。
- 若需要数据库校验，先确认使用的是本地 Compose 环境还是远端环境。
- 若需要远端部署，先核对远端 Docker / Compose 编排方式，再执行替换、重建或重启动作。
- 若需要查看远端 API、PostgreSQL 或 Neo4j 状态，优先从容器视角确认，而不是先假设宿主机直接暴露了进程。
