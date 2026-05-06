import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import service.repositories.doc_binding_repository as doc_binding_repository
import service.repositories.document_repository as document_repository


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


def _create_doc_binding_and_document(conn, code: str) -> tuple[dict, dict]:
    product_id = _create_product(conn, code)
    binding = doc_binding_repository.create(
        conn,
        product_id=product_id,
        repo_path=f"/tmp/doc-cli-{code}",
    )
    document = document_repository.create(
        conn,
        doc_binding_id=binding["id"],
        doc_id=f"DOC-CLI-{code}",
        relative_path="prd/overview.md",
        doc_type="prd",
        title="CLI DocChange Source",
    )
    conn.commit()
    return binding, document


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


def test_doc_change_register_cli_creates_pending_change(pg_conn):
    token = uuid.uuid4().hex[:8]
    _, document = _create_doc_binding_and_document(pg_conn, f"CHGREG-{token}")
    doc_change_id = "a" * 40

    proc = _run_cli(
        "doc",
        "change",
        "register",
        "--document-id",
        str(document["id"]),
        "--doc-change-id",
        doc_change_id,
        "--source-commit",
        "a" * 40,
        "--summary",
        "Add CLI doc change",
        "--created-by",
        "pytest",
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    payload = _payload(proc)
    change = payload["data"]["doc_change"]
    assert payload["ok"] is True
    assert payload["command"] == "doc change register"
    assert change["document_id"] == document["id"]
    assert change["doc_change_id"] == doc_change_id
    assert change["source_commit"] == "a" * 40
    assert change["summary"] == "Add CLI doc change"
    assert change["created_by"] == "pytest"
    assert change["status"] == "pending_implementation"


def test_doc_change_show_cli_returns_change_and_document(pg_conn):
    token = uuid.uuid4().hex[:8]
    _, document = _create_doc_binding_and_document(pg_conn, f"CHGSHOW-{token}")
    doc_change_id = "b" * 40
    register = _run_cli(
        "doc",
        "change",
        "register",
        "--document-id",
        str(document["id"]),
        "--doc-change-id",
        doc_change_id,
        "--json",
    )
    assert register.returncode == 0, register.stderr

    proc = _run_cli("doc", "change", "show", "--doc-change-id", doc_change_id, "--json")

    assert proc.returncode == 0, proc.stderr
    payload = _payload(proc)
    assert payload["command"] == "doc change show"
    assert payload["data"]["doc_change"]["doc_change_id"] == doc_change_id
    assert payload["data"]["document"]["id"] == document["id"]
    assert payload["data"]["document"]["doc_id"] == document["doc_id"]


def test_doc_change_mark_implemented_cli_is_idempotent(pg_conn):
    token = uuid.uuid4().hex[:8]
    _, document = _create_doc_binding_and_document(pg_conn, f"CHGIMPL-{token}")
    doc_change_id = "c" * 40
    register = _run_cli(
        "doc",
        "change",
        "register",
        "--document-id",
        str(document["id"]),
        "--doc-change-id",
        doc_change_id,
        "--json",
    )
    assert register.returncode == 0, register.stderr

    first = _run_cli(
        "doc",
        "change",
        "mark-implemented",
        "--doc-change-id",
        doc_change_id,
        "--json",
    )
    second = _run_cli(
        "doc",
        "change",
        "mark-implemented",
        "--doc-change-id",
        doc_change_id,
        "--json",
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    first_change = _payload(first)["data"]["doc_change"]
    second_change = _payload(second)["data"]["doc_change"]
    assert first_change["status"] == "implemented"
    assert second_change["status"] == "implemented"
    assert first_change["implemented_at"] is not None
    assert second_change["implemented_at"] == first_change["implemented_at"]


def test_doc_change_register_cli_missing_document_returns_not_found(pg_conn):
    proc = _run_cli(
        "doc",
        "change",
        "register",
        "--document-id",
        "99999999",
        "--doc-change-id",
        "d" * 40,
        "--json",
    )

    assert proc.returncode == 3
    payload = _payload(proc)
    assert payload["ok"] is False
    assert payload["command"] == "doc change register"
    assert payload["errors"][0]["category"] == "not_found"
