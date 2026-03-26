"""Requirement tree doc status semantics should not treat generation placeholders as real docs."""


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


def _create_requirement(client_with_db, product_id: int, version_id: int, title: str, parent_id: int | None = None):
    response = client_with_db.post(
        f"/api/products/{product_id}/requirements",
        json={
            "title": title,
            "level": "story",
            "parent_id": parent_id,
            "priority": "medium",
            "version_id": version_id,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


class TestProductRequirementTreeDocStatus:
    def test_tree_distinguishes_saved_doc_from_generation_placeholder(self, client_with_db, pg_conn):
        product_id, version_id = _make_product_version(client_with_db)
        generating_req_id = _create_requirement(client_with_db, product_id, version_id, "生成中需求")
        saved_req_id = _create_requirement(client_with_db, product_id, version_id, "已有文档需求")

        with pg_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO requirement_doc_meta (requirement_id, version, generation_status, generation_started_at)
                VALUES (%s, 0, 'running', now())
                """,
                (generating_req_id,),
            )
            cur.execute(
                """
                INSERT INTO requirement_doc_meta (requirement_id, version, generated_by, file_path, generation_status)
                VALUES (%s, 2, 'manual', %s, 'completed')
                """,
                (saved_req_id, f"{product_id}/{saved_req_id}/doc.md"),
            )
        pg_conn.commit()

        response = client_with_db.get(f"/api/products/{product_id}/requirements/tree?version_id={version_id}")
        assert response.status_code == 200

        items = {item["id"]: item for item in response.json()}
        assert items[generating_req_id]["has_doc"] is False
        assert items[generating_req_id]["doc_status"] == "generating"
        assert items[saved_req_id]["has_doc"] is True
        assert items[saved_req_id]["doc_status"] == "ready"
