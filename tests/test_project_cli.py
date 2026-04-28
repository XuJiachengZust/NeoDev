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

    status = _run_cli("project", "init-status", "--help")
    assert status.returncode == 0
    assert "--project-id" in status.stdout
    assert "--project-name" in status.stdout


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
                "status": "queued",
                "mode": "background",
                "status_command": "neodev project init-status --project-id 42",
                "progress": {"stage": "queued", "done": 0, "total": 5},
                "key_nodes": [{"stage": "repository_clone", "status": "pending"}],
                "default_branch": None,
                "version_id": None,
                "sync": None,
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
    assert captured["async_init"] is True
    assert captured["overwrite_existing"] is True
    assert payload["data"]["auto_graph_analysis"] is True
    assert payload["data"]["project"]["init_result"]["status"] == "queued"
    assert payload["data"]["project"]["init_result"]["status_command"] == (
        "neodev project init-status --project-id 42"
    )


def test_project_init_status_returns_process_and_key_nodes(monkeypatch):
    from service.cli.commands import project as project_command

    def fake_with_db(callback):
        return callback(object())

    monkeypatch.setattr(project_command, "_with_db", fake_with_db)
    monkeypatch.setattr(
        project_command.project_service,
        "find_projects_by_name",
        lambda conn, name: [{"id": 42, "name": name, "repo_url": "git@example/repo.git"}],
    )
    monkeypatch.setattr(
        project_command.project_service,
        "get_init_status",
        lambda conn, project_id: {
            "project": {"id": project_id, "name": "Manual Project"},
            "init_status": {
                "status": "running",
                "progress": {"stage": "graph_sync", "done": 3, "total": 5},
                "key_nodes": [
                    {"stage": "repository_clone", "label": "拉取仓库", "status": "completed"},
                    {"stage": "graph_sync", "label": "同步提交并构建图谱", "status": "running"},
                ],
            },
        },
    )

    payload = project_command.handle_project_init_status(
        argparse.Namespace(
            command_name="project init-status",
            project_id=None,
            project_name="Manual Project",
        )
    )

    assert payload["ok"] is True
    assert payload["command"] == "project init-status"
    assert payload["data"]["init_status"]["status"] == "running"
    assert payload["data"]["init_status"]["key_nodes"][1]["stage"] == "graph_sync"


def test_project_name_locator_selects_latest_duplicate(monkeypatch):
    from service.cli.commands import project as project_command

    matches = [
        {"id": 195, "name": "duplicate", "repo_url": "git@example/old.git"},
        {"id": 196, "name": "duplicate", "repo_url": "git@example/new.git"},
    ]
    monkeypatch.setattr(
        project_command.project_service,
        "find_projects_by_name",
        lambda conn, name: matches,
    )

    selected = project_command._resolve_project(
        object(),
        argparse.Namespace(project_id=None, project_name="duplicate"),
    )

    assert selected["id"] == 196
    assert selected["_duplicate_project_ids"] == [195]
    assert selected["_selected_by_name"] == "duplicate"
