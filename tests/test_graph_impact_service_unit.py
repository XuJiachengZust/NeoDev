import pytest

from service.services import graph_impact_service


def test_doc_change_impact_returns_document_relations_and_candidates(monkeypatch):
    change = {
        "id": 11,
        "document_id": 7,
        "doc_change_id": "DC-AUTH-001",
        "summary": "Update login token behavior",
        "source_commit": "doc-commit-1",
        "details_json": {
            "affected_repositories": ["auth-service"],
            "affected_modules": ["auth.session"],
            "affected_files": ["src/auth/session.py"],
            "affected_symbols": ["issue_token"],
            "risk_points": ["session expiry changes"],
            "suggested_steps": ["review auth session flow"],
        },
        "status": "pending_implementation",
    }
    document = {
        "id": 7,
        "doc_id": "REQ-AUTH",
        "title": "Auth token update",
        "relative_path": "requirements/auth.md",
        "relations_json": {
            "relations": [
                {
                    "type": "implements",
                    "target": "SRC-AUTH",
                    "evidence": "front matter relation",
                }
            ],
            "modules": ["auth.api"],
            "files": ["src/auth/api.py"],
            "symbols": ["login"],
        },
        "front_matter_json": {
            "component": "auth",
            "repository": "auth-service",
            "relations": [{"type": "depends_on", "target": "REQ-SESSION"}],
        },
    }

    monkeypatch.setattr(
        graph_impact_service.doc_change_repository,
        "find_by_doc_change_id",
        lambda conn, doc_change_id: change if doc_change_id == "DC-AUTH-001" else None,
    )
    monkeypatch.setattr(
        graph_impact_service.document_repository,
        "find_by_id",
        lambda conn, document_id: document if document_id == 7 else None,
    )

    result = graph_impact_service.doc_change_impact(
        object(),
        doc_change_id="DC-AUTH-001",
    )

    assert result["doc_change_id"] == "DC-AUTH-001"
    assert result["document_summary"]["doc_id"] == "REQ-AUTH"
    assert result["affected_repositories"] == ["auth-service"]
    assert set(result["affected_modules"]) == {"auth.session", "auth.api"}
    assert set(result["affected_files"]) == {"src/auth/session.py", "src/auth/api.py"}
    assert set(result["affected_symbols"]) == {"issue_token", "login"}
    assert result["confidence"] == "medium"
    assert result["risk_points"] == ["session expiry changes"]
    assert result["suggested_steps"] == ["review auth session flow"]
    assert any(item["source"] == "document.relations" for item in result["evidence"])
    assert any(item["source"] == "document.front_matter" for item in result["evidence"])


def test_doc_change_impact_rejects_missing_locator():
    with pytest.raises(graph_impact_service.GraphImpactError) as raised:
        graph_impact_service.doc_change_impact(object())

    assert raised.value.category == "invalid_argument"


def test_doc_change_impact_rejects_ambiguous_locator():
    with pytest.raises(graph_impact_service.GraphImpactError) as raised:
        graph_impact_service.doc_change_impact(
            object(),
            change_id=1,
            doc_change_id="DC-1",
        )

    assert raised.value.category == "invalid_argument"


def test_doc_change_impact_rejects_unknown_doc_change(monkeypatch):
    monkeypatch.setattr(
        graph_impact_service.doc_change_repository,
        "find_by_doc_change_id",
        lambda conn, doc_change_id: None,
    )

    with pytest.raises(graph_impact_service.GraphImpactError) as raised:
        graph_impact_service.doc_change_impact(object(), doc_change_id="DC-MISSING")

    assert raised.value.category == "not_found"
