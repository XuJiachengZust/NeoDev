"""Tests for commit_repository (Phase 4: upsert_commits)."""

import pytest

from service.repositories import commit_repository as commit_repo
from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo


def _make_project(conn, repo_path: str = "/tmp/p"):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO projects (name, repo_path) VALUES ('p', %s) RETURNING id",
            (repo_path,),
        )
        return cur.fetchone()[0]


def _make_version(conn, project_id: int, branch: str = "main"):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO versions (project_id, branch) VALUES (%s, %s) RETURNING id",
            (project_id, branch),
        )
        return cur.fetchone()[0]


class TestUpsertCommits:
    def test_inserts_new_commits(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        vid = _make_version(pg_conn, pid)
        pg_conn.commit()

        commits = [
            {
                "commit_sha": "a" * 40,
                "message": "first",
                "author": "alice",
                "committed_at": None,
            },
            {
                "commit_sha": "b" * 40,
                "message": "second",
                "author": "bob",
            },
        ]
        n = commit_repo.upsert_commits(pg_conn, pid, vid, commits)
        pg_conn.commit()

        assert n == 2
        listed = commit_repo.list_by_version_id(pg_conn, pid, vid)
        assert len(listed) == 2
        shas = {c["commit_sha"] for c in listed}
        assert "a" * 40 in shas and "b" * 40 in shas

    def test_idempotent_same_sha_keeps_two_records(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        vid = _make_version(pg_conn, pid)
        pg_conn.commit()

        commits1 = [
            {"commit_sha": "x" * 40, "message": "msg1"},
            {"commit_sha": "y" * 40, "message": "msg2"},
        ]
        commit_repo.upsert_commits(pg_conn, pid, vid, commits1)
        pg_conn.commit()

        commits2 = [
            {"commit_sha": "x" * 40, "message": "msg1 updated"},
            {"commit_sha": "y" * 40, "message": "msg2"},
        ]
        commit_repo.upsert_commits(pg_conn, pid, vid, commits2)
        pg_conn.commit()

        listed = commit_repo.list_by_version_id(pg_conn, pid, vid)
        assert len(listed) == 2
        by_sha = {c["commit_sha"]: c for c in listed}
        assert by_sha["x" * 40]["message"] == "msg1 updated"

    def test_empty_list_returns_zero(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        vid = _make_version(pg_conn, pid)
        pg_conn.commit()

        n = commit_repo.upsert_commits(pg_conn, pid, vid, [])
        assert n == 0

    def test_truncates_commit_sha_to_40(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        vid = _make_version(pg_conn, pid)
        pg_conn.commit()

        commit_repo.upsert_commits(
            pg_conn, pid, vid, [{"commit_sha": "z" * 50, "message": "m"}]
        )
        pg_conn.commit()

        listed = commit_repo.list_by_version_id(pg_conn, pid, vid)
        assert len(listed) == 1
        assert len(listed[0]["commit_sha"]) == 40
