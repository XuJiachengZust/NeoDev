import pytest

from service.services import git_consistency_service


def test_verify_doc_change_creates_link_and_moves_to_in_implementation(monkeypatch):
    change = {
        "id": 17,
        "doc_change_id": "DC-AUTH-001",
        "status": "pending_implementation",
    }
    created_links = []
    marked = []

    monkeypatch.setattr(
        git_consistency_service.doc_change_repository,
        "find_by_doc_change_id",
        lambda conn, doc_change_id: change if doc_change_id == "DC-AUTH-001" else None,
    )

    def fake_create_link(conn, **kwargs):
        created_links.append(kwargs)
        return {"id": 31, **kwargs}

    monkeypatch.setattr(
        git_consistency_service.code_change_link_repository,
        "create",
        fake_create_link,
    )

    def fake_mark(conn, change_id):
        marked.append(change_id)
        return {**change, "status": "in_implementation"}

    monkeypatch.setattr(
        git_consistency_service.doc_change_repository,
        "mark_in_implementation",
        fake_mark,
    )

    result = git_consistency_service.verify_doc_change(
        object(),
        project_id=11,
        branch="release/V1.0",
        commit_sha="a" * 40,
        commit_message="feat: auth\n\nDocChange-ID: DC-AUTH-001\n",
    )

    assert result["status"] == "verified"
    assert result["doc_change_id"] == "DC-AUTH-001"
    assert result["verification_status"] == "verified"
    assert result["doc_change_status"] == "in_implementation"
    assert result["risk_level"] == "none"
    assert result["next_status"] == "in_implementation"
    assert result["dangerous_commit_required"] is False
    assert result["code_change_link"]["id"] == 31
    assert created_links == [
        {
            "doc_change_id": 17,
            "project_id": 11,
            "branch": "release/V1.0",
            "commit_sha": "a" * 40,
            "commit_message": "feat: auth\n\nDocChange-ID: DC-AUTH-001\n",
        }
    ]
    assert marked == [17]


def test_verify_doc_change_rejects_unknown_doc_change(monkeypatch):
    monkeypatch.setattr(
        git_consistency_service.doc_change_repository,
        "find_by_doc_change_id",
        lambda conn, doc_change_id: None,
    )

    with pytest.raises(git_consistency_service.GitConsistencyError) as raised:
        git_consistency_service.verify_doc_change(
            object(),
            project_id=11,
            branch="main",
            commit_sha="b" * 40,
            commit_message="fix: x\n\nDocChange-ID: DC-MISSING\n",
        )

    assert raised.value.category == "not_found"


def test_verify_doc_change_rejects_implemented_doc_change(monkeypatch):
    monkeypatch.setattr(
        git_consistency_service.doc_change_repository,
        "find_by_doc_change_id",
        lambda conn, doc_change_id: {
            "id": 17,
            "doc_change_id": doc_change_id,
            "status": "implemented",
        },
    )

    with pytest.raises(git_consistency_service.GitConsistencyError) as raised:
        git_consistency_service.verify_doc_change(
            object(),
            project_id=11,
            branch="main",
            commit_sha="b" * 40,
            commit_message="fix: x\n\nDocChange-ID: DC-DONE\n",
        )

    assert raised.value.category == "conflict"


def test_list_dangerous_commits_returns_open_records(monkeypatch):
    rows = [
        {
            "id": 3,
            "project_id": 11,
            "branch": "main",
            "commit_sha": "c" * 40,
            "status": "open",
        }
    ]
    monkeypatch.setattr(
        git_consistency_service.dangerous_commit_repository,
        "list_open",
        lambda conn, project_id=None: rows,
    )

    result = git_consistency_service.list_dangerous_commits(object(), project_id=11)

    assert result == {"dangerous_commits": rows, "count": 1}


def test_resolve_dangerous_commit_returns_resolved_record(monkeypatch):
    resolved = {
        "id": 3,
        "project_id": 11,
        "branch": "main",
        "commit_sha": "c" * 40,
        "status": "resolved",
        "resolved_by": "lead",
    }
    monkeypatch.setattr(
        git_consistency_service.dangerous_commit_repository,
        "resolve",
        lambda conn, record_id, resolved_by: resolved
        if record_id == 3 and resolved_by == "lead"
        else None,
    )

    result = git_consistency_service.resolve_dangerous_commit(
        object(),
        record_id=3,
        resolved_by="lead",
    )

    assert result == {"dangerous_commit": resolved}


def test_resolve_dangerous_commit_rejects_unknown_record(monkeypatch):
    monkeypatch.setattr(
        git_consistency_service.dangerous_commit_repository,
        "resolve",
        lambda conn, record_id, resolved_by: None,
    )

    with pytest.raises(git_consistency_service.GitConsistencyError) as raised:
        git_consistency_service.resolve_dangerous_commit(
            object(),
            record_id=404,
            resolved_by="lead",
        )

    assert raised.value.category == "not_found"


def test_post_push_refresh_delegates_to_graph_refresh(monkeypatch):
    refreshed = {
        "refresh_scope": {
            "product_version_id": 23,
            "project_id": 11,
            "branch": "release/V1.0",
            "node_ids": [],
            "paths": [],
            "commit_sha": "d" * 40,
        },
        "graph_nodes_updated": 2,
        "ai_descriptions_updated": 0,
        "embeddings_reused": 0,
        "embeddings_regenerated": 0,
        "status": "completed",
        "semantic_status": "refresh_requested",
        "degraded_reasons": [],
    }
    calls = []

    monkeypatch.setattr(
        git_consistency_service,
        "_resolve_bound_product_version",
        lambda conn, project_id, branch, version_id=None: 23,
    )

    def fake_refresh(conn, **kwargs):
        calls.append(kwargs)
        return refreshed

    monkeypatch.setattr(git_consistency_service.graph_refresh_service, "refresh_nodes", fake_refresh)

    result = git_consistency_service.post_push_refresh(
        object(),
        project_id=11,
        branch="release/V1.0",
        commit_sha="d" * 40,
    )

    assert result["project_id"] == 11
    assert result["branch"] == "release/V1.0"
    assert result["product_version_id"] == 23
    assert result["commits_synced"] == 0
    assert result["graph_nodes_updated"] == 2
    assert result["chains_updated"] == 0
    assert result["ai_descriptions_updated"] == 0
    assert result["embeddings_reused"] == 0
    assert result["embeddings_regenerated"] == 0
    assert result["status"] == "completed"
    assert calls == [
        {
            "product_version_id": 23,
            "project_id": 11,
            "branch": "release/V1.0",
            "commit_sha": "d" * 40,
        }
    ]


def test_post_push_refresh_rejects_unbound_project_branch(monkeypatch):
    monkeypatch.setattr(
        git_consistency_service,
        "_find_product_version_branches",
        lambda conn, project_id, branch: [],
    )

    with pytest.raises(git_consistency_service.GitConsistencyError) as raised:
        git_consistency_service.post_push_refresh(
            object(),
            project_id=11,
            branch="main",
        )

    assert raised.value.category == "not_found"
