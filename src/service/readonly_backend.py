"""ReadOnly Filesystem Backend: 包装 FilesystemBackend，拦截所有写操作。

用于项目目录的只读挂载，允许读取和搜索但禁止修改。
"""

from pathlib import Path

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import (
    EditResult,
    FileUploadResponse,
    WriteResult,
)

_READONLY_ERROR = "permission_denied: 此目录为只读挂载，不允许写入操作"


class ReadOnlyFilesystemBackend(FilesystemBackend):
    """只读文件系统后端：继承 FilesystemBackend 的读取能力，拦截所有写操作。"""

    def __init__(self, root_dir: str | Path):
        super().__init__(root_dir=root_dir)

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
