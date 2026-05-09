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
            (name, f"/tmp/neodev-cli/{name}"),
        )
        project_id = cur.fetchone()[0]
    conn.commit()
    return project_id


def test_product_cli_create_and_show_support_product_code(pg_conn):
    token = uuid.uuid4().hex[:8]
    code = f"CLI-{token}"

    create_proc = _run_cli(
        "product",
        "create",
        "--name",
        f"CLI Product {token}",
        "--product-code",
        code,
        "--owner",
        "codex",
        "--json",
    )
    assert create_proc.returncode == 0, create_proc.stderr
    created = _payload(create_proc)
    assert created["ok"] is True
    assert created["command"] == "product create"
    assert created["data"]["product"]["code"] == code

    show_proc = _run_cli("product", "show", "--product-code", code, "--json")
    assert show_proc.returncode == 0, show_proc.stderr
    shown = _payload(show_proc)
    assert shown["ok"] is True
    assert shown["data"]["product"]["id"] == created["data"]["product"]["id"]
    assert shown["data"]["product"]["code"] == code


def test_product_cli_show_and_version_bind_support_numeric_ids(pg_conn):
    token = uuid.uuid4().hex[:8]
    project_id = _make_project(pg_conn, f"cli-id-project-{token}")

    create_product = _run_cli(
        "product",
        "create",
        "--name",
        f"CLI ID Product {token}",
        "--product-code",
        f"CLIID-{token}",
        "--json",
    )
    assert create_product.returncode == 0, create_product.stderr
    product_id = _payload(create_product)["data"]["product"]["id"]

    show_product = _run_cli("product", "show", "--product-id", str(product_id), "--json")
    assert show_product.returncode == 0, show_product.stderr
    assert _payload(show_product)["data"]["product"]["id"] == product_id

    create_version = _run_cli(
        "product",
        "version",
        "create",
        "--product-id",
        str(product_id),
        "--version-name",
        "V2.0",
        "--json",
    )
    assert create_version.returncode == 0, create_version.stderr
    version_id = _payload(create_version)["data"]["version"]["id"]

    bind_proc = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--version-id",
        str(version_id),
        "--project-id",
        str(project_id),
        "--branch",
        "release/V2.0",
        "--json",
    )
    assert bind_proc.returncode == 0, bind_proc.stderr
    bind_data = _payload(bind_proc)["data"]
    binding = bind_data["binding"]
    assert binding["product_version_id"] == version_id
    assert binding["project_id"] == project_id
    assert binding["branch"] == "release/V2.0"
    assert bind_data["mutation_action"] == "bind"
    assert bind_data["mutation_target"] == "branch"
    assert bind_data["mutation_status"] in {"ready", "missing"}

    unbind_proc = _run_cli(
        "product",
        "version",
        "unbind-branch",
        "--version-id",
        str(version_id),
        "--project-id",
        str(project_id),
        "--json",
    )
    assert unbind_proc.returncode == 0, unbind_proc.stderr
    unbound = _payload(unbind_proc)["data"]
    assert unbound["binding_removed"] is True
    assert unbound["binding"]["branch"] == "release/V2.0"
    assert unbound["mutation_action"] == "unbind"
    assert unbound["mutation_target"] == "branch"
    assert unbound["mutation_status"] == "removed"


