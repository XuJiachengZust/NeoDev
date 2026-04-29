from service.services import project_service


class FakeConn:
    def commit(self):
        pass


def test_project_init_refreshes_default_branch_without_project_version(monkeypatch):
    from service import git_ops
    from service.repositories import branch_repository
    from service.services import sync_service

    refreshed = {}

    monkeypatch.setattr(sync_service, "_resolve_local_repo", lambda project, project_id: "/repo")
    monkeypatch.setattr(git_ops, "fetch_repo", lambda local_root: None)
    monkeypatch.setattr(git_ops, "get_branches", lambda local_root: ["main"])
    monkeypatch.setattr(git_ops, "get_default_branch", lambda local_root: "main")
    monkeypatch.setattr(branch_repository, "upsert_many", lambda conn, project_id, branches: None)

    def fake_refresh(conn, project_id, branch):
        refreshed.update({"project_id": project_id, "branch": branch})
        return {"graph_action": "full_refresh", "current_snapshot_id": 42}

    monkeypatch.setattr(sync_service, "refresh_graph_for_branch", fake_refresh)
    monkeypatch.setattr(project_service, "_update_init_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(project_service, "_complete_init", lambda conn, project_id, result: result.update(status="completed"))
    monkeypatch.setattr(project_service, "_fail_init", lambda conn, project_id, result, error: result.update(status="failed", error=error))

    result = project_service._init_repo_and_refresh_default_branch(FakeConn(), {"id": 42})

    assert result["status"] == "completed"
    assert result["default_branch"] == "main"
    assert result["sync"] == {"graph_action": "full_refresh", "current_snapshot_id": 42}
    assert refreshed == {"project_id": 42, "branch": "main"}
