"""GitReadOnlyBackend: 通过 git 对象存储读取指定分支文件，无需 checkout。

解决多用户并发使用不同分支时的竞争条件问题。
所有读操作通过 git show / git ls-tree / git grep 实现，写操作全部拒绝。
"""

import fnmatch
import logging
import re
import subprocess
from pathlib import Path

from deepagents.backends.protocol import (
    BackendProtocol,
    EditResult,
    FileDownloadResponse,
    FileInfo,
    FileUploadResponse,
    GrepMatch,
    WriteResult,
)
from deepagents.backends.utils import (
    check_empty_content,
    format_content_with_line_numbers,
)
from service.git_ops import _resolve_ref

logger = logging.getLogger(__name__)

_READONLY_ERROR = "permission_denied: 此目录为只读挂载（git分支模式），不允许写入操作"
_TIMEOUT = 15


class GitReadOnlyBackend(BackendProtocol):
    """通过 git 对象存储读取指定分支的文件，无需 checkout。"""

    def __init__(self, repo_dir: str | Path, branch: str):
        self.repo_dir = Path(repo_dir).resolve()
        self.branch = branch
        self.ref = _resolve_ref(self.repo_dir, branch)

    # ── 路径处理 ──────────────────────────────────────────────────────

    def _to_rel(self, path: str) -> str:
        """将虚拟路径转换为仓库相对路径，防止路径穿越。"""
        if not path or path == "/":
            return ""
        # 去掉前导 /
        rel = path.lstrip("/")
        # 防止路径穿越
        if ".." in rel.split("/") or "~" in rel:
            raise ValueError(f"路径不安全: {path}")
        return rel

    # ── read ──────────────────────────────────────────────────────────

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        try:
            rel = self._to_rel(file_path)
        except ValueError as e:
            return f"Error: {e}"

        if not rel:
            return "Error: 请指定文件路径"

        try:
            result = subprocess.run(
                ["git", "show", f"{self.ref}:{rel}"],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"Error: 读取文件超时 '{file_path}'"

        if result.returncode != 0:
            return f"Error: File '{file_path}' not found on branch {self.branch}"

        content = result.stdout
        empty_msg = check_empty_content(content)
        if empty_msg:
            return empty_msg

        lines = content.splitlines()
        start_idx = offset
        end_idx = min(start_idx + limit, len(lines))

        if start_idx >= len(lines):
            return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

        selected = lines[start_idx:end_idx]
        return format_content_with_line_numbers(selected, start_line=start_idx + 1)

    # ── ls_info ───────────────────────────────────────────────────────

    def ls_info(self, path: str) -> list[FileInfo]:
        try:
            rel = self._to_rel(path)
        except ValueError:
            return []

        tree_path = f"{rel}/" if rel else ""
        try:
            result = subprocess.run(
                ["git", "ls-tree", "--long", self.ref, tree_path],
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
        except subprocess.TimeoutExpired:
            return []

        if result.returncode != 0:
            return []

        entries: list[FileInfo] = []
        # 格式: "<mode> <type> <hash> <size>\t<name>"
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            match = re.match(r"(\d+)\s+(blob|tree)\s+\w+\s+(-|\d+)\t(.+)", line)
            if not match:
                continue
            obj_type = match.group(2)
            size_str = match.group(3)
            name = match.group(4)

            is_dir = obj_type == "tree"
            size = 0 if size_str == "-" else int(size_str)

            # 构造虚拟绝对路径
            vpath = f"/{name}" if not name.startswith("/") else name
            entries.append(FileInfo(path=vpath, is_dir=is_dir, size=size))

        return entries

    # ── glob_info ─────────────────────────────────────────────────────

    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        try:
            rel = self._to_rel(path)
        except ValueError:
            return []

        cmd = ["git", "ls-tree", "-r", "--name-only", self.ref]
        if rel:
            # ls-tree -r 不支持路径前缀过滤，获取全部后手动过滤
            pass

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return []

        if result.returncode != 0:
            return []

        entries: list[FileInfo] = []
        for line in result.stdout.strip().splitlines():
            name = line.strip()
            if not name:
                continue

            # 如果有 path 限制，过滤不在该路径下的文件
            if rel and not name.startswith(rel + "/") and name != rel:
                continue

            # 获取相对于 path 的名称用于 glob 匹配
            if rel:
                relative = name[len(rel) + 1:] if name.startswith(rel + "/") else name
            else:
                relative = name

            if fnmatch.fnmatch(relative, pattern):
                vpath = f"/{name}"
                entries.append(FileInfo(path=vpath, is_dir=False))

        return entries

    # ── grep_raw ──────────────────────────────────────────────────────

    def grep_raw(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> list[GrepMatch] | str:
        cmd = ["git", "grep", "-n", "-F", "--", pattern, self.ref]

        if path:
            try:
                rel = self._to_rel(path)
            except ValueError as e:
                return str(e)
            if rel:
                cmd.append(rel)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return "Error: grep 操作超时"

        # exit code 1 = 无匹配，不是错误
        if result.returncode not in (0, 1):
            return f"Error: git grep failed: {result.stderr.strip()}"

        if result.returncode == 1 or not result.stdout.strip():
            return []

        matches: list[GrepMatch] = []
        # 输出格式: "{ref}:{file}:{line}:{text}"
        ref_prefix = f"{self.ref}:"
        for line in result.stdout.strip().splitlines():
            if not line.startswith(ref_prefix):
                continue
            rest = line[len(ref_prefix):]
            # 解析 "file:line:text"
            parts = rest.split(":", 2)
            if len(parts) < 3:
                continue
            file_path = parts[0]
            try:
                line_num = int(parts[1])
            except ValueError:
                continue
            text = parts[2]

            # glob 过滤
            if glob and not fnmatch.fnmatch(file_path, glob):
                continue

            vpath = f"/{file_path}"
            matches.append(GrepMatch(path=vpath, line=line_num, text=text))

        return matches

    # ── download_files ────────────────────────────────────────────────

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        responses = []
        for p in paths:
            try:
                rel = self._to_rel(p)
            except ValueError:
                responses.append(FileDownloadResponse(path=p, error="invalid_path"))
                continue

            if not rel:
                responses.append(FileDownloadResponse(path=p, error="is_directory"))
                continue

            try:
                result = subprocess.run(
                    ["git", "show", f"{self.ref}:{rel}"],
                    cwd=self.repo_dir,
                    capture_output=True,
                    timeout=_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                responses.append(FileDownloadResponse(path=p, error="file_not_found"))
                continue

            if result.returncode != 0:
                responses.append(FileDownloadResponse(path=p, error="file_not_found"))
            else:
                responses.append(FileDownloadResponse(path=p, content=result.stdout))

        return responses

    # ── 写操作拒绝 ────────────────────────────────────────────────────

    def write(self, file_path: str, content: str) -> WriteResult:
        return WriteResult(error=_READONLY_ERROR)

    async def awrite(self, file_path: str, content: str) -> WriteResult:
        return WriteResult(error=_READONLY_ERROR)

    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        return EditResult(error=_READONLY_ERROR)

    async def aedit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        return EditResult(error=_READONLY_ERROR)

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return [FileUploadResponse(path=f[0], error="permission_denied") for f in files]

    async def aupload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return self.upload_files(files)
