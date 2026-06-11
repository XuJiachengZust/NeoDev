import json
import os
import subprocess
import sys
from pathlib import Path

from service.cli.errors import CliError


ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NEODEV_CONFIG_DIR"] = str(ROOT / ".test-tmp" / "cli-workflow-config")
    return subprocess.run(
        [sys.executable, "neodev.py", *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_primary_workflow_commands_return_closure_payloads():
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
        proc = _run(*args, "--json")
        assert proc.returncode == 0, (args, proc.stdout, proc.stderr)
        payload = json.loads(proc.stdout)
        data = payload["data"]
        assert data["scenario_id"]
        assert data["stage"]
        assert data["summary"] is not None
        assert data["steps"], args
        assert data["closure_evidence"], args
        assert data["next_actions"], args
        for step in data["steps"]:
            assert {"id", "command", "status", "summary"}.issubset(step)


def test_workflow_runner_reports_failed_step_and_retry_hint():
    from service.cli.workflow_runner import WorkflowStepSpec, run_workflow

    def fail_docs():
        raise CliError("validation_error", "front matter invalid", {"file": "docs/example.md"})

    result = run_workflow(
        scenario_id="S02",
        stage="docs",
        steps=[
            WorkflowStepSpec("validate_docs", "validate_mvp_docs.py", run=fail_docs, retry_hint="Fix front matter and rerun `neodev docs sync`."),
            WorkflowStepSpec("import_docs", "neodev doc import", summary="Import controlled documents."),
        ],
        summary={"doc_graph_status": "blocked"},
        closure_evidence=[{"type": "doc_graph", "status": "blocked"}],
        next_actions=[{"intent": "docs", "command": "neodev docs sync"}],
    )

    assert result["failed_step"] == "validate_docs"
    assert result["retry_hint"] == "Fix front matter and rerun `neodev docs sync`."
    assert result["steps"][0]["status"] == "failed"
    assert result["steps"][0]["error"]["category"] == "validation_error"
    assert result["steps"][1]["status"] == "skipped"
