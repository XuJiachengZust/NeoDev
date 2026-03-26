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


def _create_requirement(client_with_db, product_id: int, version_id: int, title: str, level: str):
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


class TestRequirementDocChildrenGate:
    def test_can_generate_children_returns_reason_code_for_missing_doc(self, client_with_db):
        product_id, version_id = _make_product_version(client_with_db)
        requirement_id = _create_requirement(client_with_db, product_id, version_id, "Epic A", "epic")

        response = client_with_db.get(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc/can-generate-children"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["can_generate_children"] is False
        assert payload["reason_code"] == "doc_missing"
        assert isinstance(payload["detail"], str) and payload["detail"]

    def test_can_generate_children_blocks_running_doc_and_generate_endpoint_returns_409(self, client_with_db, pg_conn):
        product_id, version_id = _make_product_version(client_with_db)
        requirement_id = _create_requirement(client_with_db, product_id, version_id, "Story A", "story")

        with pg_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO requirement_doc_meta (requirement_id, version, generation_status, generation_started_at)
                VALUES (%s, 0, 'running', now())
                """,
                (requirement_id,),
            )
        pg_conn.commit()

        gate = client_with_db.get(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc/can-generate-children"
        )
        assert gate.status_code == 200
        gate_payload = gate.json()
        assert gate_payload["can_generate_children"] is False
        assert gate_payload["reason_code"] == "doc_generating"

        generate = client_with_db.post(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc/generate-children"
        )
        assert generate.status_code == 409
        assert isinstance(generate.json()["detail"], str) and generate.json()["detail"]

    def test_can_generate_children_returns_failed_reason_code_when_parent_doc_failed(self, client_with_db, pg_conn):
        product_id, version_id = _make_product_version(client_with_db)
        requirement_id = _create_requirement(client_with_db, product_id, version_id, "Story Failed", "story")

        with pg_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO requirement_doc_meta (requirement_id, version, generation_status, generation_error)
                VALUES (%s, 1, 'failed', 'workflow exploded')
                """,
                (requirement_id,),
            )
        pg_conn.commit()

        response = client_with_db.get(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc/can-generate-children"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["can_generate_children"] is False
        assert payload["reason_code"] == "doc_failed"
        assert isinstance(payload["detail"], str) and payload["detail"]

    def test_can_generate_children_allows_saved_doc(self, client_with_db, pg_conn):
        product_id, version_id = _make_product_version(client_with_db)
        requirement_id = _create_requirement(client_with_db, product_id, version_id, "Epic Ready", "epic")

        with pg_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO requirement_doc_meta (requirement_id, version, generated_by, file_path, generation_status)
                VALUES (%s, 2, 'manual', %s, 'completed')
                """,
                (requirement_id, f"{product_id}/{requirement_id}/doc.md"),
            )
        pg_conn.commit()

        response = client_with_db.get(
            f"/api/products/{product_id}/requirements/{requirement_id}/doc/can-generate-children"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["can_generate_children"] is True
        assert payload["reason_code"] is None
        assert isinstance(payload["detail"], str) and payload["detail"]
