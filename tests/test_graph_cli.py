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
