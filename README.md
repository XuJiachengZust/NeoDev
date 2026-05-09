# NeoDev SP

NeoDev SP 是面向 AI 软件工程的一人团队工作台。它把产品目标、研发文档、代码仓库、分支图谱和 AI 协作规范连接起来，让个人在借助 AI 提升产出速度的同时，仍然保留可追踪、可复盘、可验证的研发秩序。

这个仓库提供 NeoDev SP 的后端服务、轻量 CLI、代码图谱解析器、研发知识插件示例和 Docker 部署资产。核心目标不是单次生成代码，而是让需求、文档、代码事实、分支状态和变更影响可以被持续管理。

## 产品理念

NeoDev SP 的产品意义，是为 AI 时代的一人团队提供一套以文档和规范为中心的研发秩序。

AI 正在改变软件工程的生产方式。个人的产出能力被显著放大，过去需要多人协作完成的需求梳理、方案比较、执行推进和结果检查，现在越来越多可以由一个人在 AI 辅助下完成。但能力被放大之后，新的瓶颈不再只是“能不能做出来”，而是“能不能持续做对、做稳、做得可追踪”。

NeoDev SP 要解决的正是这个持续性问题：让 OPT（One-Person Team，一人团队）在 AI 软件工程中，不只是更快地产出，而是能围绕清晰目标、稳定文档、明确规范和可追踪结果持续演进。

### AI 软件工程需要新的秩序

AI 让软件工程从“人直接完成大量工作”，转向“人负责判断和约束，AI 辅助完成大量过程性工作”。

这种变化带来了明显机会：

- 一个人可以承担过去多个角色才能推进的工作。
- 想法到结果的周期被大幅缩短。
- 探索、生成、修改和验证的成本下降。
- 小团队甚至个人也能尝试更复杂的产品目标。

但它也带来新的风险：

- 产出变快，方向更容易漂移。
- 对话变多，决策依据更容易丢失。
- 结果变多，人与 AI 都更难保持上下文一致。
- 局部任务完成了，但整体目标可能已经被稀释。
- 一个人越依赖 AI，越需要一种能管理 AI 协作的秩序。

因此，AI 软件工程的核心问题不只是“如何使用 AI 提高效率”，而是“如何让 AI 在清晰目标和稳定规范下提高效率”。

### OPT 是新的组织形态

OPT 不是简单的“一个人做所有事”，而是一种被 AI 放大的个人组织形态。

在 OPT 中，一个人需要同时承担多种责任：判断方向、定义问题、控制范围、组织执行、检查结果、复盘过程，并保持长期连续性。

AI 可以帮助完成很多工作，但不能自动承担最终判断。AI 可以生成建议、整理信息、推动执行，但它不知道什么才是这个产品真正应该坚持的目标，也不会天然记住每一次变化背后的取舍。

所以，OPT 的关键能力不是“一个人加 AI 可以做多少事”，而是“一个人能否把 AI 纳入一套稳定的工作方式”。

NeoDev SP 的意义就在这里：它帮助一人团队建立接近小型研发组织的秩序，让个人不再完全依赖记忆和临时对话维持项目连续性。

### Spec Coding 解决开始问题，NeoDev SP 解决持续问题

Spec Coding 的核心价值，是让 AI 在产出之前先理解规格。它强调先明确目标、范围、约束和完成标准，再让 AI 参与执行。这比“直接给 AI 一个模糊提示，然后边做边修”更稳定。

但在真实项目中，只把规格写在开始阶段仍然不够。

因为项目会持续变化：需求会被调整，判断会被更新，产出会不断累积，AI 会参与多个阶段，一个人也会在不同时间重新接手同一件事。

这时，Spec Coding 面临的真正挑战变成：规格如何不变成旧文档？AI 的产出如何持续回到规格？后续变化如何知道影响了哪些目标？一个人如何在长期迭代中保持判断一致？

NeoDev SP 对 Spec Coding 的意义，是把规格从“开始前的说明”升级为“贯穿全过程的秩序”。

它强调：

