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
