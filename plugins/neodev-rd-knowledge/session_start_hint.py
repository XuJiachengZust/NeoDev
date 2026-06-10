"""Print lightweight NeoDev session-start guidance."""

from __future__ import annotations

import json
import sys
from typing import Any


def main() -> int:
    payload = _read_payload()
    source = str(payload.get("source") or "session").strip() or "session"
    print(
        "\n".join(
            [
                f"NeoDev RD Knowledge session hint ({source}):",
                "- For NeoDev state-changing workflows, verify the local client first: "
                "`neodev config show` and `neodev cli version-check --json`.",
                "- After a successful Agent `git push`, do not manually refresh the graph; "
                "the plugin PostToolUse hook runs `post_push_graph_update.py --json`.",
                "- This SessionStart hook performs no remote calls and no writes.",
            ]
        )
    )
    return 0


def _read_payload() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
    except OSError:
        return {}
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