- 规格不是一次性输入，而是持续约束。
- 文档不是事后记录，而是过程中心。
- 规范不是个人习惯，而是 AI 协作边界。
- 实际产出不是孤立结果，而要和目标、需求、设计判断保持关联。
- 复盘不是结束动作，而是下一轮迭代的起点。

因此，NeoDev SP 不是替代 Spec Coding，而是把 Spec Coding 推向更完整的产品工程状态：从“按照规格做一次”，走向“围绕规格持续演进”。

### 文档、规范和代码的关联是长期稳定器

现有 AI 研发流程的痛点，往往不是某一次产出失败，而是过程失去连续性。

常见问题包括：

- 文档写过，但后续产出没有持续对齐。
- 代码改了，但不知道对应哪个目标或需求。
- AI 完成了局部任务，但不知道是否破坏了整体意图。
- 变化发生了，但没有沉淀为新的判断依据。
- 复盘时只能翻聊天记录，无法还原完整过程。

NeoDev SP 把文档、规范和代码关联起来，核心价值是让 AI 研发重新具备可追踪性。

这种关联带来的不是复杂管理，而是几个关键优势：

- 目标不悬空：每一项实际产出都能回到对应目标。
- 变化不失忆：每一次调整都能留下依据和影响。
- AI 不跑偏：AI 的协作被文档和规范约束，而不是只被即时对话牵引。
- 复盘不靠猜：过程可以被还原，经验可以被积累。
- 一人团队不被细节淹没：个人可以把精力放在方向、取舍和判断上。

这就是 NeoDev SP 区别于普通 AI 工具的地方：它关注的不是单次生成能力，而是长期协作能力。

### 以文档和规范为中心

AI 让软件工程更快，但越快越需要秩序。

在传统流程里，文档常常被视为补充材料：先做事，做完再补说明。但在 AI 软件工程中，这种方式会带来更大的风险。因为 AI 的速度越快，偏离目标的速度也越快；如果没有文档和规范作为中心，个人很容易被零散产出推着走。

NeoDev SP 主张把文档和规范放在研发过程中心：

- 先明确为什么做，再决定做什么。
- 先定义完成标准，再判断是否完成。
- 先沉淀关键取舍，再推动后续变化。
- 先建立规范边界，再让 AI 批量辅助。
- 每次变化都回到文档中沉淀，而不是只留在对话里。

这不是增加负担，而是减少长期混乱。对一人团队来说，文档和规范承担了一部分“团队组织能力”：它们帮助个人保持方向，帮助 AI 理解边界，也帮助未来的自己接续过去的工作。

### 产品定位

NeoDev SP 不是传统项目管理工具，也不是单纯的 AI 生成工具。

它更适合被理解为：面向 AI 软件工程的一人团队工作台。

它连接四件事：

- 产品目标：为什么做，服务谁，解决什么问题。
- 研发文档：要达成什么结果，如何判断完成。
- 工作规范：AI 和人如何协作，如何避免偏离。
- 实际产出：已经完成了什么，和目标是否一致。

通过这四件事的连接，NeoDev SP 帮助 OPT 从“一个人和 AI 临时协作”，升级为“一个人管理多个 AI 助手持续推进产品”。

### 最终价值

NeoDev SP 要回答的问题不是：AI 能不能让一个人做得更快。

它要回答的是：当 AI 让一个人拥有接近团队的产出能力时，这个人如何拥有接近团队的秩序、记忆、规范和复盘能力。

所以，NeoDev SP 的长期意义可以概括为一句话：

让一人团队在 AI 软件工程时代，不只是拥有更强的生产力，也拥有能够驾驭这种生产力的产品工程秩序。

## 核心能力

- 产品与版本管理：维护产品、版本、项目仓库和版本到分支的绑定关系。
- 代码仓库登记：支持通过远程 Git URL 或服务端本地路径登记项目。
- 分支代码图谱：解析仓库代码结构，生成文件、符号、调用、继承、导入等代码事实，并写入 Neo4j。
- 文档绑定与导入：把产品文档仓库绑定到产品版本，扫描并导入受控文档。
- DocChange 流程：登记文档变更，追踪实现状态，并关联代码变更。
- 图谱查询：按产品、版本、项目和分支查询实体上下文、关系链和影响范围。
- Git 一致性检查：检查提交与 DocChange 的关联，识别需要处理的危险提交。
- CLI 与插件协同：通过 `neodev` CLI 和 `plugins/neodev-rd-knowledge` 里的技能、命令、工作流约束协作。

