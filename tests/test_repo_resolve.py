"""TDD tests for resolve_repo_root and ensure_repo_from_url."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


def _git_init(path: str) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=path,
        capture_output=True,
        check=True,
        timeout=5,
    )


class TestResolveRepoRoot:
    def test_returns_absolute_root_when_given_repo_root(self):
        from gitnexus_parser.ingestion.repo_resolve import resolve_repo_root

        with tempfile.TemporaryDirectory() as tmp:
            _git_init(tmp)
            result = resolve_repo_root(tmp)
            assert result is not None
            assert os.path.isabs(result)
            assert os.path.normpath(result) == os.path.normpath(Path(tmp).resolve())

    def test_returns_repo_root_when_given_subdirectory(self):
        from gitnexus_parser.ingestion.repo_resolve import resolve_repo_root

        with tempfile.TemporaryDirectory() as tmp:
            _git_init(tmp)
            subdir = os.path.join(tmp, "a", "b")
            os.makedirs(subdir, exist_ok=True)
            result = resolve_repo_root(subdir)
            assert result is not None
            assert os.path.normpath(result) == os.path.normpath(Path(tmp).resolve())

    def test_returns_none_for_non_git_directory(self):
        from gitnexus_parser.ingestion.repo_resolve import resolve_repo_root

        with tempfile.TemporaryDirectory() as tmp:
            # no git init
            result = resolve_repo_root(tmp)
            assert result is None

    def test_returns_none_for_nonexistent_path(self):
        from gitnexus_parser.ingestion.repo_resolve import resolve_repo_root

        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "does_not_exist")
            result = resolve_repo_root(bad)
            assert result is None

    def test_returns_none_when_path_is_file(self):
        from gitnexus_parser.ingestion.repo_resolve import resolve_repo_root

        with tempfile.NamedTemporaryFile(delete=False) as f:
            try:
                result = resolve_repo_root(f.name)
                assert result is None
            finally:
                try:
                    os.unlink(f.name)
                except OSError:
                    pass

    def test_returned_path_is_consistent_with_resolve(self):
        from gitnexus_parser.ingestion.repo_resolve import resolve_repo_root

        with tempfile.TemporaryDirectory() as tmp:
            _git_init(tmp)
            result = resolve_repo_root(tmp)
            assert result is not None
            assert Path(result).resolve() == Path(tmp).resolve()


class TestEnsureRepoFromUrl:
    def test_clone_into_empty_dir_returns_repo_root(self):
        from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url, resolve_repo_root

        with tempfile.TemporaryDirectory() as parent:
            # Create a bare repo to clone from (no network)
            bare = os.path.join(parent, "bare.git")
            os.makedirs(bare, exist_ok=True)
            subprocess.run(["git", "init", "--bare"], cwd=bare, capture_output=True, check=True, timeout=5)
            repo_url = Path(bare).as_uri()

            target = os.path.join(parent, "clone")
            root = ensure_repo_from_url(repo_url, target)
            assert root is not None
            assert resolve_repo_root(target) == root
            assert os.path.normpath(root) == os.path.normpath(Path(target).resolve())

    def test_existing_repo_returns_same_root(self):
        from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url, resolve_repo_root

        with tempfile.TemporaryDirectory() as parent:
            bare = os.path.join(parent, "bare.git")
            os.makedirs(bare, exist_ok=True)
            subprocess.run(["git", "init", "--bare"], cwd=bare, capture_output=True, check=True, timeout=5)
            repo_url = Path(bare).as_uri()

            target = os.path.join(parent, "clone")
            root1 = ensure_repo_from_url(repo_url, target)
            root2 = ensure_repo_from_url(repo_url, target)
            assert root1 == root2
            assert root1 == resolve_repo_root(target)

    def test_existing_non_git_directory_raises(self):
        from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url

        with tempfile.TemporaryDirectory() as tmp:
            # tmp is not a git repo
            with pytest.raises((ValueError, OSError)) as exc_info:
                ensure_repo_from_url("https://github.com/some/repo.git", tmp)
            assert "repo" in str(exc_info.value).lower() or "git" in str(exc_info.value).lower()

    def test_invalid_url_raises(self):
        from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url

        with tempfile.TemporaryDirectory() as parent:
            target = os.path.join(parent, "nonexistent_clone")
            with pytest.raises(Exception):
                ensure_repo_from_url("https://invalid.invalid/nonexistent/repo.git", target)

    def test_return_value_equals_resolve_repo_root(self):
        from gitnexus_parser.ingestion.repo_resolve import ensure_repo_from_url, resolve_repo_root

        with tempfile.TemporaryDirectory() as parent:
            bare = os.path.join(parent, "bare.git")
            os.makedirs(bare, exist_ok=True)
            subprocess.run(["git", "init", "--bare"], cwd=bare, capture_output=True, check=True, timeout=5)
            target = os.path.join(parent, "clone")
            root = ensure_repo_from_url(Path(bare).as_uri(), target)
            assert root == resolve_repo_root(target)
