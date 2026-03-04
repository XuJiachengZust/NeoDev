"""TDD tests for Phase 3: /api/projects/{project_id}/impact-analyses (plan 4.5)."""

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


def _make_commit(client_with_db, pg_conn, project_id, version_id, sha="a" * 40):
    with pg_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO commits (project_id, version_id, commit_sha, message, author) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (project_id, version_id, sha, "msg", "author"),
        )
        return cur.fetchone()[0]


class TestImpactAnalysesApi:
    def test_create_returns_201_with_id_status_triggered_at(self, client_with_db, pg_conn):
        pid = _make_project(client_with_db)
        vid = _make_version(client_with_db, pid)
        cid = _make_commit(client_with_db, pg_conn, pid, vid)
        pg_conn.commit()
        r = client_with_db.post(
            f"/api/projects/{pid}/impact-analyses",
            json={"commit_ids": [cid]},
        )
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert "status" in data
        assert "triggered_at" in data

    def test_create_then_list_contains_item(self, client_with_db, pg_conn):
        pid = _make_project(client_with_db)
        vid = _make_version(client_with_db, pid)
        cid = _make_commit(client_with_db, pg_conn, pid, vid)
        pg_conn.commit()
        create = client_with_db.post(
            f"/api/projects/{pid}/impact-analyses",
            json={"commit_ids": [cid]},
        )
        assert create.status_code == 201
        aid = create.json()["id"]
        r = client_with_db.get(f"/api/projects/{pid}/impact-analyses")
        assert r.status_code == 200
        ids = [x["id"] for x in r.json()]
        assert aid in ids

    def test_get_detail_includes_commit_info(self, client_with_db, pg_conn):
        pid = _make_project(client_with_db)
        vid = _make_version(client_with_db, pid)
        cid = _make_commit(client_with_db, pg_conn, pid, vid)
        pg_conn.commit()
        create = client_with_db.post(
            f"/api/projects/{pid}/impact-analyses",
            json={"commit_ids": [cid]},
        )
        aid = create.json()["id"]
        r = client_with_db.get(f"/api/projects/{pid}/impact-analyses/{aid}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == aid
        assert "commit_ids" in data or "commits" in data
        if "commit_ids" in data:
            assert cid in data["commit_ids"]
        else:
            assert any(c.get("id") == cid for c in data["commits"])

    def test_create_empty_commit_ids_returns_400(self, client_with_db):
        pid = _make_project(client_with_db)
        r = client_with_db.post(
            f"/api/projects/{pid}/impact-analyses",
            json={"commit_ids": []},
        )
        assert r.status_code == 400

    def test_create_project_not_found_returns_404(self, client_with_db, pg_conn):
        pid = _make_project(client_with_db)
        vid = _make_version(client_with_db, pid)
        cid = _make_commit(client_with_db, pg_conn, pid, vid)
        pg_conn.commit()
        r = client_with_db.post(
            "/api/projects/999999/impact-analyses",
            json={"commit_ids": [cid]},
        )
        assert r.status_code == 404
