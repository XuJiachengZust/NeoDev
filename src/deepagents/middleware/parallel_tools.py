"""中间件：为子智能体启用并行工具调用。

通过在 model.bind_tools() 时注入 parallel_tool_calls=True，
使模型可以在一次响应中返回多个工具调用，提升检索效率。
"""

from langchain.agents.middleware import AgentMiddleware


class ParallelToolCallsMiddleware(AgentMiddleware):
    """在 model.bind_tools() 时注入 parallel_tool_calls=True。"""

    def wrap_model_call(self, request, handler):
        new_settings = {**request.model_settings, "parallel_tool_calls": True}
        return handler(request.override(model_settings=new_settings))

    async def awrap_model_call(self, request, handler):
        new_settings = {**request.model_settings, "parallel_tool_calls": True}
        return await handler(request.override(model_settings=new_settings))
