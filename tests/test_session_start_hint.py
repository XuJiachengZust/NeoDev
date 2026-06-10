import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins" / "neodev-rd-knowledge" / "session_start_hint.py"


def test_session_start_hint_is_lightweight_context_only():
    payload = {
        "hook_event_name": "SessionStart",
        "source": "startup",
        "cwd": str(ROOT),
    }

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0
    assert proc.stderr == ""
    assert "NeoDev RD Knowledge session hint" in proc.stdout
    assert "neodev config show" in proc.stdout
    assert "neodev cli version-check --json" in proc.stdout
    assert "post_push_graph_update.py --json" in proc.stdout
    assert "no remote calls and no writes" in proc.stdout
    assert "project refresh-graph" not in proc.stdout
