from service.services import watch_service


def test_watch_refreshes_bound_branches(monkeypatch):
    calls = []

    monkeypatch.setattr(
        watch_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {
            "id": project_id,
            "repo_path": "D:/repo",
            "watch_enabled": True,
        },
    )
    monkeypatch.setattr(watch_service, "_list_bound_branches", lambda conn, project_id: ["main", "release/x"])

    from service.services import sync_service

    def fake_refresh(conn, project_id, branch):
        calls.append({"project_id": project_id, "branch": branch})
        return {"graph_action": "full_refresh", "current_snapshot_id": len(calls)}

    monkeypatch.setattr(sync_service, "refresh_graph_for_branch", fake_refresh)

    result = watch_service.run_once(object(), 7, {})

    assert calls == [
        {"project_id": 7, "branch": "main"},
        {"project_id": 7, "branch": "release/x"},
    ]
    assert result["actions"] == [
        {"branch": "main", "action": "full_refresh", "snapshot_id": 1},
        {"branch": "release/x", "action": "full_refresh", "snapshot_id": 2},
    ]


def test_watch_skips_disabled_project(monkeypatch):
    monkeypatch.setattr(
        watch_service.project_repo,
        "find_by_id",
        lambda conn, project_id: {"id": project_id, "watch_enabled": False},
    )

    assert watch_service.run_once(object(), 7, {}) == {
        "project_id": 7,
        "skipped": True,
        "reason": "watch_disabled",
    }
