"""Agent Factory: 根据 profile 创建或复用 LangGraph agent。

使用 create_deep_agent() 构建智能体，按 profile 名称缓存编译后的 StateGraph。
复用 .env 中的 OPENAI_API_KEY, OPENAI_BASE, OPENAI_MODEL_CHAT 配置。
支持 CompositeBackend：项目目录只读挂载 + 沙箱可写区域。
"""

import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from service.agent_profiles import (
    AGENT_PROFILES,
    PRODUCT_AGENT_PROFILE,
    SUBAGENT_DEFINITIONS,
    build_product_system_prompt,
    get_profile,
)

logger = logging.getLogger(__name__)

# ── 缓存 ──────────────────────────────────────────────────────────────

_agent_cache: dict[str, Any] = {}


def _get_model_name() -> str:
    """从 .env 获取模型标识，格式为 openai:<model>。"""
    model_name = os.environ.get("OPENAI_MODEL_CHAT", "gpt-4o-mini")
    return f"openai:{model_name}"


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


def _build_backend(profile_name: str, session_id: str | None = None, project_path: str | None = None):
    """构建 CompositeBackend：项目目录只读 + 沙箱可写 + 默认 StateBackend。"""
    from deepagents.backends import CompositeBackend, StateBackend
    from service.readonly_backend import ReadOnlyFilesystemBackend
    from service.sandbox_manager import ensure_sandbox

    routes: dict[str, Any] = {}

    # 项目只读挂载
    if project_path and Path(project_path).is_dir():
        routes["/workspace/project/"] = ReadOnlyFilesystemBackend(root_dir=project_path)
        logger.info("只读挂载项目: %s -> /workspace/project/", project_path)

    # 沙箱可写区域
    if session_id:
        sandbox = ensure_sandbox(session_id)
        routes["/workspace/tmp/"] = sandbox
        logger.info("沙箱挂载: session=%s -> /workspace/tmp/", session_id)

    # 返回工厂函数（create_deep_agent 需要 BackendFactory）
    def factory(rt):
        default = StateBackend(rt)
        if routes:
            return CompositeBackend(default=default, routes=routes)
        return default

    return factory


def get_or_create_agent(
    profile_name: str,
    session_id: str | None = None,
    project_path: str | None = None,
) -> Any:
    """获取或创建编译后的 agent（CompiledStateGraph）。

    如果提供了 session_id 和 project_path，将构建 CompositeBackend。
    无 session/project 时按 profile_name 缓存。
    """
    # 有 session/project 参数时不缓存（每次创建带上下文的 agent）
    cache_key = profile_name if (session_id is None and project_path is None) else None
    if cache_key and cache_key in _agent_cache:
        return _agent_cache[cache_key]

    from deepagents.graph import create_deep_agent

    profile = get_profile(profile_name)
    system_prompt = profile["system_prompt"]
    model_name = _get_model_name()

    # 确保 OPENAI_API_BASE 设置正确
    openai_env = _get_openai_env()
    for k, v in openai_env.items():
        if k not in os.environ:
            os.environ[k] = v

    logger.info("创建 Agent [%s] model=%s", profile_name, model_name)

    # 构建 backend
    backend = _build_backend(profile_name, session_id, project_path)

    # 构建子智能体
    subagents = None
    subagent_names = profile.get("subagents", [])
    if subagent_names:
        from deepagents.middleware.subagents import SubAgent
        subagents = []
        for name in subagent_names:
            defn = SUBAGENT_DEFINITIONS.get(name)
            if defn:
                subagents.append(SubAgent(
                    name=defn["name"],
                    description=defn["description"],
                    prompt=defn["prompt"],
                ))

    agent = create_deep_agent(
        model=model_name,
        system_prompt=system_prompt,
        tools=None,  # 使用默认内置工具
        backend=backend,
        subagents=subagents,
    )

    if cache_key:
        _agent_cache[cache_key] = agent
    return agent


