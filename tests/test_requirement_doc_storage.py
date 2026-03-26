"""RequirementDocStorage 单元测试：读写、版本归档、list_versions。"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from service.storage import RequirementDocStorage


@pytest.fixture
def doc_tmp_path():
    base = Path("D:/PycharmProjects/NeoDev/tests/.tmp_requirement_docs")
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class TestRequirementDocStorage:
    """文件系统存储层：按 product_id/requirement_id 读写 doc.md 与 versions/。"""

    def test_read_missing_returns_none(self, doc_tmp_path):
        storage = RequirementDocStorage(root=str(doc_tmp_path))
        assert storage.read(1, 100) is None

    def test_write_first_version_creates_doc_md(self, doc_tmp_path):
        storage = RequirementDocStorage(root=str(doc_tmp_path))
        path = storage.write(1, 100, "# Hello\n", version=1)
        assert path.is_file()
        assert path.name == "doc.md"
        assert path.parent == doc_tmp_path / "1" / "100"
        assert storage.read(1, 100) == "# Hello\n"

    def test_write_archives_previous_version(self, doc_tmp_path):
        storage = RequirementDocStorage(root=str(doc_tmp_path))
        storage.write(1, 100, "v1 content", version=1)
        storage.write(1, 100, "v2 content", version=2)
        assert storage.read(1, 100) == "v2 content"
        assert storage.list_versions(1, 100) == [1]
        assert storage.read_version(1, 100, 1) == "v1 content"

    def test_list_versions_multiple(self, doc_tmp_path):
        storage = RequirementDocStorage(root=str(doc_tmp_path))
        storage.write(1, 100, "v1", version=1)
        storage.write(1, 100, "v2", version=2)
        storage.write(1, 100, "v3", version=3)
        assert storage.list_versions(1, 100) == [1, 2]
        assert storage.read_version(1, 100, 1) == "v1"
        assert storage.read_version(1, 100, 2) == "v2"
        assert storage.read_version(1, 100, 3) is None  # 当前版本在 doc.md，不在 versions

    def test_exists(self, doc_tmp_path):
        storage = RequirementDocStorage(root=str(doc_tmp_path))
        assert storage.exists(1, 100) is False
        storage.write(1, 100, "x", version=1)
        assert storage.exists(1, 100) is True

    def test_delete_removes_directory(self, doc_tmp_path):
        storage = RequirementDocStorage(root=str(doc_tmp_path))
        storage.write(1, 100, "x", version=1)
        assert storage.exists(1, 100) is True
        assert storage.delete(1, 100) is True
        assert storage.exists(1, 100) is False
        assert storage.read(1, 100) is None

    def test_delete_missing_returns_false(self, doc_tmp_path):
        storage = RequirementDocStorage(root=str(doc_tmp_path))
        assert storage.delete(1, 100) is False

    def test_read_version_missing_returns_none(self, doc_tmp_path):
        storage = RequirementDocStorage(root=str(doc_tmp_path))
        storage.write(1, 100, "v1", version=1)
        assert storage.read_version(1, 100, 99) is None
        assert storage.read_version(1, 100, 0) is None

    def test_list_versions_ignores_non_version_files(self, doc_tmp_path):
        storage = RequirementDocStorage(root=str(doc_tmp_path))
        storage.write(1, 100, "v1", version=1)
        versions_dir = Path(doc_tmp_path) / "1" / "100" / "versions"
        versions_dir.mkdir(exist_ok=True)
        (versions_dir / "notes.md").write_text("ignore", encoding="utf-8")
        (versions_dir / "vbad.md").write_text("ignore", encoding="utf-8")
        (versions_dir / "v0.md").write_text("ignore", encoding="utf-8")

        assert storage.list_versions(1, 100) == []
