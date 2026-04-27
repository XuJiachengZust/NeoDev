import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from service.repositories import code_change_link_repository
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


def test_git_verify_doc_change_creates_link_and_updates_status(pg_conn):
    token = uuid.uuid4().hex[:8]
    project_id = _make_project(pg_conn, f"git-verify-project-{token}")
    product_id = _make_product(pg_conn, f"GITVERIFY-{token}")
    binding = doc_binding_repository.create(
        pg_conn,
        product_id=product_id,
        repo_path=f"/tmp/neodev-docs/{token}",
    )
    document = document_repository.create(
        pg_conn,
        doc_binding_id=binding["id"],
        doc_id=f"REQ-GIT-{token}",
        relative_path=f"requirements/git-{token}.md",
    )
    change = doc_change_repository.create(
        pg_conn,
        document_id=document["id"],
        doc_change_id=f"DC-GIT-{token}",
    )
    pg_conn.commit()

    commit_message = f"feat: implement git verification\n\nDocChange-ID: DC-GIT-{token}\n"
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
    assert data["doc_change_id"] == f"DC-GIT-{token}"
    assert data["verification_status"] == "verified"
    assert data["doc_change_status"] == "in_implementation"
    assert data["next_status"] == "in_implementation"

    updated = doc_change_repository.find_by_id(pg_conn, change["id"])
    links = code_change_link_repository.list_by_doc_change(pg_conn, change["id"])
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
