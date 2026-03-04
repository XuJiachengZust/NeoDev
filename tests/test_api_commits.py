"""TDD tests for Phase 3: /api/projects/{project_id}/commits and .../versions/{version_id}/commits (plan 4.4)."""

import pytest


def _make_project(client):
    r = client.post("/api/projects", json={"name": "p", "repo_path": "/tmp/p"})
    assert r.status_code == 201
    return r.json()["id"]


def _make_version(client, project_id, branch="main"):
    r = client.post(
        f"/api/projects/{project_id}/versions",
        json={"branch": branch},
    )
    assert r.status_code == 201
    return r.json()["id"]


class TestCommitsApi:
    def test_list_empty_returns_200_and_empty_list(self, client_with_db):
        pid = _make_project(client_with_db)
        r = client_with_db.get(f"/api/projects/{pid}/commits")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_returns_commits_with_expected_fields(self, client_with_db, pg_conn):
        pid = _make_project(client_with_db)
        vid = _make_version(client_with_db, pid)
        with pg_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO commits (project_id, version_id, commit_sha, message, author) VALUES (%s, %s, %s, %s, %s)",
                (pid, vid, "a" * 40, "msg", "author"),
            )
        pg_conn.commit()
        r = client_with_db.get(f"/api/projects/{pid}/commits")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["project_id"] == pid
        assert data[0]["version_id"] == vid
        assert data[0]["commit_sha"] == "a" * 40
        assert "id" in data[0]
        assert "message" in data[0]
        assert "author" in data[0]
        assert "committed_at" in data[0]

    def test_list_by_version_id_filters(self, client_with_db, pg_conn):
        pid = _make_project(client_with_db)
        v1 = _make_version(client_with_db, pid, "main")
        v2 = _make_version(client_with_db, pid, "dev")
        with pg_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO commits (project_id, version_id, commit_sha, message, author) VALUES (%s, %s, %s, %s, %s), (%s, %s, %s, %s, %s)",
                (pid, v1, "a" * 40, "m1", "a1", pid, v2, "b" * 40, "m2", "a2"),
            )
        pg_conn.commit()
        r = client_with_db.get(f"/api/projects/{pid}/versions/{v1}/commits")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["commit_sha"] == "a" * 40

    def test_list_project_not_found_returns_404(self, client_with_db):
        r = client_with_db.get("/api/projects/999999/commits")
        assert r.status_code == 404
