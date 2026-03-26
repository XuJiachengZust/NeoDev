import shutil
import uuid
from pathlib import Path

import pytest

from service.dependencies import get_requirement_doc_storage
from service.main import app
from service.storage import RequirementDocStorage


def _make_product_version(client_with_db):
    product = client_with_db.post("/api/products", json={"name": "neo"})
    assert product.status_code == 201
    product_id = product.json()["id"]

    version = client_with_db.post(
        f"/api/products/{product_id}/versions",
        json={"version_name": "1.0.0"},
    )
    assert version.status_code == 201
    version_id = version.json()["id"]
    return product_id, version_id


def _create_requirement(client_with_db, product_id: int, version_id: int, title: str, level: str = "story"):
    response = client_with_db.post(
        f"/api/products/{product_id}/requirements",
        json={
            "title": title,
            "level": level,
            "priority": "medium",
            "version_id": version_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def doc_tmp_path():
    base = Path("D:/PycharmProjects/NeoDev/tests/.tmp_requirement_docs")
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"case_{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def client_with_doc_storage(client_with_db, doc_tmp_path):
    def override_storage():
        return RequirementDocStorage(root=str(doc_tmp_path))

    app.dependency_overrides[get_requirement_doc_storage] = override_storage
    try:
        yield client_with_db, doc_tmp_path
    finally:
        app.dependency_overrides.pop(get_requirement_doc_storage, None)


class TestRequirementDocApi:
    def test_save_doc_then_versions_and_diff_follow_main_path(self, client_with_doc_storage):
        client, storage_root = client_with_doc_storage
        product_id, version_id = _make_product_version(client)
        requirement_id = _create_requirement(client, product_id, version_id, "Story Doc")

        first_save = client.put(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc",
            json={"content": "# v1", "generated_by": "manual"},
        )
        assert first_save.status_code == 200
        assert first_save.json()["version"] == 1

        second_save = client.put(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc",
            json={"content": "# v2", "generated_by": "manual"},
        )
        assert second_save.status_code == 200
        assert second_save.json()["version"] == 2

        get_doc = client.get(f"/api/products/{product_id}/requirements/{requirement_id}/doc")
        assert get_doc.status_code == 200
        assert get_doc.json()["content"] == "# v2"
        assert get_doc.json()["version"] == 2

        versions = client.get(f"/api/products/{product_id}/requirements/{requirement_id}/doc/versions")
        assert versions.status_code == 200
        assert versions.json() == [{"version": 1}, {"version": 2}]

        diff = client.get(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc/diff",
            params={"v1": 1, "v2": 2},
        )
        assert diff.status_code == 200
        assert diff.json() == {"v1": "# v1", "v2": "# v2"}

        archived = storage_root / str(product_id) / str(requirement_id) / "versions" / "v1.md"
        assert archived.read_text(encoding="utf-8") == "# v1"

    def test_diff_returns_null_for_missing_version_instead_of_500(self, client_with_doc_storage):
        client, _ = client_with_doc_storage
        product_id, version_id = _make_product_version(client)
        requirement_id = _create_requirement(client, product_id, version_id, "Story Diff")

        save = client.put(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc",
            json={"content": "# current", "generated_by": "manual"},
        )
        assert save.status_code == 200

        diff = client.get(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc/diff",
            params={"v1": 99, "v2": 1},
        )
        assert diff.status_code == 200
        assert diff.json() == {"v1": None, "v2": "# current"}

    def test_generation_status_returns_null_then_failed_semantics(self, client_with_doc_storage, pg_conn):
        client, _ = client_with_doc_storage
        product_id, version_id = _make_product_version(client)
        requirement_id = _create_requirement(client, product_id, version_id, "Story Status")

        empty = client.get(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc/generation-status"
        )
        assert empty.status_code == 200
        assert empty.json() == {
            "generation_status": None,
            "generation_started_at": None,
            "generation_error": None,
        }

        with pg_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO requirement_doc_meta (requirement_id, version, generation_status, generation_error)
                VALUES (%s, 0, 'failed', 'workflow exploded')
                """,
                (requirement_id,),
            )
        pg_conn.commit()

        failed = client.get(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc/generation-status"
        )
        assert failed.status_code == 200
        payload = failed.json()
        assert payload["generation_status"] == "failed"
        assert payload["generation_error"] == "workflow exploded"
        assert payload["generation_started_at"] is None
