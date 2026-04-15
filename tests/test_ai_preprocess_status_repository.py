"""TDD tests for ai_preprocess_status_repository (单分支与状态方案)."""

from datetime import datetime, timezone

import pytest

from service.repositories import ai_preprocess_status_repository as status_repo


def _make_project(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO projects (name, repo_path) VALUES ('p', '/tmp/p') RETURNING id"
        )
        return cur.fetchone()[0]


def _insert_status(conn, project_id: int, branch: str, status: str, started_at=None):
    from psycopg2.extras import Json
    if started_at is None:
        started_at = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO ai_preprocess_status (project_id, branch, status, started_at, updated_at)
             VALUES (%s, %s, %s, %s, %s)
             ON CONFLICT (project_id, branch) DO UPDATE SET
               status = EXCLUDED.status, started_at = EXCLUDED.started_at, updated_at = EXCLUDED.updated_at""",
            (project_id, branch, status, started_at, started_at),
        )
    conn.commit()


class TestHasRunning:
    def test_has_running_false_when_no_row(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        pg_conn.commit()
        assert status_repo.has_running(pg_conn, pid) is False

    def test_has_running_true_when_status_running(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        pg_conn.commit()
        _insert_status(pg_conn, pid, "main", "running")
        assert status_repo.has_running(pg_conn, pid) is True

    def test_has_running_false_when_status_completed(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        pg_conn.commit()
        _insert_status(pg_conn, pid, "main", "completed")
        assert status_repo.has_running(pg_conn, pid) is False


class TestSetRunning:
    def test_set_running_creates_row_returns_true(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        pg_conn.commit()
        ok = status_repo.set_running(pg_conn, pid, "main")
        pg_conn.commit()
        assert ok is True
        rows = status_repo.get_status(pg_conn, pid, "main")
        assert len(rows) == 1
        assert rows[0]["status"] == "running"
        assert rows[0]["project_id"] == pid
        assert rows[0]["branch"] == "main"

    def test_set_running_when_already_running_returns_false(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        pg_conn.commit()
        assert status_repo.set_running(pg_conn, pid, "main") is True
        pg_conn.commit()
        # 同一 project 已有 running，再 set_running 任意 branch 应返回 False
        assert status_repo.set_running(pg_conn, pid, "develop") is False
        pg_conn.commit()


class TestSetCompletedAndFailed:
    def test_set_completed_updates_row(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        pg_conn.commit()
        status_repo.set_running(pg_conn, pid, "main")
        pg_conn.commit()
        status_repo.set_completed(pg_conn, pid, "main", {"saved": 10})
        pg_conn.commit()
        rows = status_repo.get_status(pg_conn, pid, "main")
        assert len(rows) == 1
        assert rows[0]["status"] == "completed"
        assert rows[0]["finished_at"] is not None
        assert rows[0].get("extra") and rows[0]["extra"].get("saved") == 10

    def test_set_failed_updates_row(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        pg_conn.commit()
        status_repo.set_running(pg_conn, pid, "main")
        pg_conn.commit()
        status_repo.set_failed(pg_conn, pid, "main", "error msg")
        pg_conn.commit()
        rows = status_repo.get_status(pg_conn, pid, "main")
        assert len(rows) == 1
        assert rows[0]["status"] == "failed"
        assert rows[0]["error_message"] == "error msg"


class TestGetStatus:
    def test_get_status_by_project_and_branch_returns_one(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        pg_conn.commit()
        _insert_status(pg_conn, pid, "main", "completed")
        result = status_repo.get_status(pg_conn, pid, "main")
        assert isinstance(result, list)
        assert len(result) == 1
        row = result[0]
        assert row["project_id"] == pid
        assert row["branch"] == "main"
        assert row["status"] == "completed"
        assert "started_at" in row

    def test_get_status_by_project_only_returns_all_branches(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        pg_conn.commit()
        _insert_status(pg_conn, pid, "main", "completed")
        _insert_status(pg_conn, pid, "develop", "running")
        result = status_repo.get_status(pg_conn, pid, None)
        assert isinstance(result, list)
        assert len(result) == 2
        branches = {r["branch"] for r in result}
        assert "main" in branches
        assert "develop" in branches
