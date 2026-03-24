"""Agent Factory: 根据 thread_id 缓存 LangGraph agent 实例。

一个 thread_id 对应一个 agent 实例，后续复用。
system_prompt 通过 DynamicPromptMiddleware 在运行时动态注入，
不随 agent 编译固化，支持页面切换时 prompt 更新。
"""

import logging
import os
import ssl
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphRecursionError

from service.agent_profiles import (
    PRODUCT_AGENT_PROFILE,
    SUBAGENT_DEFINITIONS,
    build_commit_analyzer_subagent,
    build_nexus_subagent,
    build_pre_generate_prompt,
    build_product_system_prompt,
    build_requirement_doc_prompt,
    build_retriever_subagent,
    get_profile,
)
from service.checkpointer import get_checkpointer

logger = logging.getLogger(__name__)


# ── 沙箱文档路径常量 ──────────────────────────────────────────────────
_SANDBOX_DOC_PATH = "/requirement_doc.md"  # 直接访问 workspace backend 时的路径（不含路由前缀）


def _read_raw_doc(ws) -> str | None:
    """读取沙箱文档的原始内容（不含行号前缀）。

    ws.read() 会添加行号格式化（如 '     1\t# Title'），
    这里直接从文件系统读取原始内容。
    """
    try:
        doc_path = ws.workspace_path / _SANDBOX_DOC_PATH.lstrip("/")
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")
    except Exception:
        pass
    return None

# ── 缓存（key = thread_id）─────────────────────────────────────────────

_agent_cache: dict[str, Any] = {}
_workspace_cache: dict[str, Any] = {}  # thread_id → SandboxWorkspaceBackend
_retrieval_cache_store: dict[str, Any] = {}  # thread_id → RetrievalCache
_fallback_checkpointer = None


def _get_effective_checkpointer():
    """获取 checkpointer，如果 PostgreSQL 不可用则降级为内存 checkpointer。"""
    global _fallback_checkpointer
    cp = get_checkpointer()
    if cp is not None:
        return cp
    if _fallback_checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver
        _fallback_checkpointer = MemorySaver()
        logger.warning("PostgreSQL checkpointer 不可用，降级为 MemorySaver（仅进程内持久化）")
    return _fallback_checkpointer


def evict_agent(thread_id: str) -> bool:
    """从缓存中移除指定 thread_id 的 agent 实例。返回是否确实移除了。"""
    ws = _workspace_cache.pop(thread_id, None)
    if ws:
        try:
            ws.cleanup()
            logger.info("已清理 workspace [%s]", thread_id)
        except Exception:
            logger.warning("workspace cleanup 失败 [%s]", thread_id, exc_info=True)
    rc = _retrieval_cache_store.pop(thread_id, None)
    if rc:
        rc.clear()
        logger.info("已清理 RetrievalCache [%s]", thread_id)
    removed = _agent_cache.pop(thread_id, None)
    if removed:
        logger.info("已移除缓存 Agent [%s]", thread_id)
    return removed is not None


def _ensure_openai_env() -> None:
    """确保 OPENAI_API_BASE 等环境变量已设置。"""
    openai_env = _get_openai_env()
    for k, v in openai_env.items():
        if k not in os.environ:
            os.environ[k] = v


def _get_model_name() -> str:
    """从 .env 获取模型标识，格式为 openai:<model>。"""
    model_name = os.environ.get("OPENAI_MODEL_CHAT", "gpt-4o-mini")
    return f"openai:{model_name}"


def _ssl_context() -> ssl.SSLContext:
    """跳过 SSL 验证以兼容内网代理（自签名证书 / 弱密钥）。"""
    ctx = ssl.SSLContext()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
    return ctx


