"""TDD tests for Phase 3: /api/projects CRUD (plan 4.1)."""

import pytest


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
