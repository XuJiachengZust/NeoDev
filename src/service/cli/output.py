from copy import deepcopy
from datetime import date
from datetime import datetime, timezone

from service.cli.errors import CliError


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_ready(value):
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def build_success_payload(command: str, data: dict | None = None) -> dict:
    return {
        "ok": True,
        "command": command,
        "timestamp": _timestamp(),
        "data": _json_ready(deepcopy(data or {})),
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