def _create_chat_model():
    """创建 ChatOpenAI 实例，使用自定义 SSL 上下文以兼容内网环境。"""
    from langchain_openai import ChatOpenAI

    model_name = os.environ.get("OPENAI_MODEL_CHAT", "gpt-4o-mini")
    base_url = os.environ.get("OPENAI_BASE", "").strip() or None
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or None

    ssl_ctx = _ssl_context()
    timeout = httpx.Timeout(600.0, connect=10.0)
    http_client = httpx.Client(verify=ssl_ctx, timeout=timeout)
    http_async_client = httpx.AsyncClient(verify=ssl_ctx, timeout=timeout)

    return ChatOpenAI(
        model=model_name,
        base_url=base_url,
        api_key=api_key,
        http_client=http_client,
        http_async_client=http_async_client,
        max_tokens=8192,
    )


def _get_openai_env() -> dict[str, str]:
    """收集 OpenAI 兼容 API 环境变量。"""
    env = {}
    base = os.environ.get("OPENAI_BASE", "").strip()
    if base:
        # langchain_openai 使用 OPENAI_API_BASE 或构造函数参数
        env["OPENAI_API_BASE"] = base
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        env["OPENAI_API_KEY"] = key
    return env


def _load_nexus_neo4j_config() -> dict[str, str] | None:
    """加载全局 Neo4j 连接配置（不依赖 project）。

    返回 {"neo4j_uri": ..., "neo4j_user": ..., "neo4j_password": ..., "neo4j_database": ...}
    或 None（未配置）。
    """
    config: dict[str, str] = {}
    try:
        from gitnexus_parser import load_config
        config = load_config()
        if not config.get("neo4j_uri"):
            src_dir = Path(__file__).resolve().parent.parent
            for path in [src_dir / "config.json", src_dir / "config.example.json"]:
                if path.is_file():
                    try:
                        config = load_config(path)
                        if config.get("neo4j_uri"):
                            break
                    except Exception:
                        pass
    except Exception:
        pass
    if not config.get("neo4j_uri"):
        return None
    return {
        "neo4j_uri": config["neo4j_uri"],
        "neo4j_user": config.get("neo4j_user", "neo4j"),
        "neo4j_password": config.get("neo4j_password", ""),
        "neo4j_database": config.get("neo4j_database") or None,
    }


def _build_backend(
    profile_name: str,
    session_id: str | None = None,
    project_path: str | None = None,
    project_id: int | None = None,
):
    """构建 CompositeBackend：项目目录只读 + 沙箱可写 + 默认 StateBackend。"""
    from deepagents.backends import CompositeBackend, StateBackend
    from service.readonly_backend import ReadOnlyFilesystemBackend
    from service.sandbox_manager import ensure_sandbox

    routes: dict[str, Any] = {}

    resolved = _resolve_repo_dir(project_path or "", project_id)
    if resolved:
        backend_inst = ReadOnlyFilesystemBackend(root_dir=resolved)
        routes["/workspace/project/"] = backend_inst
        logger.info("只读挂载项目: %s -> /workspace/project/", resolved)
        if project_id is not None:
            routes[f"/workspace/tmp/{project_id}/"] = backend_inst
            logger.info("只读挂载项目(ID): %s -> /workspace/tmp/%s/", resolved, project_id)

    if session_id:
        sandbox = ensure_sandbox(session_id)
        routes["/workspace/tmp/"] = sandbox
        logger.info("沙箱挂载: session=%s -> /workspace/tmp/", session_id)

    def factory(rt):
        default = StateBackend(rt)
        if routes:
            return CompositeBackend(default=default, routes=routes)
        return default

    return factory


