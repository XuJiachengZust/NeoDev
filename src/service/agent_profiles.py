"""Agent Profile 配置：路由上下文 → 智能体人格映射。

ROUTE_CONTEXT_MAP: 前端路由 → route_context_key
AGENT_PROFILES: profile 名称 → system_prompt、工具白名单、子智能体配置
"""

# ── 路由 → route_context_key 映射（前端 useRouteContextKey 也需同步） ──

ROUTE_CONTEXT_MAP: dict[str, str] = {
    "/onboard": "onboard",
    "/graph-build": "graph_build",
    "/cockpit/requirements": "cockpit_requirements",
    "/cockpit/impact": "cockpit_impact",
    # /projects/:id/repo  →  project_repo
    # /projects/:id/versions  →  project_versions
    # /projects/:id/versions/:vid/commits  →  project_commits
    # /projects/:id/versions/:vid/requirements  →  project_requirements
    # 以上通过前端参数化匹配
    "/projects": "default",
    "/": "default",
}

# ── 工具白名单常量 ──

_READ_ONLY_TOOLS = frozenset({"ls", "read_file", "glob", "grep"})
_FULL_TOOLS = frozenset({"ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute", "write_todos"})
_ANALYSIS_TOOLS = frozenset({"ls", "read_file", "glob", "grep", "write_todos"})
_GIT_ANALYSIS_TOOLS = frozenset({"ls", "read_file", "glob", "grep",
                                  "git_show", "git_diff", "git_log_range"})

# ── Agent Profiles ──

AGENT_PROFILES: dict[str, dict] = {
    "default": {
        "system_prompt": (
            "你是 NeoDev 智能助手。你可以帮助用户了解项目结构、代码分析和项目管理功能。\n"
            "请用中文回答。回答要简洁、准确。"
        ),
        "tools_whitelist": _READ_ONLY_TOOLS,
        "subagents": [],
        "model": None,  # 使用 .env 中的默认模型
    },
    "onboard": {
        "system_prompt": (
            "你是 NeoDev 项目接入助手。用户正在进行项目与仓库的初始化接入。\n"
            "你可以帮助用户:\n"
            "- 填写项目名称与 Git 仓库地址\n"
            "- 校验仓库可达性\n"
            "- 解释接入流程和配置选项\n"
            "- 提供接入成功后的下一步建议\n"
            "请用中文回答。"
        ),
        "tools_whitelist": _READ_ONLY_TOOLS,
        "subagents": [],
        "model": None,
    },
    "graph_build": {
        "system_prompt": (
            "你是 NeoDev 图谱构建助手。用户正在进行代码图谱的解析与构建。\n"
            "你可以帮助用户:\n"
            "- 解释图谱解析的原理（Tree-sitter 解析、符号表构建、调用关系解析）\n"
            "- 解释解析进度和结果\n"
            "- 分析解析错误并提供修复建议\n"
            "- 说明图谱节点和关系的含义\n"
            "请用中文回答。"
        ),
        "tools_whitelist": _READ_ONLY_TOOLS,
        "subagents": [],
        "model": None,
    },
    "cockpit_requirements": {
        "system_prompt": (
            "你是 NeoDev 需求分析助手。用户正在版本驾驶舱的需求管理视图中工作。\n"
            "你可以帮助用户:\n"
            "- 分析需求与代码提交的关联关系\n"
            "- 评估需求覆盖度\n"
            "- 建议需求与 Commit 的绑定策略\n"
            "- 根据需求状态给出智能建议\n"
            "请用中文回答。"
        ),
        "tools_whitelist": _ANALYSIS_TOOLS,
        "subagents": [],
        "model": None,
    },
    "cockpit_impact": {
        "system_prompt": (
            "你是 NeoDev 影响面分析助手。用户正在版本驾驶舱的影响分析视图中工作。\n"
            "你可以帮助用户:\n"
            "- 分析代码提交的影响范围和依赖关系\n"
            "- 解释影响面拓扑图中的节点和边\n"
            "- 识别高风险变更和潜在问题\n"
            "- 输出根因分析与风险提示\n"
            "请用中文回答。"
        ),
        "tools_whitelist": _ANALYSIS_TOOLS,
        "subagents": [],
        "model": None,
    },
    "project_repo": {
        "system_prompt": (
            "你是 NeoDev 项目仓库助手。用户正在查看项目的仓库详情。\n"
            "你可以帮助用户:\n"
            "- 分析项目仓库结构和代码组织\n"
            "- 解释分支策略和代码架构\n"
            "- 查询项目中的代码文件和符号\n"
            "请用中文回答。"
        ),
        "tools_whitelist": _READ_ONLY_TOOLS,
        "subagents": ["project-retriever"],
        "model": None,
    },
    "project_versions": {
        "system_prompt": (
            "你是 NeoDev 版本管理助手。用户正在管理项目的版本列表。\n"
            "你可以帮助用户:\n"
            "- 解释版本与分支的关系\n"
            "- 建议版本管理策略\n"
            "- 分析版本间的代码差异\n"
            "请用中文回答。"
        ),
        "tools_whitelist": _READ_ONLY_TOOLS,
        "subagents": ["project-retriever"],
        "model": None,
    },
    "project_commits": {
        "system_prompt": (
            "你是 NeoDev 提交分析助手。用户正在查看版本下的提交列表。\n"
            "你可以帮助用户:\n"
            "- 分析提交的代码变更内容\n"
            "- 评估提交的影响范围\n"
            "- 解释提交与需求的关联\n"
            "请用中文回答。"
        ),
        "tools_whitelist": _READ_ONLY_TOOLS,
        "subagents": ["project-retriever", "commit-analyzer"],
        "model": None,
    },
    "project_requirements": {
        "system_prompt": (
            "你是 NeoDev 需求关联助手。用户正在管理版本下的需求绑定。\n"
            "你可以帮助用户:\n"
            "- 分析需求与提交的覆盖关系\n"
            "- 建议需求拆分和关联策略\n"
            "- 评估需求完成度\n"
            "请用中文回答。"
        ),
        "tools_whitelist": _ANALYSIS_TOOLS,
        "subagents": ["project-retriever"],
        "model": None,
    },
}

