import json
import os
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from service.cli.errors import CliError, error_to_exit_code
from service.cli.output import build_error_payload, build_success_payload, render_payload

ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NEODEV_CONFIG_DIR"] = str(ROOT / ".test-tmp" / "cli-contract-config")
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_build_success_payload_contains_required_fields():
    payload = build_success_payload(
        command="cli version-check",
        data={"cli_version": "dev"},
    )
    assert payload["ok"] is True
    assert payload["command"] == "cli version-check"
    assert "timestamp" in payload
    assert payload["data"]["cli_version"] == "dev"
    assert payload["errors"] == []


def test_build_error_payload_contains_error_category():
    err = CliError(
        category="invalid_argument",
        message="missing --json",
        details={"arg": "--json"},
    )
    payload = build_error_payload(command="cli version-check", error=err)
    assert payload["ok"] is False
    assert payload["command"] == "cli version-check"
    assert payload["data"] is None
    assert payload["errors"] == [
        {
            "category": "invalid_argument",
            "message": "missing --json",
            "details": {"arg": "--json"},
        }
    ]


def test_error_to_exit_code_is_stable():
    assert error_to_exit_code(CliError("invalid_argument", "bad")) == 2
    assert error_to_exit_code(CliError("invalid_scope", "out of scope")) == 2
    assert error_to_exit_code(CliError("not_found", "missing")) == 3
    assert error_to_exit_code(CliError("conflict", "busy")) == 4
    assert error_to_exit_code(CliError("not_ready", "later")) == 5
    assert error_to_exit_code(CliError("version_mismatch", "mismatch")) == 6
    assert error_to_exit_code(CliError("internal_error", "boom")) == 10


def test_cli_error_exception_semantics_are_stable():
    err = CliError(category="invalid_argument", message="missing --json")
    assert str(err) == "missing --json"
    assert err.args == ("missing --json",)


def test_build_error_payload_defaults_details_to_empty_dict():
    err = CliError(category="invalid_argument", message="missing --json")
    payload = build_error_payload(command="cli version-check", error=err)
    assert payload["errors"][0]["details"] == {}


def test_build_success_payload_defaults_data_to_empty_dict():
    payload = build_success_payload(command="cli version-check")
    assert payload["data"] == {}


def test_error_to_exit_code_defaults_unknown_category_to_10():
    assert error_to_exit_code(CliError("unexpected", "boom")) == 10


def test_build_success_payload_does_not_alias_input_data():
    source = {"cli_version": "dev"}
    payload = build_success_payload(command="cli version-check", data=source)
    source["cli_version"] = "changed"
    assert payload["data"]["cli_version"] == "dev"


def test_build_error_payload_does_not_alias_error_details():
    details = {"arg": "--json"}
    err = CliError(category="invalid_argument", message="missing --json", details=details)
    payload = build_error_payload(command="cli version-check", error=err)
    details["arg"] = "--xml"
    assert payload["errors"][0]["details"]["arg"] == "--json"


def test_build_success_payload_does_not_alias_nested_input_data():
    source = {"meta": {"cli_version": "dev"}}
    payload = build_success_payload(command="cli version-check", data=source)
    source["meta"]["cli_version"] = "changed"
    assert payload["data"]["meta"]["cli_version"] == "dev"


def test_build_error_payload_does_not_alias_nested_error_details():
    details = {"meta": {"arg": "--json"}}
    err = CliError(category="invalid_argument", message="missing --json", details=details)
    payload = build_error_payload(command="cli version-check", error=err)
    details["meta"]["arg"] = "--xml"
    assert payload["errors"][0]["details"]["meta"]["arg"] == "--json"


def test_build_error_payload_converts_datetime_details_to_json_ready_strings():
    err = CliError(
        category="conflict",
        message="dangerous commit",
        details={"created_at": datetime(2026, 5, 11, 7, 30, 0)},
    )

    payload = build_error_payload(command="git verify-doc-change", error=err)

    assert payload["errors"][0]["details"]["created_at"] == "2026-05-11T07:30:00"
    json.dumps(payload)