def get_or_create_agent(
    thread_id: str,
    profile_name: str,
    session_id: str | None = None,
    project_path: str | None = None,
    project_id: int | None = None,
) -> Any:
    """获取或创建编译后的 agent，按 thread_id 缓存。

    system_prompt 使用占位符，实际 prompt 在运行时由 DynamicPromptMiddleware 注入。
    """
    current_cp = _get_effective_checkpointer()

    if thread_id in _agent_cache:
        cached = _agent_cache[thread_id]
        cached_cp = getattr(cached, "checkpointer", None)
        if cached_cp is not current_cp:
            logger.info("Checkpointer 变化，重建 Agent [%s]", thread_id)
            del _agent_cache[thread_id]
        else:
            logger.debug("复用 Agent [%s]", thread_id)
            return cached

    from deepagents.graph import create_deep_agent

    model = _create_chat_model()

    logger.info("创建 Agent [%s] profile=%s model=%s checkpointer=%s",
                thread_id, profile_name, model, type(current_cp).__name__)

    backend = _build_backend(profile_name, session_id, project_path, project_id=project_id)

    subagents = None
    profile = get_profile(profile_name)
    subagent_names = profile.get("subagents", [])
    if subagent_names:
        from deepagents.middleware.git_tools import GitToolsMiddleware
        from deepagents.middleware.subagents import SubAgent
        subagents = []
        retriever_path = f"/workspace/tmp/{project_id}/" if project_id else (
            "/workspace/project/" if project_path else None
        )
        for name in subagent_names:
            if name == "project-retriever":
                defn = build_retriever_subagent(
                    project_path=retriever_path,
                )
            elif name == "commit-analyzer":
                if not project_path:
                    continue
                real_repo_map = {"default": project_path}
                defn = build_commit_analyzer_subagent()
                subagents.append(SubAgent(
                    name=defn["name"],
                    description=defn["description"],
                    system_prompt=defn["prompt"],
                    middleware=[GitToolsMiddleware(repo_path_map=real_repo_map)],
                ))
                continue
            else:
                defn = SUBAGENT_DEFINITIONS.get(name)
            if defn:
                subagents.append(SubAgent(
                    name=defn["name"],
                    description=defn["description"],
                    system_prompt=defn["prompt"],
                ))

    # system_prompt 占位符，运行时由 DynamicPromptMiddleware 替换
    agent = create_deep_agent(
        model=model,
        system_prompt="placeholder",
        tools=None,
        backend=backend,
        subagents=subagents,
        checkpointer=current_cp,
    )

    _agent_cache[thread_id] = agent
    return agent


async def _process_stream_events(
    agent,
    input_msg: dict,
    config: dict,
    label: str = "",
    thread_id: str = "",
) -> AsyncIterator[dict]:
    """公共 SSE 事件处理：统一子智能体深度追踪、token 累加、事件转发。"""
    full_content = ""
    token_in = 0
    token_out = 0
    subagent_depth = 0
    has_emitted_content = False
    had_tool_call = False

    cp_type = type(agent.checkpointer).__name__ if hasattr(agent, "checkpointer") and agent.checkpointer else "None"
    logger.info("Agent stream 开始 [%s] thread=%s checkpointer=%s",
                label, thread_id, cp_type)

    try:
        async for event in agent.astream_events(input_msg, config=config, version="v2"):
            kind = event.get("event", "")
            data = event.get("data", {})

            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    if subagent_depth > 0:
                        yield {"event": "subagent_token", "data": chunk.content}
                    else:
                        if has_emitted_content and had_tool_call:
                            yield {"event": "content_start", "data": {}}
                            had_tool_call = False
                        full_content += chunk.content
                        has_emitted_content = True
                        yield {"event": "token", "data": chunk.content}

            elif kind == "on_chat_model_end":
                if subagent_depth > 0:
                    continue
                output = data.get("output")
                if output and hasattr(output, "usage_metadata") and output.usage_metadata:
                    usage = output.usage_metadata
                    token_in += getattr(usage, "input_tokens", 0) or 0
                    token_out += getattr(usage, "output_tokens", 0) or 0

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = data.get("input", {})
                if tool_name == "task":
                    if subagent_depth == 0:
                        yield {"event": "tool_start", "data": {"name": tool_name, "args": tool_input}}
                    subagent_depth += 1
                else:
                    if subagent_depth > 0:
                        yield {"event": "subagent_tool_start", "data": {"name": tool_name}}
                    else:
                        yield {"event": "tool_start", "data": {"name": tool_name, "args": tool_input}}
                had_tool_call = True

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = data.get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                if tool_name == "task":
                    subagent_depth = max(0, subagent_depth - 1)
                    if subagent_depth == 0:
                        yield {"event": "tool_end", "data": {"name": tool_name, "result": str(output)[:2000]}}
                else:
                    if subagent_depth > 0:
                        yield {"event": "subagent_tool_end", "data": {"name": tool_name, "result": str(output)[:500]}}
                    else:
                        yield {"event": "tool_end", "data": {"name": tool_name, "result": str(output)[:2000]}}

        logger.info("Agent stream 完成 [%s] thread=%s content_len=%d in=%d out=%d",
                    label, thread_id, len(full_content), token_in, token_out)

        yield {
            "event": "done",
            "data": {
                "content": full_content,
                "token_in": token_in,
                "token_out": token_out,
            },
        }

    except GraphRecursionError:
        logger.warning("Agent recursion limit [%s] thread=%s", label, thread_id)
        yield {
            "event": "recursion_limit",
            "data": {
                "content": full_content,
                "token_in": token_in,
                "token_out": token_out,
                "message": "我已经进行了很多轮思考，到达了循环上限。你可以选择让我继续。",
            },
        }

    except Exception as e:
        logger.exception("Agent stream error [%s]", label)
        yield {"event": "error", "data": {"message": str(e)}}


