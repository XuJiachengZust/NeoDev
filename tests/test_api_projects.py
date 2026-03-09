"""TDD tests for Phase 3: /api/projects CRUD (plan 4.1)."""

import pytest
from unittest.mock import patch


class TestProjectsApi:
    """GET /api/projects, POST, GET /{id}, PATCH, DELETE."""

    def test_list_returns_200_and_list(self, client_with_db):
        r = client_with_db.get("/api/projects")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_create_returns_201_and_body_has_id_name_repo_path_created_at(self, client_with_db):
        r = client_with_db.post(
            "/api/projects",
            json={"name": "p1", "repo_path": "/tmp/repo1"},
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["name"] == "p1"
        assert data["repo_path"] == "/tmp/repo1"
        assert "created_at" in data

    def test_create_then_list_contains_item(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p2", "repo_path": "/tmp/repo2"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        r = client_with_db.get("/api/projects")
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert pid in ids

    def test_get_by_id_exists_returns_200(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p3", "repo_path": "/tmp/repo3"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        r = client_with_db.get(f"/api/projects/{pid}")
        assert r.status_code == 200
        assert r.json()["id"] == pid
        assert r.json()["name"] == "p3"

    def test_get_by_id_not_exists_returns_404(self, client_with_db):
        r = client_with_db.get("/api/projects/999999")
        assert r.status_code == 404

    def test_patch_updates_name_then_get_sees_it(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "old", "repo_path": "/tmp/r"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        patch = client_with_db.patch(f"/api/projects/{pid}", json={"name": "new"})
        assert patch.status_code == 200
        get_r = client_with_db.get(f"/api/projects/{pid}")
        assert get_r.json()["name"] == "new"

    def test_delete_then_get_returns_404(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "del", "repo_path": "/tmp/del"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        del_r = client_with_db.delete(f"/api/projects/{pid}")
        assert del_r.status_code == 204
        get_r = client_with_db.get(f"/api/projects/{pid}")
        assert get_r.status_code == 404

    def test_project_branches_returns_list_and_includes_version_bound_branch(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p-branches", "repo_path": "/tmp/not-git"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        ver = client_with_db.post(
            f"/api/projects/{pid}/versions",
            json={"branch": "main", "version_name": "v1"},
        )
        assert ver.status_code == 201

        branches_r = client_with_db.get(f"/api/projects/{pid}/branches")
        assert branches_r.status_code == 200
        assert "main" in branches_r.json()

    def test_project_branches_not_found_returns_404(self, client_with_db):
        r = client_with_db.get("/api/projects/999999/branches")
        assert r.status_code == 404

    def test_project_branches_remote_repo_scans_and_persists_local_repo_path(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={
                "name": "p-remote-scan",
                "repo_path": "https://git.example.com/group/repo.git",
                "repo_username": "gituser",
                "repo_password": "token",
            },
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        local_root = f"/tmp/repos/{pid}"

        with (
            patch("service.services.branch_service.ensure_repo_from_url", return_value=local_root),
            patch("service.services.branch_service.git_ops.get_branches", return_value=["main", "dev"]),
        ):
            branches_r = client_with_db.get(f"/api/projects/{pid}/branches")

        assert branches_r.status_code == 200
        assert set(branches_r.json()) >= {"main", "dev"}

        get_r = client_with_db.get(f"/api/projects/{pid}")
        assert get_r.status_code == 200
        assert get_r.json()["repo_path"] == local_root

    def test_create_with_repo_auth_returns_and_persists_credentials(self, client_with_db):
        r = client_with_db.post(
            "/api/projects",
            json={
                "name": "remote-p",
                "repo_path": "https://git.example.com/group/repo.git",
                "repo_username": "gituser",
                "repo_password": "secret",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["repo_username"] == "gituser"
        assert data["repo_password"] == "secret"
        pid = data["id"]
        get_r = client_with_db.get(f"/api/projects/{pid}")
        assert get_r.json()["repo_username"] == "gituser"
        assert get_r.json()["repo_password"] == "secret"

    def test_patch_repo_auth_updates_and_clear(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p", "repo_path": "https://x/y.git", "repo_username": "u", "repo_password": "p"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        patch = client_with_db.patch(
            f"/api/projects/{pid}",
            json={"repo_username": "u2", "repo_password": "p2"},
        )
        assert patch.status_code == 200
        assert patch.json()["repo_username"] == "u2"
        assert patch.json()["repo_password"] == "p2"
        clear = client_with_db.patch(
            f"/api/projects/{pid}",
            json={"repo_username": None, "repo_password": None},
        )
        assert clear.status_code == 200
        assert clear.json().get("repo_username") is None
        assert clear.json().get("repo_password") is None
