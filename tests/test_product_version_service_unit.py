from service.services import product_version_service


def test_set_branch_records_product_version_branch_only(monkeypatch):
    captured = {}

    def fake_set_branch(conn, version_id, project_id, branch):
        captured.update(
            {
                "version_id": version_id,
                "project_id": project_id,
                "branch": branch,
            }
        )
        return {
            "id": 1,
            "product_version_id": version_id,
            "project_id": project_id,
            "branch_name": branch,
        }

    monkeypatch.setattr(product_version_service.repo, "set_branch", fake_set_branch)

    row = product_version_service.set_branch(object(), 3, 42, " release/V2.0R26C01 ")

    assert row["product_version_id"] == 3
    assert row["branch_name"] == "release/V2.0R26C01"
    assert captured == {
        "version_id": 3,
        "project_id": 42,
        "branch": "release/V2.0R26C01",
    }