def test_product_version_cli_supports_business_keys_for_create_show_and_bind(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"CLIV-{token}"
    project_name = f"cli-project-{token}"
    _make_project(pg_conn, project_name)

    create_product = _run_cli(
        "product",
        "create",
        "--name",
        f"CLI Version Product {token}",
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
        "--status",
        "planning",
        "--json",
    )
    assert create_version.returncode == 0, create_version.stderr
    version_payload = _payload(create_version)
    version_id = version_payload["data"]["version"]["id"]

    bind_proc = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--product-code",
        product_code,
        "--version-name",
        "V1.0",
        "--project-name",
        project_name,
        "--branch",
        "release/V1.0",
        "--json",
    )
    assert bind_proc.returncode == 0, bind_proc.stderr
    binding = _payload(bind_proc)
    assert binding["ok"] is True
    assert binding["command"] == "product version bind-branch"
    assert binding["data"]["binding"]["product_version_id"] == version_id
    assert binding["data"]["binding"]["branch"] == "release/V1.0"
    assert binding["data"]["mutation_action"] == "bind"
    assert binding["data"]["mutation_target"] == "branch"
    assert binding["data"]["mutation_status"] in {"ready", "missing"}

    show_proc = _run_cli(
        "product",
        "version",
        "show",
        "--product-code",
        product_code,
        "--version-name",
        "V1.0",
        "--json",
    )
    assert show_proc.returncode == 0, show_proc.stderr
    shown = _payload(show_proc)
    assert shown["data"]["version"]["id"] == version_id
    assert shown["data"]["branches"][0]["project_name"] == project_name
    assert shown["data"]["branches"][0]["branch"] == "release/V1.0"

    project_show = _run_cli("project", "show", "--project-name", project_name, "--json")
    assert project_show.returncode == 0, project_show.stderr
    project_versions = _payload(project_show)["data"]["versions"]
    project_version = next(row for row in project_versions if row["branch"] == "release/V1.0")
    assert project_version["id"]
    assert project_version["version_name"] == "V1.0"


def test_product_cli_missing_business_key_returns_not_found(pg_conn):
    proc = _run_cli("product", "show", "--product-code", f"NOPE-{uuid.uuid4().hex}", "--json")
    assert proc.returncode == 3
    payload = _payload(proc)
    assert payload["ok"] is False
    assert payload["errors"][0]["category"] == "not_found"


def test_product_cli_duplicate_product_code_returns_conflict(pg_conn):
    code = f"DUP-{uuid.uuid4().hex[:8]}"
    first = _run_cli("product", "create", "--name", "Duplicate A", "--product-code", code, "--json")
    assert first.returncode == 0, first.stderr

    second = _run_cli("product", "create", "--name", "Duplicate B", "--product-code", code, "--json")
    assert second.returncode == 4
    payload = _payload(second)
    assert payload["ok"] is False
    assert payload["errors"][0]["category"] == "conflict"


def test_product_cli_update_supports_business_key_and_new_code(pg_conn):
    token = uuid.uuid4().hex[:8]
    old_code = f"UPD-{token}"
    new_code = f"UPD2-{token}"
    create_proc = _run_cli(
        "product",
        "create",
        "--name",
        "Update Product",
        "--product-code",
        old_code,
        "--owner",
        "before",
        "--json",
    )
    assert create_proc.returncode == 0, create_proc.stderr

    update_proc = _run_cli(
        "product",
        "update",
        "--product-code",
        old_code,
        "--new-product-code",
        new_code,
        "--name",
        "Updated Product",
        "--owner",
        "after",
        "--status",
        "archived",
        "--json",
    )
    assert update_proc.returncode == 0, update_proc.stderr
    updated = _payload(update_proc)["data"]["product"]
    assert updated["code"] == new_code
    assert updated["name"] == "Updated Product"
    assert updated["owner"] == "after"
    assert updated["status"] == "archived"

    show_proc = _run_cli("product", "show", "--product-code", new_code, "--json")
    assert show_proc.returncode == 0, show_proc.stderr
    assert _payload(show_proc)["data"]["product"]["code"] == new_code


def test_product_cli_rejects_multiple_product_locators(pg_conn):
    token = uuid.uuid4().hex[:8]
    create_proc = _run_cli(
        "product",
        "create",
        "--name",
        "Locator Product",
        "--product-code",
        f"LOC-{token}",
        "--json",
    )
    assert create_proc.returncode == 0, create_proc.stderr
    product = _payload(create_proc)["data"]["product"]

    proc = _run_cli(
        "product",
        "show",
        "--product-id",
        str(product["id"]),
        "--product-code",
        product["code"],
        "--json",
    )
    assert proc.returncode == 2
    payload = _payload(proc)
    assert payload["ok"] is False
    assert payload["errors"][0]["category"] == "invalid_argument"


