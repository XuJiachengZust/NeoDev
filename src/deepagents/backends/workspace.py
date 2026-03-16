"""`SandboxWorkspaceBackend`: 基于临时目录的沙箱工作空间。

子智能体将详细报告写入磁盘，父智能体按需读取。
每轮对话可通过 reset() 自动清理并重建工作空间。
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from deepagents.backends.filesystem import FilesystemBackend


class SandboxWorkspaceBackend(FilesystemBackend):
    """基于临时目录的沙箱工作空间后端。

    继承 FilesystemBackend，自动创建和管理临时磁盘目录。
    使用 virtual_mode=True 保证路径沙箱隔离，
    files_update 始终为 None（文件只在磁盘，不进 state）。

    典型用法::

        workspace = SandboxWorkspaceBackend()
        workspace.write("/reports/analysis.md", "# 分析报告\\n...")
        content = workspace.read("/reports/analysis.md")
        workspace.cleanup()  # 清理临时目录
    """

    def __init__(
        self,
        base_dir: str | Path | None = None,
        prefix: str = "workspace_",
    ) -> None:
        """初始化沙箱工作空间。

        Args:
            base_dir: 临时目录的父目录。None 则使用系统默认临时目录。
            prefix: 临时目录名前缀。
        """
        self._base_dir = str(base_dir) if base_dir else None
        self._prefix = prefix
        tmpdir = tempfile.mkdtemp(dir=self._base_dir, prefix=self._prefix)
        self._tmpdir = Path(tmpdir)
        self._init_workspace_dirs()
        super().__init__(root_dir=self._tmpdir, virtual_mode=True)

    def _init_workspace_dirs(self) -> None:
        """创建工作空间标准子目录。"""
        (self._tmpdir / "reports").mkdir(exist_ok=True)
        (self._tmpdir / "artifacts").mkdir(exist_ok=True)

    @property
    def workspace_path(self) -> Path:
        """返回工作空间根目录的绝对路径。"""
        return self._tmpdir

    def cleanup(self) -> None:
        """删除整个临时工作空间目录。"""
        if self._tmpdir.exists():
            shutil.rmtree(self._tmpdir, ignore_errors=True)

    def reset(self) -> None:
        """清理旧工作空间并创建新的临时目录。

        cleanup() + 重新创建目录 + 更新 self.cwd。
        """
        self.cleanup()
        tmpdir = tempfile.mkdtemp(dir=self._base_dir, prefix=self._prefix)
        self._tmpdir = Path(tmpdir)
        self._init_workspace_dirs()
        self.cwd = self._tmpdir
