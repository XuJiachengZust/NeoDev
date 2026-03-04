"""TDD tests for service HTTP API: /api/repos/resolve, /api/repos/ensure, /api/parse, path allowlist."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from service.main import app

client = TestClient(app)


# --- Step 1.1: pytest + TestClient 就绪 ---
def test_client_import():
    """Placeholder: TestClient can be created and used."""
    c = TestClient(app)
    assert c is not None


# --- Step 1.2: POST /api/repos/resolve ---
class TestResolveApi:
    @staticmethod
    def _git_init(path: str) -> None:
        subprocess.run(
            ["git", "init"],
            cwd=path,
            capture_output=True,
            check=True,
            timeout=5,
        )

    def test_resolve_valid_repo_root_returns_200_and_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._git_init(tmp)
            r = client.post("/api/repos/resolve", json={"path": tmp})
            assert r.status_code == 200
            data = r.json()
            assert "repo_root" in data
            assert os.path.isabs(data["repo_root"])
            assert os.path.normpath(data["repo_root"]) == os.path.normpath(Path(tmp).resolve())

    def test_resolve_repo_subdirectory_returns_200_and_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._git_init(tmp)
            subdir = os.path.join(tmp, "a", "b")
            os.makedirs(subdir, exist_ok=True)
            r = client.post("/api/repos/resolve", json={"path": subdir})
            assert r.status_code == 200
            data = r.json()
            assert os.path.normpath(data["repo_root"]) == os.path.normpath(Path(tmp).resolve())

    def test_resolve_non_git_directory_returns_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = client.post("/api/repos/resolve", json={"path": tmp})
            assert r.status_code == 404
            assert "detail" in r.json()
            detail = r.json()["detail"].lower()
            assert "not a git repository" in detail or "path invalid" in detail

    def test_resolve_nonexistent_path_returns_404_or_500(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "does_not_exist")
            r = client.post("/api/repos/resolve", json={"path": bad})
            assert r.status_code in (404, 500)
            assert "detail" in r.json()

    def test_resolve_missing_path_returns_422(self):
        r = client.post("/api/repos/resolve", json={})
        assert r.status_code == 422
        r2 = client.post("/api/repos/resolve", data="not json", headers={"Content-Type": "text/plain"})
        assert r2.status_code == 422


# --- Step 1.3: POST /api/repos/ensure ---
class TestEnsureApi:
    @staticmethod
    def _make_bare_repo(parent: str) -> str:
        bare = os.path.join(parent, "bare.git")
        os.makedirs(bare, exist_ok=True)
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=bare,
            capture_output=True,
            check=True,
            timeout=5,
        )
        return bare

    def test_ensure_clone_into_empty_dir_returns_200_and_repo_root(self):
        with tempfile.TemporaryDirectory() as parent:
            bare = self._make_bare_repo(parent)
            repo_url = Path(bare).as_uri()
            target = os.path.join(parent, "clone")
            r = client.post(
                "/api/repos/ensure",
                json={"repo_url": repo_url, "target_path": target},
            )
            assert r.status_code == 200
            data = r.json()
            assert "repo_root" in data
            assert os.path.normpath(data["repo_root"]) == os.path.normpath(Path(target).resolve())

    def test_ensure_existing_clone_returns_200_same_repo_root(self):
        with tempfile.TemporaryDirectory() as parent:
            bare = self._make_bare_repo(parent)
            repo_url = Path(bare).as_uri()
            target = os.path.join(parent, "clone")
            r1 = client.post(
                "/api/repos/ensure",
                json={"repo_url": repo_url, "target_path": target},
            )
            assert r1.status_code == 200
            r2 = client.post(
                "/api/repos/ensure",
                json={"repo_url": repo_url, "target_path": target},
            )
            assert r2.status_code == 200
            assert r1.json()["repo_root"] == r2.json()["repo_root"]

    def test_ensure_target_exists_not_git_returns_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = client.post(
                "/api/repos/ensure",
                json={
                    "repo_url": "https://github.com/some/repo.git",
                    "target_path": tmp,
                },
            )
            assert r.status_code == 400
            detail = r.json().get("detail", "").lower()
            assert "empty" in detail or "git" in detail or "repo" in detail

    def test_ensure_missing_body_fields_returns_422(self):
        r = client.post("/api/repos/ensure", json={})
        assert r.status_code == 422


# --- Step 1.4: Path allowlist ---
class TestPathAllowlist:
    @staticmethod
    def _git_init(path: str) -> None:
        subprocess.run(
            ["git", "init"],
            cwd=path,
            capture_output=True,
            check=True,
            timeout=5,
        )

    def test_resolve_without_allowlist_succeeds_for_valid_path(self, monkeypatch):
        monkeypatch.delenv("ALLOWED_BASE_PATHS", raising=False)
        with tempfile.TemporaryDirectory() as tmp:
            self._git_init(tmp)
            r = client.post("/api/repos/resolve", json={"path": tmp})
            assert r.status_code == 200

    def test_resolve_with_allowlist_succeeds_when_path_under_base(self, monkeypatch):
        with tempfile.TemporaryDirectory() as base:
            self._git_init(base)
            monkeypatch.setenv("ALLOWED_BASE_PATHS", base)
            r = client.post("/api/repos/resolve", json={"path": base})
            assert r.status_code == 200

    def test_resolve_with_allowlist_returns_400_when_path_outside_base(self, monkeypatch):
        with tempfile.TemporaryDirectory() as base:
            monkeypatch.setenv("ALLOWED_BASE_PATHS", base)
            with tempfile.TemporaryDirectory() as other:
                if os.path.normpath(other).startswith(os.path.normpath(base)):
                    pytest.skip("temp dirs can be under same base on some systems")
                r = client.post("/api/repos/resolve", json={"path": other})
                assert r.status_code == 400
                detail = r.json().get("detail", "").lower()
                assert "not allowed" in detail or "allowed_base" in detail or "allowlist" in detail


# --- Step 1.5: POST /api/parse ---
class TestParseApi:
    @staticmethod
    def _git_init(path: str) -> None:
        subprocess.run(
            ["git", "init"],
            cwd=path,
            capture_output=True,
            check=True,
            timeout=5,
        )

    def test_parse_valid_repo_write_neo4j_false_returns_200_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._git_init(tmp)
            r = client.post(
                "/api/parse",
                json={"repo_path": tmp, "write_neo4j": False},
            )
            assert r.status_code == 200
            data = r.json()
            assert "node_count" in data
            assert "relationship_count" in data
            assert "file_count" in data

    def test_parse_nonexistent_path_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "nonexistent")
            r = client.post(
                "/api/parse",
                json={"repo_path": bad, "write_neo4j": False},
            )
            assert r.status_code in (400, 404, 500)
            assert "detail" in r.json()

    def test_parse_missing_repo_path_returns_422(self):
        r = client.post(
            "/api/parse",
            json={"write_neo4j": False},
        )
        assert r.status_code == 422


# --- Step 1.6: Health (optional) ---
def test_health_returns_200_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