def test_product_version_show_rejects_version_id(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"VID-{token}"
    create_product = _run_cli(
        "product",
        "create",
        "--name",
        "Version ID Product",
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
        "V-ID",
        "--json",
    )
    assert create_version.returncode == 0, create_version.stderr
    version_id = _payload(create_version)["data"]["version"]["id"]

    show_proc = _run_cli("product", "version", "show", "--version-id", str(version_id), "--json")
    assert show_proc.returncode == 2
    payload = _payload(show_proc)
    assert payload["ok"] is False
    assert payload["errors"][0]["category"] == "invalid_argument"
    assert "--version-id" in payload["errors"][0]["message"]


def test_product_version_bind_branch_rejects_ambiguous_project_name(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"AMB-{token}"
    project_name = f"same-project-{token}"
    _make_project(pg_conn, project_name)
    _make_project(pg_conn, project_name)

    create_product = _run_cli(
        "product",
        "create",
        "--name",
        "Ambiguous Project Product",
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
        "V-AMB",
        "--json",
    )
    assert create_version.returncode == 0, create_version.stderr

    proc = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--product-code",
        product_code,
        "--version-name",
        "V-AMB",
        "--project-name",
        project_name,
        "--branch",
        "main",
        "--json",
    )
    assert proc.returncode == 4
    payload = _payload(proc)
    assert payload["errors"][0]["category"] == "ambiguous_name"
    assert payload["errors"][0]["details"]["project_name"] == project_name


def test_product_version_bind_branch_rejects_project_bound_to_other_product(pg_conn):
    token = uuid.uuid4().hex[:8]
    project_id = _make_project(pg_conn, f"cross-product-project-{token}")

    first_product = _run_cli(
        "product",
        "create",
        "--name",
        "First Product",
        "--product-code",
        f"CROSSA-{token}",
        "--json",
    )
    assert first_product.returncode == 0, first_product.stderr
    second_product = _run_cli(
        "product",
        "create",
        "--name",
        "Second Product",
        "--product-code",
        f"CROSSB-{token}",
        "--json",
    )
    assert second_product.returncode == 0, second_product.stderr

    first_version = _run_cli(
        "product",
        "version",
        "create",
        "--product-code",
        f"CROSSA-{token}",
        "--version-name",
        "V1",
        "--json",
    )
    assert first_version.returncode == 0, first_version.stderr
    second_version = _run_cli(
        "product",
        "version",
        "create",
        "--product-code",
        f"CROSSB-{token}",
        "--version-name",
        "V1",
        "--json",
    )
    assert second_version.returncode == 0, second_version.stderr

    first_bind = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--product-code",
        f"CROSSA-{token}",
        "--version-name",
        "V1",
        "--project-id",
        str(project_id),
        "--branch",
        "main",
        "--json",
    )
    assert first_bind.returncode == 0, first_bind.stderr

    second_bind = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--product-code",
        f"CROSSB-{token}",
        "--version-name",
        "V1",
        "--project-id",
        str(project_id),
        "--branch",
        "main",
        "--json",
    )
    assert second_bind.returncode == 4
    payload = _payload(second_bind)
    assert payload["errors"][0]["category"] == "conflict"