def test_cli_error_copies_details_at_construction_time():
    source = {"meta": {"arg": "--json"}}
    err = CliError(category="invalid_argument", message="missing --json", details=source)
    source["meta"]["arg"] = "--xml"
    payload = build_error_payload(command="cli version-check", error=err)
    assert payload["errors"][0]["details"]["meta"]["arg"] == "--json"


def test_root_entrypoint_returns_version_check_json():
    proc = _run("neodev.py", "cli", "version-check", "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert {"ok", "command", "timestamp", "data", "errors"}.issubset(payload)
    assert payload["ok"] is True
    assert payload["command"] == "cli version-check"
    assert isinstance(payload["timestamp"], str)
    assert isinstance(payload["data"], dict)
    assert payload["data"]["cli_version"]
    assert payload["data"]["plugin_version"] == "0.2.0"
    assert payload["data"]["skill_version"] == "0.2.0"
    assert payload["data"]["compatible"] is True
    assert payload["data"]["update_available"] is False
    assert payload["data"]["target_version"]
    assert isinstance(payload["data"]["message"], str)
    assert payload["data"]["message"]
    assert payload["errors"] == []


def test_version_check_does_not_require_plugin_or_skill_versions(monkeypatch):
    from service.cli.commands import cli as cli_command

    monkeypatch.setattr(cli_command, "PLUGIN_MANIFEST", ROOT / ".test-tmp" / "missing-plugin.json")
    monkeypatch.setattr(cli_command, "WORKFLOW_CONTRACT", ROOT / ".test-tmp" / "missing-skill.json")

    payload = cli_command.handle_version_check(
        SimpleNamespace(command_name="cli version-check")
    )

    assert payload["data"]["plugin_version"] is None
    assert payload["data"]["skill_version"] is None
    assert payload["data"]["compatible"] is True
    assert payload["data"]["target_version"] == "dev"


def test_root_entrypoint_defaults_to_plain_text_output():
    proc = _run("neodev.py", "cli", "version-check")
    assert proc.returncode == 0
    assert not proc.stdout.lstrip().startswith("{")
    assert "command: cli version-check" in proc.stdout
    assert "compatible: true" in proc.stdout


def test_render_payload_prints_plain_error_without_json():
    payload = build_error_payload(
        command="unknown",
        error=CliError(category="invalid_argument", message="bad command"),
    )
    text = render_payload(payload)
    assert text == "ERROR [invalid_argument]: bad command\n"


def test_module_entrypoint_matches_root_entrypoint_shape():
    root_proc = _run("neodev.py", "cli", "version-check", "--json")
    mod_proc = _run("-m", "service.cli.main", "cli", "version-check", "--json")
    root_payload = json.loads(root_proc.stdout)
    mod_payload = json.loads(mod_proc.stdout)
    assert root_proc.returncode == 0
    assert mod_proc.returncode == 0
    assert root_payload["command"] == mod_payload["command"] == "cli version-check"
    assert root_payload["data"]["compatible"] == mod_payload["data"]["compatible"] is True


def test_invalid_top_level_command_returns_structured_json_error():
    proc = _run("neodev.py", "bad")
    assert proc.returncode != 0
    assert not proc.stdout.lstrip().startswith("{")
    assert "ERROR [invalid_argument]" in proc.stdout


def test_missing_cli_subcommand_returns_structured_json_error():
    proc = _run("neodev.py", "cli")
    assert proc.returncode != 0
    assert not proc.stdout.lstrip().startswith("{")
    assert "ERROR [invalid_argument]" in proc.stdout


def test_product_version_analysis_commands_are_hidden_from_standard_help():
    proc = _run("neodev.py", "product", "version", "--help")
    assert proc.returncode == 0
    assert "analyze" not in proc.stdout
    assert "analyze-status" not in proc.stdout
    assert "watch-status" not in proc.stdout


def test_primary_workflow_commands_are_registered():
    cases = [
        ("doctor",),
        ("context", "show"),
        ("setup", "repo"),
        ("docs", "sync"),
        ("change", "start"),
        ("change", "impact"),
        ("git", "check"),
        ("status",),
    ]

    for args in cases:
        proc = _run("neodev.py", *args, "--help")
        assert proc.returncode == 0, (args, proc.stdout, proc.stderr)


def test_default_help_shows_primary_path_and_hides_advanced_commands():
    proc = _run("neodev.py", "--help")

    assert proc.returncode == 0
    assert "neodev doctor" in proc.stdout
    assert "neodev context show" in proc.stdout
    assert "neodev setup repo" in proc.stdout
    assert "neodev docs sync" in proc.stdout
    assert "neodev change start" in proc.stdout
    assert "neodev change impact" in proc.stdout
    assert "neodev git check" in proc.stdout
    assert "neodev status" in proc.stdout
    assert "neodev help --all" in proc.stdout
    assert "graph edge add" not in proc.stdout
    assert "git post-push-graph-update" not in proc.stdout
    assert "product version analyze" not in proc.stdout


def test_help_all_lists_all_visibility_levels_and_advanced_commands():
    proc = _run("neodev.py", "help", "--all")

    assert proc.returncode == 0
    assert "Primary" in proc.stdout
    assert "Advanced" in proc.stdout
    assert "Internal" in proc.stdout
    assert "Hidden" in proc.stdout
    assert "neodev graph edge add" in proc.stdout
    assert "manual graph mutation" in proc.stdout
    assert "neodev git post-push-graph-update" in proc.stdout
    assert "hook-only" in proc.stdout
    assert "neodev product version analyze" in proc.stdout


def test_help_all_json_returns_command_metadata():
    proc = _run("neodev.py", "help", "--all", "--json")

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["command"] == "help all"
    commands = {item["command"]: item for item in payload["data"]["commands"]}
    assert commands["neodev docs sync"]["visibility"] == "primary"
    assert commands["neodev graph edge add"]["visibility"] == "advanced"
    assert commands["neodev graph edge add"]["risk"] == "manual graph mutation"
    assert commands["neodev git post-push-graph-update"]["visibility"] == "internal"
    assert commands["neodev git post-push-graph-update"]["replacement"] == "neodev status"
    assert commands["neodev product version analyze"]["visibility"] == "hidden"


def test_command_metadata_covers_required_cli_layers():
    from service.cli.command_metadata import CommandVisibility, get_command_metadata

    metadata = get_command_metadata()
    by_command = {"neodev " + " ".join(item.path): item for item in metadata}

    assert by_command["neodev doctor"].visibility is CommandVisibility.PRIMARY
    assert by_command["neodev docs sync"].visibility is CommandVisibility.PRIMARY
    assert by_command["neodev graph edge add"].visibility is CommandVisibility.ADVANCED
    assert by_command["neodev git post-push-graph-update"].visibility is CommandVisibility.INTERNAL
    assert by_command["neodev product version analyze"].visibility is CommandVisibility.HIDDEN


def test_all_registered_commands_have_metadata():
    from service.cli.command_metadata import get_command_metadata
    from service.cli.executor import build_parser

    registered = {"neodev " + " ".join(path) for path in _registered_command_paths(build_parser())}
    metadata = {item.command for item in get_command_metadata()}

    assert registered - metadata == set()


def _registered_command_paths(
    parser: argparse.ArgumentParser,
    prefix: tuple[str, ...] = (),
) -> set[tuple[str, ...]]:
    subparser_actions = [
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    ]
    if not subparser_actions:
        return {prefix}

    paths: set[tuple[str, ...]] = set()
    for action in subparser_actions:
        for name, subparser in action.choices.items():
            paths.update(_registered_command_paths(subparser, prefix + (name,)))
    return paths


def test_doc_change_commands_are_registered():
    register = _run("neodev.py", "doc", "change", "register", "--help")
    assert register.returncode == 0
    assert "--document-id" in register.stdout
    assert "--doc-change-id" in register.stdout

    show = _run("neodev.py", "doc", "change", "show", "--help")
    assert show.returncode == 0
    assert "--doc-change-id" in show.stdout

    implemented = _run("neodev.py", "doc", "change", "mark-implemented", "--help")
    assert implemented.returncode == 0
    assert "--doc-change-id" in implemented.stdout


def test_doc_import_command_is_registered():
    proc = _run("neodev.py", "doc", "import", "--help")
    assert proc.returncode == 0
    assert "--doc-binding-id" in proc.stdout
    assert "--force" in proc.stdout


def test_doc_graph_show_command_accepts_name_scope():
    proc = _run("neodev.py", "doc", "graph", "show", "--help")
    assert proc.returncode == 0
    assert "--product-name" in proc.stdout
    assert "--version-name" in proc.stdout
    assert "--json" in proc.stdout


def test_doc_binding_commands_are_registered():
    create = _run("neodev.py", "doc", "binding", "create", "--help")
    assert create.returncode == 0
    assert "--product-code" in create.stdout
    assert "--project-id" in create.stdout
    assert "--repo-url" in create.stdout
    assert "--branch" in create.stdout

    list_proc = _run("neodev.py", "doc", "binding", "list", "--help")
    assert list_proc.returncode == 0
    assert "--product-code" in list_proc.stdout
    assert "--product-id" in list_proc.stdout

    switch = _run("neodev.py", "doc", "binding", "switch", "--help")
    assert switch.returncode == 0
    assert "--doc-binding-id" in switch.stdout
    assert "--version-id" in switch.stdout
    assert "--version-name" in switch.stdout
    assert "--repo-path" in switch.stdout
    assert "--repo-url" in switch.stdout
    assert "--branch" in switch.stdout
    assert "--json" in switch.stdout


def test_git_verify_doc_change_command_is_registered():
    proc = _run("neodev.py", "git", "verify-doc-change", "--help")
    assert proc.returncode == 0
    assert "--project-id" in proc.stdout
    assert "--branch" in proc.stdout
    assert "--commit-sha" in proc.stdout
    assert "--commit-message" in proc.stdout


def test_git_post_push_graph_update_command_is_registered():
    proc = _run("neodev.py", "git", "post-push-graph-update", "--help")
    assert proc.returncode == 0
    assert "--payload-file" in proc.stdout
    assert "--payload-json" in proc.stdout
    assert "--json" in proc.stdout


def test_git_post_push_payload_argument_errors_do_not_need_rollback():
    from service.cli.commands import git as git_command

    try:
        git_command._load_post_push_payload(SimpleNamespace(payload_file=None, payload_json=None))
    except CliError as exc:
        assert exc.category == "invalid_argument"
        assert exc.details["rollback_status"] == "not_needed"
    else:
        raise AssertionError("expected payload argument error")


def test_git_post_push_payload_json_errors_do_not_need_rollback():
    from service.cli.commands import git as git_command

    try:
        git_command._load_post_push_payload(SimpleNamespace(payload_file=None, payload_json="{bad"))
    except CliError as exc:
        assert exc.category == "invalid_argument"
        assert exc.details["rollback_status"] == "not_needed"
    else:
        raise AssertionError("expected payload JSON error")


def test_git_dangerous_commit_commands_are_registered():
    list_proc = _run("neodev.py", "git", "dangerous-commit", "list", "--help")
    assert list_proc.returncode == 0
    assert "--project-id" in list_proc.stdout

    resolve_proc = _run("neodev.py", "git", "dangerous-commit", "resolve", "--help")
    assert resolve_proc.returncode == 0
    assert "--record-id" in resolve_proc.stdout
    assert "--resolved-by" in resolve_proc.stdout


def test_git_post_push_refresh_command_is_removed():
    proc = _run("neodev.py", "git", "post-push-refresh", "--help")
    assert proc.returncode != 0
    assert "invalid choice" in proc.stdout


def test_project_refresh_graph_command_is_registered():
    proc = _run("neodev.py", "project", "refresh-graph", "--help")
    assert proc.returncode == 0
    assert "--project-id" in proc.stdout
    assert "--project-name" in proc.stdout
    assert "--branch" in proc.stdout
    assert "--version-id" not in proc.stdout
    assert "--json" in proc.stdout


def test_product_version_code_fact_commands_are_registered():
    show = _run("neodev.py", "product", "version", "show", "--help")
    assert show.returncode == 0
    assert "--product-name" in show.stdout
    assert "--product-code" in show.stdout
    assert "--version-name" in show.stdout
    assert "--project-name" in show.stdout
    assert "--branch-name" in show.stdout
    assert "--version-id" not in show.stdout

    link = _run("neodev.py", "product", "version", "link-code", "--help")
    assert link.returncode == 0
    assert "--doc-id" in link.stdout
    assert "--symbol-key" not in link.stdout
    assert "--code-node-id" in link.stdout
    assert "--locator-json" in link.stdout
    assert "--unlink" in link.stdout
    assert "--link-id" in link.stdout
    assert "--relation-type" in link.stdout
    assert "--code-project-id" in link.stdout

    unbind = _run("neodev.py", "product", "version", "unbind-branch", "--help")
    assert unbind.returncode == 0
    assert "--project-id" in unbind.stdout
    assert "--project-name" in unbind.stdout
    assert "--branch" not in unbind.stdout
    assert "--json" in unbind.stdout

    facts = _run("neodev.py", "product", "version", "code-facts", "--help")
    assert facts.returncode == 0
    assert "--doc-id" in facts.stdout
    assert "--node-type" in facts.stdout
    assert "--json" in facts.stdout


def test_project_refresh_commit_graph_command_is_removed():
    proc = _run("neodev.py", "project", "refresh-commit-graph", "--help")
    assert proc.returncode != 0
    assert "invalid choice" in proc.stdout


def test_graph_semantic_search_command_is_removed():
    proc = _run("neodev.py", "graph", "semantic-search", "--help")
    assert proc.returncode != 0
    assert "invalid choice" in proc.stdout


def test_graph_impact_command_is_registered():
    proc = _run("neodev.py", "graph", "impact", "--help")
    assert proc.returncode == 0
    assert "--change-id" in proc.stdout
    assert "--doc-change-id" in proc.stdout


def test_graph_refresh_nodes_command_is_removed():
    proc = _run("neodev.py", "graph", "refresh-nodes", "--help")
    assert proc.returncode != 0
    assert "invalid choice" in proc.stdout


def test_graph_entity_context_command_is_registered():
    proc = _run("neodev.py", "graph", "entity-context", "--help")
    assert proc.returncode == 0
    assert "--product-name" in proc.stdout
    assert "--product-code" in proc.stdout
    assert "--version-name" in proc.stdout
    assert "--project-id" in proc.stdout
    assert "--branch" in proc.stdout
    assert "--branch-name" in proc.stdout
    assert "--entity-id" in proc.stdout
    assert "--depth" in proc.stdout


def test_graph_get_chain_command_is_registered():
    proc = _run("neodev.py", "graph", "get-chain", "--help")
    assert proc.returncode == 0
    assert "--product-name" in proc.stdout
    assert "--product-code" in proc.stdout
    assert "--version-name" in proc.stdout
    assert "--project-id" in proc.stdout
    assert "--branch" in proc.stdout
    assert "--branch-name" in proc.stdout
    assert "--start-node" in proc.stdout
    assert "--file-path" in proc.stdout
    assert "--symbol" in proc.stdout
    assert "--commit-sha" in proc.stdout
    assert "--depth" in proc.stdout


def test_graph_management_commands_are_registered():
    node_type = _run("neodev.py", "graph", "type", "node", "add", "--help")
    assert node_type.returncode == 0
    assert "--project-id" in node_type.stdout
    assert "--key" in node_type.stdout
    assert "--name" in node_type.stdout

    edge_type = _run("neodev.py", "graph", "type", "edge", "add", "--help")
    assert edge_type.returncode == 0
    assert "--project-id" in edge_type.stdout
    assert "--key" in edge_type.stdout
    assert "--cross-project-allowed" in edge_type.stdout

    node_update = _run("neodev.py", "graph", "node", "update", "--help")
    assert node_update.returncode == 0
    assert "--project-id" in node_update.stdout
    assert "--node-id" in node_update.stdout
    assert "--type" in node_update.stdout
    assert "--prop" in node_update.stdout

    edge_add = _run("neodev.py", "graph", "edge", "add", "--help")
    assert edge_add.returncode == 0
    assert "--project-id" in edge_add.stdout
    assert "--from-node-id" in edge_add.stdout
    assert "--to-node-id" in edge_add.stdout
    assert "--type" in edge_add.stdout
