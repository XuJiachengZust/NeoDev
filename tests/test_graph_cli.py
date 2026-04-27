import json
import os
import subprocess
import sys
import uuid
from pathlib import Path


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


def test_graph_semantic_search_rejects_unbound_product_version(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"GRAPH-{token}"

    create_product = _run_cli(
        "product",
        "create",
        "--name",
        f"Graph Product {token}",
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

    search = _run_cli(
        "graph",
        "semantic-search",
        "--product-code",
        product_code,
        "--version-name",
        "V1.0",
        "--query",
        "login token",
        "--json",
    )

    assert search.returncode == 2
    payload = _payload(search)
    assert payload["ok"] is False
    assert payload["command"] == "graph semantic-search"
    assert payload["errors"][0]["category"] == "invalid_scope"
    assert payload["errors"][0]["details"]["product_version_id"] == _payload(create_version)["data"]["version"]["id"]


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