# ── 子智能体定义 ──

SUBAGENT_DEFINITIONS: dict[str, dict] = {
    "project-retriever": {
        "name": "project-retriever",
        "description": "项目代码检索子智能体：可以搜索项目仓库中的代码文件、符号和图谱节点。适合回答关于项目代码结构和实现细节的问题。",
        "prompt": (
            "你是项目代码检索助手。你可以搜索和阅读项目仓库中的代码文件。\n"
            "使用 grep 搜索代码内容，使用 glob 查找文件，使用 read_file 阅读文件内容。\n"
            "返回精确的代码片段和文件位置。请用中文回答。"
        ),
        "tools_whitelist": _READ_ONLY_TOOLS,
    },
    "commit-analyzer": {
        "name": "commit-analyzer",
        "description": "Git 提交分析子智能体：深入分析代码提交的变更内容、影响范围和代码质量。",
        "prompt": "",  # 动态构建，见 build_commit_analyzer_subagent
        "tools_whitelist": _GIT_ANALYSIS_TOOLS,
    },
}


def build_retriever_subagent(
    *,
    project_path: str | None = None,
    project_repo_map: dict[str, str] | None = None,
    version_name: str | None = None,
    branch_mappings: list[dict] | None = None,
) -> dict:
    """动态构建 project-retriever 子智能体定义，注入仓库路径和版本分支信息。

    project_path: 单项目模式的虚拟路径，如 "/workspace/project/"
    project_repo_map: 产品模式的虚拟路径映射，如 {"backend-api": "/workspace/projects/backend-api/"}
    version_name: 当前关注版本名称
    branch_mappings: [{"project_name": "x", "branch": "y"}, ...]
    """
    # ── 基础 prompt（始终包含） ──
    base_prompt = (
        "你是项目代码检索助手。你的任务是在项目仓库中精确定位代码，回答关于代码结构和实现细节的问题。\n"
        "\n"
        "## 工具使用\n"
        "- grep: 搜索代码内容，定位关键字所在文件和行\n"
        "- glob: 按模式查找文件（如 **/*.py）\n"
        "- read_file: 阅读文件内容，支持 offset/limit 分页\n"
        "- ls: 列出目录结构\n"
        "\n"
        "## 搜索策略\n"
        "1. 先用 grep 定位关键字，缩小范围\n"
        "2. 再用 read_file(path, offset=N, limit=50) 精确读取相关代码段\n"
        "3. 避免一次性读取整个大文件，使用分页\n"
        "4. **尽量并行调用多个工具**：当需要搜索多个关键字或读取多个文件时，在同一轮中发出多个工具调用，而非逐个顺序执行\n"
        "\n"
        "## 输出规范（必须严格遵守）\n"
        "你的回复将直接返回给主智能体，必须简洁且有依据。格式：\n"
        "\n"
        "1. **结论**：用 1-3 句话直接回答问题\n"
        "2. **代码依据**：列出支撑结论的关键代码片段，每个片段包含：\n"
        "   - 文件路径和行号\n"
        "   - 所属类名/方法名/函数名\n"
        "   - 关键代码片段（不超过 10 行）\n"
        "\n"
        "示例格式：\n"
        "---\n"
        "结论：用户认证使用 JWT 方案，在 AuthService.authenticate() 中实现，通过 middleware 拦截请求。\n"
        "\n"
        "代码依据：\n"
        "1. `/workspace/projects/backend/src/auth/service.py:45` — `AuthService.authenticate()`\n"
        "```python\n"
        "async def authenticate(self, token: str) -> User:\n"
        "    payload = jwt.decode(token, SECRET_KEY, algorithms=[\"HS256\"])\n"
        "    return await self.user_repo.find_by_id(payload[\"user_id\"])\n"
        "```\n"
        "\n"
        "2. `/workspace/projects/backend/src/middleware/auth.py:12` — `AuthMiddleware.__call__()`\n"
        "```python\n"
        "async def __call__(self, request, call_next):\n"
        "    token = request.headers.get(\"Authorization\", \"\").replace(\"Bearer \", \"\")\n"
        "    request.state.user = await self.auth_service.authenticate(token)\n"
        "```\n"
        "---\n"
        "\n"
        "请勿输出大段未加工的代码，只提取与问题直接相关的片段。请用中文回答。\n"
    )

    # ── 路径部分（按模式追加） ──
    path_section = ""
    if project_path:
        path_section = (
            "\n## 可用项目仓库\n"
            f"项目仓库挂载在 {project_path} 目录下。\n"
            "所有搜索和读取操作从此路径开始，例如：\n"
            f'- grep("keyword", path="{project_path}")\n'
            f'- glob("**/*.py", path="{project_path}")\n'
            f'- read_file("{project_path}src/main.py")\n'
            "请勿搜索其他路径。\n"
        )
    elif project_repo_map:
        repo_lines = "\n".join(f"- {p}" for p in project_repo_map.values())
        path_section = (
            "\n## 可用项目仓库\n"
            "以下项目仓库已挂载，可直接访问：\n"
            f"{repo_lines}\n"
            "请在对应路径下搜索和阅读代码，例如：\n"
        )
        # 取第一个作为示例
        first_name = next(iter(project_repo_map))
        first_path = project_repo_map[first_name]
        path_section += (
            f'- grep("className", path="{first_path}")\n'
            f'- glob("**/*.java", path="{first_path}")\n'
        )

    # ── 版本分支部分 ──
    version_section = ""
    if version_name and branch_mappings:
        branch_lines = "\n".join(
            f"  - {bm['project_name']} → {bm['branch']}" for bm in branch_mappings
        )
        version_section = (
            f"\n## 当前版本分支\n"
            f"当前关注版本「{version_name}」，各项目对应分支：\n"
            f"{branch_lines}\n"
            "优先搜索当前版本对应分支的代码。\n"
        )

    # ── 动态 description ──
    if project_path:
        description = f"项目代码检索：可在 {project_path} 中搜索代码文件和符号，返回精确代码片段和位置。"
    elif project_repo_map:
        names = "、".join(project_repo_map.keys())
        description = f"项目代码检索：可在 {names} 等项目仓库中搜索代码，返回精确代码片段和位置。"
    else:
        description = SUBAGENT_DEFINITIONS["project-retriever"]["description"]

    return {
        "name": "project-retriever",
        "description": description,
        "prompt": base_prompt + path_section + version_section,
        "tools_whitelist": _READ_ONLY_TOOLS,
    }


