from service.services import watch_service


def test_watch_copy_data_clones_snapshot_without_neo4j_copy(monkeypatch):
    commits = {"main": "a" * 40, "feature/a": "a" * 40}
    versions = [
        {"id": 1, "branch": "main", "last_parsed_commit": "a" * 40},
        {"id": 2, "branch": "feature/a", "last_parsed_commit": None},
    ]
    clone_calls = []

    monkeypatch.setattr(
        watch_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {
            "id": project_id,
            "repo_path": "D:/repo",
            "watch_enabled": True,
        },
    )
    monkeypatch.setattr(watch_service.version_repo, "list_by_project_id", lambda conn, project_id: versions)
    monkeypatch.setattr(watch_service.git_ops, "get_head_commit", lambda repo_path, branch: commits[branch])
    monkeypatch.setattr(watch_service.version_repo, "update_last_parsed_commit", lambda conn, version_id, head: None)
    monkeypatch.setattr(
        watch_service,
        "branch_snapshot_service",
        type(
            "SnapshotService",
            (),
            {
                "get_current_snapshot": staticmethod(
                    lambda conn, project_id, branch: {"id": 101} if branch == "main" else None
                ),
                "clone_snapshot": staticmethod(
                    lambda conn, **kwargs: clone_calls.append(kwargs) or {"id": 102, "entry_count": 3}
                ),
            },
        ),
        raising=False,
    )

    class Conn:
        def commit(self):
            pass

    result = watch_service.run_once(Conn(), 7, {}, neo4j_driver=object())

    assert result["actions"] == [{"version_id": 2, "branch": "feature/a", "action": "copy_data"}]
    assert clone_calls == [
        {
            "source_snapshot_id": 101,
            "project_id": 7,
            "branch": "feature/a",
            "head_commit": "a" * 40,
            "last_parsed_commit": "a" * 40,
        }
    ]


def test_watch_full_creates_snapshot_and_passes_project_id(monkeypatch):
    versions = [{"id": 1, "branch": "main", "last_parsed_commit": None}]
    pipeline_calls = []
    snapshot_calls = []

    monkeypatch.setattr(
        watch_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {
            "id": project_id,
            "repo_path": "D:/repo",
            "watch_enabled": True,
        },
    )
    monkeypatch.setattr(watch_service.version_repo, "list_by_project_id", lambda conn, project_id: versions)
    monkeypatch.setattr(watch_service.git_ops, "get_head_commit", lambda repo_path, branch: "b" * 40)
    monkeypatch.setattr(watch_service.version_repo, "update_last_parsed_commit", lambda conn, version_id, head: None)
    monkeypatch.setattr(
        watch_service,
        "branch_snapshot_service",
        type(
            "SnapshotService",
            (),
            {
                "get_current_snapshot": staticmethod(lambda conn, project_id, branch: None),
                "create_snapshot_from_repo": staticmethod(
                    lambda conn, **kwargs: snapshot_calls.append(kwargs) or {"id": 201, "entry_count": 2}
                ),
            },
        ),
        raising=False,
    )

    def pipeline_runner(repo_path, config, branch, incremental, since_commit, project_id=None):
        pipeline_calls.append(
            {
                "repo_path": repo_path,
                "branch": branch,
                "incremental": incremental,
                "since_commit": since_commit,
                "project_id": project_id,
            }
        )

    class Conn:
        def commit(self):
            pass

    result = watch_service.run_once(Conn(), 7, {}, pipeline_runner=pipeline_runner)

    assert result["actions"] == [{"version_id": 1, "branch": "main", "action": "full"}]
    assert pipeline_calls == [
        {
            "repo_path": "D:/repo",
            "branch": "main",
            "incremental": False,
            "since_commit": None,
            "project_id": 7,
        }
    ]
    assert snapshot_calls == [
        {
            "repo_path": "D:/repo",
            "project_id": 7,
            "branch": "main",
            "head_commit": "b" * 40,
            "last_parsed_commit": "b" * 40,
            "created_from_action": "full",
        }
    ]


def test_watch_incremental_creates_snapshot(monkeypatch):
    versions = [{"id": 1, "branch": "main", "last_parsed_commit": "a" * 40}]
    snapshot_calls = []

    monkeypatch.setattr(
        watch_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {
            "id": project_id,
            "repo_path": "D:/repo",
            "watch_enabled": True,
        },
    )
    monkeypatch.setattr(watch_service.version_repo, "list_by_project_id", lambda conn, project_id: versions)
    monkeypatch.setattr(watch_service.git_ops, "get_head_commit", lambda repo_path, branch: "b" * 40)
    monkeypatch.setattr(watch_service.version_repo, "update_last_parsed_commit", lambda conn, version_id, head: None)
    monkeypatch.setattr(
        watch_service,
        "branch_snapshot_service",
        type(
            "SnapshotService",
            (),
            {
                "create_snapshot_from_repo": staticmethod(
                    lambda conn, **kwargs: snapshot_calls.append(kwargs) or {"id": 202, "entry_count": 2}
                ),
            },
        ),
        raising=False,
    )

    class Conn:
        def commit(self):
            pass

    result = watch_service.run_once(
        Conn(),
        7,
        {},
        pipeline_runner=lambda repo_path, config, branch, incremental, since_commit, project_id=None: None,
    )

    assert result["actions"] == [{"version_id": 1, "branch": "main", "action": "incremental"}]
    assert snapshot_calls == [
        {
            "repo_path": "D:/repo",
            "project_id": 7,
            "branch": "main",
            "head_commit": "b" * 40,
            "last_parsed_commit": "b" * 40,
            "created_from_action": "incremental",
        }
    ]
