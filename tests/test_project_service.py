from service.services import project_service


class FakeConn:
    def commit(self):
        pass


def test_project_init_reuses_existing_default_version_when_overwriting(monkeypatch):
    from service import git_ops
    from service.repositories import branch_repository
    from service.repositories import version_repository
    from service.services import sync_service
    from service.services import version_service

    synced = {}

    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "/repo")
    monkeypatch.setattr(git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(git_ops, "get_branches", lambda local_root: ["main"])
    monkeypatch.setattr(git_ops, "get_default_branch", lambda local_root: "main")
    monkeypatch.setattr(branch_repository, "upsert_many", lambda conn, project_id, branches: None)
    monkeypatch.setattr(version_service, "create_version", lambda conn, project_id, branch: (None, "duplicate_branch"))
    monkeypatch.setattr(
        version_repository,
        "find_by_project_and_branch",
        lambda conn, project_id, branch: {
            "id": 123,
            "project_id": project_id,
            "branch": branch,
            "version_name": None,
            "created_at": None,
            "last_parsed_commit": None,
        },
    )

    def fake_sync(conn, project_id, version_id):
        synced["version_id"] = version_id
        return {"versions_synced": 1, "commits_synced": 10}

    monkeypatch.setattr(sync_service, "sync_commits_for_version", fake_sync)
    monkeypatch.setattr(project_service, "_update_init_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(project_service, "_complete_init", lambda conn, project_id, result: result.update(status="completed"))
    monkeypatch.setattr(project_service, "_fail_init", lambda conn, project_id, result, error: result.update(status="failed", error=error))

    result = project_service._init_repo_and_sync(FakeConn(), {"id": 42})

    assert result["status"] == "completed"
    assert result["version_id"] == 123
    assert result["sync"] == {"versions_synced": 1, "commits_synced": 10}
    assert synced["version_id"] == 123
