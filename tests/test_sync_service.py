"""Tests for sync_service (Phase 4)."""

import pytest
from unittest.mock import patch

from service.repositories import commit_repository as commit_repo
from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo
from service.services import sync_service


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


class TestSyncCommitsForProject:
    def test_returns_none_when_project_not_found(self, pg_conn):
        result = sync_service.sync_commits_for_project(pg_conn, 999999)
        assert result is None

    def test_syncs_commits_to_pg_when_git_returns_commits(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn, repo_path="/tmp/repo")
        vid = _make_version(pg_conn, pid, "main")
        pg_conn.commit()

        mock_commits = [
            {"commit_sha": "a" * 40, "message": "m1", "author": "a1", "committed_at": None},
            {"commit_sha": "b" * 40, "message": "m2", "author": "a2", "committed_at": None},
        ]
        with (
            patch("service.services.sync_service._resolve_local_repo", return_value="/tmp/repo"),
            patch("service.services.sync_service.git_ops.fetch_repo"),
            patch("service.services.sync_service.git_ops.list_commits", return_value=mock_commits),
        ):
            result = sync_service.sync_commits_for_project(pg_conn, pid)

        assert result is not None
        assert result["project_id"] == pid
        assert result["versions_synced"] == 1
        assert result["commits_synced"] == 2

        listed = commit_repo.list_by_version_id(pg_conn, pid, vid)
        assert len(listed) == 2
