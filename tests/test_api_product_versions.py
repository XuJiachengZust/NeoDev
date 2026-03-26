"""API tests for product version branch mapping behavior."""


class TestProductVersionBranchMappingApi:
    def test_set_branch_auto_creates_project_version_once(self, client_with_db):
        product = client_with_db.post("/api/products", json={"name": "neo"})
        assert product.status_code == 201
        product_id = product.json()["id"]

        project = client_with_db.post(
            f"/api/products/{product_id}/projects/create",
            json={"name": "proj-a", "repo_path": "/tmp/proj-a"},
        )
        assert project.status_code == 201
        project_id = project.json()["id"]

        version = client_with_db.post(
            f"/api/products/{product_id}/versions",
            json={"version_name": "1.0.0"},
        )
        assert version.status_code == 201
        version_id = version.json()["id"]

        before = client_with_db.get(f"/api/projects/{project_id}/versions")
        assert before.status_code == 200
        assert before.json() == []

        set_branch = client_with_db.post(
            f"/api/products/{product_id}/versions/{version_id}/branches",
            json={"project_id": project_id, "branch": "release/1.0"},
        )
        assert set_branch.status_code == 200
        assert set_branch.json()["project_id"] == project_id
        assert set_branch.json()["branch"] == "release/1.0"

        versions = client_with_db.get(f"/api/projects/{project_id}/versions")
        assert versions.status_code == 200
        assert len(versions.json()) == 1
        assert versions.json()[0]["branch"] == "release/1.0"

        set_branch_again = client_with_db.post(
            f"/api/products/{product_id}/versions/{version_id}/branches",
            json={"project_id": project_id, "branch": "release/1.0"},
        )
        assert set_branch_again.status_code == 200

        versions_again = client_with_db.get(f"/api/projects/{project_id}/versions")
        assert versions_again.status_code == 200
        assert len(versions_again.json()) == 1
        assert versions_again.json()[0]["branch"] == "release/1.0"
