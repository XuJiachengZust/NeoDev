"""TDD tests for Phase 3: /api/projects/{project_id}/versions (plan 4.2)."""

import pytest


class TestVersionsApi:
    def test_list_empty_returns_200_and_empty_list(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p", "repo_path": "/tmp/p"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        r = client_with_db.get(f"/api/projects/{pid}/versions")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_returns_versions_with_expected_fields(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p", "repo_path": "/tmp/p"},
        )
        pid = create.json()["id"]
        client_with_db.post(
            f"/api/projects/{pid}/versions",
            json={"branch": "main", "version_name": "v1"},
        )
        r = client_with_db.get(f"/api/projects/{pid}/versions")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert "id" in data[0]
        assert data[0]["project_id"] == pid
        assert data[0]["branch"] == "main"
        assert data[0]["version_name"] == "v1"
        assert "created_at" in data[0]

    def test_create_returns_201(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p", "repo_path": "/tmp/p"},
        )
        pid = create.json()["id"]
        r = client_with_db.post(
            f"/api/projects/{pid}/versions",
            json={"branch": "main"},
        )
        assert r.status_code == 201
        assert r.json()["branch"] == "main"
        assert r.json()["project_id"] == pid

    def test_create_duplicate_branch_same_project_returns_409(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p", "repo_path": "/tmp/p"},
        )
        pid = create.json()["id"]
        client_with_db.post(
            f"/api/projects/{pid}/versions",
            json={"branch": "main"},
        )
        r = client_with_db.post(
            f"/api/projects/{pid}/versions",
            json={"branch": "main"},
        )
        assert r.status_code == 409

    def test_create_project_not_found_returns_404(self, client_with_db):
        r = client_with_db.post(
            "/api/projects/999999/versions",
            json={"branch": "main"},
        )
        assert r.status_code == 404

    def test_delete_exists_returns_204(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p", "repo_path": "/tmp/p"},
        )
        pid = create.json()["id"]
        ver = client_with_db.post(
            f"/api/projects/{pid}/versions",
            json={"branch": "main"},
        )
        vid = ver.json()["id"]
        r = client_with_db.delete(f"/api/projects/{pid}/versions/{vid}")
        assert r.status_code == 204
        list_r = client_with_db.get(f"/api/projects/{pid}/versions")
        assert len(list_r.json()) == 0

    def test_delete_not_exists_returns_404(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p", "repo_path": "/tmp/p"},
        )
        pid = create.json()["id"]
        r = client_with_db.delete(f"/api/projects/{pid}/versions/999999")
        assert r.status_code == 404
