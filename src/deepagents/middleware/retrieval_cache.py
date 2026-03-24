"""Middleware for caching read-only tool results across sub-agents.

Provides a shared, thread-safe cache that prevents duplicate retrieval
operations when multiple sub-agents run in parallel or serially within
the same session.

Cache key naming convention: ``{tool_category}:{semantic_key}``
  - File system:  ``grep:keyword@/path``, ``read_file:/path#L1-50``
  - Git:          ``git_show:sha@project``, ``git_diff:sha@project:file``
  - Graph:        ``nexus_search:query@project?label=Class``
"""

import hashlib
import logging
import threading
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

logger = logging.getLogger(__name__)

_CACHEABLE_TOOLS: frozenset[str] = frozenset({
    "grep", "glob", "read_file", "ls",
    "git_show", "git_diff", "git_log_range",
    "nexus_search", "nexus_cypher", "nexus_explore",
    "nexus_overview", "nexus_impact",
})


class RetrievalCache:
    """Thread-safe, session-scoped cache for read-only tool results.

    Instances are meant to be shared across all sub-agents in a single
    agent session so that identical queries are not executed twice.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    # ── public API ──

    def get(self, key: str) -> str | None:
        with self._lock:
            val = self._store.get(key)
            if val is not None:
                self._hits += 1
                logger.debug("CACHE HIT: %s", key)
            else:
                self._misses += 1
                logger.debug("CACHE MISS: %s", key)
            return val

    def put(self, key: str, value: str) -> None:
        with self._lock:
            self._store[key] = value

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    @property
    def stats(self) -> dict[str, int]:
        with self._lock:
            return {"hits": self._hits, "misses": self._misses, "size": len(self._store)}

    # ── key builders (见名知意 naming convention) ──

    @staticmethod
    def build_key(tool_name: str, args: dict[str, Any]) -> str:
        """Dispatch to the tool-specific key builder."""
        builder = _KEY_BUILDERS.get(tool_name)
        if builder is None:
            return _generic_key(tool_name, args)
        return builder(args)


def _arg(args: dict, name: str, default: str = "") -> str:
    val = args.get(name)
    return str(val).strip() if val else default


# ── file system key builders ──

def _key_grep(args: dict) -> str:
    keyword = _arg(args, "pattern") or _arg(args, "keyword") or _arg(args, "query")
    path = _arg(args, "path", "/")
    include = _arg(args, "include")
    base = f"grep:{keyword}@{path}"
    if include:
        base += f"?pattern={include}"
    return base


def _key_glob(args: dict) -> str:
    pattern = _arg(args, "pattern")
    path = _arg(args, "path", "/")
    return f"glob:{pattern}@{path}"


def _key_read_file(args: dict) -> str:
    path = _arg(args, "path")
    offset = args.get("offset")
    limit = args.get("limit")
    if offset is not None or limit is not None:
        return f"read_file:{path}#L{offset or 0}-{limit or 'end'}"
    return f"read_file:{path}"


def _key_ls(args: dict) -> str:
    path = _arg(args, "path", "/")
    return f"ls:{path}"


# ── git key builders ──

def _key_git_show(args: dict) -> str:
    sha = _arg(args, "commit_sha")
    project = _arg(args, "project", "default")
    stat = args.get("stat_only")
    base = f"git_show:{sha}@{project}"
    if stat:
        base += "?stat"
    return base


def _key_git_diff(args: dict) -> str:
    sha = _arg(args, "commit_sha")
    project = _arg(args, "project", "default")
    file_path = _arg(args, "file_path")
    if file_path:
        return f"git_diff:{sha}@{project}:{file_path}"
    return f"git_diff:{sha}@{project}"


def _key_git_log_range(args: dict) -> str:
    range_spec = _arg(args, "range") or _arg(args, "revision_range")
    project = _arg(args, "project", "default")
    path = _arg(args, "path")
    base = f"git_log:{range_spec}@{project}"
    if path:
        base += f":{path}"
    return base


# ── nexus key builders ──

def _key_nexus_search(args: dict) -> str:
    query = _arg(args, "query")
    project = _arg(args, "project", "default")
    label = _arg(args, "label_filter")
    base = f"nexus_search:{query}@{project}"
    if label:
        base += f"?label={label}"
    return base


def _key_nexus_cypher(args: dict) -> str:
    query = _arg(args, "query")
    digest = hashlib.sha256(query.encode()).hexdigest()[:12]
    return f"nexus_cypher:{digest}"


def _key_nexus_explore(args: dict) -> str:
    node_id = _arg(args, "node_id")
    project = _arg(args, "project", "default")
    depth = args.get("depth", 1)
    return f"nexus_explore:{node_id}@{project}?depth={depth}"


def _key_nexus_overview(args: dict) -> str:
    project = _arg(args, "project", "default")
    return f"nexus_overview:{project}"


def _key_nexus_impact(args: dict) -> str:
    node_id = _arg(args, "node_id")
    project = _arg(args, "project", "default")
    depth = args.get("depth", 2)
    return f"nexus_impact:{node_id}@{project}?depth={depth}"


def _generic_key(tool_name: str, args: dict) -> str:
    """Fallback: deterministic hash of all args."""
    raw = f"{tool_name}:{sorted(args.items())}"
    return f"{tool_name}:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


_KEY_BUILDERS: dict[str, Callable[[dict], str]] = {
    "grep": _key_grep,
    "glob": _key_glob,
    "read_file": _key_read_file,
    "ls": _key_ls,
    "git_show": _key_git_show,
    "git_diff": _key_git_diff,
    "git_log_range": _key_git_log_range,
    "nexus_search": _key_nexus_search,
    "nexus_cypher": _key_nexus_cypher,
    "nexus_explore": _key_nexus_explore,
    "nexus_overview": _key_nexus_overview,
    "nexus_impact": _key_nexus_impact,
}


def _extract_text(result: ToolMessage | Command) -> str | None:
    """Extract the text content from a tool result for caching."""
    if isinstance(result, ToolMessage):
        content = result.content
        return content if isinstance(content, str) else str(content)
    return None


class RetrievalCacheMiddleware(AgentMiddleware):
    """Middleware that caches read-only tool results to avoid duplicate retrieval.

    Intercepts tool calls via ``wrap_tool_call`` / ``awrap_tool_call``.
    Only caches tools listed in ``_CACHEABLE_TOOLS``; write operations
    are always passed through unmodified.

    Args:
        cache: A shared ``RetrievalCache`` instance (typically one per agent session).
        cacheable_tools: Override the set of tool names to cache.
    """

    def __init__(
        self,
        cache: RetrievalCache,
        cacheable_tools: frozenset[str] | None = None,
    ) -> None:
        super().__init__()
        self._cache = cache
        self._cacheable = cacheable_tools or _CACHEABLE_TOOLS

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        tool_name = request.tool_call.get("name", "")
        if tool_name not in self._cacheable:
            return handler(request)

        args = request.tool_call.get("args", {})
        cache_key = RetrievalCache.build_key(tool_name, args)
        cached = self._cache.get(cache_key)
        if cached is not None:
            tool_call_id = request.tool_call.get("id", "")
            return ToolMessage(content=cached, tool_call_id=tool_call_id, name=tool_name)

        result = handler(request)
        text = _extract_text(result)
        if text is not None:
            self._cache.put(cache_key, text)
        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        tool_name = request.tool_call.get("name", "")
        if tool_name not in self._cacheable:
            return await handler(request)

        args = request.tool_call.get("args", {})
        cache_key = RetrievalCache.build_key(tool_name, args)
        cached = self._cache.get(cache_key)
        if cached is not None:
            tool_call_id = request.tool_call.get("id", "")
            return ToolMessage(content=cached, tool_call_id=tool_call_id, name=tool_name)

        result = await handler(request)
        text = _extract_text(result)
        if text is not None:
            self._cache.put(cache_key, text)
        return result
