import uuid
from datetime import datetime
from datetime import timezone

import psycopg2
import pytest

import service.repositories.code_change_link_repository as code_change_link_repository
import service.repositories.dangerous_commit_repository as dangerous_commit_repository
import service.repositories.doc_binding_repository as doc_binding_repository
import service.repositories.doc_change_repository as doc_change_repository
import service.repositories.document_repository as document_repository


def _create_product(conn) -> int:
    token = uuid.uuid4().hex[:8]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO products (name, code)
            VALUES (%s, %s)
            RETURNING id
            """,
            (f"metadata-product-{token}", f"META-{token}"),
        )
        return cur.fetchone()[0]


def _create_project(conn) -> int:
    token = uuid.uuid4().hex[:8]
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects (name, repo_path)
            VALUES (%s, %s)
            RETURNING id
            """,
            (f"metadata-project-{token}", f"/tmp/meta/{token}"),
        )
        return cur.fetchone()[0]


def test_doc_binding_create_and_find_round_trip(metadata_db_case):
    product_id = _create_product(metadata_db_case)
    created = doc_binding_repository.create(
        metadata_db_case,
        product_id=product_id,
        repo_path="/workspace/docs",
        repo_url="https://example.com/repo.git",
        default_branch="main",
    )

    found = doc_binding_repository.find_by_id(metadata_db_case, created["id"])
    active = doc_binding_repository.list_active_by_product(metadata_db_case, product_id)

    assert found is not None
    assert found["product_id"] == product_id
    assert found["repo_path"] == "/workspace/docs"
    assert found["repo_url"] == "https://example.com/repo.git"
    assert found["default_branch"] == "main"
    assert found["is_active"] is True
    assert len(active) == 1
    assert active[0]["id"] == created["id"]


def test_doc_change_id_unique_constraint_is_enforced(metadata_db_case):
    product_id = _create_product(metadata_db_case)
    binding = doc_binding_repository.create(
        metadata_db_case, product_id=product_id, repo_path="/docs"
    )
    document = document_repository.create(
        metadata_db_case,
        doc_binding_id=binding["id"],
        doc_id=f"DOC-{uuid.uuid4().hex[:10]}",
        relative_path="design/overview.md",
    )

    doc_change_id = f"CHANGE-{uuid.uuid4().hex[:10]}"
    first = doc_change_repository.create(
        metadata_db_case,
        document_id=document["id"],
        doc_change_id=doc_change_id,
    )
    assert first["doc_change_id"] == doc_change_id

    with pytest.raises(psycopg2.IntegrityError):
        doc_change_repository.create(
            metadata_db_case,
            document_id=document["id"],
            doc_change_id=doc_change_id,
        )


def test_dangerous_commit_resolve_persists_resolution_fields(metadata_db_case):
    project_id = _create_project(metadata_db_case)
    created = dangerous_commit_repository.create(
        metadata_db_case,
        project_id=project_id,
        branch="main",
        commit_sha="a" * 40,
        risk_level="high",
        reason="api key leaked",
    )
    open_rows = dangerous_commit_repository.list_open(metadata_db_case, project_id=project_id)
    assert len(open_rows) == 1
    assert open_rows[0]["id"] == created["id"]
    assert open_rows[0]["status"] == "open"

    resolved = dangerous_commit_repository.resolve(
        metadata_db_case,
        record_id=created["id"],
        resolved_by="security-bot",
    )
    assert resolved is not None
    assert resolved["status"] == "resolved"
    assert resolved["resolved_by"] == "security-bot"
    assert resolved["resolved_at"] is not None

    after = dangerous_commit_repository.find_by_id(metadata_db_case, created["id"])
    assert after is not None
    assert after["status"] == "resolved"
    assert after["resolved_by"] == "security-bot"
    assert after["resolved_at"] is not None
    assert dangerous_commit_repository.list_open(metadata_db_case, project_id=project_id) == []


