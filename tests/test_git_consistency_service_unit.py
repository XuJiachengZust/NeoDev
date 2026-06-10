import pytest

from service.services import git_consistency_service


def _stub_dangerous_commit(monkeypatch):
    created = []

    monkeypatch.setattr(
        git_consistency_service.dangerous_commit_repository,
        "find_open_by_identity",
        lambda conn, project_id, branch, commit_sha: None,
    )

    def fake_create(conn, **kwargs):
        row = {"id": 91, **kwargs}
        created.append(row)
        return row

    monkeypatch.setattr(
        git_consistency_service.dangerous_commit_repository,
        "create",
        fake_create,
    )
    return created


def test_verify_doc_change_creates_link_and_moves_to_in_implementation(monkeypatch):
    doc_commit = "d" * 40
    change = {
        "id": 17,
        "doc_change_id": doc_commit,
        "status": "pending_implementation",
    }
    created_links = []
    marked = []

    monkeypatch.setattr(
        git_consistency_service.doc_change_repository,
        "find_by_doc_change_id",
        lambda conn, doc_change_id: change if doc_change_id == doc_commit else None,
    )

    def fake_create_link(conn, **kwargs):
        created_links.append(kwargs)
        return {"id": 31, **kwargs}

    monkeypatch.setattr(
        git_consistency_service.code_change_link_repository,
        "create",
        fake_create_link,
    )
    monkeypatch.setattr(
        git_consistency_service.code_change_link_repository,
        "list_by_commit",
        lambda conn, project_id, branch, commit_sha: [],
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
        commit_message=f"feat: auth\n\nDocChange-ID: {doc_commit}\n",
    )

    assert result["status"] == "verified"
    assert result["doc_change_id"] == doc_commit
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
            "commit_message": f"feat: auth\n\nDocChange-ID: {doc_commit}\n",
        }
    ]
    assert marked == [17]


def test_verify_doc_change_reuses_existing_code_change_link(monkeypatch):
    doc_commit = "d" * 40
    change = {
        "id": 17,
        "doc_change_id": doc_commit,
        "status": "in_implementation",
    }
    existing_link = {
        "id": 41,
        "doc_change_id": 17,
        "project_id": 11,
        "branch": "main",
        "commit_sha": "a" * 40,
        "commit_message": f"feat: auth\n\nDocChange-ID: {doc_commit}\n",
    }
    created_links = []
    marked = []

    monkeypatch.setattr(
        git_consistency_service.doc_change_repository,
        "find_by_doc_change_id",
        lambda conn, doc_change_id: change if doc_change_id == doc_commit else None,
    )
    monkeypatch.setattr(
        git_consistency_service.code_change_link_repository,
        "list_by_commit",
        lambda conn, project_id, branch, commit_sha: [existing_link],
    )

    def fake_create_link(conn, **kwargs):
        created_links.append(kwargs)
        return {"id": 99, **kwargs}

    monkeypatch.setattr(
        git_consistency_service.code_change_link_repository,
        "create",
        fake_create_link,
    )

    def fake_mark(conn, change_id):
        marked.append(change_id)
        return change

    monkeypatch.setattr(
        git_consistency_service.doc_change_repository,
        "mark_in_implementation",
        fake_mark,
    )

    result = git_consistency_service.verify_doc_change(
        object(),
        project_id=11,
        branch="main",
        commit_sha="a" * 40,
        commit_message=f"feat: auth\n\nDocChange-ID: {doc_commit}\n",
    )

    assert result["status"] == "verified"
    assert result["code_change_link"] == existing_link
    assert created_links == []
    assert marked == [17]


def test_verify_doc_change_rejects_unknown_doc_change(monkeypatch):
    created = _stub_dangerous_commit(monkeypatch)
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
            commit_message=f"fix: x\n\nDocChange-ID: {'f' * 40}\n",
        )

    assert raised.value.category == "not_found"
    assert raised.value.details["dangerous_commit"]["id"] == 91
    assert created[0]["reason"] == "doc change not found"


def test_verify_doc_change_registers_dangerous_commit_for_missing_trailer(monkeypatch):
    created = _stub_dangerous_commit(monkeypatch)

    with pytest.raises(git_consistency_service.GitConsistencyError) as raised:
        git_consistency_service.verify_doc_change(
            object(),
            project_id=11,
            branch="main",
            commit_sha="b" * 40,
            commit_message="fix: missing trailer",
        )

    assert raised.value.category == "invalid_argument"
    assert raised.value.details["dangerous_commit"]["id"] == 91
    assert created == [
        {
            "id": 91,
            "project_id": 11,
            "branch": "main",
            "commit_sha": "b" * 40,
            "risk_level": "high",
            "reason": "DocChange-ID trailer is required",
            "extra_json": {
                "category": "invalid_argument",
                "details": {},
                "commit_message": "fix: missing trailer",
            },
        }
    ]


def test_verify_doc_change_rejects_implemented_doc_change(monkeypatch):
    created = _stub_dangerous_commit(monkeypatch)
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
            commit_message=f"fix: x\n\nDocChange-ID: {'e' * 40}\n",
        )

    assert raised.value.category == "conflict"
    assert raised.value.details["dangerous_commit"]["id"] == 91
    assert created[0]["reason"] == "doc change is already implemented"


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


def test_git_consistency_service_has_no_post_push_refresh_entrypoint():
    assert not hasattr(git_consistency_service, "post_push_refresh")
