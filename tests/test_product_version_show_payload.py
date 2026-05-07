from service.cli.commands import product


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
