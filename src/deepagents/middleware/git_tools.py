"""Middleware for providing git analysis tools to an agent."""

import re
from collections.abc import Awaitable, Callable
from typing import Annotated

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.tools import StructuredTool

from deepagents.backends.utils import truncate_if_too_long
from deepagents.middleware._utils import append_to_system_message

# SHA 校验: 4-40 位十六进制
_SHA_RE = re.compile(r"^[0-9a-fA-F]{4,40}$")
# ref 校验: 字母数字 + . _ / -
_REF_RE = re.compile(r"^[a-zA-Z0-9_./-]+$")

GIT_TOOLS_SYSTEM_PROMPT = (
    "## Git 分析工具\n"
    "你可以使用以下 git 工具分析代码提交：\n"
    "- git_show: 查看 commit 详情和变更统计\n"
    "- git_diff: 获取 commit 的代码变更（unified diff）\n"
    "- git_log_range: 获取提交列表\n"
    "\n"
    "分析策略：先用 git_show(stat_only=True) 看概览，再用 git_diff 看关键文件详情。"
)


def _validate_sha(s: str) -> str:
    """校验 commit SHA 格式，不合法抛 ValueError。"""
    if not _SHA_RE.match(s):
        raise ValueError(f"无效的 commit SHA: {s!r}")
    return s


def _validate_ref(s: str) -> str:
    """校验 git ref 格式，不合法抛 ValueError。"""
    if not _REF_RE.match(s):
        raise ValueError(f"无效的 git ref: {s!r}")
    return s


class GitToolsMiddleware(AgentMiddleware):
    """为 agent 提供 git 分析工具的中间件。"""

    TOOL_NAMES = ("git_show", "git_diff", "git_log_range")

    def __init__(
        self,
        repo_path_map: dict[str, str] | None = None,
        tools_whitelist: frozenset[str] | None = None,
    ):
        """
        Args:
            repo_path_map: 项目名 → 真实仓库路径
                例: {"backend-api": "D:/repos/backend-api"}
                单项目时可传 {"default": "/path/to/repo"}
            tools_whitelist: 限制暴露的工具集，默认全部
        """
        self._repo_path_map = repo_path_map or {}
        self._tools_whitelist = tools_whitelist
        self.tools = self._build_tools()

    def _resolve_repo(self, project: str | None) -> str:
        """根据 project 名称解析真实仓库路径。"""
        if not self._repo_path_map:
            raise ValueError("没有可用的项目仓库路径配置")

        if len(self._repo_path_map) == 1:
            # 单项目：忽略 project 参数，直接返回唯一路径
            return next(iter(self._repo_path_map.values()))

        if not project:
            available = "、".join(self._repo_path_map.keys())
            raise ValueError(f"多项目环境下必须指定 project 参数。可用项目: {available}")

        repo_path = self._repo_path_map.get(project)
        if not repo_path:
            available = "、".join(self._repo_path_map.keys())
            raise ValueError(f"未知项目: {project!r}。可用项目: {available}")
        return repo_path

    def _build_tools(self) -> list[StructuredTool]:
        """构建 git 工具列表。"""
        from service.git_ops import diff_commit, log_range, show_commit

        tools: list[StructuredTool] = []

        # ── git_show ──
        def git_show(
            commit_sha: Annotated[str, "commit SHA（4-40 位十六进制）"],
            project: Annotated[str | None, "项目名称（多项目时必填）"] = None,
            stat_only: Annotated[bool, "仅返回 --stat 统计信息"] = False,
        ) -> str:
            """获取 commit 详细信息，包括作者、日期、提交消息和变更内容。"""
            try:
                _validate_sha(commit_sha)
                repo_path = self._resolve_repo(project)
            except ValueError as e:
                return f"错误: {e}"
            result = show_commit(repo_path, commit_sha, stat_only=stat_only)
            if result is None:
                return f"错误: 无法获取 commit {commit_sha} 的信息，请确认 SHA 是否正确"
            return truncate_if_too_long(result)

        # ── git_diff ──
        def git_diff(
            commit_sha: Annotated[str, "commit SHA（4-40 位十六进制）"],
            project: Annotated[str | None, "项目名称（多项目时必填）"] = None,
            file_path: Annotated[str | None, "只看指定文件的变更"] = None,
            context_lines: Annotated[int, "diff 上下文行数"] = 3,
            stat_only: Annotated[bool, "仅返回 --stat 统计信息"] = False,
        ) -> str:
            """获取 commit 的代码变更（unified diff 格式）。"""
            try:
                _validate_sha(commit_sha)
                repo_path = self._resolve_repo(project)
            except ValueError as e:
                return f"错误: {e}"
            result = diff_commit(
                repo_path, commit_sha,
                file_path=file_path,
                context_lines=context_lines,
                stat_only=stat_only,
            )
            if result is None:
                return f"错误: 无法获取 commit {commit_sha} 的 diff，请确认 SHA 是否正确"
            if not result.strip():
                return "该 commit 没有代码变更（可能是 merge commit 或空提交）"
            return truncate_if_too_long(result)

        # ── git_log_range ──
        def git_log_range(
            to_ref: Annotated[str, "结束 ref（默认 HEAD）"] = "HEAD",
            from_ref: Annotated[str | None, "起始 ref（不含），用于范围查询 from..to"] = None,
            project: Annotated[str | None, "项目名称（多项目时必填）"] = None,
            path: Annotated[str | None, "只看指定路径的提交"] = None,
            max_count: Annotated[int, "最大返回条数（1-200）"] = 50,
            show_stat: Annotated[bool, "是否显示每个 commit 的 --stat"] = False,
        ) -> str:
            """获取 ref 范围内的提交列表。"""
            try:
                _validate_ref(to_ref)
                if from_ref:
                    _validate_ref(from_ref)
                repo_path = self._resolve_repo(project)
            except ValueError as e:
                return f"错误: {e}"
            result = log_range(
                repo_path,
                from_ref=from_ref,
                to_ref=to_ref,
                path=path,
                max_count=max_count,
                show_stat=show_stat,
            )
            if result is None:
                return f"错误: 无法获取提交列表，请确认 ref 是否正确"
            if not result.strip():
                return "指定范围内没有提交记录"
            return truncate_if_too_long(result)

        # 构造 StructuredTool
        tool_defs = [
            ("git_show", git_show, "获取 commit 详细信息，包括作者、日期、提交消息和变更内容。stat_only=True 时只返回变更统计。"),
            ("git_diff", git_diff, "获取 commit 的代码变更（unified diff 格式）。可指定文件和上下文行数。"),
            ("git_log_range", git_log_range, "获取 ref 范围内的提交列表。支持路径过滤和 --stat 统计。"),
        ]

        for name, func, description in tool_defs:
            if self._tools_whitelist and name not in self._tools_whitelist:
                continue
            tools.append(StructuredTool.from_function(
                func=func,
                name=name,
                description=description,
            ))

        return tools

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """在 system prompt 中注入 git 工具使用说明。"""
        new_system_message = append_to_system_message(
            request.system_message,
            GIT_TOOLS_SYSTEM_PROMPT,
        )
        return handler(request.override(system_message=new_system_message))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """（async）在 system prompt 中注入 git 工具使用说明。"""
        new_system_message = append_to_system_message(
            request.system_message,
            GIT_TOOLS_SYSTEM_PROMPT,
        )
        return await handler(request.override(system_message=new_system_message))
