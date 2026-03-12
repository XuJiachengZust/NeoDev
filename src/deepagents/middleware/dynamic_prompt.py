"""运行时动态替换 system_prompt 的中间件。

通过 config["configurable"]["system_prompt_override"] 传入最新 prompt，
在每次 LLM 调用时替换 system_message。

用于 Agent 实例缓存场景：agent 编译一次后复用，system_prompt 随页面上下文动态更新。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Annotated, NotRequired

from langchain_core.messages import SystemMessage
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


class DynamicPromptState(AgentState):
    """DynamicPromptMiddleware 的 state schema。"""

    _dynamic_system_prompt: NotRequired[Annotated[str | None, PrivateStateAttr]]


class DynamicPromptMiddleware(AgentMiddleware):
    """运行时动态替换 system_prompt。

    从 config["configurable"]["system_prompt_override"] 读取新 prompt，
    在每次 LLM 调用时用 request.override(system_message=...) 替换 system_message。
    """

    state_schema = DynamicPromptState

    def before_agent(
        self, state: DynamicPromptState, runtime: Runtime, config: RunnableConfig,
    ) -> dict | None:
        configurable = config.get("configurable", {})
        override = configurable.get("system_prompt_override")
        if override:
            return {"_dynamic_system_prompt": override}
        return None

    async def abefore_agent(
        self, state: DynamicPromptState, runtime: Runtime, config: RunnableConfig,
    ) -> dict | None:
        return self.before_agent(state, runtime, config)

    def _apply_override(self, request: ModelRequest) -> ModelRequest:
        """如果 state 中有动态 prompt，替换 system_message。"""
        prompt = request.state.get("_dynamic_system_prompt")
        if prompt:
            return request.override(system_message=SystemMessage(content=prompt))
        return request

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        modified = self._apply_override(request)
        return handler(modified)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        modified = self._apply_override(request)
        return await handler(modified)
