import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from service.repositories import doc_binding_repository
from service.repositories import doc_change_repository
from service.repositories import document_repository


ROOT = Path(__file__).resolve().parent.parent


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", env.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/neodev"))
    return subprocess.run(
        [sys.executable, "neodev.py", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _payload(proc: subprocess.CompletedProcess[str]) -> dict:
    assert proc.stdout
    return json.loads(proc.stdout)


def _make_project(conn, name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects (name, repo_path)
            VALUES (%s, %s)
            RETURNING id
            """,
            (name, f"/tmp/neodev-graph-cli/{name}"),
        )
        project_id = cur.fetchone()[0]
    conn.commit()
    return project_id


def _make_version(conn, product_id: int, version_name: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO product_versions (product_id, version_name)
            VALUES (%s, %s)
            RETURNING id
            """,
            (product_id, version_name),
        )
        version_id = cur.fetchone()[0]
    conn.commit()
    return version_id


def test_graph_impact_rejects_unknown_doc_change(pg_conn):
    impact = _run_cli(
        "graph",
        "impact",
        "--doc-change-id",
        f"DC-MISSING-{uuid.uuid4().hex[:8]}",
        "--json",
    )

    assert impact.returncode == 3
    payload = _payload(impact)
    assert payload["ok"] is False
    assert payload["command"] == "graph impact"
    assert payload["errors"][0]["category"] == "not_found"


def test_graph_impact_returns_docchange_scope(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"GRAPHIMPACT-{token}"

    create_product = _run_cli(
        "product",
        "create",
        "--name",
        f"Graph Impact Product {token}",
        "--product-code",
        product_code,
        "--json",
    )
    assert create_product.returncode == 0, create_product.stderr
    product_id = _payload(create_product)["data"]["product"]["id"]
    product_version_id = _make_version(pg_conn, product_id, f"V-{token}")

    binding = doc_binding_repository.create(
        pg_conn,
        product_id=product_id,
        product_version_id=product_version_id,
        repo_path=f"/tmp/neodev-docs/{token}",
        repo_url=f"https://example.test/docs/{token}.git",
        default_branch="main",
    )
    document = document_repository.create(
        pg_conn,
        doc_binding_id=binding["id"],
        product_version_id=product_version_id,
        doc_id=f"REQ-{token}",
        relative_path=f"requirements/{token}.md",
        front_matter_json={
            "repository": "auth-service",
            "relations": [{"type": "depends_on", "target": "REQ-SESSION"}],
        },
        relations_json={
            "modules": ["auth.api"],
            "files": ["src/auth/api.py"],
            "symbols": ["login"],
        },
        title=f"Impact Requirement {token}",
    )
    change = doc_change_repository.create(
        pg_conn,
        document_id=document["id"],
        doc_change_id=f"DC-{token}",
        summary="Update login behavior",
        details_json={
            "affected_repositories": ["auth-service"],
            "affected_files": ["src/auth/session.py"],
        },
    )
    pg_conn.commit()

    impact = _run_cli(
        "graph",
        "impact",
        "--change-id",
        str(change["id"]),
        "--json",
    )

    assert impact.returncode == 0, impact.stderr
    payload = _payload(impact)
    assert payload["ok"] is True
    assert payload["command"] == "graph impact"
    data = payload["data"]
    assert data["doc_change_id"] == f"DC-{token}"
    assert data["document_summary"]["doc_id"] == f"REQ-{token}"
    assert data["affected_repositories"] == ["auth-service"]
    assert set(data["affected_files"]) == {"src/auth/session.py", "src/auth/api.py"}
    assert data["affected_symbols"] == ["login"]
    assert data["confidence"] == "medium"
    assert data["evidence"]


def test_graph_entity_context_rejects_branch_outside_product_version(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"GRAPHCTX-{token}"
    project_id = _make_project(pg_conn, f"graph-ctx-project-{token}")

    create_product = _run_cli(
        "product",
        "create",
        "--name",
        f"Graph Context Product {token}",
        "--product-code",
        product_code,
        "--json",
    )
    assert create_product.returncode == 0, create_product.stderr

    create_version = _run_cli(
        "product",
        "version",
        "create",
        "--product-code",
        product_code,
        "--version-name",
        "V1.0",
        "--json",
    )
    assert create_version.returncode == 0, create_version.stderr
    version_id = _payload(create_version)["data"]["version"]["id"]

    bind_branch = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--version-id",
        str(version_id),
        "--project-id",
        str(project_id),
        "--branch",
        "release/V1.0",
        "--json",
    )
    assert bind_branch.returncode == 0, bind_branch.stderr

    context = _run_cli(
        "graph",
        "entity-context",
        "--version-id",
        str(version_id),
        "--project-id",
        str(project_id),
        "--branch",
        "feature/not-bound",
        "--entity-id",
        "Function:auth:login",
        "--json",
    )

    assert context.returncode == 2
    payload = _payload(context)
    assert payload["ok"] is False
    assert payload["command"] == "graph entity-context"
    assert payload["errors"][0]["category"] == "invalid_scope"
    assert payload["errors"][0]["details"]["expected_branch"] == "release/V1.0"
    assert payload["errors"][0]["details"]["actual_branch"] == "feature/not-bound"


def test_graph_get_chain_rejects_multiple_start_locators(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"GRAPHCHAIN-{token}"
    project_id = _make_project(pg_conn, f"graph-chain-project-{token}")

    create_product = _run_cli(
        "product",
        "create",
        "--name",
        f"Graph Chain Product {token}",
        "--product-code",
        product_code,
        "--json",
    )
    assert create_product.returncode == 0, create_product.stderr

    create_version = _run_cli(
        "product",
        "version",
        "create",
        "--product-code",
        product_code,
        "--version-name",
        "V1.0",
        "--json",
    )
    assert create_version.returncode == 0, create_version.stderr
    version_id = _payload(create_version)["data"]["version"]["id"]

    bind_branch = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--version-id",
        str(version_id),
        "--project-id",
        str(project_id),
        "--branch",
        "release/V1.0",
        "--json",
    )
    assert bind_branch.returncode == 0, bind_branch.stderr

    chain = _run_cli(
        "graph",
        "get-chain",
        "--version-id",
        str(version_id),
        "--project-id",
        str(project_id),
        "--branch",
        "release/V1.0",
        "--start-node",
        "Function:auth:login",
        "--symbol",
        "login",
        "--json",
    )

    assert chain.returncode == 2
    payload = _payload(chain)
    assert payload["ok"] is False
    assert payload["command"] == "graph get-chain"
    assert payload["errors"][0]["category"] == "invalid_argument"
