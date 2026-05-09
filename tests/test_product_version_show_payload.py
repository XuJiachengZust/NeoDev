from service.cli.commands import product
from service.cli.commands.product import SimpleArgs


def test_version_show_payload_includes_name_query_params_without_graph_fields():
    payload = product._version_show_payload(
        {"id": 2, "name": "NeoDev SP", "code": "NEODEV"},
        {"id": 4, "version_name": "neodev-sp"},
        [{"project_name": "NeoDev", "branch_name": "neodev-sp"}],
    )

    assert payload["query_params"] == [
        {
            "product_name": "NeoDev SP",
            "version_name": "neodev-sp",
            "project_name": "NeoDev",
            "branch_name": "neodev-sp",
        }
    ]
    assert "code_graphs" not in payload
    assert "document_graph" not in payload


def test_query_params_accepts_branch_alias():
    params = product._query_params(
        {"name": "NeoDev SP"},
        {"version_name": "neodev-sp"},
        {"project_name": "NeoDev", "branch": "neodev-sp"},
    )

    assert params["branch_name"] == "neodev-sp"


def test_branch_lookup_can_be_filtered_by_product_name(monkeypatch):
    monkeypatch.setattr(
        product,
        "_resolve_project",
        lambda conn, args: {"id": 7, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        product.product_service,
        "find_products_by_name",
        lambda conn, name: [{"id": 22, "name": name, "code": "TARGET"}],
    )
    monkeypatch.setattr(
        product.product_version_service,
        "list_versions_by_project_branch",
        lambda conn, project_id, branch_name: [
            {
                "id": 11,
                "product_id": 21,
                "product_name": "Other",
                "product_code": "OTHER",
                "version_name": "V1",
                "branch_binding_id": 101,
                "branch_name": branch_name,
            },
            {
                "id": 12,
                "product_id": 22,
                "product_name": "Target",
                "product_code": "TARGET",
                "version_name": "V2",
                "branch_binding_id": 102,
                "branch_name": branch_name,
            },
        ],
    )

    payload = product._show_versions_by_branch(
        object(),
        SimpleArgs(
            project_name="NeoDev",
            branch_name="main",
            product_id=None,
            product_code=None,
            product_name="Target",
        ),
    )

    assert [item["product"]["name"] for item in payload["resolved_versions"]] == ["Target"]
    assert payload["resolved_versions"][0]["query_params"] == {
        "product_name": "Target",
        "version_name": "V2",
        "project_name": "NeoDev",
        "branch_name": "main",
    }


def test_branch_lookup_can_be_filtered_by_product_id(monkeypatch):
    monkeypatch.setattr(
        product,
        "_resolve_project",
        lambda conn, args: {"id": 7, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        product.product_service,
        "get_product",
        lambda conn, product_id: {"id": product_id, "name": "Target", "code": "TARGET"},
    )
    monkeypatch.setattr(
        product.product_version_service,
        "list_versions_by_project_branch",
        lambda conn, project_id, branch_name: [
            {
                "id": 11,
                "product_id": 21,
                "product_name": "Other",
                "product_code": "OTHER",
                "version_name": "V1",
                "branch_binding_id": 101,
                "branch_name": branch_name,
            },
            {
                "id": 12,
                "product_id": 22,
                "product_name": "Target",
                "product_code": "TARGET",
                "version_name": "V2",
                "branch_binding_id": 102,
                "branch_name": branch_name,
            },
        ],
    )

    payload = product._show_versions_by_branch(
        object(),
        SimpleArgs(
            project_name="NeoDev",
            branch_name="main",
            product_id=22,
            product_code=None,
            product_name=None,
        ),
    )

    assert [item["product"]["id"] for item in payload["resolved_versions"]] == [22]
    assert payload["resolved_versions"][0]["query_params"]["product_name"] == "Target"


def test_branch_lookup_can_be_filtered_by_product_code(monkeypatch):
    monkeypatch.setattr(
        product,
        "_resolve_project",
        lambda conn, args: {"id": 7, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        product.product_service,
        "get_product_by_code",
        lambda conn, product_code: {"id": 22, "name": "Target", "code": product_code},
    )
    monkeypatch.setattr(
        product.product_version_service,
        "list_versions_by_project_branch",
        lambda conn, project_id, branch_name: [
            {
                "id": 11,
                "product_id": 21,
                "product_name": "Other",
                "product_code": "OTHER",
                "version_name": "V1",
                "branch_binding_id": 101,
                "branch_name": branch_name,
            },
            {
                "id": 12,
                "product_id": 22,
                "product_name": "Target",
                "product_code": "TARGET",
                "version_name": "V2",
                "branch_binding_id": 102,
                "branch_name": branch_name,
            },
        ],
    )

    payload = product._show_versions_by_branch(
        object(),
        SimpleArgs(
            project_name="NeoDev",
            branch_name="main",
            product_id=None,
            product_code="TARGET",
            product_name=None,
        ),
    )

    assert [item["product"]["code"] for item in payload["resolved_versions"]] == ["TARGET"]
    assert payload["resolved_versions"][0]["query_params"]["product_name"] == "Target"


def test_branch_lookup_rejects_ambiguous_product_name(monkeypatch):
    monkeypatch.setattr(
        product,
        "_resolve_project",
        lambda conn, args: {"id": 7, "name": "NeoDev"},
    )
    monkeypatch.setattr(
        product.product_service,
        "find_products_by_name",
        lambda conn, name: [
            {"id": 21, "name": name, "code": "A"},
            {"id": 22, "name": name, "code": "B"},
        ],
    )

    try:
        product._show_versions_by_branch(
            object(),
            SimpleArgs(
                project_name="NeoDev",
                branch_name="main",
                product_id=None,
                product_code=None,
                product_name="Target",
            ),
        )
    except product.CliError as exc:
        assert exc.category == "ambiguous_name"
        assert exc.details == {"product_name": "Target", "matches": [21, 22]}
    else:
        raise AssertionError("expected ambiguous_name")


def test_branch_lookup_requires_branch_name_when_project_name_is_provided():
    try:
        product._show_versions_by_branch(
            object(),
            SimpleArgs(project_name="NeoDev", branch_name=None),
        )
    except product.CliError as exc:
        assert exc.category == "invalid_argument"
        assert "--project-name and --branch-name" in exc.message
    else:
        raise AssertionError("expected invalid_argument")


def test_version_show_rejects_version_name_with_branch_lookup(monkeypatch):
    monkeypatch.setattr(product, "_with_db", lambda callback: callback(object()))

    try:
        product.handle_version_show(
            SimpleArgs(
                command_name="product version show",
                product_id=None,
                product_code=None,
                product_name=None,
                version_name="V1",
                project_name="NeoDev",
                branch_name="main",
            )
        )
    except product.CliError as exc:
        assert exc.category == "invalid_argument"
        assert "do not combine --version-name" in exc.message
    else:
        raise AssertionError("expected invalid_argument")


def test_name_unique_constraint_maps_to_name_conflict():
    error = Exception("duplicate key value violates unique constraint \"uq_product_versions_product_name\"")

    assert product._integrity_error_category(error) == "name_conflict"


def test_non_name_unique_constraint_remains_conflict():
    error = Exception("duplicate key value violates unique constraint \"products_code_key\"")

    assert product._integrity_error_category(error) == "conflict"
