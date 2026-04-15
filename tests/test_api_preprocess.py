"""TDD tests for preprocess API: POST preprocess (AI 分析), GET preprocess/status (单分支与状态方案)."""

import pytest

from service.repositories import ai_preprocess_status_repository as status_repo


class TestPostPreprocess:
    def test_post_preprocess_project_not_found_returns_404(self, client_with_db):
        r = client_with_db.post("/api/projects/999999/preprocess")
        assert r.status_code == 404

    def test_post_preprocess_success_returns_200_and_body(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p-pre", "repo_path": "/tmp/pre"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        r = client_with_db.post(f"/api/projects/{pid}/preprocess")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["project_id"] == pid
        assert data.get("branch") == "main"
        assert "message" in data

    def test_post_preprocess_when_running_returns_409(self, client_with_db, pg_conn):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p-busy", "repo_path": "/tmp/busy"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        pg_conn.commit()
        status_repo.set_running(pg_conn, pid, "main")
        pg_conn.commit()
        r = client_with_db.post(f"/api/projects/{pid}/preprocess")
        assert r.status_code == 409
        data = r.json()
        assert "detail" in data or "message" in data
        assert data.get("code") == "PROJECT_BUSY" or "处理中" in str(data.get("detail", data.get("message", "")))

    def test_post_preprocess_with_branch_and_force(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p-branch", "repo_path": "/tmp/br"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        r = client_with_db.post(
            f"/api/projects/{pid}/preprocess?branch=develop&force=true",
        )
        assert r.status_code == 200
        assert r.json().get("branch") == "develop"


class TestGetPreprocessStatus:
    def test_get_status_project_not_found_returns_404(self, client_with_db):
        r = client_with_db.get("/api/projects/999999/preprocess/status")
        assert r.status_code == 404

    def test_get_status_no_record_returns_200_with_items(self, client_with_db):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p-nostatus", "repo_path": "/tmp/ns"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        r = client_with_db.get(f"/api/projects/{pid}/preprocess/status")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert data["items"] == []

    def test_get_status_with_branch_returns_single_record(self, client_with_db, pg_conn):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p-one", "repo_path": "/tmp/one"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        pg_conn.commit()
        status_repo.set_running(pg_conn, pid, "main")
        pg_conn.commit()
        status_repo.set_completed(pg_conn, pid, "main", {"saved": 5})
        pg_conn.commit()
        r = client_with_db.get(f"/api/projects/{pid}/preprocess/status?branch=main")
        assert r.status_code == 200
        data = r.json()
        assert data["project_id"] == pid
        assert data["branch"] == "main"
        assert data["status"] == "completed"
        assert "started_at" in data
        assert "finished_at" in data
        assert data.get("extra", {}).get("saved") == 5

    def test_get_status_without_branch_returns_items_list(self, client_with_db, pg_conn):
        create = client_with_db.post(
            "/api/projects",
            json={"name": "p-multi", "repo_path": "/tmp/multi"},
        )
        assert create.status_code == 201
        pid = create.json()["id"]
        pg_conn.commit()
        status_repo.set_running(pg_conn, pid, "main")
        pg_conn.commit()
        status_repo.set_completed(pg_conn, pid, "main", None)
        status_repo.set_running(pg_conn, pid, "develop")
        pg_conn.commit()
        status_repo.set_completed(pg_conn, pid, "develop", None)
        pg_conn.commit()
        r = client_with_db.get(f"/api/projects/{pid}/preprocess/status")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert len(data["items"]) == 2
        branches = {x["branch"] for x in data["items"]}
        assert "main" in branches
        assert "develop" in branches
