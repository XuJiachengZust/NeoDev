import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

from service.cli.commands import doc as doc_cli_command
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


def _create_version(conn, product_id: int, version_name: str) -> int:
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


def _create_project(conn, product_id: int, name: str, repo_path: str, repo_url: str | None = None) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO projects (name, repo_path, repo_url, product_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (name, repo_path, repo_url, product_id),
        )
        project_id = cur.fetchone()[0]
    conn.commit()
    return project_id


def _create_doc_binding_and_document(conn, code: str) -> tuple[dict, dict]:
    product_id = _create_product(conn, code)
    product_version_id = _create_version(conn, product_id, f"V-{code}")
    binding = doc_binding_repository.create(
        conn,
        product_id=product_id,
        product_version_id=product_version_id,
        repo_path=f"/tmp/doc-cli-{code}",
    )
    document = document_repository.create(
        conn,
        doc_binding_id=binding["id"],
        product_version_id=product_version_id,
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


def test_doc_binding_create_cli_uses_project_source_and_returns_import_command(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"BINDCLI-{token}"
    product_id = _create_product(pg_conn, product_code)
    product_version_id = _create_version(pg_conn, product_id, f"V-{token}")
    project_id = _create_project(
        pg_conn,
        product_id,
        f"docs-{token}",
        f"git@example.com:docs/{token}.git",
    )

    proc = _run_cli(
        "doc",
        "binding",
        "create",
        "--product-code",
        product_code,
        "--version-id",
        str(product_version_id),
        "--project-id",
        str(project_id),
        "--branch",
        "release/V1",
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    payload = _payload(proc)
    binding = payload["data"]["binding"]
    assert payload["ok"] is True
    assert payload["command"] == "doc binding create"
    assert binding["product_id"] == product_id
    assert binding["repo_url"] == f"git@example.com:docs/{token}.git"
    assert binding["repo_path"].endswith(f"docs-{token}")
    assert binding["default_branch"] == "release/V1"
    assert payload["data"]["import_command"].endswith(
        f"doc import --doc-binding-id {binding['id']} --json"
    )


def test_doc_binding_list_cli_returns_active_bindings(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"BINDLIST-{token}"
    product_id = _create_product(pg_conn, product_code)
    product_version_id = _create_version(pg_conn, product_id, f"V-{token}")
    binding = doc_binding_repository.create(
        pg_conn,
        product_id=product_id,
        product_version_id=product_version_id,
        repo_path=f"/tmp/docs/{token}",
        repo_url=f"https://example.invalid/docs/{token}.git",
        default_branch="main",
    )
    pg_conn.commit()

    proc = _run_cli(
        "doc",
        "binding",
        "list",
        "--product-code",
        product_code,
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    payload = _payload(proc)
    bindings = payload["data"]["bindings"]
    assert payload["command"] == "doc binding list"
    assert [row["id"] for row in bindings] == [binding["id"]]


def test_doc_binding_switch_handler_archives_before_creating_target_without_auto_import(monkeypatch):
    fake_conn = object()
    old_binding = {"id": 7, "product_id": 3, "product_version_id": 11}
    archived_binding = {
        **old_binding,
        "repo_path": "",
        "repo_url": "",
        "default_branch": "",
        "is_active": False,
    }
    product = {"id": 3, "code": "SWITCH"}
    version = {"id": 13, "product_id": 3, "version_name": "V2"}
    calls = []

    def fake_with_db(callback):
        return callback(fake_conn)

    def fake_find_active_by_id(conn, binding_id):
        calls.append(("find_active_by_id", binding_id))
        assert conn is fake_conn
        return old_binding

    def fake_find_product(conn, product_id):
        calls.append(("find_product", product_id))
        return product

    def fake_resolve_version(conn, resolved_product, args):
        calls.append(("resolve_version", args.version_id))
        assert resolved_product == product
        return version

    def fake_archive_binding_data(conn, binding_id):
        calls.append(("archive_binding_data", binding_id))
        return archived_binding

    def fake_create(conn, **kwargs):
        calls.append(("create", kwargs))
        return {
            "id": 17,
            "product_id": kwargs["product_id"],
            "product_version_id": kwargs["product_version_id"],
            "repo_path": kwargs["repo_path"],
            "repo_url": kwargs["repo_url"],
            "default_branch": kwargs["default_branch"],
            "is_active": kwargs["is_active"],
        }

    monkeypatch.setattr(doc_cli_command, "_with_db", fake_with_db)
    monkeypatch.setattr(
        doc_cli_command.doc_binding_repository,
        "find_active_by_id",
        fake_find_active_by_id,
    )
    monkeypatch.setattr(doc_cli_command.product_repository, "find_by_id", fake_find_product)
    monkeypatch.setattr(doc_cli_command, "_resolve_version", fake_resolve_version)
    monkeypatch.setattr(
        doc_cli_command.doc_binding_repository,
        "archive_binding_data",
        fake_archive_binding_data,
    )
    monkeypatch.setattr(doc_cli_command.doc_binding_repository, "create", fake_create)

    payload = doc_cli_command.handle_doc_binding_switch(
        SimpleNamespace(
            command_name="doc binding switch",
            doc_binding_id=old_binding["id"],
            version_id=version["id"],
            version_name=None,
            repo_path="/tmp/docs/new",
            repo_url=None,
            branch="release/docs",
        )
    )

    assert [name for name, _ in calls] == [
        "find_active_by_id",
        "find_product",
        "resolve_version",
        "archive_binding_data",
        "create",
    ]
    create_kwargs = calls[-1][1]
    assert create_kwargs["product_id"] == product["id"]
    assert create_kwargs["product_version_id"] == version["id"]
    assert create_kwargs["repo_path"] == "/tmp/docs/new"
    assert create_kwargs["repo_url"] == ""
    assert create_kwargs["default_branch"] == "release/docs"
    assert create_kwargs["is_active"] is True
    assert payload["data"]["deleted_binding_id"] == old_binding["id"]
    assert payload["data"]["binding"]["id"] == 17
    assert "scan_command" in payload["data"]
    assert "import_command" in payload["data"]
    assert "registered_count" not in payload["data"]
    assert "imported_count" not in payload["data"]


def test_doc_binding_switch_cli_archives_old_binding_and_creates_target_binding(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_id = _create_product(pg_conn, f"BINSW-{token}")
    old_version_id = _create_version(pg_conn, product_id, f"V-OLD-{token}")
    target_version_id = _create_version(pg_conn, product_id, f"V-NEW-{token}")
    old_binding = doc_binding_repository.create(
        pg_conn,
        product_id=product_id,
        product_version_id=old_version_id,
        repo_path=f"/tmp/docs/switch-old-{token}",
        default_branch="main",
    )
    old_document = document_repository.create(
        pg_conn,
        doc_binding_id=old_binding["id"],
        product_version_id=old_version_id,
        doc_id=f"DOC-SW-{token}",
        relative_path="prd/overview.md",
        doc_type="prd",
        title="Switch Source",
    )
    pg_conn.commit()

    proc = _run_cli(
        "doc",
        "binding",
        "switch",
        "--doc-binding-id",
        str(old_binding["id"]),
        "--version-id",
        str(target_version_id),
        "--repo-path",
        f"/tmp/docs/switch-new-{token}",
        "--branch",
        "release/docs",
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    payload = _payload(proc)
    binding = payload["data"]["binding"]
    assert payload["ok"] is True
    assert payload["command"] == "doc binding switch"
    assert payload["data"]["deleted_binding_id"] == old_binding["id"]
    assert binding["product_id"] == product_id
    assert binding["product_version_id"] == target_version_id
    assert binding["repo_path"] == f"/tmp/docs/switch-new-{token}"
    assert binding["default_branch"] == "release/docs"
    assert payload["data"]["scan_command"].endswith(
        f"doc scan --doc-binding-id {binding['id']} --json"
    )
    assert payload["data"]["import_command"].endswith(
        f"doc import --doc-binding-id {binding['id']} --json"
    )
    assert "registered_count" not in payload["data"]
    assert "imported_count" not in payload["data"]

    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT repo_path, repo_url, git_source_key, default_branch, is_active
              FROM doc_bindings
             WHERE id = %s
            """,
            (old_binding["id"],),
        )
        archived = cur.fetchone()
    assert archived == ("", "", "", "", False)
    assert document_repository.find_by_id(pg_conn, old_document["id"]) is not None
    active_bindings = doc_binding_repository.list_active_by_product(pg_conn, product_id)
    assert active_bindings[0]["id"] == binding["id"]

    scan_old = _run_cli(
        "doc",
        "scan",
        "--doc-binding-id",
        str(old_binding["id"]),
        "--json",
    )
    assert scan_old.returncode == 3
    assert _payload(scan_old)["errors"][0]["category"] == "not_found"


def test_doc_binding_switch_cli_rolls_back_old_binding_when_target_source_conflicts(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_id = _create_product(pg_conn, f"BINSWCF-{token}")
    old_version_id = _create_version(pg_conn, product_id, f"V-OLD-{token}")
    target_version_id = _create_version(pg_conn, product_id, f"V-NEW-{token}")
    other_version_id = _create_version(pg_conn, product_id, f"V-OTHER-{token}")
    old_binding = doc_binding_repository.create(
        pg_conn,
        product_id=product_id,
        product_version_id=old_version_id,
        repo_url=f"https://example.invalid/docs/old-{token}.git",
        default_branch="main",
    )
    other_binding = doc_binding_repository.create(
        pg_conn,
        product_id=product_id,
        product_version_id=other_version_id,
        repo_url=f"https://example.invalid/docs/conflict-{token}.git",
        default_branch="release/docs",
    )
    pg_conn.commit()

    proc = _run_cli(
        "doc",
        "binding",
        "switch",
        "--doc-binding-id",
        str(old_binding["id"]),
        "--version-id",
        str(target_version_id),
        "--repo-url",
        f"https://example.invalid/docs/conflict-{token}.git",
        "--branch",
        "release/docs",
        "--json",
    )

    assert proc.returncode == 4
    payload = _payload(proc)
    assert payload["ok"] is False
    assert payload["command"] == "doc binding switch"
    assert payload["errors"][0]["category"] == "name_conflict"
    assert doc_binding_repository.find_by_id(pg_conn, old_binding["id"])["is_active"] is True
    assert doc_binding_repository.find_by_id(pg_conn, other_binding["id"])["is_active"] is True


def test_doc_scan_cli_scans_binding_and_returns_summary(pg_conn):
    token = uuid.uuid4().hex[:8]
    repo_path = _make_doc_repo()
    try:
        product_id = _create_product(pg_conn, f"DOCCLI-{token}")
        product_version_id = _create_version(pg_conn, product_id, f"V-{token}")
        binding = doc_binding_repository.create(
            pg_conn,
            product_id=product_id,
            product_version_id=product_version_id,
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
