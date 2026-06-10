import json
from pathlib import Path
import urllib.error
import urllib.request

from service.cli.errors import CliError, error_to_exit_code
from service.cli.output import build_error_payload


def execute_remote(server_url: str, argv: list[str]) -> tuple[int, dict]:
    try:
        argv = prepare_remote_argv(argv)
    except CliError as exc:
        return error_to_exit_code(exc), build_error_payload("git post-push-graph-update", exc)

    endpoint = f"{server_url.rstrip('/')}/api/cli/execute"
    body = json.dumps({"argv": argv}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        error = CliError(
            category="internal_error",
            message=f"remote CLI request failed with HTTP {exc.code}",
            details={"server_url": server_url, "detail": detail},
        )
        return error_to_exit_code(error), build_error_payload("remote cli execute", error)
    except (OSError, json.JSONDecodeError) as exc:
        error = CliError(
            category="internal_error",
            message="remote CLI request failed",
            details={"server_url": server_url, "error": str(exc)},
        )
        return error_to_exit_code(error), build_error_payload("remote cli execute", error)

    remote_payload = payload.get("payload")
    if not isinstance(remote_payload, dict):
        error = CliError(
            category="internal_error",
            message="remote CLI response missing payload",
            details={"server_url": server_url, "response": payload},
        )
        return error_to_exit_code(error), build_error_payload("remote cli execute", error)
    return int(payload.get("exit_code", 0)), remote_payload


def prepare_remote_argv(argv: list[str]) -> list[str]:
    if argv[:2] != ["git", "post-push-graph-update"]:
        return list(argv)
    if "--payload-file" not in argv and not any(item.startswith("--payload-file=") for item in argv):
        return list(argv)
    if "--payload-json" in argv or any(item.startswith("--payload-json=") for item in argv):
        return list(argv)

    prepared: list[str] = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--payload-file":
            if index + 1 >= len(argv):
                return list(argv)
            payload_file = argv[index + 1]
            prepared.extend(["--payload-json", _read_local_payload(payload_file)])
            index += 2
            continue
        if item.startswith("--payload-file="):
            payload_file = item.split("=", 1)[1]
            prepared.extend(["--payload-json", _read_local_payload(payload_file)])
            index += 1
            continue
        prepared.append(item)
        index += 1
    return prepared


def _read_local_payload(payload_file: str) -> str:
    try:
        return Path(payload_file).read_text(encoding="utf-8")
    except OSError as exc:
        raise CliError(
            category="invalid_argument",
            message="payload file is not readable",
            details={"payload_file": payload_file, "error": str(exc), "rollback_status": "not_needed"},
        ) from exc
