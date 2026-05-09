import json
import os
import subprocess
import sys
import uuid
from contextlib import closing
from pathlib import Path

import psycopg2

from service.repositories import code_change_link_repository
from service.repositories import dangerous_commit_repository
from service.repositories import doc_binding_repository
from service.repositories import doc_change_repository
from service.repositories import document_repository


ROOT = Path(__file__).resolve().parent.parent


def _database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL") or os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/neodev",
    )


def _connect_fresh():
    return psycopg2.connect(_database_url())


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


def test_git_verify_doc_change_creates_link_and_updates_status(pg_conn):
    token = uuid.uuid4().hex[:8]
    doc_commit = "d" * 40
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
    commit_sha = "a" * 40
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


def test_git_verify_doc_change_rejects_missing_trailer(pg_conn):
    proc = _run_cli(
        "git",
        "verify-doc-change",
        "--project-id",
        "1",
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


def test_git_dangerous_commit_list_and_resolve(pg_conn):
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


def test_git_dangerous_commit_resolve_rejects_unknown_record(pg_conn):
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


def test_git_post_push_refresh_is_removed(pg_conn):
    proc = _run_cli("git", "post-push-refresh", "--help")

    assert proc.returncode != 0
    assert "invalid choice" in proc.stderr
