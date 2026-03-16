"""需求文档文件系统存储：按 product_id/requirement_id 读写 doc.md 与 versions/。"""

import os
import shutil
from pathlib import Path


class RequirementDocStorage:
    """纯文件系统操作，不涉及数据库。"""

    def __init__(self, root: str | Path | None = None) -> None:
        if root is None:
            root = os.environ.get("REQUIREMENT_DOCS_ROOT", "/data/requirement_docs")
        self.root = Path(root)

    def _dir(self, product_id: int, requirement_id: int) -> Path:
        """返回该需求文档的目录路径。"""
        return self.root / str(product_id) / str(requirement_id)

    def _doc_path(self, product_id: int, requirement_id: int) -> Path:
        return self._dir(product_id, requirement_id) / "doc.md"

    def _versions_dir(self, product_id: int, requirement_id: int) -> Path:
        return self._dir(product_id, requirement_id) / "versions"

    def read(self, product_id: int, requirement_id: int) -> str | None:
        """读取当前版本文档内容；不存在则返回 None。"""
        path = self._doc_path(product_id, requirement_id)
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def write(
        self, product_id: int, requirement_id: int, content: str, version: int
    ) -> Path:
        """
        写入新内容并归档旧版本。
        先将当前 doc.md 拷贝为 versions/v{old_version}.md，再写入新内容到 doc.md。
        version 为写入后的新版本号（≥1）。
        """
        d = self._dir(product_id, requirement_id)
        d.mkdir(parents=True, exist_ok=True)
        doc_path = d / "doc.md"
        old_version = version - 1
        if old_version >= 1 and doc_path.is_file():
            versions_dir = self._versions_dir(product_id, requirement_id)
            versions_dir.mkdir(exist_ok=True)
            archive_path = versions_dir / f"v{old_version}.md"
            shutil.copy2(doc_path, archive_path)
        doc_path.write_text(content, encoding="utf-8")
        return doc_path

    def list_versions(self, product_id: int, requirement_id: int) -> list[int]:
        """列出已归档的版本号（versions/ 下的 vN.md），升序。不包含当前 doc.md 代表的版本。"""
        versions_dir = self._versions_dir(product_id, requirement_id)
        if not versions_dir.is_dir():
            return []
        result: list[int] = []
        for p in versions_dir.iterdir():
            if p.suffix == ".md" and p.stem.startswith("v"):
                try:
                    n = int(p.stem[1:])
                    if n >= 1:
                        result.append(n)
                except ValueError:
                    continue
        return sorted(result)

    def read_version(
        self, product_id: int, requirement_id: int, version: int
    ) -> str | None:
        """读取指定历史版本内容；不存在则返回 None。"""
        if version < 1:
            return None
        path = self._versions_dir(product_id, requirement_id) / f"v{version}.md"
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    def exists(self, product_id: int, requirement_id: int) -> bool:
        """是否存在当前文档（doc.md）。"""
        return self._doc_path(product_id, requirement_id).is_file()

    def delete(self, product_id: int, requirement_id: int) -> bool:
        """删除该需求下的整个文档目录（doc.md + versions/）。不存在则返回 False。"""
        d = self._dir(product_id, requirement_id)
        if not d.is_dir():
            return False
        shutil.rmtree(d)
        return True