## 架构概览

NeoDev SP 由以下几层组成：

- API 服务：`src/service/main.py` 启动 FastAPI 应用，统一暴露产品、项目、仓库、解析、同步和 CLI 执行接口。
- Router 层：`src/service/routers/` 处理 HTTP 传输协议和请求响应模型。
- Service 层：`src/service/services/` 承载产品版本、分支分析、文档导入、图谱查询、Git 检查等业务流程。
- Repository 层：`src/service/repositories/` 负责 PostgreSQL 持久化访问。
- 代码解析器：`src/gitnexus_parser/` 基于 tree-sitter 解析多语言代码，并构建可写入图数据库的代码事实。
- CLI 客户端：`src/service/cli/` 实现 `neodev` 命令行入口，可调用远程 API 服务。
- 插件与技能：`plugins/neodev-rd-knowledge/` 提供 Codex/NeoSuperpower 工作流、命令说明、文档校验脚本和插件元数据。
- 部署资产：`docker-compose.yml`、`Dockerfile`、`docker/` 提供 PostgreSQL、Neo4j、API 和 Web 反向代理部署配置。

运行时主要依赖：

- PostgreSQL + pgvector：保存产品、项目、文档、DocChange、图谱元数据和 CLI 业务状态。
- Neo4j：保存分支代码图谱和人工图谱事实。
- OpenAI 兼容接口：用于文档语义搜索、摘要或 LLM 辅助能力，可通过环境变量替换为内网兼容服务。

## 目录结构

```text
.
├── src/
│   ├── service/              # FastAPI 服务、CLI、业务服务、仓储、迁移入口
│   ├── deepagents/           # Agent graph、middleware 和 backend adapter
│   └── gitnexus_parser/      # 代码解析、符号表、调用/导入/继承关系解析和图谱写入
├── plugins/
│   └── neodev-rd-knowledge/  # NeoDev 研发知识插件、技能、命令和工作流契约
├── docs/                     # PRD、技术设计、计划和验收材料
├── harness/                  # 仓库级协作规则和上下文
├── tests/                    # pytest 测试
├── docker/                   # 镜像、初始化 SQL、离线部署脚本和 Nginx 配置
├── docker-compose.yml        # 本地/服务端容器编排
├── environment.yml           # Conda 环境定义
└── neodev.py                 # 不安装 shim 时的本地 CLI 调用入口
```

## 快速开始

### 1. 创建 Python 环境

```powershell
conda env create -f environment.yml
conda activate NeoDev
```

`environment.yml` 使用 Python 3.11，并通过 `src/requirements.txt` 安装 FastAPI、uvicorn、pytest、tree-sitter、Neo4j、LangChain/LangGraph 等依赖。

### 2. 配置环境变量

复制 `.env.example` 为本地 `.env`，按需修改：

```powershell
Copy-Item .env.example .env
```

常用变量：

```text
POSTGRES_PORT=5432
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
NEO4J_HTTP_PORT=7474
NEO4J_BOLT_PORT=7687
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE=
OPENAI_MODEL_CHAT=gpt-4o-mini
OPENAI_MODEL_EMBEDDING=text-embedding-3-small
WEB_PORT=80
```

服务端运行时还会使用：

- `DATABASE_URL`：PostgreSQL 连接串。
- `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`：Neo4j 连接配置。
- `REPO_CLONE_BASE`：服务端克隆远程仓库的目录。
- `AGENT_SANDBOX_ROOT`：Agent 执行沙箱目录。
- `ALLOWED_BASE_PATHS`：可选路径白名单；设置后，本地路径必须位于白名单下。

不要提交真实密钥或内网部署地址。远程服务地址、部署细节和凭据应放在本地环境或 `harness/context/dev-environment.md` 这类受控上下文中。