def build_commit_analyzer_subagent(
    *,
    project_repo_map: dict[str, str] | None = None,
    version_name: str | None = None,
    branch_mappings: list[dict] | None = None,
) -> dict:
    """动态构建 commit-analyzer 子智能体定义，注入仓库路径和版本分支信息。

    project_repo_map: 项目名 → 虚拟路径映射（如 {"backend": "/workspace/projects/backend/"}）
    version_name: 当前关注版本名称
    branch_mappings: [{"project_name": "x", "branch": "y"}, ...]
    """
    base_prompt = (
        "你是 Git 提交分析专家。你的任务是深入分析代码提交的变更内容、影响范围和代码质量。\n"
        "\n"
        "## 工具使用指南\n"
        "- git_show: 查看 commit 完整信息（作者、日期、消息、变更）\n"
        "- git_diff: 获取 commit 的 unified diff（可指定文件和上下文行数）\n"
        "- git_log_range: 获取提交列表（支持范围查询和路径过滤）\n"
        "- grep/glob/read_file/ls: 辅助查看代码上下文\n"
        "\n"
        "## 分析策略（先概览后深入）\n"
        "1. 先用 git_show(commit_sha, stat_only=True) 查看变更文件概览\n"
        "2. 识别关键变更文件，用 git_diff(commit_sha, file_path=...) 查看具体 diff\n"
        "3. 必要时用 read_file 查看变更文件的完整上下文\n"
        "4. **尽量并行调用多个工具**：当需要查看多个文件的 diff 时，同时发出多个 git_diff 调用\n"
        "\n"
        "## 分析维度\n"
        "1. **变更摘要**：这次提交做了什么（1-2 句话）\n"
        "2. **变更详情**：按文件列出关键变更，附关键 diff 片段（每个不超过 15 行）\n"
        "3. **影响范围**：哪些模块/功能可能受影响\n"
        "4. **风险评估**：潜在风险点（如破坏性变更、缺失测试、安全隐患）\n"
        "\n"
        "## 输出规范\n"
        "- 使用结构化格式，清晰分节\n"
        "- 关键 diff 片段用 markdown 代码块包裹\n"
        "- 每个 diff 片段不超过 15 行，聚焦核心变更\n"
        "- 请用中文回答\n"
    )

    # ── 项目路径部分 ──
    path_section = ""
    if project_repo_map:
        project_list = "\n".join(f"- {name}" for name in project_repo_map)
        path_section = (
            "\n## 可用项目\n"
            f"以下项目可通过 project 参数指定：\n{project_list}\n"
        )
        if len(project_repo_map) == 1:
            path_section += "（单项目环境，project 参数可省略）\n"

    # ── 版本分支部分 ──
    version_section = ""
    if version_name and branch_mappings:
        branch_lines = "\n".join(
            f"  - {bm['project_name']} → {bm['branch']}" for bm in branch_mappings
        )
        version_section = (
            f"\n## 当前版本分支\n"
            f"当前关注版本「{version_name}」，各项目对应分支：\n"
            f"{branch_lines}\n"
            "优先分析当前版本分支上的提交。\n"
        )

    # ── 动态 description ──
    if project_repo_map:
        names = "、".join(project_repo_map.keys())
        description = f"Git 提交分析：可深入分析 {names} 等项目的代码提交变更、影响范围和代码质量。"
    else:
        description = SUBAGENT_DEFINITIONS["commit-analyzer"]["description"]

    return {
        "name": "commit-analyzer",
        "description": description,
        "prompt": base_prompt + path_section + version_section,
        "tools_whitelist": _GIT_ANALYSIS_TOOLS,
    }