async def run_agent_stream(
    profile_name: str,
    thread_id: str,
    user_message: str,
    session_id: str | None = None,
    project_path: str | None = None,
    project_id: int | None = None,
) -> AsyncIterator[dict]:
    """流式调用 agent，yield SSE 事件字典。"""
    agent = get_or_create_agent(
        thread_id, profile_name, session_id=session_id,
        project_path=project_path, project_id=project_id,
    )

    system_prompt = get_profile(profile_name)["system_prompt"]
    config = {
        "configurable": {
            "thread_id": thread_id,
            "system_prompt_override": system_prompt,
        },
        "recursion_limit": 1000,
    }
    input_msg = {"messages": [HumanMessage(content=user_message)]}

    async for event in _process_stream_events(agent, input_msg, config, profile_name, thread_id):
        yield event


async def run_agent_invoke(
    profile_name: str,
    thread_id: str,
    user_message: str,
    session_id: str | None = None,
    project_path: str | None = None,
    project_id: int | None = None,
) -> dict:
    """非流式调用 agent，返回完整响应。"""
    agent = get_or_create_agent(
        thread_id, profile_name, session_id=session_id,
        project_path=project_path, project_id=project_id,
    )

    system_prompt = get_profile(profile_name)["system_prompt"]
    config = {
        "configurable": {
            "thread_id": thread_id,
            "system_prompt_override": system_prompt,
        },
        "recursion_limit": 1000,
    }
    input_msg = {"messages": [HumanMessage(content=user_message)]}

    try:
        result = await agent.ainvoke(input_msg, config=config)
        messages = result.get("messages", [])
        # 取最后一条 AI 消息
        ai_msg = None
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                ai_msg = msg
                break

        content = ai_msg.content if ai_msg else ""
        token_in = 0
        token_out = 0
        if ai_msg and hasattr(ai_msg, "usage_metadata") and ai_msg.usage_metadata:
            usage = ai_msg.usage_metadata
            token_in = getattr(usage, "input_tokens", 0) or 0
            token_out = getattr(usage, "output_tokens", 0) or 0

        return {
            "content": content,
            "token_in": token_in,
            "token_out": token_out,
        }
    except GraphRecursionError:
        logger.warning("Agent recursion limit reached (invoke) [%s]", profile_name)
        return {
            "content": "",
            "token_in": 0,
            "token_out": 0,
            "recursion_limit": True,
            "message": "我已经进行了很多轮思考，到达了循环上限。你可以选择让我继续。",
        }
    except Exception as e:
        logger.exception("Agent invoke error [%s]", profile_name)
        return {"content": "", "error": str(e)}