### 3. 启动依赖服务

本地完整栈：

```powershell
docker compose up -d --build
```

默认包含：

- PostgreSQL：`localhost:5432`，数据库 `neodev`。
- Neo4j HTTP：`localhost:7474`。
- Neo4j Bolt：`localhost:7687`。
- Web/Nginx：由 `WEB_PORT` 控制，默认 `80`。

如需重建本地数据库卷：

```powershell
docker compose down -v
docker compose up -d --build
```

### 4. 启动 API 服务

如果只本地启动 API：

```powershell
$env:PYTHONPATH="src"
python -m uvicorn service.main:app --reload
```

健康检查：

```powershell
curl http://127.0.0.1:8000/health
```

FastAPI 文档默认位于：

```text
http://127.0.0.1:8000/docs
```

## API 入口

API 当前注册的主要路由：

- `GET /health`：服务健康检查。
- `/cli/execute`：远程执行 CLI 命令。
- `/repos/*`：仓库分支查询、路径解析、远程仓库确保本地可用。
- `/parse/`：解析代码仓库并生成图谱数据。
- `/projects/*`：项目创建、查询、更新、删除、分支查询和图谱刷新。
- `/products/*`：产品创建、查询、更新、删除以及产品-项目关联。
- `/products/{product_id}/versions/*`：产品版本管理、版本-分支绑定和解绑。

Router 只处理传输层逻辑。业务规则应放在 `src/service/services/`，数据库访问应放在 `src/service/repositories/`。

## CLI 使用

安装远程 CLI shim 后可直接使用：

```powershell
neodev config show
neodev cli version-check --json
```

切换远程服务：

```powershell
neodev config set-server http://<neodev-api-host>
```

如果尚未安装 shim，可在仓库内直接调用：

```powershell
python neodev.py --server http://<neodev-api-host> cli version-check --json
```

### 常用命令

产品与版本：

```powershell
neodev product create --name <product_name> --product-code <product_code> --json
neodev product version create --product-code <product_code> --version-name <version_name> --json
neodev product version show --product-code <product_code> --version-name <version_name> --json
```

项目登记与分支绑定：

```powershell
neodev project create --name <project_name> --repo-url <repo_url> --json
neodev product version bind-branch --product-code <product_code> --version-name <version_name> --project-name <project_name> --branch <branch> --json
```

刷新分支代码图谱：

```powershell
neodev project refresh-graph --project-name <project_name> --branch <branch> --json
neodev project init-status --project-name <project_name> --branch <branch> --json
```

文档绑定、扫描和导入：

```powershell
neodev doc binding create --product-code <product_code> --project-name <doc_project_name> --branch <branch> --json
neodev doc binding list --product-code <product_code> --json
neodev doc scan --doc-binding-id <doc_binding_id> --json
neodev doc import --doc-binding-id <doc_binding_id> --json
```

DocChange：

```powershell
neodev doc change register --document-id <document_id> --json
neodev doc change show --doc-change-id <doc_change_id> --json
neodev doc change mark-implemented --doc-change-id <doc_change_id> --json
```

图谱查询：

```powershell
neodev graph impact --doc-change-id <doc_change_id> --json
neodev graph entity-context --product-code <product_code> --version-name <version_name> --project-name <project_name> --branch-name <branch> --entity-id <node_id> --json
neodev graph get-chain --product-code <product_code> --version-name <version_name> --project-name <project_name> --branch-name <branch> --file-path <path> --json
```

Git 检查：

```powershell
neodev git verify-doc-change --doc-change-id <doc_change_id> --json
neodev git dangerous-commit list --json
neodev git dangerous-commit resolve --commit <commit_sha> --json
```

## 推荐工作流

### 代码仓库图谱

1. 创建产品和版本。
2. 登记代码仓库。
3. 将产品版本绑定到项目分支。
4. 刷新分支代码图谱。
5. 使用 `product version show` 获取低噪声导航信息。
6. 使用 `graph entity-context` 或 `graph get-chain` 查询代码事实。

示例：