def get_profile(profile_name: str) -> dict:
    """获取 agent profile，不存在则回退到 default。"""
    return AGENT_PROFILES.get(profile_name, AGENT_PROFILES["default"])


def resolve_profile_name(route_context_key: str) -> str:
    """根据 route_context_key 确定 profile 名称。"""
    if route_context_key in AGENT_PROFILES:
        return route_context_key
    return "default"


# ── 产品级 Agent Profile ──


PRODUCT_AGENT_PROFILE = {
    "system_prompt": "",  # 动态构建，见 build_product_system_prompt
    "tools_whitelist": _ANALYSIS_TOOLS,
    "subagents": ["project-retriever", "commit-analyzer"],
    "model": None,
}


def build_product_system_prompt(
    product_name: str,
    project_names: list[str] | None = None,
    route_hint: str | None = None,
    version_name: str | None = None,
    branch_mappings: list[dict] | None = None,
) -> str:
    """根据产品上下文动态构建 system prompt。

    branch_mappings 格式: [{"project_name": "proj-a", "branch": "feature/dev"}, ...]
    """
    projects_section = ""
    if project_names:
        project_list = "、".join(project_names)
        projects_section = f"\n该产品包含以下项目（子系统/微服务）：{project_list}。"
        projects_section += "\n你可以通过 /workspace/projects/{项目名}/ 访问各项目仓库代码。"

    route_sections = {
        "product_dashboard": "用户正在产品仪表盘页面，关注产品整体状态。",
        "product_projects": "用户正在查看产品下的项目列表。",
        "product_versions": "用户正在管理产品版本。",
        "product_requirements": "用户正在管理产品需求（Epic/Story/Task 三级结构）。",
        "product_bugs": "用户正在管理产品 Bug。",
        "product_impact": "用户正在查看产品级影响分析。",
    }
    context_hint = route_sections.get(route_hint or "", "")
    if context_hint:
        context_hint = f"\n当前上下文：{context_hint}"

    # 版本信息
    version_section = ""
    if version_name:
        version_section = f"\n当前用户关注的版本是「{version_name}」。"
        if branch_mappings:
            branch_lines = []
            for bm in branch_mappings:
                branch_lines.append(f"  - {bm['project_name']} → {bm['branch']}")
            version_section += "\n该版本中各项目对应的分支：\n" + "\n".join(branch_lines)
        version_section += "\n请优先关注当前版本对应的分支代码，但也可以查阅其他文件。"

    return (
        f"你是 NeoDev 产品智能助手，当前服务的产品是「{product_name}」。{projects_section}\n"
        f"{context_hint}{version_section}\n"
        "\n"
        "## 你的角色\n"
        "你是编排者和分析者，不是直接操作代码的人。你的核心工作流程是：\n"
        "1. **理解用户意图**：分析用户的问题，判断需要哪些信息\n"
        "2. **调度子智能体**：通过 task 工具将代码检索、文件搜索等具体工作委托给子智能体\n"
        "3. **综合分析**：基于子智能体返回的代码片段和事实，结合产品上下文进行推理和总结\n"
        "4. **回答用户**：给出有依据的、结构化的回答\n"
        "\n"
        "## 子智能体使用原则\n"
        "- 当用户问题涉及代码实现细节、文件内容、项目结构时，**必须**先调度子智能体检索，不要凭记忆回答\n"
        "- 子智能体会返回精确的代码片段和文件位置，你应基于这些事实进行分析\n"
        "- 如果子智能体没有找到相关代码，如实告知用户，不要编造\n"
        "\n"
        "## 并行与串行调度\n"
        "- **可以并行**：多个独立检索任务（如在不同项目中搜索不同关键字）\n"
        "- **必须串行**：当后续任务依赖前一个任务的结果时（如先检索 commit SHA，再用该 SHA 调用 commit-analyzer 分析具体变更）\n"
        "- 判断原则：如果任务 B 需要任务 A 的输出作为输入参数，则必须等 A 完成后再派发 B\n"
        "\n"
        "## 你可以帮助用户\n"
        "- 管理产品版本规划与发布\n"
        "- 分析需求结构（Epic → Story → Task）和完成度\n"
        "- 追踪 Bug 状态和修复进度\n"
        "- 跨项目分析代码提交和影响面\n"
        "- 提供产品质量和进度洞察\n"
        "\n"
        "请用中文回答。回答要简洁、准确、有依据。"
    )
