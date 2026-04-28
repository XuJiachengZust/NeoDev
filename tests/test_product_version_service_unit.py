from service.services import product_version_service


def test_set_branch_creates_project_version_with_product_version_name(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        product_version_service.repo,
        "set_branch",
        lambda conn, version_id, project_id, branch: {
            "id": 1,
            "product_version_id": version_id,
            "project_id": project_id,
            "branch": branch,
        },
    )
    monkeypatch.setattr(
        product_version_service.repo,
        "find_by_id",
        lambda conn, version_id: {"id": version_id, "version_name": "V2.0R26C01"},
    )
    monkeypatch.setattr(
        product_version_service.version_repository,
        "find_by_project_and_branch",
        lambda conn, project_id, branch: None,
    )

    def fake_create_version(conn, project_id, branch, version_name=None):
        captured.update(
            {
                "project_id": project_id,
                "branch": branch,
                "version_name": version_name,
            }
        )
        return {"id": 7}, None

    monkeypatch.setattr(product_version_service.version_service, "create_version", fake_create_version)

    row = product_version_service.set_branch(object(), 3, 42, "release/V2.0R26C01")

    assert row["product_version_id"] == 3
    assert captured == {
        "project_id": 42,
        "branch": "release/V2.0R26C01",
        "version_name": "V2.0R26C01",
    }


def test_set_branch_backfills_missing_project_version_name(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        product_version_service.repo,
        "set_branch",
        lambda conn, version_id, project_id, branch: {
            "id": 1,
            "product_version_id": version_id,
            "project_id": project_id,
            "branch": branch,
        },
    )
    monkeypatch.setattr(
        product_version_service.repo,
        "find_by_id",
        lambda conn, version_id: {"id": version_id, "version_name": "V2.0R26C01"},
    )
    monkeypatch.setattr(
        product_version_service.version_repository,
        "find_by_project_and_branch",
        lambda conn, project_id, branch: {"id": 9, "project_id": project_id, "branch": branch, "version_name": None},
    )
    monkeypatch.setattr(
        product_version_service.version_repository,
        "update_version_name",
        lambda conn, version_id, version_name: captured.update(
            {"version_id": version_id, "version_name": version_name}
        ),
    )

    product_version_service.set_branch(object(), 3, 42, "release/V2.0R26C01")

    assert captured == {"version_id": 9, "version_name": "V2.0R26C01"}
