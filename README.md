# NeoDev

NeoDev 是一个面向研发团队的 **AI 原生研发闭环平台**。它不只是提供代码分析、需求管理或 AI 助手能力，而是试图把 **需求、上下文、执行、证据、验收** 连接成一条可追踪的协作链路。

一句话理解：

> **NeoDev = 让团队不再靠转述和工具跳转推进研发，而是靠共享上下文与可审查结果推进研发。**

当前项目由多个子系统组成：

- **Service**：基于 FastAPI 的后端服务，负责产品、项目、版本、需求、提交、影响面分析、AI 预处理等业务能力
- **GitNexus Parser**：基于 Tree-sitter 的多语言代码解析与图谱构建能力
- **Deep Agents**：基于 LangGraph / LangChain 的智能体框架与中间件体系
- **Web Frontend**：基于 React + TypeScript + Vite 的前端工作台

---

## 1. 项目定位

NeoDev 不是一个单点工具，也不是“再做一个更强的 AI 编码助手”。

它更接近一个正在演进中的 **人机协作研发闭环平台**：把需求、版本、任务、代码、影响面、文档与 AI 协作串成一条更低损耗的研发主链路。

它当前主要关注这些方向：

- 产品与版本管理
- 需求管理与需求树
- 提交同步与关联
- 影响面分析
- AI 辅助需求文档生成与编辑
- Agent 驱动的上下文协作能力

一句话理解：

> **NeoDev = 面向研发团队的 AI 原生需求—版本—代码闭环平台**

### 1.1 为什么 NeoDev 存在

很多研发团队已经在使用 AI，但真实工作流仍然是割裂的：

- 需求在文档里
- 讨论在聊天里
- 任务在项目系统里
- 代码在仓库里
- 验收依据散落在评论、口头同步或截图里

结果是：AI 参与变多了，但上下文并没有自然汇聚，执行过程仍然依赖大量转述，结果也缺少可共享、可审查、可复用的证据链。

NeoDev 想解决的，正是这类 **碎片化、转述型、上下文高损耗** 的研发协作问题。

### 1.2 NeoDev 的核心价值

NeoDev 希望为研发团队提供几件更本质的能力：

- **共享上下文**：把需求、历史任务、代码模块、文档与相关结论聚合到同一条工作链路中
- **先计划再执行**：让 AI 协作不止停留在“直接生成”，而是先形成可审查的执行计划
- **结果附带证据**：让改动、依据、风险、未决项和验收入口一起出现，而不是只得到一句“已完成”
- **经验可沉淀复用**：把一次任务沉淀为后续可复用的组织资产，而不是做完即散

### 1.3 NeoDev 的主链路

NeoDev 重点支持这样一条研发主链路：

1. 明确目标、边界与验收标准
2. 自动或半自动聚合相关上下文
3. 先生成计划，再进入执行
4. 在执行过程中持续产出结果与证据
5. 由人完成关键判断、审查与放行
6. 将过程和结论沉淀为可复用资产

### 1.4 NeoDev 与传统工具 / 纯 AI 工具的区别

与传统项目管理或文档工具相比，NeoDev 不只记录状态，而更关注 **上下文如何进入执行、执行如何回到验收、结果如何形成复用资产**。

与纯 AI 工具相比，NeoDev 也不把价值停留在“更快生成”，而更强调：

- 人与 AI 在同一条链路中协作
- 结果天然可审查、可共享、可验收
- 关键判断仍由人做，AI 负责加速分析、规划与执行
- 一次任务的过程与证据能够沉淀为团队能力

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

## 12. 许可证

本项目当前采用：

- **GNU Affero General Public License v3.0（AGPL-3.0）**

这意味着：
- 允许使用、修改和分发
- 修改后的网络服务化使用也需要按 AGPL 要求提供对应源码
- 适合希望保持开源传染性、避免闭源服务化占便宜的场景

详情请见仓库根目录的 `LICENSE` 文件。

---

## 13. 说明

本 README 的目标是帮助开发者快速理解：

- 这个项目是什么
- 当前核心能力有哪些
- 如何跑起来
- 从哪里开始读
- 当前工程协作的基本约束是什么

如果项目后续继续收敛主线或调整开发方式，README 也应同步更新。
