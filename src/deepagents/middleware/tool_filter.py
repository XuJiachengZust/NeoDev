"""运行时动态过滤工具的中间件。

通过 config["configurable"]["disabled_tools"] 传入要禁用的工具名集合，
在每次 LLM 调用时从 request.tools 中移除对应工具。

用于按回答模式（simple/medium/hard）控制主 Agent 的规划能力。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, NotRequired

from langchain_core.runnables import RunnableConfig

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
    PrivateStateAttr,
)
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)


class ToolFilterState(AgentState):
    """ToolFilterMiddleware 的 state schema。"""

    _disabled_tools: NotRequired[Annotated[set[str] | None, PrivateStateAttr]]


class ToolFilterMiddleware(AgentMiddleware):
    """运行时动态过滤工具。

    从 config["configurable"]["disabled_tools"] 读取工具名集合，
    在 wrap_model_call 时从 request.tools 中移除。
    """

    state_schema = ToolFilterState

    def before_agent(
        self, state: ToolFilterState, runtime: Runtime, config: RunnableConfig,
    ) -> dict | None:
        configurable = config.get("configurable", {})
        disabled = configurable.get("disabled_tools")
        if disabled:
            return {"_disabled_tools": set(disabled)}
        return None

    async def abefore_agent(
        self, state: ToolFilterState, runtime: Runtime, config: RunnableConfig,
    ) -> dict | None:
        return self.before_agent(state, runtime, config)

    def _filter_tools(self, request: ModelRequest) -> ModelRequest:
        """如果 state 中有 disabled_tools，从 request.tools 中移除。"""
        disabled = request.state.get("_disabled_tools")
        if disabled and request.tools:
            filtered = [t for t in request.tools if t.name not in disabled]
            if len(filtered) < len(request.tools):
                removed = {t.name for t in request.tools} - {t.name for t in filtered}
                logger.debug("ToolFilter: 移除工具 %s", removed)
                return request.override(tools=filtered)
        return request

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        modified = self._filter_tools(request)
        return handler(modified)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        modified = self._filter_tools(request)
        return await handler(modified)