# ── 产品级 Agent ──────────────────────────────────────────────────────


def _resolve_repo_dir(repo_path: str, project_id: int | None) -> str | None:
    """尝试将 repo_path 解析为本地目录：若为 URL，回退到 REPO_CLONE_BASE/{project_id}。"""
    if repo_path and Path(repo_path).is_dir():
        return repo_path
    if project_id is not None:
        clone_base = os.environ.get("REPO_CLONE_BASE", "").strip()
        if clone_base:
            fallback = Path(clone_base) / str(project_id)
            if fallback.is_dir():
                return str(fallback)
    return None


def _build_product_backend(
    session_id: str | None,
    project_repo_map: dict[str, str] | None = None,
    workspace_backend: Any = None,
    branch_mappings: list[dict] | None = None,
    project_id_map: dict[str, int] | None = None,
):
    """产品级 CompositeBackend：多项目只读挂载 + 沙箱可写 + workspace。

    project_repo_map: {"project-a": "/path/to/repo-a", ...}
    挂载为 /workspace/projects/project-a/ 和 /workspace/tmp/{project_id}/。
    workspace_backend: SandboxWorkspaceBackend 实例，挂载到 /workspace/sandbox/。
    branch_mappings: [{"project_name": "xxx", "branch": "yyy"}, ...] 指定分支时使用 GitReadOnlyBackend。
    project_id_map: {"project-a": 1, ...} 项目名→ID，用于 /workspace/tmp/{id}/ 路由。
    """
    from deepagents.backends import CompositeBackend, StateBackend
    from service.git_readonly_backend import GitReadOnlyBackend
    from service.readonly_backend import ReadOnlyFilesystemBackend
    from service.sandbox_manager import ensure_sandbox

    routes: dict[str, Any] = {}

    branch_by_project: dict[str, str] = {}
    if branch_mappings:
        for bm in branch_mappings:
            pname = bm.get("project_name")
            branch = bm.get("branch")
            if pname and branch:
                branch_by_project[pname] = branch

    if project_repo_map:
        for proj_name, repo_path in project_repo_map.items():
            pid = project_id_map.get(proj_name) if project_id_map else None
            resolved = _resolve_repo_dir(repo_path, pid)
            if not resolved:
                continue
            branch = branch_by_project.get(proj_name)

            def _make_backend(rpath: str, br: str | None):
                if br:
                    return GitReadOnlyBackend(repo_dir=rpath, branch=br)
                return ReadOnlyFilesystemBackend(root_dir=rpath)

            backend_inst = _make_backend(resolved, branch)

            mount_name = f"/workspace/projects/{proj_name}/"
            routes[mount_name] = backend_inst
            logger.info("项目挂载: %s -> %s", resolved, mount_name)

            if pid is not None:
                mount_id = f"/workspace/tmp/{pid}/"
                routes[mount_id] = backend_inst
                logger.info("项目挂载(ID): %s -> %s", resolved, mount_id)

    if session_id:
        sandbox = ensure_sandbox(session_id)
        routes["/workspace/tmp/"] = sandbox
        logger.info("沙箱挂载: session=%s -> /workspace/tmp/", session_id)

    if workspace_backend is not None:
        routes["/workspace/sandbox/"] = workspace_backend
        logger.info("workspace 挂载: /workspace/sandbox/")

    def factory(rt):
        default = StateBackend(rt)
        if routes:
            return CompositeBackend(default=default, routes=routes)
        return default

    return factory


