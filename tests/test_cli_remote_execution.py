import json
import importlib.util
import shutil
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parent.parent


def _local_tmp_dir(name: str) -> Path:
    path = ROOT / ".test-tmp" / f"{name}-{uuid.uuid4().hex[:8]}"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def _load_module(path: Path):
    spec = importlib.util.spec_from_file_location(f"neodev_client_{uuid.uuid4().hex}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_cli_main_forwards_all_command_arguments_to_remote_server(monkeypatch, capsys):
    from service.cli import main as cli_main

    calls = {}

    def fake_execute_remote(server_url, argv):
        calls["server_url"] = server_url
        calls["argv"] = argv
        return 0, {
            "ok": True,
            "command": "product show",
            "timestamp": "2026-04-27T00:00:00+00:00",
            "data": {"remote": True},
            "errors": [],
        }

    monkeypatch.setattr(cli_main, "execute_remote", fake_execute_remote)

    rc = cli_main.main(
        [
            "--server",
            "http://10.50.3.149",
            "product",
            "show",
            "--product-code",
            "NEODEV",
            "--json",
        ]
    )

    assert rc == 0
    assert calls == {
        "server_url": "http://10.50.3.149",
        "argv": ["product", "show", "--product-code", "NEODEV", "--json"],
    }
    assert json.loads(capsys.readouterr().out)["data"] == {"remote": True}


def test_cli_main_uses_neodev_api_url_env_for_remote_server(monkeypatch, capsys):
    from service.cli import main as cli_main

    calls = {}

    def fake_execute_remote(server_url, argv):
        calls["server_url"] = server_url
        calls["argv"] = argv
        return 0, {
            "ok": True,
            "command": "cli version-check",
            "timestamp": "2026-04-27T00:00:00+00:00",
            "data": {"remote": True},
            "errors": [],
        }

    monkeypatch.setattr(cli_main, "execute_remote", fake_execute_remote)
    monkeypatch.setenv("NEODEV_API_URL", "http://10.50.3.149")

    rc = cli_main.main(["cli", "version-check", "--json"])

    assert rc == 0
    assert calls == {
        "server_url": "http://10.50.3.149",
        "argv": ["cli", "version-check", "--json"],
    }
    assert json.loads(capsys.readouterr().out)["data"] == {"remote": True}


def test_cli_main_prints_plain_remote_output_without_json(monkeypatch, capsys):
    from service.cli import main as cli_main

    calls = {}

    def fake_execute_remote(server_url, argv):
        calls["server_url"] = server_url
        calls["argv"] = argv
        return 0, {
            "ok": True,
            "command": "cli version-check",
            "timestamp": "2026-04-27T00:00:00+00:00",
            "data": {"remote": True},
            "errors": [],
        }

    monkeypatch.setattr(cli_main, "execute_remote", fake_execute_remote)

    rc = cli_main.main(["--server", "http://10.50.3.149", "cli", "version-check"])

    assert rc == 0
    assert calls == {
        "server_url": "http://10.50.3.149",
        "argv": ["cli", "version-check"],
    }
    output = capsys.readouterr().out
    assert not output.lstrip().startswith("{")
    assert "command: cli version-check" in output
    assert "remote: true" in output


def test_cli_main_follows_project_init_progress_in_text_mode(monkeypatch, capsys):
    from service.cli import main as cli_main

    calls = []
    responses = [
        (
            0,
            {
                "ok": True,
                "command": "project create",
                "timestamp": "2026-04-28T00:00:00+00:00",
                "data": {
                    "project": {
                        "id": 42,
                        "name": "repo",
                        "init_result": {"status": "queued"},
                    },
                    "auto_graph_analysis": True,
                },
                "errors": [],
            },
        ),
        (
            0,
            {
                "ok": True,
                "command": "project init-status",
                "timestamp": "2026-04-28T00:00:01+00:00",
                "data": {
                    "init_status": {
                        "status": "running",
                        "progress": {
                            "stage": "repository_clone",
                            "done": 0,
                            "total": 5,
                            "detail": "正在拉取仓库",
                        },
                        "key_nodes": [
                            {"stage": "repository_clone", "label": "拉取仓库", "status": "running"}
                        ],
                    }
                },
                "errors": [],
            },
        ),
        (
            0,
            {
                "ok": True,
                "command": "project init-status",
                "timestamp": "2026-04-28T00:00:02+00:00",
                "data": {
                    "init_status": {
                        "status": "completed",
                        "progress": {
                            "stage": "completed",
                            "done": 5,
                            "total": 5,
                            "detail": "图谱构建完成",
                        },
                        "key_nodes": [
                            {"stage": "completed", "label": "完成", "status": "completed"}
                        ],
                    }
                },
                "errors": [],
            },
        ),
    ]

    def fake_execute_remote(server_url, argv):
        calls.append((server_url, argv))
        return responses.pop(0)

    monkeypatch.setattr(cli_main, "execute_remote", fake_execute_remote)
    monkeypatch.setattr(cli_main.time, "sleep", lambda seconds: None)

    rc = cli_main.main(
        [
            "--server",
            "http://10.50.3.149",
            "project",
            "create",
            "--name",
            "repo",
            "--repo-url",
            "git@example/repo.git",
        ]
    )

    assert rc == 0
    assert calls[1][1] == ["project", "init-status", "--project-id", "42", "--json"]
    assert calls[2][1] == ["project", "init-status", "--project-id", "42", "--json"]
    output = capsys.readouterr().out
    assert "init_result:" not in output
    assert "status: queued" not in output
    assert "[project 42] repository_clone 0/5 (running)" in output
    assert "[project 42] completed 5/5 (completed)" in output


def test_cli_main_does_not_follow_project_init_in_json_mode(monkeypatch, capsys):
    from service.cli import main as cli_main

    calls = []

    def fake_execute_remote(server_url, argv):
        calls.append(argv)
        return 0, {
            "ok": True,
            "command": "project create",
            "timestamp": "2026-04-28T00:00:00+00:00",
            "data": {"project": {"id": 42, "init_result": {"status": "queued"}}},
            "errors": [],
        }

    monkeypatch.setattr(cli_main, "execute_remote", fake_execute_remote)

    rc = cli_main.main(
        [
            "--server",
            "http://10.50.3.149",
            "project",
            "create",
            "--name",
            "repo",
            "--repo-url",
            "git@example/repo.git",
            "--json",
        ]
    )

    assert rc == 0
    assert len(calls) == 1
    assert json.loads(capsys.readouterr().out)["command"] == "project create"


def test_cli_execute_api_reuses_existing_cli_contract():
    from service.main import app

    with TestClient(app) as client:
        response = client.post(
            "/api/cli/execute",
            json={"argv": ["cli", "version-check", "--json"]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["exit_code"] == 0
    assert body["payload"]["ok"] is True
    assert body["payload"]["command"] == "cli version-check"
    assert body["payload"]["data"]["plugin_version"] == "0.2.0"
    assert body["payload"]["data"]["skill_version"] == "0.2.0"
    assert body["payload"]["data"]["compatible"] is True


def test_cli_execute_api_returns_help_payload_instead_of_raising():
    from service.main import app

    with TestClient(app) as client:
        response = client.post("/api/cli/execute", json={"argv": ["--help"]})

    assert response.status_code == 200
    body = response.json()
    assert body["exit_code"] == 0
    assert body["payload"]["ok"] is True
    assert body["payload"]["command"] == "help"
    assert "usage: neodev" in body["payload"]["data"]["text"]


def test_code_ai_preprocess_routes_are_not_registered():
    from service.main import app

    paths = {getattr(route, "path", "") for route in app.routes}

    assert "/api/projects/{project_id}/preprocess" not in paths
    assert "/api/projects/{project_id}/preprocess/status" not in paths


def test_cli_main_prints_remote_help_text(monkeypatch, capsys):
    from service.cli import main as cli_main

    def fake_execute_remote(server_url, argv):
        return 0, {
            "ok": True,
            "command": "help",
            "timestamp": "2026-04-27T00:00:00+00:00",
            "data": {"text": "usage: neodev ...\n"},
            "errors": [],
        }

    monkeypatch.setattr(cli_main, "execute_remote", fake_execute_remote)

    rc = cli_main.main(["--server", "http://10.50.3.149", "--help"])

    assert rc == 0
    assert capsys.readouterr().out == "usage: neodev ...\n"


def test_install_client_command_writes_terminal_wrapper(capsys):
    from service.cli import main as cli_main

    install_dir = _local_tmp_dir("client-install")
    rc = cli_main.main(
        [
            "install-client",
            "--bin-dir",
            str(install_dir),
            "--config-dir",
            str(install_dir / "config"),
            "--no-path-update",
            "--json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["command"] == "install-client"
    assert payload["data"]["server_url"] is None
    assert (install_dir / "neodev_client.py").exists()
    assert (install_dir / "neodev.cmd").exists()
    assert "config set-server" in (install_dir / "neodev_client.py").read_text(encoding="utf-8")
    assert 'payload.get("command") == "help"' in (
        install_dir / "neodev_client.py"
    ).read_text(encoding="utf-8")
    assert "_render_payload" in (install_dir / "neodev_client.py").read_text(encoding="utf-8")
    assert "_follow_project_init" in (install_dir / "neodev_client.py").read_text(encoding="utf-8")
    assert "_prepare_remote_argv" in (install_dir / "neodev_client.py").read_text(encoding="utf-8")


def test_installed_client_sends_local_post_push_payload_file_as_json(monkeypatch, capsys):
    from service.cli import main as cli_main

    install_dir = _local_tmp_dir("client-local-payload")
    rc = cli_main.main(
        [
            "install-client",
            "--bin-dir",
            str(install_dir),
            "--config-dir",
            str(install_dir / "config"),
            "--no-path-update",
            "--json",
        ]
    )
    assert rc == 0
    capsys.readouterr()

    payload_file = install_dir / "payload.json"
    payload_file.write_text('{"branch": "neodev-sp"}', encoding="utf-8")
    client = _load_module(install_dir / "neodev_client.py")
    calls = {}

    def fake_execute_remote(server_url, argv):
        calls["server_url"] = server_url
        calls["argv"] = argv
        return 0, {
            "ok": True,
            "command": "git post-push-graph-update",
            "timestamp": "2026-05-26T00:00:00+00:00",
            "data": {"accepted": True},
            "errors": [],
        }

    monkeypatch.setattr(client, "_execute_remote", fake_execute_remote)

    run_rc = client.main(
        [
            "--server",
            "http://10.50.3.149",
            "git",
            "post-push-graph-update",
            "--payload-file",
            str(payload_file),
            "--json",
        ]
    )

    assert run_rc == 0
    assert calls["server_url"] == "http://10.50.3.149"
    assert calls["argv"] == [
        "git",
        "post-push-graph-update",
        "--payload-json",
        '{"branch": "neodev-sp"}',
        "--json",
    ]


def test_install_client_command_defaults_to_plain_text(capsys):
    from service.cli import main as cli_main

    install_dir = _local_tmp_dir("client-install-plain")
    rc = cli_main.main(
        [
            "install-client",
            "--bin-dir",
            str(install_dir),
            "--config-dir",
            str(install_dir / "config"),
            "--no-path-update",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert not output.lstrip().startswith("{")
    assert "command: install-client" in output
    assert "written:" in output
    assert "neodev_client.py" in output


def test_config_set_server_and_show_are_local_commands(monkeypatch, capsys):
    from service.cli import main as cli_main

    config_dir = _local_tmp_dir("client-config")
    monkeypatch.setenv("NEODEV_CONFIG_DIR", str(config_dir))

    set_rc = cli_main.main(["config", "set-server", "http://10.50.3.149"])
    set_output = capsys.readouterr().out
    show_rc = cli_main.main(["config", "show"])
    show_output = capsys.readouterr().out

    assert set_rc == 0
    assert "server_url: http://10.50.3.149" in set_output
    assert show_rc == 0
    assert "server_url: http://10.50.3.149" in show_output


def test_config_commands_can_still_print_json_when_requested(monkeypatch, capsys):
    from service.cli import main as cli_main

    config_dir = _local_tmp_dir("client-config-json")
    monkeypatch.setenv("NEODEV_CONFIG_DIR", str(config_dir))

    set_rc = cli_main.main(["config", "set-server", "http://10.50.3.149", "--json"])
    set_payload = json.loads(capsys.readouterr().out)
    show_rc = cli_main.main(["config", "show", "--json"])
    show_payload = json.loads(capsys.readouterr().out)

    assert set_rc == 0
    assert set_payload["data"]["server_url"] == "http://10.50.3.149"
    assert show_rc == 0
    assert show_payload["data"]["server_url"] == "http://10.50.3.149"


def test_cli_main_uses_configured_server_by_default(monkeypatch, capsys):
    from service.cli import main as cli_main

    config_dir = _local_tmp_dir("client-config-default")
    monkeypatch.setenv("NEODEV_CONFIG_DIR", str(config_dir))
    cli_main.main(["config", "set-server", "http://10.50.3.149"])
    capsys.readouterr()

    calls = {}

    def fake_execute_remote(server_url, argv):
        calls["server_url"] = server_url
        calls["argv"] = argv
        return 0, {
            "ok": True,
            "command": "cli version-check",
            "timestamp": "2026-04-27T00:00:00+00:00",
            "data": {"remote": True},
            "errors": [],
        }

    monkeypatch.setattr(cli_main, "execute_remote", fake_execute_remote)

    rc = cli_main.main(["cli", "version-check", "--json"])

    assert rc == 0
    assert calls == {
        "server_url": "http://10.50.3.149",
        "argv": ["cli", "version-check", "--json"],
    }
    assert json.loads(capsys.readouterr().out)["data"] == {"remote": True}


def test_github_powershell_installer_supports_one_line_remote_install():
    script = ROOT / "scripts" / "install-neodev-client.ps1"
    text = script.read_text(encoding="utf-8")

    assert "param(" in text
    assert "[string]$Server" in text
    assert "neodev_client.py" in text
    assert "config set-server" in text
    assert "neodev.cmd" in text
    assert "_render_payload" in text
    assert "_prepare_remote_argv" in text


def test_windows_cmd_installer_bypasses_powershell_execution_policy():
    script = ROOT / "scripts" / "install-neodev-client.cmd"
    text = script.read_text(encoding="utf-8")

    assert "powershell.exe" in text
    assert "-NoProfile" in text
    assert "-ExecutionPolicy Bypass" in text
    assert "install-neodev-client.ps1" in text