def test_product_version_create_duplicate_name_returns_name_conflict(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"VDUP-{token}"
    product = _run_cli(
        "product",
        "create",
        "--name",
        "Duplicate Version Product",
        "--product-code",
        product_code,
        "--json",
    )
    assert product.returncode == 0, product.stderr

    first = _run_cli(
        "product",
        "version",
        "create",
        "--product-code",
        product_code,
        "--version-name",
        "Same",
        "--json",
    )
    assert first.returncode == 0, first.stderr

    second = _run_cli(
        "product",
        "version",
        "create",
        "--product-code",
        product_code,
        "--version-name",
        "Same",
        "--json",
    )
    assert second.returncode == 4
    assert _payload(second)["errors"][0]["category"] == "name_conflict"


def test_product_version_show_branch_lookup_supports_product_filter(pg_conn):
    token = uuid.uuid4().hex[:8]
    project_name = f"branch-lookup-{token}"
    _make_project(pg_conn, project_name)

    alpha_code = f"BLA-{token}"
    beta_code = f"BLB-{token}"
    for name, code in (("Alpha Product", alpha_code), ("Beta Product", beta_code)):
        create_product = _run_cli(
            "product",
            "create",
            "--name",
            f"{name} {token}",
            "--product-code",
            code,
            "--json",
        )
        assert create_product.returncode == 0, create_product.stderr
        create_version = _run_cli(
            "product",
            "version",
            "create",
            "--product-code",
            code,
            "--version-name",
            "V1",
            "--json",
        )
        assert create_version.returncode == 0, create_version.stderr
        bind_proc = _run_cli(
            "product",
            "version",
            "bind-branch",
            "--product-code",
            code,
            "--version-name",
            "V1",
            "--project-name",
            project_name,
            "--branch",
            "main",
            "--json",
        )
        assert bind_proc.returncode == 0, bind_proc.stderr

    show_proc = _run_cli(
        "product",
        "version",
        "show",
        "--project-name",
        project_name,
        "--branch-name",
        "main",
        "--product-code",
        beta_code,
        "--json",
    )
    assert show_proc.returncode == 0, show_proc.stderr
    payload = _payload(show_proc)
    resolved_versions = payload["data"]["resolved_versions"]
    assert len(resolved_versions) == 1
    assert resolved_versions[0]["product"]["code"] == beta_code
    assert resolved_versions[0]["query_params"] == {
        "product_name": f"Beta Product {token}",
        "version_name": "V1",
        "project_name": project_name,
        "branch_name": "main",
    }


def test_product_version_show_branch_lookup_returns_all_matching_versions(pg_conn):
    token = uuid.uuid4().hex[:8]
    project_name = f"branch-multi-lookup-{token}"
    _make_project(pg_conn, project_name)

    expected_products = []
    for prefix in ("Alpha Multi", "Beta Multi"):
        code = f"BML-{prefix[0]}-{token}"
        create_product = _run_cli(
            "product",
            "create",
            "--name",
            f"{prefix} {token}",
            "--product-code",
            code,
            "--json",
        )
        assert create_product.returncode == 0, create_product.stderr
        create_version = _run_cli(
            "product",
            "version",
            "create",
            "--product-code",
            code,
            "--version-name",
            "V1",
            "--json",
        )
        assert create_version.returncode == 0, create_version.stderr
        bind_proc = _run_cli(
            "product",
            "version",
            "bind-branch",
            "--product-code",
            code,
            "--version-name",
            "V1",
            "--project-name",
            project_name,
            "--branch",
            "main",
            "--json",
        )
        assert bind_proc.returncode == 0, bind_proc.stderr
        expected_products.append(f"{prefix} {token}")

    show_proc = _run_cli(
        "product",
        "version",
        "show",
        "--project-name",
        project_name,
        "--branch-name",
        "main",
        "--json",
    )
    assert show_proc.returncode == 0, show_proc.stderr
    payload = _payload(show_proc)
    resolved_versions = payload["data"]["resolved_versions"]
    assert [item["product"]["name"] for item in resolved_versions] == expected_products
    assert [item["query_params"]["branch_name"] for item in resolved_versions] == ["main", "main"]


def test_product_version_show_branch_lookup_returns_empty_result_for_unbound_branch(pg_conn):
    token = uuid.uuid4().hex[:8]
    project_name = f"branch-empty-lookup-{token}"
    _make_project(pg_conn, project_name)

    show_proc = _run_cli(
        "product",
        "version",
        "show",
        "--project-name",
        project_name,
        "--branch-name",
        "missing",
        "--json",
    )
    assert show_proc.returncode == 0, show_proc.stderr
    payload = _payload(show_proc)
    assert payload["ok"] is True
    assert payload["data"]["resolved_versions"] == []


def test_product_version_show_branch_lookup_rejects_ambiguous_product_name(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_name = f"shared-product-{token}"
    for code in (f"AMBPA-{token}", f"AMBPB-{token}"):
        create_product = _run_cli(
            "product",
            "create",
            "--name",
            product_name,
            "--product-code",
            code,
            "--json",
        )
        assert create_product.returncode == 0, create_product.stderr

    project_name = f"lookup-project-{token}"
    _make_project(pg_conn, project_name)

    proc = _run_cli(
        "product",
        "version",
        "show",
        "--project-name",
        project_name,
        "--branch-name",
        "main",
        "--product-name",
        product_name,
        "--json",
    )
    assert proc.returncode == 4
    payload = _payload(proc)
    assert payload["errors"][0]["category"] == "ambiguous_name"
    assert payload["errors"][0]["details"]["product_name"] == product_name


def test_product_version_name_locator_requires_product_locator(pg_conn):
    proc = _run_cli(
        "product",
        "version",
        "show",
        "--version-name",
        "missing-product-scope",
        "--json",
    )
    assert proc.returncode == 2
    payload = _payload(proc)
    assert payload["errors"][0]["category"] == "invalid_argument"
    assert "product" in payload["errors"][0]["message"]


def test_product_version_bind_branch_missing_project_returns_not_found(pg_conn):
    token = uuid.uuid4().hex[:8]
    product_code = f"MPROJ-{token}"
    product = _run_cli(
        "product",
        "create",
        "--name",
        "Missing Project Product",
        "--product-code",
        product_code,
        "--json",
    )
    assert product.returncode == 0, product.stderr
    version = _run_cli(
        "product",
        "version",
        "create",
        "--product-code",
        product_code,
        "--version-name",
        "V1",
        "--json",
    )
    assert version.returncode == 0, version.stderr

    proc = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--product-code",
        product_code,
        "--version-name",
        "V1",
        "--project-name",
        f"missing-{token}",
        "--branch",
        "main",
        "--json",
    )
    assert proc.returncode == 3
    assert _payload(proc)["errors"][0]["category"] == "not_found"


def test_product_version_bind_branch_updates_existing_mapping(pg_conn):
    token = uuid.uuid4().hex[:8]
    project_id = _make_project(pg_conn, f"update-branch-project-{token}")
    product_code = f"BRUP-{token}"
    product = _run_cli(
        "product",
        "create",
        "--name",
        "Branch Update Product",
        "--product-code",
        product_code,
        "--json",
    )
    assert product.returncode == 0, product.stderr
    version = _run_cli(
        "product",
        "version",
        "create",
        "--product-code",
        product_code,
        "--version-name",
        "V1",
        "--json",
    )
    assert version.returncode == 0, version.stderr

    first = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--product-code",
        product_code,
        "--version-name",
        "V1",
        "--project-id",
        str(project_id),
        "--branch",
        "main",
        "--json",
    )
    assert first.returncode == 0, first.stderr
    second = _run_cli(
        "product",
        "version",
        "bind-branch",
        "--product-code",
        product_code,
        "--version-name",
        "V1",
        "--project-id",
        str(project_id),
        "--branch",
        "release/V1",
        "--json",
    )
    assert second.returncode == 0, second.stderr
    assert _payload(second)["data"]["binding"]["branch"] == "release/V1"