def get_or_create_product_agent(
    thread_id: str,
    session_id: str | None = None,
    project_repo_map: dict[str, str] | None = None,
    version_name: str | None = None,
    branch_mappings: list[dict] | None = None,
    project_id_map: dict[str, int] | None = None,
    exclude_subagents: set[str] | None = None,
) -> Any:
    """获取或创建产品级 Agent，按 thread_id 缓存。

    system_prompt 在运行时由 DynamicPromptMiddleware 动态注入。
    """
    current_cp = _get_effective_checkpointer()

    if thread_id in _agent_cache:
        cached = _agent_cache[thread_id]
        cached_cp = getattr(cached, "checkpointer", None)
        if cached_cp is not current_cp:
            logger.info("Checkpointer 变化，重建产品 Agent [%s]", thread_id)
            del _agent_cache[thread_id]
        else:
            logger.debug("复用产品 Agent [%s]", thread_id)
            return cached

    from deepagents.backends.workspace import SandboxWorkspaceBackend
    from deepagents.graph import create_deep_agent
    from deepagents.middleware.git_tools import GitToolsMiddleware
    from deepagents.middleware.retrieval_cache import RetrievalCache
    from deepagents.middleware.subagents import SubAgent

    model = _create_chat_model()

    logger.info("创建产品 Agent [%s] model=%s checkpointer=%s",
                thread_id, model, type(current_cp).__name__)

    # 创建 workspace
    workspace_backend = SandboxWorkspaceBackend()
    _workspace_cache[thread_id] = workspace_backend

    backend = _build_product_backend(
        session_id, project_repo_map,
        workspace_backend=workspace_backend,
        branch_mappings=branch_mappings,
        project_id_map=project_id_map,
    )

    # 虚拟路径映射：优先使用 /workspace/tmp/{pid}/ 路径（智能体更易定位）
    virtual_repo_map: dict[str, str] | None = None
    if project_repo_map and project_id_map:
        virtual_repo_map = {}
        for pname in project_repo_map:
            pid = project_id_map.get(pname)
            if pid is not None:
                virtual_repo_map[pname] = f"/workspace/tmp/{pid}/"
            else:
                virtual_repo_map[pname] = f"/workspace/projects/{pname}/"
    elif project_repo_map:
        virtual_repo_map = {
            pname: f"/workspace/projects/{pname}/"
            for pname in project_repo_map
        }

    subagents = []
    for name in PRODUCT_AGENT_PROFILE.get("subagents", []):
        if exclude_subagents and name in exclude_subagents:
            continue
        if name == "project-retriever":
            defn = build_retriever_subagent(
                project_repo_map=virtual_repo_map,
                version_name=version_name,
                branch_mappings=branch_mappings,
            )
        elif name == "commit-analyzer":
            if not project_repo_map:
                continue
            defn = build_commit_analyzer_subagent(
                project_repo_map=virtual_repo_map,
                version_name=version_name,
                branch_mappings=branch_mappings,
            )
            # commit-analyzer 需要真实路径访问 git
            subagents.append(SubAgent(
                name=defn["name"],
                description=defn["description"],
                system_prompt=defn["prompt"],
                middleware=[GitToolsMiddleware(repo_path_map=project_repo_map)],
            ))
            continue
        elif name == "nexus":
            neo4j_cfg = _load_nexus_neo4j_config()
            if not neo4j_cfg:
                logger.info("Neo4j 未配置，跳过 nexus 子智能体")
                continue
            from deepagents.middleware.nexus_tools import NexusToolsMiddleware
            branch_map = {
                bm["project_name"]: bm["branch"]
                for bm in (branch_mappings or [])
            }
            nexus_mw = NexusToolsMiddleware(
                neo4j_uri=neo4j_cfg["neo4j_uri"],
                neo4j_user=neo4j_cfg.get("neo4j_user", "neo4j"),
                neo4j_password=neo4j_cfg.get("neo4j_password", ""),
                neo4j_database=neo4j_cfg.get("neo4j_database"),
                project_id_map=project_id_map,
                branch_map=branch_map,
            )
            defn = build_nexus_subagent(
                project_id_map=project_id_map,
                branch_map=branch_map,
                version_name=version_name,
            )
            subagents.append(SubAgent(
                name=defn["name"],
                description=defn["description"],
                system_prompt=defn["prompt"],
                tools=nexus_mw.tools,
                middleware=[nexus_mw],
            ))
            continue
        else:
            defn = SUBAGENT_DEFINITIONS.get(name)
        if defn:
            subagents.append(SubAgent(
                name=defn["name"],
                description=defn["description"],
                system_prompt=defn["prompt"],
            ))

    shared_retrieval_cache = RetrievalCache()
    _retrieval_cache_store[thread_id] = shared_retrieval_cache

    agent = create_deep_agent(
        model=model,
        system_prompt="placeholder",
        tools=None,
        backend=backend,
        subagents=subagents or None,
        checkpointer=current_cp,
        workspace=workspace_backend,
        workspace_routing={"/workspace/sandbox/": workspace_backend},
        workspace_path_prefix="/workspace/sandbox/",
        general_purpose_agent=False,
        retrieval_cache=shared_retrieval_cache,
    )

    _agent_cache[thread_id] = agent
    return agent


