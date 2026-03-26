# NeoDev

NeoDev 是一个面向研发团队的代码分析与产品研发管理平台，目标是把 **产品、版本、需求、提交、影响面分析、需求文档与 AI 协作** 串成一条更清晰的研发闭环。

当前项目由多个子系统组成：

- **Service**：基于 FastAPI 的后端服务，负责产品、项目、版本、需求、提交、影响面分析、AI 预处理等业务能力
- **GitNexus Parser**：基于 Tree-sitter 的多语言代码解析与图谱构建能力
- **Deep Agents**：基于 LangGraph / LangChain 的智能体框架与中间件体系
- **Web Frontend**：基于 React + TypeScript + Vite 的前端工作台

---

## 1. 项目定位

NeoDev 不是一个单点工具，而是一个正在演进中的研发工作平台。

它当前主要关注这些方向：

- 产品与版本管理
- 需求管理与需求树
- 提交同步与关联
- 影响面分析
- AI 辅助需求文档生成与编辑
- Agent 驱动的上下文协作能力

一句话理解：

> **NeoDev = 面向研发团队的 AI 原生需求—版本—代码闭环平台**

---

## 2. 项目结构

```text
neodev/
├─ src/
│  ├─ service/            # FastAPI 后端
│  ├─ gitnexus_parser/    # 多语言解析与图谱构建
│  └─ deepagents/         # 智能体框架与中间件
├─ web/                   # React + TypeScript 前端
├─ tests/                 # 后端/部分集成测试
├─ docs/                  # 设计文档、执行文档、专项说明
├─ docker/                # Docker 与部署相关文件
├─ Dockerfile
├─ docker-compose.yml
├─ environment.yml
└─ .env.example
```

---

## 3. 核心能力概览

### 后端 Service
后端当前已经覆盖多个业务域，包括：

- 产品管理（products）
- 项目管理（projects / repos）
- 版本管理（versions / product_versions）
- 需求管理（requirements / product_requirements）
- Bug 管理（product_bugs）
- 提交同步与查询（commits / sync）
- 影响面分析（impact）
- 需求文档（requirement_docs）
- Agent 会话与上下文（agent）
- 解析与预处理（parse / preprocess）

### 前端 Web
前端提供面向产品与研发过程的页面工作台，包括：

- 产品列表与产品工作台
- 产品项目详情页
- 版本视图与工作区
- 需求树与需求文档页
- 报告页
- 影响面分析相关页面

### 需求文档工作流
目前 NeoDev 的一个重要方向是：

- 文档生成
- 文档编辑
- diff / review
- 版本历史
- 拆分建议
- 子级文档生成
- 与 Agent 会话联动

这也是当前项目中最值得持续打磨的一条主工作流之一。

---

## 4. 技术栈

### 后端
- Python 3.11
- FastAPI
- psycopg2
- PostgreSQL + pgvector
- Neo4j（可选）
- Tree-sitter

### 前端
- React 18
- TypeScript
- Vite
- Vitest

### AI / Agent
- LangChain
- LangGraph
- OpenAI-compatible LLM 接口

---

## 5. 本地开发

### 5.1 创建 Python 环境

使用 Conda：

```bash
conda env create -f environment.yml
conda activate neodev
```

或根据 `src/requirements.txt` 自行安装依赖。

### 5.2 启动后端

在仓库根目录执行：

```bash
PYTHONPATH=src uvicorn service.main:app --reload
```

默认服务地址：

- API: <http://localhost:8000>

### 5.3 启动前端

```bash
cd web
npm install
npm run dev
```

默认开发地址：

- Web: <http://localhost:5173>

前端会将 `/api` 请求代理到本地后端。

---

## 6. Docker 运行

如需启动完整栈：

```bash
docker compose up -d --build
```

停止：

```bash
docker compose down
```

清理卷：

```bash
docker compose down -v
```

---

## 7. 测试

### 后端测试

```bash
pytest
```

运行单个文件：

```bash
pytest tests/test_api_requirements.py -q
```

### 前端测试

```bash
cd web
npm run test:run
```

### 前端构建验证

```bash
cd web
npm run build
```

---

## 8. 配置说明

主要环境变量来自仓库根目录的 `.env` 文件。

典型配置包括：

- `OPENAI_API_KEY`
- `OPENAI_BASE`
- `OPENAI_MODEL_CHAT`
- `POSTGRES_*`
- `NEO4J_*`
- `REPO_CLONE_BASE`
- `AI_ANALYSIS_MAX_WORKERS`

建议从：

- `.env.example`

复制并修改，不要提交真实密钥。

---

## 9. 当前开发约束

为了让项目持续可维护，当前建议遵循以下原则：

- 以最小可用单元推进改动
- 一个提交只解决一个明确问题
- 避免无关重构与顺手修改
- 后端尽量遵循 `router -> service -> repository -> tests`
- 前端尽量遵循 `api/client -> page/component -> tests`
- 优先补齐验证，再扩大范围

---

## 10. 仓库内推荐阅读顺序

如果你第一次进入这个仓库，建议按下面顺序阅读：

1. `README.md`
2. `CLAUDE.md`
3. `AGENTS.md`
4. `docs/` 下的相关设计文档
5. `src/service/routers/api.py`
6. `web/src/pages/product/` 下主要页面

---

## 11. 后续方向

NeoDev 当前仍处于持续演进阶段。后续重点会集中在：

- 强化版本驱动的产品主线
- 打磨需求文档工作流
- 增强提交、需求、版本之间的闭环关系
- 建立更适合 Agent 协作开发的工程机制

---

## 12. 说明

本 README 的目标是帮助开发者快速理解：

- 这个项目是什么
- 当前核心能力有哪些
- 如何跑起来
- 从哪里开始读
- 当前工程协作的基本约束是什么

如果项目后续继续收敛主线或调整开发方式，README 也应同步更新。
