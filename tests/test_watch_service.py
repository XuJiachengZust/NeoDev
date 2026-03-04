"""Unit tests for watch_service three-step strategy (Phase 4); mocks for PG, git_ops, pipeline."""

from unittest.mock import patch, MagicMock

import pytest

from service.repositories import project_repository as project_repo
from service.repositories import version_repository as version_repo
from service.services import watch_service


def _make_project(conn, watch_enabled: bool = True, repo_path: str = "/tmp/repo"):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO projects (name, repo_path, watch_enabled) VALUES ('p', %s, %s) RETURNING id",
            (repo_path, watch_enabled),
        )
        return cur.fetchone()[0]


def _make_version(conn, project_id: int, branch: str = "main", last_parsed_commit: str | None = None):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO versions (project_id, branch, last_parsed_commit) VALUES (%s, %s, %s) RETURNING id""",
            (project_id, branch, last_parsed_commit),
        )
        return cur.fetchone()[0]


class TestRunOnce:
    def test_returns_none_when_project_not_found(self, pg_conn):
        result = watch_service.run_once(pg_conn, 999999)
        assert result is None

    def test_skipped_when_watch_disabled(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn, watch_enabled=False)
        pg_conn.commit()
        result = watch_service.run_once(pg_conn, pid)
        assert result is not None
        assert result.get("skipped") is True
        assert result.get("reason") == "watch_disabled"

    def test_skipped_when_no_repo_path(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn, repo_path="")
        pg_conn.commit()
        result = watch_service.run_once(pg_conn, pid)
        assert result is not None
        assert result.get("skipped") is True
        assert result.get("reason") == "no_repo_path"

    def test_full_run_when_no_last_parsed_commit(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn, repo_path="/tmp/repo")
        vid = _make_version(pg_conn, pid, "main", last_parsed_commit=None)
        pg_conn.commit()

        pipeline_calls = []
        def capture_pipeline(repo_path, cfg, branch, incremental, since_commit):
            pipeline_calls.append((repo_path, branch, incremental, since_commit))
            return MagicMock()

        with patch("service.services.watch_service.git_ops.get_head_commit", return_value="abc123"):
            result = watch_service.run_once(
                pg_conn, pid, pipeline_runner=capture_pipeline
            )

        assert result is not None
        assert result.get("actions") == [{"version_id": vid, "branch": "main", "action": "full"}]
        assert len(pipeline_calls) == 1
        assert pipeline_calls[0] == ("/tmp/repo", "main", False, None)
        row = version_repo.find_by_id(pg_conn, vid)
        assert row["last_parsed_commit"] == "abc123"

    def test_incremental_run_when_head_differs_from_last(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn, repo_path="/tmp/repo")
        vid = _make_version(pg_conn, pid, "main", last_parsed_commit="oldsha")
        pg_conn.commit()

        pipeline_calls = []
        def capture_pipeline(repo_path, cfg, branch, incremental, since_commit):
            pipeline_calls.append((incremental, since_commit))
            return MagicMock()

        with patch("service.services.watch_service.git_ops.get_head_commit", return_value="newsha"):
            result = watch_service.run_once(
                pg_conn, pid, pipeline_runner=capture_pipeline
            )

        assert result is not None
        assert result["actions"] == [{"version_id": vid, "branch": "main", "action": "incremental"}]
        assert pipeline_calls == [(True, "oldsha")]
        row = version_repo.find_by_id(pg_conn, vid)
        assert row["last_parsed_commit"] == "newsha"

    def test_copy_data_when_new_branch_same_head_as_another_version(self, pg_conn):
        pg_conn.rollback()
        pid = _make_project(pg_conn, repo_path="/tmp/repo")
        vid_main = _make_version(pg_conn, pid, "main", last_parsed_commit="samehead")
        vid_feat = _make_version(pg_conn, pid, "feat/x", last_parsed_commit=None)
        pg_conn.commit()

        add_branch_calls = []
        mock_driver = MagicMock()
        with patch("service.services.watch_service._add_branch_to_nodes_if_available") as mock_add:
            mock_add.return_value = True
            with patch("service.services.watch_service.git_ops.get_head_commit") as mock_head:
                def head_side_effect(repo_path, branch):
                    return "samehead" if branch in ("main", "feat/x") else None
                mock_head.side_effect = head_side_effect
                result = watch_service.run_once(pg_conn, pid, neo4j_driver=mock_driver)

        assert result is not None
        assert result["actions"] == [{"version_id": vid_feat, "branch": "feat/x", "action": "copy_data"}]
        mock_add.assert_called_once_with(mock_driver, "main", "feat/x", None)
        row = version_repo.find_by_id(pg_conn, vid_feat)
        assert row["last_parsed_commit"] == "samehead"