_PRE_GEN_CACHE_PREFIX = "pre_gen:"
_pre_gen_history: dict[str, list] = {}

# 预生成引导对话的结构化输出 schema
try:
    from pydantic import BaseModel as _PydanticBase, Field as _Field

    class _PreGenResponse(_PydanticBase):
        """AI 预生成引导的结构化回复格式"""
        question: str = _Field(description="对用户的问题或引导语，支持 Markdown 格式")
        options: list[str] = _Field(
            description="2-4 个用户可快速选择的简短回答选项（每项 15 字以内）",
            min_length=2,
            max_length=4,
        )
except Exception:
    _PreGenResponse = None  # type: ignore[assignment,misc]


async def run_pre_generate_agent_stream(
    thread_id: str,
    user_message: str,
    doc_context: dict,
) -> AsyncIterator[dict]:
    """预生成引导对话（直接使用 LLM 结构化输出，不经过 DeepAgent）。

    AI 直接输出结构化的 {question, options} 格式。
    前端会自动在 options 后追加 Skip 和手动输入框。
    """
    from langchain_core.messages import HumanMessage as HM, SystemMessage

    system_prompt = build_pre_generate_prompt(
        level=doc_context.get("level", "epic"),
        requirement_title=doc_context.get("requirement_title", ""),
        requirement_description=doc_context.get("requirement_description"),
        product_name=doc_context.get("product_name", ""),
        sibling_titles=doc_context.get("sibling_titles") or [],
        parent_doc=doc_context.get("parent_doc"),
    )

    # 从内存缓存加载对话历史（pre-gen 会话是短暂的，无需持久化）
    messages = list(_pre_gen_history.get(thread_id, []))

    if not messages or not any(isinstance(m, SystemMessage) for m in messages):
        messages.insert(0, SystemMessage(content=system_prompt))
    messages.append(HM(content=user_message))

    try:
        model = _create_chat_model()
        structured = model.with_structured_output(_PreGenResponse)

        logger.info("预生成引导：开始调用 LLM thread=%s", thread_id)
        result = await structured.ainvoke(messages)

        question = result.question
        options = list(result.options) if result.options else []

        logger.info("预生成引导完成 thread=%s question_len=%d options=%d",
                   thread_id, len(question), len(options))

        from langchain_core.messages import AIMessage
        messages.append(AIMessage(content=question))
        _pre_gen_history[thread_id] = messages

        # 先发送 question 作为 token 事件（模拟流式）
        yield {"event": "token", "data": question}
        yield {"event": "done", "data": {"content": question}}

        # 再发送 options 事件（前端会自动追加 Skip 和手动输入框）
        if options:
            yield {"event": "structured", "data": {"options": options}}

    except Exception as e:
        logger.exception("预生成引导错误 thread=%s", thread_id)
        yield {"event": "error", "data": {"message": str(e)}}


