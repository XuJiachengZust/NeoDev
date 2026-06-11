from copy import deepcopy
from datetime import date
from datetime import datetime, timezone
import json

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
        "errors": [_json_ready(error.to_dict())],
    }


def render_payload(payload: dict, json_output: bool = False) -> str:
    if json_output:
        return json.dumps(payload, ensure_ascii=False) + "\n"

    if payload.get("command") in {"help", "help all"}:
        text = (payload.get("data") or {}).get("text")
        if isinstance(text, str):
            return text if text.endswith("\n") else text + "\n"

    if not payload.get("ok"):
        return _render_error(payload)

    lines = [f"command: {payload.get('command', 'unknown')}", "ok: true"]
    data = payload.get("data") or {}
    message = data.get("message") if isinstance(data, dict) else None
    if isinstance(message, str) and message.strip():
        lines.insert(0, message)
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "message":
                continue
            _append_plain(lines, key, value)
    elif data:
        _append_plain(lines, "data", data)
    return "\n".join(lines) + "\n"


def _render_error(payload: dict) -> str:
    errors = payload.get("errors") or []
    if not errors:
        return f"ERROR: command failed: {payload.get('command', 'unknown')}\n"
    lines = []
    for error in errors:
        category = error.get("category") or "error"
        message = error.get("message") or "command failed"
        lines.append(f"ERROR [{category}]: {message}")
        details = error.get("details") or {}
        if isinstance(details, dict):
            for key, value in details.items():
                _append_plain(lines, f"details.{key}", value)
    return "\n".join(lines) + "\n"


def _append_plain(lines: list[str], key: str, value, indent: int = 0) -> None:
    if key == "init_result":
        return
    prefix = "  " * indent
    if isinstance(value, dict):
        if not value:
            lines.append(f"{prefix}{key}: {{}}")
            return
        lines.append(f"{prefix}{key}:")
        for child_key, child_value in value.items():
            _append_plain(lines, str(child_key), child_value, indent + 1)
        return
    if isinstance(value, list):
        if not value:
            lines.append(f"{prefix}{key}: []")
            return
        lines.append(f"{prefix}{key}:")
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}  -")
                _append_plain(lines, "value", item, indent + 2)
            else:
                lines.append(f"{prefix}  - {_plain_scalar(item)}")
        return
    lines.append(f"{prefix}{key}: {_plain_scalar(value)}")


def _plain_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
