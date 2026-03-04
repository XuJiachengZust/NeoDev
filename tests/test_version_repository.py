"""Tests for version_repository (Phase 4: update_last_parsed_commit)."""

import pytest

from service.repositories import version_repository as version_repo


def _make_project(conn):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO projects (name, repo_path) VALUES ('p', '/tmp/p') RETURNING id"
        )
        return cur.fetchone()[0]


def _make_version(conn, project_id: int, branch: str = "main"):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO versions (project_id, branch) VALUES (%s, %s) RETURNING id",
            (project_id, branch),
        )
        return cur.fetchone()[0]


class TestUpdateLastParsedCommit:
    def test_updates_and_returns_row(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        vid = _make_version(pg_conn, pid, "main")
        pg_conn.commit()

        result = version_repo.update_last_parsed_commit(
            pg_conn, vid, "abc123def456789012345678901234567890abcd"
        )
        pg_conn.commit()

        assert result is not None
        assert result["id"] == vid
        assert result["last_parsed_commit"] == "abc123def456789012345678901234567890abcd"

        row = version_repo.find_by_id(pg_conn, vid)
        assert row["last_parsed_commit"] == "abc123def456789012345678901234567890abcd"

    def test_truncates_to_40_chars(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn)
        vid = _make_version(pg_conn, pid)
        pg_conn.commit()

        version_repo.update_last_parsed_commit(
            pg_conn, vid, "a" * 50
        )
        pg_conn.commit()

        row = version_repo.find_by_id(pg_conn, vid)
        assert len(row["last_parsed_commit"]) == 40

    def test_returns_none_for_nonexistent_version(self, pg_conn):
        result = version_repo.update_last_parsed_commit(pg_conn, 999999, "abc123")
        assert result is None
