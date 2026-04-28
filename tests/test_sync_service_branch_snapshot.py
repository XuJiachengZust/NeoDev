import shutil
import uuid
from pathlib import Path


def _local_tmp_dir(name: str) -> Path:
    root = Path(__file__).resolve().parent.parent / ".test-tmp" / name
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True, exist_ok=True)
    return root


class FakeConn:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


def test_sync_commits_for_version_creates_current_branch_snapshot(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import branch_snapshot_service, sync_service

    repo = _local_tmp_dir(f"sync-snapshot-{uuid.uuid4().hex[:8]}")
    try:
        (repo / "app.py").write_text("print('sync')\n", encoding="utf-8")
        head = "c" * 40
        calls = {}

        monkeypatch.setattr(
            sync_service.project_repo,
            "find_by_id",
            lambda conn, project_id: {"id": project_id, "repo_path": str(repo)},
        )
        monkeypatch.setattr(
            sync_service.version_repo,
            "find_by_id",
            lambda conn, version_id: {
                "id": version_id,
                "project_id": 3,
                "branch": "main",
                "last_parsed_commit": None,
            },
        )
        monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: str(repo))
        monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
        monkeypatch.setattr(sync_service.git_ops, "list_commits", lambda local_root, branch: [])
        monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: head)
        monkeypatch.setattr(sync_service.commit_repo, "upsert_commits", lambda conn, project_id, version_id, commits: 0)
        monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: None)

        import gitnexus_parser

        monkeypatch.setattr(
            gitnexus_parser,
            "load_config",
            lambda path=None: {"neo4j_uri": "bolt://neo4j", "neo4j_database": "neo4j"},
        )

        def fake_run_pipeline(local_root, *, config, branch, project_id, write_neo4j, incremental, since_commit):
            calls["pipeline"] = {
                "local_root": local_root,
                "branch": branch,
                "project_id": project_id,
                "write_neo4j": write_neo4j,
                "incremental": incremental,
                "since_commit": since_commit,
            }

        monkeypatch.setattr(pipeline, "run_pipeline", fake_run_pipeline)

        def fake_update_last_parsed_commit(conn, version_id, commit):
            calls["last_parsed_commit"] = {"version_id": version_id, "commit": commit}

        monkeypatch.setattr(
            sync_service.version_repo,
            "update_last_parsed_commit",
            fake_update_last_parsed_commit,
        )

        def fake_create_snapshot_from_repo(conn, **kwargs):
            calls["snapshot"] = kwargs
            return {"id": 99, "entry_count": 1, **kwargs}

        monkeypatch.setattr(
            branch_snapshot_service,
            "create_snapshot_from_repo",
            fake_create_snapshot_from_repo,
        )

        result = sync_service.sync_commits_for_version(FakeConn(), project_id=3, version_id=5)

        assert result["graph_action"] == "full"
        assert result["head_commit"] == head
        assert result["current_snapshot_id"] == 99
        assert result["snapshot_entry_count"] == 1
        assert calls["last_parsed_commit"] == {"version_id": 5, "commit": head}
        assert calls["snapshot"]["repo_path"] == str(repo)
        assert calls["snapshot"]["project_id"] == 3
        assert calls["snapshot"]["branch"] == "main"
        assert calls["snapshot"]["head_commit"] == head
        assert calls["snapshot"]["last_parsed_commit"] == head
        assert calls["snapshot"]["created_from_action"] == "full"
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_sync_commit_graph_for_version_uses_commit_incremental_for_small_commit(monkeypatch):
    from gitnexus_parser.ingestion import pipeline
    from service.services import branch_snapshot_service, sync_service

    repo = _local_tmp_dir(f"sync-commit-incremental-{uuid.uuid4().hex[:8]}")
    try:
        (repo / "app.py").write_text("print('sync')\n", encoding="utf-8")
        parent = "a" * 40
        commit = "b" * 40
        calls = {}

        monkeypatch.setattr(
            sync_service.project_repo,
            "find_by_id",
            lambda conn, project_id: {"id": project_id, "repo_path": str(repo)},
        )
        monkeypatch.setattr(
            sync_service.version_repo,
            "find_by_id",
            lambda conn, version_id: {
                "id": version_id,
                "project_id": 3,
                "branch": "main",
                "last_parsed_commit": parent,
            },
        )
        monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: str(repo))
        monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
        monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: commit)
        monkeypatch.setattr(sync_service.git_ops, "list_commits", lambda local_root, branch, max_count=5000: [])
        monkeypatch.setattr(sync_service.commit_repo, "upsert_commits", lambda conn, project_id, version_id, commits: 1)
        monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: None)
        monkeypatch.setattr(sync_service, "_get_commit_parent", lambda local_root, commit_sha: parent)
        monkeypatch.setattr(sync_service, "get_changed_paths", lambda local_root, base, head: ["app.py"])

        import gitnexus_parser

        monkeypatch.setattr(
            gitnexus_parser,
            "load_config",
            lambda path=None: {"neo4j_uri": "bolt://neo4j", "neo4j_database": "neo4j"},
        )

        def fake_run_pipeline(
            local_root,
            *,
            config,
            branch,
            project_id,
            write_neo4j,
            incremental,
            since_commit,
            target_commit,
        ):
            calls["pipeline"] = {
                "branch": branch,
                "project_id": project_id,
                "write_neo4j": write_neo4j,
                "incremental": incremental,
                "since_commit": since_commit,
                "target_commit": target_commit,
            }

        monkeypatch.setattr(pipeline, "run_pipeline", fake_run_pipeline)
        monkeypatch.setattr(
            sync_service.version_repo,
            "update_last_parsed_commit",
            lambda conn, version_id, commit: calls.setdefault(
                "last_parsed_commit",
                {"version_id": version_id, "commit": commit},
            ),
        )
        monkeypatch.setattr(
            branch_snapshot_service,
            "create_snapshot_from_repo",
            lambda conn, **kwargs: calls.setdefault("snapshot", kwargs) or {"id": 7, "entry_count": 1},
        )

        result = sync_service.sync_commit_graph_for_version(
            FakeConn(),
            project_id=3,
            version_id=5,
            commit_sha=commit,
            max_changed_files=10,
        )

        assert result["graph_action"] == "commit_incremental"
        assert result["fallback"] is False
        assert result["changed_paths"] == ["app.py"]
        assert calls["pipeline"] == {
            "branch": "main",
            "project_id": 3,
            "write_neo4j": True,
            "incremental": True,
            "since_commit": parent,
            "target_commit": commit,
        }
        assert calls["last_parsed_commit"] == {"version_id": 5, "commit": commit}
        assert calls["snapshot"]["created_from_action"] == "commit_incremental"
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_sync_commit_graph_for_version_falls_back_when_commit_is_large(monkeypatch):
    from service.services import sync_service

    repo = _local_tmp_dir(f"sync-commit-large-{uuid.uuid4().hex[:8]}")
    try:
        commit = "b" * 40
        monkeypatch.setattr(
            sync_service.project_repo,
            "find_by_id",
            lambda conn, project_id: {"id": project_id, "repo_path": str(repo)},
        )
        monkeypatch.setattr(
            sync_service.version_repo,
            "find_by_id",
            lambda conn, version_id: {
                "id": version_id,
                "project_id": 3,
                "branch": "main",
                "last_parsed_commit": None,
            },
        )
        monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: str(repo))
        monkeypatch.setattr(sync_service.git_ops, "fetch_repo", lambda local_root: None)
        monkeypatch.setattr(sync_service.git_ops, "get_head_commit", lambda local_root, branch: commit)
        monkeypatch.setattr(sync_service, "_git_checkout", lambda local_root, branch: None)
        monkeypatch.setattr(sync_service, "_get_commit_parent", lambda local_root, commit_sha: "a" * 40)
        monkeypatch.setattr(sync_service, "get_changed_paths", lambda local_root, base, head: ["a.py", "b.py", "c.py"])

        captured = {}

        def fake_sync_commits_for_version(conn, project_id, version_id):
            captured["fallback"] = {"project_id": project_id, "version_id": version_id}
            return {"project_id": project_id, "version_id": version_id, "graph_action": "full"}

        monkeypatch.setattr(sync_service, "sync_commits_for_version", fake_sync_commits_for_version)

        result = sync_service.sync_commit_graph_for_version(
            FakeConn(),
            project_id=3,
            version_id=5,
            commit_sha=commit,
            max_changed_files=2,
        )

        assert result["graph_action"] == "full"
        assert result["fallback"] is True
        assert result["fallback_reason"] == "changed_files_exceeded_threshold"
        assert result["changed_file_count"] == 3
        assert captured["fallback"] == {"project_id": 3, "version_id": 5}
    finally:
        shutil.rmtree(repo, ignore_errors=True)
