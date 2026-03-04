"""TDD tests for Phase 3: /api/projects/{project_id}/requirements and requirement-commits (plan 4.3)."""

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


def _make_commit(client, project_id, version_id, sha="a" * 40):
    """Insert commit via raw DB is not exposed; use sync or fixture. For test we need commits in PG."""
    pass


class TestRequirementsApi:
    def test_list_empty_returns_200_and_empty_list(self, client_with_db):
        pid = _make_project(client_with_db)
        r = client_with_db.get(f"/api/projects/{pid}/requirements")
        assert r.status_code == 200
        assert r.json() == []

    def test_create_returns_201(self, client_with_db):
        pid = _make_project(client_with_db)
        r = client_with_db.post(
            f"/api/projects/{pid}/requirements",
            json={"title": "R1", "description": "d1"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "R1"
        assert data["description"] == "d1"
        assert data["project_id"] == pid
        assert "id" in data

    def test_get_detail_returns_200(self, client_with_db):
        pid = _make_project(client_with_db)
        create = client_with_db.post(
            f"/api/projects/{pid}/requirements",
            json={"title": "R1"},
        )
        rid = create.json()["id"]
        r = client_with_db.get(f"/api/projects/{pid}/requirements/{rid}")
        assert r.status_code == 200
        assert r.json()["id"] == rid

    def test_get_detail_not_found_returns_404(self, client_with_db):
        pid = _make_project(client_with_db)
        r = client_with_db.get(f"/api/projects/{pid}/requirements/999999")
        assert r.status_code == 404

    def test_patch_updates_title(self, client_with_db):
        pid = _make_project(client_with_db)
        create = client_with_db.post(
            f"/api/projects/{pid}/requirements",
            json={"title": "Old"},
        )
        rid = create.json()["id"]
        client_with_db.patch(
            f"/api/projects/{pid}/requirements/{rid}",
            json={"title": "New"},
        )
        r = client_with_db.get(f"/api/projects/{pid}/requirements/{rid}")
        assert r.json()["title"] == "New"

    def test_delete_returns_204(self, client_with_db):
        pid = _make_project(client_with_db)
        create = client_with_db.post(
            f"/api/projects/{pid}/requirements",
            json={"title": "R1"},
        )
        rid = create.json()["id"]
        r = client_with_db.delete(f"/api/projects/{pid}/requirements/{rid}")
        assert r.status_code == 204
        r2 = client_with_db.get(f"/api/projects/{pid}/requirements/{rid}")
        assert r2.status_code == 404

    def test_bind_commits_then_detail_shows_commit_ids(self, client_with_db, pg_conn):
        pid = _make_project(client_with_db)
        vid = _make_version(client_with_db, pid)
        # Insert a commit directly (no sync API yet)
        with pg_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO commits (project_id, version_id, commit_sha, message, author) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (pid, vid, "a" * 40, "msg", "author"),
            )
            commit_id = cur.fetchone()[0]
        pg_conn.commit()
        create = client_with_db.post(
            f"/api/projects/{pid}/requirements",
            json={"title": "R1"},
        )
        rid = create.json()["id"]
        bind = client_with_db.post(
            f"/api/projects/{pid}/requirements/{rid}/commits",
            json={"commit_ids": [commit_id]},
        )
        assert bind.status_code in (200, 201, 204)
        r = client_with_db.get(f"/api/projects/{pid}/requirements/{rid}")
        assert r.status_code == 200
        # Detail may include commit_ids or commits list
        data = r.json()
        assert "commit_ids" in data or "commits" in data
        if "commit_ids" in data:
            assert commit_id in data["commit_ids"]
        else:
            assert any(c.get("id") == commit_id for c in data["commits"])

    def test_unbind_commits_removes_association(self, client_with_db, pg_conn):
        pid = _make_project(client_with_db)
        vid = _make_version(client_with_db, pid)
        with pg_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO commits (project_id, version_id, commit_sha, message, author) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (pid, vid, "b" * 40, "msg", "author"),
            )
            commit_id = cur.fetchone()[0]
        pg_conn.commit()
        create = client_with_db.post(
            f"/api/projects/{pid}/requirements",
            json={"title": "R1"},
        )
        rid = create.json()["id"]
        client_with_db.post(
            f"/api/projects/{pid}/requirements/{rid}/commits",
            json={"commit_ids": [commit_id]},
        )
        r = client_with_db.delete(
            f"/api/projects/{pid}/requirements/{rid}/commits",
            params=[("commit_ids", commit_id)],
        )
        assert r.status_code in (200, 204)
        get_r = client_with_db.get(f"/api/projects/{pid}/requirements/{rid}")
        data = get_r.json()
        if "commit_ids" in data:
            assert commit_id not in data["commit_ids"]
        else:
            assert not any(c.get("id") == commit_id for c in data.get("commits", []))
