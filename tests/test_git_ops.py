"""Unit tests for service.git_ops (Phase 4); mock subprocess."""

from unittest.mock import patch, MagicMock

import pytest

from service import git_ops


class TestGetBranches:
    def test_non_repo_returns_empty_list(self):
        result = git_ops.get_branches("/nonexistent/path")
        assert result == []

    def test_returns_branch_list_when_git_succeeds(self):
        with patch("service.git_ops.Path") as PathMock:
            PathMock.return_value.resolve.return_value.is_dir.return_value = True
            with patch("subprocess.run") as run:
                run.return_value = MagicMock(
                    returncode=0,
                    stdout="main\nfeat/x\n",
                )
                result = git_ops.get_branches("/tmp/repo")
        assert result == ["main", "feat/x"]

    def test_returns_empty_on_git_failure(self):
        with patch("service.git_ops.Path") as PathMock:
            PathMock.return_value.resolve.return_value.is_dir.return_value = True
            with patch("subprocess.run") as run:
                run.return_value = MagicMock(returncode=1, stdout="")
                result = git_ops.get_branches("/tmp/repo")
        assert result == []


class TestGetHeadCommit:
    def test_non_repo_returns_none(self):
        result = git_ops.get_head_commit("/nonexistent")
        assert result is None

    def test_returns_sha_when_git_succeeds(self):
        sha = "a" * 40
        with patch("service.git_ops.Path") as PathMock:
            PathMock.return_value.resolve.return_value.is_dir.return_value = True
            with patch("subprocess.run") as run:
                run.return_value = MagicMock(returncode=0, stdout=sha + "\n")
                result = git_ops.get_head_commit("/tmp/repo", "main")
        assert result == sha

    def test_returns_none_on_git_failure(self):
        with patch("service.git_ops.Path") as PathMock:
            PathMock.return_value.resolve.return_value.is_dir.return_value = True
            with patch("subprocess.run") as run:
                run.return_value = MagicMock(returncode=1, stdout="")
                result = git_ops.get_head_commit("/tmp/repo", "main")
        assert result is None


class TestListCommits:
    def test_non_repo_returns_empty_list(self):
        result = git_ops.list_commits("/nonexistent", "main")
        assert result == []

    def test_parses_git_log_format(self):
        # One commit: sha, subject, author, date
        out = "abc123\nSubject line\nAlice\n2024-01-15T10:00:00+00:00\n"
        with patch("service.git_ops.Path") as PathMock:
            PathMock.return_value.resolve.return_value.is_dir.return_value = True
            with patch("subprocess.run") as run:
                run.return_value = MagicMock(returncode=0, stdout=out)
                result = git_ops.list_commits("/tmp/repo", "main")
        assert len(result) == 1
        assert result[0]["commit_sha"] == "abc123"
        assert result[0]["message"] == "Subject line"
        assert result[0]["author"] == "Alice"
        assert result[0]["committed_at"] == "2024-01-15T10:00:00+00:00"

    def test_multiple_commits(self):
        out = (
            "sha1\nmsg1\na1\nd1\n"
            "sha2\nmsg2\na2\nd2\n"
        )
        with patch("service.git_ops.Path") as PathMock:
            PathMock.return_value.resolve.return_value.is_dir.return_value = True
            with patch("subprocess.run") as run:
                run.return_value = MagicMock(returncode=0, stdout=out)
                result = git_ops.list_commits("/tmp/repo", "main", since_sha="base")
        assert len(result) == 2
        assert result[0]["commit_sha"] == "sha1" and result[1]["commit_sha"] == "sha2"
