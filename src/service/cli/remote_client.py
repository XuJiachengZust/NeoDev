import json
import urllib.error
import urllib.request

from service.cli.errors import CliError, error_to_exit_code
from service.cli.output import build_error_payload


def execute_remote(server_url: str, argv: list[str]) -> tuple[int, dict]:
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
