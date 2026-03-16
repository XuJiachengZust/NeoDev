"""沙箱工作空间中间件。

通过 role 参数区分父智能体（orchestrator）和子智能体（subagent），
注入不同的系统提示词，实现多智能体协作中的磁盘级报告传递。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from deepagents.backends.workspace import SandboxWorkspaceBackend

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 系统提示词
# ---------------------------------------------------------------------------

def _build_orchestrator_prompt(prefix: str = "/workspace/") -> str:
    """根据路径前缀构建父智能体（orchestrator）提示词。"""
    return f"""\
## 沙箱工作空间

你有一个临时工作空间 {prefix}，子智能体会将详细报告写入其中。

### 协作规范
- 子智能体完成任务后返回 **简短摘要 + 报告文件路径**
- 你通过 read_file 按需查看详细内容

### 动态规划循环
每当一个子任务完成并返回结果时，你必须：
1. **评估结果**：阅读摘要，判断是否需要 read_file 查看详细报告
2. **更新认知**：识别新发现的信息、风险、依赖关系
3. **调整规划**：
   - 是否需要新增子任务（发现预期外的问题）
   - 是否需要删除/修改后续子任务（已被当前结果覆盖）
   - 是否可以并行执行多个独立子任务
4. **执行下一步**：分派调整后的下一批子任务

不要机械地按初始计划执行，每一步都要基于最新上下文做判断。

### 目录结构
- {prefix}reports/   — 子智能体详细报告
- {prefix}artifacts/ — 中间产物
- {prefix}plan.md    — 你的动态规划文档（可选）"""


def _build_subagent_prompt(prefix: str = "/workspace/") -> str:
    """根据路径前缀构建子智能体（subagent）提示词。"""
    return f"""\
## 工作空间输出规范

你必须将详细分析写入工作空间文件，并在最终回复中包含文件路径。

### 必须遵守的流程
1. 执行任务，收集详细分析内容
2. 调用 write_file 将完整内容写入 {prefix}reports/{{task_name}}.md
3. 最终回复**必须**包含以下格式：

## 摘要
（3-5句关键发现）

## 报告路径
{prefix}reports/{{task_name}}.md

### 重要
- 详细内容写文件，回复只写摘要 — 节省父智能体的上下文空间
- **必须包含报告文件路径**，否则父智能体无法定位你的详细输出
- 中间产物（代码片段、数据）写入 {prefix}artifacts/"""


# 向后兼容：保留常量供外部引用（使用默认前缀）
WORKSPACE_ORCHESTRATOR_PROMPT = _build_orchestrator_prompt()
WORKSPACE_SUBAGENT_PROMPT = _build_subagent_prompt()


def _append_to_system_message(
    system_message: str | SystemMessage | None,
    extra: str,
) -> str | SystemMessage:
    """将额外文本追加到系统消息末尾。"""
    if system_message is None:
        return extra
    if isinstance(system_message, SystemMessage):
        content_blocks = list(system_message.content_blocks)
        content_blocks.append({"type": "text", "text": f"\n\n{extra}"})
        return SystemMessage(content=content_blocks)
    return f"{system_message}\n\n{extra}"


class SandboxWorkspaceMiddleware(AgentMiddleware):
    """沙箱工作空间中间件。

    根据 role 注入不同提示词：
    - orchestrator: 父智能体收到动态规划循环指令
    - subagent: 子智能体收到输出规范（必须写文件+返回路径）

    orchestrator 角色在每轮对话开始时自动 reset 工作空间（首轮除外）。
    """

    def __init__(
        self,
        workspace: SandboxWorkspaceBackend,
        role: str = "orchestrator",
        path_prefix: str = "/workspace/",
    ) -> None:
        """初始化。

        Args:
            workspace: 沙箱工作空间后端实例。
            role: "orchestrator"（父智能体）或 "subagent"（子智能体）。
            path_prefix: 提示词中使用的路径前缀，默认 "/workspace/"。
                产品 Agent 可传入 "/workspace/sandbox/" 避免与已有路由冲突。
        """
        if role not in ("orchestrator", "subagent"):
            raise ValueError(f"role 必须是 'orchestrator' 或 'subagent'，收到: {role!r}")
        self._workspace = workspace
        self._role = role
        self._path_prefix = path_prefix
        self._initialized = False

    @property
    def workspace(self) -> SandboxWorkspaceBackend:
        return self._workspace

    @property
    def role(self) -> str:
        return self._role

    def before_agent(
        self, state: dict, runtime: Runtime, config: RunnableConfig,
    ) -> dict | None:
        """orchestrator 角色：首轮跳过，后续轮次 reset 工作空间。"""
        if self._role == "orchestrator":
            if self._initialized:
                self._workspace.reset()
            else:
                self._initialized = True
        return None

    async def abefore_agent(
        self, state: dict, runtime: Runtime, config: RunnableConfig,
    ) -> dict | None:
        return self.before_agent(state, runtime, config)

    def _get_prompt(self) -> str:
        """根据 role 和 path_prefix 返回对应提示词。"""
        if self._role == "orchestrator":
            return _build_orchestrator_prompt(self._path_prefix)
        return _build_subagent_prompt(self._path_prefix)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        prompt = self._get_prompt()
        new_system = _append_to_system_message(request.system_message, prompt)
        return handler(request.override(system_message=new_system))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        prompt = self._get_prompt()
        new_system = _append_to_system_message(request.system_message, prompt)
        return await handler(request.override(system_message=new_system))
