"""GitToolsMiddleware 和 git_ops 新函数的单元测试。"""

import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

from service.git_ops import diff_commit, log_range, show_commit

# deepagents.__init__ 会导入 langchain.agents.create_agent，
# 在没有完整 langchain 环境时会失败。尝试导入，不可用则跳过中间件测试。
try:
    from deepagents.middleware.git_tools import (
        GitToolsMiddleware,
        _validate_ref,
        _validate_sha,
    )
    _HAS_MIDDLEWARE = True
except ImportError:
    _HAS_MIDDLEWARE = False

needs_middleware = pytest.mark.skipif(
    not _HAS_MIDDLEWARE,
    reason="deepagents middleware 依赖不可用（需要 langchain agents）",
)


# ── TestGitOpsNewFunctions ──────────────────────────────────────────────


class TestShowCommit:
    """show_commit 正常/异常/超时场景。"""

    @patch("service.git_ops.subprocess.run")
    def test_normal(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="commit abc\nAuthor: test\n")
        result = show_commit(str(tmp_path), "abc123")
        assert result is not None
        assert "commit abc" in result
        cmd = mock_run.call_args[0][0]
        assert cmd[:3] == ["git", "show", "abc123"]
        assert "--stat" not in cmd

    @patch("service.git_ops.subprocess.run")
    def test_stat_only(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="1 file changed\n")
        result = show_commit(str(tmp_path), "abc123", stat_only=True)
        assert result is not None
        cmd = mock_run.call_args[0][0]
        assert "--stat" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        assert show_commit(str(tmp_path), "bad") is None

    @patch("service.git_ops.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30))
    def test_timeout(self, mock_run, tmp_path):
        assert show_commit(str(tmp_path), "abc123") is None

    def test_invalid_dir(self):
        assert show_commit("/nonexistent/path", "abc123") is None


class TestDiffCommit:
    """diff_commit 正常/异常/超时场景。"""

    @patch("service.git_ops.subprocess.run")
    def test_normal(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="diff --git a/f b/f\n")
        result = diff_commit(str(tmp_path), "abc123")
        assert result is not None
        cmd = mock_run.call_args[0][0]
        assert "abc123^..abc123" in cmd[2]
        assert "-U3" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_with_file_path(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="diff\n")
        diff_commit(str(tmp_path), "abc123", file_path="src/main.py")
        cmd = mock_run.call_args[0][0]
        assert "--" in cmd
        assert "src/main.py" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_stat_only(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="1 file\n")
        diff_commit(str(tmp_path), "abc123", stat_only=True)
        cmd = mock_run.call_args[0][0]
        assert "--stat" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_custom_context(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="diff\n")
        diff_commit(str(tmp_path), "abc123", context_lines=10)
        cmd = mock_run.call_args[0][0]
        assert "-U10" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        assert diff_commit(str(tmp_path), "bad") is None

    @patch("service.git_ops.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30))
    def test_timeout(self, mock_run, tmp_path):
        assert diff_commit(str(tmp_path), "abc123") is None


class TestLogRange:
    """log_range 正常/异常/超时场景。"""

    @patch("service.git_ops.subprocess.run")
    def test_normal(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="commit abc\n")
        result = log_range(str(tmp_path))
        assert result is not None
        cmd = mock_run.call_args[0][0]
        assert "HEAD" in cmd
        assert "--max-count=50" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_with_range(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="log\n")
        log_range(str(tmp_path), from_ref="v1.0", to_ref="v2.0")
        cmd = mock_run.call_args[0][0]
        assert "v1.0..v2.0" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_with_path(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="log\n")
        log_range(str(tmp_path), path="src/")
        cmd = mock_run.call_args[0][0]
        assert "--" in cmd
        assert "src/" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_with_stat(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="log\n")
        log_range(str(tmp_path), show_stat=True)
        cmd = mock_run.call_args[0][0]
        assert "--stat" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_max_count_clamp(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        log_range(str(tmp_path), max_count=999)
        cmd = mock_run.call_args[0][0]
        assert "--max-count=200" in cmd

        log_range(str(tmp_path), max_count=-5)
        cmd = mock_run.call_args[0][0]
        assert "--max-count=1" in cmd

    @patch("service.git_ops.subprocess.run")
    def test_failure(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=128, stdout="")
        assert log_range(str(tmp_path)) is None

    @patch("service.git_ops.subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30))
    def test_timeout(self, mock_run, tmp_path):
        assert log_range(str(tmp_path)) is None


# ── TestGitToolsMiddleware ──────────────────────────────────────────────


@needs_middleware
class TestGitToolsMiddleware:
    """中间件工具创建、whitelist 过滤、SHA/ref 校验。"""

    def test_creates_all_tools(self):
        mw = GitToolsMiddleware(repo_path_map={"proj": "/tmp/repo"})
        tools = mw._build_tools()
        names = {t.name for t in tools}
        assert names == {"git_show", "git_diff", "git_log_range"}

    def test_whitelist_filters(self):
        mw = GitToolsMiddleware(
            repo_path_map={"proj": "/tmp/repo"},
            tools_whitelist=frozenset({"git_show"}),
        )
        tools = mw._build_tools()
        assert len(tools) == 1
        assert tools[0].name == "git_show"

    def test_validate_sha_valid(self):
        assert _validate_sha("abcd") == "abcd"
        assert _validate_sha("a1b2c3d4e5f6") == "a1b2c3d4e5f6"
        assert _validate_sha("A" * 40) == "A" * 40

    def test_validate_sha_invalid(self):
        with pytest.raises(ValueError):
            _validate_sha("xyz")
        with pytest.raises(ValueError):
            _validate_sha("ab")  # 太短
        with pytest.raises(ValueError):
            _validate_sha("abcd; rm -rf /")

    def test_validate_ref_valid(self):
        assert _validate_ref("HEAD") == "HEAD"
        assert _validate_ref("main") == "main"
        assert _validate_ref("feature/my-branch") == "feature/my-branch"
        assert _validate_ref("v1.0.0") == "v1.0.0"

    def test_validate_ref_invalid(self):
        with pytest.raises(ValueError):
            _validate_ref("main; echo pwned")
        with pytest.raises(ValueError):
            _validate_ref("branch name with spaces")


# ── TestRepoPathResolution ──────────────────────────────────────────────


@needs_middleware
class TestRepoPathResolution:
    """_resolve_repo 单项目/多项目/未知项目场景。"""

    def test_single_project_ignores_param(self):
        mw = GitToolsMiddleware(repo_path_map={"only": "/path/to/repo"})
        assert mw._resolve_repo(None) == "/path/to/repo"
        assert mw._resolve_repo("anything") == "/path/to/repo"

    def test_multi_project_requires_param(self):
        mw = GitToolsMiddleware(repo_path_map={"a": "/a", "b": "/b"})
        with pytest.raises(ValueError, match="必须指定"):
            mw._resolve_repo(None)

    def test_multi_project_resolves(self):
        mw = GitToolsMiddleware(repo_path_map={"a": "/path/a", "b": "/path/b"})
        assert mw._resolve_repo("a") == "/path/a"
        assert mw._resolve_repo("b") == "/path/b"

    def test_multi_project_unknown(self):
        mw = GitToolsMiddleware(repo_path_map={"a": "/a", "b": "/b"})
        with pytest.raises(ValueError, match="未知项目"):
            mw._resolve_repo("c")

    def test_empty_map_raises(self):
        mw = GitToolsMiddleware(repo_path_map={})
        with pytest.raises(ValueError, match="没有可用"):
            mw._resolve_repo(None)
