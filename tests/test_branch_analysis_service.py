import uuid

import pytest

from service.services import branch_analysis_service
from service.services import product_version_service


def _create_product(conn, code: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO products (name, code)
            VALUES (%s, %s)
            RETURNING id
            """,
            (f"branch-analysis-product-{code}", code),
        )
        product_id = cur.fetchone()[0]
    conn.commit()
    return product_id


def _create_project(conn, name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects (name, repo_path)
            VALUES (%s, %s)
            RETURNING id
            """,
            (name, f"/tmp/neodev-branch-analysis/{name}"),
        )
        project_id = cur.fetchone()[0]
    conn.commit()
    return project_id


def test_branch_analysis_service_validates_product_version_scope(pg_conn, monkeypatch):
    token = uuid.uuid4().hex[:8]
    product_id = _create_product(pg_conn, f"BA-{token}")
    project_id = _create_project(pg_conn, f"ba-project-{token}")
    version = product_version_service.create_version(pg_conn, product_id, "V-BA")
    product_version_service.set_branch(pg_conn, version["id"], project_id, "release/ba")
    pg_conn.commit()

    def fake_sync(conn, project_id_arg):
        assert project_id_arg == project_id
        return {
            "project_id": project_id_arg,
            "versions_synced": 1,
            "commits_synced": 0,
            "graph_actions": [],
            "graph_errors": None,
        }

    monkeypatch.setattr(branch_analysis_service, "_sync_project_graph", fake_sync)

    result = branch_analysis_service.analyze_version_branch(
        pg_conn,
        product_version_id=version["id"],
        project_id=project_id,
        branch="release/ba",
        force=True,
    )

    assert result["analysis_task"]["status"] == "completed"
    assert result["analysis_task"]["product_version_id"] == version["id"]
    assert result["analysis_task"]["project_id"] == project_id
    assert result["analysis_task"]["branch"] == "release/ba"
    assert result["analysis_task"]["progress"]["stage"] == "completed"
    assert result["analysis_task"]["analysis_action"] == "graph_sync"


def test_branch_analysis_service_rejects_branch_outside_version_scope(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_id = _create_product(pg_conn, f"BASCOPE-{token}")
    project_id = _create_project(pg_conn, f"ba-scope-project-{token}")
    version = product_version_service.create_version(pg_conn, product_id, "V-SCOPE")
    product_version_service.set_branch(pg_conn, version["id"], project_id, "release/allowed")
    pg_conn.commit()

    with pytest.raises(branch_analysis_service.BranchAnalysisError) as exc_info:
        branch_analysis_service.get_analysis_status(
            pg_conn,
            product_version_id=version["id"],
            project_id=project_id,
            branch="release/denied",
        )

    assert exc_info.value.category == "invalid_scope"
    assert exc_info.value.details["expected_branch"] == "release/allowed"