async def run_product_agent_stream(
    product_name: str,
    thread_id: str,
    user_message: str,
    project_names: list[str] | None = None,
    route_hint: str | None = None,
    session_id: str | None = None,
    project_repo_map: dict[str, str] | None = None,
    version_name: str | None = None,
    branch_mappings: list[dict] | None = None,
    project_id_map: dict[str, int] | None = None,
    doc_context: dict | None = None,
) -> AsyncIterator[dict]:
    """产品级 Agent 流式调用。

    当 doc_context 存在时，切换为文档编辑模式：
    - 使用 build_requirement_doc_prompt 替代 build_product_system_prompt
    - 排除 commit-analyzer 子智能体
    - 将文档写入沙箱，Agent 通过 edit_file 编辑
    - tool_end(edit_file) 时附加 doc_snapshot
    - done 时附加 modified_doc（如有变更）
    """
    exclude_subagents = {"commit-analyzer"} if doc_context else None

    agent = get_or_create_product_agent(
        thread_id,
        session_id=session_id, project_repo_map=project_repo_map,
        version_name=version_name, branch_mappings=branch_mappings,
        project_id_map=project_id_map,
        exclude_subagents=exclude_subagents,
    )

    if doc_context:
        system_prompt = build_requirement_doc_prompt(
            level=doc_context.get("level", "story"),
            requirement_title=doc_context.get("requirement_title", ""),
            requirement_description=doc_context.get("requirement_description"),
            parent_doc=doc_context.get("parent_doc"),
            sibling_titles=doc_context.get("sibling_titles") or [],
            product_name=doc_context.get("product_name", ""),
            version_name=doc_context.get("version_name") or version_name,
            code_context=doc_context.get("code_context"),
            graph_context=doc_context.get("graph_context"),
            existing_doc=doc_context.get("existing_doc"),
            for_editing=True,
            project_repo_map=virtual_repo_map,
        )
    else:
        system_prompt = build_product_system_prompt(
            product_name, project_names, route_hint,
            version_name=version_name, branch_mappings=branch_mappings,
            project_id_map=project_id_map,
        )

    config = {
        "configurable": {
            "thread_id": thread_id,
            "system_prompt_override": system_prompt,
        },
        "recursion_limit": 1000,
    }
    input_msg = {"messages": [HumanMessage(content=user_message)]}

    # 文档模式：写入沙箱
    existing_doc = ""
    ws = None
    if doc_context:
        existing_doc = doc_context.get("existing_doc") or ""
        ws = _workspace_cache.get(thread_id)
        if ws:
            try:
                doc_path = ws.workspace_path / _SANDBOX_DOC_PATH.lstrip("/")
                doc_path.parent.mkdir(parents=True, exist_ok=True)
                doc_path.write_text(existing_doc, encoding="utf-8")
                logger.info("文档已写入沙箱 [%s] len=%d", thread_id, len(existing_doc))
            except Exception:
                logger.warning("写入沙箱文档失败 [%s]", thread_id, exc_info=True)

    async for event in _process_stream_events(agent, input_msg, config, f"product:{product_name}", thread_id):
        if doc_context and ws:
            if event["event"] == "tool_end":
                data = event.get("data", {})
                if data.get("name") == "edit_file":
                    snapshot = _read_raw_doc(ws)
                    if snapshot:
                        event["data"]["doc_snapshot"] = snapshot

            elif event["event"] == "done":
                modified = _read_raw_doc(ws)
                if modified and modified != existing_doc:
                    event["data"]["modified_doc"] = modified
                    event["data"]["pre_change_content"] = existing_doc
                    text_content = event["data"].get("content", "")
                    if len(text_content) > 500:
                        event["data"]["content"] = text_content[:200] + "\n\n…（已通过工具完成文档修改，请在编辑器中审阅变更）"

        yield event