async def run_agent_stream(
    profile_name: str,
    thread_id: str,
    user_message: str,
    session_id: str | None = None,
    project_path: str | None = None,
) -> AsyncIterator[dict]:
    """流式调用 agent，yield SSE 事件字典。

    事件格式:
    - {"event": "token", "data": "文本片段"}
    - {"event": "tool_start", "data": {"name": "...", "args": {...}}}
    - {"event": "tool_end", "data": {"name": "...", "result": "..."}}
    - {"event": "done", "data": {"content": "完整回复", "token_in": N, "token_out": N}}
    - {"event": "error", "data": {"message": "错误信息"}}
    """
    agent = get_or_create_agent(profile_name, session_id=session_id, project_path=project_path)

    config = {
        "configurable": {"thread_id": thread_id},
    }
    input_msg = {"messages": [HumanMessage(content=user_message)]}

    full_content = ""
    token_in = 0
    token_out = 0

    try:
        async for event in agent.astream_events(input_msg, config=config, version="v2"):
            kind = event.get("event", "")
            data = event.get("data", {})

            if kind == "on_chat_model_stream":
                # 逐 token 输出
                chunk = data.get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    full_content += chunk.content
                    yield {"event": "token", "data": chunk.content}

            elif kind == "on_chat_model_end":
                # 提取 token usage
                output = data.get("output")
                if output and hasattr(output, "usage_metadata") and output.usage_metadata:
                    usage = output.usage_metadata
                    token_in += getattr(usage, "input_tokens", 0) or 0
                    token_out += getattr(usage, "output_tokens", 0) or 0

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = data.get("input", {})
                yield {
                    "event": "tool_start",
                    "data": {"name": tool_name, "args": tool_input},
                }

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = data.get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                yield {
                    "event": "tool_end",
                    "data": {"name": tool_name, "result": str(output)[:2000]},
                }

        yield {
            "event": "done",
            "data": {
                "content": full_content,
                "token_in": token_in,
                "token_out": token_out,
            },
        }

    except Exception as e:
        logger.exception("Agent stream error [%s]", profile_name)
        yield {"event": "error", "data": {"message": str(e)}}


async def run_agent_invoke(
    profile_name: str,
    thread_id: str,
    user_message: str,
    session_id: str | None = None,
    project_path: str | None = None,
) -> dict:
    """非流式调用 agent，返回完整响应。"""
    agent = get_or_create_agent(profile_name, session_id=session_id, project_path=project_path)

    config = {
        "configurable": {"thread_id": thread_id},
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
    except Exception as e:
        logger.exception("Agent invoke error [%s]", profile_name)
        return {"content": "", "error": str(e)}


# ── 产品级 Agent ──────────────────────────────────────────────────────


def get_or_create_product_agent(
    product_name: str,
    project_names: list[str] | None = None,
    route_hint: str | None = None,
    session_id: str | None = None,
    project_path: str | None = None,
) -> Any:
    """创建带有产品上下文的 Agent。不缓存（每次带最新产品上下文）。"""
    from deepagents.graph import create_deep_agent
    from deepagents.middleware.subagents import SubAgent

    system_prompt = build_product_system_prompt(product_name, project_names, route_hint)
    model_name = _get_model_name()

    openai_env = _get_openai_env()
    for k, v in openai_env.items():
        if k not in os.environ:
            os.environ[k] = v

    logger.info("创建产品 Agent [%s] model=%s", product_name, model_name)

    backend = _build_backend("product", session_id, project_path)

    subagents = []
    for name in PRODUCT_AGENT_PROFILE.get("subagents", []):
        defn = SUBAGENT_DEFINITIONS.get(name)
        if defn:
            subagents.append(SubAgent(
                name=defn["name"],
                description=defn["description"],
                prompt=defn["prompt"],
            ))

    return create_deep_agent(
        model=model_name,
        system_prompt=system_prompt,
        tools=None,
        backend=backend,
        subagents=subagents or None,
    )


async def run_product_agent_stream(
    product_name: str,
    thread_id: str,
    user_message: str,
    project_names: list[str] | None = None,
    route_hint: str | None = None,
    session_id: str | None = None,
    project_path: str | None = None,
) -> AsyncIterator[dict]:
    """产品级 Agent 流式调用。"""
    agent = get_or_create_product_agent(
        product_name, project_names=project_names, route_hint=route_hint,
        session_id=session_id, project_path=project_path,
    )

    config = {"configurable": {"thread_id": thread_id}}
    input_msg = {"messages": [HumanMessage(content=user_message)]}

    full_content = ""
    token_in = 0
    token_out = 0

    try:
        async for event in agent.astream_events(input_msg, config=config, version="v2"):
            kind = event.get("event", "")
            data = event.get("data", {})

            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    full_content += chunk.content
                    yield {"event": "token", "data": chunk.content}

            elif kind == "on_chat_model_end":
                output = data.get("output")
                if output and hasattr(output, "usage_metadata") and output.usage_metadata:
                    usage = output.usage_metadata
                    token_in += getattr(usage, "input_tokens", 0) or 0
                    token_out += getattr(usage, "output_tokens", 0) or 0

            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = data.get("input", {})
                yield {"event": "tool_start", "data": {"name": tool_name, "args": tool_input}}

            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = data.get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                yield {"event": "tool_end", "data": {"name": tool_name, "result": str(output)[:2000]}}

        yield {
            "event": "done",
            "data": {"content": full_content, "token_in": token_in, "token_out": token_out},
        }

    except Exception as e:
        logger.exception("Product Agent stream error [%s]", product_name)
        yield {"event": "error", "data": {"message": str(e)}}
