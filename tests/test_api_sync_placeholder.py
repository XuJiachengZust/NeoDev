"""API tests for sync-commits and watch-status (Phase 4)."""

import pytest


def _make_project(client, repo_path: str = "/tmp/p"):
    r = client.post("/api/projects", json={"name": "p", "repo_path": repo_path})
    assert r.status_code == 201
    return r.json()["id"]


class TestSyncApi:
    def test_sync_commits_returns_200_with_summary(self, client_with_db):
        pid = _make_project(client_with_db)
        client_with_db.post(f"/api/projects/{pid}/versions", json={"branch": "main"})
        r = client_with_db.post(f"/api/projects/{pid}/sync-commits")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == pid
        assert "versions_synced" in data
        assert "commits_synced" in data

    def test_sync_commits_project_not_found_returns_404(self, client_with_db):
        r = client_with_db.post("/api/projects/999999/sync-commits")
        assert r.status_code == 404
        assert r.json()["detail"] == "Project not found"

    def test_watch_status_returns_versions_with_last_parsed(self, client_with_db):
        pid = _make_project(client_with_db)
        client_with_db.post(
            f"/api/projects/{pid}/versions",
            json={"branch": "main"},
        )
        r = client_with_db.get(f"/api/projects/{pid}/watch-status")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == pid
        assert "watch_enabled" in data
        assert "versions" in data
        assert len(data["versions"]) == 1
        assert data["versions"][0]["branch"] == "main"
        assert "last_parsed_commit" in data["versions"][0]
