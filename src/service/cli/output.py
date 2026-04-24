from copy import deepcopy
from datetime import datetime, timezone

from service.cli.errors import CliError


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_success_payload(command: str, data: dict | None = None) -> dict:
    return {
        "ok": True,
        "command": command,
        "timestamp": _timestamp(),
        "data": deepcopy(data or {}),
        "errors": [],
    }


def build_error_payload(command: str, error: CliError) -> dict:
    return {
        "ok": False,
        "command": command,
        "timestamp": _timestamp(),
        "data": None,
        "errors": [error.to_dict()],
    }
