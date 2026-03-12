"""全局 LangGraph Checkpointer：基于 PostgreSQL 的对话状态持久化。

使用 psycopg (v3) AsyncConnectionPool + AsyncPostgresSaver，
使 agent 在请求间通过 thread_id 恢复完整对话上下文。

生命周期由 FastAPI startup/shutdown 事件管理。
"""

import logging
import os

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# 全局单例
_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None


def _get_conninfo() -> str:
    """构建 psycopg v3 连接字符串。

    优先读取 DATABASE_URL 环境变量，否则使用默认值。
    psycopg v3 兼容标准 postgresql:// URI。
    """
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/neodev",
    )


async def init_checkpointer() -> AsyncPostgresSaver:
    """初始化连接池和 checkpointer，创建所需的数据库表。

    应在 FastAPI startup 事件中调用。
    """
    global _pool, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    conninfo = _get_conninfo()
    logger.info("初始化 LangGraph Checkpointer 连接池...")

    _pool = AsyncConnectionPool(
        conninfo,
        min_size=2,
        max_size=10,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    await _pool.open()

    _checkpointer = AsyncPostgresSaver(_pool)
    await _checkpointer.setup()

    logger.info("LangGraph Checkpointer 就绪（PostgreSQL）")
    return _checkpointer


async def close_checkpointer() -> None:
    """关闭连接池，释放资源。

    应在 FastAPI shutdown 事件中调用。
    """
    global _pool, _checkpointer

    _checkpointer = None
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("LangGraph Checkpointer 连接池已关闭")


def get_checkpointer() -> AsyncPostgresSaver | None:
    """获取全局 checkpointer 实例。未初始化时返回 None。"""
    return _checkpointer
