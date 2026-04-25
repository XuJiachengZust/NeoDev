import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import service.repositories.doc_binding_repository as doc_binding_repository


ROOT = Path(__file__).resolve().parent.parent


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault(
        "DATABASE_URL",
        env.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/neodev"),
    )
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


def _create_product(conn, code: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO products (name, code)
            VALUES (%s, %s)
            RETURNING id
            """,
            (f"doc-cli-product-{code}", code),
        )
        product_id = cur.fetchone()[0]
    conn.commit()
    return product_id


def _make_doc_repo() -> Path:
    path = ROOT / ".test-tmp" / f"doc-cli-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    return path


def _write_doc(path: Path, front_matter: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{front_matter}\n---\n\ncontent\n", encoding="utf-8")


def test_doc_scan_cli_scans_binding_and_returns_summary(pg_conn):
    token = uuid.uuid4().hex[:8]
    repo_path = _make_doc_repo()
    try:
        product_id = _create_product(pg_conn, f"DOCCLI-{token}")
        binding = doc_binding_repository.create(
            pg_conn,
            product_id=product_id,
            repo_path=str(repo_path),
        )
        pg_conn.commit()
        _write_doc(
            repo_path / "prd" / "overview.md",
            f"""
doc_id: DOC-CLI-{token}
title: CLI Doc
doc_type: prd
product_key: DOCCLI-{token}
status: active
relations:
  target:
    - PRODUCT
""".strip(),
        )

        proc = _run_cli("doc", "scan", "--doc-binding-id", str(binding["id"]), "--json")

        assert proc.returncode == 0, proc.stderr
        payload = _payload(proc)
        assert payload["ok"] is True
        assert payload["command"] == "doc scan"
        assert payload["data"]["registered_count"] == 1
        assert payload["data"]["error_count"] == 0
        assert payload["data"]["documents"][0]["relative_path"] == "prd/overview.md"
    finally:
        shutil.rmtree(repo_path, ignore_errors=True)


def test_doc_scan_cli_missing_binding_returns_not_found(pg_conn):
    proc = _run_cli("doc", "scan", "--doc-binding-id", "99999999", "--json")

    assert proc.returncode == 3
    payload = _payload(proc)
    assert payload["ok"] is False
    assert payload["errors"][0]["category"] == "not_found"