def test_code_change_link_create_and_list_by_doc_change(metadata_db_case):
    product_id = _create_product(metadata_db_case)
    project_id = _create_project(metadata_db_case)
    binding = doc_binding_repository.create(
        metadata_db_case, product_id=product_id, repo_path="/docs"
    )
    document = document_repository.create(
        metadata_db_case,
        doc_binding_id=binding["id"],
        doc_id=f"DOC-{uuid.uuid4().hex[:10]}",
        relative_path="api/spec.md",
    )
    change = doc_change_repository.create(
        metadata_db_case,
        document_id=document["id"],
        doc_change_id=f"CHANGE-{uuid.uuid4().hex[:10]}",
    )

    created = code_change_link_repository.create(
        metadata_db_case,
        doc_change_id=change["id"],
        project_id=project_id,
        branch="main",
        commit_sha="b" * 40,
        commit_message="Link doc change to implementation commit",
    )
    rows = code_change_link_repository.list_by_doc_change(metadata_db_case, change["id"])

    assert created["doc_change_id"] == change["id"]
    assert created["project_id"] == project_id
    assert created["commit_message"] == "Link doc change to implementation commit"
    assert len(rows) == 1
    assert rows[0]["id"] == created["id"]
    assert rows[0]["commit_message"] == "Link doc change to implementation commit"


def test_document_create_persists_last_scanned_at_and_json(metadata_db_case):
    product_id = _create_product(metadata_db_case)
    binding = doc_binding_repository.create(
        metadata_db_case, product_id=product_id, repo_path="/docs"
    )
    scan_time = datetime(2026, 4, 24, 12, 0, 0, tzinfo=timezone.utc)
    front_matter = {"owner": "platform", "priority": "p1"}
    relations = {"requires": ["DOC-ROOT"], "blocks": []}

    created = document_repository.create(
        metadata_db_case,
        doc_binding_id=binding["id"],
        doc_id=f"DOC-{uuid.uuid4().hex[:10]}",
        relative_path="metadata/scan.md",
        front_matter_json=front_matter,
        relations_json=relations,
        last_scanned_at=scan_time,
    )
    found = document_repository.find_by_id(metadata_db_case, created["id"])

    assert created["last_scanned_at"] == scan_time
    assert created["front_matter_json"] == front_matter
    assert created["relations_json"] == relations
    assert found is not None
    assert found["last_scanned_at"] == scan_time
    assert found["front_matter_json"] == front_matter
    assert found["relations_json"] == relations


def test_dangerous_commit_resolve_is_idempotent_for_audit_fields(metadata_db_case):
    project_id = _create_project(metadata_db_case)
    created = dangerous_commit_repository.create(
        metadata_db_case,
        project_id=project_id,
        branch="main",
        commit_sha="c" * 40,
        reason="unsafe change",
    )

    first = dangerous_commit_repository.resolve(
        metadata_db_case,
        record_id=created["id"],
        resolved_by="first-resolver",
    )
    second = dangerous_commit_repository.resolve(
        metadata_db_case,
        record_id=created["id"],
        resolved_by="second-resolver",
    )

    assert first is not None
    assert second is not None
    assert first["status"] == "resolved"
    assert second["status"] == "resolved"
    assert first["resolved_by"] == "first-resolver"
    assert second["resolved_by"] == "first-resolver"
    assert second["resolved_at"] == first["resolved_at"]


def test_doc_change_mark_implemented_is_idempotent_for_implemented_at(metadata_db_case):
    product_id = _create_product(metadata_db_case)
    binding = doc_binding_repository.create(
        metadata_db_case, product_id=product_id, repo_path="/docs"
    )
    document = document_repository.create(
        metadata_db_case,
        doc_binding_id=binding["id"],
        doc_id=f"DOC-{uuid.uuid4().hex[:10]}",
        relative_path="design/implemented.md",
    )
    change = doc_change_repository.create(
        metadata_db_case,
        document_id=document["id"],
        doc_change_id=f"CHANGE-{uuid.uuid4().hex[:10]}",
    )

    first = doc_change_repository.mark_implemented(metadata_db_case, change["id"])
    sentinel_time = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    with metadata_db_case.cursor() as cur:
        cur.execute(
            """
            UPDATE doc_changes
            SET implemented_at = %s, status = 'implemented'
            WHERE id = %s
            """,
            (sentinel_time, change["id"]),
        )
    second = doc_change_repository.mark_implemented(metadata_db_case, change["id"])

    assert first is not None
    assert second is not None
    assert first["status"] == "implemented"
    assert second["status"] == "implemented"
    assert first["implemented_at"] is not None
    assert second["implemented_at"] == sentinel_time


def test_metadata_db_case_can_change_search_path(metadata_db_case):
    with metadata_db_case.cursor() as cur:
        cur.execute("SET search_path TO public")
    metadata_db_case.commit()


def test_metadata_db_case_restores_expected_search_path(
    metadata_db_case, metadata_repo_schema_name
):
    with metadata_db_case.cursor() as cur:
        cur.execute("SELECT current_schemas(false)")
        schemas = cur.fetchone()[0]

    assert schemas[:2] == [metadata_repo_schema_name, "public"]
