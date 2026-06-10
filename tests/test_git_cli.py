import json
import os
import subprocess
import sys
import urllib.parse
import uuid
from contextlib import closing
from pathlib import Path

import psycopg2
import pytest

from service.repositories import code_change_link_repository
from service.repositories import dangerous_commit_repository
from service.repositories import doc_binding_repository
from service.repositories import doc_change_repository
from service.repositories import document_repository


ROOT = Path(__file__).resolve().parent.parent
INIT_SQL = ROOT / "docker" / "init.sql"


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/neodev",
    )


def _base_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/neodev",
    )


def _scoped_database_url(base_url: str, schema_name: str) -> str:
    options = urllib.parse.quote(f"-c search_path={schema_name},public", safe="")
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}options={options}"


def _connect_fresh():
    return psycopg2.connect(_database_url())


@pytest.fixture(autouse=True)
def git_cli_db_env(monkeypatch):
    base_url = _base_database_url()
    schema_name = f"tmp_git_cli_{uuid.uuid4().hex[:8]}"
    scoped_url = _scoped_database_url(base_url, schema_name)
    admin_conn = psycopg2.connect(base_url)
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
        scoped_conn = psycopg2.connect(scoped_url)
        try:
            with scoped_conn.cursor() as cur:
                cur.execute(INIT_SQL.read_text(encoding="utf-8"))
            scoped_conn.commit()
        finally:
            scoped_conn.close()
        monkeypatch.setenv("TEST_DATABASE_URL", scoped_url)
        yield
    finally:
        with admin_conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
        admin_conn.close()


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NEODEV_CONFIG_DIR"] = str(ROOT / ".test-tmp" / "git-cli-config")
    env.pop("NEODEV_API_URL", None)
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
            (name, f"/tmp/neodev-git-cli/{name}"),
        )
        project_id = cur.fetchone()[0]
    conn.commit()
    return project_id


