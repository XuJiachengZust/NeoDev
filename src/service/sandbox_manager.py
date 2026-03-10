"""Session Sandbox Manager: 基于 LocalShellBackend 的本地沙箱管理。

每个会话对应一个沙箱目录，用于隔离代码执行环境。
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path

from deepagents.backends.local_shell import LocalShellBackend

logger = logging.getLogger(__name__)

# 沙箱根目录（默认在项目根的 .sandboxes 下）
_SANDBOX_ROOT: Path | None = None

# session_id → LocalShellBackend 缓存
_sandbox_cache: dict[str, LocalShellBackend] = {}


def _get_sandbox_root() -> Path:
    """获取沙箱根目录。"""
    global _SANDBOX_ROOT
    if _SANDBOX_ROOT is None:
        base = os.environ.get("AGENT_SANDBOX_ROOT", "").strip()
        if base:
            _SANDBOX_ROOT = Path(base)
        else:
            # 项目根/.sandboxes
            root = Path(__file__).resolve().parent.parent.parent
            _SANDBOX_ROOT = root / ".sandboxes"
        _SANDBOX_ROOT.mkdir(parents=True, exist_ok=True)
    return _SANDBOX_ROOT


def ensure_sandbox(session_id: str) -> LocalShellBackend:
    """创建或复用会话沙箱，返回 LocalShellBackend 实例。"""
    if session_id in _sandbox_cache:
        return _sandbox_cache[session_id]

    sandbox_dir = _get_sandbox_root() / session_id
    sandbox_dir.mkdir(parents=True, exist_ok=True)

    backend = LocalShellBackend(root_dir=sandbox_dir)
    _sandbox_cache[session_id] = backend

    logger.info("沙箱已创建/复用: session=%s path=%s", session_id, sandbox_dir)
    return backend


def get_sandbox_path(session_id: str) -> Path:
    """获取沙箱目录路径。"""
    return _get_sandbox_root() / session_id


def recycle_sandbox(session_id: str) -> bool:
    """回收会话沙箱：清理目录和缓存。"""
    backend = _sandbox_cache.pop(session_id, None)
    sandbox_dir = _get_sandbox_root() / session_id

    if sandbox_dir.exists():
        try:
            shutil.rmtree(sandbox_dir)
            logger.info("沙箱已回收: session=%s", session_id)
            return True
        except Exception:
            logger.exception("沙箱回收失败: session=%s", session_id)
            return False

    return False


def list_sandboxes() -> list[str]:
    """列出所有活跃沙箱的 session_id。"""
    root = _get_sandbox_root()
    if not root.exists():
        return []
    return [d.name for d in root.iterdir() if d.is_dir()]