```powershell
neodev product create --name NeoDev --product-code neodev --json
neodev product version create --product-code neodev --version-name v1 --json
neodev project create --name neodev-service --repo-url https://example.com/org/neodev.git --json
neodev product version bind-branch --product-code neodev --version-name v1 --project-name neodev-service --branch main --json
neodev project refresh-graph --project-name neodev-service --branch main --json
```

### 版本范围文档流程

1. 登记文档仓库为项目。
2. 创建产品文档绑定。
3. 扫描文档结构。
4. 导入文档 chunk 和 embedding。
5. 登记 DocChange。
6. 查询 DocChange 影响范围。
7. 实现后标记 DocChange 状态并执行 Git 一致性检查。

受控文档校验脚本：

```powershell
python plugins/neodev-rd-knowledge/validate_mvp_docs.py <docs_path>
python plugins/neodev-rd-knowledge/validate_obsidian_docs.py <docs_path>
```

## 代码图谱解析能力

`src/gitnexus_parser/` 负责把代码仓库转换为可查询图谱事实。当前依赖 tree-sitter，支持 Python、Java、Lua、C、C++、JavaScript、TypeScript、Go、Rust 等语言的基础解析。

主要处理内容：

- 文件和目录结构。
- 函数、类、方法等符号节点。
- 调用关系、继承关系、覆盖关系。
- import/use 关系解析。
- 可增量更新的分支快照和图谱写入。

解析结果会服务于版本-分支导航、实体上下文查询、影响分析和文档变更闭环。

## NeoDev 研发知识插件

`plugins/neodev-rd-knowledge/` 是 NeoDev SP 的协作层示例，包含：

- `workflows/core-workflows.json`：共享工作流契约。
- `skills/`：NeoSuperpower 工作流技能。
- `commands/`：面向 Codex/插件入口的命令说明。
- `validate_mvp_docs.py`、`validate_obsidian_docs.py`：文档规范校验脚本。
- `hooks/`：环境检查、Git 提交范围检查、DocChange trailer 检查等钩子配置。

日常使用时，优先通过 `neodev` CLI 读写 NeoDev 状态。不要绕过 CLI 直接写 PostgreSQL 或 Neo4j；直连数据库只用于排障定位。

## 测试

运行全部测试：

```powershell
pytest
```

运行单个测试文件：

```powershell
pytest tests/test_project_cli.py
```

测试覆盖范围包括：

- CLI 契约和远程执行。
- 产品、版本、项目、文档和图谱服务。
- PostgreSQL 初始化 SQL。
- Neo4j 分支图谱写入。
- 文档扫描、导入、DocChange 和语义搜索相关逻辑。
- 插件平台、文档校验脚本和环境 hook。

## 开发约定

- Python 使用 4 空格缩进。
- 模块、函数和变量使用 `snake_case`；类使用 `PascalCase`。
- Router 只处理 HTTP 传输；业务逻辑放在 Service；持久化访问放在 Repository。
- 配置形状以 `.env.example` 和 `src/config.example.json` 为公开参考。
- 不提交真实密钥、内网地址或本地环境文件。
- 涉及接口、字段、schema、跨层契约变更时，同步补充测试和文档。
- 变更完成后，能本地执行的检查不要只靠静态审查。

提交信息建议使用 Conventional Commit：

```text
feat: add graph entity context cli
fix: repair doc import status update
test: cover product version branch binding
docs: expand project readme
chore: update docker bootstrap config
```

## 部署说明

本仓库提供两类部署方式：

- 开发/本地验证：使用根目录 `docker-compose.yml` 构建并启动完整依赖。
- 镜像包/离线部署：使用 `docker/images/` 和 `docker/deploy-offline.sh` 相关资产。

根目录 compose 栈包含：

- `neodev-postgres`：PostgreSQL + pgvector，首次启动执行 `docker/init.sql`。
- `neodev-neo4j`：Neo4j 5 community，启用 APOC。
- `neodev-api`：FastAPI 服务。
- `neodev-web`：Nginx 入口。

本地数据库 schema 变更时，当前约定是更新 `docker/init.sql`，再重建 volume 验证初始化结果。
