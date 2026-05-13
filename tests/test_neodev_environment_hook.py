import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins" / "neodev-rd-knowledge" / "check_neodev_environment.py"


def _local_tmp_dir(name: str) -> Path:
    path = ROOT / ".test-tmp" / f"{name}-{uuid.uuid4().hex[:8]}"
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_environment_hook_reports_missing_cli_with_structured_error(monkeypatch):
    env = os.environ.copy()
    env["PATH"] = ""
    env.pop("NEODEV_CLI", None)

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["errors"][0]["category"] == "not_ready"
    assert "install-neodev-client.ps1" in payload["errors"][0]["message"]


def test_environment_hook_accepts_configured_cli(monkeypatch):
    tmp_path = _local_tmp_dir("env-hook")
    cli = tmp_path / ("neodev.cmd" if os.name == "nt" else "neodev")
    marker = tmp_path / "calls.txt"
    if os.name == "nt":
        cli.write_text(
            "@echo off\r\n"
            f"echo %*>> \"{marker}\"\r\n"
            "echo {\"ok\": true, \"command\": \"stub\", \"timestamp\": null, \"data\": {\"server_url\": \"http://example\", \"compatible\": true}, \"errors\": []}\r\n",
            encoding="utf-8",
        )
    else:
        cli.write_text(
            "#!/usr/bin/env sh\n"
            f"echo \"$@\" >> \"{marker}\"\n"
            "echo '{\"ok\": true, \"command\": \"stub\", \"timestamp\": null, \"data\": {\"server_url\": \"http://example\", \"compatible\": true}, \"errors\": []}'\n",
            encoding="utf-8",
        )
        cli.chmod(0o755)

    env = os.environ.copy()
    env["NEODEV_CLI"] = str(cli)

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    calls = marker.read_text(encoding="utf-8")
    assert "config show --json" in calls
    assert "cli version-check --json" in calls