def _make_product(conn, code: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO products (name, code)
            VALUES (%s, %s)
            RETURNING id
            """,
            (f"Git Product {code}", code),
        )
        product_id = cur.fetchone()[0]
    conn.commit()
    return product_id


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


def _make_bound_doc_change(conn, token: str, doc_commit: str, *, status: str = "pending_implementation") -> dict:
    product_id = _make_product(conn, f"GITDOC-{token}")
    product_version_id = _make_version(conn, product_id, f"V-{token}")
    binding = doc_binding_repository.create(
        conn,
        product_id=product_id,
        product_version_id=product_version_id,
        repo_path=f"/tmp/neodev-docs/{token}",
    )
    document = document_repository.create(
        conn,
        doc_binding_id=binding["id"],
        product_version_id=product_version_id,
        doc_id=f"REQ-GIT-{token}",
        relative_path=f"requirements/git-{token}.md",
    )
    change = doc_change_repository.create(
        conn,
        document_id=document["id"],
        doc_change_id=doc_commit,
        source_commit=doc_commit,
        status=status,
    )
    conn.commit()
    return change


def _assert_single_dangerous_record(project_id: int, *, commit_sha: str, reason: str) -> dict:
    list_proc = _run_cli(
        "git",
        "dangerous-commit",
        "list",
        "--project-id",
        str(project_id),
        "--json",
    )
    assert list_proc.returncode == 0, list_proc.stderr
    list_payload = _payload(list_proc)
    assert list_payload["data"]["count"] == 1
    row = list_payload["data"]["dangerous_commits"][0]
    assert row["commit_sha"] == commit_sha
    assert row["reason"] == reason
    return row


def test_git_verify_doc_change_creates_link_and_updates_status():
    token = uuid.uuid4().hex[:8]
    doc_commit = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"[:40]
    commit_sha = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"[:40]
    with closing(_connect_fresh()) as conn:
        project_id = _make_project(conn, f"git-verify-project-{token}")
        product_id = _make_product(conn, f"GITVERIFY-{token}")
        product_version_id = _make_version(conn, product_id, f"V-{token}")
        binding = doc_binding_repository.create(
            conn,
            product_id=product_id,
            product_version_id=product_version_id,
            repo_path=f"/tmp/neodev-docs/{token}",
        )
        document = document_repository.create(
            conn,
            doc_binding_id=binding["id"],
            product_version_id=product_version_id,
            doc_id=f"REQ-GIT-{token}",
            relative_path=f"requirements/git-{token}.md",
        )
        change = doc_change_repository.create(
            conn,
            document_id=document["id"],
            doc_change_id=doc_commit,
            source_commit=doc_commit,
        )
        conn.commit()

    commit_message = f"feat: implement git verification\n\nDocChange-ID: {doc_commit}\n"
    proc = _run_cli(
        "git",
        "verify-doc-change",
        "--project-id",
        str(project_id),
        "--branch",
        "main",
        "--commit-sha",
        commit_sha,
        "--commit-message",
        commit_message,
        "--json",
    )

    assert proc.returncode == 0, proc.stderr
    payload = _payload(proc)
    assert payload["ok"] is True
    assert payload["command"] == "git verify-doc-change"
    data = payload["data"]
    assert data["doc_change_id"] == doc_commit
    assert data["verification_status"] == "verified"
    assert data["doc_change_status"] == "in_implementation"
    assert data["next_status"] == "in_implementation"

    with closing(_connect_fresh()) as conn:
        updated = doc_change_repository.find_by_id(conn, change["id"])
        links = code_change_link_repository.list_by_doc_change(conn, change["id"])
    assert updated["status"] == "in_implementation"
    assert len(links) == 1
    assert links[0]["project_id"] == project_id
    assert links[0]["branch"] == "main"
    assert links[0]["commit_sha"] == commit_sha


def test_git_verify_doc_change_rejects_missing_trailer():
    token = uuid.uuid4().hex[:8]
    with closing(_connect_fresh()) as conn:
        project_id = _make_project(conn, f"git-dangerous-missing-{token}")

    proc = _run_cli(
        "git",
        "verify-doc-change",
        "--project-id",
        str(project_id),
        "--branch",
        "main",
        "--commit-sha",
        "b" * 40,
        "--commit-message",
        "feat: no doc change",
        "--json",
    )

    assert proc.returncode == 2
    payload = _payload(proc)
    assert payload["ok"] is False
    assert payload["command"] == "git verify-doc-change"
    assert payload["errors"][0]["category"] == "invalid_argument"
    assert payload["errors"][0]["details"]["dangerous_commit"]["project_id"] == project_id

    _assert_single_dangerous_record(
        project_id,
        commit_sha="b" * 40,
        reason="DocChange-ID trailer is required",
    )


def test_git_verify_doc_change_rejects_unknown_doc_change_and_records_dangerous():
    token = uuid.uuid4().hex[:8]
    doc_commit = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"[:40]
    commit_sha = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"[:40]
    with closing(_connect_fresh()) as conn:
        project_id = _make_project(conn, f"git-dangerous-unknown-{token}")

    proc = _run_cli(
        "git",
        "verify-doc-change",
        "--project-id",
        str(project_id),
        "--branch",
        "main",
        "--commit-sha",
        commit_sha,
        "--commit-message",
        f"feat: unknown doc change\n\nDocChange-ID: {doc_commit}\n",
        "--json",
    )

    assert proc.returncode == 3
    payload = _payload(proc)
    assert payload["errors"][0]["category"] == "not_found"
    assert payload["errors"][0]["details"]["dangerous_commit_required"] is True
    _assert_single_dangerous_record(
        project_id,
        commit_sha=commit_sha,
        reason="doc change not found",
    )


def test_git_verify_doc_change_rejects_implemented_doc_change_and_records_dangerous():
    token = uuid.uuid4().hex[:8]
    doc_commit = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"[:40]
    commit_sha = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"[:40]
    with closing(_connect_fresh()) as conn:
        project_id = _make_project(conn, f"git-dangerous-implemented-{token}")
        _make_bound_doc_change(conn, token, doc_commit, status="implemented")

    proc = _run_cli(
        "git",
        "verify-doc-change",
        "--project-id",
        str(project_id),
        "--branch",
        "main",
        "--commit-sha",
        commit_sha,
        "--commit-message",
        f"feat: already implemented\n\nDocChange-ID: {doc_commit}\n",
        "--json",
    )

    assert proc.returncode == 4
    payload = _payload(proc)
    assert payload["errors"][0]["category"] == "conflict"
    assert payload["errors"][0]["details"]["dangerous_commit_required"] is True
    _assert_single_dangerous_record(
        project_id,
        commit_sha=commit_sha,
        reason="doc change is already implemented",
    )


def test_git_verify_doc_change_records_dangerous_commit_idempotently():
    token = uuid.uuid4().hex[:8]
    commit_sha = f"{uuid.uuid4().hex}{uuid.uuid4().hex}"[:40]
    with closing(_connect_fresh()) as conn:
        project_id = _make_project(conn, f"git-dangerous-idempotent-{token}")

    for _ in range(2):
        proc = _run_cli(
            "git",
            "verify-doc-change",
            "--project-id",
            str(project_id),
            "--branch",
            "main",
            "--commit-sha",
            commit_sha,
            "--commit-message",
            "feat: missing docchange",
            "--json",
        )

        assert proc.returncode == 2, proc.stderr
        payload = _payload(proc)
        assert payload["ok"] is False
        assert payload["errors"][0]["details"]["dangerous_commit_required"] is True

    _assert_single_dangerous_record(
        project_id,
        commit_sha=commit_sha,
        reason="DocChange-ID trailer is required",
    )


def test_git_dangerous_commit_list_and_resolve():
    token = uuid.uuid4().hex[:8]
    with closing(_connect_fresh()) as conn:
        project_id = _make_project(conn, f"dangerous-project-{token}")
        created = dangerous_commit_repository.create(
            conn,
            project_id=project_id,
            branch="main",
            commit_sha="c" * 40,
            risk_level="high",
            reason="manual override without doc change",
        )
        conn.commit()

    list_proc = _run_cli(
        "git",
        "dangerous-commit",
        "list",
        "--project-id",
        str(project_id),
        "--json",
    )
    assert list_proc.returncode == 0, list_proc.stderr
    list_payload = _payload(list_proc)
    assert list_payload["ok"] is True
    assert list_payload["command"] == "git dangerous-commit list"
    assert list_payload["data"]["count"] == 1
    assert list_payload["data"]["dangerous_commits"][0]["id"] == created["id"]

    resolve_proc = _run_cli(
        "git",
        "dangerous-commit",
        "resolve",
        "--record-id",
        str(created["id"]),
        "--resolved-by",
        "release-manager",
        "--json",
    )
    assert resolve_proc.returncode == 0, resolve_proc.stderr
    resolve_payload = _payload(resolve_proc)
    assert resolve_payload["ok"] is True
    assert resolve_payload["command"] == "git dangerous-commit resolve"
    resolved = resolve_payload["data"]["dangerous_commit"]
    assert resolved["status"] == "resolved"
    assert resolved["resolved_by"] == "release-manager"
    assert resolved["resolved_at"] is not None

    with closing(_connect_fresh()) as conn:
        after = dangerous_commit_repository.find_by_id(conn, created["id"])
    assert after["status"] == "resolved"
    assert after["resolved_by"] == "release-manager"


def test_git_dangerous_commit_resolve_rejects_unknown_record():
    proc = _run_cli(
        "git",
        "dangerous-commit",
        "resolve",
        "--record-id",
        "999999999",
        "--resolved-by",
        "release-manager",
        "--json",
    )

    assert proc.returncode == 3
    payload = _payload(proc)
    assert payload["ok"] is False
    assert payload["command"] == "git dangerous-commit resolve"
    assert payload["errors"][0]["category"] == "not_found"


def test_git_post_push_refresh_is_removed():
    proc = _run_cli("git", "post-push-refresh", "--help")

    assert proc.returncode != 0
    assert "invalid choice" in proc.stdout
