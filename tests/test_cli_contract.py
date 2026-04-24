import json
import subprocess
import sys
from pathlib import Path

from service.cli.errors import CliError, error_to_exit_code
from service.cli.output import build_error_payload, build_success_payload

ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
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
    assert "plugin_version" in payload["data"]
    assert "skill_version" in payload["data"]
    assert payload["data"]["compatible"] is True
    assert payload["data"]["update_available"] is False
    assert payload["data"]["target_version"]
    assert isinstance(payload["data"]["message"], str)
    assert payload["data"]["message"]
    assert payload["errors"] == []


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
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "unknown"
    assert payload["data"] is None
    assert payload["errors"][0]["category"] == "invalid_argument"


def test_missing_cli_subcommand_returns_structured_json_error():
    proc = _run("neodev.py", "cli")
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "unknown"
    assert payload["data"] is None
    assert payload["errors"][0]["category"] == "invalid_argument"
