"""GitReadOnlyBackend 单元测试。

使用真实 git 仓库（git init + 提交文件 + 创建分支）验证所有读操作。

deepagents.__init__ 会导入 langchain.agents.create_agent，
在没有完整 langchain 环境时会失败。所有 deepagents 导入用 try/except 包裹。
"""

import subprocess
from pathlib import Path

import pytest

try:
    from service.git_readonly_backend import GitReadOnlyBackend
    _HAS_BACKEND = True
except ImportError:
    _HAS_BACKEND = False

pytestmark = pytest.mark.skipif(
    not _HAS_BACKEND,
    reason="deepagents 依赖不可用（需要 langchain agents）",
)


@pytest.fixture()
def git_repo(tmp_path):
    """创建一个包含两个分支的 git 仓库。

    main 分支: hello.py, sub/module.py
    feature 分支: hello.py (修改版), feature_only.txt
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args, **kwargs):
        return subprocess.run(
            args, cwd=repo, capture_output=True, text=True,
            encoding="utf-8", timeout=10, **kwargs,
        )

    run("git", "init")
    run("git", "config", "user.email", "test@test.com")
    run("git", "config", "user.name", "Test")

    # main 分支内容
    (repo / "hello.py").write_text("print('hello')\nprint('world')\n", encoding="utf-8")
    (repo / "sub").mkdir()
    (repo / "sub" / "module.py").write_text("import os\n\ndef func():\n    return 42\n", encoding="utf-8")
    (repo / "readme.txt").write_text("README content\n", encoding="utf-8")
    run("git", "add", ".")
    run("git", "commit", "-m", "initial")

    # 创建 feature 分支
    run("git", "checkout", "-b", "feature")
    (repo / "hello.py").write_text("print('hello feature')\nprint('world')\nprint('new line')\n", encoding="utf-8")
    (repo / "feature_only.txt").write_text("feature content\n", encoding="utf-8")
    run("git", "add", ".")
    run("git", "commit", "-m", "feature changes")

    # 回到 main
    run("git", "checkout", "master")
    # 如果默认分支不是 master，可能是 main
    r = run("git", "branch", "--show-current")
    default_branch = r.stdout.strip()
    if not default_branch:
        # 可能在 detached HEAD，尝试 main
        run("git", "checkout", "main")
        default_branch = "main"

    return repo, default_branch


class TestRead:
    def test_read_existing_file(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.read("/hello.py")
        assert "print('hello')" in result
        assert "print('world')" in result
        # 应包含行号
        assert "1\t" in result

    def test_read_with_offset_limit(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.read("/hello.py", offset=1, limit=1)
        assert "print('world')" in result
        assert "print('hello')" not in result

    def test_read_nonexistent_file(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.read("/nonexistent.py")
        assert "Error" in result
        assert "not found" in result

    def test_read_subdirectory_file(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.read("/sub/module.py")
        assert "import os" in result
        assert "return 42" in result

    def test_read_offset_exceeds_length(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.read("/hello.py", offset=1000)
        assert "Error" in result
        assert "exceeds" in result


class TestLsInfo:
    def test_ls_root(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        entries = backend.ls_info("/")
        names = [e["path"] for e in entries]
        assert any("hello.py" in n for n in names)
        assert any("readme.txt" in n for n in names)
        # sub 目录应标记为 is_dir
        sub_entries = [e for e in entries if "sub" in e["path"]]
        assert len(sub_entries) >= 1
        assert sub_entries[0].get("is_dir") is True

    def test_ls_subdirectory(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        entries = backend.ls_info("/sub")
        assert len(entries) >= 1
        assert any("module.py" in e["path"] for e in entries)

    def test_ls_nonexistent(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        entries = backend.ls_info("/nonexistent")
        assert entries == []


class TestGlobInfo:
    def test_glob_py_files(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        entries = backend.glob_info("*.py", "/")
        paths = [e["path"] for e in entries]
        # hello.py 在根目录，应匹配 *.py
        assert any("hello.py" in p for p in paths)

    def test_glob_recursive(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        entries = backend.glob_info("**/*.py", "/")
        paths = [e["path"] for e in entries]
        assert any("hello.py" in p for p in paths)
        assert any("module.py" in p for p in paths)

    def test_glob_in_subdir(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        entries = backend.glob_info("*.py", "/sub")
        paths = [e["path"] for e in entries]
        assert any("module.py" in p for p in paths)
        assert not any("hello.py" in p for p in paths)


class TestGrepRaw:
    def test_grep_basic(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        matches = backend.grep_raw("print")
        assert isinstance(matches, list)
        assert len(matches) >= 1
        assert all(isinstance(m, dict) for m in matches)
        assert all("path" in m and "line" in m and "text" in m for m in matches)

    def test_grep_no_match(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        matches = backend.grep_raw("NONEXISTENT_STRING_XYZ")
        assert matches == []

    def test_grep_with_path(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        matches = backend.grep_raw("import", path="/sub")
        assert isinstance(matches, list)
        assert len(matches) >= 1
        assert all("/sub/" in m["path"] for m in matches)

    def test_grep_with_glob_filter(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        matches = backend.grep_raw("print", glob="*.txt")
        # hello.py 中有 print，但 *.txt 不匹配
        assert all(".txt" in m["path"] for m in matches)


class TestMultiBranchIsolation:
    """验证不同分支读到不同内容。"""

    def test_main_branch_content(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.read("/hello.py")
        assert "print('hello')" in result
        assert "hello feature" not in result

    def test_feature_branch_content(self, git_repo):
        repo, _ = git_repo
        backend = GitReadOnlyBackend(repo, "feature")
        result = backend.read("/hello.py")
        assert "hello feature" in result

    def test_feature_only_file(self, git_repo):
        repo, branch = git_repo
        # main 分支没有 feature_only.txt
        backend_main = GitReadOnlyBackend(repo, branch)
        result = backend_main.read("/feature_only.txt")
        assert "Error" in result

        # feature 分支有
        backend_feature = GitReadOnlyBackend(repo, "feature")
        result = backend_feature.read("/feature_only.txt")
        assert "feature content" in result

    def test_concurrent_read_different_branches(self, git_repo):
        """同时创建两个 backend 指向不同分支，验证互不干扰。"""
        repo, branch = git_repo
        backend_main = GitReadOnlyBackend(repo, branch)
        backend_feature = GitReadOnlyBackend(repo, "feature")

        main_content = backend_main.read("/hello.py")
        feature_content = backend_feature.read("/hello.py")

        assert "hello feature" not in main_content
        assert "hello feature" in feature_content


class TestWriteOperationsRejected:
    def test_write_rejected(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.write("/test.py", "content")
        assert result.error is not None
        assert "permission_denied" in result.error

    def test_edit_rejected(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.edit("/hello.py", "old", "new")
        assert result.error is not None
        assert "permission_denied" in result.error

    def test_upload_rejected(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        results = backend.upload_files([("/test.py", b"content")])
        assert len(results) == 1
        assert results[0].error == "permission_denied"


class TestPathTraversal:
    def test_dotdot_rejected(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.read("/../etc/passwd")
        assert "Error" in result

    def test_tilde_rejected(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        result = backend.read("/~/.ssh/id_rsa")
        assert "Error" in result


class TestDownloadFiles:
    def test_download_existing(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        results = backend.download_files(["/hello.py"])
        assert len(results) == 1
        assert results[0].error is None
        assert results[0].content is not None
        assert b"print" in results[0].content

    def test_download_nonexistent(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        results = backend.download_files(["/nonexistent.py"])
        assert len(results) == 1
        assert results[0].error == "file_not_found"

    def test_download_path_traversal(self, git_repo):
        repo, branch = git_repo
        backend = GitReadOnlyBackend(repo, branch)
        results = backend.download_files(["/../etc/passwd"])
        assert len(results) == 1
        assert results[0].error == "invalid_path"
