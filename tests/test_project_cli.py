import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NEODEV_CONFIG_DIR"] = str(ROOT / ".test-tmp" / "project-cli-config")
    env.setdefault(
        "DATABASE_URL",
        env.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/neodev"),
    )
    return subprocess.run(
        [sys.executable, "neodev.py", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_project_create_command_is_registered_for_repo_url():
    proc = _run_cli("project", "create", "--help")

    assert proc.returncode == 0
    assert "--repo-url" in proc.stdout
    assert "--repo-path" in proc.stdout


def test_project_create_passes_repo_url_and_triggers_auto_graph_sync(monkeypatch):
    from service.cli.commands import project as project_command

    captured = {}

    def fake_with_db(callback):
        return callback(object())

    def fake_create_project(conn, **kwargs):
        captured.update(kwargs)
        return {
            "id": 42,
            "name": kwargs["name"],
            "repo_path": kwargs["repo_path"],
            "repo_url": kwargs["repo_url"],
            "init_result": {
                "default_branch": "main",
                "version_id": 7,
                "sync": {"graph_action": "full", "commits_synced": 3},
                "error": None,
            },
        }

    monkeypatch.setattr(project_command, "_with_db", fake_with_db)
    monkeypatch.setattr(project_command.project_service, "create_project", fake_create_project)

    payload = project_command.handle_project_create(
        argparse.Namespace(
            command_name="project create",
            name="Manual Project",
            repo_url="https://example.invalid/repo.git",
            repo_path=None,
            watch_enabled=False,
            neo4j_database=None,
            neo4j_identifier=None,
            repo_username=None,
            repo_password=None,
        )
    )

    assert payload["ok"] is True
    assert payload["command"] == "project create"
    assert captured["repo_path"] == "https://example.invalid/repo.git"
    assert captured["repo_url"] == "https://example.invalid/repo.git"
    assert payload["data"]["auto_graph_analysis"] is True
    assert payload["data"]["project"]["init_result"]["sync"]["graph_action"] == "full"
